#!/usr/bin/env python3
"""R3877.77: opt-in one-shot ARM EABI write+exit probe in Kindle RAM-backed tmpfs.

Generated ELF performs only write(1, fixed string, n) and exit(0).
No runtime libraries, dynamic interpreter, loader, chroot or mount calls.
Device SSH remains explicit opt-in and is refused unless a pre-existing
executable tmpfs is discovered. Never accesses block devices or boot hooks.
"""
import argparse
import hashlib
import json
import re
import shlex
import struct
import subprocess
import sys
import zlib

MARKER = b'R3877_77_ARM_SYSCALL_OK\n'
LOAD_BASE = 0x10000
CODE_OFFSET = 0x100
ARM_WORDS = (
    0xE3A00001,  # mov r0, #1        (stdout)
    0xE28F1014,  # add r1, pc, #20   (literal at code + 32)
    0xE3A02000 | len(MARKER),  # mov r2, #marker length
    0xE3A07004,  # mov r7, #4        (Linux ARM EABI write)
    0xEF000000,  # svc #0
    0xE3A00000,  # mov r0, #0
    0xE3A07001,  # mov r7, #1        (Linux ARM EABI exit)
    0xEF000000,  # svc #0
)


def generate_elf():
    code = struct.pack('<8I', *ARM_WORDS) + MARKER
    size = CODE_OFFSET + len(code)
    ident = b'\x7fELF' + bytes([1, 1, 1, 0]) + bytes(8)
    ehdr = struct.pack('<16sHHIIIIIHHHHHH', ident, 2, 40, 1,
                       LOAD_BASE + CODE_OFFSET, 52, 0, 0x05000000,
                       52, 32, 1, 0, 0, 0)
    phdr = struct.pack('<8I', 1, 0, LOAD_BASE, LOAD_BASE,
                       size, size, 5, 0x1000)
    assert len(ehdr) == 52 and len(phdr) == 32
    return ehdr + phdr + bytes(CODE_OFFSET - 84) + code


REMOTE_TEMPLATE = r'''set -fu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
umask 077
[ "$(uname -r 2>/dev/null)" = '3.0.35-lab126' ] || exit 40
[ "$(uname -m 2>/dev/null)" = 'armv7l' ] || exit 40
[ -r /proc/mounts ] || exit 41
exec_tmpfs=''
while read -r device point kind opts other; do
  case "$point:$kind" in
    /tmp:tmpfs|/dev/shm:tmpfs|/run:tmpfs) : ;;
    *) continue ;;
  esac
  case ",$opts," in *,rw,*) : ;; *) continue ;; esac
  case ",$opts," in *,noexec,*) continue ;; esac
  [ -d "$point" ] && [ ! -L "$point" ] || continue
  exec_tmpfs="$point"
  break
done </proc/mounts
[ -n "$exec_tmpfs" ] || exit 42
work="$exec_tmpfs/pw3-r3877-77-$$"
mkdir "$work" || exit 43
probe="$work/probe"
cleanup() { rm -f "$probe"; rmdir "$work"; }
trap 'cleanup' 0
trap 'exit 70' 1 2 3 15
cat > "$probe" || exit 44
size=$(wc -c < "$probe") || exit 45
[ "$size" = "EXPECTED_BYTES" ] || exit 45
set -- $(sha256sum "$probe")
[ "$1" = 'EXPECTED_SHA256' ] || exit 46
chmod 500 "$probe" || exit 47
ulimit -t 3 2>/dev/null || :
"$probe" || exit 48
rm -f "$probe" || exit 49
rmdir "$work" || exit 49
trap - 0 1 2 3 15
exit 0'''

