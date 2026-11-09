#!/usr/bin/env python3
"""R3877.63: explicit read-only, bounded Kindle recovery candidate *content* triage.

No Kindle, Docker, network, archive decompression/extraction or file writes.
Pathless report: candidate ordinals, counts, bounded ZIP central-directory metadata,
file content digests compared with untrusted local manifests (digest never printed).
Even a digest match is NOT recovery authenticity. Always HOLD / exit 2.
"""
import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import zipfile

import pw3_r3877_62_recovery_inventory as base
import pw3_r3877_62_2_candidate_triage as prev

MILESTONE='R3877.63'
PINNED_PREV_SHA256='37106001ea836d964e1e96834501def740e32299b51290f02d6c64c9dbde02f1'
INCLUDE=frozenset(('nonresearch_named_backup_archive_candidate',
    'integrity_manifest_filename_candidate','recovery_document_candidate',
    'stock_partition_image_candidate','image_or_dump_other'))
ARCHIVE_CATEGORIES=frozenset(('nonresearch_named_backup_archive_candidate',
    'stock_partition_image_candidate','image_or_dump_other'))
MAX_ARCHIVE_BYTES=128*1024*1024
MAX_MANIFEST_BYTES=256*1024
MAX_DOCUMENT_BYTES=256*1024
MAX_ZIP_CENTRAL_DIRECTORY_BYTES=2*1024*1024
MAX_ZIP_ENTRIES=4096
MAX_CONTENT_BYTES_TOTAL=256*1024*1024
MAX_REVIEW_FILES=256
# Manifest records must have SHA-256 hash *and* an exact basename match.
HASH_LINE=re.compile(r'^([a-fA-F0-9]{64})\s+\*?([^\r\n]+)$')
DOC_TERMS={
    'mentions_backup':re.compile(r'\bbackups?\b',re.I),
    'mentions_restore':re.compile(r'\brestor(?:e|ed|ing|ation)\b',re.I),
    'mentions_serial_uart':re.compile(r'\b(?:serial|uart)\b',re.I),
    'mentions_fastboot':re.compile(r'\bfastboot\b',re.I),
    'mentions_bootloader':re.compile(r'\b(?:bootloader|u-boot|uboot)\b',re.I),
    'mentions_checksums':re.compile(r'\b(?:sha256|checksum|hash|digest)\b',re.I),
    'mentions_kindle':re.compile(r'\b(?:kindle|paperwhite)\b',re.I),
    'mentions_mmc_partition':re.compile(r'\b(?:mmcblk|partition|eMMC)\b',re.I),
}

class Hold(Exception): pass


def pins_ok():
    prev_path=Path(prev.__file__)
    if prev_path.is_symlink() or not prev_path.is_file() or hashlib.sha256(prev_path.read_bytes()).hexdigest()!=PINNED_PREV_SHA256:
        raise Hold('PINNED_R62_2_SCANNER_CHANGED')
    try: prev.require_base()
    except Exception: raise Hold('PINNED_R62_1_SCANNER_CHANGED')
    return True


def choose(root,max_depth,max_entries,max_candidates):
    """Deterministic, no-symlink candidate selection, matching R62.2 policy."""
    root=base.check_root(root)
    found=[]
    entries=0
    candidates=0
    stack=[(root,0)]
    while stack:
        directory,depth=stack.pop()
        if directory.is_symlink() or not directory.is_dir():
            raise Hold('DIRECTORY_CHANGED_DURING_SELECTION')
        try:
            with os.scandir(directory) as it:
                children=sorted(list(it),key=lambda e:e.name)
        except OSError:
            raise Hold('DIRECTORY_UNREADABLE_DURING_SELECTION')
        descend=[]
        for entry in children:
            entries+=1
            if entries>max_entries:
                raise Hold('ENTRY_BUDGET_EXHAUSTED_DURING_SELECTION')
            try: st=entry.stat(follow_symlinks=False)
            except OSError: raise Hold('ENTRY_CHANGED_DURING_SELECTION')
            if stat.S_ISLNK(st.st_mode):continue
            if stat.S_ISDIR(st.st_mode):
                if depth<max_depth and entry.name not in base.EXCLUDED_DIRS and not entry.name.startswith('.'):
                    descend.append((Path(entry.path),depth+1))
                continue
            if not stat.S_ISREG(st.st_mode):continue
            c=prev.category(entry.name)
            if c is None:continue
            candidates+=1
            if candidates>max_candidates:raise Hold('CANDIDATE_BUDGET_EXHAUSTED_DURING_SELECTION')
            if c in INCLUDE:found.append((Path(entry.path),c,st))
        stack.extend(reversed(descend))
    return sorted(found,key=lambda q:str(q[0]))


