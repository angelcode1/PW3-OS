#!/usr/bin/env python3
"""R3877.62: bounded, read-only local recovery asset *candidate* inventory.

Finds possible local evidence only; never asserts recoverability. No Kindle,
Docker, SSH, external commands, network, firmware writes, or raw file reads.
"""
import argparse
from collections import Counter
from pathlib import Path
import json
import re
import stat
import sys

MILESTONE = 'R3877.62.1'
CAP_FILES = 20000
CAP_DEPTH = 4
EXCLUDED_DIRS = {'.git', '.Trash', 'node_modules', '.venv', 'venv', '__pycache__', '.cache', 'Library'}
CATEGORIES = {
    'stock_partition_image_candidate': re.compile(r'(?i)(?:mmcblk|boot[0-9]?|rootfs|kernel|u-boot|uboot|partition|factory|original|stock).*(?:\.img|\.bin|\.dump|\.dd|\.raw|\.ubi|\.ubifs)$'),
    'image_or_dump_other': re.compile(r'(?i)\.(?:img|dump|dd|raw|ubi|ubifs)$'),
    'recovery_document_candidate': re.compile(r'(?i)(?:recover|restore|rescue|fastboot|serial|uboot|u-boot).*(?:\.md|\.txt|\.pdf|\.json|\.log)$'),
    'backup_archive_candidate': re.compile(r'(?i)(?:backup|pw3|kindle|rootfs|recovery).*(?:\.zip|\.tar|\.tgz|\.tar\.gz|\.xz|\.zst|\.7z)$'),
}

class Hold(Exception):
    pass


def classify(name):
    for key,pattern in CATEGORIES.items():
        if pattern.search(name):
            return key
    return None


# On macOS /var and /tmp are system-owned aliases into /private.
# Everything else remains subject to the fail-closed symlink rule.
MACOS_SYSTEM_ALIASES = {'/var': '/private/var', '/tmp': '/private/tmp'}


def approved_macos_system_alias(path):
    """Allow only a canonical macOS system alias, never user-owned links."""
    if sys.platform != 'darwin':
        return False
    target = MACOS_SYSTEM_ALIASES.get(str(path))
    if target is None:
        return False
    try:
        expected = Path(target)
        return (path.is_symlink() and expected.is_dir()
                and not expected.is_symlink()
                and path.resolve(strict=True) == expected)
    except (OSError, RuntimeError):
        return False


def check_root(root):
    root = Path(root).expanduser()
    if not root.is_absolute():
        root = Path.cwd() / root
    if '..' in root.parts:
        raise Hold('PARENT_DIRECTORY_COMPONENT_UNVERIFIED')
    if root.is_symlink() or not root.exists() or not root.is_dir():
        raise Hold('DIRECTORY_MISSING_INVALID_OR_SYMLINK')
    if any(p.is_symlink() and not approved_macos_system_alias(p)
           for p in (root, *root.parents)):
        raise Hold('SYMLINK_IN_DIRECTORY_ANCESTRY')
    canonical = root.resolve(strict=True)
    if any(p.is_symlink() for p in (canonical, *canonical.parents)):
        raise Hold('SYMLINK_IN_RESOLVED_ANCESTRY')
    return canonical


def inventory(root, max_depth=CAP_DEPTH, cap=CAP_FILES):
    if not isinstance(max_depth,int) or not 0 <= max_depth <= CAP_DEPTH:
        raise Hold('DEPTH_OUT_OF_BOUNDS')
    if not isinstance(cap,int) or not 1 <= cap <= CAP_FILES:
        raise Hold('FILE_BUDGET_OUT_OF_BOUNDS')
    root=check_root(root)
    stack=[(root,0)]
    visited=0
    symlink_skipped=0
    inaccessible=0
    skipped_dirs=0
    truncated=False
    categories=Counter()
    extension_sizes={key:0 for key in CATEGORIES}
    while stack and not truncated:
        path,depth=stack.pop()
        try:
            items=sorted(path.iterdir(),key=lambda v:v.name)
        except (PermissionError, OSError):
            inaccessible+=1
            continue
        for entry in items:
            try:
                mode=entry.lstat().st_mode
                if stat.S_ISLNK(mode):
                    symlink_skipped+=1
                    continue
                if stat.S_ISDIR(mode):
                    if depth < max_depth and entry.name not in EXCLUDED_DIRS and not entry.name.startswith('.'):
                        stack.append((entry,depth+1))
                    else:
                        skipped_dirs+=1
                    continue
                if not stat.S_ISREG(mode):
                    continue
                visited+=1
                if visited > cap:
                    truncated=True
                    break
                category=classify(entry.name)
                if category:
                    categories[category]+=1
                    extension_sizes[category]+=entry.stat().st_size
            except (PermissionError, OSError):
                inaccessible+=1
    return {'inventory_status':'BOUNDED_CANDIDATE_INVENTORY_ONLY',
            'regular_files_considered':min(visited,cap),
            'candidate_counts_by_category':dict(sorted(categories.items())),
            'candidate_total_sizes_bytes_by_category':{k:v for k,v in sorted(extension_sizes.items()) if categories[k]},
            'file_budget_exhausted':truncated,
            'unreadable_entries_count':inaccessible,
            'symlink_entries_skipped':symlink_skipped,
            'directory_entries_skipped':skipped_dirs,
            'max_relative_depth':max_depth,
            'raw_names_or_paths_published':False,
            'candidate_file_contents_read':False,
            'file_hashes_verified':False,
            'recovery_assets_authenticated':False,
            'recovery_procedure_tested':False}


def preflight():
    return {'milestone':MILESTONE, 'result':'HOLD', 'immutable_hold':'NOT_BOOTABLE',
        'recovery_verified':False,'vendor_kernel_compatibility_verified':False,
        'physical_device_access_performed':False, 'kindle_ssh_sessions':0,
        'arm_guest_execution_performed':False, 'docker_used':False,
        'boot_performed':False,'firmware_write_performed':False,
        'network_access_performed':False,'local_files_modified':False,
        'no_untrusted_candidate_implies_recovery':True}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scan-root', help='Explicit local directory to scan read-only; no default')
    p.add_argument('--max-depth',type=int,default=CAP_DEPTH)
    p.add_argument('--max-files',type=int,default=CAP_FILES)
    a=p.parse_args(argv)
    result=preflight()
    if not a.scan_root:
        result['hold_category']='EXPLICIT_LOCAL_DIRECTORY_REQUIRED'
    else:
        try:
            result['inventory']=inventory(a.scan_root,a.max_depth,a.max_files)
            result['hold_category']='RECOVERY_AUTHENTICITY_AND_INDEPENDENT_RESTORE_UNVERIFIED'
        except (Hold,ValueError,TypeError,RuntimeError,OSError) as err:
            result['hold_category']=str(err).splitlines()[0][:140]
    print(json.dumps(result,sort_keys=True,separators=(',',':')))
    return 2

if __name__=='__main__':sys.exit(main())
