#!/usr/bin/env python3
"""Bounded, static-only ELF and Lua literal readers. No ldd/exec/mmap/device."""
import re
import struct

ELF_MAGIC=b'\x7fELF'
PT_LOAD=1
PT_DYNAMIC=2
PT_INTERP=3
DT_NULL=0
DT_NEEDED=1
DT_STRTAB=5
DT_STRSZ=10
DT_SONAME=14
DT_RPATH=15
DT_RUNPATH=29
MAX_PHDRS=4096
MAX_DYN_ENTRIES=100_000

class ELFHold(ValueError): pass


def _range(blob,offset,size):
    if type(offset)!=int or type(size)!=int or offset < 0 or size<0 or offset > len(blob) or size > len(blob)-offset:
        raise ELFHold('invalid_offset_or_size')
    return blob[offset:offset+size]


def _unpack(fmt,blob,offset):
    raw=_range(blob,offset,struct.calcsize(fmt))
    return struct.unpack(fmt,raw)


def _cstring(buf, offset):
    if offset<0 or offset>=len(buf):raise ELFHold('dynamic_string_offset_invalid')
    end=buf.find(b'\0',offset)
    if end<0:raise ELFHold('dynamic_string_unterminated')
    return buf[offset:end].decode('utf-8',errors='replace')


def parse_elf(blob):
    """Return data-only ELF metadata. Raises ELFHold on malformed ELF, never executes."""
    if not isinstance(blob,bytes) or not blob.startswith(ELF_MAGIC): raise ELFHold('not_elf')
    if len(blob)<52:raise ELFHold('short_elf')
    klass,endian=blob[4],blob[5]
    if klass not in (1,2) or endian not in (1,2) or blob[6]!=1:raise ELFHold('bad_elf_ident')
    e='<' if endian==1 else '>'
    if klass==2 and len(blob)<64: raise ELFHold('short_elf64')
    if klass==1:
        header=_unpack(e+'HHIIIIIHHHHHH',blob,16)
        etype,machine,eversion,entry,phoff,shoff,flags,ehsize,phentsize,phnum,shentsize,shnum,shstridx=header
        pfmt=e+'IIIIIIII';dynfmt=e+'iI'; minph=32
    else:
        header=_unpack(e+'HHIQQQIHHHHHH',blob,16)
        etype,machine,eversion,entry,phoff,shoff,flags,ehsize,phentsize,phnum,shentsize,shnum,shstridx=header
        pfmt=e+'IIQQQQQQ';dynfmt=e+'qQ';minph=56
    if eversion!=1 or phnum>MAX_PHDRS or phentsize<minph or (phnum and phoff==0):raise ELFHold('bad_program_headers')
    if phnum and (phoff>len(blob) or phnum*phentsize>len(blob)-phoff):raise ELFHold('program_headers_out_of_range')
    phs=[]
    for i in range(phnum):
        vals=_unpack(pfmt,blob,phoff+i*phentsize)
        if klass==1:
            ptype,off,vaddr,paddr,filesz,memsz,pflags,align=vals
        else:
            ptype,pflags,off,vaddr,paddr,filesz,memsz,align=vals
        if ptype in (PT_LOAD,PT_DYNAMIC,PT_INTERP): _range(blob,off,filesz)
        phs.append(dict(type=ptype,offset=off,vaddr=vaddr,filesz=filesz,memsz=memsz))
    interp=None
    if len([p for p in phs if p['type']==PT_INTERP])>1:raise ELFHold('multiple_interpreters')
    for p in phs:
        if p['type']==PT_INTERP:
            interp=_cstring(_range(blob,p['offset'],p['filesz']),0)
    dyn=[p for p in phs if p['type']==PT_DYNAMIC]
    if len(dyn)>1:raise ELFHold('multiple_dynamic_segments')
    tags=[]; names=[];soname=None;rpath=None;runpath=None
    if dyn:
        seg=dyn[0]; step=struct.calcsize(dynfmt)
        if seg['filesz']%step:raise ELFHold('partial_dynamic_entry')
        if seg['filesz']//step>MAX_DYN_ENTRIES:raise ELFHold('too_many_dynamic_entries')
        saw_null=False
        for i in range(seg['filesz']//step):
            tag,value=_unpack(dynfmt,blob,seg['offset']+i*step)
            if tag==DT_NULL:
                saw_null=True;break
            tags.append((tag,value))
        if not saw_null: raise ELFHold('unterminated_dynamic_segment')
        d=dict(tags)
        if any(t in d for t in (DT_NEEDED,DT_SONAME,DT_RPATH,DT_RUNPATH)):
            if DT_STRTAB not in d or DT_STRSZ not in d:raise ELFHold('missing_dynamic_string_table')
            ptr=d[DT_STRTAB]; length=d[DT_STRSZ]
            candidates=[p for p in phs if p['type']==PT_LOAD and p['vaddr']<=ptr<p['vaddr']+p['filesz']]
            if len(candidates)!=1:raise ELFHold('dynamic_string_table_unmapped')
            p=candidates[0]; st_off=p['offset']+(ptr-p['vaddr'])
            # Require table to remain inside its file-backed PT_LOAD mapping.
            if length>p['filesz']-(ptr-p['vaddr']):raise ELFHold('dynamic_string_table_overruns_load')
            strtab=_range(blob,st_off,length)
            names=[_cstring(strtab,v) for t,v in tags if t==DT_NEEDED]
            soname=_cstring(strtab,d[DT_SONAME]) if DT_SONAME in d else None
            rpath=_cstring(strtab,d[DT_RPATH]) if DT_RPATH in d else None
            runpath=_cstring(strtab,d[DT_RUNPATH]) if DT_RUNPATH in d else None
    return {
        'elf_class':32 if klass==1 else 64,
        'endianness':'little' if endian==1 else 'big',
        'machine':machine,
        'type':etype,
        'arm_float_abi':'hard' if machine==40 and flags & 0x400 else 'soft' if machine==40 and flags & 0x200 else 'unspecified',
        'interpreter':interp,
        'needed':names,
        'soname':soname,
        'rpath':rpath,
        'runpath':runpath,
        'has_pt_dynamic':bool(dyn),
    }

# Find only lexical candidates; dynamic/computed requires and FFI loads remain UNKNOWN_HOLD.
_LUA_REF=re.compile(r'(?<![A-Za-z0-9_])\b(require|dofile|loadfile)\s*(?:\(\s*([\'\"])(.{1,255}?)\2\s*\)|([\'\"])(.{1,255}?)\4)',re.S)


def lua_literals(text):
    if not isinstance(text,str):raise ValueError('Lua source must be text')
    # Very conservative: ignore whole-line -- comments; multi-line comments and strings are NOT lexed.
    text='\n'.join('' if line.lstrip().startswith('--') else line for line in text.splitlines())
    results=[]
    for m in _LUA_REF.finditer(text):
        method=m.group(1); val=m.group(3) if m.group(3) is not None else m.group(5)
        if val and '\\' not in val and '\x00' not in val and '\n' not in val and '\r' not in val:
            results.append({'operation':method,'literal':val})
    return results
