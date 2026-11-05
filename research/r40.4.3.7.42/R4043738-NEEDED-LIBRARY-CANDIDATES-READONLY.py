#!/usr/bin/env python3
"""R40.4.3.7.38: static DT_NEEDED basename candidates for 12 ELF requesters.

Read-only research; inherits exact SHA-pinned R3737 parent chain and baseline.
Reads DT_NEEDED names in memory only. NEVER exports paths, libraries, symbols or
source bytes. Does not run linkers, apply relocations, build images or create links.
NOT_BOOTABLE.
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

PARENT_NAME = 'R4043737-ARM-RELOCATION-SYMBOL-READONLY.py'
PARENT_SHA = '27ac20c24670424623ecc8f6bd52e80b6b5835935a403d62548c734b11104c77'
EXPECTED_TYPES = {'2':14,'17':5,'18':1,'19':32,'21':218,'22':575,'23':2654}
EXPECTED_SOURCE_CATEGORY = {'RELOCATION_TYPES_AND_DYNSYM_INDICES_STATIC_CANDIDATE':12}

class Hold(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def load_parent(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('PARENT_DIRECTORY_HOLD')
    path = folder / PARENT_NAME
    if path.is_symlink() or not path.is_file():
        raise Hold('PARENT_SOURCE_FILE_HOLD')
    if hashlib.sha256(path.read_bytes()).hexdigest() != PARENT_SHA:
        raise Hold('PARENT_SOURCE_SHA256_HOLD')
    spec = importlib.util.spec_from_file_location('pw3_r3737_pinned_for_r3738', path)
    if not spec or not spec.loader:
        raise Hold('PARENT_IMPORT_HOLD')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def elf_needed_literals(p26, path):
    """Return (byte-string DT_NEEDED literals, ELF header), strictly file-backed.

    Names are never included in the public result. A name-only candidate from
    DT_NEEDED does not establish dynamic loader search or provider suitability.
    """
    try:
        with p26.open_regular_nofollow(path) as f:
            h = p26.elf_header(f)
            if h is None or h['cls'] != 1 or h['machine'] != 40 or h['phsize'] < 32:
                raise Hold('SOURCE_NOT_ELF32_ARM_HOLD')
            loads, dynamics = [], []
            for i in range(h['phnum']):
                rec = p26.read_at(f,h['phoff']+i*h['phsize'],h['phsize'])
                kind,off,vaddr,_,size,memsz,_,_ = struct.unpack_from(h['endian']+'IIIIIIII',rec)
                if kind not in (1,2):
                    continue
                if off > h['length'] or size > h['length']-off or size > memsz or vaddr+memsz > 2**32:
                    raise Hold('SOURCE_SEGMENT_BOUNDS_HOLD')
                if kind == 1:
                    loads.append((vaddr,off,size))
                else:
                    dynamics.append((off,size))
            if not loads or len(dynamics) > 1:
                raise Hold('SOURCE_LOAD_DYNAMIC_COUNT_HOLD')
            if not dynamics:
                return [],h
            start,size=dynamics[0]
            if size == 0 or size > 65536 or size % 8:
                raise Hold('SOURCE_DYNAMIC_LENGTH_HOLD')
            dt_needed=[]; strtab=[]; strsz=[]; terminated=False
            for i in range(size//8):
                tag,value=struct.unpack(h['endian']+'II',p26.read_at(f,start+i*8,8))
                if tag == 0:
                    terminated=True;break
                if tag == 1:
                    dt_needed.append(value)
                elif tag == 5:
                    strtab.append(value)
                elif tag == 10:
                    strsz.append(value)
            if not terminated:
                raise Hold('SOURCE_DYNAMIC_TERMINATOR_HOLD')
            if not dt_needed:
                return [],h
            if len(strtab) != 1 or len(strsz) != 1:
                raise Hold('SOURCE_DYNAMIC_STRTAB_DESCRIPTORS_HOLD')
            addr,length=strtab[0],strsz[0]
            if not length or length > 2**20 or addr+length > 2**32:
                raise Hold('SOURCE_DYNAMIC_STRTAB_SIZE_HOLD')
            matches={off+addr-vaddr for vaddr,off,sz in loads
                     if vaddr <= addr and addr-vaddr <= sz and length <= sz-(addr-vaddr)}
            if len(matches) != 1:
                raise Hold('SOURCE_DYNAMIC_STRTAB_MAPPING_HOLD')
            table=p26.read_at(f,next(iter(matches)),length)
            literals=[]
            for offset in dt_needed:
                if offset >= length:
                    raise Hold('NEEDED_STRING_OFFSET_HOLD')
                nul=table.find(b'\x00',offset)
                if nul < 0:
                    raise Hold('NEEDED_STRING_NOT_TERMINATED_HOLD')
                name=table[offset:nul]
                if not name or len(name) > 4096:
                    raise Hold('NEEDED_NAME_EMPTY_OR_LONG_HOLD')
                literals.append(name)
            return literals,h
    except p26.Hold:
        raise Hold('SOURCE_IO_OR_ELF_PARSE_HOLD') from None


def category_for_needed(root, index, name, source_hdr, p26):
    """Use only basename comparisons; never claim guest runtime resolution."""
    if b'/' in name or b'\\' in name:
        return 'PATH_BEARING_NEEDED_LITERAL_REVIEW_HOLD',0,0
    if name in (b'.',b'..'):
        return 'INVALID_NEEDED_BASENAME_HOLD',0,0
    entries = index.get(name, ())
    regular=0; symlink=0
    for candidate, typ in entries:
        guest='/' + candidate.relative_to(root).as_posix()
        try:
            classification,_=p26.classify_guest_target(root,guest,source_hdr)
        except p26.Hold:
            raise Hold('GUEST_CANDIDATE_CLASSIFICATION_HOLD') from None
        if classification == 'GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE':
            if typ=='regular': regular+=1
            elif typ=='link': symlink+=1
    total=regular+symlink
    if total > 1: return 'MULTIPLE_ABI_HEADER_BASENAME_CANDIDATES',regular,symlink
    if regular == 1: return 'ONE_REGULAR_ABI_HEADER_BASENAME_CANDIDATE',regular,symlink
    if symlink == 1: return 'ONE_SYMLINK_ABI_HEADER_BASENAME_CANDIDATE',regular,symlink
    if entries: return 'BASENAME_ENTRIES_BUT_NO_ABI_HEADER_CANDIDATE',regular,symlink
    return 'NO_BASENAME_ENTRY_IN_STAGE',regular,symlink


def audit(root, folder, parent37):
    if root.is_symlink() or not root.is_dir():
        raise Hold('ROOTFS_INVALID_HOLD')
    try:
        previous=parent37.audit(root,folder,parent37.import_parent(folder))
    except parent37.Hold:
        raise Hold('R3737_REPLAY_HOLD') from None
    if (previous.get('result') != 'ARM_RELOCATION_TYPES_AND_SYMBOL_INDICES_STATIC_CLASSIFIED_ONLY'
            or previous.get('requesting_elf_count') != 12
            or previous.get('requesting_elf_categories') != EXPECTED_SOURCE_CATEGORY
            or previous.get('requesting_arm_relocation_type_counts') != EXPECTED_TYPES
            or previous.get('candidate',{}).get('arm_relocation_type_counts') != {'21':4,'22':6,'23':17}
            or previous.get('candidate',{}).get('dt_needed_count') != 0
            or previous.get('requesting_symbol_index_and_dynsym_counts',{}).get('dynsym_undefined') != 632
            or previous.get('stage_modified') is not False):
        raise Hold('R3737_COUNTS_AND_TYPES_REPLAY_HOLD')
    p36=parent37.import_parent(folder)
    p35=p36.import_parent(folder)
    p34=p35.import_parent(folder)
    p33=p34.import_r33(folder)
    p26=p33.import_parent(folder/p33.R3726,p33.R3726)
    p27=p33.import_parent(folder/p33.R3727,p33.R3727)
    try:
        index, sources, nfiles, nlinks=p27.inventory(root,p26)
    except p27.Hold:
        raise Hold('R3727_INVENTORY_HOLD') from None
    if nfiles != 1446 or nlinks != 335 or len(sources) != 12 or len({x for x,_ in sources}) != 1:
        raise Hold('SOURCE_INVENTORY_HOLD')
    absent=sources[0][0]
    byte_index={}
    for basename,entries in index.items():
        b=os.fsencode(basename)
        if b in byte_index:
            raise Hold('BASENAME_ENCODING_COLLISION_HOLD')
        byte_index[b]=entries
    counts=Counter(); total=0; source_count=0; unique_names=set(); per_source=Counter()
    compatible_regular_edges=0;compatible_symlink_edges=0
    # Inspect each physical source once, without following any stage symlinks.
    def onerror(_):
        raise Hold('ROOTFS_WALK_ERROR_HOLD')
    for base, dirs, files in os.walk(root,topdown=True,followlinks=False,onerror=onerror):
        dirs[:]=sorted(x for x in dirs if not (Path(base)/x).is_symlink())
        for name in sorted(files):
            path=Path(base)/name
            try: mode=path.lstat().st_mode
            except OSError:raise Hold('ROOTFS_FILE_LSTAT_HOLD') from None
            if not stat.S_ISREG(mode):continue
            try:
                with p26.open_regular_nofollow(path) as f:
                    parsed=p26.inspect_elf(f)
            except p26.Hold:
                raise Hold('R3726_SCAN_HOLD') from None
            if parsed is None or not any(lit==absent for lit,_ in parsed[1]):
                continue
            names,hdr=elf_needed_literals(p26,path)
            source_count+=1;per_source[str(len(names))]+=1
            for needed in names:
                total+=1;unique_names.add(needed)
                classification,regular,symlink=category_for_needed(root,byte_index,needed,hdr,p26)
                counts[classification]+=1
                compatible_regular_edges+=regular
                compatible_symlink_edges+=symlink
    if source_count != 12 or total != 19:
        raise Hold('R3737_NEEDED_TOTAL_REPLAY_HOLD')
    return {
        'milestone':'R40.4.3.7.38',
        'result':'REQUESTER_NEEDED_BASENAME_STATIC_CANDIDATES_ONLY',
        'parent_r3737_sha256_verified_and_replayed':True,
        'parent_r3736_and_older_source_sha_pins_inherited':True,
        'source_elf_count':source_count,
        'dt_needed_entries':total,
        'distinct_dt_needed_name_literals':len(unique_names),
        'per_source_dt_needed_entry_count_histogram':dict(sorted(per_source.items(),key=lambda x:int(x[0]))),
        'dt_needed_same_basename_candidate_categories':dict(sorted(counts.items())),
        'compatible_regular_entry_matches_across_needed_edges':compatible_regular_edges,
        'compatible_symlink_entry_matches_across_needed_edges':compatible_symlink_edges,
        'arm_tls_relocation_counts_from_parent':{k:EXPECTED_TYPES[k] for k in ('17','18','19')},
        'dynamic_symbol_names_or_library_names_exported':False,
        'file_basename_is_not_dynamic_loader_resolution':True,
        'needed_library_runtime_resolution_verified':False,
        'tls_runtime_compatibility_verified':False,
        'full_dependency_closure_proven':False,
        'guest_interpreter_path_resolved':False,
        'future_image_mapping_applied':False,
        'source_provenance_authenticated':False,
        'historical_hashes_reverified':False,
        'stage_modified':False,
        'firmware_write_authorized':False,
        'boot_authorized':False,
        'prune_authorized':False,
        'immutable_hold':'NOT_BOOTABLE',
    }


def main():
    parser=argparse.ArgumentParser(description='Read-only DT_NEEDED basename candidate inventory; NOT_BOOTABLE')
    parser.add_argument('--rootfs',required=True,type=Path)
    parser.add_argument('--parent-dir',required=True,type=Path)
    args=parser.parse_args()
    try:
        parent=load_parent(args.parent_dir)
        result=audit(args.rootfs,args.parent_dir,parent)
    except (Hold,OSError) as exc:
        result={'milestone':'R40.4.3.7.38','result':'HOLD',
                'hold_category':exc.code if isinstance(exc,Hold) else 'HOST_IO_HOLD',
                'boot_authorized':False,'prune_authorized':False,
                'immutable_hold':'NOT_BOOTABLE'}
    print(json.dumps(result,sort_keys=True))
    return 0 if result['result']=='REQUESTER_NEEDED_BASENAME_STATIC_CANDIDATES_ONLY' else 2

if __name__=='__main__':
    raise SystemExit(main())
