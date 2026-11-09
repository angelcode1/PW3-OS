#!/usr/bin/env python3
"""R3877.83 pinned-stage, fail-closed, opt-in one-shot glibc LuaJIT smoke.

Host validates exactly six existing R13-stage ARM objects with the pinned R81/R82
read-only parsers; one SSH session MAY then use a pre-existing executable tmpfs.
No chroot, mount, boot hook, GUI, e-ink, firmware write or persistent install.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import struct
import subprocess
import sys
import tarfile

import pw3_r3877_81_glibc_closure as r81
import pw3_r3877_82_version_abi_audit as r82

NAMES = ('ld-linux.so.3', 'libc.so.6', 'libdl.so.2', 'libgcc_s.so.1', 'libm.so.6')
APP = 'opt/koreader-compat/app/luajit'
LIB_PREFIX = 'opt/koreader-compat/gnu/lib'
MARKER = b'R3877_83_GLIBC_LUAJIT_OK\n'
MAX_TOTAL = 24 * 1024 * 1024
MAX_STAGE = 32 * 1024 * 1024
EXPECTED_SYMBOL_VERSIONS = 13
PRIOR_SOURCE_SHA256 = {
    'pw3_r3877_81_glibc_closure.py': '016c56838c6ceea1e2cb75646e87dc5d742fd8ce5eb045284e62375c1b6d68f5',
    'pw3_r3877_82_version_abi_audit.py': 'a83a6c15149f54fad69564d0c3d941873be8ef3be0c7a6608448ad891355ad18',
}


class Hold(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def report_base():
    return dict(milestone='R3877.83', result='HOLD', immutable_hold='NOT_BOOTABLE',
                hold_category='LIVE_SINGLE_PROCESS_OPT_IN_REQUIRED',
                kindle_access_performed=False, device_execution_attempted=False,
                stage_files_modified=False, firmware_write_performed=False,
                boot_hook_modified=False, mount_performed=False,
                chroot_performed=False, independent_restore_verified=False,
                koreader_gui_started=False, lua_native_execution_verified=False,
                glibc_loader_resolution_verified=False,
                complete_koreader_runtime_verified=False,
                symbol_binding_fully_verified=False,
                r26_stage_identity_revalidated=False)


def validate_stage(stage):
    for name, expected in PRIOR_SOURCE_SHA256.items():
        if digest((Path(__file__).parent / name).read_bytes()) != expected:
            raise Hold('PINNED_ABI_PARSER_SOURCE_CHANGED')
    root = Path(stage).expanduser()
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise Hold('STAGE_ABSOLUTE_REGULAR_DIRECTORY_REQUIRED')
    review = r82.inspect(root)
    counts = review['counts']
    if (counts['required_versions'] != EXPECTED_SYMBOL_VERSIONS or
            counts['matched_versions'] != EXPECTED_SYMBOL_VERSIONS or
            counts['missing_versions'] != 0 or
            counts['versions_without_definition_table'] != 0 or
            review['arm_vfp_warnings']):
        raise Hold('ABI_OR_SYMBOL_VERSION_PREFLIGHT_UNRESOLVED')
    if len(review['objects']) != 6 or set(review['objects']) != set(NAMES) | {'luajit'}:
        raise Hold('UNEXPECTED_PROVIDER_SET')
    for obj in review['objects'].values():
        if obj['float_e_flags'] != 'soft':
            raise Hold('FLOAT_ABI_FLAGS_NOT_MATCHED')
        if obj['arm_vfp_args']['status'] not in ('TAG_ABSENT', 'BASE_AAPCS', 'BOTH_COMPATIBLE'):
            raise Hold('ARM_VFP_ABI_NOT_REVIEWED')
    if not review['objects']['luajit']['rpath_resolution_categories']:
        raise Hold('LUAJIT_RPATH_NOT_PRESENT_TO_INHIBIT')
    if review['objects']['luajit']['has_pt_interp'] is not True:
        raise Hold('LUAJIT_INTERP_UNEXPECTED')
    if review['objects']['ld-linux.so.3']['has_pt_interp'] is not False:
        raise Hold('LOADER_HAS_UNEXPECTED_INTERPRETER')
    objects = {}
    for name, path in [('luajit', APP)] + [(name, f'{LIB_PREFIX}/{name}') for name in NAMES]:
        rel = Path(path)
        current = root
        for comp in rel.parts[:-1]:
            current = current / comp
            if current.is_symlink() or not current.is_dir():
                raise Hold('STAGE_PROVIDER_PARENT_SYMLINK_OR_MISSING')
        try:
            b = r81.raw_file(root / rel)
        except (r81.Refused, OSError) as err:
            raise Hold('STAGE_ELF_READ_REFUSED') from err
        if len(b) > MAX_STAGE:
            raise Hold('STAGE_ELF_TOO_LARGE')
        objects[name] = b
    if sum(map(len, objects.values())) > MAX_TOTAL:
        raise Hold('BUNDLE_TOTAL_TOO_LARGE')
    loader = objects['ld-linux.so.3']
    for literal in (b'--inhibit-rpath', b'--library-path', b'--inhibit-cache', b'--list'):
        if literal not in loader:
            raise Hold('LOADER_OPTION_STRING_UNVERIFIED')
    # RPATH may include unsafe or unknown entries. We ONLY run LuaJIT after
    # the relocated loader's --list shows all needed providers in tmpfs.
    # Explicit --inhibit-rpath must be recognized by this loader (above).
    return objects, review


def bundle_tar(objects):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w', format=tarfile.USTAR_FORMAT) as tf:
        for name in ('luajit',) + NAMES:
            data = objects[name]
            info = tarfile.TarInfo(name)
            info.mode = 0o500
            info.uid = info.gid = 0
            info.mtime = 0
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return output.getvalue()


def remote_shell(objects):
    checks = '\n'.join(
        'check_one ' + shlex.quote(n) + ' ' + str(len(objects[n])) + ' ' + digest(objects[n]) + ' || exit 48'
        for n in ('luajit',) + NAMES
    )
    # shell is passed via sh -c and the tar archive via stdin. All archived
    # entries have host-authored bare filenames and no links/paths.
    return r'''set -fu
PATH=/bin:/sbin:/usr/bin:/usr/sbin; export PATH
umask 077
[ "$(uname -r 2>/dev/null)" = 3.0.35-lab126 ] || exit 40
[ "$(uname -m 2>/dev/null)" = armv7l ] || exit 40
[ -r /proc/mounts ] || exit 41
place=''
while read -r device mp kind opts rest; do
  case "$mp:$kind" in /tmp:tmpfs|/dev/shm:tmpfs|/run:tmpfs) : ;; *) continue ;; esac
  case ",$opts," in *,rw,*) : ;; *) continue ;; esac
  case ",$opts," in *,noexec,*) continue ;; esac
  [ -d "$mp" ] && [ ! -L "$mp" ] || continue
  place="$mp"; break
done </proc/mounts
[ -n "$place" ] || exit 42
bb=''
for x in /bin/busybox /sbin/busybox /usr/bin/busybox /usr/sbin/busybox; do
  [ -x "$x" ] && { bb="$x"; break; }
done
[ -n "$bb" ] || exit 43
work="$place/pw3-r3877-83-$$"
mkdir "$work" || exit 44
cleanup() {
  for f in luajit ld-linux.so.3 libc.so.6 libdl.so.2 libgcc_s.so.1 libm.so.6; do rm -f "$work/$f"; done
  rmdir "$work"
}
trap 'cleanup' 0
trap 'exit 70' 1 2 3 15
"$bb" tar -xf - -C "$work" || exit 45
check_one() {
  nm="$1"; expected_size="$2"; expected_hash="$3"; file="$work/$nm"
  [ -f "$file" ] && [ ! -L "$file" ] || return 1
  actual_size=$(wc -c < "$file") || return 1
  [ "$actual_size" = "$expected_size" ] || return 1
  set -- $(sha256sum "$file")
  [ "$1" = "$expected_hash" ] || return 1
}
CHECKS
chmod 500 "$work/luajit" "$work/ld-linux.so.3" || exit 49
ulimit -c 0 2>/dev/null || :
ulimit -t 5 2>/dev/null || :
# Explicit loader suppresses the embedded ELF PT_INTERP /lib path.
# Inhibit potentially untrusted RPATH BEFORE enforcing complete list mapping.
list=$(
  "$bb" env -i PATH="$PATH" HOME="$work" LC_ALL=C \
    "$work/ld-linux.so.3" --inhibit-cache \
    --inhibit-rpath "luajit:$work/luajit" \
    --library-path "$work" --list "$work/luajit"
) || exit 50
# Every named needed library must have been relocated into our private RAM dir.
for name in libc.so.6 libdl.so.2 libgcc_s.so.1 libm.so.6; do
  case "$list" in *"$name => $work/$name "*) : ;; *) exit 51 ;; esac
done
case "$list" in *"$work/ld-linux.so.3"*) : ;; *) exit 51 ;; esac
printf '%s\n' "$list" | while IFS= read -r line; do
  case "$line" in
    *' => '*)
      case "$line" in *" => $work/"*) : ;; *) exit 52 ;; esac
      ;;
  esac
done || exit 52
# Bounded no-GUI LuaJIT program; no filesystem writes or KOReader imports.
"$bb" env -i PATH="$PATH" HOME="$work" LC_ALL=C \
  "$work/ld-linux.so.3" --inhibit-cache \
  --inhibit-rpath "luajit:$work/luajit" \
  --library-path "$work" "$work/luajit" \
  -e 'io.write("R3877_83_GLIBC_LUAJIT_OK\n")' || exit 53
cleanup || exit 54
trap - 0 1 2 3 15
exit 0'''.replace('CHECKS', checks)


FAILURES = {
    40:'TARGET_KERNEL_OR_ARCH_MISMATCH', 41:'MOUNT_METADATA_MISSING',
    42:'NO_EXISTING_EXECUTABLE_TMPFS', 43:'STOCK_BUSYBOX_MISSING',
    44:'PRIVATE_RAM_DIRECTORY_CREATE_FAILED', 45:'BUNDLE_TAR_UNPACK_FAILED',
    48:'BUNDLE_HASH_OR_SIZE_OR_TYPE_FAILED', 49:'EXEC_PERMISSION_FAILED',
    50:'DYNAMIC_LOADER_LIST_FAILED', 51:'DYNAMIC_LOADER_PROVIDER_NOT_IN_RAM',
    52:'DYNAMIC_LOADER_RESOLVED_OTHER_DEPENDENCY', 53:'LUAJIT_SMOKE_EXEC_FAILED',
    54:'TMPFS_CLEANUP_FAILED', 70:'REMOTE_INTERRUPTED',
    255:'SSH_FAILED',
}


def main(argv=None, runner=subprocess.run):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage', required=True)
    ap.add_argument('--review-only', action='store_true')
    ap.add_argument('--acknowledge-one-shot-kindle-glibc-test', action='store_true')
    ap.add_argument('--target', default='root@192.168.8.102')
    ap.add_argument('--port', type=int, default=2222)
    args = ap.parse_args(argv)
    report = report_base()
    if not args.review_only and not args.acknowledge_one_shot_kindle_glibc_test:
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 2
    if args.acknowledge_one_shot_kindle_glibc_test and args.review_only:
        report['hold_category'] = 'MUTUALLY_EXCLUSIVE_MODES'
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 2
    if not re.fullmatch(r'root@[A-Za-z0-9][A-Za-z0-9.\-]{0,252}', args.target) or not 1 <= args.port <= 65535:
        report['hold_category'] = 'TARGET_OR_PORT_INVALID'
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 2
    try:
        objects, reviewed = validate_stage(args.stage)
        report['host_bundle_sha256_verified'] = True
        report['host_glibc_version_names_matched'] = True
        report['host_bundle_bytes'] = sum(len(v) for v in objects.values())
        report['rpath_entries_reviewed_but_inhibited'] = len(reviewed['objects']['luajit']['rpath_resolution_categories'])
        payload = bundle_tar(objects)
    except (Hold, r81.Refused, r82.Refused, OSError, ValueError, UnicodeError, KeyError, struct.error, tarfile.TarError) as e:
        report['hold_category'] = 'OFFLINE_STAGE_GLIBC_REVIEW_REFUSED'
        if isinstance(e, Hold): report['offline_refusal_code'] = str(e)
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 2
    if args.review_only:
        report['hold_category'] = 'HOST_CHECK_PASS_DEVICE_LOADER_UNVERIFIED'
        report['offline_validation_passed'] = True
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 2
    command = ['ssh', '-T', '-o', 'ConnectTimeout=15', '-o', 'ConnectionAttempts=1',
               '-p', str(args.port), args.target,
               'sh -c ' + shlex.quote(remote_shell(objects))]
    report['kindle_access_performed'] = True
    report['device_execution_attempted'] = True
    try:
        done = runner(command, input=payload, stdout=subprocess.PIPE,
                      stderr=subprocess.PIPE, timeout=75, check=False)
    except (OSError, subprocess.TimeoutExpired):
        report['hold_category'] = 'SSH_OR_TIMEOUT_CLEANUP_UNVERIFIED'
    else:
        report['ssh_exit_code'] = done.returncode
        if done.returncode == 0 and done.stdout == MARKER:
            report['result'] = 'PASS_GLIBC_LUAJIT_SINGLE_PROCESS'
            report['hold_category'] = 'KOREADER_GUI_BOOT_AND_RECOVERY_STILL_UNVERIFIED'
            report['glibc_loader_resolution_verified'] = True
            report['lua_native_execution_verified'] = True
            report['tmpfs_cleanup_reported_complete'] = True
        else:
            report['hold_category'] = FAILURES.get(done.returncode, 'REMOTE_OUTPUT_OR_EXIT_UNEXPECTED')
            report['tmpfs_cleanup_reported_complete'] = False
    print(json.dumps(report, sort_keys=True, separators=(',', ':')))
    return 0 if report['lua_native_execution_verified'] else 2

if __name__ == '__main__':
    sys.exit(main())
