#!/usr/bin/env python3
"""R40.4.3.7.37: bounded ARM relocation type and dynsym index audit.

Read-only source evidence. Never exposes filenames/symbol strings or modifies the
R13 stage. No relocation or symbol resolution, guest execution, boot or pruning.
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

PARENT_NAME = 'R4043736-DYNAMIC-RELOCATION-READONLY.py'
PARENT_SHA256 = '48189e67421d5aaebfa3dfdc1bfd64cd8b383c347d09a0fc58fa8bbdb38fb447'
EXPECTED_PARENT_RESULT = 'DYNAMIC_RELOCATION_TABLES_STATIC_CLASSIFIED_ONLY'
EXPECTED_CANDIDATE_CATEGORY = 'RELOCATION_TABLES_BOUNDED_STATIC_CANDIDATE'
ARM_RELOCATION_CODES_KNOWN = frozenset({
    0, 1, 2, 3, 5, 6, 8, 9, 10, 12, 13, 15, 16, 17, 18, 19,
    20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33,
    38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51,
    52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64,
    65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76,
    77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88,
    89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
    102, 103, 104, 105, 106, 107, 108, 109, 110, 111,
    112, 113, 114, 115, 116, 117, 118, 119, 120, 121,
    122, 123, 124, 125, 126, 127, 128, 129, 130, 131,
})  # Recognition of a number is not evidence of semantics or kernel support.


class Hold(Exception):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


def import_parent(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('PARENT_DIRECTORY_HOLD')
    path = folder / PARENT_NAME
    if path.name != PARENT_NAME or path.is_symlink() or not path.is_file():
        raise Hold('PARENT_FILE_HOLD')
    if hashlib.sha256(path.read_bytes()).hexdigest() != PARENT_SHA256:
        raise Hold('PARENT_SHA256_HOLD')
    spec = importlib.util.spec_from_file_location('pw3_r3736_pin_for_r3737', path)
    if spec is None or spec.loader is None:
        raise Hold('PARENT_IMPORT_HOLD')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_arm_relocation_symbol_metadata(p26, fileobj, p36):
    """Read bounded ELF32 ARM REL/RELA/PLT r_info and *fixed-size* dynsym entries.

    Dynamic symbol names, needed libraries and source paths are not read. A
    symbol entry at a mapped file address is not proof of symbol resolution.
    """
    previous = p36.read_dynamic_relocations(p26, fileobj)
    if previous['category'] not in ('RELOCATION_TABLES_BOUNDED_STATIC_CANDIDATE',
                                    'DYNAMIC_PRESENT_NO_RELOCATIONS','NO_PT_DYNAMIC'):
        raise Hold('PARENT_RELOCATION_CATEGORY_HOLD')
    h = p26.elf_header(fileobj)
    if h is None or h['cls'] != 1 or h['machine'] != 40 or h['phsize'] < 32:
        raise Hold('INVALID_ELF32_ARM_HEADER_HOLD')
    loads, dynamics = [], []
    for i in range(h['phnum']):
        raw = p26.read_at(fileobj, h['phoff'] + i*h['phsize'], h['phsize'])
        typ, off, vaddr, _, filesz, memsz, _, _ = struct.unpack_from(h['endian']+'IIIIIIII', raw)
        if typ not in (1,2):
            continue
        if off > h['length'] or filesz > h['length']-off or filesz > memsz or vaddr+memsz > 0x100000000:
            raise Hold('SEGMENT_BOUNDS_HOLD')
        if typ == 1:
            loads.append((vaddr, off, filesz))
        else:
            dynamics.append((off, filesz))
    if len(dynamics) > 1 or not loads:
        raise Hold('PT_DYNAMIC_OR_LOAD_COUNT_HOLD')
    tags = {}
    if dynamics:
        off,size = dynamics[0]
        if not size or size > 65536 or size % 8:
            raise Hold('DYNAMIC_SIZE_HOLD')
        ended = False
        for i in range(size//8):
            tag,value = struct.unpack(h['endian']+'II', p26.read_at(fileobj, off+i*8, 8))
            if tag == 0:
                ended = True
                break
            if tag in (2,5,6,7,8,9,10,11,17,18,19,20,23) and tag in tags:
                raise Hold('REPEATED_DYNAMIC_DESCRIPTOR_HOLD')
            if tag in (2,5,6,7,8,9,10,11,17,18,19,20,23):
                tags[tag] = value
        if not ended:
            raise Hold('DYNAMIC_TERMINATOR_HOLD')

    def file_offset(vaddr, width):
        mapped = {off + vaddr-start for start,off,length in loads
                  if start <= vaddr and vaddr-start <= length and width <= length-(vaddr-start)}
        return next(iter(mapped)) if len(mapped) == 1 else None

    tables = []
    def add_table(name, ptrtag, sizetag, enttag, width):
        present = [t in tags for t in (ptrtag,sizetag,enttag)]
        if not any(present):
            return
        if not all(present) or tags[enttag] != width:
            raise Hold('RELOCATION_DESCRIPTOR_HOLD')
        size = tags[sizetag]
        if size > 262144 or size % width:
            raise Hold('RELOCATION_SIZE_HOLD')
        if size:
            off = file_offset(tags[ptrtag],size)
            if off is None:
                raise Hold('RELOCATION_TABLE_MAPPING_HOLD')
            tables.append((name,off,size//width,width))

    add_table('rel',17,18,19,8)
    add_table('rela',7,8,9,12)
    if any(k in tags for k in (23,2,20)):
        if not all(k in tags for k in (23,2,20)) or tags[20] not in (17,7):
            raise Hold('PLT_RELOCATION_DESCRIPTOR_HOLD')
        width = 8 if tags[20] == 17 else 12
        size = tags[2]
        if size > 262144 or size % width:
            raise Hold('PLT_RELOCATION_SIZE_HOLD')
        if size:
            off = file_offset(tags[23],size)
            if off is None:
                raise Hold('PLT_RELOCATION_MAPPING_HOLD')
            tables.append(('plt',off,size//width,width))
    table_counts = {name: sum(count for group,_,count,_ in tables if group == name)
                    for name in ('rel','rela','plt')}
    if (table_counts['rel'] != previous['rel_entries']
            or table_counts['rela'] != previous['rela_entries']
            or table_counts['plt'] != previous['plt_entries']):
        raise Hold('PARENT_RELOCATION_COUNT_REPLAY_HOLD')
    types=Counter(); unique_indices=set(); counters=Counter()
    for group,off,n,width in tables:
        for i in range(n):
            rec=p26.read_at(fileobj,off+i*width,width)
            _target,info=struct.unpack_from(h['endian']+'II',rec)
            reloc_type=info & 0xff
            index=info >> 8
            types[reloc_type]+=1
            unique_indices.add(index)
            counters['symbol_index_zero' if index == 0 else 'symbol_index_nonzero']+=1
            if group == 'plt':
                counters['plt_entries']+=1
            if reloc_type not in ARM_RELOCATION_CODES_KNOWN:
                counters['unrecognized_relocation_code_entries']+=1
            if reloc_type == 23 and index != 0:
                # AAELF32 explicitly permits R_ARM_RELATIVE with nonzero S.
                counters['arm_relative_with_nonzero_symbol_index']+=1
    if len(types) != previous['distinct_relocation_type_count']:
        raise Hold('PARENT_DISTINCT_TYPE_COUNT_REPLAY_HOLD')
    if len(unique_indices) > 65536:
        raise Hold('EXCESSIVE_UNIQUE_SYMBOL_INDICES_HOLD')

    symbol_refs={i for i in unique_indices if i != 0}
    if symbol_refs and (6 not in tags or 11 not in tags or tags[11] != 16):
        counters['files_with_missing_or_invalid_symtab_descriptors']+=1
    elif symbol_refs:
        for index in sorted(symbol_refs):
            # No names are read; st_info and st_shndx are used only as aggregate evidence.
            addr = tags[6]+index*16
            if addr >= 0x100000000 or addr+16 > 0x100000000:
                counters['dynsym_entries_not_filebacked']+=1
                continue
            entry_off = file_offset(addr,16)
            if entry_off is None:
                counters['dynsym_entries_not_filebacked']+=1
                continue
            raw=p26.read_at(fileobj,entry_off,16)
            info = raw[12]
            section, = struct.unpack_from(h['endian']+'H',raw,14)
            counters['dynsym_entries_filebacked']+=1
            counters['dynsym_undefined' if section == 0 else 'dynsym_defined_or_special']+=1
            counters['dynsym_weak' if (info >> 4) == 2 else 'dynsym_nonweak']+=1
    counters['unique_nonzero_symbol_indices'] = len(symbol_refs)
    counters['relocation_entries_total'] = sum(table_counts.values())
    category=('RELOCATION_TYPES_WITH_DYNSYM_INDEX_REVIEW_HOLD'
              if (counters['unrecognized_relocation_code_entries']
                  or counters['dynsym_entries_not_filebacked']
                  or counters['files_with_missing_or_invalid_symtab_descriptors'])
              else 'RELOCATION_TYPES_AND_DYNSYM_INDICES_STATIC_CANDIDATE')
    return {'category':category,
            'arm_relocation_type_counts':{str(k):v for k,v in sorted(types.items())},
            'symbol_index_and_dynsym_counts':dict(sorted(counters.items())),
            'dynsym_index_count_is_bound_not_symbol_resolution':True,
            'dt_needed_count':previous['dt_needed_count']}


def audit(root, folder, parent):
    if root.is_symlink() or not root.is_dir():
        raise Hold('ROOTFS_INVALID_HOLD')
    p35 = parent.import_parent(folder)
    replay = parent.audit(root,folder,p35)
    if (replay.get('result') != EXPECTED_PARENT_RESULT
          or replay.get('candidate_relocation_metadata',{}).get('category') != EXPECTED_CANDIDATE_CATEGORY
          or replay.get('candidate_relocation_metadata',{}).get('relocation_targets_outside_load') != 0
          or replay.get('requesting_elf_count') != 12
          or replay.get('requesting_elf_relocation_categories') != {EXPECTED_CANDIDATE_CATEGORY:12}
          or replay.get('requesting_elf_relocation_totals',{}).get('relocation_targets_outside_load') != 0
          or replay.get('stage_modified') is not False):
        raise Hold('R3736_REPLAY_HOLD')
    r34 = p35.import_parent(folder)
    r33 = r34.import_r33(folder)
    p26 = r33.import_parent(folder/r33.R3726,r33.R3726)
    p27 = r33.import_parent(folder/r33.R3727,r33.R3727)
    index,sources,nfiles,nlinks = p27.inventory(root,p26)
    if len(sources) != 12 or nfiles != 1446 or nlinks != 335 or len({x for x,_ in sources}) != 1:
        raise Hold('R3727_SOURCE_INVENTORY_HOLD')
    absent=sources[0][0]
    basename=absent.rsplit('/',1)[-1]
    candidates=set()
    for literal,header in sources:
        if literal != absent:
            raise Hold('SOURCES_DIFFER_HOLD')
        matches = [item for item,kind in index.get(basename,()) if kind == 'regular'
                   and p26.classify_guest_target(root,r33.relative_guest_path(root,item),header)[0]
                   == 'GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE']
        if len(matches) != 1:
            raise Hold('CANDIDATE_AMBIGUOUS_HOLD')
        candidates.add(matches[0])
    if len(candidates) != 1:
        raise Hold('CANDIDATE_IDENTITY_HOLD')
    r34.absent_leaf(root,absent)
    with p26.open_regular_nofollow(next(iter(candidates))) as f:
        candidate=read_arm_relocation_symbol_metadata(p26,f,parent)
    source_types=Counter(); source_stats=Counter(); source_categories=Counter(); n=0
    def onerror(_):
        raise Hold('STAGE_WALK_HOLD')
    for base,dirs,files in os.walk(root,topdown=True,followlinks=False,onerror=onerror):
        dirs[:]=sorted(x for x in dirs if not (Path(base)/x).is_symlink())
        for name in sorted(files):
            path=Path(base)/name
            if not stat.S_ISREG(path.lstat().st_mode):
                continue
            with p26.open_regular_nofollow(path) as f:
                parsed=p26.inspect_elf(f)
            if parsed is None or not any(lit == absent for lit,_ in parsed[1]):
                continue
            n+=1
            try:
                with p26.open_regular_nofollow(path) as f:
                    result=read_arm_relocation_symbol_metadata(p26,f,parent)
                source_categories[result['category']]+=1
                source_stats.update(result['symbol_index_and_dynsym_counts'])
                for label,count in result['arm_relocation_type_counts'].items():
                    source_types[label]+=count
            except (Hold,p26.Hold):
                source_categories['PER_ELF_RELOCATION_SYMBOL_READ_HOLD']+=1
    if n != 12:
        raise Hold('REQUESTING_ELF_COUNT_HOLD')
    return {
        'milestone':'R40.4.3.7.37',
        'result':'ARM_RELOCATION_TYPES_AND_SYMBOL_INDICES_STATIC_CLASSIFIED_ONLY',
        'parent_r3736_source_sha_pinned_and_replayed':True,
        'parent_r3735_and_earlier_source_sha_pins_inherited':True,
        'candidate':candidate,
        'requesting_elf_count':n,
        'requesting_elf_categories':dict(sorted(source_categories.items())),
        'requesting_arm_relocation_type_counts':dict(sorted(source_types.items(),key=lambda pair:int(pair[0]))),
        'requesting_symbol_index_and_dynsym_counts':dict(sorted(source_stats.items())),
        'symbols_resolved':False,
        'relocations_applied':False,
        'guest_interpreter_path_resolved':False,
        'mapping_applied':False,
        'kernel_runtime_loader_verified':False,
        'transitive_dependency_closure_proven':False,
        'original_r26_source_provenance_authenticated':False,
        'historical_inventory_hashes_reverified':False,
        'paths_or_symbol_names_exported':False,
        'stage_modified':False,
        'boot_authorized':False,
        'prune_authorized':False,
        'immutable_hold':'NOT_BOOTABLE',
    }


def main():
    p=argparse.ArgumentParser(description='Read-only ARM relocation type/dynsym audit; NOT_BOOTABLE')
    p.add_argument('--rootfs',type=Path,required=True)
    p.add_argument('--parent-dir',type=Path,required=True)
    args=p.parse_args()
    try:
        parent=import_parent(args.parent_dir)
        result=audit(args.rootfs,args.parent_dir,parent)
    except (Hold,OSError) as exc:
        result={'milestone':'R40.4.3.7.37','result':'HOLD',
                'hold_category':exc.category if isinstance(exc,Hold) else 'HOST_IO_HOLD',
                'boot_authorized':False,'prune_authorized':False,
                'immutable_hold':'NOT_BOOTABLE'}
    print(json.dumps(result,sort_keys=True))
    return 0 if result['result']=='ARM_RELOCATION_TYPES_AND_SYMBOL_INDICES_STATIC_CLASSIFIED_ONLY' else 2


if __name__=='__main__':
    raise SystemExit(main())
