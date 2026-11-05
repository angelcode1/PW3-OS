#!/usr/bin/env python3
"""R3744: classify static ELF32 ARM weak relocation slots, never resolve them.

Read only the SHA-pinned R3743.1 audit and unchanged Mac R13 rootfs. Separate
weak undefined VERSYM-local and unversioned references; inspect relocation
slot geometry (PT_LOAD permission, original word/BSS, GNU RELRO) and NOW flags.
Never replace weak symbols with zero, execute loader, modify a stage or boot.
No guest paths, symbol strings, version names, addresses or slot values emitted.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

PARENT = 'R4043743-1-OVERLAP-AWARE-EXPORT-SURVEY-READONLY.py'
PARENT_SHA256 = '001aa31f058296b8792141b0032aa5b1d5d3a58346b9ab55b7b252cbdaca0a55'
PT_LOAD, PT_DYNAMIC, PT_GNU_RELRO = 1, 2, 0x6474e552
PT_W = 2
DT_BIND_NOW, DT_FLAGS, DT_FLAGS_1 = 24, 30, 0x6ffffffb
DF_BIND_NOW, DF_1_NOW = 0x8, 0x1
MAX_RELOCS = 65536


class Hold(Exception):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


def import_pinned(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('PARENT_DIRECTORY_HOLD')
    p = folder / PARENT
    if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != PARENT_SHA256:
        raise Hold('R3743_1_SOURCE_SHA_HOLD')
    spec = importlib.util.spec_from_file_location('r3743_1_pinned_for_r3744',p)
    if spec is None or spec.loader is None:
        raise Hold('PARENT_IMPORT_HOLD')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def classify_word_location(loads, relro, vaddr, f, p26, endian):
    """Return categories only. Never export offsets or the original word.

    Load tuple: (virtual address, file offset, file size, memory size, flags).
    A BSS slot is inferred as zero-initialized, not read from disk.
    """
    if not 0 <= vaddr <= 0xffffffff:
        raise Hold('RELOCATION_OFFSET_RANGE_HOLD')
    if vaddr & 3:
        return 'UNALIGNED_SLOT_REVIEW', 'RELRO_UNDETERMINED'
    hits = [x for x in loads if x[0] <= vaddr and vaddr-x[0] <= x[3] and 4 <= x[3]-(vaddr-x[0])]
    if not hits:
        return 'NO_CONTAINING_PT_LOAD_REVIEW', 'RELRO_UNDETERMINED'
    if len(hits) != 1:
        return 'AMBIGUOUS_OVERLAPPING_PT_LOAD_REVIEW', 'RELRO_UNDETERMINED'
    va, off, filesz, memsz, flags = hits[0]
    d = vaddr-va
    r_hits = [x for x in relro if x[0] <= vaddr and 4 <= x[1]-(vaddr-x[0])]
    relro_category = 'RELRO_INSIDE' if r_hits else 'RELRO_OUTSIDE'
    if len(r_hits) > 1:
        relro_category='OVERLAPPING_RELRO_REVIEW'
    perm = 'WRITABLE' if flags & PT_W else 'NONWRITABLE_REVIEW'
    if d+4 <= filesz:
        # Read file-backed word with the checked ELF read helper; no value output.
        raw = p26.read_at(f, off+d, 4)
        word, = struct.unpack(endian+'I', raw)
        content = 'INITIAL_WORD_ZERO' if word==0 else 'INITIAL_WORD_NONZERO'
    elif d>=filesz:
        content='BSS_ZERO_INITIALIZED'
    else:
        content='CROSSES_FILE_BSS_BOUNDARY_REVIEW'
    return perm+'_'+content, relro_category


def read_relocation_sites(p26, path, target_indices):
    """Gather only selected target records. Index 0 is never a symbol ref."""
    try:
        with p26.open_regular_nofollow(path) as f:
            h = p26.elf_header(f)
            if h is None or h['cls'] != 1 or h['machine'] != 40 or h['phsize'] != 32:
                raise Hold('ELF32_ARM_HEADER_HOLD')
            loads=[]; dynamic=[]; relro=[]
            if h['phnum'] > 512:
                raise Hold('PROGRAM_HEADER_COUNT_HOLD')
            for i in range(h['phnum']):
                ph=p26.read_at(f,h['phoff']+i*32,32)
                typ, off, va, _, filesz, memsz, flags, _ = struct.unpack(h['endian']+'IIIIIIII',ph)
                if typ not in (PT_LOAD,PT_DYNAMIC,PT_GNU_RELRO):
                    continue
                if off>h['length'] or filesz>h['length']-off or (typ==PT_LOAD and filesz>memsz) or va+memsz>0x100000000:
                    raise Hold('PROGRAM_SEGMENT_BOUNDS_HOLD')
                if typ==PT_LOAD:loads.append((va,off,filesz,memsz,flags))
                elif typ==PT_DYNAMIC:dynamic.append((off,filesz))
                else:relro.append((va,memsz))
            if not loads or len(dynamic)!=1:
                raise Hold('DYNAMIC_OR_LOAD_LAYOUT_HOLD')
            off,size=dynamic[0]
            if size<8 or size>65536 or size%8:
                raise Hold('DYNAMIC_SIZE_HOLD')
            tags={}; done=False
            relevant={17,18,19,7,8,9,23,2,20,DT_BIND_NOW,DT_FLAGS,DT_FLAGS_1}
            for i in range(size//8):
                tag,val=struct.unpack(h['endian']+'II',p26.read_at(f,off+i*8,8))
                if tag==0:done=True;break
                if tag in relevant:
                    if tag in tags:raise Hold('DUPLICATE_DYNAMIC_TAG_HOLD')
                    tags[tag]=val
            if not done:raise Hold('DYNAMIC_UNTERMINATED_HOLD')
            tables=[]
            def add(kind,pointer,sz,ent,width):
                present=[k in tags for k in (pointer,sz,ent)]
                if not any(present):return
                if not all(present) or tags[ent]!=width or tags[sz]%(width) or tags[sz]>MAX_RELOCS*width:
                    raise Hold('RELOCATION_TABLE_DESCRIPTOR_HOLD')
                if tags[sz]:
                    loc=backed_location(loads,tags[pointer],tags[sz])
                    tables.append((kind,loc,tags[sz]//width,width))
            add('REL',17,18,19,8)
            add('RELA',7,8,9,12)
            if any(k in tags for k in (23,2,20)):
                if not all(k in tags for k in (23,2,20)) or tags[20] not in (17,7):
                    raise Hold('PLT_RELOCATION_DESCRIPTOR_HOLD')
                width=8 if tags[20]==17 else 12
                if tags[2]%width or tags[2]>MAX_RELOCS*width:
                    raise Hold('PLT_RELOCATION_SIZE_HOLD')
                if tags[2]:tables.append(('PLT',backed_location(loads,tags[23],tags[2]),tags[2]//width,width))
            counters=defaultdict(Counter)
            total=0
            for table,loc,n,width in tables:
                for i in range(n):
                    raw=p26.read_at(f,loc+i*width,width)
                    r_off,r_info=struct.unpack_from(h['endian']+'II',raw)
                    index=r_info>>8;typ=r_info&255
                    total+=1
                    if index in target_indices:
                        storage,relro_cat=classify_word_location(loads,relro,r_off,f,p26,h['endian'])
                        counters[index][('TABLE',table)] += 1
                        counters[index][('TYPE',str(typ))] += 1
                        counters[index][('SLOT',storage)] += 1
                        counters[index][('RELRO',relro_cat)] += 1
            settings={
              'bind_now':DT_BIND_NOW in tags or bool(tags.get(DT_FLAGS,0)&DF_BIND_NOW) or bool(tags.get(DT_FLAGS_1,0)&DF_1_NOW),
              'gnu_relro':bool(relro),
              'relocation_records':total,
            }
            return dict(counters), settings
    except p26.Hold:
        raise Hold('STAGED_ELF_IO_HOLD') from None


def backed_location(loads, vaddr, length):
    if vaddr<0 or length<0 or vaddr+length>0x100000000:
        raise Hold('RELOCATION_TABLE_VADDR_HOLD')
    locs={off+vaddr-va for va,off,filesz,_,_ in loads if va<=vaddr and vaddr-va<=filesz and length<=filesz-(vaddr-va)}
    if len(locs)!=1:
        raise Hold('RELOCATION_TABLE_NOT_UNIQUELY_FILEBACKED_HOLD')
    return next(iter(locs))


def aggregate(sources, providers, per_object, settings):
    """Group weak imports without exporting names or relocation offsets."""
    if len(sources)!=12 or len(per_object)!=12 or len(settings)!=12:
        raise Hold('SOURCE_COUNT_HOLD')
    exported=Counter()
    for provider in providers:
        for sym in provider['symbols']:
            if sym['name'] and sym['defined'] and sym['binding'] in (1,2,10) and sym['visibility'] in (0,3):
                exported[sym['name']]+=1
    groups=Counter(); per_group=defaultdict(Counter); missing=0
    for src,sites in zip(sources,per_object):
        for index in src['referenced_indices']:
            sym=src['symbols'][index]
            if sym['defined']:continue
            vi=src['versym'][index]&0x7fff
            if vi==0:
                if sym['binding']!=2 or sym['type']!=0:
                    raise Hold('LOCAL_WEAK_BASELINE_HOLD')
                group='LOCAL_ZERO_NAME_IN_SIX' if exported[sym['name']] else 'LOCAL_ZERO_NAME_NOT_IN_SIX'
            elif vi==1 and not exported[sym['name']]:
                if sym['binding']!=2 or sym['type']!=0:
                    raise Hold('UNVERSIONED_WEAK_BASELINE_HOLD')
                group='UNVERSIONED_WEAK_NAME_NOT_IN_SIX'
            else:continue
            groups[group]+=1
            context=sites.get(index)
            if not context:
                missing+=1
                continue
            for k,n in context.items():per_group[group][k]+=n
    if groups != {'LOCAL_ZERO_NAME_IN_SIX':9,'LOCAL_ZERO_NAME_NOT_IN_SIX':33,'UNVERSIONED_WEAK_NAME_NOT_IN_SIX':2}:
        raise Hold('WEAK_GROUP_COUNTS_HOLD')
    if missing:raise Hold('TARGET_WEAK_RELOCATION_MISSING_HOLD')
    if sum(x.get(('TABLE','REL'),0)+x.get(('TABLE','PLT'),0)+x.get(('TABLE','RELA'),0) for x in per_group.values()) != 62:
        raise Hold('WEAK_SITE_TOTAL_HOLD')
    out={}
    for group,rows in sorted(per_group.items()):
        out[group]={}
        for dimension in ('TABLE','TYPE','SLOT','RELRO'):
            out[group][dimension]=dict(sorted((key[1],value) for key,value in rows.items() if key[0]==dimension))
    return {'weak_reference_symbol_group_counts':dict(sorted(groups.items())),
            'weak_relocation_site_total':62,
            'weak_relocation_slot_categories_by_group':out,
            'requester_now_policy_objects':sum(int(s['bind_now']) for s in settings),
            'requester_gnu_relro_objects':sum(int(s['gnu_relro']) for s in settings),
            'requester_relocation_sites_reverified':sum(s['relocation_records'] for s in settings),
            'weak_reference_names_are_not_runtime_symbols_resolved':True}


def audit(root,folder,old):
    if root.is_symlink() or not root.is_dir():raise Hold('ROOTFS_HOLD')
    original = old.load_original(folder)
    baseline=old.audit(root,folder,original)
    if (baseline.get('result')!='OVERLAP_AWARE_ADDITIONAL_WEAK_EXPORT_NAME_REVIEW_ONLY'
            or baseline.get('source_provider_overlap_regular_files')!=4
            or baseline.get('additional_name_candidate_categories') != {'NO_NAME_CANDIDATE_IN_PARSED_ADDITIONAL_FILES':35}
            or baseline.get('additional_scan_counters',{}).get('additional_dynamic_elf_parsed')!=69
            or baseline.get('distinct_target_weak_symbol_names_in_memory')!=5):
        raise Hold('R3743_1_MAC_BASELINE_HOLD')
    p42=original.load_pinned_parent(folder)
    p11=p42.load_parent(folder)
    original41=p11.load_original(folder)
    p40=original41.load_parent(folder)
    p26,src_paths,provider_paths=original41.locate_sources_providers(root,folder,p40)
    sources=[original41.parse_version_file(p26,p40,p) for p in src_paths]
    providers=[original41.parse_version_file(p26,p40,p) for p in provider_paths]
    exported={s['name'] for p in providers for s in p['symbols'] if s['name'] and s['defined'] and s['binding'] in (1,2,10) and s['visibility'] in (0,3)}
    byobject=[];settings=[]
    for p,obj in zip(src_paths,sources):
        target={i for i in obj['referenced_indices'] if not obj['symbols'][i]['defined'] and ((obj['versym'][i]&0x7fff)==0 or ((obj['versym'][i]&0x7fff)==1 and obj['symbols'][i]['name'] not in exported))}
        sites,flags=read_relocation_sites(p26,p,target)
        byobject.append(sites);settings.append(flags)
    out=aggregate(sources,providers,byobject,settings)
    if out['requester_relocation_sites_reverified']!=3499:
        raise Hold('REQUESTER_RELOCATION_COUNT_CHANGED_HOLD')
    return {'milestone':'R40.4.3.7.44','result':'WEAK_RELOCATION_SLOT_STORAGE_STATIC_ONLY',
            'parent_r3743_1_source_sha_pinned_and_replayed':True,
            'original_r3743_overlap_hold_preserved':True,
            'source_elf_count':12,'provider_elf_count':6,
            'additional_dynamic_elfs_previous_audit_parsed':69,
            **out,
            'runtime_weak_symbol_semantics_verified':False,
            'dynamic_loader_name_resolution_verified':False,
            'relocation_or_zero_substitution_applied':False,
            'rootfs_stage_modified':False,'mapping_applied':False,
            'original_r26_source_provenance_authenticated':False,
            'historical_inventory_hashes_reverified':False,
            'guest_interpreter_path_resolved':False,
            'tls_runtime_compatibility_verified':False,
            'complete_transitive_dependency_closure_proven':False,
            'firmware_write_authorized':False,'boot_authorized':False,'prune_authorized':False,
            'immutable_hold':'NOT_BOOTABLE'}


def main():
    ap=argparse.ArgumentParser(description='Read-only ARM weak-relocation slot audit; NOT_BOOTABLE')
    ap.add_argument('--rootfs',required=True,type=Path)
    ap.add_argument('--parent-dir',required=True,type=Path)
    args=ap.parse_args()
    try:result=audit(args.rootfs,args.parent_dir,import_pinned(args.parent_dir))
    except (Hold,OSError,RecursionError) as exc:
        result={'milestone':'R40.4.3.7.44','result':'HOLD',
                'hold_category':exc.category if isinstance(exc,Hold) else 'HOST_IO_OR_PARSER_HOLD',
                'boot_authorized':False,'prune_authorized':False,'immutable_hold':'NOT_BOOTABLE'}
    except Exception:
        result={'milestone':'R40.4.3.7.44','result':'HOLD',
                'hold_category':'UNEXPECTED_STATIC_PARSER_HOLD',
                'boot_authorized':False,'prune_authorized':False,'immutable_hold':'NOT_BOOTABLE'}
    print(json.dumps(result,sort_keys=True))
    return 0 if result['result']=='WEAK_RELOCATION_SLOT_STORAGE_STATIC_ONLY' else 2

if __name__=='__main__':raise SystemExit(main())
