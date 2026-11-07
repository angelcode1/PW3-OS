#!/usr/bin/env python3
"""Bounded ELF32 ARM dynamic-symbol / GNU version-index / relocation parser.

Research-only offline parser: never loads or executes target code.
The output is candidate metadata, not proof of ld.so runtime binding.
"""
import struct

class BindingHold(Exception):
    pass

SHT_NOBITS=8
SHT_DYNSYM=11
SHT_REL=9
SHT_RELA=4
SHT_STRTAB=3
SHT_VERDEF=0x6ffffffd
SHT_VERNEED=0x6ffffffe
SHT_VERSYM=0x6fffffff
MAX_SECTIONS=2048
MAX_SYMBOLS=300000
MAX_RELOCATIONS=1000000
MAX_VERSION_RECORDS=16000
MAX_NAME=4096


def ensure(cond, error):
    if not cond: raise BindingHold(error)


def unpack(fmt, b, off, err):
    n=struct.calcsize(fmt)
    ensure(0<=off and n<=len(b)-off,err)
    return struct.unpack_from(fmt,b,off)


def read_name(b, off):
    ensure(0<=off<len(b),'NAME_OFFSET_OUT_OF_BOUNDS')
    end=b.find(b'\0',off,min(len(b),off+MAX_NAME+1))
    ensure(end>off and end-off<=MAX_NAME,'NAME_NOT_TERMINATED_OR_EMPTY')
    name=b[off:end]
    ensure(all(32<=x<127 for x in name),'NAME_INVALID_BYTES')
    return name.decode('ascii')


