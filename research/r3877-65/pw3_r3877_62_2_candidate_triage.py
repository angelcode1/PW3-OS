#!/usr/bin/env python3
"""R3877.62.2: candidate-first, metadata-only Kindle recovery triage.

Read-only: no candidate content, hashing, archive extraction, network, Docker,
QEMU or Kindle operations. Outputs aggregate counts, NOT names or paths.
Always HOLD; no candidate implies an authenticated backup or verified restore.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

import pw3_r3877_62_recovery_inventory as base

MILESTONE = 'R3877.62.2'
BASE_SHA256 = '996590a6d9271029102cd62be54975bcb10e24d8b4e386e00f687eb12688cc02'
MAX_ENTRIES = 150000
MAX_CANDIDATES = 10000
MAX_DEPTH = 4
ARCHIVE = re.compile(r'(?i)(?:\.zip|\.tar|\.tgz|\.tar\.gz|\.tar\.xz|\.tar\.zst|\.xz|\.zst|\.7z)$')
RESEARCH_ARCHIVE = re.compile(r'(?i)^(?:pw3-r[0-9]|pw3-os-r[0-9]|pw3-os-.*(?:research|evidence|audit|inventory|qemu|host-only)|r3877[-_])')
UPDATE = re.compile(r'(?i)^(?:update_kindle|kindle[_-]update|firmware[_-]update).*(?:\.bin|\.zip)$')
CHECKSUM = re.compile(r'(?i)(?:sha256sums(?:_.*)?\.txt|checksums?(?:\.txt|\.sha256)|\.(?:sha256|md5|sha512))$')
BANDS = ('zero_bytes','under_1_mib','1_to_16_mib','16_to_128_mib','128_mib_or_more')

class Hold(Exception): pass

def require_base():
    p = Path(base.__file__)
    if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=BASE_SHA256:
        raise Hold('PINNED_R62_1_BASE_CHANGED')
    return True

def category(name):
    """Precedence matters: research ZIPs must not masquerade as stock backups."""
    if UPDATE.search(name): return 'official_update_package_candidate_not_recovery_backup'
    if ARCHIVE.search(name) and RESEARCH_ARCHIVE.search(name):
        return 'research_named_archive_candidate_not_authenticated_backup'
    original = base.classify(name)
    if original == 'backup_archive_candidate': return 'nonresearch_named_backup_archive_candidate'
    if original: return original
    if CHECKSUM.search(name): return 'integrity_manifest_filename_candidate'
    return None

def band(size):
    if size==0: return BANDS[0]
    if size < 1024*1024: return BANDS[1]
    if size < 16*1024*1024: return BANDS[2]
    if size < 128*1024*1024: return BANDS[3]
    return BANDS[4]

def triage(root, max_depth=3, max_entries=60000, max_candidates=3000):
    if not isinstance(max_depth,int) or not 0<=max_depth<=MAX_DEPTH:
        raise Hold('DEPTH_OUT_OF_BOUNDS')
    if not isinstance(max_entries,int) or not 1<=max_entries<=MAX_ENTRIES:
        raise Hold('ENTRY_BUDGET_OUT_OF_BOUNDS')
    if not isinstance(max_candidates,int) or not 1<=max_candidates<=MAX_CANDIDATES:
        raise Hold('CANDIDATE_BUDGET_OUT_OF_BOUNDS')
    root=base.check_root(root)
    todo=[(root,0)]
    categories=Counter()
    sizes=Counter()
    bands=defaultdict(Counter)
    entries=0
    files=0
    skipped_links=0
    skipped_dirs=0
    unreadable=0
    directories_scanned=0
    truncated_by_entries=False
    truncated_by_candidates=False
    while todo and not (truncated_by_entries or truncated_by_candidates):
        path,depth=todo.pop()
        # A replaced directory must never be followed if it has turned into a link.
        try:
            if path.is_symlink() or not path.is_dir():
                unreadable+=1
                continue
            with os.scandir(path) as it:
                directories_scanned+=1
                for entry in it:
                    if entries>=max_entries:
                        truncated_by_entries=True
                        break
                    entries+=1
                    try:
                        st=entry.stat(follow_symlinks=False)
                        mode=st.st_mode
                        if stat.S_ISLNK(mode):
                            skipped_links+=1
                            continue
                        if stat.S_ISDIR(mode):
                            if (depth<max_depth and entry.name not in base.EXCLUDED_DIRS
                                 and not entry.name.startswith('.')):
                                todo.append((Path(entry.path),depth+1))
                            else: skipped_dirs+=1
                            continue
                        if not stat.S_ISREG(mode): continue
                        files+=1
                        c=category(entry.name)
                        if c:
                            if sum(categories.values())>=max_candidates:
                                truncated_by_candidates=True
                                break
                            categories[c]+=1
                            sizes[c]+=st.st_size
                            bands[c][band(st.st_size)]+=1
                    except (OSError,ValueError):
                        unreadable+=1
        except (OSError,ValueError):
            unreadable+=1
    completed=not truncated_by_entries and not truncated_by_candidates and unreadable==0
    return {
        'inventory_status':'CANDIDATE_FIRST_METADATA_TRIAGE_ONLY',
        'bounded_scope_scan_complete':completed,
        'max_relative_depth':max_depth,
        'directory_entries_considered':entries,
        'directories_scanned':directories_scanned,
        'regular_files_considered':files,
        'candidate_count_total':sum(categories.values()),
        'candidate_counts_by_category':dict(sorted(categories.items())),
        'candidate_total_sizes_bytes_by_category':dict(sorted(sizes.items())),
        'candidate_size_bands_by_category':{k:dict(sorted(v.items())) for k,v in sorted(bands.items())},
        'entry_budget_exhausted':truncated_by_entries,
        'candidate_budget_exhausted':truncated_by_candidates,
        'unreadable_entries_count':unreadable,
        'symlink_entries_skipped':skipped_links,
        'directory_entries_skipped':skipped_dirs,
        'raw_names_or_paths_published':False,
        'candidate_file_contents_read':False,
        'file_hashes_verified':False,
        'recovery_assets_authenticated':False,
        'recovery_procedure_tested':False,
        'stock_partition_image_authenticity_verified':False,
    }

def preflight():
    return {'milestone':MILESTONE,'result':'HOLD','hold_category':'EXPLICIT_LOCAL_DIRECTORY_REQUIRED',
        'immutable_hold':'NOT_BOOTABLE','recovery_verified':False,
        'vendor_kernel_compatibility_verified':False,
        'physical_device_access_performed':False,'kindle_ssh_sessions':0,
        'arm_guest_execution_performed':False,'docker_used':False,
        'boot_performed':False,'firmware_write_performed':False,
        'network_access_performed':False,'local_files_modified':False,
        'candidate_authenticity_verified':False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scan-root')
    p.add_argument('--max-depth',type=int,default=3)
    p.add_argument('--max-entries',type=int,default=60000)
    p.add_argument('--max-candidates',type=int,default=3000)
    a=p.parse_args(argv)
    r=preflight()
    if a.scan_root:
        try:
            require_base()
            r['inventory']=triage(a.scan_root,a.max_depth,a.max_entries,a.max_candidates)
            r['hold_category']='RECOVERY_AUTHENTICITY_AND_INDEPENDENT_RESTORE_UNVERIFIED'
        except (Hold,base.Hold,TypeError,ValueError,RuntimeError,OSError) as e:
            r['hold_category']=str(e).splitlines()[0][:140]
    print(json.dumps(r,sort_keys=True,separators=(',',':')))
    return 2
if __name__=='__main__':sys.exit(main())
