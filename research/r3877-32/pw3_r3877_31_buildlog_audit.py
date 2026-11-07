#!/usr/bin/env python3
"""Host-only audit of user-pinned public Alpine ARMv7 musl build log.

Never runs binaries, invokes shell commands, accesses Kindle, or reads raw flash.
The log is unsigned public text and does not prove historical builder identity.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re

EXPECTED_SHA256 = 'a8405a50c1849aebc0fefadcab4e4f7fa7da27d9c1296fa2ce46b73df56ca2ce'
EXPECTED_BYTES = 1644394
MAX_BYTES = 2 * 1024 * 1024
SOURCE_COMMIT = '8f79d39391b46d6dbf1800fb68b8212a21d5ee2e'
PKG_MARKER = 'musl-1.2.6-r3'
ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
COMPILER = re.compile(r'(?<![\w./+-])(?:[a-z0-9_.+-]+-)?(?:gcc|cc|clang|g\+\+|c\+\+|ld|ld\.bfd)(?![\w.+-])', re.I)
OPT = re.compile(r'(?<!\S)-(?:O(?:[0-3sgz]|fast)|m(?:arch|cpu|tune|fpu|float-abi|abi)=[a-zA-Z0-9_.+-]{1,50}|f(?:PIC|pic|PIE|pie|no-pic|no-plt|stack-protector(?:-strong|-all)?|no-stack-protector|no-asynchronous-unwind-tables)|Wl,-(?:z,[a-zA-Z0-9_,-]{1,45}|soname,[a-zA-Z0-9_.+-]{1,45}|shared|static|Bsymbolic(?:-functions)?))(?=\s|$|[\'\"])')
VERSION = re.compile(r'\b(?:gcc|clang|binutils|GNU ld|GNU Make|abuild)\s*(?:\([^\n]*?\))?\s*(?:version\s*)?(\d{1,3}\.\d{1,3}(?:\.\d{1,4})?)',re.I)

class AuditHold(Exception):
    pass

def require(cond,reason):
    if not cond:
        raise AuditHold(reason)

def base():
    return dict(milestone='R3877.31', result='HOLD',hold_category='NOT_BOOTABLE',
        immutable_hold='NOT_BOOTABLE',kindle_ssh_sessions=0,
        firmware_write_performed=False,boot_performed=False,
        new_kindle_binary_installed_or_executed=False,
        historical_builder_machine_identity_verified=False,
        historical_builder_toolchain_versions_verified=False,
        historical_builder_cflags_ldflags_verified=False,
        public_build_log_signature_verified=False,
        source_to_binary_reproducibility_verified=False,
        target_musl_runtime_verified=False,recovery_verified=False)

def analyze(raw,expected_hash=EXPECTED_SHA256,expected_length=EXPECTED_BYTES):
    require(isinstance(raw,bytes),'INVALID_LOG_TYPE')
    require(0<len(raw)<=MAX_BYTES,'LOG_SIZE_LIMIT')
    require(len(raw)==expected_length,'LOG_LENGTH_MISMATCH')
    checksum=hashlib.sha256(raw).hexdigest()
    require(checksum==expected_hash,'LOG_SHA256_MISMATCH')
    require(b'\0' not in raw,'LOG_NUL_BYTE')
    doc=ANSI.sub('',raw.decode('utf-8','replace'))
    require(PKG_MARKER in doc,'PACKAGE_VERSION_MISSING')
    require('<html' not in doc[:8000].lower(),'LOG_IS_HTML')
    lines=doc.splitlines()
    require(len(lines)<=150000,'TOO_MANY_LOG_LINES')
    flags=collections.Counter(); compile_flags=collections.Counter(); link_flags=collections.Counter()
    versions=collections.Counter(); assignments=collections.Counter()
    sample_lines=[]; compile_lines=0; link_lines=0; compiler_lines=0
    complete=0; failed=0; stage=0
    for number,line in enumerate(lines,1):
        s=line.strip()
        if re.search(r'>>>\s*musl:\s*(?:Building|Starting|Packaging)',s,re.I): stage+=1
        if re.search(r'>>>\s*musl:\s*(?:Build complete|Build succeeded|Build finished)',s,re.I):complete+=1
        if re.search(r'>>>\s*musl:\s*(?:Build failed|Error)',s,re.I):failed+=1
        for key in ('CFLAGS','CPPFLAGS','LDFLAGS'):
            if re.search(r'(?<!\w)(?:export\s+)?'+key+r'\s*=',s): assignments[key]+=1
        if len(s)<500:
            v=VERSION.search(s)
            if v and ('version' in s.lower() or '(' in s):versions[v.group(1)]+=1
        if len(s)>15000 or not COMPILER.search(s):continue
        found=set(OPT.findall(s))
        if not found:continue
        compiler_lines+=1
        flags.update(found)
        if len(sample_lines)<12:sample_lines.append(number)
        if re.search(r'(?:^|\s)-c(?:\s|$)',s):compile_lines+=1;compile_flags.update(found)
        if re.search(r'(?:^|\s)-shared(?:\s|$)',s) or '-Wl,' in s:link_lines+=1;link_flags.update(found)
    def ordered(counter,limit=30):
        return [{'flag':k,'observed_line_count':n} for k,n in sorted(counter.items(),key=lambda kv:(-kv[1],kv[0]))[:limit]]
    return dict(log_sha256_verified_against_user_report=True,log_bytes=len(raw),
        log_sha256=checksum,log_line_count=len(lines),package_version_marker_present=True,
        source_commit_marker_found=SOURCE_COMMIT in doc,
        musl_build_stage_marker_count=stage,
        musl_build_complete_marker_count=complete,musl_build_failure_marker_count=failed,
        compiler_like_lines_with_flags=compiler_lines,likely_compile_lines=compile_lines,
        likely_link_lines=link_lines,allowlisted_flags=ordered(flags),
        allowlisted_compile_flags=ordered(compile_flags),allowlisted_link_flags=ordered(link_flags),
        explicit_assignment_mentions=dict(assignments),
        version_banner_numbers_unverified=[{'number':v,'mentions':n} for v,n in versions.most_common(12)],
        sample_compiler_like_log_line_numbers=sample_lines,raw_command_lines_disclosed=False,
        log_cryptographically_authenticated=False,historical_builder_environment_verified=False,
        compiler_versions_from_executables_verified=False,
        source_to_binary_reproducibility_verified=False)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('log',help='Local musl-1.2.6-r3.log downloaded in R3877.30')
    args=p.parse_args(argv)
    result=base();rc=2
    try:
        path=Path(args.log)
        require(path.is_file() and not path.is_symlink(),'LOG_FILE_MISSING_OR_SYMLINK')
        with path.open('rb') as f:raw=f.read(MAX_BYTES+1)
        result['inventory']=analyze(raw)
        result['result']='PASS_HASH_PINNED_PUBLIC_BUILDLOG_STATIC_EVIDENCE_ONLY'
        rc=0
    except AuditHold as e:result['hold_category']=str(e)
    except (OSError,ValueError,UnicodeError):result['hold_category']='LOG_READ_ERROR'
    print(json.dumps(result,indent=2,sort_keys=True));return rc

if __name__=='__main__':raise SystemExit(main())