@contextmanager
def opened_regular_file(path,st):
    """Reject symlink files, changed inode/size and any ambiguous open."""
    flags=os.O_RDONLY | getattr(os,'O_NOFOLLOW',0) | getattr(os,'O_CLOEXEC',0)
    # Directory names were checked by no-follow traversal, but may change
    # concurrently. Check all current ancestors again before opening.
    parent=path.parent
    while True:
        if parent.is_symlink():raise Hold('FILE_PARENT_BECAME_SYMLINK')
        if parent==parent.parent:break
        parent=parent.parent
    try:fd=os.open(str(path),flags)
    except OSError:raise Hold('CANDIDATE_OPEN_REJECTED')
    try:
        before=os.fstat(fd)
        identity=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)
        current=(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)
        if not stat.S_ISREG(before.st_mode) or current!=identity:
            raise Hold('CANDIDATE_CHANGED_BEFORE_READ')
        with os.fdopen(fd,'rb',closefd=False) as f:
            yield f
            after=os.fstat(fd)
            if (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)!=identity:
                raise Hold('CANDIDATE_CHANGED_DURING_READ')
    finally:os.close(fd)


def sha256_stream(f, byte_size):
    h=hashlib.sha256()
    total=0
    f.seek(0)
    while True:
        b=f.read(min(1024*1024, byte_size-total))
        if not b:break
        total+=len(b)
        h.update(b)
        if total>byte_size:raise Hold('CANDIDATE_SIZE_CHANGED_DURING_READ')
        if total==byte_size:break
    if total!=byte_size:raise Hold('CANDIDATE_SIZE_CHANGED_DURING_READ')
    return h.hexdigest()


def magic_format(f):
    f.seek(0)
    p=f.read(272)
    if p.startswith((b'PK\x03\x04',b'PK\x05\x06',b'PK\x07\x08')):return 'zip'
    if p.startswith(b'7z\xbc\xaf\x27\x1c'):return '7z_opaque'
    if p.startswith(b'\x1f\x8b'):return 'gzip_opaque'
    if p.startswith(b'\xfd7zXZ\x00'):return 'xz_opaque'
    if p.startswith(b'\x28\xb5\x2f\xfd'):return 'zstd_opaque'
    if p[257:262]==b'ustar':return 'tar_opaque'
    return 'unknown_or_raw'


def zip_metadata(f,size):
    """No ZIP member data read, extracted, decompressed or executed."""
    tail=min(size,65557)
    f.seek(size-tail)
    buf=f.read(tail)
    offset=buf.rfind(b'PK\x05\x06')
    if offset<0 or offset+22>len(buf):return dict(status='INVALID_EOCD_OR_UNSUPPORTED_ZIP')
    try:
        (_sig,disk,central_disk,disk_count,total_count,central_size,_central_off,comment_len)=struct.unpack_from('<IHHHHIIH',buf,offset)
    except struct.error:return dict(status='INVALID_EOCD_OR_UNSUPPORTED_ZIP')
    if (disk or central_disk or disk_count!=total_count or total_count==0xffff
        or central_size==0xffffffff or central_size>MAX_ZIP_CENTRAL_DIRECTORY_BYTES
        or total_count>MAX_ZIP_ENTRIES or offset+22+comment_len>len(buf)):
        return dict(status='ZIP_CENTRAL_DIRECTORY_BOUNDS_OR_MULTIDISK_HOLD')
    try:
        f.seek(0)
        with zipfile.ZipFile(f,'r',allowZip64=False) as z:
            info=z.infolist()
            if len(info)!=total_count: return dict(status='ZIP_ENTRY_COUNT_MISMATCH')
            suspicious=0; symlinks=0; encrypted=0; image_like=0; nested_archives=0
            declared_size=0
            for member in info:
                name=member.filename.replace('\\','/')
                comps=name.split('/')
                if name.startswith('/') or '..' in comps or re.match('^[A-Za-z]:',name):suspicious+=1
                mode=(member.external_attr>>16)&0xffff
                if stat.S_ISLNK(mode):symlinks+=1
                if member.flag_bits & 1:encrypted+=1
                if base.classify(Path(name).name) in ('stock_partition_image_candidate','image_or_dump_other'):
                    image_like+=1
                if prev.ARCHIVE.search(Path(name).name):nested_archives+=1
                declared_size+=member.file_size
            return dict(status='ZIP_CENTRAL_DIRECTORY_PARSED_NOT_EXTRACTED',entry_count=len(info),
                image_named_member_count=image_like,nested_archive_member_count=nested_archives,
                suspicious_path_member_count=suspicious,symlink_member_count=symlinks,
                encrypted_member_count=encrypted,declared_uncompressed_total_exceeds_1_gib=declared_size>1024**3)
    except (zipfile.BadZipFile,zipfile.LargeZipFile,RuntimeError,OSError,ValueError):
        return dict(status='ZIP_CENTRAL_DIRECTORY_INVALID_OR_UNSUPPORTED')


