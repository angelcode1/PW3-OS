#!/usr/bin/env python3
"""R3877.37: exact-token context of five extra musl objects; read-only.

Research and educational purposes. Never runs log text or reveals paths.
Printed commands are NOT proof of executed commands. NOT_BOOTABLE is immutable.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import pw3_r3877_31_buildlog_audit as r31
import pw3_r3877_34_pinned_link_structure as r34
import pw3_r3877_35_object_link_consistency as r35
import pw3_r3877_36_unlinked_compile_triage as r36

MILESTONE = 'R3877.37'
EXPECTED_SCANNED = 551
EXPECTED_UNPARSED = 1
FAMILIES = {'cp':'copy', 'mv':'move', 'install':'install',
            'strip':'binary_tool', 'objcopy':'binary_tool',
            'ar':'archive', 'ranlib':'archive',
            'cc':'compiler_or_linker', 'gcc':'compiler_or_linker',
            'clang':'compiler_or_linker', 'ld':'compiler_or_linker',
            'ld.bfd':'compiler_or_linker'}


def require(ok, msg):
    if not ok:
        raise r31.AuditHold(msg)


def family(words):
    """Only classify the printed first token, never execute it."""
    if not words:
        return 'other_or_unresolved'
    command = words[0].rsplit('/', 1)[-1].lstrip('@+')
    if not re.fullmatch('[A-Za-z0-9_.-]{1,48}', command):
        return 'other_or_unresolved'
    return FAMILIES.get(command.lower(), 'other_or_unresolved')


def role(words, pos, kind):
    """Candidate argument position, not proven source/destination semantics."""
    require(0 <= pos < len(words), 'INVALID_ARGUMENT_POSITION')
    if kind not in ('copy', 'move', 'install') or len(words) < 3:
        return 'role_unverified'
    if '-t' in words or '--target-directory' in words or any(
            x.startswith('--target-directory=') for x in words):
        return 'role_unverified'
    if pos == len(words)-1:
        return 'final_argument_candidate'
    if 0 < pos < len(words)-1:
        return 'earlier_argument_candidate'
    return 'role_unverified'


def private_context(lines, orphan_outputs, compile_lines):
    """All path strings stay private. Aggregate exact-token matches only."""
    require(len(lines) <= 3000, 'LINE_COUNT_BUDGET')
    private = set(orphan_outputs)
    require(len(private) == len(orphan_outputs) == 5, 'FIVE_DISTINCT_OBJECTS_REQUIRED')
    seen = set()
    kinds = Counter()
    roles = Counter()
    distinct_kinds = {}
    scanned = unparsed = mentioning_lines = occurrences = 0
    for n, line in enumerate(lines, 1):
        if n in compile_lines or n in (1666, 1667):
            continue
        scanned += 1
        if not line.strip():
            continue
        if len(line) > r34.r331.MAX_LEX_JOIN_CHARS:
            unparsed += 1
            continue
        try:
            tokens = r34.tokenize_no_execution(line.strip())
        except r31.AuditHold:
            unparsed += 1
            continue
        require(len(tokens) <= 10000, 'OTHER_TOKEN_BUDGET')
        matches = [(i, token) for i, token in enumerate(tokens) if token in private]
        if not matches:
            continue
        mentioning_lines += 1
        kind = family(tokens)
        distinct_kinds.setdefault(kind, set()).update(x for _, x in matches)
        for i, token in matches:
            seen.add(token)
            occurrences += 1
            kinds[kind] += 1
            roles[role(tokens, i, kind)] += 1
    require(scanned == EXPECTED_SCANNED, 'NONMAIN_SCANNED_LINE_COUNT_CHANGED')
    require(unparsed == EXPECTED_UNPARSED, 'NONMAIN_UNPARSED_LINE_COUNT_CHANGED')
    require(len(seen) == 5, 'NOT_ALL_FIVE_OBJECTS_RECOGNIZED')
    return {
        'nonmain_lines_scanned': scanned,
        'nonmain_lines_not_lexically_parsed': unparsed,
        'nonmain_lines_with_extra_object_mentions': mentioning_lines,
        'exact_printed_object_token_mentions': occurrences,
        'extra_objects_with_any_exact_printed_mention': len(seen),
        'printed_command_family_mention_counts': dict(sorted(kinds.items())),
        'printed_command_family_distinct_object_counts': {
            name:len(vals) for name, vals in sorted(distinct_kinds.items())},
        'printed_argument_position_candidate_counts':dict(sorted(roles.items())),
        'unparsed_line_may_contain_additional_mentions': bool(unparsed),
        'printed_argument_positions_are_not_executed_io_proof': True,
        'paths_and_basenames_and_raw_tokens_disclosed': False,
    }


def analyze(raw, *, expected_hash=r31.EXPECTED_SHA256,
            expected_length=r31.EXPECTED_BYTES):
    old = r36.analyze(raw, expected_hash=expected_hash,
                      expected_length=expected_length)
    for key, expect in {
        'printed_compile_outputs_not_in_main_link':5,
        'unmatched_printed_main_link_objects':0,
        'other_printed_lines_scanned':551,
        'other_printed_lines_not_lexically_parsed':1,
        'unlinked_outputs_with_full_token_mentions_outside_compile_or_main_link':5,
        'extra_printed_token_mentions_by_generic_context':{
            'copy_install_or_binary_tool_like':5}}.items():
        require(old.get(key) == expect, 'PRIOR_R3877_36_'+key.upper()+'_CHANGED')
    lines, records = r36.extract_records(raw)
    link_tokens = r35.link_tokens_from_pinned(raw)
    orphan, _ = r36.reconcile_records(records, link_tokens)
    extra = private_context(lines, [r['output'] for r in orphan],
                            {r['line_number'] for r in records})
    return {
        'log_bytes':len(raw),
        'log_sha256':hashlib.sha256(raw).hexdigest(),
        'joined_link_candidate_sha256':r34.PINNED_JOINED_SHA256,
        'compile_output_count':1428, 'main_link_matched_object_count':1423,
        'extra_compile_output_count':5,
        'prior_r3877_36_pins_and_counts_reverified':True,
        **extra,
        'historical_builder_machine_identity_verified':False,
        'historical_builder_toolchain_versions_verified':False,
        'historical_builder_cflags_ldflags_verified':False,
        'historical_builder_complete_link_invocation_verified':False,
        'historical_builder_compiler_and_linker_invocation_provenance_verified':False,
        'public_build_log_signature_verified':False,
        'source_to_binary_reproducibility_verified':False,
        'target_musl_runtime_verified':False,
        'printed_log_command_execution_attested':False,
        'binary_execution_performed':False,
        'kindle_ssh_sessions':0,
    }


def base():
    result=r36.base()
    result.update(milestone=MILESTONE, result='HOLD',
                  hold_category='NOT_BOOTABLE',
                  historical_builder_complete_link_invocation_verified=False)
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('log', help='Pinned, already-downloaded R3877.30 build log')
    args=p.parse_args(argv)
    result=base()
    rc=2
    try:
        path=Path(args.log)
        require(path.is_file() and not path.is_symlink(), 'LOG_FILE_MISSING_OR_SYMLINK')
        with path.open('rb') as f:
            raw=f.read(r31.MAX_BYTES + 1)
        result['inventory']=analyze(raw)
        result['result']='PASS_PINNED_FIVE_EXTRA_OBJECT_PRINTED_CONTEXTS_ONLY'
        rc=0
    except r31.AuditHold as e:
        result['hold_category']=str(e)
    except (OSError, ValueError, UnicodeError, OverflowError):
        result['hold_category']='EXTRA_OBJECT_CONTEXT_PARSE_ERROR'
    print(json.dumps(result, indent=2, sort_keys=True))
    return rc

if __name__=='__main__':
    raise SystemExit(main())
