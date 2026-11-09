#!/usr/bin/env python3
"""R3877.78: pinned Alpine ARMv7 musl loader+BusyBox smoke test in Kindle tmpfs.

No boot hooks, mount, chroot, firmware writes, persistent copies or serial access.
Device execution requires explicit opt-in; remote writes only to existing
executable tmpfs, verifies exact bytes, runs one BusyBox echo, cleans up.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import posixpath
import re
import shlex
import struct
import subprocess
import sys
import tarfile

ROOTFS_NAME = 'alpine-minirootfs-3.24.2-armv7.tar.gz'
ROOTFS_SHA256 = '5552f1ef2398cee46ef2cf733f8f1258f39a77ad065dfd47282fc0df9fe1976c'
ROOTFS_URL = 'https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/armv7/' + ROOTFS_NAME
MARKER = 'R3877_78_MUSL_BUSYBOX_OK\n'
PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3
DT_NEEDED, DT_STRTAB, DT_STRSZ = 1, 5, 10

class Refused(Exception):
    pass


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_pinned_archive(path):
    p = Path(path).expanduser()
    if p.is_symlink() or not p.is_file() or p.stat().st_size > 8_388_608:
        raise Refused('ROOTFS_FILE_INVALID_OR_TOO_LARGE')
    data = p.read_bytes()
    if sha256(data) != ROOTFS_SHA256:
        raise Refused('ROOTFS_PINNED_SHA256_MISMATCH')
    return data


def lookup_member(tf, name):
    for i in range(5):
        candidates = [x for x in tf.getmembers() if x.name.lstrip('./') == name]
        if len(candidates) != 1:
            raise Refused('ROOTFS_REQUIRED_MEMBER_MISSING_OR_DUPLICATED')
        m = candidates[0]
        if m.isreg():
            if not (64 <= m.size <= 8_388_608):
                raise Refused('ROOTFS_MEMBER_SIZE_INVALID')
            stream = tf.extractfile(m)
            if stream is None:
                raise Refused('ROOTFS_MEMBER_READ_FAILED')
            contents = stream.read(8_388_609)
            if len(contents) != m.size:
                raise Refused('ROOTFS_MEMBER_READ_TRUNCATED')
            return contents
        if not m.issym() and not m.islnk():
            raise Refused('ROOTFS_MEMBER_NOT_ELF_FILE_OR_SYMLINK')
        target = m.linkname
        if target.startswith('/'):
            target = target.lstrip('/')
        elif m.issym():
            target = posixpath.join(posixpath.dirname(name), target)
        target = posixpath.normpath(target)
        if target.startswith('../') or target.startswith('/') or not target.startswith('lib/'):
            raise Refused('ROOTFS_LIB_SYMLINK_ESCAPES_LIBRARY_DIR')
        name = target
    raise Refused('ROOTFS_LIB_SYMLINK_CHAIN_TOO_DEEP')


def elf_metadata(data):
    if len(data) < 52 or data[:4] != b'\x7fELF' or data[4:7] != b'\x01\x01\x01':
        raise Refused('ELF32_LE_HEADER_MISSING')
    etype, machine, version = struct.unpack_from('<HHI', data, 16)
    flags, phoff, phentsize, phnum = (struct.unpack_from('<I', data, 36)[0],
                                     struct.unpack_from('<I', data, 28)[0],
                                     struct.unpack_from('<H', data, 42)[0],
                                     struct.unpack_from('<H', data, 44)[0])
    if machine != 40 or version != 1 or etype not in (2, 3) or (flags >> 24) != 5:
        raise Refused('ELF_ARM_EABI5_MISMATCH')
    if not (flags & 0x400):
        raise Refused('ELF_ARM_HARD_FLOAT_FLAG_ABSENT')
    if phentsize != 32 or not (1 <= phnum <= 64) or phoff + phentsize * phnum > len(data):
        raise Refused('ELF_PROGRAM_HEADERS_INVALID')
    ph = []
    interp = None
    for n in range(phnum):
        p = struct.unpack_from('<8I', data, phoff + 32*n)
        typ, off, vaddr, _paddr, filesz, _memsz, _flags, _align = p
        if off + filesz > len(data):
            raise Refused('ELF_SEGMENT_OUTSIDE_FILE')
        ph.append(p)
        if typ == PT_INTERP:
            value = data[off:off+filesz]
            if not value.endswith(b'\0') or len(value) > 128:
                raise Refused('ELF_INTERP_UNTERMINATED')
            interp = value[:-1].decode('ascii', errors='strict')
    return {'type': etype, 'interp': interp, 'ph': ph, 'hard_float': True}


def needed_libraries(data, info):
    dynamic = [p for p in info['ph'] if p[0] == PT_DYNAMIC]
    if len(dynamic) != 1:
        raise Refused('BUSYBOX_DYNAMIC_SEGMENT_MISSING')
    _, off, _, _, size, _, _, _ = dynamic[0]
    if size > 65536 or size % 8:
        raise Refused('ELF_DYNAMIC_SEGMENT_INVALID')
    values = {}
    needed_offsets = []
    for i in range(0, size, 8):
        tag, val = struct.unpack_from('<II', data, off + i)
        if tag == 0:
            break
        if tag == DT_NEEDED:
            needed_offsets.append(val)
        if tag in (DT_STRTAB, DT_STRSZ):
            values[tag] = val
    if DT_STRTAB not in values or DT_STRSZ not in values or not needed_offsets:
        raise Refused('ELF_DYNAMIC_STRING_TABLE_INVALID')
    va, length = values[DT_STRTAB], values[DT_STRSZ]
    if length > 2_000_000:
        raise Refused('ELF_DYNAMIC_STRING_TABLE_OVERSIZE')
    for p in info['ph']:
        if p[0] != PT_LOAD:
            continue
        _, poff, pvaddr, _, psz, _, _, _ = p
        if pvaddr <= va and va + length <= pvaddr + psz:
            tab = data[poff + va - pvaddr:poff + va - pvaddr + length]
            libs = []
            for n in needed_offsets:
                if n >= len(tab):
                    raise Refused('ELF_NEEDED_STRING_OUT_OF_BOUNDS')
                end = tab.find(b'\0', n)
                if end < 0:
                    raise Refused('ELF_NEEDED_STRING_UNTERMINATED')
                libs.append(tab[n:end].decode('ascii', errors='strict'))
            return libs
    raise Refused('ELF_STRING_TABLE_VADDR_UNMAPPED')


def prepare(archive):
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tf:
        loader = lookup_member(tf, 'lib/ld-musl-armhf.so.1')
        busybox = lookup_member(tf, 'bin/busybox')
    ld = elf_metadata(loader)
    bb = elf_metadata(busybox)
    if ld['type'] != 3 or ld['interp'] is not None:
        raise Refused('LOADER_ELF_SHAPE_UNEXPECTED')
    if bb['interp'] != '/lib/ld-musl-armhf.so.1':
        raise Refused('BUSYBOX_INTERPRETER_UNEXPECTED')
    needed = needed_libraries(busybox, bb)
    if needed != ['libc.musl-armv7.so.1']:
        raise Refused('BUSYBOX_DEPENDENCY_SET_UNEXPECTED')
    items = {'ld-musl-armhf.so.1': loader,
             'libc.musl-armv7.so.1': loader,
             'busybox': busybox}
    if sum(len(v) for v in items.values()) > 8_388_608:
        raise Refused('STAGING_TOO_LARGE')
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w', format=tarfile.USTAR_FORMAT) as tf:
        for name, data in sorted(items.items()):
            m = tarfile.TarInfo(name)
            m.mode = 0o500
            m.uid = m.gid = 0
            m.mtime = 0
            m.size = len(data)
            tf.addfile(m, io.BytesIO(data))
    return buf.getvalue(), items, needed


def remote_script(items):
    hashes = {name: sha256(data) for name, data in items.items()}
    return r'''set -fu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
umask 077
[ "$(uname -r 2>/dev/null)" = 3.0.35-lab126 ] || exit 40
[ "$(uname -m 2>/dev/null)" = armv7l ] || exit 40
[ -r /proc/mounts ] || exit 41
chosen=''
while read -r dev point fs opts other; do
  case "$point:$fs" in /tmp:tmpfs|/dev/shm:tmpfs|/run:tmpfs) : ;; *) continue ;; esac
  case ",$opts," in *,rw,*) : ;; *) continue ;; esac
  case ",$opts," in *,noexec,*) continue ;; esac
  [ -d "$point" ] && [ ! -L "$point" ] || continue
  chosen="$point"
  break
done < /proc/mounts
[ -n "$chosen" ] || exit 42
bb=''
for candidate in /bin/busybox /sbin/busybox /usr/bin/busybox /usr/sbin/busybox; do
  [ -x "$candidate" ] && { bb="$candidate"; break; }
done
[ -n "$bb" ] || exit 43
work="$chosen/pw3-r3877-78-$$"
mkdir "$work" || exit 44
cleanup() { rm -f "$work/ld-musl-armhf.so.1" "$work/libc.musl-armv7.so.1" "$work/busybox"; rmdir "$work"; }
trap 'cleanup' 0
trap 'exit 70' 1 2 3 15
"$bb" tar -xf - -C "$work" || exit 45
for item in ld-musl-armhf.so.1 libc.musl-armv7.so.1 busybox; do
  [ -f "$work/$item" ] && [ ! -L "$work/$item" ] || exit 46
  case "$item" in
    ld-musl-armhf.so.1) expected=HASH_LD ; bytes=BYTES_LD ;;
    libc.musl-armv7.so.1) expected=HASH_LIBC ; bytes=BYTES_LIBC ;;
    busybox) expected=HASH_BB ; bytes=BYTES_BB ;;
  esac
  actual_bytes=$(wc -c < "$work/$item") || exit 47
  [ "$actual_bytes" = "$bytes" ] || exit 47
  set -- $(sha256sum "$work/$item")
  [ "$1" = "$expected" ] || exit 48
done
chmod 500 "$work/ld-musl-armhf.so.1" "$work/busybox" || exit 49
ulimit -c 0 2>/dev/null || :
ulimit -t 5 2>/dev/null || :
unset LD_PRELOAD
LD_LIBRARY_PATH="$work" LC_ALL=C "$work/ld-musl-armhf.so.1" "$work/busybox" echo R3877_78_MUSL_BUSYBOX_OK || exit 50
cleanup || exit 51
trap - 0 1 2 3 15
exit 0'''.replace('HASH_LD', hashes['ld-musl-armhf.so.1']) \
        .replace('HASH_LIBC', hashes['libc.musl-armv7.so.1']) \
        .replace('HASH_BB', hashes['busybox']) \
        .replace('BYTES_LD', str(len(items['ld-musl-armhf.so.1']))) \
        .replace('BYTES_LIBC', str(len(items['libc.musl-armv7.so.1']))) \
        .replace('BYTES_BB', str(len(items['busybox'])))


REMOTE_EXIT = {
    40: 'TARGET_KERNEL_ARCH_MISMATCH', 41: 'MOUNT_INFO_MISSING',
    42: 'NO_EXECUTABLE_EXISTING_TMPFS', 43: 'STOCK_BUSYBOX_MISSING',
    44: 'TMPFS_WORKDIR_CREATE_FAILED', 45: 'TMPFS_TAR_STAGE_FAILED',
    46: 'TMPFS_MEMBER_TYPE_INVALID', 47: 'TMPFS_MEMBER_SIZE_MISMATCH',
    48: 'TMPFS_MEMBER_SHA256_MISMATCH', 49: 'TMPFS_EXEC_PERMISSION_FAILED',
    50: 'MUSL_LOADER_OR_BUSYBOX_EXECUTION_FAILED', 51: 'TMPFS_CLEANUP_FAILED',
    70: 'REMOTE_INTERRUPTED', 255: 'SSH_FAILED',
}


def main(argv=None, runner=subprocess.run):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rootfs-tar', default=ROOTFS_NAME)
    p.add_argument('--validate-archive-only', action='store_true')
    p.add_argument('--acknowledge-single-process-mac-and-kindle-tmpfs', action='store_true')
    p.add_argument('--target', default='root@192.168.8.102')
    p.add_argument('--port', type=int, default=2222)
    a = p.parse_args(argv)
    report = {'milestone': 'R3877.78.1', 'result': 'HOLD', 'immutable_hold': 'NOT_BOOTABLE',
              'hold_category': 'DEVICE_MUSL_TEST_NOT_AUTHORIZED',
              'archive_pinned_version': 'Alpine_3.24.2_armv7',
              'archive_sha256_verified': False, 'offline_validation_passed': False,
              'single_process_musl_verified': False,
              'physical_restore_verified': False, 'stock_boot_modified': False,
              'chroot_performed': False, 'mount_performed': False,
              'firmware_write_performed': False, 'device_execution_attempted': False}
    if not a.acknowledge_single_process_mac_and_kindle_tmpfs and not a.validate_archive_only:
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 2
    if not re.fullmatch(r'root@[A-Za-z0-9][A-Za-z0-9.\-]{0,252}', a.target) or not (1 <= a.port <= 65535):
        report['hold_category'] = 'TARGET_OR_PORT_INVALID'
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 2
    try:
        archive = read_pinned_archive(a.rootfs_tar)
        report['archive_sha256_verified'] = True
        payload, items, needed = prepare(archive)
        report['offline_armv7_elf_abi_verified'] = True
        report['offline_validation_passed'] = True
        report['busybox_exact_needed_libraries'] = needed
        report['loader_and_busybox_staging_bytes'] = sum(len(v) for v in items.values())
    except (OSError, ValueError, Refused, tarfile.TarError, UnicodeError, struct.error) as exc:
        report['hold_category'] = 'PINNED_ARCHIVE_OR_ELF_VALIDATION_REFUSED'
        if isinstance(exc, Refused):
            # Only approved fixed diagnostic labels, never file paths or hashes.
            report['offline_refusal_code'] = str(exc)
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 2
    if a.validate_archive_only:
        report['hold_category'] = 'OFFLINE_ELF_VALIDATION_PASS_DEVICE_RUNTIME_UNVERIFIED'
        report['offline_validation_passed'] = True
        report['device_execution_attempted'] = False
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 2
    cmd = ['ssh', '-T', '-o', 'ConnectTimeout=15', '-o', 'ConnectionAttempts=1',
           '-p', str(a.port), a.target, 'sh -c ' + shlex.quote(remote_script(items))]
    report['device_execution_attempted'] = True
    try:
        done = runner(cmd, input=payload, stdout=subprocess.PIPE,
                      stderr=subprocess.PIPE, timeout=70, check=False)
        report['ssh_exit_code'] = done.returncode
        if done.returncode == 0 and done.stdout == MARKER.encode():
            report['result'] = 'PASS_ALPINE_3_24_2_MUSL_BUSYBOX_SINGLE_PROCESS'
            report['hold_category'] = 'RECOVERY_AND_KOREADER_RUNTIME_STILL_UNVERIFIED'
            report['single_process_musl_verified'] = True
            report['tmpfs_cleanup_reported_complete'] = True
        else:
            report['hold_category'] = REMOTE_EXIT.get(done.returncode, 'REMOTE_OUTPUT_UNEXPECTED')
            report['tmpfs_cleanup_reported_complete'] = False
    except (OSError, subprocess.TimeoutExpired):
        report['hold_category'] = 'SSH_OR_TIMEOUT_FAILURE_CLEANUP_UNVERIFIED'
        report['tmpfs_cleanup_reported_complete'] = False
    print(json.dumps(report, sort_keys=True, separators=(',', ':')))
    return 0 if report['single_process_musl_verified'] else 2


if __name__ == '__main__':
    sys.exit(main())