def parse_manifest(f,size):
    f.seek(0)
    data=f.read(size+1)
    if len(data)!=size or len(data)>MAX_MANIFEST_BYTES:raise Hold('MANIFEST_SIZE_CHANGED_OR_TOO_LARGE')
    try:text=data.decode('utf-8')
    except UnicodeDecodeError:return []
    rows=[]
    for line in text.splitlines():
        if len(line)>1024:continue
        m=HASH_LINE.fullmatch(line.strip())
        if not m:continue
        name=m.group(2)
        if '/' in name or '\\' in name:continue
        rows.append((m.group(1).lower(),name))
    return rows


def inspect(root,max_depth=3,max_entries=100000,max_candidates=3000):
    pins_ok()
    # Reuse entire previous broad classification to establish scan completeness.
    whole=prev.triage(root,max_depth,max_entries,max_candidates)
    if not whole['bounded_scope_scan_complete']:
        raise Hold('PREVIOUS_SCOPE_INCOMPLETE')
    selected=choose(root,max_depth,max_entries,max_candidates)
    counts=Counter(c for _,c,_ in selected)
    for c in INCLUDE:
        if counts[c]!=whole['candidate_counts_by_category'].get(c,0):
            raise Hold('CANDIDATE_SET_CHANGED_BETWEEN_SCANS')
    if len(selected)>MAX_REVIEW_FILES:raise Hold('TOO_MANY_FILES_FOR_FOCUSED_CONTENT_REVIEW')
    archives=[t for t in selected if t[1] in ARCHIVE_CATEGORIES]
    manifests=[t for t in selected if t[1]=='integrity_manifest_filename_candidate']
    docs=[t for t in selected if t[1]=='recovery_document_candidate']
    if sum(st.st_size for _,_,st in archives)>MAX_CONTENT_BYTES_TOTAL:
        raise Hold('AGGREGATE_ARCHIVE_BYTE_CAP_EXCEEDED')
    if any(st.st_size>MAX_ARCHIVE_BYTES for _,_,st in archives):
        raise Hold('ARCHIVE_BYTE_CAP_EXCEEDED')
    if any(st.st_size>MAX_MANIFEST_BYTES for _,_,st in manifests):
        raise Hold('MANIFEST_BYTE_CAP_EXCEEDED')
    if any(st.st_size>MAX_DOCUMENT_BYTES for _,_,st in docs):
        raise Hold('DOCUMENT_BYTE_CAP_EXCEEDED')
    hashes=defaultdict(list); archive_details=[]
    for ordinal,(p,c,st) in enumerate(archives,1):
        with opened_regular_file(p,st) as f:
            digest=sha256_stream(f,st.st_size)
            fmt=magic_format(f)
            details=zip_metadata(f,st.st_size) if fmt=='zip' else {'status':'OPAQUE_FORMAT_NOT_DECOMPRESSED'}
        hashes[p.name].append((digest,ordinal))
        archive_details.append(dict(candidate_id='A%02d'%ordinal,category=c,
            format_detected_from_bytes=fmt,byte_length=st.st_size,structural_review=details,
            content_sha256_computed_not_published=True))
    parsed=0; manifests_read=0; matched=defaultdict(set)
    for p,c,st in manifests:
        with opened_regular_file(p,st) as f:records=parse_manifest(f,st.st_size)
        manifests_read+=1
        parsed+=len(records)
        for digest,name in records:
            for expected_digest, ordinal in hashes.get(name,()):
                if expected_digest==digest:
                    matched[ordinal].add(str(p))
    term_counts=Counter(); docs_parsed=0; opaque_docs=0
    for p,c,st in docs:
        with opened_regular_file(p,st) as f:
            f.seek(0);data=f.read(st.st_size+1)
        if len(data)!=st.st_size:raise Hold('DOCUMENT_SIZE_CHANGED')
        if data.startswith(b'%PDF-'):
            opaque_docs+=1
            continue
        try:text=data.decode('utf-8')
        except UnicodeDecodeError:
            opaque_docs+=1
            continue
        docs_parsed+=1
        for k,pat in DOC_TERMS.items():
            if pat.search(text):term_counts[k]+=1
    for i,d in enumerate(archive_details,1):
        d['matching_untrusted_sha256_manifest_file_count']=len(matched[i])
    return dict(scope=whole,
        content_inspection_status='BOUNDED_READ_ONLY_CONTENT_TRIAGE_NOT_AUTHENTICATION',
        archive_candidates_reviewed=len(archives),manifest_files_reviewed=manifests_read,
        checksum_records_parsed_from_untrusted_manifests=parsed,
        archive_candidates_with_matching_untrusted_sha256_manifest=sum(bool(x) for x in matched.values()),
        archive_candidates=archive_details,
        recovery_docs_reviewed=len(docs),recovery_docs_plaintext_read=docs_parsed,
        recovery_docs_opaque_or_binary=opaque_docs,recovery_doc_keyword_mentions_by_document=dict(sorted(term_counts.items())),
        raw_archive_names_or_paths_published=False,raw_document_text_published=False,
        content_hashes_published=False,contents_extracted_or_executed=False,
        manifest_matching_is_not_authenticity=True,restoration_verified=False,
        stock_image_authenticated=False,independent_restore_method_verified=False)


