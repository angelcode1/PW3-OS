#!/usr/bin/env python3
"""Classify prior R3877.18.1 strict DT_NEEDED candidate misses without changing them.

Do not infer runtime load order or actual glibc bindings. All ELF parsing occurs
on the Mac using fixed-scope, read-only SSH collection from the existing runner.
"""
from collections import Counter, defaultdict, deque
import pw3_r3877_18_1_relocation_candidates as prior
import pw3_r3877_15_koreader_elf_audit as app
import r3877_18_binding_parser as parser

class ScopeHold(Exception):
    pass

MAX_SAMPLES_PER_CLASS=12
MAX_PROVIDER_EXAMPLES=18

def compatible(exp, imp):
    if exp['name'] != imp['name']: return False
    if imp['version']:
        if exp['version'] != imp['version']: return False
    elif exp['version'] is not None and exp['version_hidden']:
        return False
    return not (imp['typ'] and exp['typ'] and imp['typ']!=exp['typ'])

def describe(imp, path, exports_index, reachable, providers):
    """Return reason category plus bounded exact symbol-export diagnostics.

    Categories are *alternative static candidates*, not proof of runtime load.
    Must be called ONLY for an import that strict R3877.18.1 did not match.
    """
    named=providers.get(imp['version_provider']) if imp.get('version_provider') else None
    all_named=exports_index.get(imp['name'],[])
    exact=[(source,exp) for source,exp in all_named if compatible(exp,imp)]
    if imp.get('version_provider'):
        named_list=[(s,e) for s,e in all_named if s==named]
        if named and named not in reachable[path] and any(s==named for s,e in exact):
            reason='named_provider_outside_strict_dependency_scope'
        elif named_list:
            if any(s==named and e['version']==imp['version'] for s,e in named_list):
                reason='named_provider_symbol_type_mismatch'
            else:
                reason='named_provider_version_or_default_mismatch'
        elif exact:
            reason='exact_export_in_other_collected_provider'
        elif named:
            reason='named_provider_has_no_matching_symbol'
        else:
            reason='version_provider_name_uncollected'
    elif any(s=='koreader/luajit' for s,e in exact) and 'koreader/luajit' not in reachable[path]:
        reason='main_luajit_executable_export_candidate_outside_strict_scope'
    elif exact:
        reason='export_candidate_outside_strict_dependency_scope'
    elif all_named:
        reason='collected_symbol_name_found_but_type_or_version_incompatible'
    else:
        reason='no_export_with_this_name_in_collected_elf_set'
    # Never include addresses, paths outside the audited app/system inventory, or binary data.
    matches=sorted({s for s,e in exact})[:5]
    named_versions=sorted({(e['version'] or 'UNVERSIONED') for s,e in all_named if s==named})[:8]
    return {'reason':reason,'matching_export_paths_in_collected_set':matches,
            'named_provider_available_versions':named_versions}

def analyze(af,sf):
    baseline=prior.analyze(af,sf)
    blobs={}
    for path,(kind,data) in af.items():
        if kind=='file': blobs['koreader/'+path]=data
    for path,data in sf.items(): blobs['system/'+path]=data
    records={}
    for path,b in sorted(blobs.items()):
        try:
            parsed=parser.parse(b)
            info=app.inspect_elf(b)
        except (parser.BindingHold,app.Hold) as e:
            raise ScopeHold('PARSER_'+path.replace('/','_')+'_'+str(e)) from e
        records[path]={**parsed,'needed':info['needed'],'soname':info['soname']}
    providers={}
    for path,r in records.items():
        for name in [path.rsplit('/',1)[-1]]+r['soname']:
            if name in providers and providers[name]!=path:raise ScopeHold('DUPLICATE_PROVIDER_'+name)
            providers[name]=path
    for path,(kind,target) in af.items():
        if kind!='symlink':continue
        dest='koreader/libs/'+target
        if dest not in records:raise ScopeHold('SYMLINK_TARGET_NOT_COLLECTED')
        alias=path.rsplit('/',1)[-1]
        if alias in providers and providers[alias]!=dest:raise ScopeHold('COLLIDING_PROVIDER_ALIAS')
        providers[alias]=dest
    reachable={}
    for path in records:
        visited=set();q=deque([path])
        while q:
            p=q.popleft()
            if p in visited:continue
            visited.add(p)
            for dep in records[p]['needed']:
                if dep not in providers:raise ScopeHold('MISSING_PROVIDER_FOR_'+dep)
                q.append(providers[dep])
        reachable[path]=visited
    exports_index=defaultdict(list)
    for path,r in records.items():
        for exp in r['exports']:
            exports_index[exp['name']].append((path,exp))
    counts=Counter(); samples=defaultdict(list); perfile=Counter()
    counted_strong=counted_weak=counted_missing=0
    for path,r in records.items():
        for imp in r['relocated_imports']:
            weak=imp['bind']==2 or imp['version_weak']
            if weak:counted_weak+=1
            else:counted_strong+=1
            if imp['version_provider']:
                named=providers.get(imp['version_provider'])
                allowed=[named] if named and named in reachable[path] else []
            else:allowed=reachable[path]
            had_candidate=any(source in allowed and compatible(exp,imp) for source,exp in exports_index.get(imp['name'],[]))
            if weak or had_candidate:continue
            details=describe(imp,path,exports_index,reachable,providers)
            reason=details['reason'];counts[reason]+=1;perfile[path]+=1;counted_missing+=1
            if len(samples[reason])<MAX_SAMPLES_PER_CLASS:
                samples[reason].append({
                    'required_by':path,'symbol':imp['name'],
                    'version':imp['version'],'version_provider':imp['version_provider'],
                    'dynsym_type':imp['typ'],**details})
    if len(records)!=baseline['files_parsed'] or counted_strong!=baseline['strong_relocated_imports'] or counted_weak!=baseline['weak_relocated_imports'] or counted_missing!=baseline['strong_imports_without_export_candidates'] or sum(counts.values())!=counted_missing:
        raise ScopeHold('BASELINE_STRONG_IMPORT_COUNTS_DO_NOT_RECONCILE')
    return {
        'original_r3877_18_1_strong_missing_count':counted_missing,
        'original_r3877_18_1_strong_matched_count':baseline['strong_imports_with_export_candidates'],
        'original_r3877_18_1_weak_missing_count':baseline['weak_imports_without_export_candidates'],
        'files_parsed':len(records),
        'missing_strong_reason_counts':dict(sorted(counts.items())),
        'missing_strong_reason_samples':dict(sorted(samples.items())),
        'missing_strong_top_requesting_files':[
            {'file':p,'count':n} for p,n in perfile.most_common(15)],
        'classified_strong_import_count':sum(counts.values()),
        'same_scope_baseline_reconciled':True,
        'conditional_main_executable_export_candidates_not_runtime_proof':True,
        'possible_global_scope_not_confirmed':True,
        'runtime_bindings_verified':False,
        'glibc_load_order_verified':False,
        'dlopen_module_dependency_closure_verified':False,
        'koreader_dependency_closure_verified':False,
        'target_musl_runtime_verified':False,
        'target_kernel_syscall_compatibility_verified':False,
        'snapshots_atomic':False,
        'immutable_hold':'NOT_BOOTABLE',
    }
