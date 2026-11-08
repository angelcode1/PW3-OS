#!/usr/bin/env python3
"""R3877.55: pinned Alpine BusyBox recipe and upstream seedrng source only.

Offline unless an operator separately downloads public source. Never Docker,
Kindle SSH, ARM execution, firmware access, boot or syscalls. NOT_BOOTABLE.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

MILESTONE='R3877.55'
SOURCE_ROOT='https://raw.githubusercontent.com'
ALPINE_REV='35f5eb2864e50dd4448758d31f3e2a32f733ab84'
BUSYBOX_REV='1_37_0'
BUSYBOX_HASH='df4dd71f89214032872e60328f3af03faf35e344f6fa5493656d8775d35e930c'
LOADER_HASH='2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990'
PINNED={
 'alpine/APKBUILD': ('alpinelinux/aports',ALPINE_REV,'main/busybox/APKBUILD','8b0ce27e089dcabb2b16b78c556ecc65a7c292cb'),
 'alpine/busyboxconfig': ('alpinelinux/aports',ALPINE_REV,'main/busybox/busyboxconfig','f94784573735b83ad7129c92ef37c170a676bf8e'),
 'alpine/busyboxconfig-extras': ('alpinelinux/aports',ALPINE_REV,'main/busybox/busyboxconfig-extras','2345ed1f3d651132d13c7b5b0df7008d0e5583ec'),
 'busybox/miscutils/seedrng.c': ('vda-linux/busybox_mirror',BUSYBOX_REV,'miscutils/seedrng.c','7a2331cb18b96b00116de54a21ebbd401fa1e3f2'),
 'busybox/shell/random.c': ('vda-linux/busybox_mirror',BUSYBOX_REV,'shell/random.c','56c7c5a3c88f7fd539fd152c991f09cdc076d892'),
}

class AuditHold(Exception):
    pass

def git_blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def read_limited(path, maxbytes=131072):
    path=Path(path)
    if path.is_symlink() or not path.is_file():
        raise AuditHold('INPUT_MISSING_OR_SYMLINK')
    size=path.stat().st_size
    if not 1<=size<=maxbytes:
        raise AuditHold('INPUT_SIZE_INVALID')
    return path.read_bytes()

def check_source(source_dir, pins=PINNED):
    files={}
    hashes={}
    for key,(_,_,_,expected) in pins.items():
        raw=read_limited(Path(source_dir)/key)
        computed=git_blob(raw)
        if computed!=expected:
            raise AuditHold('GIT_BLOB_MISMATCH_'+key.replace('/','_').replace('.','_'))
        hashes[key]=computed
        try: files[key]=raw.decode('utf-8')
        except UnicodeDecodeError as e: raise AuditHold('SOURCE_UTF8_INVALID') from e
    apk=files['alpine/APKBUILD']
    if not re.search(r'^pkgver=1\.37\.0\s*$',apk,re.M) or not re.search(r'^pkgrel=31\s*$',apk,re.M):
        raise AuditHold('ALPINE_BUSYBOX_RECIPE_VERSION_CHANGED')
    if 'cp "$_config" .config' not in apk or 'install -Dm755 busybox "$pkgdir"/bin/busybox' not in apk:
        raise AuditHold('ALPINE_BUSYBOX_CONFIG_LINKAGE_UNVERIFIED')
    statuses={}
    for k in ('alpine/busyboxconfig','alpine/busyboxconfig-extras'):
        s=files[k]
        seed=re.findall(r'^(?:CONFIG_SEEDRNG=.*|# CONFIG_SEEDRNG is not set)\s*$',s,re.M)
        random=re.findall(r'^(?:CONFIG_ASH_RANDOM_SUPPORT=.*|# CONFIG_ASH_RANDOM_SUPPORT is not set)\s*$',s,re.M)
        if len(seed)!=1 or seed[0].strip()!='# CONFIG_SEEDRNG is not set':
            raise AuditHold('ALPINE_SEEDRNG_NOT_DISABLED_'+k.split('/')[-1])
        if len(random)!=1:
            raise AuditHold('ALPINE_ASH_RANDOM_CONFIG_MISSING')
        statuses[k.split('/')[-1]]={'seedrng_enabled':False,'ash_random_support_enabled':random[0].strip()=='CONFIG_ASH_RANDOM_SUPPORT=y'}
    if statuses['busyboxconfig']['ash_random_support_enabled'] is not True:
        raise AuditHold('ALPINE_NORMAL_ASH_RANDOM_UNEXPECTED')
    if statuses['busyboxconfig-extras']['ash_random_support_enabled'] is not False:
        raise AuditHold('ALPINE_EXTRAS_ASH_RANDOM_UNEXPECTED')
    seed=files['busybox/miscutils/seedrng.c']
    for marker in ('//kbuild:lib-$(CONFIG_SEEDRNG) += seedrng.o',
                   'ret = getrandom(seed, len, GRND_NONBLOCK)',
                   'ret < 0 && errno == ENOSYS',
                   'open_read_close("/dev/urandom", seed, len)'):
        if marker not in seed:
            raise AuditHold('UPSTREAM_SEEDRNG_SOURCE_CHANGED')
    shell=files['busybox/shell/random.c']
    for marker in ('next_random(random_t *rnd)','INIT_RANDOM_T(rnd, getpid(), monotonic_us())'):
        if marker not in shell:
            raise AuditHold('UPSTREAM_ASH_RANDOM_SOURCE_CHANGED')
    return {'verified_source_git_blob_count':len(files),'source_git_blob_sha1_by_path':hashes,
            'source_recipe_busybox_version':'1.37.0-r31',
            'source_recipe_config_status':statuses,
            'upstream_seedrng_getrandom_enosys_to_urandom_fallback_in_source':True,
            'source_recipe_seedrng_disabled':True,
            'source_seedrng_fallback_not_enabled_by_pinned_alpine_recipe':True,
            'ash_random_generator_source_present':True,
            'ash_random_is_not_a_cryptographic_entropy_fallback':True,
            'installed_busybox_exact_recipe_build_verified':False,
            'all_application_entropy_paths_verified':False}

def check_prior(report):
    try:r=json.loads(read_limited(report,16384))
    except (UnicodeError,ValueError) as e:raise AuditHold('PRIOR_R54_JSON_INVALID') from e
    if r.get('milestone')!='R3877.54' or r.get('result')!='PASS_PINNED_BUSYBOX_DIRECT_ELF_ENTROPY_INDICATORS_ONLY':
        raise AuditHold('PRIOR_R54_RESULT_CHANGED')
    audit=r.get('binary_audit')
    if not isinstance(audit,dict) or audit.get('direct_getrandom_dynamic_import_present') is not False or audit.get('direct_getentropy_dynamic_import_present') is not False or audit.get('dynamic_import_table_readable') is not True:
        raise AuditHold('PRIOR_R54_IMPORT_EVIDENCE_CHANGED')
    if audit.get('embedded_byte_marker_present',{}).get('/dev/urandom') is not True or audit.get('interesting_undefined_imports',{}).get('syscall') is not True:
        raise AuditHold('PRIOR_R54_ENTROPY_INDICATORS_CHANGED')
    l=audit.get('linkage',{})
    if l.get('busybox_sha256')!=BUSYBOX_HASH or l.get('loader_sha256')!=LOADER_HASH:
        raise AuditHold('PRIOR_R54_PINNED_BINARY_IDENTITY_CHANGED')
    if r.get('original_image_unchanged') is not True or r.get('stopped_container_removed') is not True or r.get('immutable_hold')!='NOT_BOOTABLE':
        raise AuditHold('PRIOR_R54_ISOLATION_OR_HOLD_CHANGED')
    return {'prior_observed_busybox_sha256':BUSYBOX_HASH,
            'prior_observed_loader_sha256':LOADER_HASH,
            'prior_busybox_imports_syscall':True,
            'prior_busybox_direct_getrandom_and_getentropy_imports_absent':True,
            'prior_busybox_urandom_string_present':True,
            'prior_elf_string_or_import_not_runtime_proof':True}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir')
    parser.add_argument('--r54-report')
    a=parser.parse_args(argv)
    result={'milestone':MILESTONE,'result':'HOLD','hold_category':'INPUTS_REQUIRED',
        'immutable_hold':'NOT_BOOTABLE','arm_executable_launched':False,'docker_used':False,
        'kindle_ssh_sessions':0,'physical_device_access_performed':False,'firmware_write_performed':False,
        'boot_performed':False,'target_musl_linux_3_0_35_compatibility_verified':False,
        'recovery_verified':False,'application_entropy_fallback_verified':False,
        'installed_busybox_exact_recipe_build_verified':False}
    if a.source_dir is None or a.r54_report is None:
        print(json.dumps(result,sort_keys=True));return 2
    try:
        source=check_source(a.source_dir)
        prior=check_prior(a.r54_report)
        result.update(source_audit=source,prior_elf_audit=prior,
             result='PASS_PINNED_ALPINE_BUSYBOX_SEEDRNG_DISABLED_AND_UPSTREAM_FALLBACK_SOURCE_ONLY',
             hold_category='NOT_BOOTABLE')
    except (AuditHold,OSError,ValueError) as e:
        result['hold_category']=str(e) if isinstance(e,AuditHold) else 'INPUT_READ_OR_PARSE_ERROR'
    print(json.dumps(result,sort_keys=True,separators=(',',':')))
    return 0 if result['result'].startswith('PASS_') else 2

if __name__=='__main__':sys.exit(main())