#!/usr/bin/env python3
"""R4043740: bounded STATIC ELF32 ARM dynsym-name candidate matching.

Read-only source research. All library, symbol and guest path names remain in
memory only; output is aggregate categories. No guest mapping, stage writes,
loader execution, QEMU, boot, pruning or firmware writes. NOT_BOOTABLE.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct

PARENT = 'R4043739-NEEDED-TRANSITIVE-SONAME-READONLY.py'
PARENT_SHA256 = '63f40e5932260ec0d2a2cdc2681ea5436153fa35ba8c2718881e5349b76f429b'
MAX_DYNSYM = 65536
MAX_STRTAB = 1 << 20
MAX_RELOC = 65536
VERSION_TAGS = {0x6ffffff0:'DT_VERSYM', 0x6ffffffe:'DT_VERNEED',
                0x6ffffffc:'DT_VERDEF'}
PATH_TAGS = {15:'DT_RPATH',29:'DT_RUNPATH'}

class Hold(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def import_parent(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('PARENT_DIRECTORY_HOLD')
    path = folder / PARENT
    if path.is_symlink() or not path.is_file():
        raise Hold('PARENT_SOURCE_MISSING_HOLD')
    if hashlib.sha256(path.read_bytes()).hexdigest() != PARENT_SHA256:
        raise Hold('PARENT_SOURCE_SHA_HOLD')
    spec = importlib.util.spec_from_file_location('r3739_pinned_for_r3740', path)
    if not spec or not spec.loader:
        raise Hold('PARENT_IMPORT_HOLD')
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def checked_cstr(table, offset):
    if not isinstance(offset,int) or not 0 <= offset < len(table):
        raise Hold('SYMBOL_NAME_OFFSET_HOLD')
    stop = table.find(b'\0', offset)
    if stop < 0 or stop-offset > 4096:
        raise Hold('SYMBOL_NAME_LENGTH_HOLD')
    return table[offset:stop]


def map_filebacked(loads, vaddr, size):
    if size < 0 or vaddr < 0 or vaddr+size > 0x100000000:
        raise Hold('ADDRESS_RANGE_HOLD')
    matches = {off+vaddr-va for va,off,filesz in loads
               if va <= vaddr and vaddr-va <= filesz and size <= filesz-(vaddr-va)}
    if len(matches) != 1:
        raise Hold('ADDRESS_LOAD_MAPPING_HOLD')
    return next(iter(matches))


def parse_dynamic_and_sections(p26, path):
    """Sections are cross-checked against the runtime PT_DYNAMIC VA descriptors.

    No symbol strings or paths are returned to output except to the in-memory
    caller. Fail closed for absent SHT_DYNSYM or non-file-backed symbol data.
    """
    try:
        with p26.open_regular_nofollow(path) as f:
            h = p26.elf_header(f)
            if h is None or h['cls'] != 1 or h['machine'] != 40 or h['phsize'] != 32:
                raise Hold('NOT_ELF32_ARM_HOLD')
            loads, dynamics = [], []
            for i in range(h['phnum']):
                ph = p26.read_at(f, h['phoff']+32*i, 32)
                kind,off,va,_,fsz,msz,_,_ = struct.unpack_from(h['endian']+'IIIIIIII',ph)
                if kind not in (1,2):
                    continue
                if off > h['length'] or fsz > h['length']-off or fsz > msz or va+msz > 0x100000000:
                    raise Hold('PHDR_BOUNDS_HOLD')
                (loads if kind == 1 else dynamics).append((va,off,fsz))
            if not loads or len(dynamics)!=1:
                raise Hold('PT_LOAD_DYNAMIC_LAYOUT_HOLD')
            _,d_off,d_len = dynamics[0]
            if d_len == 0 or d_len > 65536 or d_len % 8:
                raise Hold('DYNAMIC_LENGTH_HOLD')
            tags = {}
            repeats = Counter()
            ended = False
            for i in range(d_len//8):
                tag,val=struct.unpack(h['endian']+'II',p26.read_at(f,d_off+8*i,8))
                if tag == 0:
                    ended=True;break
                repeats[tag]+=1
                if tag not in tags: tags[tag]=val
            if not ended:
                raise Hold('DYNAMIC_TERMINATION_HOLD')
            # Singleton dynamic descriptors; duplicate DT_NEEDED is valid.
            for k in (5,6,10,11,17,18,19,7,8,9,23,2,20,15,29,*VERSION_TAGS):
                if repeats[k]>1:
                    raise Hold('REPEATED_DYNAMIC_DESCRIPTOR_HOLD')
            if not all(x in tags for x in (5,6,10,11)) or tags[11] != 16:
                raise Hold('DYNAMIC_SYMBOL_DESCRIPTORS_HOLD')
            if tags[10] == 0 or tags[10] > MAX_STRTAB:
                raise Hold('DYNAMIC_STRING_SIZE_HOLD')
            dynstr_off = map_filebacked(loads,tags[5],tags[10])
            dynstr = p26.read_at(f,dynstr_off,tags[10])
            shoff,=struct.unpack(h['endian']+'I',p26.read_at(f,32,4))
            shentsize, shnum, _ = struct.unpack(h['endian']+'HHH',p26.read_at(f,46,6))
            if shentsize != 40 or not 1 <= shnum <= 16384 or shoff == 0 or shoff > h['length'] or shnum*shentsize > h['length']-shoff:
                raise Hold('SECTION_HEADER_LAYOUT_HOLD')
            sections=[]
            for i in range(shnum):
                sec=p26.read_at(f,shoff+40*i,40)
                _,stype,_,addr,off,size,link,_,_,entsize=struct.unpack(h['endian']+'IIIIIIIIII',sec)
                if off > h['length'] or size > h['length']-off:
                    # NOBITS does not occupy file bytes; never used as dynsym.
                    if stype != 8:raise Hold('SECTION_FILE_BOUNDS_HOLD')
                sections.append((stype,addr,off,size,link,entsize))
            symsecs=[x for x in sections if x[0] == 11]
            if len(symsecs)!=1:
                raise Hold('DYNSYM_SECTION_COUNT_HOLD')
            stype,addr,symoff,size,link,entsize=symsecs[0]
            if addr != tags[6] or entsize != 16 or not size or size%16 or size//16 > MAX_DYNSYM:
                raise Hold('DYNSYM_SECTION_DESCRIPTOR_HOLD')
            if map_filebacked(loads,addr,size)!=symoff:
                raise Hold('DYNSYM_NOT_FILEBACKED_HOLD')
            if link >= len(sections) or sections[link][0] != 3:
                raise Hold('DYNSYM_STRTAB_LINK_HOLD')
            _t,straddr,stroff,strsz,_,_=sections[link]
            if straddr != tags[5] or stroff != dynstr_off or strsz != tags[10]:
                raise Hold('DYNSYM_DYNSTR_MISMATCH_HOLD')
            records=[]
            for i in range(size//16):
                raw=p26.read_at(f,symoff+i*16,16)
                nameoff,_,_,info,other,section=struct.unpack(h['endian']+'IIIBBH',raw)
                name=checked_cstr(dynstr,nameoff)
                records.append({'name':name,'defined':section!=0,
                                'binding':info>>4,'type':info&15,
                                'visibility':other&3})
            # Read relocation indices, not relocated values or symbol definitions.
            tables=[]
            def table(ptr,sizekey,entrykey,width):
                presence=[k in tags for k in (ptr,sizekey,entrykey)]
                if not any(presence):return
                if not all(presence) or tags[entrykey]!=width or tags[sizekey]>MAX_RELOC*width or tags[sizekey]%width:
                    raise Hold('RELOCATION_DESCRIPTOR_HOLD')
                if tags[sizekey]:
                    tables.append((map_filebacked(loads,tags[ptr],tags[sizekey]),tags[sizekey]//width,width))
            table(17,18,19,8);table(7,8,9,12)
            if any(k in tags for k in (23,2,20)):
                if not all(k in tags for k in (23,2,20)) or tags[20] not in (17,7):
                    raise Hold('PLT_RELOCATION_DESCRIPTOR_HOLD')
                width=8 if tags[20]==17 else 12
                if tags[2]>MAX_RELOC*width or tags[2]%width:
                    raise Hold('PLT_RELOCATION_SIZE_HOLD')
                if tags[2]:tables.append((map_filebacked(loads,tags[23],tags[2]),tags[2]//width,width))
            references=set()
            entries=0
            for off,n,width in tables:
                entries+=n
                for i in range(n):
                    _,info=struct.unpack(h['endian']+'II',p26.read_at(f,off+i*width,8))
                    index=info>>8
                    if index >= len(records):
                        raise Hold('DYNAMIC_SYMBOL_INDEX_OUTSIDE_SECTION_HOLD')
                    if index:
                        references.add(index)
            meta={k: k in tags for k in (*VERSION_TAGS,*PATH_TAGS)}
            return {'symbols':records,'referenced_indices':references,'relocation_entries':entries,
                    'metadata':meta,'dynamic_symbol_count':len(records)}
    except p26.Hold:
        raise Hold('ELF_SOURCE_READ_HOLD') from None


def classify_candidate_names(sources, providers):
    """Match bytes only, and never claim actual symbol resolution.

    Sources are parsed object records; providers are separate exact ELF records.
    Count each unique nonzero referenced undefined dynsym index per requester.
    """
    names={}
    for p in providers:
        for sym in p['symbols']:
            # Only exported defined symbols: global, weak or GNU-unique, and
            # default/protected visibility; this is still not a loader lookup.
            if sym['defined'] and sym['name'] and sym['binding'] in (1,2,10) and sym['visibility'] in (0,3):
                names[sym['name']]=names.get(sym['name'],0)+1
    relations=Counter();undefined=0;defined=0;unique_names=set();versioned=0
    for src in sources:
        if src['metadata'].get(0x6ffffff0) or src['metadata'].get(0x6ffffffe):versioned+=1
        for index in sorted(src['referenced_indices']):
            sym=src['symbols'][index]
            if sym['defined']:
                defined+=1;continue
            undefined+=1
            name=sym['name']
            if not name:
                relations['UNDEFINED_EMPTY_NAME_REVIEW']+=1
                continue
            unique_names.add(name)
            if names.get(name,0)==0:
                relations['NO_STAGED_PROVIDER_NAME_CANDIDATE']+=1
            elif names[name]==1:
                relations['ONE_STAGED_PROVIDER_NAME_CANDIDATE']+=1
            else:
                relations['MULTIPLE_STAGED_PROVIDER_NAME_CANDIDATES']+=1
    return {'referenced_undefined_dynsym_entries':undefined,
            'referenced_defined_or_special_dynsym_entries':defined,
            'distinct_referenced_undefined_symbol_names':len(unique_names),
            'undefined_symbol_candidate_categories':dict(sorted(relations.items())),
            'requesting_objects_with_symbol_versioning_metadata':versioned,
            'provider_export_name_comparison_is_not_symbol_resolution':True}


def audit(root, folder, parent):
    if root.is_symlink() or not root.is_dir():
        raise Hold('ROOTFS_HOLD')
    try:
        p38=parent.load_parent(folder)
        previous=parent.graph_audit(root,folder,p38)
    except parent.Hold:
        raise Hold('R3739_PARENT_REPLAY_HOLD') from None
    if (previous.get('result') != 'STATIC_SONAME_AND_TRANSITIVE_BASENAME_GRAPH_CLASSIFIED_ONLY'
            or previous.get('source_elf_count')!=12
            or previous.get('direct_needed_edges')!=19
            or previous.get('distinct_direct_needed_literals')!=6
            or previous.get('provider_soname_categories') != {'SONAME_EQUALS_REFERENCED_NEEDED_NAME':6}
            or previous.get('provider_needed_basename_candidate_categories') != {'ONE_REGULAR_HEADER_CANDIDATE':7}
            or previous.get('transitive_graph_regular_files_seen')!=6
            or previous.get('provider_graph_cycles',{}).get('cyclic_strong_components')!=0):
        raise Hold('R3739_COUNTS_REPLAY_HOLD')
    p37=p38.load_parent(folder);p36=p37.import_parent(folder);p35=p36.import_parent(folder)
    p34=p35.import_parent(folder);p33=p34.import_r33(folder)
    p26=p33.import_parent(folder/p33.R3726,p33.R3726)
    p27=p33.import_parent(folder/p33.R3727,p33.R3727)
    index,sources,nregular,nlinks=p27.inventory(root,p26)
    if nregular!=1446 or nlinks!=335 or len(sources)!=12 or len({s for s,_ in sources})!=1:
        raise Hold('R3727_INVENTORY_HOLD')
    missing=sources[0][0]
    byteindex={os.fsencode(k):v for k,v in index.items()}
    if len(byteindex)!=len(index):raise Hold('BASENAME_ENCODING_COLLISION_HOLD')
    sourcefiles=[]
    for base,dirs,files in os.walk(root,topdown=True,followlinks=False):
        dirs[:]=sorted(x for x in dirs if not (Path(base)/x).is_symlink())
        for name in sorted(files):
            path=Path(base)/name
            if not stat.S_ISREG(path.lstat().st_mode):continue
            try:
                with p26.open_regular_nofollow(path) as f:parsed=p26.inspect_elf(f)
            except p26.Hold:raise Hold('R3726_ELF_SCAN_HOLD') from None
            if parsed and any(g==missing for g,_ in parsed[1]):sourcefiles.append(path)
    if len(sourcefiles)!=12:raise Hold('SOURCE_COUNT_HOLD')
    provider_set=set()
    for path in sourcefiles:
        needed,hdr=p38.elf_needed_literals(p26,path)
        for needed_name in needed:
            cat,hits=parent.providers_for_needed(root,byteindex,needed_name,hdr,p26)
            if cat != 'ONE_REGULAR_HEADER_CANDIDATE' or len(hits)!=1:
                raise Hold('PROVIDER_SEARCH_CATEGORY_HOLD')
            provider_set.add(hits[0][0])
    if len(provider_set)!=6:raise Hold('PROVIDER_COUNT_HOLD')
    src=[parse_dynamic_and_sections(p26,p) for p in sourcefiles]
    providers=[parse_dynamic_and_sections(p26,p) for p in sorted(provider_set)]
    relations=classify_candidate_names(src,providers)
    if relations['referenced_undefined_dynsym_entries']!=632 or relations['referenced_defined_or_special_dynsym_entries']!=145:
        raise Hold('R3737_REFERENCED_SYMBOL_COUNTS_REPLAY_HOLD')
    meta=Counter()
    for label,items in (('source',src),('provider',providers)):
        for obj in items:
            for tag,yes in obj['metadata'].items():
                if yes:meta[label+'_'+(VERSION_TAGS|PATH_TAGS)[tag]]+=1
    return {'milestone':'R40.4.3.7.40',
            'result':'STAGED_SYMBOL_NAME_CANDIDATES_AND_VERSION_TAGS_STATIC_ONLY',
            'parent_r3739_source_sha_pinned_and_replayed':True,
            'parent_r3738_and_older_source_sha_pins_inherited':True,
            'source_elf_count':len(src),'provider_elf_count':len(providers),
            'source_and_provider_dynamic_metadata_tag_counts':dict(sorted(meta.items())),
            **relations,
            'version_aware_symbol_resolution_verified':False,
            'dynamic_loader_search_and_symbol_interposition_verified':False,
            'tls_relocation_semantics_verified':False,
            'guest_interpreter_path_resolved':False,'mapping_applied':False,
            'full_dependency_closure_proven':False,
            'original_r26_source_provenance_authenticated':False,
            'stage_modified':False,'names_paths_strings_exported':False,
            'boot_authorized':False,'prune_authorized':False,
            'immutable_hold':'NOT_BOOTABLE'}


def main():
    ap=argparse.ArgumentParser(description='R3740 static dynsym name candidates; NOT_BOOTABLE')
    ap.add_argument('--rootfs',type=Path,required=True)
    ap.add_argument('--parent-dir',type=Path,required=True)
    args=ap.parse_args()
    try:
        parent=import_parent(args.parent_dir)
        result=audit(args.rootfs,args.parent_dir,parent)
    except (Hold,OSError,RecursionError) as e:
        result={'milestone':'R40.4.3.7.40','result':'HOLD',
                'hold_category':e.code if isinstance(e,Hold) else 'HOST_IO_OR_GRAPH_HOLD',
                'boot_authorized':False,'prune_authorized':False,
                'immutable_hold':'NOT_BOOTABLE'}
    print(json.dumps(result,sort_keys=True))
    return 0 if result['result']=='STAGED_SYMBOL_NAME_CANDIDATES_AND_VERSION_TAGS_STATIC_ONLY' else 2

if __name__=='__main__':raise SystemExit(main())
