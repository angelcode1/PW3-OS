#!/usr/bin/env python3
"""Host-only ELF32 ARM GNU symbol versions, .ARM.attributes and $ORIGIN audit.

Never starts Kindle SSH, runs target ELF files, mounts anything, or writes to
its stage. This is not an authenticated stage hash/recovery/boot evaluation.
"""
import argparse
import json
import os
from pathlib import Path
import posixpath
import re
import struct
import sys

import pw3_r3877_81_glibc_closure as prior

APP = 'opt/koreader-compat/app/luajit'
LIBDIR = 'opt/koreader-compat/gnu/lib'
KNOWN = ('ld-linux.so.3', 'libm.so.6', 'libdl.so.2', 'libgcc_s.so.1', 'libc.so.6')
NAME = re.compile(r'^[A-Za-z0-9_.+\-]{1,128}$')
VERNEED = 0x6ffffffe
VERDEF = 0x6ffffffd
ARMATTR = 0x70000003

class Refused(ValueError): pass


def span(b, pos, n):
    if pos < 0 or n < 0 or pos > len(b) or n > len(b) - pos:
        raise Refused('SECTION_RANGE_INVALID')
    return b[pos:pos+n]


def u16(b, off): return struct.unpack('<H', span(b, off, 2))[0]
def u32(b, off): return struct.unpack('<I', span(b, off, 4))[0]


def cstr(b, off):
    if off < 0 or off >= len(b): raise Refused('STRING_OFFSET_INVALID')
    end = b.find(b'\0', off)
    if end < 0: raise Refused('STRING_TERMINATOR_MISSING')
    raw = b[off:end]
    if len(raw) > 128: raise Refused('STRING_TOO_LONG')
    try: return raw.decode('ascii')
    except UnicodeDecodeError: raise Refused('NONASCII_STRING') from None


def metadata_sections(b):
    if len(b) < 52 or b[:7] != b'\x7fELF\x01\x01\x01':
        raise Refused('NOT_ELF32_LE')
    off, entsize, n, shnames = u32(b,32), u16(b,46), u16(b,48),u16(b,50)
    if n == 0 or off == 0:
        return []   # stripped section table: explicitly unresolved
    if entsize != 40 or n > 4096 or shnames >= n:
        raise Refused('SECTION_HEADER_LAYOUT_INVALID')
    span(b,off,n*entsize)
    secs=[]
    for i in range(n):
        row=struct.unpack('<10I',b[off+i*entsize:off+(i+1)*entsize])
        name,typ,flags,addr,soff,size,link,info,align,esize=row
        if typ!=8: span(b,soff,size)
        secs.append({'nameoff':name,'type':typ,'offset':soff,'size':size,'link':link,'info':info,'entsize':esize})
    strings=span(b,secs[shnames]['offset'],secs[shnames]['size'])
    for sec in secs:
        sec['name']=cstr(strings,sec['nameoff'])
    return secs


def section_bytes(b, s): return span(b,s['offset'],s['size'])


def linked_strings(b, sections, sec):
    n=sec['link']
    if n >= len(sections) or sections[n]['type'] != 3:
        raise Refused('GNU_VERSION_LINKED_STRTAB_INVALID')
    return section_bytes(b,sections[n])


def parse_verneed(b, sections):
    sec=[x for x in sections if x['type']==VERNEED]
    if len(sec)>1: raise Refused('DUPLICATE_VERNEED_SECTION')
    if not sec: return None
    s=sec[0]; raw=section_bytes(b,s); strings=linked_strings(b,sections,s)
    out={}; off=0; visited=set()
    for _ in range(256):
        if off in visited: raise Refused('VERNEED_LOOP')
        visited.add(off)
        if off+16>len(raw): raise Refused('VERNEED_RECORD_BOUNDS')
        ver,cnt,name,aux,nextrec=struct.unpack_from('<HHIII',raw,off)
        if ver!=1 or not 1<=cnt<=128: raise Refused('VERNEED_FORMAT_INVALID')
        lib=cstr(strings,name)
        if not NAME.fullmatch(lib):raise Refused('VERNEED_LIBRARY_INVALID')
        names=out.setdefault(lib,set()); p=off+aux; a_seen=set()
        for _j in range(cnt):
            if p in a_seen or p+16>len(raw):raise Refused('VERNEED_AUX_BOUNDS')
            a_seen.add(p)
            h,flags,other,nameidx,nxt=struct.unpack_from('<IHHII',raw,p)
            vname=cstr(strings,nameidx)
            if not NAME.fullmatch(vname):raise Refused('VERNEED_VERSION_NAME_INVALID')
            names.add(vname)
            if _j<cnt-1 and nxt==0:raise Refused('VERNEED_AUX_CHAIN_SHORT')
            p+=nxt
        if nextrec==0: return {k:sorted(v) for k,v in sorted(out.items())}
        if nextrec<16 or off+nextrec>=len(raw):raise Refused('VERNEED_NEXT_INVALID')
        off+=nextrec
    raise Refused('VERNEED_TOO_MANY_RECORDS')


