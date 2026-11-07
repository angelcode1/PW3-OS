#!/usr/bin/env python3
"""R3877.18: single SSH read-only ELF relocations / symbol export candidates.

Read only existing, predetermined KOReader + seven stock ELF files. All symbol
analysis is done locally. This is not dynamic-linker emulation or runtime proof.
"""
import argparse
import hashlib
import subprocess
import json
import sys
from collections import Counter,deque
import pw3_r3877_17_2_single_ssh_audit as transport
import pw3_r3877_17_symbol_version_audit as earlier
import pw3_r3877_15_koreader_elf_audit as app
import r3877_18_binding_parser as parser
import r3877_18_1_ssh_diagnostic as diag

class Hold(Exception):
    pass

MAX_EXAMPLE_COUNT=35

def analyze(af,sf):
    prior=earlier.analyze(af,sf)  # The 174-version baseline must still pass.
    if not prior['version_requirements_statically_satisfied']:
        raise Hold('PREVIOUS_VERSION_NAME_BASELINE_NOT_SATISFIED')
    blobs={}
    for path,(kind,data) in af.items():
        if kind=='file': blobs['koreader/'+path]=data
    for path,data in sf.items(): blobs['system/'+path]=data
    records={}
    for path,b in sorted(blobs.items()):
        try: records[path]={**parser.parse(b),'needed':app.inspect_elf(b)['needed'],'soname':app.inspect_elf(b)['soname']}
        except parser.BindingHold as e:
            raise Hold('DYNAMIC_SYMBOL_PARSE_'+path.replace('/','_')+'_'+str(e)) from e
    providers={}
    for path,r in records.items():
        for name in [path.rsplit('/',1)[-1]]+r['soname']:
            if name in providers and providers[name]!=path: raise Hold('DUPLICATE_SONAME_'+name)
            providers[name]=path
    for path,(kind,target) in af.items():
        if kind!='symlink': continue
        dest='koreader/libs/'+target
        if dest not in records: raise Hold('UNRESOLVED_SYMLINK_'+path.replace('/','_'))
        alias=path.rsplit('/',1)[-1]
        if alias in providers and providers[alias]!=dest: raise Hold('COLLIDING_APP_ALIAS_'+alias)
        providers[alias]=dest
    reachable={}
    for path in records:
        visited=set()
        q=deque([path])
        while q:
            p=q.popleft()
            if p in visited: continue
            visited.add(p)
            for dep in records[p]['needed']:
                if dep not in providers: raise Hold('REQUIRED_PROVIDER_NOT_COLLECTED_'+dep)
                if providers[dep] not in visited: q.append(providers[dep])
        reachable[path]=visited
    # Candidate names come only from the explicit dependency graph. This is NOT
    # a model of glibc link-map order, dlopen, interposition or reloc values.
    missing=[]
    strong_total=weak_total=versioned_total=resolved_strong=resolved_weak=0
    total_rel=total_refs=total_dynsym=total_exports=total_undefined=0
    import_refs=0
    types=Counter()
    perfile={}
    for path,r in sorted(records.items()):
        total_rel+=r['reloc_count'];total_refs+=r['reloc_symbol_references']
        total_dynsym+=r['dynsym_count'];total_exports+=r['export_count'];total_undefined+=r['import_count']
        types.update({k:int(v) for k,v in r['relocation_types'].items()})
        bindings=r['relocated_imports']
        import_refs+=len(bindings)
        perfile[path]={'relocations':r['reloc_count'], 'relocation_import_symbols':len(bindings),
                       'exported_dynamic_symbols':r['export_count']}
        for imp in bindings:
            isweak=imp['bind']==2 or imp['version_weak']
            if isweak: weak_total+=1
            else: strong_total+=1
            if imp['version']: versioned_total+=1
            if imp['version_provider']:
                provider=providers.get(imp['version_provider'])
                possible=[provider] if provider and provider in reachable[path] else []
            else:
                possible=sorted(reachable[path])
            candidates=[]
            for source in possible:
                for exp in records[source]['exports']:
                    if exp['name']!=imp['name']: continue
                    if imp['version']:
                        if exp['version']!=imp['version']: continue
                    else:
                        if exp['version'] is not None and exp['version_hidden']: continue
                    # Only exact type matches, or STT_NOTYPE wildcard, are strong
                    # static candidates; TLS or IFUNC requires separate runtime proof.
                    if imp['typ'] and exp['typ'] and imp['typ']!=exp['typ']:continue
                    candidates.append(source)
                    break
            if candidates:
                if isweak: resolved_weak+=1
                else: resolved_strong+=1
            else:
                missing.append({'required_by':path,'symbol':imp['name'],
                                'version':imp['version'], 'version_provider':imp['version_provider'],
                                'weak':isweak, 'dynsym_type':imp['typ']})
    ensure_total=(total_rel>0 and import_refs>0)
    if not ensure_total: raise Hold('NO_RELOCATION_IMPORT_EVIDENCE')
    hard_missing=[m for m in missing if not m['weak']]
    weak_missing=[m for m in missing if m['weak']]
    return {
        'files_parsed':len(records), 'app_elf_count':prior['app_elf_count'],
        'stock_provider_elf_count':prior['stock_provider_elf_count'],
        'prior_version_names_statically_satisfied':True,
        'total_relocation_entries':total_rel,'relocation_symbol_references':total_refs,
        'unique_undefined_dynsym_symbols_referenced_by_allocated_relocations':import_refs,
        'strong_relocated_imports':strong_total,'weak_relocated_imports':weak_total,
        'versioned_relocated_imports':versioned_total,
        'strong_imports_with_export_candidates':resolved_strong,
        'weak_imports_with_export_candidates':resolved_weak,
        'strong_imports_without_export_candidates':len(hard_missing),
        'weak_imports_without_export_candidates':len(weak_missing),
        'strong_missing_samples':hard_missing[:MAX_EXAMPLE_COUNT],
        'weak_missing_samples':weak_missing[:MAX_EXAMPLE_COUNT],
        'dynamic_symbol_count_total':total_dynsym,
        'exported_dynamic_symbols_total':total_exports,
        'undefined_dynamic_symbols_total':total_undefined,
        'relocation_type_counts':dict(sorted(types.items(),key=lambda x:int(x[0]))),
        'per_file_counts':perfile,
        'all_strong_relocation_imports_have_static_candidates':not hard_missing,
        'runtime_bindings_verified':False,'relocation_application_verified':False,
        'glibc_load_order_verified':False,'dlopen_module_dependency_closure_verified':False,
        'koreader_dependency_closure_verified':False,'snapshots_atomic':False,
        'target_musl_runtime_verified':False,'kernel_syscall_compatibility_verified':False,
    }


