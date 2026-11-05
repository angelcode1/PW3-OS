#!/usr/bin/env python3
"""R4043743: static export-name survey outside six direct provider candidates.

Uses original SHA-pinned R3742 and its parents. Checks the 35 undefined weak
symbols which have NO name match among the six R3740 direct providers.
Only aggregates leave memory. Does not resolve symbols, run any staged ELF,
change files, create links, install packages, access hardware or authorize boot.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct

PARENT = 'R4043742-UNRESOLVED-WEAK-RELOCATION-READONLY.py'
PARENT_SHA256 = '4d118c490746d974e9f197db3260a3cb54f2b24b26ecebf82b4a3580b86715ed'
MAX_ADDITIONAL_ELFS = 256

class Hold(Exception):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


def load_pinned_parent(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('PARENT_DIR_INVALID_HOLD')
    path=folder/PARENT
    if path.name != PARENT or path.is_symlink() or not path.is_file():
        raise Hold('R3742_PARENT_SOURCE_INVALID_HOLD')
    if hashlib.sha256(path.read_bytes()).hexdigest() != PARENT_SHA256:
        raise Hold('R3742_PARENT_SOURCE_SHA_HOLD')
    spec=importlib.util.spec_from_file_location('pw3_r3742_pinned_for_3743',path)
    if not spec or not spec.loader:
        raise Hold('R3742_PARENT_IMPORT_HOLD')
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def exported_names(symbols):
    """Strong/weak/GNU-unique defined, externally visible name bytes only."""
    return {s['name'] for s in symbols
            if s['defined'] and s['name'] and s['binding'] in (1,2,10)
            and s['visibility'] in (0,3)}


def missing_weak_targets(sources, direct_providers):
    """Preserve R3742 42+2 weak baseline, return 35 TARGETS privately."""
    offered=Counter()
    for p in direct_providers:
        for name in exported_names(p['symbols']):
            # Count each defined dynsym name per provider, not unique filenames;
            # we only need whether the name was seen at all for this survey.
            offered[name]+=1
    target=[]
    all_local=0
    local_direct=0
    global_missing=0
    for source in sources:
        if len(source['symbols']) != len(source['versym']):
            raise Hold('SOURCE_SYMBOL_VERSION_LENGTH_HOLD')
        for idx in sorted(source['referenced_indices']):
            if idx < 1 or idx >= len(source['symbols']):
                raise Hold('REFERENCED_SYMBOL_INDEX_HOLD')
            sym=source['symbols'][idx]
            if sym['defined']:
                continue
            vi=source['versym'][idx] & 0x7fff
            name=sym['name']
            if vi==0:
                all_local+=1
                if sym['binding']!=2 or sym['type']!=0 or not name:
                    raise Hold('WEAK_LOCAL_BASELINE_CHANGED_HOLD')
                if offered[name]:
                    local_direct+=1
                else:
                    target.append(('LOCAL_INDEX_ZERO',name))
            elif not offered[name]:
                if vi != 1 or sym['binding']!=2 or sym['type']!=0 or not name:
                    raise Hold('OTHER_NO_PROVIDER_BASELINE_CHANGED_HOLD')
                global_missing+=1
                target.append(('UNVERSIONED_WEAK',name))
    if (all_local,local_direct,global_missing,len(target))!=(42,9,2,35):
        raise Hold('R3742_WEAK_42_9_2_35_REPLAY_HOLD')
    return target


def probe_arm32_dynamic(p26, path):
    """Return ONLY_ARM_DYNAMIC, ARM_NO_DYNAMIC or NOT_ARM32; fail closed IO."""
    try:
        with p26.open_regular_nofollow(path) as f:
            h=p26.elf_header(f)
            if h is None or h['cls']!=1 or h['machine']!=40:
                return 'NOT_ARM32'
            if h['phsize']!=32 or h['phnum']>2048:
                raise Hold('ARM_PROGRAM_HEADER_LAYOUT_HOLD')
            for i in range(h['phnum']):
                raw=p26.read_at(f,h['phoff']+i*32,32)
                kind=struct.unpack_from(h['endian']+'I',raw)[0]
                if kind==2:
                    return 'ARM_DYNAMIC'
            return 'ARM_NO_DYNAMIC'
    except p26.Hold:
        raise Hold('ARM_ELF_SCAN_IO_HOLD') from None


def bounded_elf_inventory(root, p26, sourcefiles, providerfiles, parser):
    """Return names per additional file; ambiguous/unsupported files explicit.

    Candidate filenames never appear in output. The absence of a name match in
    parsed files NEVER implies full stage inventory/search-path completeness.
    """
    sourceset=set(sourcefiles); providerset=set(providerfiles)
    if sourceset & providerset:
        raise Hold('SOURCE_PROVIDER_OVERLAP_HOLD')
    exports=defaultdict(set)
    counts=Counter()
    pathcount=0
    for base, dirs, names in os.walk(root,topdown=True,followlinks=False):
        dirs[:]=sorted(n for n in dirs if not (Path(base)/n).is_symlink())
        for n in sorted(names):
            p=Path(base)/n
            mode=p.lstat().st_mode
            if not stat.S_ISREG(mode):
                continue
            if p in sourceset or p in providerset:
                continue
            pathcount+=1
            counts['other_regular_stage_files_seen']+=1
            if pathcount>200000:
                raise Hold('STAGE_ENUMERATION_BOUNDS_HOLD')
            kind=probe_arm32_dynamic(p26,p)
            if kind=='NOT_ARM32':continue
            counts['additional_arm_elf_files_seen']+=1
            if kind=='ARM_NO_DYNAMIC':
                counts['additional_arm_elf_without_dynamic']+=1
                continue
            counts['additional_arm_elf_with_dynamic']+=1
            if counts['additional_arm_elf_with_dynamic']>MAX_ADDITIONAL_ELFS:
                raise Hold('ADDITIONAL_DYNAMIC_ELF_LIMIT_HOLD')
            try:
                obj=parser(p)
            except Exception as exc:
                # An unsupported ELF does not become a 'no export' result.
                # Narrow to caller-supplied parser's known Hold/OSError types;
                # unexpected exceptions must fail closed rather than be hidden.
                if not isinstance(exc, (OSError, Hold)) and not isinstance(exc, parser.hold_types):
                    raise
                counts['additional_dynamic_elf_parser_refusals']+=1
                continue
            counts['additional_dynamic_elf_parsed']+=1
            for name in exported_names(obj['symbols']):
                exports[name].add(p)
    return exports,dict(counts)


def compare_extra_targets(targets, source_objs, other_exports, counters):
    source_export_counts=Counter()
    for source in source_objs:
        for name in exported_names(source['symbols']):
            source_export_counts[name]+=1
    c=Counter(); by_group=defaultdict(Counter)
    unique_names=set()
    extra_file_edges=0
    for typ,name in targets:
        unique_names.add(name)
        source_hits=source_export_counts[name]>0
        other_hits=len(other_exports.get(name,()))
        extra_file_edges+=other_hits
        category=('SOURCE_AND_OTHER_STAGE_EXPORT_NAME' if source_hits and other_hits else
                  'SOURCE_ELF_EXPORT_NAME_ONLY' if source_hits else
                  'OTHER_STAGE_ELF_EXPORT_NAME_ONLY' if other_hits else
                  'NO_NAME_CANDIDATE_IN_PARSED_ADDITIONAL_FILES')
        c[category]+=1
        by_group[typ][category]+=1
        by_group[typ]['TARGETS']+=1
    if len(targets)!=35 or dict((k,x['TARGETS']) for k,x in by_group.items())!={'LOCAL_INDEX_ZERO':33,'UNVERSIONED_WEAK':2}:
        raise Hold('TARGET_ACCOUNTING_HOLD')
    parse_failures=counters.get('additional_dynamic_elf_parser_refusals',0)
    return {
        'target_weak_entries_without_six_provider_name_candidate':35,
        'target_weak_entry_categories':{'LOCAL_INDEX_ZERO':33,'UNVERSIONED_WEAK':2},
        'distinct_target_weak_symbol_names_in_memory':len(unique_names),
        'additional_name_candidate_categories':dict(sorted(c.items())),
        'additional_name_candidate_categories_by_target_group':{
           key:dict(sorted({k:v for k,v in v.items() if k!='TARGETS'}.items()))
           for key,v in sorted(by_group.items())},
        'additional_regular_elf_export_file_matches_across_target_entries':extra_file_edges,
        'additional_scan_counters':dict(sorted(counters.items())),
        'all_additional_dynamic_elfs_parsed':parse_failures==0,
        'no_match_in_parsed_files_does_not_prove_absent_runtime_symbol':True,
        'extra_export_name_matching_is_not_loader_namespace_or_symbol_resolution':True,
    }


def audit(root,folder,r42):
    if root.is_symlink() or not root.is_dir():
        raise Hold('ROOTFS_DIR_HOLD')
    p11=r42.load_parent(folder)
    baseline=r42.audit(root,folder,p11)
    if (baseline.get('result')!='UNDEFINED_WEAK_LOCAL_VERSION_RELOCATION_CONTEXT_STATIC_ONLY'
        or baseline.get('local_index_weak_symbol_entries')!=42
        or baseline.get('local_index_weak_relocation_sites')!=58
        or baseline.get('no_staged_provider_name_entries')!=2
        or baseline.get('source_elf_count')!=12 or baseline.get('provider_elf_count')!=6
        or baseline.get('local_index_weak_relocation_type_counts')!={'21':42,'22':16}
        or baseline.get('no_staged_provider_name_symbol_categories')!={'GNU_VERSION_INDEX_1':2,'STB_2':2,'TYPE_0':2}
        or baseline.get('local_index_weak_relocation_context_categories',{}).get('LOCAL_NAME_ZERO_PROVIDER')!=33
        or baseline.get('local_index_weak_relocation_context_categories',{}).get('LOCAL_NAME_ONE_PROVIDER')!=9):
        raise Hold('R3742_USER_MAC_BASELINE_HOLD')
    original=p11.load_original(folder)
    p40=original.load_parent(folder)
    p26,sourcefiles,providerfiles=original.locate_sources_providers(root,folder,p40)
    sourceobjs=[original.parse_version_file(p26,p40,p) for p in sourcefiles]
    providerobjs=[original.parse_version_file(p26,p40,p) for p in providerfiles]
    targets=missing_weak_targets(sourceobjs,providerobjs)
    def read_provider(p):
        return p40.parse_dynamic_and_sections(p26,p)
    read_provider.hold_types=(p40.Hold,p26.Hold)
    exports,counters=bounded_elf_inventory(root,p26,sourcefiles,providerfiles,read_provider)
    info=compare_extra_targets(targets,sourceobjs,exports,counters)
    return {
       'milestone':'R40.4.3.7.43',
       'result':'WEAK_UNDEFINED_ADDITIONAL_STAGED_ELF_EXPORT_NAMES_STATIC_ONLY',
       'r3742_original_source_sha_pinned_and_replayed':True,
       'r3741_1_and_original_historical_hold_preserved':True,
       'prior_source_pins_inherited':True,
       'source_elf_count':12,'initial_provider_elf_count':6,
       **info,
       'complete_dynamic_loader_namespace_verified':False,
       'symbol_version_resolution_verified':False,
       'weak_runtime_semantics_verified':False,
       'guest_interpreter_path_resolved':False,
       'mapping_applied':False,
       'runtime_tls_compatibility_verified':False,
       'transitive_dependency_closure_proven':False,
       'original_r26_source_provenance_authenticated':False,
       'historical_inventory_hashes_reverified':False,
       'stage_modified':False,
       'paths_symbols_versions_exported':False,
       'boot_authorized':False,'prune_authorized':False,'firmware_write_authorized':False,
       'immutable_hold':'NOT_BOOTABLE',
    }


def main():
    ap=argparse.ArgumentParser(description='R3743 read-only staged ELF weak-name export survey')
    ap.add_argument('--rootfs',required=True,type=Path)
    ap.add_argument('--parent-dir',required=True,type=Path)
    args=ap.parse_args()
    try:
        result=audit(args.rootfs,args.parent_dir,load_pinned_parent(args.parent_dir))
    except (Hold,OSError,RecursionError) as e:
        result={'milestone':'R40.4.3.7.43','result':'HOLD',
           'hold_category':e.category if isinstance(e,Hold) else 'HOST_IO_OR_GRAPH_HOLD',
           'boot_authorized':False,'prune_authorized':False,
           'immutable_hold':'NOT_BOOTABLE'}
    print(json.dumps(result,sort_keys=True))
    return 0 if result['result']=='WEAK_UNDEFINED_ADDITIONAL_STAGED_ELF_EXPORT_NAMES_STATIC_ONLY' else 2

if __name__=='__main__':
    raise SystemExit(main())
