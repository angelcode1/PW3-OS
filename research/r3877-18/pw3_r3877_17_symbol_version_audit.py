#!/usr/bin/env python3
"""R3877.17 - read-only KOReader and stock-glibc GNU symbol version name audit.
No target executable launched, no writes, no system binary executed on Kindle.
"""
import argparse
import hashlib
import json
import sys
from r3877_17_version_parser import VersionHold, parse_version_sections, normalize_interp
import pw3_r3877_15_koreader_elf_audit as app
import pw3_r3877_16_system_elf_audit as syslib

EXPECTED_TARGET=app.EXPECTED_TARGET
assert EXPECTED_TARGET==syslib.EXPECTED_TARGET
EXPECTED_SHA={
    'fbink':'f6f70557d351657f7e4900b61dfc89d7068e72a9fc0710e6a8ff6e8223bfbe56',
    'luajit':'b830a60c2d0b0e64de37f20d18595990d5e408f945d2af4c0ea3181a13ed7f1c',
    'libc.so.6':'cdc61ca432e922abe8a2272987912c1332da5336d2fb7881c6d3174b6f131b05',
}
class Hold(Exception): pass

def analyze(appfiles,systemfiles):
    binaries={}
    for path,(kind,content) in appfiles.items():
        if kind=='file': binaries['koreader/'+path]=content
        elif kind=='symlink': pass # aliases represented by installed names below
        else: raise Hold('INVALID_APP_ARCHIVE_TYPE')
    for path,content in systemfiles.items():
        binaries['system/'+path]=content
    if len(binaries)<40 or len(systemfiles)!=7:
        raise Hold('BINARY_SET_INCOMPLETE')
    metadata={}
    nobits_count_total=0
    nobits_non_file_extent_paths=[]
    for path,blob in sorted(binaries.items()):
        ident=app.inspect_elf(blob)
        if ident['kind']!='ELF32_ARM' or ident['eabi_version']!=5 or ident['float_abi']!='SOFT':
            raise Hold('INCOMPATIBLE_ELF_'+path.replace('/','_'))
        try:
            versions=parse_version_sections(blob)
            interpreter=normalize_interp(blob)
        except VersionHold as e:
            raise Hold('GNU_VERSION_PARSE_'+path.replace('/','_')+'_'+str(e)) from e
        nobits_count_total+=versions['nobits_section_count']
        if versions['nobits_non_file_extent_count']:
            nobits_non_file_extent_paths.append(path)
        metadata[path]={
            'source_sha256':hashlib.sha256(blob).hexdigest(),
            'size_bytes':len(blob),
            'soname':ident['soname'],
            'needed':ident['needed'],
            'pt_interp':interpreter,
            'version_requirements':versions['needs'],
            'version_definitions':versions['defines'],
            'version_sections_seen':versions['sections_seen']}
    # Ensure the current file set belongs to the same audited KOReader and system-glibc baseline.
    paths_by_file={path.rsplit('/',1)[1]:rec for path,rec in metadata.items()}
    for name,digest in EXPECTED_SHA.items():
        match=(metadata['koreader/'+name] if name in ('fbink','luajit') else
               next((rec for path,rec in metadata.items() if path.startswith('system/') and path.endswith('/'+name)),None))
        if match is None or match['source_sha256']!=digest:
            raise Hold('BASELINE_SHA256_CHANGED_'+name)
    providers={}
    # Providers are fixed to audited application libs and the seven stock system libraries.
    for path,rec in metadata.items():
        basename=path.rsplit('/',1)[1]
        labels=[basename]+rec['soname']
        for label in labels:
            if label in providers and providers[label]!=path:
                # If two DSOs claim a SONAME, resolution is context-dependent; fail closed.
                raise Hold('DUPLICATE_PROVIDER_NAME_'+label)
            providers[label]=path
    # Existing app library symlinks are only accepted if their target is a collected file.
    for path,(kind,target) in appfiles.items():
        if kind!='symlink': continue
        if '/' in target or target in ('.','..') or '..' in target: raise Hold('UNSAFE_APP_SYMLINK')
        dest='koreader/libs/'+target
        if dest not in metadata: raise Hold('UNRESOLVED_APP_SYMLINK_'+path)
        alias=path.rsplit('/',1)[1]
        if alias in providers and providers[alias]!=dest: raise Hold('DUPLICATE_APP_SYMLINK_PROVIDER')
        providers[alias]=dest
    unresolved_names={}
    absent_versions={}
    optional_weak_absences={}
    requirements=0
    per_provider={}
    for requester,rec in sorted(metadata.items()):
        for name,vers in rec['version_requirements'].items():
            requirements+=len(vers)
            if name not in providers:
                unresolved_names.setdefault(name,[]).append(requester)
                continue
            candidate=metadata[providers[name]]
            for version,weak in vers:
                if version not in candidate['version_definitions']:
                    dest=optional_weak_absences if weak else absent_versions
                    dest.setdefault(name,[]).append({'required_by':requester,'version':version})
            per_provider.setdefault(name,{'provider_file':providers[name],'required_versions':set()})['required_versions'].update(v for v,w in vers)
    for val in per_provider.values(): val['required_versions']=sorted(val['required_versions'])
    concise={
        'app_elf_count':sum(path.startswith('koreader/') for path in metadata),
        'stock_provider_elf_count':sum(path.startswith('system/') for path in metadata),
        'total_version_requirements':requirements,
        'nobits_section_count_total':nobits_count_total,
        'nobits_non_file_extent_paths':sorted(nobits_non_file_extent_paths),
        'versioned_requesting_files':sum(bool(v['version_requirements']) for v in metadata.values()),
        'provider_names_with_version_requirements':sorted(per_provider),
        'provider_requirement_summary':per_provider,
        'provider_names_absent':{k:sorted(set(v)) for k,v in sorted(unresolved_names.items())},
        'required_version_names_absent':{k:sorted(v,key=lambda z:(z['version'],z['required_by'])) for k,v in sorted(absent_versions.items())},
        'weak_version_names_absent':{k:sorted(v,key=lambda z:(z['version'],z['required_by'])) for k,v in sorted(optional_weak_absences.items())},
        'version_requirements_statically_satisfied':not unresolved_names and not absent_versions,
        'app_executable_interpreters':{k:metadata['koreader/'+k]['pt_interp'] for k in ('fbink','luajit')},
        'system_glibc_interpreter_normalized':next(v['pt_interp'] for p,v in metadata.items() if p.endswith('/libc.so.6')),
        'source_baseline_sha256_checked':sorted(EXPECTED_SHA),
        'runtime_dependency_resolution_verified':False,
        'symbol_exports_and_relocations_verified':False,
        'full_koreader_dependency_closure_verified':False,
        'source_snapshots_atomic':False,
    }
    return concise

