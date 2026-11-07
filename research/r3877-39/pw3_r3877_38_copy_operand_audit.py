#!/usr/bin/env python3
"""R3877.38: classify exact, printed cp operand roles of five auxiliary objects.

Read-only host static analysis; no source names, paths, commands, invocation or
object-derived fingerprints disclosed. This is NOT historical execution proof.
All boot/deployment/Kindle actions remain prohibited: NOT_BOOTABLE.
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

MILESTONE = 'R3877.38'
EXPECTED_ORPHANS = 5
EXPECTED_COPY_LINES = 5
# Safe subset only. Unknown options -> unresolved, never guessed.
NO_VALUE_SHORT = set('aAbdfiHlnpPRrsTuvx')
NO_VALUE_LONG = {
    '--archive', '--attributes-only', '--backup', '--copy-contents', '--dereference',
    '--force', '--interactive', '--link', '--no-clobber', '--no-dereference',
    '--no-preserve', '--one-file-system', '--parents', '--preserve',
    '--recursive', '--remove-destination', '--sparse', '--strip-trailing-slashes',
    '--symbolic-link', '--update', '--verbose', '--no-target-directory',
}
# Intentionally exclude -t, --target-directory, -S, --suffix and other value-taking
# options; never misidentify their arguments as operands.


def require(condition, reason):
    if not condition:
        raise r31.AuditHold(reason)


def cp_operands(words):
    """Return (mode, private operands) only if a conservative cp syntax matches.

    Not a cp interpreter. Does not check filesystem, perform expansion or I/O.
    A successful result means only *printed tokens* resemble supported cp argv.
    """
    require(isinstance(words, list) and len(words) <= 10000, 'COPY_TOKEN_BUDGET')
    if r37.family(words) != 'copy':
        return 'not_copy', []
    if len(words) < 3:
        return 'insufficient_operands', []
    positional = []
    post_dash = False
    options_seen = set()
    for token in words[1:]:
        if not isinstance(token, str) or not token or len(token) > 16384:
            return 'unsupported_token', []
        if not post_dash and token == '--':
            post_dash = True
            continue
        if not post_dash and token.startswith('--'):
            if token in NO_VALUE_LONG:
                options_seen.add(token)
                continue
            return 'option_unresolved', []
        if not post_dash and token.startswith('-'):
            if token == '-':
                positional.append(token)
                continue
            if token.startswith('-') and all(c in NO_VALUE_SHORT for c in token[1:]):
                options_seen.update(token[1:])
                continue
            return 'option_unresolved', []
        # Never expand/unescape more than existing bounded shlex already did.
        positional.append(token)
    if len(positional) < 2:
        return 'insufficient_operands', []
    # -T/--no-target-directory require exactly one SOURCE and one DEST operand.
    if ('T' in options_seen or '--no-target-directory' in options_seen) and len(positional) != 2:
        return 'no_target_directory_arity_unresolved', []
    # Reject shell-looking strings as executable-command evidence. Preserves data
    # privacy while refusing to assign roles to suspicious printed tokens.
    if any(any(mark in t for mark in ('$(','${','`','$[','\x00')) for t in positional):
        return 'expansion_or_invalid_operand_unresolved', []
    return 'supported_cp_positional_shape', positional


def classify_copy_mentions(lines, orphans, compile_lines):
    """Compare exact private words; return aggregate counts with no path leakage."""
    require(len(lines) <= 3000, 'NONMAIN_LINE_BUDGET')
    require(len(orphans) == EXPECTED_ORPHANS and len(set(orphans)) == EXPECTED_ORPHANS,
            'FIVE_DISTINCT_UNLINKED_OBJECTS_REQUIRED')
    orphan_set = set(orphans)
    mention_classes = Counter()
    context_counts = Counter()
    source_seen = set()
    target_seen = set()
    any_seen = set()
    targets = []  # private, do not disclose
    copy_lines = 0
    scanned = 0
    unparsed = 0
    exact_occurrences = 0
    for lineno, line in enumerate(lines, 1):
        if lineno in compile_lines or lineno in (1666, 1667):
            continue
        scanned += 1
        if not line.strip():
            continue
        if len(line) > r34.r331.MAX_LEX_JOIN_CHARS:
            unparsed += 1
            continue
        try:
            words = r34.tokenize_no_execution(line.strip())
        except r31.AuditHold:
            unparsed += 1
            continue
        require(len(words) <= 10000, 'NONMAIN_TOKEN_BUDGET')
        matches = [token for token in words if token in orphan_set]
        if not matches:
            continue
        require(r37.family(words) == 'copy', 'NONCOPY_ORPHAN_MENTION_CHANGED')
        copy_lines += 1
        exact_occurrences += len(matches)
        any_seen.update(matches)
        mode, operands = cp_operands(words)
        context_counts[mode] += 1
        for obj in matches:
            if mode != 'supported_cp_positional_shape':
                mention_classes['role_unresolved'] += 1
                continue
            sources = operands[:-1]
            dest = operands[-1]
            if obj in sources:
                mention_classes['source_operand_candidate'] += 1
                source_seen.add(obj)
            elif obj == dest:
                mention_classes['destination_operand_candidate'] += 1
                target_seen.add(obj)
            else:
                mention_classes['option_or_unresolved_operand'] += 1
        if mode == 'supported_cp_positional_shape':
            targets.append(operands[-1])
    require(scanned == r37.EXPECTED_SCANNED, 'PRINTED_NONMAIN_SCANNED_LINES_CHANGED')
    require(unparsed == r37.EXPECTED_UNPARSED, 'PRINTED_NONMAIN_UNPARSED_LINES_CHANGED')
    require(copy_lines == EXPECTED_COPY_LINES, 'PRINTED_COPY_MENTION_LINE_COUNT_CHANGED')
    require(exact_occurrences == EXPECTED_ORPHANS, 'PRINTED_COPY_MENTION_COUNT_CHANGED')
    require(len(any_seen) == EXPECTED_ORPHANS, 'NOT_ALL_FIVE_COPY_MENTIONS_PRESENT')
    return {
        'nonmain_lines_scanned': scanned,
        'nonmain_lines_not_lexically_parsed': unparsed,
        'copy_command_lines_with_exact_orphan_mentions': copy_lines,
        'exact_copy_object_token_mentions': exact_occurrences,
        'distinct_extra_objects_mentioned_by_copy': len(any_seen),
        'printed_cp_syntax_classes': dict(sorted(context_counts.items())),
        'printed_cp_operand_role_candidates': dict(sorted(mention_classes.items())),
        'extra_objects_in_source_operand_position': len(source_seen),
        'extra_objects_in_destination_operand_position': len(target_seen),
        'distinct_printed_destination_texts_for_supported_copy_shapes': len(set(targets)),
        'unparsed_line_may_contain_additional_mentions': bool(unparsed),
        'paths_basenames_destinations_and_command_tokens_disclosed': False,
        'printed_cp_argv_and_filesystem_effects_verified': False,
        'cp_command_interpreter_or_shell_executed': False,
    }


def analyze(raw, *, expected_hash=r31.EXPECTED_SHA256,
            expected_length=r31.EXPECTED_BYTES):
    baseline = r37.analyze(raw, expected_hash=expected_hash,
                           expected_length=expected_length)
    require(baseline['printed_command_family_mention_counts'] == {'copy':5},
            'R3877_37_COPY_CONTEXT_CHANGED')
    require(baseline['printed_argument_position_candidate_counts'] ==
            {'earlier_argument_candidate':5}, 'R3877_37_ARGUMENT_POSITIONS_CHANGED')
    require(baseline['extra_objects_with_any_exact_printed_mention']==5,
            'R3877_37_FIVE_OBJECTS_CHANGED')
    lines, records = r36.extract_records(raw)
    link_tokens = r35.link_tokens_from_pinned(raw)
    orphan, _ = r36.reconcile_records(records, link_tokens)
    extra = classify_copy_mentions(lines, [r['output'] for r in orphan],
                                   {r['line_number'] for r in records})
    return {
        'log_sha256': hashlib.sha256(raw).hexdigest(),
        'log_bytes': len(raw),
        'joined_link_candidate_sha256': r34.PINNED_JOINED_SHA256,
        'compile_output_count': 1428,
        'main_link_exact_match_count': 1423,
        'unlinked_compile_output_count': 5,
        'prior_r3877_37_pins_and_counts_reverified': True,
        **extra,
        'historical_builder_complete_link_invocation_verified': False,
        'historical_builder_compiler_and_linker_invocation_provenance_verified': False,
        'historical_builder_machine_identity_verified': False,
        'historical_builder_toolchain_versions_verified': False,
        'historical_builder_cflags_ldflags_verified': False,
        'printed_build_log_signature_verified': False,
        'source_to_binary_reproducibility_verified': False,
        'target_musl_runtime_verified': False,
        'kindle_ssh_sessions': 0,
        'binary_execution_performed': False,
    }


def base():
    result = r37.base()
    result.update(milestone=MILESTONE, result='HOLD', hold_category='NOT_BOOTABLE',
                  historical_builder_complete_link_invocation_verified=False,
                  source_to_binary_reproducibility_verified=False,
                  binary_execution_performed=False)
    return result


def main(argv=None):
    argp = argparse.ArgumentParser(description=__doc__)
    argp.add_argument('log', help='Previously downloaded SHA256-pinned log')
    args = argp.parse_args(argv)
    result = base()
    rc = 2
    try:
        path = Path(args.log)
        require(path.is_file() and not path.is_symlink(), 'LOG_FILE_MISSING_OR_SYMLINK')
        with path.open('rb') as f:
            raw = f.read(r31.MAX_BYTES + 1)
        result['inventory'] = analyze(raw)
        result['result'] = 'PASS_PINNED_FIVE_EXTRA_OBJECT_COPY_ARGUMENT_STRUCTURE_ONLY'
        rc = 0
    except r31.AuditHold as exc:
        result['hold_category'] = str(exc)
    except (OSError, UnicodeError, ValueError, OverflowError):
        result['hold_category'] = 'COPY_ARGUMENT_STATIC_TRIAGE_ERROR'
    print(json.dumps(result, sort_keys=True, indent=2))
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
