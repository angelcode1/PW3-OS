#!/usr/bin/env python3
"""R3877.28: pinned recipe snapshot, patched-tree and signed APK metadata audit.

Host-only. No rebuilds, compiler invocation, guest execution, Docker, SSH or Kindle changes.
Build-recipe versions in aports are *NOT* proof of the historical builder versions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import pw3_r3877_26_aports_input_audit as r26
import pw3_r3877_27_patched_tree_fingerprint as r27
import pw3_r3877_24_public_apk_loader_match as r24
import pw3_r3877_25_signed_apk_provenance as r25

MILESTONE = 'R3877.28'
PINS = 'R3877_28_PINNED_BUILD_RECIPE_BLOBS.json'
EXPECTED_COMMIT = '35f5eb2864e50dd4448758d31f3e2a32f733ab84'
EXPECTED_TREE = '61bc0d7c9559ffb9c6d1f25a40f041a04391bd2960a0176ac65cc9fe4aae7b8e'
EXPECTED_MUSL_RECIPE_SHA1 = 'b729315a72d9060cc69ba9bddec53c0691c05158'
MAX_RECIPE = 1024 * 1024


def require(condition, code):
    if not condition:
        raise r26.AuditHold(code)


def safe_pins(pins):
    require(isinstance(pins, dict) and pins.get('alpine_aports_commit') == EXPECTED_COMMIT,
            'UNEXPECTED_APORTS_SNAPSHOT')
    require(pins.get('expected_patched_tree_sha256') == EXPECTED_TREE,
            'UNEXPECTED_PATCHED_TREE_PIN')
    expected = {'build-base', 'gcc', 'binutils', 'make', 'abuild'}
    records = pins.get('snapshot_recipe_git_blobs')
    require(isinstance(records,dict) and set(records) == expected, 'RECIPE_SET_INVALID')
    for k, record in records.items():
        require(record.get('path') == f'main/{k}/APKBUILD' and
                re.fullmatch('[0-9a-f]{40}', str(record.get('git_blob_sha1', ''))) and
                re.fullmatch('[0-9A-Za-z.]+-r[0-9]+', str(record.get('version', ''))),
                'RECIPE_PIN_RECORD_INVALID')
    # Every individual pin is immutable in the audit, not just the file itself.
    known = {'build-base':('862243111685766848fe529178cf6a8504577c97','0.5-r4'),
             'gcc':('de97708e6ba1e5f868d635f39a0050e7bc418b05','15.2.0-r5'),
             'binutils':('59b9bcf6aee1d5898bdf282c7b11277ee56c4a6a','2.45.1-r1'),
             'make':('99115a0bb4ac709dd77f74a82f75c182cec7d448','4.4.1-r4'),
             'abuild':('0978e9fa2cd31cfceefde0e930258be6ddcbbad7','3.17.0-r0')}
    require(all((records[k]['git_blob_sha1'],records[k]['version']) == known[k] for k in expected),
            'RECIPE_PIN_VALUES_MISMATCH')
    return records


def pkgver_from_recipe(src):
    try:
        text=src.decode('utf-8', errors='strict')
    except UnicodeError:
        raise r26.AuditHold('RECIPE_NOT_UTF8') from None
    v=re.search(r'^pkgver=([0-9A-Za-z.]+)\s*$',text,re.M)
    rel=re.search(r'^pkgrel=([0-9]+)\s*$',text,re.M)
    require(v is not None and rel is not None,'RECIPE_VERSION_NOT_LITERAL')
    return v.group(1)+'-r'+rel.group(1)


def check_recipes(directory, records):
    require(directory.is_dir(),'RECIPE_DIRECTORY_MISSING')
    result={}
    for name in sorted(records):
        p=directory/(name+'.APKBUILD')
        require(p.is_file() and not p.is_symlink(),'RECIPE_FILE_MISSING_OR_SYMLINK')
        raw=r24.read_bounded(p,MAX_RECIPE,'RECIPE_'+name)
        require(r26.git_blob(raw)==records[name]['git_blob_sha1'], 'RECIPE_GIT_BLOB_MISMATCH_'+name)
        version=pkgver_from_recipe(raw)
        require(version == records[name]['version'], 'RECIPE_VERSION_MISMATCH_'+name)
        result[name]={'snapshot_recipe_version':version,
                      'git_blob_sha1':records[name]['git_blob_sha1'],
                      'historical_builder_package_version_verified':False}
        if name == 'build-base':
            require(b'binutils file gcc g++ make libc-dev fortify-headers patch' in raw,
                    'BUILD_BASE_DEPENDENCY_LINE_MISMATCH')
    return result


def verify_r27_inputs(source_dir, manifest_path, expected_path):
    manifest=r26.load_manifest(manifest_path)
    raw,_ = r26.check_inputs(source_dir,manifest)
    pin=json.loads(expected_path.read_text('utf-8'))
    require(pin.get('milestone')=='R3877.27' and
            pin.get('source_git_snapshot')==EXPECTED_COMMIT, 'PATCHED_SHA_BASELINE_INVALID')
    expected=pin['expected']
    patch_inputs=[(e['name'],raw[e['name']]) for e in manifest['entries'] if e['role']=='patch']
    changed,_,_=r27.reconstruct_changed_blobs(raw[manifest['source_tarball']],patch_inputs)
    require({k:hashlib.sha256(v).hexdigest() for k,v in changed.items()}==expected,
            'PATCHED_FILE_HASH_MISMATCH')
    digest=r27.source_tree_manifest(raw[manifest['source_tarball']],changed)['canonical_patched_source_tree_sha256']
    require(digest==EXPECTED_TREE,'PATCHED_TREE_DIGEST_MISMATCH')
    return digest


def read_signed_package_info(apk):
    parts=r24.gzip_members(apk)
    require(len(parts)==3, 'APK_STREAM_COUNT_INVALID')
    files=r24.tar_files(parts[1][1])
    require('.PKGINFO' in files,'PKGINFO_NOT_IN_CONTROL')
    try: text=files['.PKGINFO'].decode('utf-8',errors='strict')
    except UnicodeError: raise r26.AuditHold('PKGINFO_NOT_UTF8') from None
    result={}
    wanted={'pkgname','pkgver','arch','builddate','commit','origin','datahash'}
    for line in text.splitlines():
        if line.startswith('#') or not line.strip():continue
        if ' = ' not in line: continue
        k,v=line.split(' = ',1)
        if k in wanted:
            require(k not in result,'PKGINFO_DUPLICATE_'+k)
            require(len(v)<=128,'PKGINFO_VALUE_TOO_LONG')
            result[k]=v
    require(result.get('pkgname')=='musl' and result.get('pkgver')=='1.2.6-r3'
            and result.get('arch')=='armv7','PKGINFO_PACKAGE_IDENTITY_MISMATCH')
    require(result.get('origin') in (None,'musl'),'PKGINFO_ORIGIN_DIFFERENT')
    if 'builddate' in result: require(re.fullmatch('[0-9]{9,12}',result['builddate']), 'PKGINFO_BUILD_DATE_INVALID')
    if 'commit' in result: require(re.fullmatch('[0-9a-f]{40}',result['commit']), 'PKGINFO_COMMIT_FORMAT_INVALID')
    return {'declared_builddate_utc_epoch':result.get('builddate'),
            'declared_aports_commit':result.get('commit'),
            'declared_source_commit_matches_pinned_snapshot':
                result.get('commit') == EXPECTED_COMMIT if result.get('commit') else None,
            'package_commit_field_present':bool(result.get('commit'))}


def base():
    return {'milestone':MILESTONE,'result':'HOLD','hold_category':'INPUTS_NOT_VERIFIED',
            'immutable_hold':'NOT_BOOTABLE','kindle_ssh_sessions':0,
            'new_kindle_binary_installed_or_executed':False,'boot_performed':False,
            'firmware_write_performed':False,'original_r13_stage_accessed':False,
            'physical_device_access_performed':False,'recovery_verified':False,
            'candidate_image_id_expected':r24.IMAGE_ID,
            'signed_loader_rebuild_performed':False,
            'signed_loader_rebuild_byte_match_verified':False,
            'historical_alpine_builder_toolchain_versions_verified':False,
            'historical_alpine_builder_cflags_ldflags_verified':False,
            'build_environment_equivalence_verified':False,
            'binary_provenance_to_patched_source_verified':False,
            'target_musl_runtime_verified':False,'vendor_kernel_dispatch_verified':False}


def main(argv=None):
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--source-dir')
    a.add_argument('--recipe-dir')
    a.add_argument('--apk')
    a.add_argument('--index')
    a.add_argument('--candidate-loader')
    a.add_argument('--key-dir')
    a.add_argument('--pin-manifest',default=str(Path(__file__).with_name(PINS)))
    a.add_argument('--source-manifest',default=str(Path(__file__).with_name(r26.MANIFEST_NAME)))
    a.add_argument('--patched-sha-file',default=str(Path(__file__).with_name('R3877_27_EXPECTED_PATCHED_SHA256.json')))
    args=a.parse_args(argv)
    report=base()
    try:
        require(all((args.source_dir,args.recipe_dir,args.apk,args.index,args.candidate_loader,args.key_dir)),
                'MISSING_EXPLICIT_LOCAL_INPUTS')
        pins=json.loads(Path(args.pin_manifest).read_text('utf-8'))
        recipe_pins=safe_pins(pins)
        recipes=check_recipes(Path(args.recipe_dir),recipe_pins)
        source_hash=verify_r27_inputs(Path(args.source_dir),Path(args.source_manifest),Path(args.patched_sha_file))
        apk=r24.read_bounded(args.apk,r24.MAX_APK_BYTES,'APK')
        index=r24.read_bounded(args.index,r24.MAX_INDEX_BYTES,'INDEX')
        loader=r24.read_bounded(args.candidate_loader,r24.MAX_LOADER_BYTES,'CANDIDATE_LOADER')
        require(hashlib.sha256(apk).hexdigest()=='9fca75b09538f9788b1ca800d56cd93dd4d584fac76a57c959666a9a0b93d397',
                'PUBLISHED_PACKAGE_SHA256_CHANGED_FROM_R3877_25')
        authentic=r25.audit_authenticity(apk,index,loader,Path(args.key_dir))
        info=read_signed_package_info(apk)
        report['inventory']={
            'pinned_aports_snapshot':EXPECTED_COMMIT,
            'canonical_patched_source_tree_sha256':source_hash,
            'patched_source_tree_reverified_this_run':True,
            'source_tarball_and_patches_reverified_this_run':True,
            'public_alpine_index_signature_verified_this_run':authentic['index']['signature_verified'],
            'public_alpine_apk_signature_verified_this_run':authentic['apk']['signature_verified'],
            'cached_loader_matches_signed_public_package':authentic['candidate_loader_byte_for_byte_match'],
            'public_package_sha256':authentic['package_sha256'],
            'aports_snapshot_recipe_versions_not_builder_installed_versions':recipes,
            'alpine_musl_build_recipe_blob_sha1':EXPECTED_MUSL_RECIPE_SHA1,
            'alpine_musl_build_recipe_uses_host_CHOST':True,
            'alpine_musl_build_recipe_adjusts_CFLAGS':True,
            'alpine_musl_build_recipe_sets_LDFLAGS_soname':True,
            'actual_historical_build_flags_identified':False,
            'historical_builder_compiler_identity_verified':False,
            'historical_builder_linker_identity_verified':False,
            'historical_builder_abuild_identity_verified':False,
            'aports_snapshot_is_historical_builder_snapshot_proven':False,
            **info}
        report.update(result='PASS_PINNED_RECIPES_AND_SIGNED_PACKAGE_BUILD_METADATA_ONLY',hold_category='NOT_BOOTABLE')
        code=0
    except (r26.AuditHold,r24.Refusal,ValueError,TypeError,KeyError,OSError,MemoryError,UnicodeError) as e:
        report['hold_category']=(str(e) if isinstance(e,(r26.AuditHold,r24.Refusal)) else 'HOST_INPUT_OR_PARSE_FAILED')[:128]
        code=2
    print(json.dumps(report,indent=2,sort_keys=True))
    return code

if __name__=='__main__': sys.exit(main())
