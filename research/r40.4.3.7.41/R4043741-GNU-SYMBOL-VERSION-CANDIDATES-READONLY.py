#!/usr/bin/env python3
"""R4043741: read-only bounded GNU ELF symbol-version candidate classification.

Uses the SHA-pinned R3740 graph/name audit and original R13 rootfs. Never loads
an ELF, applies relocations, modifies the rootfs, or exposes any guest path,
SONAME, library or dynamic-symbol name. Results are static candidate counts.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct

PARENT = 'R4043740-SYMBOL-NAME-VERSION-READONLY.py'
PARENT_SHA256 = '075869999337fb6601e2d4f49a0bf28786a9879337fbba54c54b77ea58785d91'
SHT_DYNSYM = 11
SHT_DYNSTR = 3
SHT_VERSYM = 0x6fffffff
SHT_VERDEF = 0x6ffffffd
SHT_VERNEED = 0x6ffffffe
DT_VERSYM = 0x6ffffff0
DT_VERDEF = 0x6ffffffc
DT_VERDEFNUM = 0x6ffffffd
DT_VERNEED = 0x6ffffffe
DT_VERNEEDNUM = 0x6fffffff
MAX_VERSION_RECORDS = 4096

class Hold(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def load_parent(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('PARENT_DIRECTORY_HOLD')
    path = folder/PARENT
    if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=PARENT_SHA256:
        raise Hold('R3740_PARENT_SHA_HOLD')
    spec=importlib.util.spec_from_file_location('pinned_r3740_for_r3741',path)
    if not spec or not spec.loader:raise Hold('R3740_PARENT_IMPORT_HOLD')
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def u16(data, off, endian):
    if off<0 or off+2>len(data):raise Hold('VERSION_FIELD_BOUNDS_HOLD')
    return struct.unpack_from(endian+'H',data,off)[0]


def u32(data,off,endian):
    if off<0 or off+4>len(data):raise Hold('VERSION_FIELD_BOUNDS_HOLD')
    return struct.unpack_from(endian+'I',data,off)[0]


def parse_verdef(data, dynstr, expected, endian, p40):
    """Return version-index to private bytes name; fail closed for malformed lists."""
    if expected<1 or expected>MAX_VERSION_RECORDS:raise Hold('VERDEF_COUNT_HOLD')
    out={}
    offset=0
    visited=set()
    for i in range(expected):
        if offset in visited or offset+20>len(data):raise Hold('VERDEF_HEADER_BOUNDS_HOLD')
        visited.add(offset)
        vers,flags,idx,cnt = struct.unpack_from(endian+'HHHH',data,offset)
        aux=u32(data,offset+12,endian);nxt=u32(data,offset+16,endian)
        if vers!=1 or idx<1 or cnt<1 or cnt>128 or aux<20:
            raise Hold('VERDEF_DESCRIPTOR_HOLD')
        if idx in out:raise Hold('VERDEF_DUPLICATE_INDEX_HOLD')
        auxpos=offset+aux
        # Explicit bounds: at least the first Verdaux must be accessible.
        nameoff=u32(data,auxpos,endian)
        out[idx]=p40.checked_cstr(dynstr,nameoff)
        ap=auxpos
        for j in range(cnt):
            step=u32(data,ap+4,endian)
            if j+1<cnt:
                if step<8:raise Hold('VERDEF_AUX_CHAIN_HOLD')
                ap+=step
                u32(data,ap,endian)
            elif step!=0:
                raise Hold('VERDEF_AUX_END_HOLD')
        if i+1<expected:
            if nxt<20:raise Hold('VERDEF_NEXT_HOLD')
            offset+=nxt
            if offset>=len(data):raise Hold('VERDEF_NEXT_BOUNDS_HOLD')
        elif nxt!=0:
            raise Hold('VERDEF_TERMINATION_HOLD')
    return out


def parse_verneed(data,dynstr,expected,endian,p40):
    """Return per-requirement version index to private bytes version name."""
    if expected<1 or expected>MAX_VERSION_RECORDS:raise Hold('VERNEED_COUNT_HOLD')
    out={}
    pos=0
    seen=set()
    for i in range(expected):
        if pos in seen or pos+16>len(data):raise Hold('VERNEED_HEADER_BOUNDS_HOLD')
        seen.add(pos)
        vers,cnt=struct.unpack_from(endian+'HH',data,pos)
        liboff=u32(data,pos+4,endian);aux=u32(data,pos+8,endian);nxt=u32(data,pos+12,endian)
        if vers!=1 or cnt<1 or cnt>128 or aux<16:
            raise Hold('VERNEED_DESCRIPTOR_HOLD')
        p40.checked_cstr(dynstr,liboff)  # check, never export
        ap=pos+aux
        auxseen=set()
        for j in range(cnt):
            if ap in auxseen or ap+16>len(data):raise Hold('VERNEED_AUX_BOUNDS_HOLD')
            auxseen.add(ap)
            _,flags,other,nameoff,nextaux=struct.unpack_from(endian+'IHHII',data,ap)
            idx=other&0x7fff
            if idx<=1 or idx in out:raise Hold('VERNEED_VERSION_INDEX_HOLD')
            out[idx]={'version':p40.checked_cstr(dynstr,nameoff),'weak':bool(flags&2)}
            if j+1<cnt:
                if nextaux<16:raise Hold('VERNEED_AUX_CHAIN_HOLD')
                ap+=nextaux
            elif nextaux!=0:
                raise Hold('VERNEED_AUX_END_HOLD')
        if i+1<expected:
            if nxt<16:raise Hold('VERNEED_NEXT_HOLD')
            pos+=nxt
            if pos>=len(data):raise Hold('VERNEED_NEXT_BOUNDS_HOLD')
        elif nxt!=0:
            raise Hold('VERNEED_TERMINATION_HOLD')
    return out


def parse_version_file(p26,p40,path):
    """Cross-check version sections against file-backed PT_DYNAMIC descriptors."""
    baseline=p40.parse_dynamic_and_sections(p26,path)
    try:
        with p26.open_regular_nofollow(path) as f:
            h=p26.elf_header(f)
            if not h or h['cls']!=1 or h['machine']!=40 or h['phsize']!=32:
                raise Hold('ELF_HEADER_HOLD')
            loads=[];dynamic=[]
            for i in range(h['phnum']):
                typ,offset,vaddr,_,filesz,memsz,_,_ = struct.unpack(h['endian']+'IIIIIIII',p26.read_at(f,h['phoff']+32*i,32))
                if typ in (1,2):
                    if offset>h['length'] or filesz>h['length']-offset or filesz>memsz:
                        raise Hold('VERSION_PHDR_BOUNDS_HOLD')
                    if typ==1:loads.append((vaddr,offset,filesz))
                    else:dynamic.append((offset,filesz))
            if len(dynamic)!=1:raise Hold('VERSION_DYNAMIC_COUNT_HOLD')
            off,sz=dynamic[0]
            if sz%8 or sz==0 or sz>65536:raise Hold('VERSION_DYNAMIC_SIZE_HOLD')
            tags={};terminated=False
            for i in range(sz//8):
                t,v=struct.unpack(h['endian']+'II',p26.read_at(f,off+8*i,8))
                if t==0:terminated=True;break
                if t in tags and t not in (1,):raise Hold('VERSION_DUPLICATE_DYNAMIC_TAG_HOLD')
                tags[t]=v
            if not terminated or any(t not in tags for t in (5,6,10,11)):
                raise Hold('VERSION_DYNAMIC_TERMINATION_HOLD')
            dstr=p26.read_at(f,p40.map_filebacked(loads,tags[5],tags[10]),tags[10])
            shoff=u32(p26.read_at(f,32,4),0,h['endian'])
            shentsize,shnum=struct.unpack(h['endian']+'HH',p26.read_at(f,46,4))
            if shentsize!=40 or not 1<=shnum<=16384 or shoff>h['length'] or shnum*40>h['length']-shoff:
                raise Hold('VERSION_SECTION_TABLE_HOLD')
            sect=[]
            for i in range(shnum):
                _,t,_,addr,fo,fs,link,info,align,entsize=struct.unpack(h['endian']+'IIIIIIIIII',p26.read_at(f,shoff+i*40,40))
                sect.append(dict(type=t,addr=addr,off=fo,size=fs,link=link,info=info,entsize=entsize))
            dyn=[i for i,s in enumerate(sect) if s['type']==SHT_DYNSYM]
            strs=[i for i,s in enumerate(sect) if s['type']==SHT_DYNSTR and s['addr']==tags[5]]
            if len(dyn)!=1 or len(strs)!=1:raise Hold('VERSION_DYNSYM_OR_DYNSTR_HOLD')
            count=len(baseline['symbols'])
            out={'versym':[1]*count,'verdef':{},'verneed':{},**baseline}
            for t,secid,numid in ((DT_VERSYM,SHT_VERSYM,None),(DT_VERDEF,SHT_VERDEF,DT_VERDEFNUM),(DT_VERNEED,SHT_VERNEED,DT_VERNEEDNUM)):
                found=[s for s in sect if s['type']==secid]
                if t not in tags:
                    if found or (numid is not None and numid in tags):raise Hold('VERSION_TAG_SECTION_MISMATCH_HOLD')
                    continue
                if len(found)!=1:raise Hold('VERSION_SECTION_COUNT_HOLD')
                s=found[0]
                if s['link'] != (dyn[0] if t==DT_VERSYM else strs[0]):
                    raise Hold('VERSION_SECTION_LINK_HOLD')
                if s['addr']!=tags[t] or s['size']==0 or s['size']>262144 or s['off']>h['length'] or s['size']>h['length']-s['off']:
                    raise Hold('VERSION_SECTION_BOUNDS_HOLD')
                if p40.map_filebacked(loads,tags[t],s['size'])!=s['off']:
                    raise Hold('VERSION_SECTION_NOT_FILEBACKED_HOLD')
                data=p26.read_at(f,s['off'],s['size'])
                if t==DT_VERSYM:
                    if s['size']!=count*2 or s['entsize'] not in (0,2):raise Hold('VERSYM_COUNT_HOLD')
                    out['versym']=list(struct.unpack(h['endian']+'H'*count,data))
                else:
                    if numid not in tags or tags[numid]!=s['info'] or not 1<=tags[numid]<=MAX_VERSION_RECORDS:
                        raise Hold('VERSION_RECORD_COUNT_HOLD')
                    parsed=(parse_verdef(data,dstr,tags[numid],h['endian'],p40) if t==DT_VERDEF
                            else parse_verneed(data,dstr,tags[numid],h['endian'],p40))
                    out['verdef' if t==DT_VERDEF else 'verneed']=parsed
            return out
    except p26.Hold:
        raise Hold('VERSION_ELF_READ_HOLD') from None


def classify_version_candidates(sources,providers):
    """Compare private version names only. No runtime lookup or interposition."""
    names=defaultdict(list)
    for provider in providers:
        for i,sym in enumerate(provider['symbols']):
            if (sym['defined'] and sym['name'] and sym['binding'] in (1,2,10)
                and sym['visibility'] in (0,3)):
                v=provider['versym'][i];idx=v&0x7fff
                if idx>1 and idx not in provider['verdef']:
                    raise Hold('PROVIDER_VERSION_DEFINITION_MISSING_HOLD')
                names[sym['name']].append((idx, bool(v&0x8000),provider['verdef'].get(idx)))
    cats=Counter();requirements=Counter();seen=0;refnames=set();vrequired=set()
    for source in sources:
        for i in source['referenced_indices']:
            sym=source['symbols'][i]
            if sym['defined']:continue
            seen+=1
            name=sym['name'];refnames.add(name)
            if not name:raise Hold('UNDEFINED_EMPTY_NAME_HOLD')
            v=source['versym'][i];idx=v&0x7fff
            if idx==0:
                raise Hold('UNDEFINED_LOCAL_VERSION_HOLD')
            if idx>1:
                req=source['verneed'].get(idx)
                if req is None:raise Hold('REQUEST_VERSION_REQUIREMENT_MISSING_HOLD')
                required=req['version'];vrequired.add(required)
                requirements['EXPLICIT_GNU_VERSION_REQUIREMENT']+=1
            else:
                required=None
                requirements['UNVERSIONED_OR_GLOBAL_REFERENCE']+=1
            options=names.get(name,[])
            if not options:
                cats['NO_STAGED_PROVIDER_NAME_CANDIDATE']+=1;continue
            if required is not None:
                strict=sum(1 for provider_index,hidden,definition in options if provider_index>1 and definition==required)
                if strict==0:
                    cats['NAME_CANDIDATE_BUT_NO_EQUAL_GNU_VERSION_NAME']+=1
                elif strict==1:cats['ONE_GNU_VERSION_NAME_MATCHING_CANDIDATE']+=1
                else:cats['MULTIPLE_GNU_VERSION_NAME_MATCHING_CANDIDATES']+=1
            else:
                acceptable=sum(1 for provider_index,hidden,definition in options if provider_index<=1 or not hidden)
                if acceptable==0:cats['ONLY_NONDEFAULT_VERSIONED_NAME_CANDIDATES']+=1
                elif acceptable==1:cats['ONE_DEFAULT_OR_UNVERSIONED_NAME_CANDIDATE']+=1
                else:cats['MULTIPLE_DEFAULT_OR_UNVERSIONED_NAME_CANDIDATES']+=1
    return {'referenced_undefined_entries_reclassified':seen,
            'distinct_undefined_names_reverified':len(refnames),
            'distinct_required_version_names_in_memory':len(vrequired),
            'source_symbol_version_requirement_categories':dict(sorted(requirements.items())),
            'version_filtered_static_candidate_categories':dict(sorted(cats.items())),
            'version_name_equality_is_not_runtime_resolution':True}


def locate_sources_providers(root,folder,p40):
    """Re-identify only pinned R3740 files, no directory or names exported."""
    p39=p40.import_parent(folder)
    p38=p39.load_parent(folder);p37=p38.load_parent(folder)
    p36=p37.import_parent(folder);p35=p36.import_parent(folder)
    p34=p35.import_parent(folder);p33=p34.import_r33(folder)
    p26=p33.import_parent(folder/p33.R3726,p33.R3726)
    p27=p33.import_parent(folder/p33.R3727,p33.R3727)
    index,sources,nreg,nlink=p27.inventory(root,p26)
    if nreg!=1446 or nlink!=335 or len(sources)!=12 or len({x for x,_ in sources})!=1:
        raise Hold('PINNED_STAGE_INVENTORY_DIFFERENT_HOLD')
    missing=sources[0][0]
    src=[]
    for base,dirs,files in os.walk(root,topdown=True,followlinks=False):
        dirs[:]=sorted(n for n in dirs if not (Path(base)/n).is_symlink())
        for name in sorted(files):
            path=Path(base)/name
            if not stat.S_ISREG(path.lstat().st_mode):continue
            with p26.open_regular_nofollow(path) as f:parsed=p26.inspect_elf(f)
            if parsed and any(g==missing for g,_ in parsed[1]):src.append(path)
    if len(src)!=12:raise Hold('R3740_REQUESTER_LIST_HOLD')
    byteindex={os.fsencode(k):v for k,v in index.items()}
    if len(byteindex)!=len(index):raise Hold('BASENAME_ENCODING_COLLISION_HOLD')
    found=set()
    for path in src:
        needed,hdr=p38.elf_needed_literals(p26,path)
        for literal in needed:
            category,hits=p39.providers_for_needed(root,byteindex,literal,hdr,p26)
            if category!='ONE_REGULAR_HEADER_CANDIDATE' or len(hits)!=1:
                raise Hold('R3740_PROVIDER_CANDIDATE_HOLD')
            found.add(hits[0][0])
    if len(found)!=6:raise Hold('R3740_PROVIDER_COUNT_HOLD')
    return p26,src,sorted(found)


def audit(root,folder,p40):
    if root.is_symlink() or not root.is_dir():raise Hold('ROOTFS_INVALID_HOLD')
    try:prev=p40.audit(root,folder,p40.import_parent(folder))
    except p40.Hold:raise Hold('R3740_PARENT_REPLAY_HOLD') from None
    if (prev.get('result')!='STAGED_SYMBOL_NAME_CANDIDATES_AND_VERSION_TAGS_STATIC_ONLY'
        or prev.get('source_elf_count')!=12 or prev.get('provider_elf_count')!=6
        or prev.get('referenced_undefined_dynsym_entries')!=632
        or prev.get('referenced_defined_or_special_dynsym_entries')!=145
        or prev.get('distinct_referenced_undefined_symbol_names')!=369
        or prev.get('undefined_symbol_candidate_categories')!={
            'MULTIPLE_STAGED_PROVIDER_NAME_CANDIDATES':80,
            'NO_STAGED_PROVIDER_NAME_CANDIDATE':35,
            'ONE_STAGED_PROVIDER_NAME_CANDIDATE':517}):
        raise Hold('R3740_STABLE_BASELINE_HOLD')
    try:p26,src,prov=locate_sources_providers(root,folder,p40)
    except (p40.Hold,OSError) as e:raise Hold('R3740_FILE_REDISCOVERY_HOLD') from None
    try:
        sources=[parse_version_file(p26,p40,p) for p in src]
        providers=[parse_version_file(p26,p40,p) for p in prov]
    except p40.Hold:raise Hold('VERSION_PARENT_ELF_REVIEW_HOLD') from None
    result=classify_version_candidates(sources,providers)
    if result['referenced_undefined_entries_reclassified']!=632 or result['distinct_undefined_names_reverified']!=369:
        raise Hold('VERSION_SOURCE_NAME_BASELINE_HOLD')
    return {'milestone':'R40.4.3.7.41','result':'GNU_SYMBOL_VERSION_REQUIREMENTS_STATIC_CANDIDATES_ONLY',
            'source_elf_count':12,'provider_elf_count':6,
            'parent_r3740_source_sha_pinned_and_replayed':True,
            'parent_r3739_and_prior_sha_pins_inherited':True,
            **result,
            'actual_loader_search_and_interposition_verified':False,
            'full_symbol_version_resolution_verified':False,
            'tls_runtime_compatibility_verified':False,
            'guest_interpreter_path_resolved':False,
            'future_image_mapping_applied':False,
            'source_provenance_authenticated':False,
            'stage_modified':False,'names_paths_strings_exported':False,
            'full_dependency_closure_proven':False,
            'boot_authorized':False,'prune_authorized':False,
            'firmware_write_authorized':False,
            'immutable_hold':'NOT_BOOTABLE'}


def main():
    arg=argparse.ArgumentParser(description='R3741 static GNU version candidate audit; NOT_BOOTABLE')
    arg.add_argument('--rootfs',type=Path,required=True)
    arg.add_argument('--parent-dir',type=Path,required=True)
    a=arg.parse_args()
    try:
        p40=load_parent(a.parent_dir)
        result=audit(a.rootfs,a.parent_dir,p40)
    except (Hold,OSError,RecursionError) as exc:
        result={'milestone':'R40.4.3.7.41','result':'HOLD',
                'hold_category':exc.code if isinstance(exc,Hold) else 'HOST_IO_OR_GRAPH_HOLD',
                'boot_authorized':False,'prune_authorized':False,'immutable_hold':'NOT_BOOTABLE'}
    print(json.dumps(result,sort_keys=True))
    return 0 if result['result']=='GNU_SYMBOL_VERSION_REQUIREMENTS_STATIC_CANDIDATES_ONLY' else 2

if __name__=='__main__':raise SystemExit(main())
