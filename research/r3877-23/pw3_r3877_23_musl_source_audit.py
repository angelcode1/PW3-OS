#!/usr/bin/env python3
"""PW3 R3877.23: source identity/fallback observations, host ONLY.

Never connects to, writes to, or runs code on a Kindle.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

MILESTONE = 'R3877.23'
EXPECTED_IMAGE = 'sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a'
EXPECTED_LOADER_SHA256 = '2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990'
EXPECTED_MUSL_VERSION = '1.2.6-r3'  # snapshot of the pinned Alpine aports commit, NOT inferred from image tag
EXPECTED_ARCH = 'armv7'
PINS = {
    'alpine_APKBUILD': ('alpinelinux/aports', '35f5eb2864e50dd4448758d31f3e2a32f733ab84', 'main/musl/APKBUILD', 'b729315a72d9060cc69ba9bddec53c0691c05158'),
    'clock_gettime.c': ('ifduyue/musl', 'v1.2.6', 'src/time/clock_gettime.c', '4d2ec22f38a0012867632c7fcea763f090246174'),
    '__timedwait.c': ('ifduyue/musl', 'v1.2.6', 'src/thread/__timedwait.c', '666093be98516a1c84b2997f075a8dbfcb797b2c'),
    'getrandom.c': ('ifduyue/musl', 'v1.2.6', 'src/linux/getrandom.c', '6cc6f6b047c18c9c8c564b5ece3f80a2f2b1f65f'),
    'fstatat.c': ('ifduyue/musl', 'v1.2.6', 'src/stat/fstatat.c', '9eed063b26bcfb1a0d52b700d153ac3ad718774f'),
    'arm_syscall.h.in': ('ifduyue/musl', 'v1.2.6', 'arch/arm/bits/syscall.h.in', 'fb5fa9754a4fac8205318de88c552552778d2ad3'),
    'arm_syscall_arch.h': ('ifduyue/musl', 'v1.2.6', 'arch/arm/syscall_arch.h', '624e992e1ac9cbaddc6e35fa24c9ab784067a76f'),
}
EXPECTED_NR = {'futex':240,'clock_gettime32':263,'renameat2':382,'getrandom':384,'statx':397,'clock_gettime64':403,'futex_time64':422,'clone3':435,'openat2':437}

class AuditHold(Exception):
    pass


def sha_git_blob(data):
    return hashlib.sha1(f'blob {len(data)}\0'.encode('ascii') + data).hexdigest()


def limited_read(path, cap=65536):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > cap:
        raise AuditHold('FILE_MISSING_SYMLINK_OR_OVERSIZED')
    return path.read_bytes()


def analyze_source_dir(root, pins=PINS):
    contents = {}
    hashes = {}
    for name, (_repo, _ref, _path, expected) in pins.items():
        try:
            data = limited_read(root / name)
        except (OSError, AuditHold):
            raise AuditHold('PINNED_SOURCE_MISSING_OR_INVALID_' + name.replace('.','_'))
        got = sha_git_blob(data)
        if got != expected:
            raise AuditHold('PINNED_SOURCE_GIT_BLOB_MISMATCH_' + name.replace('.','_'))
        contents[name] = data.decode('utf-8')
        hashes[name] = got
    return classify_source(contents, hashes)


def expect(src, tokens, failure):
    if not all(t in src for t in tokens):
        raise AuditHold(failure)


def classify_source(c, hashes=None):
    apk=c['alpine_APKBUILD']
    m=re.search(r'^pkgver=(\d+\.\d+\.\d+)\s*$',apk,re.M)
    r=re.search(r'^pkgrel=(\d+)\s*$',apk,re.M)
    if not m or not r or f'{m.group(1)}-r{r.group(1)}'!=EXPECTED_MUSL_VERSION:
        raise AuditHold('PINNED_APKBUILD_VERSION_UNEXPECTED')
    if 'CVE-2026-107891.patch' not in apk:
        raise AuditHold('DOWNSTREAM_PATCH_LIST_UNEXPECTED')
    clock=c['clock_gettime.c']
    expect(clock,['SYS_clock_gettime64','SYS_clock_gettime','r!=-ENOSYS','__syscall(SYS_clock_gettime, clk, ts32)'],'CLOCK_FALLBACK_TOKENS_ABSENT')
    wait=c['__timedwait.c']
    expect(wait,['SYS_futex_time64','SYS_futex','r!=-ENOSYS','__syscall_cp(SYS_futex, addr','CLAMP(s)'],'FUTEX_FALLBACK_TOKENS_ABSENT')
    stat=c['fstatat.c']
    expect(stat,['fstatat_statx','ret!=-ENOSYS','fstatat_kstat'],'STATX_FALLBACK_TOKENS_ABSENT')
    rand=c['getrandom.c']
    expect(rand,['syscall_cp(SYS_getrandom, buf, buflen, flags)'],'GETRANDOM_WRAPPER_UNEXPECTED')
    # Scope this conclusion to this function, not to callers or applications.
    if 'ENOSYS' in rand or '/dev/urandom' in rand:
        raise AuditHold('GETRANDOM_WRAPPER_SEMANTICS_CHANGED')
    nums={}
    for name,number in EXPECTED_NR.items():
        m=re.search(r'^#define\s+__NR_'+re.escape(name)+r'\s+(\d+)\s*$',c['arm_syscall.h.in'],re.M)
        if not m or int(m.group(1))!=number:
            raise AuditHold('ARM_SYSCALL_NUMBER_UNEXPECTED_'+name)
        nums[name]=number
    expect(c['arm_syscall_arch.h'], ['VDSO_CGT32_SYM', 'VDSO_CGT_SYM'], 'ARM_VDSO_SOURCE_UNEXPECTED')
    return {
        'upstream_git_blob_pins_verified':bool(hashes),
        'source_blob_sha1_by_file':hashes or {},
        'alpine_aports_snapshot_package_version':EXPECTED_MUSL_VERSION,
        'alpine_aports_downstream_patches_present':True,
        'arm_syscall_numbers_from_musl_header':nums,
        'clock_gettime_legacy_fallback_source_present':True,
        'timed_futex_legacy_fallback_source_present':True,
        'fstatat_statx_to_legacy_fallback_source_present':True,
        'getrandom_wrapper_has_no_internal_enosys_fallback':True,
        'getrandom_application_fallbacks_not_checked':True,
        'conditional_compilation_and_arm_runtime_not_verified':True,
    }


def extract_musl_stanza(data):
    # apk installed DB uses blank-line-separated package records, P:/V:/A: keys.
    for stanza in data.decode('utf-8').split('\n\n'):
        lines=dict(line.split(':',1) for line in stanza.splitlines() if len(line)>=2 and line[1]==':')
        if lines.get('P')=='musl':
            return {k:lines.get(k) for k in ('P','V','A')}
    raise AuditHold('CANDIDATE_APK_DB_MUSL_RECORD_MISSING')


def analyze_candidate(root, expected_image=EXPECTED_IMAGE, expected_version=EXPECTED_MUSL_VERSION, expected_loader_sha256=EXPECTED_LOADER_SHA256):
    try:
        iid=limited_read(root/'image-id.txt',256).decode('ascii').strip()
        apk=limited_read(root/'installed.db',2*1024*1024)
        loader=limited_read(root/'loader',16*1024*1024)
    except (OSError, AuditHold, UnicodeError):
        raise AuditHold('CANDIDATE_IMAGE_FILES_MISSING_OR_INVALID')
    if iid != expected_image:
        raise AuditHold('CANDIDATE_IMAGE_ID_BASELINE_MISMATCH')
    pkg=extract_musl_stanza(apk)
    if pkg.get('V') != expected_version:
        raise AuditHold('CANDIDATE_MUSL_VERSION_DIFFERS_FROM_PINNED_APORTS')
    if pkg.get('A') != EXPECTED_ARCH:
        raise AuditHold('CANDIDATE_MUSL_ARCH_UNEXPECTED')
    digest=hashlib.sha256(loader).hexdigest()
    if digest != expected_loader_sha256:
        raise AuditHold('CANDIDATE_MUSL_LOADER_SHA256_MISMATCH')
    if loader[:4]!=b'\x7fELF' or loader[4]!=1 or loader[5]!=1 or loader[18:20]!=b'\x28\x00':
        raise AuditHold('CANDIDATE_MUSL_LOADER_NOT_ELF32_ARM')
    return {'candidate_image_id':iid,'installed_musl_version':pkg['V'],
            'installed_musl_arch':pkg['A'],'loader_sha256':digest,
            'candidate_musl_metadata_and_previous_hash_match':True,
            'patched_built_binary_equivalence_not_proven':True}


def main(argv=None):
    p=argparse.ArgumentParser(description='Host-only pinned musl source audit. No Kindle operations.')
    p.add_argument('--source-dir',default='sources')
    p.add_argument('--candidate-dir',default='candidate')
    p.add_argument('--require-candidate',action='store_true')
    a=p.parse_args(argv)
    report={'milestone':MILESTONE, 'result':'HOLD', 'hold_category':'NOT_BOOTABLE',
      'immutable_hold':'NOT_BOOTABLE','kindle_ssh_sessions':0, 'physical_device_access_performed':False,
      'new_kindle_binary_installed_or_executed':False,'firmware_write_performed':False,
      'original_r13_stage_accessed':False,'recovery_verified':False,
      'vendor_kernel_dispatch_verified':False,'target_musl_runtime_verified':False,
      'alpine_application_syscall_requirements_verified':False,
      'binary_provenance_to_patched_source_verified':False,
      'kernel_time64_and_getrandom_fallbacks_runtime_verified':False}
    try:
        report['source_audit']=analyze_source_dir(Path(a.source_dir))
        path=Path(a.candidate_dir)
        if path.is_dir():
            report['candidate_audit']=analyze_candidate(path)
            report['result']='PASS_PINNED_MUSL_SOURCE_AND_CANDIDATE_METADATA_ONLY'
        elif a.require_candidate:
            raise AuditHold('CANDIDATE_IMAGE_METADATA_REQUIRED')
        else:
            report['candidate_audit']={'status':'NOT_COLLECTED'}
            report['result']='PASS_PINNED_UPSTREAM_MUSL_SOURCE_ONLY'
    except AuditHold as e:
        report['result']='HOLD'
        report['hold_category']=str(e)
    except (OSError, UnicodeError, ValueError):
        report['result']='HOLD'
        report['hold_category']='INPUT_FILE_INVALID'
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0 if report['result'].startswith('PASS_') else 2

if __name__=='__main__':sys.exit(main())