def parse_verdef(b,sections):
    sec=[x for x in sections if x['type']==VERDEF]
    if len(sec)>1:raise Refused('DUPLICATE_VERDEF_SECTION')
    if not sec:return None
    s=sec[0]; raw=section_bytes(b,s); strings=linked_strings(b,sections,s)
    off=0; names=set(); seen=set()
    for _ in range(1024):
        if off in seen or off+20>len(raw):raise Refused('VERDEF_RECORD_BOUNDS')
        seen.add(off)
        version,flags,ndx,cnt,h,aux,nxt=struct.unpack_from('<HHHHIII',raw,off)
        if version!=1 or not 1<=cnt<=16 or off+aux+8>len(raw):raise Refused('VERDEF_RECORD_INVALID')
        nameidx,auxnext=struct.unpack_from('<II',raw,off+aux)
        name=cstr(strings,nameidx)
        if not NAME.fullmatch(name):raise Refused('VERDEF_VERSION_INVALID')
        names.add(name)
        if nxt==0:return sorted(names)
        if nxt<20 or off+nxt>=len(raw):raise Refused('VERDEF_NEXT_INVALID')
        off+=nxt
    raise Refused('VERDEF_TOO_MANY_RECORDS')


def uleb(b,i,end):
    v=0
    for k in range(5):
        if i>=end:raise Refused('ARM_ULEB_TRUNCATED')
        z=b[i];i+=1;v|=(z&127)<<(7*k)
        if not z&128:return v,i
    raise Refused('ARM_ULEB_TOO_LONG')


def arm_vfp_args(b,sections):
    sec=[x for x in sections if x['name']=='.ARM.attributes' or x['type']==ARMATTR]
    if len(sec)>1: raise Refused('ARM_ATTRIBUTES_DUPLICATE')
    if not sec:return {'status':'SECTION_ABSENT','tag_value':None}
    raw=section_bytes(b,sec[0]);
    if not raw or raw[0]!=ord('A'):raise Refused('ARM_ATTRIBUTES_FORMAT')
    i=1; values=[]; vendors=[]
    while i<len(raw):
        n=u32(raw,i)
        if n<6 or i+n>len(raw):raise Refused('ARM_VENDOR_LENGTH_INVALID')
        vend=cstr(raw,i+4); vendors.append(vend)
        j=i+4+len(vend)+1; end=i+n
        if vend=='aeabi':
            while j<end:
                tag,j2=uleb(raw,j,end)
                if j2+4>end:raise Refused('ARM_SUBSECTION_BOUNDS')
                length=u32(raw,j2)
                if length<j2+4-j or j+length>end:raise Refused('ARM_SUBSECTION_LENGTH')
                subend=j+length
                if tag==1:
                    at=j2+4
                    while at<subend:
                        typ,at=uleb(raw,at,subend)
                        if typ in (4,5,65,67):
                            word=cstr(raw,at);at+=len(word)+1
                        elif typ==32:
                            _,at=uleb(raw,at,subend)
                            word=cstr(raw,at);at+=len(word)+1
                        else:
                            val,at=uleb(raw,at,subend)
                            if typ==28: values.append(val)
                j=subend
        i=end
    if len(set(values))>1:raise Refused('ARM_VFP_ARGS_CONFLICTING')
    if not values:return {'status':'TAG_ABSENT','tag_value':None}
    val=values[0]
    return {'status':{0:'BASE_AAPCS',1:'VFP_AAPCS',2:'TOOLCHAIN_SPECIFIC',3:'BOTH_COMPATIBLE'}.get(val,'UNKNOWN_VALUE'), 'tag_value':val}


def origin_report(root,app,paths):
    directory=posixpath.dirname(app)
    out=[]
    for raw in paths:
        for element in raw.split(':'):
            if element.startswith('$ORIGIN/'):
                suffix=element[len('$ORIGIN/'):]
            elif element.startswith('${ORIGIN}/'):
                suffix=element[len('${ORIGIN}/'):]
            else:
                out.append('UNSAFE_OR_UNKNOWN_RPATH');continue
            if len(suffix)>200 or not suffix or '$' in suffix or '\\' in suffix or any(x not in ('..','.') and not re.fullmatch(r'[A-Za-z0-9_.+\-]+',x) for x in suffix.split('/')):
                out.append('UNSAFE_OR_UNKNOWN_RPATH');continue
            resolved=posixpath.normpath(posixpath.join(directory,suffix))
            if not resolved.startswith('opt/koreader-compat/'):
                out.append('RPATH_ESCAPES_APP_BUNDLE');continue
            cur=root
            status='BUNDLE_DIRECTORY_PRESENT'
            for part in resolved.split('/'):
                cur=cur/part
                if cur.is_symlink() or not cur.is_dir():
                    status='BUNDLE_DIRECTORY_MISSING_OR_SYMLINK';break
            if status=='BUNDLE_DIRECTORY_PRESENT' and resolved==LIBDIR:
                status='MATCHES_GNU_PROVIDER_DIRECTORY'
            out.append(status)
    return out


