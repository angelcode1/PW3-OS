#!/usr/bin/env python3
"""R3877.64: explicitly opted-in, read-only TAR header / gzip prefix triage.

No extraction, archive member contents, writes, output names/paths, Docker, SSH,
network or Kindle. This is NOT recovery authentication. Always HOLD and exit 2.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import sys
import zlib

import pw3_r3877_63_recovery_candidate_headers as prior

MILESTONE='R3877.64'
PINNED_R63_SHA256='0346f68381c48d48eb38ece7c5d416d77f728ebdb0369c4ae6ad3aee3f059c2c'
TAR_BLOCK=512
MAX_TAR_HEADER_RECORDS=8192
MAX_GZIP_COMPRESSED_PREFIX_BYTES=2*1024*1024
MAX_GZIP_UNCOMPRESSED_PREFIX_BYTES=512*1024
MAX_GZIP_RATIO=128

class Hold(Exception): pass


def pins_ok():
    p=Path(prior.__file__)
    if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=PINNED_R63_SHA256:
        raise Hold('PINNED_R63_SCANNER_CHANGED')
    try:prior.pins_ok()
    except Exception:raise Hold('R63_TRANSITIVE_PIN_UNVERIFIED')
    return True


def _number(field):
    # Restrict to standard octal, not GNU base-256 values.
    if not field or field[0] & 0x80:return None
    s=field.strip(b'\0 ')
    if not s:return 0
    if any(x not in b'01234567' for x in s):return None
    try:return int(s,8)
    except ValueError:return None


def _name_class(header):
    raw=header[:100].split(b'\0',1)[0]
    prefix=header[345:500].split(b'\0',1)[0]
    raw=(prefix+b'/' if prefix else b'')+raw
    # Non-UTF8 names cannot be classified reliably; don't output them.
    try:name=raw.decode('utf-8','strict')
    except UnicodeDecodeError:return ('unknown_nonutf8',False,False,False)
    norm=name.replace('\\','/')
    parts=norm.split('/')
    unsafe=norm.startswith('/') or '..' in parts or bool(re.match(r'^[A-Za-z]:',norm))
    base=Path(norm).name
    recovery=prior.base.classify(base) in ('stock_partition_image_candidate','image_or_dump_other')
    document=prior.prev.category(base)=='recovery_document_candidate'
    return ('decoded',unsafe,recovery,document)


def tar_headers(f,size,allow_prefix=False):
    """Examine only 512-byte headers, skipping member bodies by seek.

    Refuses unsupported extended-name metadata rather than claiming complete
    filename coverage. No tarfile extraction, no member body read.
    """
    if size<1024:return {'status':'TAR_TOO_SMALL_FOR_HEADER_REVIEW'}
    f.seek(0)
    pos=0
    count=0; files=0; dirs=0; symlinks=0; hardlinks=0
    unknown_names=0; suspicious=0; image_names=0; recovery_doc_names=0
    extensions=0; other_types=0; total_declared=0
    stop='END_NOT_REACHED'
    while pos+TAR_BLOCK<=size and count<MAX_TAR_HEADER_RECORDS:
        f.seek(pos)
        h=f.read(TAR_BLOCK)
        if len(h)!=TAR_BLOCK:stop='HEADER_SHORT_READ';break
        if h==b'\0'*TAR_BLOCK:
            if pos+1024<=size:
                f.seek(pos+512)
                second=f.read(512)
                stop='TWO_ZERO_END_BLOCKS' if second==b'\0'*512 else 'ONE_ZERO_END_BLOCK_ONLY'
            else:stop='ONE_ZERO_END_BLOCK_ONLY'
            break
        if h[257:262]!=b'ustar':stop='NON_USTAR_HEADER';break
        checksum=_number(h[148:156]); sz=_number(h[124:136])
        if checksum is None or sz is None:stop='UNSUPPORTED_TAR_NUMERIC_ENCODING';break
        calc=sum(h[:148])+8*32+sum(h[156:])
        if checksum!=calc:stop='INVALID_TAR_HEADER_CHECKSUM';break
        kind=h[156:157]
        if kind in (b'x',b'g',b'L',b'K',b'S'):
            extensions+=1
        elif kind in (b'\0',b'0',b'7'):files+=1
        elif kind==b'5':dirs+=1
        elif kind==b'2':symlinks+=1
        elif kind==b'1':hardlinks+=1
        else:other_types+=1
        namestate,unsafe,rec,doc=_name_class(h)
        if namestate!='decoded':unknown_names+=1
        if unsafe:suspicious+=1
        if rec:image_names+=1
        if doc:recovery_doc_names+=1
        count+=1
        total_declared+=sz
        next_pos=pos+512+((sz+511)//512)*512
        if next_pos<=pos:stop='TAR_OFFSET_OVERFLOW';break
        if next_pos>size:
            stop='PREFIX_LIMIT_REACHED' if allow_prefix else 'MEMBER_EXTENDS_BEYOND_ARCHIVE'
            break
        pos=next_pos
    else:
        if count==MAX_TAR_HEADER_RECORDS:stop='TAR_HEADER_RECORD_BUDGET_EXHAUSTED'
        elif pos+512>size:stop='PREFIX_LIMIT_REACHED' if allow_prefix else 'NO_TAR_TERMINATOR'
    # A successful end marker is only a structure indication, not authentication.
    complete=stop=='TWO_ZERO_END_BLOCKS' and not extensions and not unknown_names
    return dict(status='TAR_HEADERS_COMPLETE_NO_MEMBER_CONTENT_READ' if complete else 'TAR_HEADERS_PARTIAL_OR_UNSUPPORTED',
        termination=stop,headers_validated=count,regular_member_count=files,
        directory_member_count=dirs,symlink_member_count=symlinks,
        hardlink_member_count=hardlinks,other_type_count=other_types,
        extended_or_sparse_header_count=extensions,non_utf8_name_count=unknown_names,
        suspicious_path_member_count=suspicious,
        stock_image_named_member_count=image_names,
        recovery_document_named_member_count=recovery_doc_names,
        sum_declared_member_bytes=total_declared,
        full_name_coverage_verified=bool(complete),member_contents_read=False,
        member_names_published=False)


def _signature(b):
    if b.startswith(b'\x7fELF'):return 'elf_prefix'
    if b.startswith(b'\x27\x05\x19\x56'):return 'u_boot_uimage_header_candidate'
    if b.startswith((b'hsqs',b'sqsh')):return 'squashfs_header_candidate'
    if b.startswith(b'UBI#'):return 'ubi_header_candidate'
    if b.startswith((b'070701',b'070702')):return 'cpio_newc_header_candidate'
    if b.startswith(b'Android!'):return 'android_boot_header_candidate'
    if b.startswith(b'\x1f\x8b'):return 'nested_gzip_prefix'
    if len(b)>=262 and b[257:262]==b'ustar':return 'ustar_header_candidate'
    if len(b)>=1082 and b[1080:1082]==b'\x53\xef':return 'ext_family_superblock_magic_candidate'
    return 'unrecognized_prefix'


def gzip_bounded_prefix(f,archive_size):
    """Only decompress an in-memory, strictly capped prefix. Never write output."""
    if archive_size<10:return dict(status='GZIP_TOO_SHORT')
    f.seek(0)
    dec=zlib.decompressobj(16+zlib.MAX_WBITS)
    seen=0
    out=bytearray()
    state='PREFIX_BUDGET_REACHED'
    while (seen<min(archive_size,MAX_GZIP_COMPRESSED_PREFIX_BYTES)
           and len(out)<MAX_GZIP_UNCOMPRESSED_PREFIX_BYTES):
        chunk=f.read(min(8192,archive_size-seen,MAX_GZIP_COMPRESSED_PREFIX_BYTES-seen))
        if not chunk:
            state='COMPRESSED_INPUT_SHORT_READ'
            break
        seen+=len(chunk)
        try:
            piece=dec.decompress(chunk,MAX_GZIP_UNCOMPRESSED_PREFIX_BYTES-len(out))
        except zlib.error:
            return dict(status='INVALID_GZIP_PREFIX',compressed_bytes_consumed=seen,
                decompressed_prefix_bytes=len(out),signature='unavailable')
        out.extend(piece)
        if seen>0 and len(out)>seen*MAX_GZIP_RATIO:
            state='GZIP_PREFIX_EXPANSION_RATIO_LIMIT';break
        if dec.eof:
            state='GZIP_STREAM_END_REACHED'
            break
    # The gzip trailer is only authenticated if end-of-stream was actually seen.
    prefix=bytes(out)
    signature=_signature(prefix)
    result=dict(status='GZIP_IN_MEMORY_BOUNDED_PREFIX_ONLY',
       compressed_bytes_consumed=seen,decompressed_prefix_bytes=len(prefix),
       prefix_limit_bytes=MAX_GZIP_UNCOMPRESSED_PREFIX_BYTES,
       expansion_ratio_limit=MAX_GZIP_RATIO,
       termination=state,signature=signature,
       gzip_stream_end_observed=bool(dec.eof),
       decompressed_content_saved=False,compressed_full_hash_authenticity_verified=False)
    if signature=='ustar_header_candidate':
        r=tar_headers(io.BytesIO(prefix),len(prefix),allow_prefix=True)
        result['tar_prefix_headers']=r
    return result


def inspect(root,max_depth=3,max_entries=100000,max_candidates=3000):
    pins_ok()
    inherited=prior.inspect(root,max_depth,max_entries,max_candidates)
    selected=prior.choose(root,max_depth,max_entries,max_candidates)
    archives=[row for row in selected if row[1] in prior.ARCHIVE_CATEGORIES]
    if len(archives)!=inherited['archive_candidates_reviewed']:
        raise Hold('ARCHIVE_COUNT_CHANGED_BETWEEN_REVIEWS')
    results=[]
    for i,(p,c,st) in enumerate(archives,1):
        previous=inherited['archive_candidates'][i-1]
        if previous['candidate_id']!='A%02d'%i or previous['byte_length']!=st.st_size:
            raise Hold('ARCHIVE_ORDER_OR_SIZE_CHANGED')
        with prior.opened_regular_file(p,st) as f:
            fmt=prior.magic_format(f)
            if fmt!=previous['format_detected_from_bytes']:
                raise Hold('ARCHIVE_MAGIC_CHANGED')
            if fmt=='tar_opaque':review=tar_headers(f,st.st_size)
            elif fmt=='gzip_opaque':review=gzip_bounded_prefix(f,st.st_size)
            else:review={'status':'PRIOR_R63_CLASSIFICATION_RETAINED'}
        results.append(dict(candidate_id='A%02d'%i,format_detected_from_bytes=fmt,
            matching_untrusted_sha256_manifest_file_count=previous['matching_untrusted_sha256_manifest_file_count'],
            structural_review=review))
    return dict(structural_review='BOUNDED_TAR_HEADERS_AND_GZIP_PREFIX_NOT_AUTHENTICATION',
       previous_r63_review_complete=True,
       prior_r63_manifest_matches_are_untrusted=True,
       archive_candidates=results,archive_count=len(results),
       scope_scan_complete=inherited['scope']['bounded_scope_scan_complete'],
       filenames_or_paths_published=False,archive_members_extracted_or_executed=False,
       gzip_data_persisted=False,local_files_modified=False,
       stock_recovery_authenticity_verified=False,independent_restore_verified=False)


def preflight():
    return dict(milestone=MILESTONE,result='HOLD',immutable_hold='NOT_BOOTABLE',
        hold_category='EXPLICIT_LOCAL_ROOT_AND_BOUNDED_PREFIX_OPT_IN_REQUIRED',
        physical_device_access_performed=False,kindle_ssh_sessions=0,
        firmware_write_performed=False,boot_performed=False,
        arm_guest_execution_performed=False,docker_used=False,
        network_access_performed=False,local_files_modified=False,
        recovery_verified=False,vendor_kernel_compatibility_verified=False,
        candidate_authenticity_verified=False)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scan-root')
    p.add_argument('--acknowledge-readonly-prefix-inspection',action='store_true')
    p.add_argument('--max-depth',type=int,default=3)
    p.add_argument('--max-entries',type=int,default=100000)
    p.add_argument('--max-candidates',type=int,default=3000)
    args=p.parse_args(argv)
    report=preflight()
    if not args.scan_root: report['hold_category']='EXPLICIT_SCAN_ROOT_REQUIRED'
    elif not args.acknowledge_readonly_prefix_inspection:report['hold_category']='GZIP_DECOMPRESSION_OPT_IN_REQUIRED'
    else:
        try:
            report['review']=inspect(args.scan_root,args.max_depth,args.max_entries,args.max_candidates)
            report['hold_category']='STOCK_RECOVERY_AUTHENTICITY_AND_INDEPENDENT_RESTORE_UNVERIFIED'
        except (Hold,prior.Hold,prior.prev.Hold,prior.base.Hold,ValueError,TypeError,OSError,RuntimeError,OverflowError,EOFError):
            report['hold_category']='BOUNDED_TAR_GZIP_STRUCTURAL_REVIEW_REFUSED_OR_INCOMPLETE'
    print(json.dumps(report,sort_keys=True,separators=(',',':')))
    return 2

if __name__=='__main__':sys.exit(main())
