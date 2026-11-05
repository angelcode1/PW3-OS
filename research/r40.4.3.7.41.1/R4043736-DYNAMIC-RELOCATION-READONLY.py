#!/usr/bin/env python3
"""R40.4.3.7.36: bounded, read-only PT_DYNAMIC relocation-table preflight.

Pins R3735 and its unchanged lineage. Does not execute ELFs or write the stage.
Never emits file paths, symbol names, library names or dynamic string contents.
NOT_BOOTABLE; no image mapping, firmware, boot or pruning authorization.
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

PARENT_NAME = 'R4043735-PT-LOAD-PREFLIGHT-READONLY.py'
PARENT_SHA = '59c5154cdc63d44e0cc0ef51bff820715be6b2d5a9fe8a40b2cd50216ae83d4d'

class Hold(Exception):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


def import_parent(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('PARENT_DIRECTORY_HOLD')
    path = folder / PARENT_NAME
    if path.is_symlink() or not path.is_file():
        raise Hold('PARENT_R3735_FILE_HOLD')
    if hashlib.sha256(path.read_bytes()).hexdigest() != PARENT_SHA:
        raise Hold('PARENT_R3735_SHA_HOLD')
    spec = importlib.util.spec_from_file_location('pw3_r3735_pinned_r3736', path)
    if not spec or not spec.loader:
        raise Hold('PARENT_R3735_IMPORT_HOLD')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_dynamic_relocations(p26, f):
    """Validate ELF32 ARM relocation table descriptors and file-backed ranges.

    Header-level mapping only: no symbol resolution, relocations applied,
    code execution, instruction decoding or loader kernel compatibility.
    """
    h = p26.elf_header(f)
    if h is None or h['cls'] != 1 or h['machine'] != 40 or h['phsize'] < 32:
        raise Hold('ELF32_ARM_HEADER_HOLD')
    loads = []
    dynamics = []
    for i in range(h['phnum']):
        ph = p26.read_at(f, h['phoff'] + i*h['phsize'], h['phsize'])
        kind, off, vaddr, _paddr, filesz, memsz, _flags, _align = struct.unpack_from(h['endian']+'IIIIIIII', ph)
        if kind not in (1, 2):
            continue
        if off > h['length'] or filesz > h['length'] - off or filesz > memsz or vaddr+memsz > 0x100000000:
            raise Hold('SEGMENT_BOUNDS_HOLD')
        if kind == 1:
            loads.append((vaddr, filesz, off, memsz))
        else:
            dynamics.append((off, filesz))
    if not loads:
        raise Hold('NO_LOADABLE_SEGMENTS_HOLD')
    if len(dynamics) > 1:
        raise Hold('MULTIPLE_DYNAMIC_SEGMENTS_HOLD')
    if not dynamics:
        return {'category':'NO_PT_DYNAMIC', 'dt_needed_count':0, 'rel_entries':0,
                'rela_entries':0,'plt_entries':0,'relocation_targets_outside_load':0,
                'distinct_relocation_type_count':0}

    dynoff, dynsz = dynamics[0]
    if dynsz == 0 or dynsz > 65536 or dynsz % 8:
        raise Hold('DYNAMIC_LENGTH_HOLD')
    if not any(o <= dynoff and dynsz <= size-(dynoff-o) for _,size,o,_ in loads if o <= dynoff):
        raise Hold('DYNAMIC_NOT_FILEBACKED_HOLD')
    tags = {}
    needed = 0
    terminated = False
    for i in range(dynsz // 8):
        tag, val = struct.unpack(h['endian']+'II', p26.read_at(f,dynoff+i*8,8))
        if tag == 0:
            terminated = True
            break
        if tag == 1:  # DT_NEEDED is a repeatable name offset, never read the name
            needed += 1
            continue
        if tag in (2, 5, 7, 8, 9, 10, 11, 17, 18, 19, 20, 23):
            if tag in tags:
                raise Hold('DUPLICATE_RELOCATION_TAG_HOLD')
            tags[tag] = val
    if not terminated:
        raise Hold('DYNAMIC_NOT_TERMINATED_HOLD')

    def table(ptrtag, sizetag, enttag, entrywidth, label):
        present = [tag in tags for tag in (ptrtag, sizetag, enttag)]
        if not any(present):
            return 0, []
        if not all(present) or tags[enttag] != entrywidth:
            raise Hold(label+'_DESCRIPTORS_HOLD')
        addr, size = tags[ptrtag], tags[sizetag]
        if size > 262144 or size % entrywidth:
            raise Hold(label+'_SIZE_HOLD')
        if size == 0:
            return 0, []
        mappings = [(off+addr-vaddr) for vaddr,filesz,off,_ in loads
                    if vaddr <= addr and addr-vaddr <= filesz and size <= filesz-(addr-vaddr)]
        if len(set(mappings)) != 1 or not mappings:
            raise Hold(label+'_FILE_MAPPING_HOLD')
        return size//entrywidth, [(mappings[0], size, entrywidth)]

    nrel, reltab = table(17, 18, 19, 8, 'DT_REL')
    nrela, relatab = table(7, 8, 9, 12, 'DT_RELA')
    plttab=[]; nplt=0
    plt_present = [tag in tags for tag in (23,2,20)]
    if any(plt_present):
        if not all(plt_present) or tags[20] not in (17,7):
            raise Hold('DT_JMPREL_DESCRIPTORS_HOLD')
        ent = 8 if tags[20] == 17 else 12
        size = tags[2]
        if size > 262144 or size % ent:
            raise Hold('DT_JMPREL_SIZE_HOLD')
        if size:
            addr = tags[23]
            mappings=[off+addr-vaddr for vaddr,filesz,off,_ in loads
                      if vaddr <= addr and addr-vaddr <= filesz and size <= filesz-(addr-vaddr)]
            if len(set(mappings)) != 1 or not mappings:
                raise Hold('DT_JMPREL_FILE_MAPPING_HOLD')
            plttab=[(mappings[0],size,ent)]
            nplt=size//ent

    # Relocation targets need only be mapped in PT_LOAD memory, not file-backed.
    # Do not assess machine relocation semantics or symbol lookup.
    distinct_types=set()
    outside=0
    for off, size, width in reltab+relatab+plttab:
        for i in range(size//width):
            rec=p26.read_at(f,off+i*width,width)
            target, info=struct.unpack_from(h['endian']+'II',rec)
            distinct_types.add(info & 0xff)
            if not any(vaddr <= target < vaddr+memsz for vaddr,_filesz,_off,memsz in loads):
                outside+=1
    if outside:
        category='RELOCATION_TARGET_OUTSIDE_PT_LOAD_REVIEW_HOLD'
    elif nrel+nrela+nplt:
        category='RELOCATION_TABLES_BOUNDED_STATIC_CANDIDATE'
    else:
        category='DYNAMIC_PRESENT_NO_RELOCATIONS'
    return {'category':category,'dt_needed_count':needed,'rel_entries':nrel,
            'rela_entries':nrela,'plt_entries':nplt,
            'relocation_targets_outside_load':outside,
            'distinct_relocation_type_count':len(distinct_types)}


def audit(root, folder, parent):
    if root.is_symlink() or not root.is_dir():
        raise Hold('ROOTFS_INVALID_HOLD')
    # Mandatory full replay of previous read-only result and hold statuses.
    p34=parent.import_parent(folder)
    previous=parent.audit(root, folder, p34)
    if (previous.get('result')!='ELF_PT_LOAD_STATIC_CONSTRAINTS_CLASSIFIED_ONLY'
        or previous.get('candidate_structure_category')!='STATIC_LOAD_SEGMENT_CONSTRAINTS_CANDIDATE'
        or previous.get('requesting_elf_count')!=12
        or previous.get('requesting_elf_structural_categories')!={'STATIC_LOAD_SEGMENT_CONSTRAINTS_CANDIDATE':12}
        or previous.get('stage_modified') is not False):
        raise Hold('R3735_BASELINE_HOLD')
    r33=p34.import_r33(folder)
    p26=r33.import_parent(folder/r33.R3726,r33.R3726)
    p27=r33.import_parent(folder/r33.R3727,r33.R3727)
    idx,sources,nreg,nlinks=p27.inventory(root,p26)
    if len(sources)!=12 or nreg!=1446 or nlinks!=335 or len({x for x,_ in sources})!=1:
        raise Hold('INDEPENDENT_BASELINE_HOLD')
    missing=sources[0][0]
    basename=missing.rsplit('/',1)[-1]
    candidates=set()
    for literal,hdr in sources:
        if literal!=missing:
            raise Hold('MISSING_PATH_DIFFERENT_HOLD')
        matched=[path for path,kind in idx.get(basename,()) if kind=='regular'
                 and p26.classify_guest_target(root,r33.relative_guest_path(root,path),hdr)[0]
                 =='GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE']
        if len(matched)!=1:
            raise Hold('CANDIDATE_NOT_UNIQUE_HOLD')
        candidates.add(matched[0])
    if len(candidates)!=1:
        raise Hold('CANDIDATES_DIFFER_HOLD')
    p34.absent_leaf(root,missing)
    with p26.open_regular_nofollow(next(iter(candidates))) as f:
        candidate = read_dynamic_relocations(p26,f)
    counts=Counter(); totals=Counter(); scanned=0
    def onerror(_):
        raise Hold('STAGE_WALK_HOLD')
    for base,dirs,files in os.walk(root,topdown=True,followlinks=False,onerror=onerror):
        dirs[:]=sorted(d for d in dirs if not (Path(base)/d).is_symlink())
        for name in sorted(files):
            path=Path(base)/name
            if not stat.S_ISREG(path.lstat().st_mode):
                continue
            with p26.open_regular_nofollow(path) as f:
                parsed=p26.inspect_elf(f)
            if parsed is None or not any(lit==missing for lit,_ in parsed[1]):
                continue
            scanned+=1
            with p26.open_regular_nofollow(path) as f:
                try:
                    entry=read_dynamic_relocations(p26,f)
                except (Hold,p26.Hold):
                    counts['DYNAMIC_METADATA_HOLD']+=1
                    continue
            counts[entry['category']]+=1
            for k in ('dt_needed_count','rel_entries','rela_entries','plt_entries','relocation_targets_outside_load'):
                totals[k]+=entry[k]
    if scanned!=12:
        raise Hold('REQUESTING_ELF_COUNT_HOLD')
    return {
        'milestone':'R40.4.3.7.36',
        'result':'DYNAMIC_RELOCATION_TABLES_STATIC_CLASSIFIED_ONLY',
        'parent_r3735_sha_pinned_and_replayed':True,
        'parent_r3734_and_prior_sha_pins_inherited':True,
        'candidate_relocation_metadata':candidate,
        'requesting_elf_count':scanned,
        'requesting_elf_relocation_categories':dict(sorted(counts.items())),
        'requesting_elf_relocation_totals':dict(sorted(totals.items())),
        'guest_interpreter_path_resolved':False,
        'future_image_mapping_applied':False,
        'kernel_runtime_loader_verified':False,
        'relocations_applied':False,
        'full_abi_or_dependency_closure_proven':False,
        'original_r26_source_provenance_authenticated':False,
        'historical_inventory_hashes_reverified':False,
        'paths_and_symbols_exported':False,
        'stage_modified':False,
        'boot_authorized':False,'prune_authorized':False,
        'immutable_hold':'NOT_BOOTABLE'
    }


def main():
    ap=argparse.ArgumentParser(description='Read-only dynamic relocation descriptor preflight; NOT_BOOTABLE')
    ap.add_argument('--rootfs',type=Path,required=True)
    ap.add_argument('--parent-dir',type=Path,required=True)
    a=ap.parse_args()
    try:
        parent=import_parent(a.parent_dir)
        result=audit(a.rootfs,a.parent_dir,parent)
    except (Hold,OSError) as exc:
        result={'milestone':'R40.4.3.7.36','result':'HOLD',
                'hold_category':exc.category if isinstance(exc,Hold) else 'HOST_IO_HOLD',
                'boot_authorized':False,'prune_authorized':False,'immutable_hold':'NOT_BOOTABLE'}
    print(json.dumps(result,sort_keys=True))
    return 0 if result['result']=='DYNAMIC_RELOCATION_TABLES_STATIC_CLASSIFIED_ONLY' else 2

if __name__=='__main__':
    raise SystemExit(main())
