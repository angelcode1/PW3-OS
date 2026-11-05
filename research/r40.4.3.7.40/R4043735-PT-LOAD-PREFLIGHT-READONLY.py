#!/usr/bin/env python3
"""R4043735: static ELF PT_LOAD constraints for prospective guest interpreter.

RESEARCH ONLY. Read-only stage and pinned R3734 parent; no execution, no alias,
no boot, no pruning. Results are aggregate; no pathname or ELF strings output.
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

PARENT_NAME = 'R4043734-FUTURE-MAPPING-SIMULATION-READONLY.py'
PARENT_SHA = '3187922ba12b662081c2e8a0324b5d1df90ff1c4d62969444f7d557c4402bf66'

class Hold(Exception):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


def import_parent(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('PARENT_DIRECTORY_HOLD')
    path = folder / PARENT_NAME
    if path.is_symlink() or not path.is_file():
        raise Hold('PARENT_FILE_HOLD')
    if hashlib.sha256(path.read_bytes()).hexdigest() != PARENT_SHA:
        raise Hold('PARENT_PIN_HOLD')
    spec = importlib.util.spec_from_file_location('pw3_r3734_pinned', path)
    if not spec or not spec.loader:
        raise Hold('PARENT_IMPORT_HOLD')
    parent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parent)
    return parent


def static_load_check(p26, stream):
    """Header-level PT_LOAD, PT_DYNAMIC, p_align and e_entry checks only."""
    h = p26.elf_header(stream)
    if h is None:
        raise Hold('NOT_ELF_HOLD')
    if h['cls'] != 1 or h['machine'] != 40:
        raise Hold('NOT_ELF32_ARM_HOLD')
    e_entry, = struct.unpack(h['endian'] + 'I', p26.read_at(stream, 24, 4))
    loads = []
    dynamics = []
    for i in range(h['phnum']):
        ph = p26.read_at(stream, h['phoff'] + i * h['phsize'], h['phsize'])
        kind, off, vaddr, _paddr, filesz, memsz, flags, align = struct.unpack_from(h['endian'] + 'IIIIIIII', ph, 0)
        if kind not in (1, 2):
            continue
        if off > h['length'] or filesz > h['length'] - off or filesz > memsz:
            raise Hold('SEGMENT_FILE_BOUNDS_HOLD')
        if vaddr + memsz > 0x100000000:
            raise Hold('SEGMENT_VADDR_WRAP_HOLD')
        if kind == 1:
            loads.append((off, vaddr, filesz, memsz, flags, align))
        else:
            dynamics.append((off, filesz))
    if not loads:
        raise Hold('NO_PT_LOAD_HOLD')
    if len(dynamics) > 1:
        raise Hold('MULTIPLE_PT_DYNAMIC_HOLD')
    exec_loads = sum(bool(flags & 1) for _,_,_,_,flags,_ in loads)
    writable_loads = sum(bool(flags & 2) for _,_,_,_,flags,_ in loads)
    wx_loads = sum(bool(flags & 3 == 3) for _,_,_,_,flags,_ in loads)
    align_ok = all(align in (0, 1) or ((align & (align-1)) == 0 and (off-vaddr) % align == 0)
                   for off,vaddr,_,_,_,align in loads)
    entry_exec = any((flags & 1) and vaddr <= e_entry < vaddr + memsz
                     for _,vaddr,_,memsz,flags,_ in loads)
    dynamic_filebacked = (not dynamics) or all(any(
        o <= doff and dsize <= size-(doff-o) for o,_,size,_,_,_ in loads)
        for doff,dsize in dynamics)
    return {
        'elf_type': 'ET_DYN' if h['type'] == 3 else 'ET_EXEC' if h['type'] == 2 else 'OTHER',
        'pt_load_segments': len(loads),
        'executable_load_segments': exec_loads,
        'writable_load_segments': writable_loads,
        'writable_executable_load_segments': wx_loads,
        'all_pt_load_alignments_congruent': align_ok,
        'entrypoint_in_executable_load': entry_exec,
        'pt_dynamic_count': len(dynamics),
        'dynamic_segment_filebacked_by_load': dynamic_filebacked,
    }


def classify_structure(s):
    if s['elf_type'] not in ('ET_DYN','ET_EXEC'):
        return 'NON_EXECUTABLE_ELF_TYPE_HOLD'
    if not s['all_pt_load_alignments_congruent']:
        return 'PT_LOAD_ALIGNMENT_HOLD'
    if not s['entrypoint_in_executable_load']:
        return 'ENTRYPOINT_NOT_EXEC_MAPPED_HOLD'
    if not s['dynamic_segment_filebacked_by_load']:
        return 'DYNAMIC_SEGMENT_NOT_FILEBACKED_HOLD'
    if s['writable_executable_load_segments']:
        return 'WRITABLE_EXECUTABLE_LOAD_REVIEW_HOLD'
    return 'STATIC_LOAD_SEGMENT_CONSTRAINTS_CANDIDATE'


def audit(root, folder, parent):
    if root.is_symlink() or not root.is_dir():
        raise Hold('ROOTFS_INVALID_HOLD')
    r33 = parent.import_r33(folder)
    base = parent.audit(root, folder, r33)
    if (base.get('result') != 'FUTURE_IMAGE_GUEST_ALIAS_SIMULATION_ONLY'
        or base.get('source_interpreter_references') != 12
        or base.get('distinct_missing_guest_paths') != 1
        or base.get('unique_alternate_regular_candidates') != 1
        or base.get('stage_file_writes') != 0
        or base.get('mapping_applied') is not False):
        raise Hold('PARENT_R3734_BASELINE_HOLD')
    p26 = r33.import_parent(folder / r33.R3726, r33.R3726)
    p27 = r33.import_parent(folder / r33.R3727, r33.R3727)
    idx, sources, numreg, numlinks = p27.inventory(root, p26)
    if len(sources) != 12 or numreg != 1446 or numlinks != 335:
        raise Hold('INVENTORY_REPLAY_HOLD')
    missing = {literal for literal, _ in sources}
    if len(missing) != 1:
        raise Hold('MISSING_PATH_UNIQUENESS_HOLD')
    missing_path = next(iter(missing))
    base_name = missing_path.rsplit('/', 1)[-1]
    candidates = set()
    for literal, hdr in sources:
        if literal != missing_path:
            raise Hold('REQUESTERS_DIFFER_HOLD')
        matches = []
        for item, typ in idx.get(base_name, []):
            if typ != 'regular':
                continue
            g = r33.relative_guest_path(root, item)
            cat,hops = p26.classify_guest_target(root,g,hdr)
            if cat == 'GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE' and hops == 0:
                matches.append(item)
        if len(matches) != 1:
            raise Hold('CANDIDATE_UNIQUENESS_HOLD')
        candidates.add(matches[0])
    if len(candidates) != 1:
        raise Hold('CANDIDATE_IDENTITY_HOLD')
    candidate = next(iter(candidates))
    # Confirm the missing guest path has not become present; do not create one.
    parent.absent_leaf(root, missing_path)
    with p26.open_regular_nofollow(candidate) as f:
        loader = static_load_check(p26,f)
    sources_tally = Counter()
    scanned = 0
    def onerror(_):
        raise Hold('STAGE_WALK_HOLD')
    for basepath, dirs, filenames in os.walk(root,followlinks=False,topdown=True,onerror=onerror):
        dirs[:] = sorted(d for d in dirs if not (Path(basepath)/d).is_symlink())
        for name in sorted(filenames):
            path = Path(basepath)/name
            try:
                mode = path.lstat().st_mode
            except OSError:
                raise Hold('STAGE_LSTAT_HOLD') from None
            if not stat.S_ISREG(mode):
                continue
            with p26.open_regular_nofollow(path) as f:
                parsed = p26.inspect_elf(f)
            if parsed is None or not any(x == missing_path for x, _padded in parsed[1]):
                continue
            scanned += 1
            try:
                with p26.open_regular_nofollow(path) as f:
                    data = static_load_check(p26,f)
                sources_tally[classify_structure(data)] += 1
            except (Hold,p26.Hold) as exc:
                sources_tally['SOURCE_STRUCTURAL_HOLD'] += 1
    if scanned != 12:
        raise Hold('SOURCE_INVENTORY_COUNT_HOLD')
    return {
        'milestone':'R40.4.3.7.35',
        'result':'ELF_PT_LOAD_STATIC_CONSTRAINTS_CLASSIFIED_ONLY',
        'parent_r3734_sha_pin_verified':True,
        'parent_chain_and_layout_replayed':True,
        'candidate_structure':loader,
        'candidate_structure_category':classify_structure(loader),
        'requesting_elf_count':scanned,
        'requesting_elf_structural_categories':dict(sorted(sources_tally.items())),
        'guest_path_mapping_applied':False,
        'kernel_loader_runtime_verified':False,
        'complete_arm_abi_verified':False,
        'stage_modified':False,
        'paths_or_contents_exported':False,
        'original_r26_source_provenance_authenticated':False,
        'transitive_dependency_closure_proven':False,
        'boot_authorized':False,
        'prune_authorized':False,
        'immutable_hold':'NOT_BOOTABLE'
    }


def main():
    ap=argparse.ArgumentParser(description='PT_LOAD static constraints only; NOT_BOOTABLE')
    ap.add_argument('--rootfs',required=True,type=Path)
    ap.add_argument('--parent-dir',required=True,type=Path)
    args=ap.parse_args()
    try:
        p=import_parent(args.parent_dir)
        out=audit(args.rootfs,args.parent_dir,p)
    except (Hold,OSError) as e:
        out={'milestone':'R40.4.3.7.35','result':'HOLD',
             'hold_category':e.category if isinstance(e,Hold) else 'IO_HOLD',
             'boot_authorized':False,'prune_authorized':False,
             'immutable_hold':'NOT_BOOTABLE'}
    print(json.dumps(out,sort_keys=True))
    return 0 if out['result']=='ELF_PT_LOAD_STATIC_CONSTRAINTS_CLASSIFIED_ONLY' else 2

if __name__=='__main__':
    raise SystemExit(main())
