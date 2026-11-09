#!/usr/bin/env python3
"""R3877.65: read-only PAX/GNU TAR metadata and bounded in-memory gzip stream review.

No extraction, output of filenames or private digests, member execution, file writes,
network, Docker, physical Kindle, SSH or recovery. Always HOLD / exit 2.
"""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zlib

import pw3_r3877_64_tar_gzip_structure as prev

MILESTONE='R3877.65'
PINNED_R64_SHA256='71ee88f8a18372ad1e51495288059487ac01a78ce88a057be6c9fe9e61dba54a'
BLOCK=512
MAX_TAR_HEADERS=8192
MAX_EXTENSION_BYTES_PER_HEADER=64*1024
MAX_TOTAL_EXTENSION_BYTES=512*1024
MAX_GZIP_COMPRESSED_BYTES=8*1024*1024
MAX_GZIP_IN_MEMORY_BYTES=64*1024*1024
MAX_EXPANSION_RATIO=128
MAX_FILENAME_BYTES=4096

class Hold(Exception):pass


def pins_ok():
    path=Path(prev.__file__)
    if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=PINNED_R64_SHA256:
        raise Hold('PINNED_R64_SCANNER_CHANGED')
    try:prev.pins_ok()
    except Exception:raise Hold('TRANSITIVE_SCANNER_PIN_UNVERIFIED')
    return True


def classify_name(raw):
    """Only counts; never returns a path or filename to the report."""
    try:
        if isinstance(raw,bytes):
            if len(raw)>MAX_FILENAME_BYTES:return (False,False,False,False)
            name=raw.decode('utf-8','strict')
        else:
            if len(raw.encode('utf-8'))>MAX_FILENAME_BYTES:return (False,False,False,False)
            name=raw
    except (UnicodeDecodeError,UnicodeEncodeError):return (False,False,False,False)
    name=name.replace('\\','/')
    parts=name.split('/')
    suspicious=(name.startswith('/') or '..' in parts or bool(re.match(r'^[A-Za-z]:',name)) or '\x00' in name)
    base=name.rstrip('/').rsplit('/',1)[-1]
    image=prev.prior.base.classify(base) in ('stock_partition_image_candidate','image_or_dump_other')
    doc=prev.prior.prev.category(base)=='recovery_document_candidate'
    return (True,suspicious,image,doc)


def parse_pax(payload):
    """Validate all bounded PAX records: byte length, syntax, UTF-8, termination."""
    attrs={};i=0
    while i<len(payload):
        sp=payload.find(b' ',i,min(len(payload),i+16))
        if sp<=i or any(c not in b'0123456789' for c in payload[i:sp]):return None
        n=int(payload[i:sp])
        if n<sp-i+4 or i+n>len(payload):return None
        line=payload[sp+1:i+n]
        if not line.endswith(b'\n') or b'=' not in line:return None
        key,val=line[:-1].split(b'=',1)
        if not key or len(key)>256:return None
        try:k=key.decode('ascii','strict');v=val.decode('utf-8','strict')
        except UnicodeError:return None
        attrs[k]=v
        i+=n
    return attrs


