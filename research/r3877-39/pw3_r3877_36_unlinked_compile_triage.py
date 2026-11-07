#!/usr/bin/env python3
"""R3877.36: classify five UNLINKED PRINTED compile outputs in pinned musl log.

Offline static lexical research only: nothing is compiled, run, evaluated,
extracted or disclosed except aggregate allowlisted counts. A printed build
log is not a cryptographic record of executed argv, and a printed unused
object is not itself a build defect. All Kindle/boot/firmware gates stay held.
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
import pw3_r3877_35_object_link_consistency as r35

MILESTONE = 'R3877.36'
PINNED_COMPILES = 1428
PINNED_LINK_OBJECTS = 1423
PINNED_UNLINKED = 5
MAX_OTHER_LINES = 3000
MAX_OTHER_TOKEN_BUDGET = 10000
SAFE_FLAGS = ('-O2', '-O3', '-fPIC', '-fno-stack-protector',
              '-fno-asynchronous-unwind-tables')
SAFE_EXTENSIONS = ('.c', '.S', '.s', '.cc', '.cpp', '.cxx')


def require(value, reason):
    if not value:
        raise r31.AuditHold(reason)


def printed_compile_record(tokens, line_number):
    """No names/paths leave this function except for private comparison."""
    output = r35.output_from_compile(tokens)
    require(output is not None, 'UNRECOGNIZED_COMPILE_OUTPUT')
    cpos = [i for i, x in enumerate(tokens) if x == '-c']
    if len(cpos) == 1 and cpos[0] + 1 < len(tokens):
        source = tokens[cpos[0]+1]
        suffix = next((ext for ext in SAFE_EXTENSIONS if source.endswith(ext)), 'other_or_unresolved')
        if source.startswith('-'):
            suffix = 'other_or_unresolved'
    else:
        suffix = 'other_or_unresolved'
    return {'output': output, 'line_number': line_number,
            'source_suffix_class': suffix,
            'object_suffix_class': '.lo' if output.endswith('.lo') else '.o',
            'printed_flags': tuple(flag for flag in SAFE_FLAGS if flag in tokens)}


def extract_records(raw):
    """Exact R35 compile selection, every output unique, same SHA-pinned log."""
    lines = r31.ANSI.sub('', raw.decode('utf-8', errors='replace')).splitlines()
    require(len(lines) == 1981, 'PRINTED_LOG_LINE_COUNT_CHANGED')
    records = []
    for n, line in enumerate(lines, 1):
        s = line.strip()
        if (len(s) > 15000 or not r31.COMPILER.search(s) or
                not r31.OPT.search(s) or not re.search(r'(?:^|\s)-c(?:\s|$)', s)):
            continue
        driver, tokens = r32.parse_tool(s)
        require(driver == 'cc' and bool(tokens), 'COMPILE_DRIVER_OR_LEXER_CHANGED')
        records.append(printed_compile_record(tokens, n))
    require(len(records) == PINNED_COMPILES, 'PRINTED_COMPILE_COUNT_CHANGED')
    require(len({r['output'] for r in records}) == PINNED_COMPILES, 'DUPLICATE_PRINTED_COMPILE_OUTPUT')
    return lines, records


def classify_other_references(lines, orphan_outputs, compile_line_numbers):
    """Count only full printed tokens; no basename or substring comparison.

    These lines are separately printed log records, NOT demonstrated uses of
    compiled outputs. If lexical parsing fails, never claim absence of use.
    """
    require(len(lines) <= MAX_OTHER_LINES, 'OTHER_LINE_COUNT_BUDGET')
    orphan_set = set(orphan_outputs)
    require(len(orphan_set) == PINNED_UNLINKED, 'EXPECTED_FIVE_UNLINKED_OUTPUTS')
    observed_with_extra_mention = set()
    class_counts = Counter()
    unparsed_lines = 0
    scanned_lines = 0
    for n, line in enumerate(lines, 1):
        if n in compile_line_numbers or n in (1666, 1667):
            continue
        scanned_lines += 1
        if not line.strip():
            continue
        if len(line) > r34.r331.MAX_LEX_JOIN_CHARS:
            unparsed_lines += 1
            continue
        try:
            words = r34.tokenize_no_execution(line.strip())
        except r31.AuditHold:
            unparsed_lines += 1
            continue
        require(len(words) <= MAX_OTHER_TOKEN_BUDGET, 'OTHER_LINE_TOKEN_BUDGET')
        overlaps = orphan_set.intersection(words)
        if not overlaps:
            continue
        observed_with_extra_mention.update(overlaps)
        # Never publish raw command tokens or paths. Classify printing only.
        first = [word.rsplit('/',1)[-1].lower() for word in words[:8]]
        if any(w in ('ar', 'ranlib') for w in first):
            category = 'archive_tool_like'
        elif any(w in ('cc', 'gcc', 'ld', 'ld.bfd', 'clang') for w in first):
            category = 'compiler_linker_like'
        elif any(w in ('install', 'cp', 'mv', 'objcopy', 'strip') for w in first):
            category = 'copy_install_or_binary_tool_like'
        else:
            category = 'other_printed_context'
        class_counts[category] += len(overlaps)
    return {
        'other_printed_lines_scanned': scanned_lines,
        'other_printed_lines_not_lexically_parsed': unparsed_lines,
        'unlinked_outputs_with_full_token_mentions_outside_compile_or_main_link': len(observed_with_extra_mention),
        'unlinked_outputs_without_such_observed_mentions': PINNED_UNLINKED-len(observed_with_extra_mention),
        'extra_printed_token_mentions_by_generic_context': dict(sorted(class_counts.items())),
        'absence_of_printed_token_mentions_is_not_proof_of_unused_artifacts': True,
    }


def reconcile_records(records, link_tokens, *, expected_compile=PINNED_COMPILES,
                      expected_link=PINNED_LINK_OBJECTS,
                      expected_unlinked=PINNED_UNLINKED):
    require(len(records) == expected_compile, 'COMPILE_RECORD_COUNT_CHANGED')
    comp = [r['output'] for r in records]
    link = [x for x in link_tokens if r35.is_object_like(x)]
    require(len(link) == expected_link, 'LINK_OBJECT_COUNT_CHANGED')
    counts = r35.summarize_printed_names(comp, link)
    require(counts['exact_text_object_occurrences_matched'] == expected_link,
            'PRINTED_LINK_OBJECT_WITHOUT_COMPILE_OUTPUT')
    require(counts['printed_link_object_occurrences_without_compile_output_match'] == 0,
            'UNMATCHED_PRINTED_LINK_OBJECT')
    require(counts['printed_compile_output_occurrences_not_in_link_candidate'] == expected_unlinked,
            'UNLINKED_COMPILE_OUTPUT_COUNT_CHANGED')
    link_set = set(link)
    orphan = [r for r in records if r['output'] not in link_set]
    require(len(orphan) == expected_unlinked, 'ORPHAN_CLASSIFICATION_MISMATCH')
    kinds = Counter(r['source_suffix_class'] for r in orphan)
    outputs = Counter(r['object_suffix_class'] for r in orphan)
    flags = Counter(flag for record in orphan for flag in record['printed_flags'])
    return orphan, {
        'printed_compile_outputs': len(records),
        'printed_main_link_objects': len(link),
        'exact_text_matches': counts['exact_text_object_occurrences_matched'],
        'unmatched_printed_main_link_objects': 0,
        'printed_compile_outputs_not_in_main_link': len(orphan),
        'unlinked_output_source_suffix_classes': dict(sorted(kinds.items())),
        'unlinked_output_object_suffix_classes': dict(sorted(outputs.items())),
        'unlinked_output_allowlisted_compile_flag_counts': dict(sorted(flags.items())),
        'unlinked_compile_lines_before_main_link': sum(r['line_number'] < 1666 for r in orphan),
        'unlinked_compile_lines_after_main_link': sum(r['line_number'] > 1667 for r in orphan),
    }


def analyze(raw, *, expected_hash=r31.EXPECTED_SHA256,
            expected_length=r31.EXPECTED_BYTES):
    # Preserve the full previous check, including both link-line SHA-256 pins.
    baseline = r35.analyze(raw, expected_hash=expected_hash, expected_bytes=expected_length)
    require(baseline['printed_compile_output_occurrences_not_in_link_candidate'] == PINNED_UNLINKED,
            'PRIOR_R3877_35_UNLINKED_COUNT_CHANGED')
    require(baseline['printed_link_object_occurrences_without_compile_output_match'] == 0,
            'PRIOR_R3877_35_LINK_MATCH_CHANGED')
    lines, records = extract_records(raw)
    link_tokens = r35.link_tokens_from_pinned(raw)
    orphan,counts = reconcile_records(records,link_tokens)
    extra = classify_other_references(lines, [r['output'] for r in orphan],
                                       {r['line_number'] for r in records})
    return {
        'log_sha256': hashlib.sha256(raw).hexdigest(),
        'log_bytes': len(raw),
        'prior_r3877_35_all_pins_and_counts_reverified': True,
        'joined_link_candidate_sha256': r34.PINNED_JOINED_SHA256,
        **counts, **extra,
        'source_paths_or_basenames_disclosed': False,
        'object_paths_or_basenames_disclosed': False,
        'raw_commands_or_tokens_disclosed': False,
        'printed_command_text_executed': False,
        'printed_nonmain_link_mentions_are_not_execution_proof': True,
        'historical_builder_machine_identity_verified': False,
        'historical_builder_toolchain_versions_verified': False,
        'historical_builder_complete_link_invocation_verified': False,
        'historical_builder_cflags_ldflags_verified': False,
        'historical_builder_compiler_and_linker_invocation_provenance_verified': False,
        'public_build_log_signature_verified': False,
        'source_to_binary_reproducibility_verified': False,
        'target_musl_runtime_verified': False,
        'kindle_ssh_sessions': 0,
    }


def base():
    out = r35.base()
    out.update(milestone=MILESTONE, result='HOLD', hold_category='NOT_BOOTABLE',
               historical_builder_complete_link_invocation_verified=False,
               historical_builder_compiler_and_linker_invocation_provenance_verified=False,
               historical_builder_toolchain_versions_verified=False,
               historical_builder_cflags_ldflags_verified=False,
               source_to_binary_reproducibility_verified=False,
               binary_execution_performed=False)
    return out


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('log', help='Previously downloaded exact-hash Alpine musl public build log')
    a=p.parse_args(argv)
    result=base()
    rc=2
    try:
        path=Path(a.log)
        require(path.is_file() and not path.is_symlink(), 'LOG_FILE_MISSING_OR_SYMLINK')
        with path.open('rb') as f:
            raw=f.read(r31.MAX_BYTES+1)
        result['inventory']=analyze(raw)
        result['result']='PASS_PINNED_UNLINKED_PRINTED_COMPILE_OUTPUT_TRIAGE_ONLY'
        rc=0
    except r31.AuditHold as exc:
        result['hold_category']=str(exc)
    except (OSError, ValueError, UnicodeError, OverflowError):
        result['hold_category']='PRINTED_UNLINKED_COMPILE_TRIAGE_ERROR'
    print(json.dumps(result, indent=2, sort_keys=True))
    return rc


if __name__=='__main__':
    raise SystemExit(main())
