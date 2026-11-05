#!/usr/bin/env python3
"""R4043745.2: corrected, pinned static initial PLT-word geometry for held weak ARM imports.

Host-only, read-only analysis of the unchanged R13 rootfs. Pin R3744 and all
predecessors. Never call a loader, resolve a symbol, apply a relocation,
create a link, write a file in the rootfs, use hardware, boot or prune.
No addresses, names, bytes or paths are printed; NOT_BOOTABLE.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

PARENT='R4043744-WEAK-RELOCATION-SLOT-PREFLIGHT-READONLY.py'
PARENT_SHA256='2fed6996817186156200f126cd69ffb9a326062721d2730b03636097daceae9d'
PT_LOAD=1
PT_DYNAMIC=2
PT_X=1
PT_W=2
DT_PLTGOT=3
DT_PLTRELSZ=2
DT_JMPREL=23
DT_PLTREL=20
DT_REL=17
DT_RELA=7
MAX_PLT_RELOCS=65536

class Hold(Exception):
    def __init__(self, category):
        self.category=category
        super().__init__(category)


def load_parent(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('PARENT_DIRECTORY_HOLD')
    source=folder/PARENT
    if source.is_symlink() or not source.is_file():
        raise Hold('R3744_PARENT_MISSING_HOLD')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=PARENT_SHA256:
        raise Hold('R3744_PARENT_SHA_HOLD')
    spec=importlib.util.spec_from_file_location('pinned_r3744_for_r3745',source)
    if spec is None or spec.loader is None:
        raise Hold('R3744_IMPORT_HOLD')
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def containing_load(loads, addr, nbytes=1):
    if addr<0 or nbytes<1 or addr+nbytes>0x100000000:
        return []
    return [p for p in loads if p[0]<=addr and nbytes<=p[3]-(addr-p[0])]


def classify_plt_original_word(word,loads):
    """Classify an *unrelocated* 32-bit word, not a verified code pointer.

    An odd low bit can be an ARM/Thumb state marker for a real code pointer,
    but the value may instead be an ELF addend or stub-specific datum. Thus
    the normalised containment check is geometry only, never execution proof.
    """
    if not isinstance(word,int) or not 0<=word<=0xffffffff:
        raise Hold('INVALID_INITIAL_WORD_HOLD')
    lowbit='LOW_BIT_SET' if word&1 else 'LOW_BIT_CLEAR'
    if word==0:
        return 'ORIGINAL_WORD_ZERO_REVIEW',lowbit
    addr=word&~1
    hits=containing_load(loads,addr)
    if not hits:
        return 'ORIGINAL_WORD_OUTSIDE_OWN_PT_LOAD',lowbit
    if len(hits)>1:
        return 'ORIGINAL_WORD_AMBIGUOUS_OWN_PT_LOAD',lowbit
    return ('ORIGINAL_WORD_IN_OWN_EXEC_PT_LOAD' if hits[0][4]&PT_X
            else 'ORIGINAL_WORD_IN_OWN_NONEXEC_PT_LOAD'),lowbit


def classify_pltgot_tag(tags,loads):
    """DT_PLTGOT presence and memory-range category; never infer GOT binding."""
    if DT_PLTGOT not in tags:
        return 'DT_PLTGOT_ABSENT'
    ptr=tags[DT_PLTGOT]
    hits=containing_load(loads,ptr,4)
    if not hits:return 'DT_PLTGOT_OUTSIDE_LOAD_REVIEW'
    if len(hits)>1:return 'DT_PLTGOT_AMBIGUOUS_LOAD_REVIEW'
    return ('DT_PLTGOT_IN_WRITABLE_LOAD' if hits[0][4]&PT_W
            else 'DT_PLTGOT_IN_NONWRITABLE_LOAD_REVIEW')


def read_weak_plt_words(p26,parent,path,target_groups):
    """Read bounded DT_JMPREL sites for selected symbols; no stage mutation.

    load tuple = (p_vaddr,p_offset,p_filesz,p_memsz,p_flags).
    Output contains aggregate per-group initial-word categories only.
    """
    try:
        with p26.open_regular_nofollow(path) as f:
            h=p26.elf_header(f)
            if h is None or h['cls']!=1 or h['machine']!=40 or h['phsize']!=32 or h['phnum']>512:
                raise Hold('ELF32_ARM_LAYOUT_HOLD')
            loads=[]; dynamics=[]
            for i in range(h['phnum']):
                typ,off,va,_,fsz,msz,flags,_=struct.unpack(h['endian']+'IIIIIIII',p26.read_at(f,h['phoff']+i*32,32))
                if typ not in (PT_LOAD,PT_DYNAMIC):continue
                if off>h['length'] or fsz>h['length']-off or fsz>msz or va+msz>0x100000000:
                    raise Hold('PROGRAM_SEGMENT_BOUNDS_HOLD')
                if typ==PT_LOAD:loads.append((va,off,fsz,msz,flags))
                else:dynamics.append((off,fsz))
            if not loads or len(dynamics)!=1:raise Hold('ELF_DYNAMIC_LAYOUT_HOLD')
            doff,dsize=dynamics[0]
            if not 8<=dsize<=65536 or dsize%8:raise Hold('DYNAMIC_SIZE_HOLD')
            tags={}; terminated=False
            watched={DT_PLTGOT,DT_PLTRELSZ,DT_JMPREL,DT_PLTREL}
            for i in range(dsize//8):
                tag,val=struct.unpack(h['endian']+'II',p26.read_at(f,doff+i*8,8))
                if tag==0:terminated=True;break
                if tag in watched:
                    if tag in tags:raise Hold('DUPLICATE_DYNAMIC_TAG_HOLD')
                    tags[tag]=val
            if not terminated:raise Hold('DYNAMIC_UNTERMINATED_HOLD')
            got=classify_pltgot_tag(tags,loads)
            present=[tag in tags for tag in (DT_PLTRELSZ,DT_JMPREL,DT_PLTREL)]
            if any(present) and not all(present):raise Hold('INCOMPLETE_PLT_DESCRIPTOR_HOLD')
            if not any(present):
                return {},got,0
            width=8 if tags[DT_PLTREL]==DT_REL else 12 if tags[DT_PLTREL]==DT_RELA else 0
            if not width or tags[DT_PLTRELSZ]%width or tags[DT_PLTRELSZ]>MAX_PLT_RELOCS*width:
                raise Hold('INVALID_PLT_DESCRIPTOR_HOLD')
            bytecount=tags[DT_PLTRELSZ]
            if bytecount==0:
                return {},got,0
            offset=parent.backed_location(loads,tags[DT_JMPREL],bytecount)
            totals=defaultdict(Counter)
            targets_seen=Counter()
            for i in range(bytecount//width):
                roff,info=struct.unpack_from(h['endian']+'II',p26.read_at(f,offset+i*width,width))
                index=info>>8;rtype=info&255
                if index not in target_groups:continue
                if rtype!=22:raise Hold('TARGET_PLT_NOT_JUMP_SLOT_HOLD')
                hits=containing_load(loads,roff,4)
                if roff&3 or len(hits)!=1 or not (hits[0][4]&PT_W):
                    raise Hold('TARGET_PLT_STORAGE_GEOMETRY_HOLD')
                va,fo,fsz,msz,flags=hits[0]
                delta=roff-va
                if delta+4>fsz:raise Hold('TARGET_PLT_SLOT_NOT_FILEBACKED_HOLD')
                word,=struct.unpack(h['endian']+'I',p26.read_at(f,fo+delta,4))
                category,lowbit=classify_plt_original_word(word,loads)
                group=target_groups[index]
                totals[group][('WORD',category)]+=1
                totals[group][('LOW_BIT',lowbit)]+=1
                targets_seen[index]+=1
            return dict(totals),got,sum(targets_seen.values())
    except p26.Hold:
        raise Hold('ELF_IO_HOLD') from None
    except parent.Hold:
        raise Hold('STATIC_TABLE_MAPPING_HOLD') from None


def choose_weak_targets(parsed,exported):
    result={}
    for index in parsed['referenced_indices']:
        symbol=parsed['symbols'][index]
        if symbol['defined']:continue
        vi=parsed['versym'][index]&0x7fff
        if vi==0:
            if symbol['binding']!=2 or symbol['type']!=0:
                raise Hold('LOCAL_WEAK_BASELINE_CHANGED_HOLD')
            group='LOCAL_ZERO_NAME_IN_SIX' if symbol['name'] in exported else 'LOCAL_ZERO_NAME_NOT_IN_SIX'
        elif vi==1 and symbol['name'] not in exported:
            if symbol['binding']!=2 or symbol['type']!=0:
                raise Hold('UNVERSIONED_WEAK_BASELINE_CHANGED_HOLD')
            group='UNVERSIONED_WEAK_NAME_NOT_IN_SIX'
        else:continue
        result[index]=group
    return result


def audit(root,folder,parent):
    if root.is_symlink() or not root.is_dir():raise Hold('ROOTFS_HOLD')
    previous=parent.audit(root,folder,parent.import_pinned(folder))
    expected={'LOCAL_ZERO_NAME_IN_SIX':9,'LOCAL_ZERO_NAME_NOT_IN_SIX':33,'UNVERSIONED_WEAK_NAME_NOT_IN_SIX':2}
    if (previous.get('result')!='WEAK_RELOCATION_SLOT_STORAGE_STATIC_ONLY'
            or previous.get('weak_reference_symbol_group_counts')!=expected
            or previous.get('weak_relocation_site_total')!=62
            or previous.get('requester_now_policy_objects')!=0
            or previous.get('requester_relocation_sites_reverified')!=3499):
        raise Hold('R3744_BASELINE_HOLD')
    p43=parent.import_pinned(folder)
    original43=p43.load_original(folder)
    p42=original43.load_pinned_parent(folder)
    p11=p42.load_parent(folder)
    p41=p11.load_original(folder)
    p40=p41.load_parent(folder)
    p26,srcpaths,providerpaths=p41.locate_sources_providers(root,folder,p40)
    sources=[p41.parse_version_file(p26,p40,p) for p in srcpaths]
    providers=[p41.parse_version_file(p26,p40,p) for p in providerpaths]
    exports={s['name'] for provider in providers for s in provider['symbols']
             if s['name'] and s['defined'] and s['binding'] in (1,2,10) and s['visibility'] in (0,3)}
    result=defaultdict(Counter);got_tags=Counter();total=0
    for path,source in zip(srcpaths,sources):
        groups=choose_weak_targets(source,exports)
        counts,got,n=read_weak_plt_words(p26,parent,path,groups)
        total+=n;got_tags[got]+=1
        for group,rows in counts.items():result[group].update(rows)
    if total!=18:raise Hold('WEAK_PLT_SITE_TOTAL_HOLD')
    for group,count in (('LOCAL_ZERO_NAME_IN_SIX',9),('LOCAL_ZERO_NAME_NOT_IN_SIX',7),('UNVERSIONED_WEAK_NAME_NOT_IN_SIX',2)):
        if sum(n for (dimension,cat),n in result[group].items() if dimension=='WORD')!=count:
            raise Hold('WEAK_PLT_GROUP_COUNTS_HOLD')
    categories={}
    for group,rows in sorted(result.items()):
        categories[group]={key:dict(sorted((c,v) for (dimension,c),v in rows.items() if dimension==key))
                           for key in ('WORD','LOW_BIT')}
    return {'milestone':'R40.4.3.7.45.2',
            'result':'WEAK_PLT_INITIAL_WORD_GEOMETRY_PINNED_PARENT_CHAIN_CORRECTED_STATIC_ONLY',
            'parent_r3744_sha_pin_and_stage_baseline_replayed':True,
            'original_r3745_sha_pinned_and_original_hold_preserved':True,
            'corrected_r3743_module_chain_readonly':True,
            'original_stage_modified':False,
            'source_elf_count':len(sources),'provider_elf_count':len(providers),
            'targeted_weak_plt_sites':total,
            'weak_plt_initial_target_categories_by_group':categories,
            'requester_dt_pltgot_categories':dict(sorted(got_tags.items())),
            'unrelocated_word_as_pointer_not_proven':True,
            'weak_symbol_runtime_semantics_verified':False,
            'lazy_binding_runtime_verified':False,
            'loader_namespace_or_symbol_interposition_verified':False,
            'guest_interpreter_path_resolved':False,'mapping_applied':False,
            'original_r26_source_provenance_authenticated':False,
            'historical_inventory_hashes_reverified':False,
            'runtime_tls_compatibility_verified':False,
            'transitive_dependency_closure_proven':False,
            'paths_symbols_or_words_exported':False,
            'firmware_write_authorized':False,'boot_authorized':False,
            'prune_authorized':False,'immutable_hold':'NOT_BOOTABLE'}


ORIGINAL_R3745 = 'R4043745-WEAK-PLT-INITIAL-TARGET-READONLY.py'
ORIGINAL_R3745_SHA256 = 'c3b95955df80e896196887fe922acd253d26948728939f1ea8349782feb73794'


def verify_original_r3745(folder):
    """Preserve the original failing script as exact evidence; no execution."""
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('SOURCE_DIRECTORY_HOLD')
    path=folder/ORIGINAL_R3745
    if path.is_symlink() or not path.is_file():
        raise Hold('ORIGINAL_R3745_MISSING_HOLD')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=ORIGINAL_R3745_SHA256:
        raise Hold('ORIGINAL_R3745_SHA_HOLD')
    return True


def main():
    parser=argparse.ArgumentParser(description='R3745.2 corrected read-only weak PLT initial-word classification; NOT_BOOTABLE')
    parser.add_argument('--rootfs',required=True,type=Path)
    parser.add_argument('--parent-dir',required=True,type=Path)
    a=parser.parse_args()
    try:
        verify_original_r3745(a.parent_dir)
        parent=load_parent(a.parent_dir)
        result=audit(a.rootfs,a.parent_dir,parent)
    except (Hold,OSError,RecursionError) as exc:
        result={'milestone':'R40.4.3.7.45.2','result':'HOLD',
                'hold_category':exc.category if isinstance(exc,Hold) else 'HOST_IO_OR_GRAPH_HOLD',
                'boot_authorized':False,'prune_authorized':False,
                'immutable_hold':'NOT_BOOTABLE'}
    except Exception:
        result={'milestone':'R40.4.3.7.45.2','result':'HOLD',
                'hold_category':'R3745_2_UNEXPECTED_STATIC_PARSER_HOLD',
                'boot_authorized':False,'prune_authorized':False,
                'immutable_hold':'NOT_BOOTABLE'}
    print(json.dumps(result,sort_keys=True))
    return 0 if result['result']=='WEAK_PLT_INITIAL_WORD_GEOMETRY_PINNED_PARENT_CHAIN_CORRECTED_STATIC_ONLY' else 2

if __name__=='__main__':raise SystemExit(main())