def preflight():
    return dict(milestone=MILESTONE,result='HOLD',
        hold_category='EXPLICIT_CONTENT_REVIEW_OPT_IN_AND_SCAN_ROOT_REQUIRED',
        immutable_hold='NOT_BOOTABLE',recovery_verified=False,
        candidate_authenticity_verified=False,kindle_ssh_sessions=0,
        physical_device_access_performed=False,arm_guest_execution_performed=False,
        boot_performed=False,firmware_write_performed=False,docker_used=False,
        network_access_performed=False,host_mounts_enabled=False,
        local_files_modified=False,application_secure_entropy_fallback_verified=False,
        vendor_kernel_compatibility_verified=False)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scan-root')
    p.add_argument('--acknowledge-readonly-content-inspection',action='store_true')
    p.add_argument('--max-depth',type=int,default=3)
    p.add_argument('--max-entries',type=int,default=100000)
    p.add_argument('--max-candidates',type=int,default=3000)
    args=p.parse_args(argv)
    report=preflight()
    if not args.scan_root:
        report['hold_category']='EXPLICIT_SCAN_ROOT_REQUIRED'
    elif not args.acknowledge_readonly_content_inspection:
        report['hold_category']='READONLY_CONTENT_REVIEW_OPT_IN_REQUIRED'
    else:
        try:
            report['review']=inspect(args.scan_root,args.max_depth,args.max_entries,args.max_candidates)
            report['hold_category']='STOCK_RECOVERY_AUTHENTICITY_AND_INDEPENDENT_RESTORE_UNVERIFIED'
        except (Hold,prev.Hold,base.Hold,ValueError,TypeError,OSError,RuntimeError,OverflowError,EOFError,zipfile.BadZipFile):
            report['hold_category']='BOUNDED_CANDIDATE_CONTENT_REVIEW_REFUSED_OR_INCOMPLETE'
    print(json.dumps(report,sort_keys=True,separators=(',',':')))
    return 2

if __name__=='__main__':sys.exit(main())
