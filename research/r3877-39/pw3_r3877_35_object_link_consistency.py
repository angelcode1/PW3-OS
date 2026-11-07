#!/usr/bin/env python3
"""R3877.35: compare hash-pinned *printed* compile outputs to link inputs.

Research and educational use only. Never executes shell, compiler, ARM code,
Docker or SSH; no raw paths, names, token streams, or per-path digests emitted.
Matches are exact textual identities within a single unsigned public log.
Neither matching names nor a complete printed command attest executed argv.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import pw3_r3877_31_buildlog_audit as r31
import pw3_r3877_32_log_command_shapes as r32
import pw3_r3877_34_pinned_link_structure as r34

MILESTONE = 'R3877.35'
EXPECTED_PRINTED_COMPILE = 1428
EXPECTED_LINK_OBJECT_LIKE = 1423
EXPECTED_LINK_TOKENS = 1494
MAX_COMPILE_TOKENS = 2048


def require(condition, reason):
    if not condition:
        raise r31.AuditHold(reason)


def is_object_like(name):
    return (bool(name) and not name.startswith('-') and
            (name.endswith('.o') or name.endswith('.lo')))


def output_from_compile(tokens):
    """A single literal `-o <word>` compile output, without expansion."""
    require(isinstance(tokens, list) and len(tokens) <= MAX_COMPILE_TOKENS,
            'COMPILE_TOKEN_BUDGET_EXCEEDED')
    require('-c' in tokens, 'PRINTED_COMPILE_SWITCH_MISSING')
    positions=[i for i,token in enumerate(tokens) if token == '-o']
    if len(positions) != 1:
        return None
    i=positions[0]
    if i+1 >= len(tokens) or not is_object_like(tokens[i+1]):
        return None
    if tokens[i+1] in ('.','..'):
        return None
    return tokens[i+1]


def summarize_printed_names(compile_output_tokens, link_tokens):
    """Count exact full-token matches; do not disclose paths or basenames.

    An output token is only observed printed data, not evidence that the
    compilation ran. Repeated object inputs and repeated outputs are counted,
    never silently set-deduplicated.
    """
    require(len(compile_output_tokens) <= 2000, 'COMPILE_OUTPUT_COUNT_TOO_LARGE')
    require(len(link_tokens) <= r34.MAX_TOKENS, 'LINK_TOKEN_COUNT_TOO_LARGE')
    require(all(isinstance(x,str) and len(x) <= 16384 for x in compile_output_tokens+link_tokens),
            'TOKEN_INVALID')
    comp=Counter(x for x in compile_output_tokens if is_object_like(x))
    link=Counter(x for x in link_tokens if is_object_like(x))
    matched=sum(min(n,link.get(name,0)) for name,n in comp.items())
    unmatched_link=sum((link-comp).values())
    unlinked_compile=sum((comp-link).values())
    require(matched+unmatched_link==sum(link.values()),'INTERNAL_LINK_BALANCE_ERROR')
    require(matched+unlinked_compile==sum(comp.values()),'INTERNAL_COMPILE_BALANCE_ERROR')
    return {
        'compile_output_objects_extracted': sum(comp.values()),
        'compile_output_distinct_object_texts': len(comp),
        'compile_output_duplicate_text_occurrences': sum(n-1 for n in comp.values()),
        'link_object_like_input_tokens': sum(link.values()),
        'link_object_distinct_texts': len(link),
        'link_duplicate_object_text_occurrences': sum(n-1 for n in link.values()),
        'exact_text_object_occurrences_matched': matched,
        'printed_link_object_occurrences_without_compile_output_match': unmatched_link,
        'printed_compile_output_occurrences_not_in_link_candidate': unlinked_compile,
        'compile_output_tokens_not_disclosed': True,
        'link_input_tokens_not_disclosed': True,
        'per_path_digests_not_disclosed': True,
        'basename_or_prefix_normalization_used': False,
        'printed_text_match_is_not_executed_build_proof': True,
    }


def collect_compiles(raw):
    """Mirror the pinned R3877.32 compile-line selector; no shell execution."""
    lines=r31.ANSI.sub('',raw.decode('utf-8',errors='replace')).splitlines()
    output_words=[]
    compile_line_count=0
    parse_failures=0
    not_extractable=0
    driver_cc=0
    for physical in lines:
        s=physical.strip()
        if len(s)>15000 or not r31.COMPILER.search(s) or not r31.OPT.search(s):
            continue
        if not re.search(r'(?:^|\s)-c(?:\s|$)',s):
            continue
        compile_line_count+=1
        driver, tokens=r32.parse_tool(s)
        if not tokens or driver in ('unparsed_shell_quoting','argv_too_long'):
            parse_failures+=1
            continue
        if driver=='cc':
            driver_cc+=1
        out=output_from_compile(tokens)
        if out is None:
            not_extractable+=1
        else:
            output_words.append(out)
    require(compile_line_count==EXPECTED_PRINTED_COMPILE,
            'PRINTED_COMPILE_LINE_COUNT_CHANGED')
    require(parse_failures==0,'COMPILE_LINES_NOT_FULLY_TOKENIZED')
    require(driver_cc==EXPECTED_PRINTED_COMPILE,'PRINTED_COMPILE_DRIVERS_CHANGED')
    return output_words, {
        'compile_lines_reconciled':compile_line_count,
        'compile_argv_parse_failures':parse_failures,
        'compile_lines_without_single_literally_recognized_object_output':not_extractable,
        'all_compile_drivers_printed_cc':True,
    }


def link_tokens_from_pinned(raw):
    lines=r31.ANSI.sub('',raw.decode('utf-8',errors='replace')).splitlines()
    require(len(lines)>1666,'LINK_CANDIDATE_LINES_MISSING')
    first=lines[1665].strip()
    second=lines[1666]
    require(r34.sha(first)==r34.r321.EXPECTED_LINK_LINE_SHA256,
            'LINK_LINE_SHA_CHANGED')
    require(r34.sha(second)==r34.PINNED_SECOND_SHA256,
            'LINK_NEIGHBOR_SHA_CHANGED')
    require(first.endswith('\\'),'LINK_FIRST_LINE_NO_TRAILING_BACKSLASH')
    joined=first[:-1]+second
    require(r34.sha(joined)==r34.PINNED_JOINED_SHA256,'JOINED_CANDIDATE_SHA_CHANGED')
    require(len(joined)==r34.PINNED_JOINED_CHARS,'JOINED_CANDIDATE_LENGTH_CHANGED')
    t=r34.tokenize_no_execution(joined)
    require(len(t)==EXPECTED_LINK_TOKENS,'PRINTED_LINK_TOKEN_COUNT_CHANGED')
    require(r34.count_structure(t)['token_classes'].get('object_like')==EXPECTED_LINK_OBJECT_LIKE,
            'PRINTED_LINK_OBJECT_COUNT_CHANGED')
    return t


def analyze(raw, *, expected_hash=r31.EXPECTED_SHA256,
            expected_bytes=r31.EXPECTED_BYTES):
    # Expensive but intentional: first check every previous R3877.34 pin.
    baseline=r34.analyze(raw,expected_hash=expected_hash,expected_length=expected_bytes)
    require(baseline['lexically_recognized_candidate_token_count']==EXPECTED_LINK_TOKENS,
            'R3877_34_TOKEN_COUNT_CHANGED')
    require(baseline['token_classes']['object_like']==EXPECTED_LINK_OBJECT_LIKE,
            'R3877_34_OBJECT_CLASSIFICATION_CHANGED')
    require(baseline['explicit_output_switch_count']==1,
            'R3877_34_OUTPUT_SWITCH_CHANGED')
    compile_words,comp_meta=collect_compiles(raw)
    link_words=link_tokens_from_pinned(raw)
    comparison=summarize_printed_names(compile_words,link_words)
    return {
        'log_sha256':hashlib.sha256(raw).hexdigest(),
        'log_bytes':len(raw),
        'prior_r3877_34_full_pins_reverified':True,
        'joined_link_candidate_sha256':r34.PINNED_JOINED_SHA256,
        'joined_link_candidate_tokens':EXPECTED_LINK_TOKENS,
        **comp_meta,
        **comparison,
        'raw_command_lines_disclosed':False,
        'source_paths_or_basenames_disclosed':False,
        'linker_input_paths_or_basenames_disclosed':False,
        'historical_builder_complete_link_invocation_verified':False,
        'historical_builder_cflags_ldflags_verified':False,
        'historical_builder_toolchain_versions_verified':False,
        'historical_builder_machine_identity_verified':False,
        'source_to_binary_reproducibility_verified':False,
        'public_build_log_signature_verified':False,
        'kindle_ssh_sessions':0,
    }


def base():
    return dict(milestone=MILESTONE,result='HOLD',hold_category='NOT_BOOTABLE',
        immutable_hold='NOT_BOOTABLE',binary_execution_performed=False,
        boot_performed=False,firmware_write_performed=False,
        physical_device_access_performed=False,
        new_kindle_binary_installed_or_executed=False,kindle_ssh_sessions=0,
        historical_builder_complete_link_invocation_verified=False,
        historical_builder_compiler_and_linker_invocation_provenance_verified=False,
        historical_builder_machine_identity_verified=False,
        historical_builder_toolchain_versions_verified=False,
        historical_builder_cflags_ldflags_verified=False,
        source_to_binary_reproducibility_verified=False,
        target_musl_runtime_verified=False,recovery_verified=False,
        public_build_log_signature_verified=False)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('log',help='Existing local R3877.30 musl-armv7-build.log')
    args=p.parse_args(argv)
    result=base();rc=2
    try:
        path=Path(args.log)
        require(path.is_file() and not path.is_symlink(), 'LOG_FILE_MISSING_OR_SYMLINK')
        with path.open('rb') as f:
            raw=f.read(r31.MAX_BYTES+1)
        result['inventory']=analyze(raw)
        result['result']='PASS_PINNED_PRINTED_COMPILE_LINK_OBJECT_CROSSCHECK_ONLY'
        rc=0
    except r31.AuditHold as exc:
        result['hold_category']=str(exc)
    except (OSError,ValueError,UnicodeError,OverflowError):
        result['hold_category']='OBJECT_CROSSCHECK_PARSE_ERROR'
    print(json.dumps(result,sort_keys=True,indent=2))
    return rc


if __name__=='__main__':
    raise SystemExit(main())
