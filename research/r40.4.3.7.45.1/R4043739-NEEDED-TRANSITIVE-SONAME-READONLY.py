#!/usr/bin/env python3
"""R4043739 static DT_NEEDED provider-graph and SONAME audit, NOT_BOOTABLE.

Stage is never modified or executed. Path and library names never leave memory.
Static basename matches are NOT dynamic loader resolution or symbol closure.
"""
import argparse
from collections import Counter, defaultdict, deque
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct

PARENT = 'R4043738-NEEDED-LIBRARY-CANDIDATES-READONLY.py'
PARENT_SHA256 = '66f5f3d1fd62c7ad3515c57a1e72b32e2f41be4e9ab74b67d1144f07f1ab2ee3'
EXPECTED_CATEGORY = {'ONE_REGULAR_ABI_HEADER_BASENAME_CANDIDATE': 19}
MAX_GRAPH_NODES = 128
MAX_GRAPH_EDGES = 1024

class Hold(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code

def load_parent(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('PARENT_DIRECTORY_HOLD')
    path = folder / PARENT
    if path.is_symlink() or not path.is_file():
        raise Hold('PARENT_SOURCE_FILE_HOLD')
    if hashlib.sha256(path.read_bytes()).hexdigest() != PARENT_SHA256:
        raise Hold('PARENT_SOURCE_SHA256_HOLD')
    spec = importlib.util.spec_from_file_location('r3738_pinned_for_r3739', path)
    if spec is None or spec.loader is None:
        raise Hold('PARENT_IMPORT_HOLD')
    parent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parent)
    return parent

def read_soname(p26, path):
    """Return optional bounded DT_SONAME bytes, without printing them."""
    try:
        with p26.open_regular_nofollow(path) as f:
            h = p26.elf_header(f)
            if h is None or h['cls'] != 1 or h['machine'] != 40 or h['phsize'] < 32:
                raise Hold('PROVIDER_NOT_ELF32_ARM_HOLD')
            loads = []
            dynamic = []
            for i in range(h['phnum']):
                r = p26.read_at(f, h['phoff'] + i * h['phsize'], h['phsize'])
                typ,off,va,_,filesz,memsz,_,_ = struct.unpack_from(h['endian']+'IIIIIIII',r)
                if typ not in (1, 2):
                    continue
                if off > h['length'] or filesz > h['length']-off or filesz > memsz or va + memsz > 2**32:
                    raise Hold('PROVIDER_SEGMENT_BOUNDS_HOLD')
                if typ == 1:
                    loads.append((va,off,filesz))
                else:
                    dynamic.append((off,filesz))
            if not loads or len(dynamic) > 1:
                raise Hold('PROVIDER_DYNAMIC_LAYOUT_HOLD')
            if not dynamic:
                return None
            off,size=dynamic[0]
            if not size or size > 65536 or size % 8:
                raise Hold('PROVIDER_DYNAMIC_LENGTH_HOLD')
            tags=defaultdict(list)
            end=False
            for i in range(size//8):
                tag,val=struct.unpack(h['endian']+'II',p26.read_at(f,off+8*i,8))
                if tag==0:
                    end=True
                    break
                if tag in (14,5,10):
                    tags[tag].append(val)
            if not end:
                raise Hold('PROVIDER_DYNAMIC_TERMINATION_HOLD')
            if not tags[14]:
                return None
            if len(tags[14])!=1 or len(tags[5])!=1 or len(tags[10])!=1:
                raise Hold('PROVIDER_SONAME_DESCRIPTOR_HOLD')
            addr,length=tags[5][0],tags[10][0]
            if not length or length>2**20 or addr+length>2**32:
                raise Hold('PROVIDER_STRTAB_SIZE_HOLD')
            offsets={fo+addr-va for va,fo,sz in loads if va <= addr and addr-va <= sz and length <= sz-(addr-va)}
            if len(offsets)!=1:
                raise Hold('PROVIDER_STRTAB_MAPPING_HOLD')
            table=p26.read_at(f,next(iter(offsets)),length)
            pos=tags[14][0]
            if pos>=length:
                raise Hold('PROVIDER_SONAME_OFFSET_HOLD')
            stop=table.find(b'\0',pos)
            if stop<0 or stop==pos or stop-pos>4096:
                raise Hold('PROVIDER_SONAME_LITERAL_HOLD')
            return table[pos:stop]
    except p26.Hold:
        raise Hold('PROVIDER_ELF_READ_HOLD') from None

def providers_for_needed(root, byte_index, name, hdr, p26):
    """Classify all same-basename candidates; return physical paths only in memory."""
    if b'/' in name or b'\\' in name or not name or name in (b'.',b'..'):
        return 'NAME_PATH_COMPONENT_REVIEW', []
    entries=byte_index.get(name,())
    hits=[]
    for path,typ in entries:
        g='/' + path.relative_to(root).as_posix()
        try:
            status,hops=p26.classify_guest_target(root,g,hdr)
        except p26.Hold:
            raise Hold('PROVIDER_GUEST_CLASSIFIER_HOLD') from None
        if status=='GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE':
            hits.append((path,typ,hops))
    if len(hits)>1:
        return 'MULTIPLE_HEADER_CANDIDATES',hits
    if len(hits)==1 and hits[0][1]=='regular' and hits[0][2]==0:
        return 'ONE_REGULAR_HEADER_CANDIDATE',hits
    if len(hits)==1:
        return 'ONE_SYMLINK_OR_REDIRECTED_CANDIDATE',hits
    if entries:
        return 'BASENAME_PRESENT_NO_COMPATIBLE_PROVIDER',hits
    return 'NO_BASENAME_PROVIDER_IN_STAGE',hits

def cycle_stats(graph):
    """Tarjan SCC in a bounded graph; no node labels leave process."""
    order={}; low={}; stack=[]; members=set(); sccs=[]
    def visit(v):
        order[v]=len(order);low[v]=order[v]; stack.append(v);members.add(v)
        for w in sorted(graph.get(v,()),key=lambda x:str(x)):
            if w not in order:
                visit(w);low[v]=min(low[v],low[w])
            elif w in members:
                low[v]=min(low[v],order[w])
        if low[v]==order[v]:
            comp=[]
            while True:
                x=stack.pop();members.remove(x);comp.append(x)
                if x==v:break
            sccs.append(comp)
    for node in sorted(graph,key=lambda x:str(x)):
        if node not in order:visit(node)
    cycles=[c for c in sccs if len(c)>1 or (len(c)==1 and c[0] in graph.get(c[0],()))]
    return {'cyclic_strong_components':len(cycles),
            'nodes_in_cycles':sum(map(len,cycles)),
            'largest_cyclic_component_size':max((len(c) for c in cycles),default=0)}

def graph_audit(root, folder, parent, *, require_baseline=True, overrides=None):
    if root.is_symlink() or not root.is_dir():
        raise Hold('ROOTFS_INVALID_HOLD')
    if require_baseline:
        try:
            prior=parent.audit(root,folder,parent.load_parent(folder))
        except parent.Hold:
            raise Hold('R3738_PARENT_REPLAY_HOLD') from None
        if (prior.get('result')!='REQUESTER_NEEDED_BASENAME_STATIC_CANDIDATES_ONLY'
                or prior.get('source_elf_count')!=12
                or prior.get('dt_needed_entries')!=19
                or prior.get('distinct_dt_needed_name_literals')!=6
                or prior.get('dt_needed_same_basename_candidate_categories')!=EXPECTED_CATEGORY
                or prior.get('compatible_regular_entry_matches_across_needed_edges')!=19
                or prior.get('compatible_symlink_entry_matches_across_needed_edges')!=0
                or prior.get('per_source_dt_needed_entry_count_histogram')!={'1':7,'2':4,'4':1}
                or prior.get('stage_modified') is not False):
            raise Hold('R3738_COUNTS_REPLAY_HOLD')
    if overrides is None:
        p37=parent.load_parent(folder)
        p36=p37.import_parent(folder)
        p35=p36.import_parent(folder)
        p34=p35.import_parent(folder)
        p33=p34.import_r33(folder)
        p26=p33.import_parent(folder/p33.R3726,p33.R3726)
        p27=p33.import_parent(folder/p33.R3727,p33.R3727)
        index,sources,nfiles,nlinks=p27.inventory(root,p26)
    else:
        p26,p27,index,sources,nfiles,nlinks=overrides
    if nfiles!=1446 or nlinks!=335 or len(sources)!=12 or len({name for name,_ in sources})!=1:
        raise Hold('R3727_INVENTORY_REPLAY_HOLD')
    missing=sources[0][0]
    byte_index={}
    for name, entries in index.items():
        key=os.fsencode(name)
        if key in byte_index:
            raise Hold('BASENAME_ENCODING_COLLISION_HOLD')
        byte_index[key]=entries
    # Collect twelve requesting ELF files by the exact missing interpreter literal.
    source_elfs=[]
    for base,dirs,names in os.walk(root,topdown=True,followlinks=False):
        dirs[:]=sorted(x for x in dirs if not (Path(base)/x).is_symlink())
        for name in sorted(names):
            path=Path(base)/name
            if not stat.S_ISREG(path.lstat().st_mode):
                continue
            try:
                with p26.open_regular_nofollow(path) as f:
                    parsed=p26.inspect_elf(f)
            except p26.Hold:
                raise Hold('R3726_ELF_SCAN_HOLD') from None
            if parsed and any(x==missing for x,_ in parsed[1]):
                source_elfs.append(path)
    if len(source_elfs)!=12:
        raise Hold('SOURCE_ELF_COUNT_HOLD')
    direct=Counter(); direct_names=set(); seeds={}; direct_edges=0
    for path in source_elfs:
        needed,hdr=parent.elf_needed_literals(p26,path)
        for name in needed:
            direct_edges+=1;direct_names.add(name)
            cat,hits=providers_for_needed(root,byte_index,name,hdr,p26)
            direct[cat]+=1
            if cat=='ONE_REGULAR_HEADER_CANDIDATE':
                value=hits[0][0]
                if name in seeds and seeds[name]!=value:
                    raise Hold('DIRECT_PROVIDER_INCONSISTENT_HOLD')
                seeds[name]=value
    if direct_edges!=19 or len(direct_names)!=6 or direct!={'ONE_REGULAR_HEADER_CANDIDATE':19} or len(seeds)!=6:
        raise Hold('DIRECT_19_SIX_PROVIDER_REPLAY_HOLD')
    source_names=defaultdict(set)
    for name,path in seeds.items():source_names[path].add(name)
    queue=deque(sorted(set(seeds.values()),key=str))
    seen=set();graph=defaultdict(set);sonames=Counter();edges=Counter();needed_total=0
    while queue:
        path=queue.popleft()
        if path in seen:continue
        if len(seen)>=MAX_GRAPH_NODES:
            raise Hold('PROVIDER_GRAPH_NODE_BOUND_HOLD')
        seen.add(path);graph[path]
        needed,hdr=parent.elf_needed_literals(p26,path)
        soname=read_soname(p26,path)
        expected=source_names.get(path,())
        if soname is None:
            sonames['SONAME_UNDECLARED']+=1
        elif not expected:
            sonames['NO_EXPECTED_NEEDED_NAME']+=1
        elif all(soname==v for v in expected):
            sonames['SONAME_EQUALS_REFERENCED_NEEDED_NAME']+=1
        else:
            sonames['SONAME_DIFFERS_FROM_REFERENCED_NEEDED_NAME']+=1
        for name in needed:
            needed_total+=1
            if needed_total>MAX_GRAPH_EDGES:
                raise Hold('PROVIDER_GRAPH_EDGE_BOUND_HOLD')
            cat,hits=providers_for_needed(root,byte_index,name,hdr,p26)
            edges[cat]+=1
            if cat=='ONE_REGULAR_HEADER_CANDIDATE':
                nxt=hits[0][0]
                source_names[nxt].add(name)
                graph[path].add(nxt)
                if nxt not in seen and nxt not in queue:queue.append(nxt)
    cyc=cycle_stats(graph)
    return {'milestone':'R40.4.3.7.39',
            'result':'STATIC_SONAME_AND_TRANSITIVE_BASENAME_GRAPH_CLASSIFIED_ONLY',
            'parent_r3738_sha256_pinned_and_replayed':True,
            'earlier_source_sha_pins_inherited':True,
            'source_elf_count':12,'direct_needed_edges':19,'distinct_direct_needed_literals':6,
            'unique_initial_provider_regular_files':len(set(seeds.values())),
            'transitive_graph_regular_files_seen':len(seen),
            'provider_soname_categories':dict(sorted(sonames.items())),
            'provider_needed_edges_scanned':needed_total,
            'provider_needed_basename_candidate_categories':dict(sorted(edges.items())),
            'provider_graph_cycles':cyc,
            'dependency_graph_is_only_static_basename_evidence':True,
            'actual_dynamic_library_search_paths_verified':False,
            'dynamic_symbol_version_resolution_verified':False,
            'full_dependency_closure_proven':False,
            'arm_tls_runtime_compatibility_verified':False,
            'interpreter_guest_path_resolved':False,
            'mapping_applied':False,
            'original_r26_source_provenance_authenticated':False,
            'historical_inventory_hashes_reverified':False,
            'private_paths_names_symbols_exported':False,
            'stage_modified':False,
            'boot_authorized':False,'prune_authorized':False,
            'firmware_write_authorized':False,
            'immutable_hold':'NOT_BOOTABLE'}

def main():
    ap=argparse.ArgumentParser(description='Read-only SONAME/transitive basename graph; NOT_BOOTABLE')
    ap.add_argument('--rootfs',required=True,type=Path)
    ap.add_argument('--parent-dir',required=True,type=Path)
    args=ap.parse_args()
    try:
        parent=load_parent(args.parent_dir)
        output=graph_audit(args.rootfs,args.parent_dir,parent)
    except (Hold,OSError,RecursionError) as exc:
        code=exc.code if isinstance(exc,Hold) else 'HOST_IO_OR_GRAPH_HOLD'
        output={'milestone':'R40.4.3.7.39','result':'HOLD','hold_category':code,
                'boot_authorized':False,'prune_authorized':False,'immutable_hold':'NOT_BOOTABLE'}
    print(json.dumps(output,sort_keys=True))
    return 0 if output['result']=='STATIC_SONAME_AND_TRANSITIVE_BASENAME_GRAPH_CLASSIFIED_ONLY' else 2

if __name__=='__main__':raise SystemExit(main())