def inspect(stage):
    root=Path(stage).expanduser()
    # Preserve R81's fail-closed basename and provider index semantics.
    prior_report=prior.audit(root)
    if not prior_report['all_needed_names_unique_regular']:
        raise Refused('R81_NOT_UNIQUE_REGULAR_PROVIDER')
    root=Path(root)
    needed_objects=[('luajit',APP)] + [(x['name'],x['stage_relative_path']) for x in prior_report['provider_list']]
    objs={}; counts={'required_versions':0,'matched_versions':0,'missing_versions':0,'versions_without_definition_table':0}
    for name,path in needed_objects:
        # We intentionally accept only the R81-listed GNU provider directory.
        if name!='luajit' and path != f'{LIBDIR}/{name}':
            raise Refused('PROVIDER_NOT_IN_PINNED_GNU_LIB_DIR')
        current=root
        for part in path.split('/')[:-1]:
            current=current/part
            if current.is_symlink() or not current.is_dir():raise Refused('PROVIDER_PARENT_UNTRUSTED')
        buf=prior.raw_file(root/path)
        prior_elf=prior.parse_elf(buf)
        secs=metadata_sections(buf)
        objects=dict(section_table_present=bool(secs),arm_vfp_args=arm_vfp_args(buf,secs),
                     version_needs=parse_verneed(buf,secs), version_definitions=parse_verdef(buf,secs),
                     has_pt_interp=bool(prior_elf['interpreter']),
                     float_e_flags=prior_elf['float_flag'])
        if name=='luajit':
            objects['rpath_resolution_categories']=origin_report(root,APP,prior_elf['rpath_values'])
            objects['raw_rpath_disclosed']=False
        objs[name]=objects
    status=[]
    for name, x in objs.items():
        versions=x['version_needs']
        if versions is None:
            status.append({'consumer':name,'status':'VERSION_NEEDS_SECTION_ABSENT_UNRESOLVED'})
            continue
        for lib, required in sorted(versions.items()):
            provider=objs.get(lib)
            if provider is None:
                status.append({'consumer':name,'provider':lib,'status':'VERSION_PROVIDER_NOT_SELECTED'})
                counts['missing_versions']+=len(required)
                continue
            defined=provider['version_definitions']
            for v in required:
                counts['required_versions']+=1
                if defined is None:
                    counts['versions_without_definition_table']+=1
                    reason='PROVIDER_VERSION_TABLE_ABSENT'
                elif v not in defined:
                    counts['missing_versions']+=1
                    reason='REQUIRED_VERSION_NOT_EXPORTED'
                else:
                    counts['matched_versions']+=1
                    reason='NAME_PRESENT_NOT_SYMBOL_BINDING_PROVEN'
                status.append({'consumer':name,'provider':lib,'version':v,'status':reason})
    abi_warnings=[]
    for name,obj in objs.items():
        val=obj['arm_vfp_args']['tag_value']
        if val in (1,2) or obj['arm_vfp_args']['status']=='UNKNOWN_VALUE':
            abi_warnings.append({'object':name,'category':'ARM_VFP_ARGS_POTENTIAL_CONFLICT'})
    return {
        'objects':objs, 'symbol_version_checks':status, 'counts':counts,
        'arm_vfp_warnings':abi_warnings,
        'shared_provider_pt_interp_warning_is_not_by_itself_loader_failure':True,
        'same_stage_bytes_reverified_against_R26':False,
        'stage_regular_file_count_R81':prior_report['stage_regular_file_count'],
        'old_kernel_runtime_verified':False,
        'actual_loader_resolution_verified':False,
        'loader_symbol_resolution_verified':False,
        'manual_one_shot_device_execution_authorized':False,
    }


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage',required=True)
    ap.add_argument('--acknowledge-mac-only-review',action='store_true')
    args=ap.parse_args(argv)
    out={'milestone':'R3877.82','result':'HOLD','immutable_hold':'NOT_BOOTABLE',
         'hold_category':'HOST_ONLY_REVIEW_NOT_AUTHORIZED',
         'kindle_access_performed':False,'device_execution_performed':False,
         'stage_files_modified':False,'boot_hooks_modified':False,
         'recovery_verified':False,'koreader_device_runtime_verified':False}
    if args.acknowledge_mac_only_review:
        try:
            out['review']=inspect(args.stage)
            out['hold_category']='GLIBC_SYMBOL_BINDING_AND_DEVICE_LOADER_STILL_UNVERIFIED'
        except (prior.Refused,Refused, OSError, ValueError,struct.error,UnicodeError) as exc:
            out['hold_category']='STATIC_GLIBC_ABI_REVIEW_REFUSED'
            if isinstance(exc,(Refused,prior.Refused)):
                out['offline_refusal_code']=str(exc) if re.fullmatch('[A-Z0-9_]+',str(exc)) else 'STATIC_PARSE_REFUSED'
    print(json.dumps(out,sort_keys=True,separators=(',',':')))
    return 2

if __name__=='__main__':sys.exit(main())
