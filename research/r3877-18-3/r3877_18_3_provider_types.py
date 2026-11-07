#!/usr/bin/env python3
"""Static audit of named-provider ELF symbol-type mismatches on PW3.

No ELF binary execution, linker simulation, external writes, or security bypasses.
Classification is conditional and never treats a GNU IFUNC as runtime-proven.
"""
from collections import Counter, defaultdict, deque
import struct
import r3877_18_2_scope_classifier as scope
import r3877_18_binding_parser as parser
import pw3_r3877_15_koreader_elf_audit as app

EXPECTED_STRONG_MISSES=167
EXPECTED_LUA_SCOPE_CANDIDATES=163
EXPECTED_TYPE_MISMATCHES=4
MAX_SAMPLES=8

class ProviderHold(Exception):
    pass

def type_label(n):
    return {0:'STT_NOTYPE',1:'STT_OBJECT',2:'STT_FUNC',3:'STT_SECTION',
            4:'STT_FILE',5:'STT_COMMON',6:'STT_TLS',10:'STT_GNU_IFUNC',
            13:'STT_ARM_TFUNC'}.get(n,'STT_UNKNOWN_'+str(n))

def type_hypothesis(requested,offered):
    if requested==2 and offered==10:
        return 'FUNCTION_IMPORT_TO_GNU_IFUNC_EXPORT_CONDITIONAL'
    if requested==2 and offered==13:
        return 'FUNCTION_IMPORT_TO_ARM_THUMB_FUNCTION_EXPORT_CONDITIONAL'
    if requested==2 and offered==1:
        return 'FUNCTION_IMPORT_TO_OBJECT_EXPORT_TYPE_MISMATCH'
    return 'OTHER_IMPORT_EXPORT_TYPE_MISMATCH'

