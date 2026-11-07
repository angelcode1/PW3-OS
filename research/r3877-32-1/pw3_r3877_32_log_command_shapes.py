#!/usr/bin/env python3
"""R3877.32: bounded, hash-pinned shape analysis of a public Alpine ARMv7 build log.

Host-only local-data analysis. NO command execution, no Docker, no SSH, no flash.
A printed command is not proof of execution, exact builder versions, or reproducibility.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import shlex

import pw3_r3877_31_buildlog_audit as prior

MILESTONE = 'R3877.32'
EXPECTED_LINES = 1981
EXPECTED_COMPILE = 1428
EXPECTED_LINK = 1
EXPECTED_COMPILER_WITH_FLAGS = 1429
EXPECTED_FLAG_COUNTS = {
    '-O2': 1429,
    '-fno-asynchronous-unwind-tables': 1429,
    '-fPIC': 1425,
    '-O3': 92,
    '-fno-stack-protector': 13,
    '-Wl,-soname,libc.musl-armv7.so.1': 1,
}

# All reportable flags require full-token matches. No -I, -D, paths, URLs, etc.
SAFE_FLAG = re.compile(r'(?:-O[0-3sgz]|-Ofast|-fPIC|-fpic|-fPIE|-fpie|'
                       r'-fno-asynchronous-unwind-tables|-fno-stack-protector|'
                       r'-fstack-protector(?:-strong|-all)?|-fno-plt|'
                       r'-m(?:arch|cpu|tune|fpu|float-abi|abi)=[A-Za-z0-9_.+-]{1,48}|'
                       r'-marm|-mthumb|-mno-thumb|-Wl,-soname,libc\.musl-armv7\.so\.1|'
                       r'-Wl,-z,(?:relro|now|noexecstack)|-shared|-static|-nostdlib|'
                       r'-Wl,--hash-style=(?:gnu|sysv|both))')
DRIVER = re.compile(r'(?:(?:[a-z0-9_.+-]+-)?)(gcc|cc|clang|g\+\+|c\+\+|ld|ld\.bfd)\Z',re.I)
TOOL_TOKEN = re.compile(r'[a-zA-Z0-9_+./-]{1,120}\Z')


def require(cond, reason):
    if not cond:
        raise prior.AuditHold(reason)


def parse_tool(command_text):
    """Only classify an allowlisted compiler/linker basename; never publish paths."""
    try:
        tokens = shlex.split(command_text, posix=True)
    except ValueError:
        return ('unparsed_shell_quoting', [])
    if len(tokens) > 2048:
        return ('argv_too_long', [])
    for token in tokens[:14]:
        if not TOOL_TOKEN.fullmatch(token):
            continue
        base = token.rsplit('/',1)[-1].lower()
        found = DRIVER.fullmatch(base)
        if found:
            suffix = found.group(1)
            name = suffix.lower()
            return (('target-prefixed-' if base != name else '')+name, tokens)
    return ('driver_unresolved', tokens)


def analyze(raw, expected_hash=prior.EXPECTED_SHA256,
            expected_length=prior.EXPECTED_BYTES):
    prior_report = prior.analyze(raw, expected_hash, expected_length)
    require(prior_report['log_line_count'] == EXPECTED_LINES,'PRIOR_LOG_LINE_COUNT_CHANGED')
    require(prior_report['likely_compile_lines'] == EXPECTED_COMPILE,'PRIOR_COMPILE_LINE_COUNT_CHANGED')
    require(prior_report['likely_link_lines'] == EXPECTED_LINK,'PRIOR_LINK_LINE_COUNT_CHANGED')
    require(prior_report['compiler_like_lines_with_flags'] == EXPECTED_COMPILER_WITH_FLAGS,
            'PRIOR_COMPILER_WITH_FLAGS_LINE_COUNT_CHANGED')
    observed = {x['flag']:x['observed_line_count'] for x in prior_report['allowlisted_flags']}
    require(all(observed.get(k) == v for k,v in EXPECTED_FLAG_COUNTS.items()),
            'PRIOR_ALLOWLISTED_FLAG_COUNTS_CHANGED')

    lines = prior.ANSI.sub('', raw.decode('utf-8', 'replace')).splitlines()
    comp_tools=collections.Counter()
    link_tools=collections.Counter()
    compile_safe=collections.Counter()
    link_safe=collections.Counter()
    line_hashes=[]
    unresolved=[]
    compile_argv_parse_failures=0
    link_argv_parse_failures=0
    candidate_compile_count=0
    candidate_link_count=0
    compile_lines_with_arm_abi_flag=0
    link_line_numbers=[]
    for n,line in enumerate(lines,1):
        s=line.strip()
        if len(s)>15000 or not prior.COMPILER.search(s) or not prior.OPT.search(s):
            continue
        is_compile=bool(re.search(r'(?:^|\s)-c(?:\s|$)',s))
        is_link=bool(re.search(r'(?:^|\s)-shared(?:\s|$)',s) or '-Wl,' in s)
        if not is_compile and not is_link:
            continue
        tool,tokens=parse_tool(s)
        # Match the prior R3877.31 classification, with overlapping lines reported separately.
        flags=set(t for t in tokens if SAFE_FLAG.fullmatch(t))
        if is_compile:
            candidate_compile_count+=1
            comp_tools[tool]+=1
            compile_safe.update(flags)
            if any(t.startswith(('-mfloat-abi=','-mfpu=','-march=','-mabi=')) for t in flags):
                compile_lines_with_arm_abi_flag+=1
            if tool in ('unparsed_shell_quoting','argv_too_long'):
                compile_argv_parse_failures+=1
        if is_link:
            candidate_link_count+=1
            link_tools[tool]+=1
            link_safe.update(flags)
            link_line_numbers.append(n)
            if tool in ('unparsed_shell_quoting','argv_too_long'):
                link_argv_parse_failures+=1
            # Hash only; never disclose private paths, macros or source filenames.
            line_hashes.append({'line_number':n,'printed_command_sha256':hashlib.sha256(s.encode()).hexdigest(),
                                'driver_class':tool,'shell_tokens_parsed':bool(tokens),
                                'token_count':len(tokens) if tokens else None,
                                'allowlisted_flags':sorted(flags)})
    require(candidate_compile_count==EXPECTED_COMPILE,'COMMAND_CLASSIFICATION_COMPILE_COUNT_CHANGED')
    require(candidate_link_count==EXPECTED_LINK,'COMMAND_CLASSIFICATION_LINK_COUNT_CHANGED')
    require(len(line_hashes)==EXPECTED_LINK,'LINK_FINGERPRINT_COUNT_CHANGED')
    # Unverified banners and command strings are data, not proof of the executed toolchain.
    def counter(x):return [{'value':k,'observed_line_count':v} for k,v in sorted(x.items(),key=lambda kv:(-kv[1],kv[0]))]
    return {
        'log_sha256':prior.EXPECTED_SHA256,'log_bytes':prior.EXPECTED_BYTES,
        'prior_r3877_31_counts_reconciled':True,
        'likely_compile_line_count':candidate_compile_count,
        'likely_link_line_count':candidate_link_count,
        'compile_driver_classes':counter(comp_tools),
        'link_driver_classes':counter(link_tools),
        'safe_compile_flag_lines':counter(compile_safe),
        'safe_link_flag_lines':counter(link_safe),
        'compile_lines_with_explicit_arm_abi_flags':compile_lines_with_arm_abi_flag,
        'compile_argv_parse_failure_count':compile_argv_parse_failures,
        'link_argv_parse_failure_count':link_argv_parse_failures,
        'link_command_fingerprints':line_hashes,
        'tool_binary_path_or_hash_observed':False,
        'historical_compiler_linker_executable_versions_verified':False,
        'source_paths_disclosed':False,'raw_command_lines_disclosed':False,
        'public_build_log_signature_verified':False,
        'historical_builder_environment_reproducibility_verified':False,
    }


def base():
    d=prior.base()
    d.update(milestone=MILESTONE, result='HOLD',
        historical_builder_cflags_ldflags_verified=False,
        historical_builder_compiler_and_linker_invocation_provenance_verified=False,
        historical_builder_toolchain_versions_verified=False,
        source_to_binary_reproducibility_verified=False,
        binary_execution_performed=False)
    return d


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('log',help='Existing R3877.30 local file: musl-armv7-build.log')
    args=p.parse_args(argv)
    result=base();rc=2
    try:
        path=Path(args.log)
        require(path.is_file() and not path.is_symlink(),'LOG_FILE_MISSING_OR_SYMLINK')
        with path.open('rb') as f: raw=f.read(prior.MAX_BYTES+1)
        result['inventory']=analyze(raw)
        result['result']='PASS_HASH_PINNED_BUILDLOG_COMMAND_SHAPES_ONLY'
        rc=0
    except prior.AuditHold as e:result['hold_category']=str(e)
    except (OSError,ValueError,UnicodeError):result['hold_category']='LOG_ANALYSIS_ERROR'
    print(json.dumps(result,indent=2,sort_keys=True))
    return rc

if __name__=='__main__':raise SystemExit(main())