def parse(blob):
    ensure(len(blob)>=52 and blob[:7]==b'\x7fELF\x01\x01\x01','ELF32_LE_REQUIRED')
    ensure(unpack('<H',blob,18,'MACHINE_MISSING')[0]==40,'ARM_MACHINE_REQUIRED')
    shoff=unpack('<I',blob,32,'SECTION_TABLE_MISSING')[0]
    shentsize,shnum=unpack('<HH',blob,46,'SECTION_COUNT_MISSING')
    ensure(40<=shentsize<=512 and 1<=shnum<=MAX_SECTIONS and shoff>=52 and
           shoff+shentsize*shnum<=len(blob),'SECTION_TABLE_BAD_BOUNDS')
    sections=[]
    for i in range(shnum):
        name,typ,flags,va,off,size,link,info,align,entsize=unpack(
            '<IIIIIIIIII',blob,shoff+i*shentsize,'SECTION_TRUNCATED')
        if typ!=SHT_NOBITS:
            ensure(off<=len(blob) and size<=len(blob)-off,'SECTION_DATA_OUT_OF_BOUNDS')
        sections.append(dict(typ=typ,flags=flags,off=off,size=size,link=link,info=info,entsize=entsize))
    def data(sec): return blob[sec['off']:sec['off']+sec['size']]
    def linked_strings(sec):
        ensure(0<=sec['link']<len(sections),'LINKED_STRING_TABLE_INDEX_INVALID')
        ref=sections[sec['link']]
        ensure(ref['typ']==SHT_STRTAB,'LINKED_STRING_TABLE_INVALID')
        return data(ref)
    dynsym_idx=[i for i,s in enumerate(sections) if s['typ']==SHT_DYNSYM]
    ensure(len(dynsym_idx)==1,'DYNSYM_MISSING_OR_MULTIPLE')
    dynidx=dynsym_idx[0]
    ds=sections[dynidx]
    ensure(ds['entsize']==16 and ds['size']%16==0 and
           1<=ds['size']//16<=MAX_SYMBOLS,'DYNSYM_ENTRY_COUNT_INVALID')
    names=linked_strings(ds)
    symbols=[]
    for i in range(ds['size']//16):
        st_name,value,size,info,other,shndx=unpack('<IIIBBH',data(ds),i*16,'DYNSYM_TRUNCATED')
        name=read_name(names,st_name) if st_name else ''
        symbols.append(dict(name=name,defined=shndx!=0,bind=info>>4,
                            typ=info&15,visibility=other&3,shndx=shndx))

    vsecs=[s for s in sections if s['typ']==SHT_VERSYM]
    ensure(len(vsecs)<=1,'MULTIPLE_VERSYM_SECTIONS')
    vers=[1]*len(symbols)
    if vsecs:
        sec=vsecs[0]
        ensure(sec['link']==dynidx,'VERSYM_MUST_LINK_TO_DYNSYM')
        ensure(sec['size']==len(symbols)*2 and sec['entsize'] in (0,2),'VERSYM_SIZE_MISMATCH')
        raw=data(sec)
        vers=list(struct.unpack('<'+'H'*len(symbols),raw))
    needidx={}
    defidx={}
    count_versions=0
    for sec in sections:
        if sec['typ'] not in (SHT_VERNEED,SHT_VERDEF): continue
        strings=linked_strings(sec)
        raw=data(sec)
        count=sec['info']
        ensure(0<count<=MAX_VERSION_RECORDS,'VERSION_SECTION_COUNT_INVALID')
        seen=set()
        base=0
        for ri in range(count):
            ensure(base not in seen,'VERSION_CHAIN_LOOP')
            seen.add(base)
            if sec['typ']==SHT_VERNEED:
                vn_ver,vn_cnt,filename,aux,nextrel=unpack('<HHIII',raw,base,'VERNEED_TRUNCATED')
                ensure(vn_ver==1 and 1<=vn_cnt<=MAX_VERSION_RECORDS and aux>=16,'VERNEED_HEADER_INVALID')
                provider=read_name(strings,filename)
                apos=base+aux
                for ai in range(vn_cnt):
                    h,flags,other,nameoff,nextaux=unpack('<IHHII',raw,apos,'VERNEED_AUX_TRUNCATED')
                    idx=other&0x7fff
                    ensure(idx>=2 and idx not in needidx,'VERNEED_INDEX_DUPLICATE_OR_RESERVED')
                    needidx[idx]=(provider,read_name(strings,nameoff),bool(flags&2))
                    count_versions+=1
                    ensure(count_versions<=MAX_VERSION_RECORDS,'VERSION_COUNT_EXCESSIVE')
                    if ai+1<vn_cnt:
                        ensure(nextaux>=16,'VERNEED_AUX_LINK_INVALID')
                        apos+=nextaux
            else:
                vd_ver,flags,idx,vdcnt,h,aux,nextrel=unpack('<HHHHIII',raw,base,'VERDEF_TRUNCATED')
                ensure(vd_ver==1 and idx>=1 and vdcnt>=1 and aux>=20,'VERDEF_HEADER_INVALID')
                a_name,a_next=unpack('<II',raw,base+aux,'VERDEF_AUX_TRUNCATED')
                ensure(idx not in defidx,'VERDEF_DUPLICATE_INDEX')
                defidx[idx]=read_name(strings,a_name)
                count_versions+=1
                ensure(count_versions<=MAX_VERSION_RECORDS,'VERSION_COUNT_EXCESSIVE')
            if ri+1<count:
                ensure(nextrel >= (16 if sec['typ']==SHT_VERNEED else 20),'VERSION_NEXT_LINK_INVALID')
                base+=nextrel
                ensure(base<len(raw),'VERSION_NEXT_OUT_OF_BOUNDS')
    for i,sym in enumerate(symbols):
        idx=vers[i]&0x7fff
        sym['version_hidden']=bool(vers[i]&0x8000)
        sym['version_index']=idx
        if idx<2:
            sym['version']=None
            sym['version_provider']=None
            sym['version_weak']=False
        elif sym['defined']:
            ensure(idx in defidx,'DEFINED_VERSION_INDEX_UNKNOWN')
            sym['version']=defidx[idx]
            sym['version_provider']=None
            sym['version_weak']=False
        else:
            ensure(idx in needidx,'UNDEFINED_VERSION_INDEX_UNKNOWN')
            provider,vname,weak=needidx[idx]
            sym['version']=vname
            sym['version_provider']=provider
            sym['version_weak']=weak
    exports=[]
    for s in symbols:
        if s['defined'] and s['name'] and s['bind'] in (1,2,10) and s['visibility'] not in (1,2):
            # hidden or internal visibility excluded; global, weak, GNU-unique supported.
            exports.append({k:s[k] for k in ('name','bind','typ','version','version_hidden')})
    imports=[]
    for i,s in enumerate(symbols):
        if not s['defined'] and s['name'] and s['bind'] in (1,2,10):
            imports.append({'symidx':i,**{k:s[k] for k in ('name','bind','typ','version','version_provider','version_hidden','version_weak')}})
    reloc_types={}
    reloc_count=0
    import_reloc_indices=set()
    reloc_symbol_references=0
    for sec in sections:
        if sec['typ'] not in (SHT_REL,SHT_RELA) or not (sec['flags']&2): continue
        ensure(sec['link']==dynidx,'ALLOC_RELOC_NOT_LINKED_TO_DYNSYM')
        unit=8 if sec['typ']==SHT_REL else 12
        ensure(sec['entsize'] in (0,unit) and sec['size']%unit==0,'RELOCATION_SECTION_SIZE_INVALID')
        reloc_count+=sec['size']//unit
        ensure(reloc_count<=MAX_RELOCATIONS,'RELOCATION_COUNT_EXCESSIVE')
        raw=data(sec)
        for at in range(0,len(raw),unit):
            place,info=unpack('<II',raw,at,'RELOC_TRUNCATED')
            symidx=info>>8
            rtype=info&255
            ensure(symidx<len(symbols),'RELOC_SYMBOL_INDEX_OUT_OF_BOUNDS')
            reloc_types[str(rtype)]=reloc_types.get(str(rtype),0)+1
            if symidx:
                reloc_symbol_references+=1
                if not symbols[symidx]['defined']:
                    import_reloc_indices.add(symidx)
    return dict(exports=exports,imports=imports,
                relocated_imports=[imp for imp in imports if imp['symidx'] in import_reloc_indices],
                dynsym_count=len(symbols),import_count=len(imports),export_count=len(exports),
                reloc_count=reloc_count,reloc_symbol_references=reloc_symbol_references,
                relocation_types=reloc_types, version_need_indices=len(needidx),version_def_indices=len(defidx),
                n_allocated_reloc_sections=sum(s['typ'] in (SHT_REL,SHT_RELA) and bool(s['flags']&2) for s in sections))
