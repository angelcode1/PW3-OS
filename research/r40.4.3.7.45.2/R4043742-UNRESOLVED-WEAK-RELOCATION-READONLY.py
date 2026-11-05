#!/usr/bin/env python3
"""R4043742: source-only ARM relocation context for held VERSYM=0 weak imports.

Read-only, independently SHA-pinned R3741.1 replay. Uses no guest paths,
symbol names or version labels in emitted JSON; does not execute or modify ELF.
No weak-symbol value substitution, relocation application, symlink creation,
QEMU, firmware, physical PW3 or boot. NOT_BOOTABLE.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

PARENT = 'R4043741-1-LOCAL-VERSION-REVIEW-READONLY.py'
PARENT_SHA256 = '596b21871833423a2050828457b7a52c823b87605d0c9839542a3ec582f970d0'
MAX_RELOCS = 65536

class Hold(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def load_parent(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('PARENT_DIRECTORY_HOLD')
    path = folder/PARENT
    if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=PARENT_SHA256:
        raise Hold('PARENT_SOURCE_OR_SHA_HOLD')
    spec = importlib.util.spec_from_file_location('pinned_r3741_1_for_r3742',path)
    if not spec or not spec.loader:
        raise Hold('PARENT_IMPORT_HOLD')
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def relocation_context(p26, p40, path, expected_symbol_count, expected_relocs):
    """Return per-symbol relocation type/group counters, no symbol-name reads.

    Reuse a previously verified ELF's file-backed segment mapping. Read only
    bounded relocations from PT_DYNAMIC. Index 0 is not a dynsym reference.
    """
    try:
        with p26.open_regular_nofollow(path) as f:
            h=p26.elf_header(f)
            if h is None or h['cls']!=1 or h['machine']!=40 or h['phsize']!=32:
                raise Hold('ELF32_ARM_LAYOUT_HOLD')
            loads=[]; dynamics=[]
            for i in range(h['phnum']):
                vals=struct.unpack(h['endian']+'IIIIIIII',p26.read_at(f,h['phoff']+i*32,32))
                typ,off,va,_,filesz,memsz,_,_=vals
                if typ not in (1,2):continue
                if off > h['length'] or filesz > h['length']-off or filesz>memsz or va+memsz>0x100000000:
                    raise Hold('SEGMENT_BOUNDS_HOLD')
                if typ==1:loads.append((va,off,filesz))
                else:dynamics.append((off,filesz))
            if not loads or len(dynamics)!=1:
                raise Hold('DYNAMIC_SEGMENT_COUNT_HOLD')
            off,sz=dynamics[0]
            if not 8<=sz<=65536 or sz%8:
                raise Hold('DYNAMIC_SIZE_HOLD')
            tags={}; ended=False
            tracked={17,18,19,7,8,9,23,2,20}
            for i in range(sz//8):
                tag,val=struct.unpack(h['endian']+'II',p26.read_at(f,off+8*i,8))
                if tag==0:ended=True;break
                if tag in tracked:
                    if tag in tags:raise Hold('DUPLICATE_RELOCATION_TAG_HOLD')
                    tags[tag]=val
            if not ended:raise Hold('DYNAMIC_UNTERMINATED_HOLD')
            tables=[]
            def add(kind,ptr,szkey,ent,width):
                present=[x in tags for x in (ptr,szkey,ent)]
                if not any(present):return
                if not all(present) or tags[ent]!=width or tags[szkey]>MAX_RELOCS*width or tags[szkey]%width:
                    raise Hold('RELOCATION_DESCRIPTOR_HOLD')
                if tags[szkey]:
                    loc=p40.map_filebacked(loads,tags[ptr],tags[szkey])
                    tables.append((kind,loc,tags[szkey]//width,width))
            add('REL',17,18,19,8)
            add('RELA',7,8,9,12)
            if any(x in tags for x in (23,2,20)):
                if not all(x in tags for x in (23,2,20)) or tags[20] not in (7,17):
                    raise Hold('PLT_RELOCATION_DESCRIPTOR_HOLD')
                width=8 if tags[20]==17 else 12
                if tags[2]>MAX_RELOCS*width or tags[2]%width:
                    raise Hold('PLT_RELOCATION_SIZE_HOLD')
                if tags[2]:
                    loc=p40.map_filebacked(loads,tags[23],tags[2])
                    tables.append(('PLT',loc,tags[2]//width,width))
            totals=Counter(); sites=defaultdict(Counter)
            for kind,off,count,width in tables:
                for i in range(count):
                    raw=p26.read_at(f,off+i*width,width)
                    _,info=struct.unpack_from(h['endian']+'II',raw)
                    index=info>>8; rtype=info&0xff
                    if index>=expected_symbol_count:
                        raise Hold('RELOCATION_SYMBOL_INDEX_HOLD')
                    totals['TOTAL']+=1
                    totals[kind]+=1
                    if index:sites[index][(kind,rtype)]+=1
            if totals['TOTAL']!=expected_relocs:
                raise Hold('R3740_RELOCATION_TOTAL_REPLAY_HOLD')
            return dict(sites), dict(totals)
    except p26.Hold:
        raise Hold('PINNED_ELF_IO_HOLD') from None
    except p40.Hold:
        raise Hold('RELOCATION_TABLE_UNMAPPED_HOLD') from None


def compare_review_relocations(sources, providers, contexts):
    """Categorize 42 local-index weak & two no-provider references; no names exported."""
    if len(contexts)!=len(sources):raise Hold('SOURCE_CONTEXT_COUNT_HOLD')
    export_counts=Counter()
    for provider in providers:
        for i,sym in enumerate(provider['symbols']):
            if (sym['defined'] and sym['name'] and sym['binding'] in (1,2,10)
                and sym['visibility'] in (0,3)):
                export_counts[sym['name']]+=1
    local=Counter(); missing=Counter(); localtypes=Counter(); missingtypes=Counter()
    local_by_file=Counter(); missing_by_file=Counter();
    local_site_count=0; missing_site_count=0
    all_undefined=0; local_symbols=0; missing_symbols=0
    for source,sites in zip(sources,contexts):
        symbols=source['symbols']; version=source['versym']
        if len(symbols)!=len(version):raise Hold('VERSYM_LENGTH_HOLD')
        for idx in source['referenced_indices']:
            if idx<=0 or idx>=len(symbols):raise Hold('SYMBOL_INDEX_HOLD')
            sym=symbols[idx]
            if sym['defined']:continue
            all_undefined+=1
            name=sym['name']; raw=version[idx]; vi=raw&0x7fff
            refs=sites.get(idx,Counter())
            if not refs:raise Hold('MISSING_REFERENCED_RELOCATION_HOLD')
            if vi==0:
                if sym['binding']!=2 or sym['type']!=0 or bool(raw&0x8000) or not name:
                    raise Hold('LOCAL_WEAK_BASELINE_DIFFERENT_HOLD')
                local_symbols+=1
                for (kind,rtype),number in refs.items():
                    localtypes[str(rtype)]+=number
                    local['TABLE_'+kind]+=number
                    local_site_count+=number
                local['LOCAL_NAME_ZERO_PROVIDER' if export_counts[name]==0 else
                      'LOCAL_NAME_ONE_PROVIDER' if export_counts[name]==1 else
                      'LOCAL_NAME_MULTIPLE_PROVIDERS']+=1
                local['SYMBOL_SITE_COUNT_1' if sum(refs.values())==1 else 'SYMBOL_SITE_COUNT_2PLUS']+=1
            elif export_counts.get(name,0)==0:
                # These two records had no name candidate among the six providers.
                missing_symbols+=1
                missing['STB_'+str(sym['binding'])]+=1
                missing['GNU_VERSION_INDEX_1' if vi==1 else 'EXPLICIT_REQUIREMENT' if vi>1 else 'UNKNOWN']+=1
                missing['TYPE_'+str(sym['type'])]+=1
                for (kind,rtype),number in refs.items():
                    missingtypes[str(rtype)]+=number
                    missing_site_count+=number
        local_in_file=sum(1 for idx in source['referenced_indices'] if not source['symbols'][idx]['defined'] and (source['versym'][idx]&0x7fff)==0)
        missing_in_file=sum(1 for idx in source['referenced_indices'] if not source['symbols'][idx]['defined'] and (source['versym'][idx]&0x7fff)!=0 and export_counts[source['symbols'][idx]['name']]==0)
        if local_in_file:local_by_file['OBJECTS_WITH_LOCAL_WEAK']+=1
        if missing_in_file:missing_by_file['OBJECTS_WITH_NO_NAME_PROVIDER']+=1
    if all_undefined!=632 or local_symbols!=42 or missing_symbols!=2:
        raise Hold('EXPECTED_632_42_2_COUNTS_HOLD')
    return {'undefined_entry_count_reverified':all_undefined,
            'local_index_weak_symbol_entries':local_symbols,
            'local_index_weak_relocation_sites':local_site_count,
            'local_index_weak_relocation_type_counts':dict(sorted(localtypes.items(),key=lambda x:int(x[0]))),
            'local_index_weak_relocation_context_categories':dict(sorted(local.items())),
            'source_objects_with_local_index_weak_entries':local_by_file['OBJECTS_WITH_LOCAL_WEAK'],
            'no_staged_provider_name_entries':missing_symbols,
            'no_staged_provider_name_relocation_sites':missing_site_count,
            'no_staged_provider_name_relocation_type_counts':dict(sorted(missingtypes.items(),key=lambda x:int(x[0]))),
            'no_staged_provider_name_symbol_categories':dict(sorted(missing.items())),
            'source_objects_with_no_provider_name_entries':missing_by_file['OBJECTS_WITH_NO_NAME_PROVIDER'],
            'weak_local_version_zero_remains_review':True,
            'no_candidate_does_not_prove_runtime_missing_symbol':True}


def audit(root,folder,p11):
    original=p11.load_original(folder)
    baseline=p11.audit(root,folder,original)
    if (baseline.get('result')!='GNU_VERSION_LOCAL_INDEX_REVIEW_STATIC_ONLY'
        or baseline.get('source_elf_count')!=12
        or baseline.get('provider_elf_count')!=6
        or baseline.get('referenced_undefined_entries_reclassified')!=632
        or baseline.get('source_symbol_version_requirement_categories')!={
            'EXPLICIT_GNU_VERSION_REQUIREMENT':588,'LOCAL_VERSION_INDEX_REQUIRES_REVIEW':42,
            'UNVERSIONED_OR_GLOBAL_REFERENCE':2}
        or baseline.get('version_filtered_static_candidate_categories')!={
            'MULTIPLE_GNU_VERSION_NAME_MATCHING_CANDIDATES':80,
            'NO_STAGED_PROVIDER_NAME_CANDIDATE':2,
            'ONE_GNU_VERSION_NAME_MATCHING_CANDIDATE':508,
            'UNDEFINED_LOCAL_VERSION_INDEX_REVIEW':42}):
        raise Hold('R3741_1_STAGE_BASELINE_HOLD')
    p40=original.load_parent(folder)
    p26,srcfiles,providerfiles=original.locate_sources_providers(root,folder,p40)
    src=[original.parse_version_file(p26,p40,p) for p in srcfiles]
    prov=[original.parse_version_file(p26,p40,p) for p in providerfiles]
    contexts=[]; total=0
    for path,parsed in zip(srcfiles,src):
        sites,counters=relocation_context(p26,p40,path,len(parsed['symbols']),parsed['relocation_entries'])
        contexts.append(sites);total+=counters['TOTAL']
    if total!=3499:raise Hold('R3737_RELOCATION_SITE_BASELINE_HOLD')
    findings=compare_review_relocations(src,prov,contexts)
    return {'milestone':'R40.4.3.7.42',
            'result':'UNDEFINED_WEAK_LOCAL_VERSION_RELOCATION_CONTEXT_STATIC_ONLY',
            'parent_r3741_1_source_sha_pinned_and_replayed':True,
            'original_r3741_hold_preserved':True,
            'prior_source_pins_inherited':True,
            'source_elf_count':12,'provider_elf_count':6,
            'requester_total_relocation_sites_reverified':total,
            **findings,
            'actual_weak_symbol_runtime_semantics_verified':False,
            'actual_library_search_and_symbol_interposition_verified':False,
            'tls_runtime_compatibility_verified':False,
            'guest_interpreter_path_resolved':False,'mapping_applied':False,
            'symbol_resolution_proven':False,'transitive_dependency_closure_proven':False,
            'source_provenance_authenticated':False,'historical_inventory_hashes_reverified':False,
            'stage_modified':False,'paths_symbols_versions_exported':False,
            'boot_authorized':False,'prune_authorized':False,'firmware_write_authorized':False,
            'immutable_hold':'NOT_BOOTABLE'}


def main():
    ap=argparse.ArgumentParser(description='R3742 read-only weak local symbol relocation context; NOT_BOOTABLE')
    ap.add_argument('--rootfs',type=Path,required=True)
    ap.add_argument('--parent-dir',type=Path,required=True)
    a=ap.parse_args()
    try:
        p=load_parent(a.parent_dir)
        result=audit(a.rootfs,a.parent_dir,p)
    except (Hold,OSError,RecursionError) as e:
        result={'milestone':'R40.4.3.7.42','result':'HOLD',
                'hold_category':e.code if isinstance(e,Hold) else 'HOST_IO_OR_GRAPH_HOLD',
                'boot_authorized':False,'prune_authorized':False,'immutable_hold':'NOT_BOOTABLE'}
    print(json.dumps(result,sort_keys=True))
    return 0 if result['result']=='UNDEFINED_WEAK_LOCAL_VERSION_RELOCATION_CONTEXT_STATIC_ONLY' else 2

if __name__=='__main__':raise SystemExit(main())
