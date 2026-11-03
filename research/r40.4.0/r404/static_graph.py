#!/usr/bin/env python3
"""R40.4.0 read-only stage/ELF/Lua candidate dependency crosswalk; never prunes.

Consumes the original R26 stage and verified R40.1-3 private/public evidence locally.
All paths stay in --private-out; --summary-out exports aggregate counts only.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys

# Direct script execution (python3 r404/static_graph.py) works from any cwd.
SCRIPT_ROOT=Path(__file__).resolve().parent.parent
if str(SCRIPT_ROOT) not in sys.path: sys.path.insert(0,str(SCRIPT_ROOT))
from r403 import union_inventory as r403
from r404.elf_static import ELFHold, parse_elf, lua_literals

R403_SOURCE_SHA='7f750452a520807bca6dd6084bf410e226c7bcb8e9f5fb227c4ee8ed72c4900c'
R403_VERIFIED_HASH_REPORT_SHA='bf029bfffc7f64cd4c9d7d010acc7d7d267546ed0ee9c4ee94b379362ab38771'
MAX_ELF=128*1024*1024
MAX_LUA=4*1024*1024
APP_PREFIX='rootfs/opt/koreader-compat/app/'
SCENARIO_STATUS={
 'double_pdf_reopen':'PRIOR_R40_0_2_TRACED_PASS_NOT_NEW_R404_TEST',
 'filemanager_only':'NOT_TESTED_HOLD',
 'ink_away_canvas_save_return':'PRIOR_R22_1_UNTRACED_PASS_R404_NOT_TESTED_HOLD',
 'epub_or_plain_text_reader':'NOT_TESTED_HOLD',
 'missing_font_locale_resource_fallback':'NOT_TESTED_HOLD',
 'optional_future_puzzle_pack':'NOT_BUILT_NOT_TESTED_HOLD'
}


def sha_bytes(blob):return hashlib.sha256(blob).hexdigest()


def read_exact_file(path,limit):
    """Read one staged regular file through O_NOFOLLOW, stable inode/mtime."""
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):raise ValueError('stage object not regular')
        if before.st_size>limit:raise FileTooLarge('bounded static analysis limit')
        chunks=[];n=0
        while True:
            chunk=os.read(fd,min(1024*1024,limit+1-n))
            if not chunk:break
            n+=len(chunk)
            if n>limit:raise FileTooLarge('bounded static analysis limit')
            chunks.append(chunk)
        after=os.fstat(fd)
        x=(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)
        y=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
        if x!=y or n!=before.st_size:raise ValueError('stage file changed during read')
        return b''.join(chunks)
    finally:os.close(fd)


class FileTooLarge(Exception):pass


def src_pins(root):
    # Pin vendored R40.3 verifier: no semantic regression in sensitive path logic.
    p=Path(__file__).resolve().parent.parent/'r403/union_inventory.py'
    if r403.digest(p)!=R403_SOURCE_SHA:raise ValueError('R40.3 source changed')
    if r403.digest(root)!=R403_VERIFIED_HASH_REPORT_SHA:raise ValueError('R40.3 verified hash report changed')


def expected_sha(record):
    value=record.get('sha256',record.get('sha256_digest',record.get('sha')))
    if not isinstance(value,str) or not r403.HEX64.fullmatch(value.lower()):raise ValueError('missing original R26 SHA')
    return value.lower()


def lua_candidates(method,literal,files):
    # Suffix-based lexical CANDIDATES ONLY. No inference about actual package.path or runtime resolution.
    if not literal or '\\' in literal or '\x00' in literal or literal.startswith('/') or '..' in literal.split('/'):
        return [],'UNRESOLVED_COMPUTED_OR_UNSAFE_HOLD'
    if method=='require':
        if '/' in literal:return [],'UNRESOLVED_REQUIRE_NONMODULE_HOLD'
        stem=literal.replace('.','/')
        suffixes=(stem+'.lua',stem+'/init.lua',stem+'.so')
    else:
        suffixes=(literal.lstrip('./'),)
    matches=sorted(f for f in files if any(f==('rootfs/'+s) or f.endswith('/'+s) for s in suffixes))
    return matches, 'STATIC_NAME_CANDIDATES_ONLY' if matches else 'NO_STAGED_LEXICAL_CANDIDATE_HOLD'


def inspect_static(stage,records,r26records,observed,expected_counts=(2070,1448,347)):
    regular={r for r,v in records.items() if v['type']=='regular'}
    known_elf={};known_lua={};elf_fail={};lua_fail={};seen_elf=0
    for rel in sorted(regular):
        full=stage.parent/rel
        if rel.lower().endswith('.lua'):
            try:
                raw=read_exact_file(full,MAX_LUA)
                if sha_bytes(raw)!=expected_sha(r26records[rel]):raise ValueError('R26 file mismatch during scan')
                refs=lua_literals(raw.decode('utf-8',errors='replace'))
                known_lua[rel]={'references':refs,'observed_open':rel in observed}
            except FileTooLarge:
                lua_fail[rel]='LUA_SIZE_LIMIT_HOLD'
        else:
            # The header check is an additional read; all files were SHA verified via R40.3 first.
            fd=os.open(full,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
            try:
                st=os.fstat(fd)
                if not stat.S_ISREG(st.st_mode):raise ValueError('stage mutated to nonregular')
                head=os.read(fd,4)
            finally:os.close(fd)
            if head!=b'\x7fELF':continue
            seen_elf+=1
            try:
                raw=read_exact_file(full,MAX_ELF)
                if sha_bytes(raw)!=expected_sha(r26records[rel]):raise ValueError('R26 ELF changed during scan')
                known_elf[rel]=parse_elf(raw)
                known_elf[rel]['observed_open']=rel in observed
            except FileTooLarge:elf_fail[rel]='ELF_SIZE_LIMIT_HOLD'
            except ELFHold as exc:elf_fail[rel]='ELF_PARSE_HOLD:'+str(exc)
    # Extension-based Lua detection is approximate; other interpreted source types stay UNKNOWN_HOLD.
    name_to_paths=defaultdict(set)
    for rel,info in records.items():
        if info['type'] in ('regular','symlink'):
            name_to_paths[PurePosixPath(rel).name].add(rel)
    for rel,info in known_elf.items():
        if info.get('soname'):name_to_paths[info['soname']].add(rel)
    elf_edges=[];elf_issues=Counter()
    for source,info in sorted(known_elf.items()):
        for target in info['needed']:
            matches=sorted(name_to_paths.get(target,()))
            choices=[]
            for match in matches:
                dest=known_elf.get(match)
                kind=records[match]['type']
                compatible=(dest is not None and dest['machine']==info['machine'] and dest['elf_class']==info['elf_class'] and dest['endianness']==info['endianness'])
                choices.append({'candidate_path':match,'type':kind,'parsed_elf_abi_compatible':compatible if kind=='regular' else None})
            status=('NO_STAGE_NAME_CANDIDATE_HOLD' if not choices else
                    'SINGLE_STATIC_NAME_CANDIDATE_NOT_RUNTIME_PROVEN' if len(choices)==1 else
                    'AMBIGUOUS_STATIC_NAME_CANDIDATES_HOLD')
            elf_issues[status]+=1
            elf_edges.append({'source':source,'soname_needed':target,'choices':choices,'status':status,
                              'source_observed_open':source in observed})
        if info['interpreter']:
            i=info['interpreter']
            if not i.startswith('/') or '\x00' in i or '..' in i.split('/'):
                interpreter={'requested':i,'candidate_stage_path':None,'status':'UNSAFE_OR_RELATIVE_INTERPRETER_HOLD'}
            else:
                target='rootfs/'+i.lstrip('/')
                kind=records.get(target,{}).get('type')
                interpreter={'requested':i,'candidate_stage_path':target if kind else None,'status':('INTERPRETER_STAGE_'+kind.upper()+'_NOT_RUNTIME_PROVEN') if kind else 'INTERPRETER_NOT_AT_STAGE_PATH_HOLD'}
            info['interpreter_candidate']=interpreter
            elf_issues[interpreter['status']]+=1
    lua_edges=[];lua_issues=Counter()
    for source,info in sorted(known_lua.items()):
        for req in info['references']:
            choices,status=lua_candidates(req['operation'],req['literal'],regular)
            lua_issues[status]+=1
            lua_edges.append({'source':source,'reference':req,'choices':choices,'status':status,
                              'source_observed_open':source in observed})
    counts=Counter(v['type'] for v in records.values())
    public={
        'verdict':'R40_4_0_STATIC_CANDIDATE_GRAPH_OBSERVED_NOT_CLOSED',
        'milestone':'R40.4.0',
        'scope':'one R40.0.2 synthetic PDF trace plus locally verified R26 ELF/Lua inventory; all static edges candidates only',
        'r26_manifest_status':'ALL_RECORDED_ENTRIES_MATCH_UNAUTHENTICATED',
        'r26_provenance_authenticated':False,
        'r26_inventory_entries_rehashed':len(records),
        'stage_regular_files':counts['regular'],
        'stage_directories':counts['directory'],
        'stage_symlinks':counts['symlink'],
        'runtime_observed_open_distinct_regular':len(observed),
        'stage_regular_unobserved_retained':counts['regular']-len(observed),
        'static_elf_objects_detected':seen_elf,
        'static_elf_objects_parsed':len(known_elf),
        'static_elf_parse_or_size_holds':len(elf_fail),
        'static_elf_objects_observed_open':sum(p in observed for p in known_elf),
        'elf_dt_needed_edges':len(elf_edges),
        'elf_candidate_status_counts':dict(elf_issues),
        'lua_files_scanned':len(known_lua),
        'lua_files_unscanned_holds':len(lua_fail),
        'lua_files_observed_open':sum(p in observed for p in known_lua),
        'lua_literal_reference_edges':len(lua_edges),
        'lua_candidate_status_counts':dict(lua_issues),
        'future_optional_puzzle_feature':'FUTURE_OPTIONAL_NOT_BUILT_NOT_TESTED_HOLD',
        'scenario_status':SCENARIO_STATUS,
        'raw_and_path_level_records_private':True,
        'complete_dependency_closure_proven':False,
        'runtime_edge_resolution_proven':False,
        'static_candidates_not_required_dependency_proof':True,
        'qemu_syscall_decoder_incomplete':True,
        'all_unobserved_staged_files_retained':True,
        'older_unknown_hold_entries_preserved':976,
        'safe_to_prune_inferred':False,
        'device_access_authorized':False,
        'boot_authorized':False,
        'firmware_write_authorized':False,
        'hardware_write_authorized':False,
        'file_removal_authorized':False,
        'immutable_hold':'NOT_BOOTABLE'
    }
    if expected_counts is not None and (len(records),counts['regular'],len(observed))!=expected_counts:
        raise ValueError('runtime or staged input count drift')
    private={
        'private':True,'immutable_hold':'NOT_BOOTABLE',
        'stage_root':str(stage),
        'observed_open_regular_stage_paths':sorted(observed),
        'elf':known_elf,'elf_holds':elf_fail,'elf_candidate_edges':elf_edges,
        'lua':known_lua,'lua_holds':lua_fail,'lua_candidate_edges':lua_edges,
        'not_a_prune_manifest':True
    }
    return public,private


def refuse_paths(stage, inputs, outputs):
    if len(set(p.resolve() for p in outputs))!=len(outputs):raise ValueError('outputs overlap')
    for out in outputs:
        r403.disjoint(stage,inputs,out)
        if any(out.resolve()==p.resolve() for p in inputs):raise ValueError('output matches input')


def create_report(path,content):
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        json.dump(content,f,sort_keys=True,indent=2);f.write('\n')


def main(argv=None):
    a=argparse.ArgumentParser(description=__doc__)
    for opt in ('stage','r26-inventory','r401-private','r401-summary','r402-private','r402-summary','r403-hash-summary','private-out','summary-out'):
        a.add_argument('--'+opt,required=True,type=Path)
    args=a.parse_args(argv)
    stage=args.stage
    if stage.name!='rootfs' or stage.is_symlink() or not stage.is_dir():raise ValueError('exact rootfs stage required')
    inputs=[args.r26_inventory,args.r401_private,args.r401_summary,args.r402_private,args.r402_summary,args.r403_hash_summary]
    outputs=[args.private_out,args.summary_out]
    refuse_paths(stage,inputs,outputs)
    src_pins(args.r403_hash_summary)
    if r403.digest(args.r402_summary)!=r403.EXPECTED_R402_SUMMARY_SHA256 or r403.digest(args.r402_private)!=r403.EXPECTED_R402_PRIVATE_SHA256:
        raise ValueError('source-bound R40.2 evidence mismatch')
    p401=r403.read_json(args.r401_private);s401=r403.read_json(args.r401_summary)
    p402=r403.read_json(args.r402_private);s402=r403.read_json(args.r402_summary)
    r26=r403.read_json(args.r26_inventory);s403=r403.read_json(args.r403_hash_summary)
    if Path(p401.get('stage','/invalid')).resolve()!=stage.resolve():raise ValueError('prior crosswalk stage path mismatch')
    records=r403.scan_outer(stage.parent)
    check=r403.summarize(stage.parent,p401,s401,p402,s402,r26)
    if check!=s403 or not check.get('r26_static_inventory_hash_reconciled') or check.get('r26_provenance_authenticated') is not False:
        raise ValueError('R26 hash report inconsistency')
    absset,relmap=r403.observed_union(records,p401,s401,p402,s402)
    observed=absset|set(relmap)
    r26records,schema=r403.parse_inventory(r26)
    if schema!='entries[]' or not r26records or set(r26records)!=set(records):raise ValueError('R26 inventory schema/path mismatch')
    public,private=inspect_static(stage,records,r26records,observed)
    public['source_r403_hash_report_sha256']=R403_VERIFIED_HASH_REPORT_SHA
    public['private_dependency_graph_sha256_expected']=None  # populated after serialization, never filenames
    # Write private data first to O_EXCL path, then counts-only public summary.
    encoded=(json.dumps(private,sort_keys=True,indent=2)+'\n').encode('utf-8')
    public['private_dependency_graph_sha256_expected']=sha_bytes(encoded)
    fd=os.open(args.private_out,os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(fd,'wb') as f:f.write(encoded)
    create_report(args.summary_out,public)
    print('R40_4_0_STATIC_CANDIDATE_GRAPH_OBSERVED_NOT_CLOSED; PRIVATE_PATHS_NOT_EXPORTED; NOT_BOOTABLE')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,KeyError,TypeError,IndexError,ELFHold,json.JSONDecodeError,FileTooLarge):
        print('R40_4_0_REFUSED; stage, provenance or source contract invalid; NOT_BOOTABLE',file=sys.stderr)
        sys.exit(1)