def main(argv=None):
    ap=argparse.ArgumentParser(description='R3877.18 read-only static symbol/relocation candidate analysis')
    ap.add_argument('--target')
    ap.add_argument('-p','--port',type=int,default=2222)
    ap.add_argument('--authorize-live-readonly-ssh',action='store_true')
    ap.add_argument('--probe-ssh-only',action='store_true',help='one lightweight read-only SSH uname command; no ELF archive')
    ap.add_argument('--connect-timeout',type=int,default=20,help='SSH connect timeout in seconds, 5..60')
    args=ap.parse_args(argv)
    out={'milestone':'R3877.18.1','result':'HOLD','hold_category':'EXPLICIT_READONLY_SSH_AUTHORIZATION_REQUIRED',
         'immutable_hold':'NOT_BOOTABLE','authorized_live_readonly_ssh':bool(args.authorize_live_readonly_ssh),
         'ssh_sessions_requested':0,'app_and_stock_binary_contents_transferred':False,
         'personal_files_transferred':False,'device_files_written':False,
         'boot_performed':False,'firmware_write_performed':False,'new_target_binaries_installed_or_executed':False,
         'original_r13_stage_accessed':False,'koreader_dependency_closure_verified':False,
         'target_musl_runtime_verified':False,'target_kernel_syscall_compatibility_verified':False,
         'recovery_verified':False}
    if args.authorize_live_readonly_ssh:
        try:
            if args.target!=transport.EXPECTED_TARGET: raise Hold('UNEXPECTED_SSH_TARGET')
            if not 1<=args.port<=65535: raise Hold('SSH_PORT_INVALID')
            if not 5<=args.connect_timeout<=60: raise Hold('SSH_CONNECT_TIMEOUT_INVALID')
            out['ssh_sessions_requested']=1
            if args.probe_ssh_only:
                out['ssh_probe']=diag.probe_ssh_only(args.target,args.port,args.connect_timeout)
                out['result']='PASS_SSH_HANDSHAKE_ONLY'
                out['hold_category']='NOT_BOOTABLE'
                print(json.dumps(out,sort_keys=True,indent=2))
                return 0
            raw=diag.one_session_collect(args.target,args.port,args.connect_timeout)
            af,sf=transport.parse_concatenated_archives(raw)
            out['app_and_stock_binary_contents_transferred']=True
            out['inventory']=analyze(af,sf)
            if out['inventory']['all_strong_relocation_imports_have_static_candidates']:
                out['result']='PASS_SYMBOL_RELOCATION_CANDIDATES_METADATA_ONLY'
                out['hold_category']='NOT_BOOTABLE'
            else:
                out['hold_category']='RELOCATION_IMPORTS_WITHOUT_STATIC_EXPORT_CANDIDATES'
        except (Hold,transport.Hold,diag.Hold,app.Hold,parser.BindingHold) as e:
            out['hold_category']=e.category if isinstance(e,(transport.Hold,diag.Hold)) else str(e)
            if isinstance(e,(transport.Hold,diag.Hold)):out.update(e.evidence)
        except Exception as e:
            out['hold_category']='UNEXPECTED_'+type(e).__name__
    print(json.dumps(out,sort_keys=True,indent=2))
    return 0 if out['result']=='PASS_SYMBOL_RELOCATION_CANDIDATES_METADATA_ONLY' else 2

if __name__=='__main__':sys.exit(main())