def analyze(af,sf, expected_counts=True):
    baseline=scope.analyze(af,sf)
    counts=baseline['missing_strong_reason_counts']
    if sum(counts.values())!=baseline['classified_strong_import_count']:
        raise ProviderHold('SCOPE_CLASSIFICATION_INCONSISTENT')
    if expected_counts and (baseline['classified_strong_import_count']!=EXPECTED_STRONG_MISSES or
        counts.get('main_luajit_executable_export_candidate_outside_strict_scope',0)!=EXPECTED_LUA_SCOPE_CANDIDATES or
        counts.get('named_provider_symbol_type_mismatch',0)!=EXPECTED_TYPE_MISMATCHES or
        len(counts)!=2):
        raise ProviderHold('EXPECTED_R3877_18_2_BASELINE_DRIFT')
    files={}
    for p,(kind,b) in af.items():
        if kind=='file':files['koreader/'+p]=b
    for p,b in sf.items():files['system/'+p]=b
    records={}
    for p,b in sorted(files.items()):
        try:
            parsed=parser.parse(b)
            inf=app.inspect_elf(b)
        except (parser.BindingHold,app.Hold) as e:
            raise ProviderHold('ELF_PARSE_'+p.replace('/','_')+'_'+str(e)) from e
        records[p]={**parsed,'needed':inf['needed'],'soname':inf['soname']}
    if len(records)!=baseline['files_parsed']:
        raise ProviderHold('ELF_FILE_COUNT_DRIFT')
    providers={}
    for p,r in records.items():
        for soname in [p.rsplit('/',1)[-1]]+r['soname']:
            if soname in providers and providers[soname]!=p:
                raise ProviderHold('DUPLICATE_PROVIDER_'+soname)
            providers[soname]=p
    for p,(kind,target) in af.items():
        if kind!='symlink':continue
        dest='koreader/libs/'+target
        if dest not in records:raise ProviderHold('SYMLINK_TARGET_NOT_COLLECTED')
        alias=p.rsplit('/',1)[-1]
        if alias in providers and providers[alias]!=dest:
            raise ProviderHold('COLLIDING_PROVIDER_ALIAS')
        providers[alias]=dest
    reachable={}
    for path in records:
        q=deque([path]);seen=set()
        while q:
            k=q.popleft()
            if k in seen:continue
            seen.add(k)
            for dep in records[k]['needed']:
                if dep not in providers:raise ProviderHold('DEPENDENCY_PROVIDER_ABSENT_'+dep)
                q.append(providers[dep])
        reachable[path]=seen
    index=defaultdict(list)
    for path, rec in records.items():
        for exp in rec['exports']:
            index[exp['name']].append((path,exp))
    mismatch=[]; main_count=0; all_strong_miss=0
    for path,rec in records.items():
        for imp in rec['relocated_imports']:
            if imp['bind']==2 or imp['version_weak']:continue
            named=providers.get(imp['version_provider']) if imp['version_provider'] else None
            allowed=[named] if named and named in reachable[path] else reachable[path] if not imp['version_provider'] else []
            if any(src in allowed and scope.compatible(e,imp) for src,e in index.get(imp['name'],[])):
                continue
            all_strong_miss+=1
            detail=scope.describe(imp,path,index,reachable,providers)
            if detail['reason']=='main_luajit_executable_export_candidate_outside_strict_scope':
                main_count+=1;continue
            if detail['reason']!='named_provider_symbol_type_mismatch':
                raise ProviderHold('UNCLASSIFIED_STATIC_MISS_'+detail['reason'])
            if not named or named not in reachable[path]:raise ProviderHold('NAMED_PROVIDER_OUTSIDE_SCOPE')
            same=[e for src,e in index.get(imp['name'],[]) if src==named and e['version']==imp['version']]
            if not same:raise ProviderHold('SAME_VERSION_EXPORT_MISSING')
            same=sorted(same,key=lambda e:(e['typ'],e['bind'],e['version_hidden']))
            mismatch.append({'required_by':path,'symbol':imp['name'],
                'required_version':imp['version'],'version_provider':imp['version_provider'],
                'provider_file':named,'import_type':type_label(imp['typ']),
                'provider_export_types':[{'type':type_label(e['typ']),
                    'binding':e['bind'],'version_hidden':e['version_hidden'],
                    'hypothesis':type_hypothesis(imp['typ'],e['typ'])} for e in same][:MAX_SAMPLES],
                'runtime_bindings_verified':False})
    mismatch=sorted(mismatch,key=lambda d:(d['required_by'],d['symbol']))
    if (all_strong_miss!=baseline['classified_strong_import_count'] or
        main_count!=counts.get('main_luajit_executable_export_candidate_outside_strict_scope',0) or
        len(mismatch)!=counts.get('named_provider_symbol_type_mismatch',0)):
        raise ProviderHold('STRONG_MISS_RECONCILIATION_FAILED')
    if expected_counts and any(not (d['symbol']=='clock_gettime' and
         d['required_version']=='GLIBC_2.4' and d['version_provider']=='librt.so.1') for d in mismatch):
        raise ProviderHold('CLOCK_GETTIME_BASELINE_DRIFT')
    type_counts=Counter((d['import_type'],e['type']) for d in mismatch for e in d['provider_export_types'])
    luajit=files.get('koreader/luajit')
    if not luajit or len(luajit)<18:raise ProviderHold('LUAJIT_HEADER_MISSING')
    elf_type=struct.unpack_from('<H',luajit,16)[0]
    if elf_type not in (2,3):raise ProviderHold('UNEXPECTED_LUAJIT_ELF_TYPE')
    return {'prior_strict_scope_missing_count':all_strong_miss,
        'main_luajit_export_candidates_outside_strict_scope':main_count,
        'main_luajit_elf_type':{2:'ET_EXEC',3:'ET_DYN'}[elf_type],
        'main_luajit_dynamic_export_count':len(records['koreader/luajit']['exports']),
        'type_mismatch_count':len(mismatch),
        'type_mismatch_pairs':mismatch[:MAX_SAMPLES],
        'import_export_type_pair_counts':[
            {'import_type':k[0],'export_type':k[1],'count':v} for k,v in sorted(type_counts.items())],
        'all_prior_misses_classified':True,
        'ifunc_resolver_not_executed':True,
        'main_executable_global_scope_not_verified':True,
        'glibc_load_order_verified':False,
        'runtime_bindings_verified':False,
        'full_koreader_dependency_closure_verified':False,
        'alpine_musl_syscall_compatibility_verified':False,
        'source_snapshots_atomic':False,
        'immutable_hold':'NOT_BOOTABLE'}
