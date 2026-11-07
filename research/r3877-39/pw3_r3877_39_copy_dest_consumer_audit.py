#!/usr/bin/env python3
"""R3877.39: hash-pinned printed cp destination/consumer audit (no execution).

Reuses strict R3877.31-38 log pins. Exact printed token comparison is NOT
proof of executed argv or filesystem copies. No path, basename or derived
per-path digest is printed, persisted or sent to GitHub.
NOT_BOOTABLE remains immutable, including for complete lexical matches.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import pw3_r3877_31_buildlog_audit as r31
import pw3_r3877_34_pinned_link_structure as r34
import pw3_r3877_35_object_link_consistency as r35
import pw3_r3877_36_unlinked_compile_triage as r36
import pw3_r3877_37_auxiliary_context_audit as r37
import pw3_r3877_38_copy_operand_audit as r38

MILESTONE = 'R3877.39'
EXPECTED_COPY = 5
MAX_LINE_TOKENS = 10000
MAX_SCAN_LINES = 3000


def require(ok, reason):
    if not ok:
        raise r31.AuditHold(reason)


def destination_class(value):
    """Only coarse, allowlisted classes. Never emit path components."""
    if value.endswith('.o'):
        return 'object_o'
    if value.endswith('.lo'):
        return 'object_lo'
    if value.endswith('.a'):
        return 'archive_a'
    if value.endswith('.so') or '.so.' in value:
        return 'shared_library_like'
    if value.endswith('/'):
        return 'directory_syntax'
    return 'other_or_unresolved'


def printed_words(line):
    """Tokenize text *without* evaluating any shell command/substitution."""
    if len(line) > r34.r331.MAX_LEX_JOIN_CHARS:
        return None
    try:
        words = r34.tokenize_no_execution(line.strip())
    except r31.AuditHold:
        return None
    require(len(words) <= MAX_LINE_TOKENS, 'OTHER_LINE_TOKEN_BUDGET')
    return words


def collect_destinations(lines, orphans, compile_lines):
    """Private source/destination records, never used in returned JSON."""
    require(len(lines) <= MAX_SCAN_LINES, 'LOG_LINE_BUDGET')
    require(len(orphans) == len(set(orphans)) == EXPECTED_COPY,
            'EXPECTED_FIVE_DISTINCT_UNLINKED_OBJECTS')
    orphan_set = set(orphans)
    records = []
    seen = set()
    unparsed = 0
    nonmain = 0
    for n, line in enumerate(lines, 1):
        if n in compile_lines or n in (1666, 1667):
            continue
        nonmain += 1
        if not line.strip():
            continue
        words = printed_words(line)
        if words is None:
            unparsed += 1
            continue
        matches = [x for x in words if x in orphan_set]
        if not matches:
            continue
        require(r37.family(words) == 'copy', 'ORPHAN_MENTION_NONCOPY_CHANGED')
        require(len(matches) == 1 and matches[0] not in seen,
                'ORPHAN_COPY_MENTION_COUNT_CHANGED')
        mode, operands = r38.cp_operands(words)
        require(mode == 'supported_cp_positional_shape', 'ORPHAN_CP_SHAPE_CHANGED')
        obj = matches[0]
        require(obj in operands[:-1], 'ORPHAN_NOT_IN_COPY_SOURCE_OPERANDS')
        destination = operands[-1]
        require(destination != obj, 'COPY_SOURCE_EQUALS_DESTINATION')
        records.append({'source':obj, 'dest':destination, 'line':n,
                        'single_source':len(operands)==2})
        seen.add(obj)
    require(nonmain == r37.EXPECTED_SCANNED, 'NONMAIN_LINE_COUNT_CHANGED')
    require(unparsed == r37.EXPECTED_UNPARSED, 'NONMAIN_UNPARSED_COUNT_CHANGED')
    require(len(records) == EXPECTED_COPY, 'FIVE_COPY_RECORDS_NOT_PRESENT')
    require(len({r['dest'] for r in records}) == EXPECTED_COPY,
            'COPY_DESTINATION_UNIQUENESS_CHANGED')
    return records, unparsed


def classify_destination_consumers(lines, records, compile_records, link_tokens):
    """Count exact references strictly *later* than each cp log line.

    Main-link/compile output identity checked separately; all references are
    text matches, not evidence that a copy or consumer actually executed.
    """
    all_compile = {r['output'] for r in compile_records}
    linked_objects = {x for x in link_tokens if r35.is_object_like(x)}
    dests = {r['dest'] for r in records}
    copy_lines = {r['line'] for r in records}
    matched_consumer_destinations = set()
    later_families = Counter()
    other_later_mentions = 0
    unparsed = 0
    scan = 0
    for n, line in enumerate(lines, 1):
        if n in copy_lines or n in (1666,1667):
            continue
        scan += 1
        if not line.strip():
            continue
        words = printed_words(line)
        if words is None:
            unparsed += 1
            continue
        if not words:
            continue
        present = dests.intersection(words)
        if not present:
            continue
        family = r37.family(words)
        for r in records:
            if r['dest'] in present and n > r['line']:
                matched_consumer_destinations.add(r['dest'])
                later_families[family] += 1
                other_later_mentions += words.count(r['dest'])
    return {
        'copy_destination_suffix_classes':dict(sorted(Counter(destination_class(r['dest']) for r in records).items())),
        'copy_operand_arity_classes':dict(sorted(Counter('single_source_single_destination' if r['single_source'] else 'multiple_sources_destination' for r in records).items())),
        'copy_destinations_matching_printed_compile_output_text':len(dests.intersection(all_compile)),
        'copy_destinations_matching_main_link_object_input_text':len(dests.intersection(linked_objects)),
        'distinct_copy_destinations_with_later_full_token_mentions':len(matched_consumer_destinations),
        'later_full_token_destination_mention_count':other_later_mentions,
        'later_printed_command_family_mention_counts':dict(sorted(later_families.items())),
        'distinct_copy_destinations_without_observed_later_full_token_mentions':EXPECTED_COPY-len(matched_consumer_destinations),
        'other_scanned_log_lines_for_destination_mentions':scan,
        'other_unparsed_log_lines_for_destination_mentions':unparsed,
        'unparsed_lines_could_contain_additional_references':bool(unparsed),
        'absence_of_printed_mentions_does_not_prove_no_actual_consumers':True,
        'no_paths_basenames_raw_tokens_or_per_path_digests_disclosed':True,
    }


def analyze(raw, *, expected_hash=r31.EXPECTED_SHA256,
            expected_length=r31.EXPECTED_BYTES):
    previous = r38.analyze(raw, expected_hash=expected_hash,
                           expected_length=expected_length)
    for key, expected in {
        'extra_objects_in_source_operand_position':5,
        'extra_objects_in_destination_operand_position':0,
        'distinct_printed_destination_texts_for_supported_copy_shapes':5,
        'printed_cp_syntax_classes':{'supported_cp_positional_shape':5},
        'nonmain_lines_not_lexically_parsed':1,
    }.items():
        require(previous.get(key) == expected, 'PRIOR_R3877_38_'+key.upper()+'_CHANGED')
    lines, compiled = r36.extract_records(raw)
    linked = r35.link_tokens_from_pinned(raw)
    orphans, _ = r36.reconcile_records(compiled, linked)
    record, other_unparsed = collect_destinations(
        lines, [r['output'] for r in orphans],
        {r['line_number'] for r in compiled})
    evidence = classify_destination_consumers(lines,record,compiled,linked)
    return {
        'log_sha256': hashlib.sha256(raw).hexdigest(),
        'log_bytes':len(raw),
        'joined_link_candidate_sha256':r34.PINNED_JOINED_SHA256,
        'compile_outputs':1428,
        'main_link_object_matches':1423,
        'distinct_extra_copy_sources':len({r['source'] for r in record}),
        'distinct_extra_copy_destinations':len({r['dest'] for r in record}),
        'prior_r3877_38_all_pins_and_counts_reverified':True,
        **evidence,
        'historical_builder_machine_identity_verified':False,
        'historical_builder_toolchain_versions_verified':False,
        'historical_builder_cflags_ldflags_verified':False,
        'historical_builder_complete_link_invocation_verified':False,
        'historical_builder_compiler_and_linker_invocation_provenance_verified':False,
        'printed_copy_commands_executed_verified':False,
        'printed_log_cryptographically_authenticated':False,
        'source_to_binary_reproducibility_verified':False,
        'target_musl_runtime_verified':False,
        'kindle_ssh_sessions':0,
        'binary_execution_performed':False,
    }


def base():
    out = r38.base()
    out.update(milestone=MILESTONE,result='HOLD',hold_category='NOT_BOOTABLE',
               historical_builder_complete_link_invocation_verified=False,
               historical_builder_toolchain_versions_verified=False,
               source_to_binary_reproducibility_verified=False,
               binary_execution_performed=False)
    return out


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('log',help='Exact R3877.30 pinned public musl ARMv7 build log')
    args=p.parse_args(argv)
    result=base()
    rc=2
    try:
        path=Path(args.log)
        require(path.is_file() and not path.is_symlink(),'LOG_FILE_MISSING_OR_SYMLINK')
        with path.open('rb') as f:
            raw=f.read(r31.MAX_BYTES+1)
        result['inventory']=analyze(raw)
        result['result']='PASS_PINNED_FIVE_COPY_DESTINATION_TEXT_CONSUMER_TRIAGE_ONLY'
        rc=0
    except r31.AuditHold as e:
        result['hold_category']=str(e)
    except (OSError,ValueError,UnicodeError,OverflowError):
        result['hold_category']='COPY_DESTINATION_TRIAGE_ERROR'
    print(json.dumps(result,sort_keys=True,indent=2))
    return rc


if __name__=='__main__':
    raise SystemExit(main())