def main(argv=None):
    parser=argparse.ArgumentParser(description='R3877.17 ELF symbol version names, readonly, NOT_BOOTABLE')
    parser.add_argument('--target')
    parser.add_argument('-p','--port',type=int,default=2222)
    parser.add_argument('--authorize-live-readonly-ssh',action='store_true')
    args=parser.parse_args(argv)
    record={'milestone':'R3877.17','result':'HOLD','hold_category':'EXPLICIT_READONLY_SSH_AUTHORIZATION_REQUIRED',
        'immutable_hold':'NOT_BOOTABLE','authorized_live_readonly_ssh':bool(args.authorize_live_readonly_ssh),
        'boot_performed':False,'firmware_write_performed':False,'device_files_written':False,
        'new_target_binaries_installed_or_executed':False,'original_r13_stage_accessed':False,
        'target_musl_runtime_verified':False,'target_kernel_syscall_compatibility_verified':False,
        'recovery_verified':False,'koreader_dependency_closure_verified':False,
        'personal_files_transferred':False,'app_and_stock_binary_contents_transferred':False}
    if args.authorize_live_readonly_ssh:
        try:
            if args.target!=EXPECTED_TARGET: raise Hold('UNEXPECTED_SSH_TARGET')
            if not 1<=args.port<=65535: raise Hold('SSH_PORT_INVALID')
            # Read-only, fixed file scope; no kernel, user files, or any new executable on target.
            appblob=app.remote_tar(args.target,args.port)
            systemblob=syslib.remote_tar(args.target,args.port)
            record['app_and_stock_binary_contents_transferred']=True
            appfiles=app.parse_archive(appblob)
            systemfiles=syslib.parse_archive(systemblob)
            record['inventory']=analyze(appfiles,systemfiles)
            if record['inventory']['version_requirements_statically_satisfied']:
                record['result']='PASS_VERSION_NAMES_METADATA_ONLY'
                record['hold_category']='NOT_BOOTABLE'
            else:
                record['hold_category']='MISSING_PROVIDER_OR_REQUIRED_SYMBOL_VERSION_NAME'
        except (Hold,app.Hold,syslib.Hold,VersionHold) as e:
            record['hold_category']=str(e)
        except Exception as e:
            record['hold_category']='UNEXPECTED_'+type(e).__name__
    print(json.dumps(record,sort_keys=True,indent=2))
    return 0 if record['result']=='PASS_VERSION_NAMES_METADATA_ONLY' else 2

if __name__=='__main__': sys.exit(main())