EXIT_CATEGORIES = {
    40: 'TARGET_KERNEL_OR_ARCH_MISMATCH',
    41: 'MOUNT_METADATA_UNAVAILABLE',
    42: 'NO_EXISTING_EXECUTABLE_TMPFS',
    43: 'TMPFS_PRIVATE_DIR_CREATE_FAILED',
    44: 'PROBE_COPY_FAILED',
    45: 'PROBE_BYTE_COUNT_FAILED',
    46: 'PROBE_SHA256_FAILED',
    47: 'PROBE_CHMOD_FAILED',
    48: 'ELF_EXECUTION_FAILED',
    49: 'TMPFS_CLEANUP_FAILED',
    70: 'REMOTE_INTERRUPTED',
    255: 'SSH_TRANSPORT_FAILED',
}


def make_remote(elf):
    sha = hashlib.sha256(elf).hexdigest()
    assert re.fullmatch(r'[0-9a-f]{64}', sha)
    return REMOTE_TEMPLATE.replace('EXPECTED_BYTES', str(len(elf))).replace('EXPECTED_SHA256', sha)


def result():
    return dict(milestone='R3877.77', result='HOLD', immutable_hold='NOT_BOOTABLE',
                hold_category='DEVICE_EXECUTION_NOT_AUTHORIZED',
                device_execution_performed=False, device_firmware_write_performed=False,
                partition_mount_performed=False, chroot_performed=False,
                boot_hook_modified=False, independent_restore_verified=False,
                kernel_glibc_musl_compatibility_verified=False,
                local_elf_generation_verified=False)


def main(argv=None, runner=subprocess.run):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--acknowledge-single-process-tmpfs-execution', action='store_true')
    p.add_argument('--target', default='root@192.168.8.102')
    p.add_argument('--port', type=int, default=2222)
    args = p.parse_args(argv)
    report = result()
    elf = generate_elf()
    report['local_elf_generation_verified'] = (
        elf.startswith(b'\x7fELF') and len(elf) < 512
        and elf[CODE_OFFSET:CODE_OFFSET+32] == struct.pack('<8I', *ARM_WORDS)
        and elf.endswith(MARKER))
    report['generated_elf_bytes'] = len(elf)
    report['elf_class'] = 'ELF32_ARM_EABI5_STATIC_NO_INTERPRETER'
    report['elf_syscalls'] = ['write_stdout', 'exit']
    if not args.acknowledge_single_process_tmpfs_execution:
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 2
    if not re.fullmatch(r'root@[A-Za-z0-9][A-Za-z0-9.\-]{0,252}', args.target) or not (1 <= args.port <= 65535):
        report['hold_category'] = 'INVALID_TARGET_OR_PORT'
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 2
    remote = make_remote(elf)
    cmd = ['ssh', '-T', '-o', 'ConnectTimeout=15', '-o', 'ConnectionAttempts=1',
           '-p', str(args.port), args.target, 'sh -c ' + shlex.quote(remote)]
    try:
        completed = runner(cmd, input=elf, stdout=subprocess.PIPE, timeout=45, check=False)
    except (OSError, subprocess.TimeoutExpired):
        report['hold_category'] = 'SSH_UNAVAILABLE_OR_TIMEOUT'
    else:
        report['ssh_exit_code'] = completed.returncode
        if completed.returncode == 0 and completed.stdout == MARKER:
            report['result'] = 'PASS_SINGLE_ARM_EABI_SYSCALL_ONLY'
            report['hold_category'] = 'INDEPENDENT_RESTORE_AND_DYNAMIC_ABI_UNVERIFIED'
            report['device_execution_performed'] = True
            report['tmpfs_payload_removed_by_remote_script'] = True
            report['single_process_write_exit_verified'] = True
        else:
            report['hold_category'] = EXIT_CATEGORIES.get(completed.returncode,
                                                          'REMOTE_OUTPUT_OR_EXIT_UNEXPECTED')
            report['tmpfs_payload_removed_by_remote_script'] = False
    # Even a successful one-shot probe cannot lift the independent OS boot hold.
    print(json.dumps(report, sort_keys=True, separators=(',', ':')))
    return 0 if report['result'].startswith('PASS_') else 2


if __name__ == '__main__':
    sys.exit(main())
