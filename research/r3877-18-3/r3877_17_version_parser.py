#!/usr/bin/env python3
"""Bounded parser for GNU ELF32 ARM symbol version requirement and definition sections.
Does not resolve symbols or run guest code. Research and educational use only.
"""
import struct

class VersionHold(Exception):
    pass

SHT_STRTAB = 3
SHT_NOBITS = 8
SHT_VERDEF = 0x6ffffffd
SHT_VERNEED = 0x6ffffffe
MAX_SECTIONS = 2048
MAX_ENTRIES = 8192
MAX_VERSION_NAMES = 30000

def check(cond, why):
    if not cond: raise VersionHold(why)

def cstr(s,off):
    check(0<=off<len(s),'VERSION_STRING_OFFSET_INVALID')
    end=s.find(b'\0',off)
    check(end!=-1 and end-off<=512,'VERSION_STRING_NOT_TERMINATED_OR_LONG')
    v=s[off:end]
    check(v and all(32<=c<127 for c in v),'VERSION_STRING_NONASCII_OR_EMPTY')
    return v.decode('ascii')

def safe_unpack(fmt,buf,at,why):
    n=struct.calcsize(fmt)
    check(0<=at and at+n<=len(buf),why)
    return struct.unpack_from(fmt,buf,at)

def parse_version_sections(buf):
    check(len(buf)>=52 and buf[:7]==b'\x7fELF\x01\x01\x01','NOT_ELF32_LITTLE_ENDIAN')
    check(struct.unpack_from('<H',buf,18)[0]==40,'NOT_ARM_ELF')
    shoff=struct.unpack_from('<I',buf,32)[0]
    shentsz,shnum=struct.unpack_from('<HH',buf,46)
    check(40<=shentsz<=512 and 1<=shnum<=MAX_SECTIONS and shoff>=52 and shoff+shentsz*shnum<=len(buf),'SECTION_TABLE_UNAVAILABLE_OR_INVALID')
    sections=[]
    nobits_count=0
    nobits_non_file_extent_count=0
    for i in range(shnum):
        vals=safe_unpack('<IIIIIIIIII',buf,shoff+i*shentsz,'SECTION_HEADER_TRUNCATED')
        _name,typ,_flags,_addr,off,size,link,info,_align,entry=vals
        # SHT_NOBITS (e.g. .bss) has a conceptual sh_offset and a memory
        # sh_size, but contributes ZERO bytes to the ELF file (gABI).
        # Every file-backed section must still be entirely in bounds.
        if typ == SHT_NOBITS:
            nobits_count += 1
            if off > len(buf) or size > len(buf)-off:
                nobits_non_file_extent_count += 1
        else:
            check(off<=len(buf) and size<=len(buf)-off,'SECTION_DATA_OUT_OF_BOUNDS')
        sections.append({'typ':typ,'off':off,'size':size,'link':link,'info':info})
    req={}
    defs=set()
    sections_seen={'verneed':0,'verdef':0}
    n_total=0
    for sec in sections:
        typ=sec['typ']
        if typ not in (SHT_VERNEED,SHT_VERDEF): continue
        check(sec['link']<len(sections),'VERSION_STRING_TABLE_INDEX_INVALID')
        strs=sections[sec['link']]
        check(strs['typ']==SHT_STRTAB,'VERSION_STRING_TABLE_INVALID')
        strings=buf[strs['off']:strs['off']+strs['size']]
        raw=buf[sec['off']:sec['off']+sec['size']]
        count=sec['info']
        check(0<count<=MAX_ENTRIES,'VERSION_RECORD_COUNT_INVALID')
        offset=0
        visited=set()
        key='verneed' if typ==SHT_VERNEED else 'verdef'
        sections_seen[key]+=1
        check(sections_seen[key]==1,'MULTIPLE_VERSION_SECTIONS_UNSUPPORTED')
        for rec_i in range(count):
            check(offset not in visited,'VERSION_RECORD_CHAIN_LOOP')
            visited.add(offset)
            if typ==SHT_VERNEED:
                vn_version,vn_cnt,vn_file,vn_aux,vn_next=safe_unpack('<HHIII',raw,offset,'VERNEED_RECORD_TRUNCATED')
                check(vn_version==1 and 1<=vn_cnt<=MAX_ENTRIES and vn_aux>=16,'VERNEED_RECORD_INVALID')
                provider=cstr(strings,vn_file)
                aux_at=offset+vn_aux
                seen_aux=set()
                for j in range(vn_cnt):
                    check(aux_at not in seen_aux,'VERNEED_AUX_LOOP')
                    seen_aux.add(aux_at)
                    _hash,flags,_other,vna_name,vna_next=safe_unpack('<IHHII',raw,aux_at,'VERNEED_AUX_TRUNCATED')
                    name=cstr(strings,vna_name)
                    req.setdefault(provider,[]).append({'version':name,'weak':bool(flags&2)})
                    n_total+=1
                    check(n_total<=MAX_VERSION_NAMES,'VERSION_NAME_LIMIT')
                    if j+1<vn_cnt:
                        check(vna_next>=16,'VERNEED_AUX_CHAIN_SHORT')
                        aux_at+=vna_next
            else:
                vd_version,_flags,_idx,vd_cnt,_hash,vd_aux,vd_next=safe_unpack('<HHHHIII',raw,offset,'VERDEF_RECORD_TRUNCATED')
                check(vd_version==1 and 1<=vd_cnt<=MAX_ENTRIES and vd_aux>=20,'VERDEF_RECORD_INVALID')
                aux_at=offset+vd_aux
                seen_aux=set()
                for j in range(vd_cnt):
                    check(aux_at not in seen_aux,'VERDEF_AUX_LOOP')
                    seen_aux.add(aux_at)
                    vda_name,vda_next=safe_unpack('<II',raw,aux_at,'VERDEF_AUX_TRUNCATED')
                    name=cstr(strings,vda_name)
                    if j==0: defs.add(name)
                    n_total+=1
                    check(n_total<=MAX_VERSION_NAMES,'VERSION_NAME_LIMIT')
                    if j+1<vd_cnt:
                        check(vda_next>=8,'VERDEF_AUX_CHAIN_SHORT')
                        aux_at+=vda_next
                vn_next=vd_next
            if rec_i+1<count:
                check(vn_next>=16 if typ==SHT_VERNEED else vn_next>=20,'VERSION_RECORD_CHAIN_SHORT')
                offset+=vn_next
    return {'needs':{lib:sorted(set((v['version'],v['weak']) for v in vs)) for lib,vs in req.items()},
            'defines':sorted(defs), 'sections_seen':sections_seen,
            'nobits_section_count':nobits_count,
            'nobits_non_file_extent_count':nobits_non_file_extent_count}

def normalize_interp(blob):
    check(len(blob)>=52 and blob[:7]==b'\x7fELF\x01\x01\x01','NOT_ELF32_LITTLE_ENDIAN')
    phoff=struct.unpack_from('<I',blob,28)[0]
    sz,n=struct.unpack_from('<HH',blob,42)
    check(32<=sz<=256 and n<=128 and phoff>=52 and phoff+n*sz<=len(blob),'PROGRAM_HEADERS_INVALID')
    paths=[]
    for i in range(n):
        typ,off,_va,_pa,fsz,_memsz,_flags,_align=struct.unpack_from('<IIIIIIII',blob,phoff+i*sz)
        if typ!=3: continue
        check(0<fsz<1024 and off+fsz<=len(blob),'INTERP_BOUNDS_INVALID')
        raw=blob[off:off+fsz]
        path=raw.split(b'\0',1)[0]
        check(raw[len(path):] and not any(raw[len(path):]),'INTERP_TERMINATION_INVALID')
        check(path.startswith(b'/') and len(path)<512,'INTERP_PATH_INVALID')
        paths.append(path.decode('ascii'))
    check(len(paths)<=1,'MULTIPLE_INTERPRETERS')
    return paths[0] if paths else None