def parse_tar(f,size,allow_prefix=False):
    """Seek over all raw member bodies; only read bounded PAX/GNU extension payloads.

    For an already decompressed gzip BytesIO, the stream necessarily contained
    member bodies in memory, but this parser still reads only headers/metadata.
    """
    if size<1024:return {'status':'TAR_TOO_SMALL_FOR_HEADER_REVIEW'}
    pos=0;count=0;regular=0;dirs=0;links=0;hardlinks=0;other=0
    extensions=Counter();badname=0;unsafe=0;images=0;docs=0;unsupported=0
    total_declared=0;extension_bytes=0;global_attrs={};local_attrs={};gnu_name=None;gnu_link=None
    stop='END_NOT_REACHED'
    while count<MAX_TAR_HEADERS and pos+BLOCK<=size:
        f.seek(pos);h=f.read(BLOCK)
        if len(h)!=BLOCK:stop='SHORT_TAR_HEADER';break
        if h==b'\0'*BLOCK:
            if pos+1024<=size:
                f.seek(pos+BLOCK)
                stop='TWO_ZERO_END_BLOCKS' if f.read(BLOCK)==b'\0'*BLOCK else 'SINGLE_ZERO_BLOCK'
            else:stop='SINGLE_ZERO_BLOCK'
            break
        if h[257:262]!=b'ustar':stop='NON_USTAR_HEADER';break
        sz=prev._number(h[124:136]);chk=prev._number(h[148:156])
        if sz is None or chk is None:stop='UNSUPPORTED_TAR_NUMBER';break
        if chk!=sum(h[:148])+8*32+sum(h[156:]):stop='BAD_TAR_HEADER_CHECKSUM';break
        kind=h[156:157]
        count+=1
        nextpos=pos+BLOCK+((sz+BLOCK-1)//BLOCK)*BLOCK
        if nextpos>size:
            stop='PREFIX_LIMIT_REACHED' if allow_prefix else 'HEADER_DECLARED_CONTENT_OUTSIDE_FILE'
            break
        if kind in (b'x',b'g',b'L',b'K',b'S'):
            label={b'x':'pax_local',b'g':'pax_global',b'L':'gnu_longname',b'K':'gnu_longlink',b'S':'gnu_sparse'}[kind]
            extensions[label]+=1
            if kind==b'S':
                unsupported+=1 # GNU sparse format may use special data layouts.
            else:
                extension_bytes+=sz
                if sz>MAX_EXTENSION_BYTES_PER_HEADER or extension_bytes>MAX_TOTAL_EXTENSION_BYTES:
                    stop='EXTENSION_BYTE_BUDGET_EXCEEDED';break
                f.seek(pos+BLOCK)
                payload=f.read(sz)
                if len(payload)!=sz:stop='EXTENSION_SHORT_READ';break
                if kind in (b'x',b'g'):
                    attrs=parse_pax(payload)
                    if attrs is None:stop='MALFORMED_PAX_RECORD';break
                    if any(k.startswith(('GNU.sparse','SCHILY.realsize')) for k in attrs):unsupported+=1
                    if kind==b'g':global_attrs.update(attrs)
                    else:local_attrs.update(attrs)
                else:
                    name=payload.rstrip(b'\x00\n')
                    if not name or len(name)>MAX_FILENAME_BYTES:stop='INVALID_GNU_LONGNAME';break
                    if kind==b'L':gnu_name=name
                    else:gnu_link=name
        else:
            eff=dict(global_attrs);eff.update(local_attrs)
            # PAX size is not supported when it changes stored member offsets.
            if 'size' in eff:
                if not eff['size'].isdigit() or int(eff['size'])!=sz:
                    stop='PAX_SIZE_DIFFERS_FROM_RAW_TAR_SIZE';break
            if 'path' in eff: name=eff['path']
            elif gnu_name is not None:name=gnu_name
            else:
                head=h[:100].split(b'\0',1)[0]
                pre=h[345:500].split(b'\0',1)[0]
                name=(pre+b'/' if pre else b'')+head
            decoded,suspicious,image,doc=classify_name(name)
            if not decoded:badname+=1
            if suspicious:unsafe+=1
            if image:images+=1
            if doc:docs+=1
            # Detect unsafe symbolic/hardlink targets too; never follow links.
            if kind in (b'1',b'2'):
                target=eff.get('linkpath',gnu_link)
                if target is None:target=h[157:257].split(b'\0',1)[0]
                valid,bad,_,_=classify_name(target)
                if not valid:badname+=1
                if bad:unsafe+=1
            if kind in (b'\0',b'0',b'7'):regular+=1
            elif kind==b'5':dirs+=1
            elif kind==b'2':links+=1
            elif kind==b'1':hardlinks+=1
            else:other+=1;unsupported+=1
            total_declared+=sz
            local_attrs.clear();gnu_name=None;gnu_link=None
        pos=nextpos
    else:
        stop='TAR_HEADER_RECORD_LIMIT_REACHED' if count==MAX_TAR_HEADERS else ('PREFIX_LIMIT_REACHED' if allow_prefix else 'TAR_END_NOT_FOUND')
    if local_attrs or gnu_name is not None or gnu_link is not None:unsupported+=1
    completed=(stop=='TWO_ZERO_END_BLOCKS' and unsupported==0 and badname==0)
    return dict(status='TAR_NAMES_RESOLVED_HEADERS_COMPLETE' if completed else 'TAR_STRUCTURE_OR_NAME_COVERAGE_INCOMPLETE',
        termination=stop,headers_validated=count,regular_member_count=regular,
        directory_member_count=dirs,symlink_member_count=links,hardlink_member_count=hardlinks,
        other_type_count=other,extension_header_counts=dict(sorted(extensions.items())),
        pax_and_gnu_extension_bytes_read=extension_bytes,
        unsupported_sparse_or_other_count=unsupported,
        undecodable_or_oversize_name_count=badname,suspicious_path_or_link_count=unsafe,
        stock_image_named_member_count=images,recovery_document_named_member_count=docs,
        sum_declared_regular_member_bytes=total_declared,
        full_name_coverage_verified=completed,member_bodies_read_by_tar_parser=False,
        member_names_or_paths_published=False)


def inspect_gzip(f,size):
    """Bounded single gzip stream into memory. No decompressed data saved to disk."""
    f.seek(0)
    dec=zlib.decompressobj(16+zlib.MAX_WBITS)
    read=0;out=bytearray();pending=b'';termination='STREAM_NOT_FINISHED'
    while len(out)<MAX_GZIP_IN_MEMORY_BYTES and not dec.eof:
        if not pending:
            if read>=min(size,MAX_GZIP_COMPRESSED_BYTES):
                termination='COMPRESSED_INPUT_LIMIT_REACHED';break
            chunk=f.read(min(8192,size-read,MAX_GZIP_COMPRESSED_BYTES-read))
            if not chunk:termination='COMPRESSED_INPUT_SHORT_READ';break
            read+=len(chunk);pending=chunk
        try:
            piece=dec.decompress(pending,MAX_GZIP_IN_MEMORY_BYTES-len(out))
        except zlib.error:
            return dict(status='GZIP_INVALID_OR_CHECKSUM_ERROR',gzip_full_stream_integrity_verified=False,
                        gzip_stream_end_observed=False,decompressed_bytes_in_memory=len(out),decompressed_content_saved=False)
        pending=dec.unconsumed_tail
        out.extend(piece)
        # Limit expansion based on total bytes read. A conservative ratio guard.
        if len(out)>max(1,read)*MAX_EXPANSION_RATIO:
            termination='EXPANSION_RATIO_LIMIT_REACHED';break
        if dec.eof:
            termination='STREAM_END_REACHED';break
        if not piece and not pending and read>=size:
            termination='GZIP_TRUNCATED';break
    if len(out)>=MAX_GZIP_IN_MEMORY_BYTES and not dec.eof:
        termination='DECOMPRESSED_MEMORY_LIMIT_REACHED'
    # zlib verifies CRC+size on end-of-stream; extra data (incl concatenated
    # gzip members) must not be mistaken for a fully verified single stream.
    full=bool(dec.eof and read==size and not dec.unused_data and not pending)
    if dec.eof and not full:termination='GZIP_TRAILING_OR_CONCATENATED_DATA_UNVERIFIED'
    prefix=bytes(out)
    sig=prev._signature(prefix)
    result=dict(status='BOUNDED_IN_MEMORY_GZIP_STREAM_TRIAGE',signature=sig,
        compressed_bytes_read=read,compressed_byte_limit=MAX_GZIP_COMPRESSED_BYTES,
        decompressed_bytes_in_memory=len(prefix),decompressed_byte_limit=MAX_GZIP_IN_MEMORY_BYTES,
        gzip_stream_end_observed=bool(dec.eof),gzip_full_stream_integrity_verified=full,
        decompression_termination=termination,expansion_ratio_limit=MAX_EXPANSION_RATIO,
        decompressed_content_saved=False,member_data_decompressed_in_memory=True,
        compressed_full_hash_authenticity_verified=False)
    if sig=='ustar_header_candidate':
        result['tar_headers']=parse_tar(io.BytesIO(prefix),len(prefix),allow_prefix=not full)
        result['tar_full_coverage_verified']=bool(full and result['tar_headers']['full_name_coverage_verified'])
    else:result['tar_full_coverage_verified']=False
    return result


def inspect(root,max_depth=3,max_entries=100000,max_candidates=3000):
    pins_ok()
    inherited=prev.inspect(root,max_depth,max_entries,max_candidates)
    selected=prev.prior.choose(root,max_depth,max_entries,max_candidates)
    candidates=[x for x in selected if x[1] in prev.prior.ARCHIVE_CATEGORIES]
    if len(candidates)!=inherited['archive_count']:raise Hold('ARCHIVE_SELECTION_COUNT_CHANGED')
    results=[]
    for i,(path,category,stat_at_scan) in enumerate(candidates,1):
        prev_row=inherited['archive_candidates'][i-1]
        cid='A%02d'%i
        with prev.prior.opened_regular_file(path,stat_at_scan) as f:
            fmt=prev.prior.magic_format(f)
            if prev_row['candidate_id']!=cid or fmt!=prev_row['format_detected_from_bytes']:
                raise Hold('ARCHIVE_SELECTION_FORMAT_CHANGED')
            if fmt=='tar_opaque': r=parse_tar(f,stat_at_scan.st_size)
            elif fmt=='gzip_opaque':r=inspect_gzip(f,stat_at_scan.st_size)
            else:r={'status':'PRIOR_ZIP_OR_OPAQUE_FORMAT_RETAINED'}
        results.append(dict(candidate_id=cid,format_detected_from_bytes=fmt,structural_review=r,
            matching_untrusted_sha256_manifest_file_count=prev_row['matching_untrusted_sha256_manifest_file_count']))
    return dict(status='READ_ONLY_EXTENDED_TAR_GZIP_IN_MEMORY_TRIAGE_NOT_AUTHENTICATION',
        archive_count=len(results),archive_candidates=results,
        complete_scoped_candidate_selection_verified=inherited['scope_scan_complete'],
        raw_file_names_or_paths_published=False,raw_digests_published=False,
        archives_extracted_or_executed=False,gzip_decompressed_data_persisted=False,
        local_files_modified=False,stock_recovery_authenticity_verified=False,
        independent_restore_verified=False,prior_manifest_matches_remain_untrusted=True)


def preflight():
    return dict(milestone=MILESTONE,result='HOLD',immutable_hold='NOT_BOOTABLE',
        hold_category='EXPLICIT_SCAN_ROOT_AND_BOUNDED_DECOMPRESSION_OPT_IN_REQUIRED',
        physical_device_access_performed=False,kindle_ssh_sessions=0,
        firmware_write_performed=False,boot_performed=False,docker_used=False,
        arm_guest_execution_performed=False,network_access_performed=False,
        local_files_modified=False,recovery_verified=False,vendor_kernel_compatibility_verified=False,
        candidate_authenticity_verified=False)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scan-root')
    parser.add_argument('--max-depth',type=int,default=3)
    parser.add_argument('--max-entries',type=int,default=100000)
    parser.add_argument('--max-candidates',type=int,default=3000)
    parser.add_argument('--acknowledge-readonly-extended-metadata-and-bounded-gzip-decompression',action='store_true')
    args=parser.parse_args(argv)
    report=preflight()
    if not args.scan_root:report['hold_category']='EXPLICIT_SCAN_ROOT_REQUIRED'
    elif not args.acknowledge_readonly_extended_metadata_and_bounded_gzip_decompression:
        report['hold_category']='EXPLICIT_BOUNDED_DECOMPRESSION_OPT_IN_REQUIRED'
    else:
        try:
            report['review']=inspect(args.scan_root,args.max_depth,args.max_entries,args.max_candidates)
            report['hold_category']='STOCK_RECOVERY_AUTHENTICITY_AND_INDEPENDENT_RESTORE_UNVERIFIED'
        except (Hold,prev.Hold,prev.prior.Hold,prev.prior.prev.Hold,prev.prior.base.Hold,ValueError,TypeError,OSError,RuntimeError,OverflowError,EOFError):
            report['hold_category']='BOUNDED_EXTENDED_TAR_GZIP_REVIEW_REFUSED'
    print(json.dumps(report,sort_keys=True,separators=(',',':')))
    return 2

if __name__=='__main__':sys.exit(main())
