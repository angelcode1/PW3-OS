#!/usr/bin/env python3
"""R3877.33.1: accept long adjacent printed log lines as bounded evidence.

Research/education only. No host subprocess, shell evaluation, installation,
Docker, SSH, target access, or command/path disclosure. Do not infer executed
argv from any printed/logged candidate. All authenticated inputs remain the
user-reported hash-pinned public log and the fixed linker-line fingerprint.
"""
import argparse
import hashlib
import io
import json
import shlex
from pathlib import Path

import pw3_r3877_31_buildlog_audit as r31
import pw3_r3877_32_1_link_lexical_diagnostic as r321
import pw3_r3877_32_2_link_error_taxonomy as r322
import pw3_r3877_33_adjacent_line_triage as r33

MILESTONE = 'R3877.33.1'
OLD_MAX_ONE_LINE_CHARS = 15000
# The *entire original log* must fit r31.MAX_BYTES (2 MiB). This is an
# independent forensic sanity bound on each accepted printed neighbor.
MAX_EVIDENCE_LINE_CHARS = r31.MAX_BYTES
# Lexing is optional and size bounded; an oversized neighbor is still useful
# hash/length evidence, never a reason to read raw paths or execute anything.
MAX_LEX_JOIN_CHARS = 256 * 1024
MAX_TOKENS = 16384
MAX_ADJACENT_LINES = 5
MAX_SAFE_FLAGS = 32


def require(ok, reason):
    if not ok:
        raise r31.AuditHold(reason)


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def lex_candidate(text):
    """Lex synthetic joined text; never return untrusted tokens or filenames."""
    require(len(text) <= MAX_LEX_JOIN_CHARS, 'INTERNAL_LEX_BOUND_EXCEEDED')
    lex = shlex.shlex(io.StringIO(text), posix=True)
    lex.whitespace_split = True
    lex.commenters = ''
    driver = []
    flags = set()
    count = 0
    status = 'SHLEX_TOKENIZED_CANDIDATE_ONLY'
    while count < MAX_TOKENS:
        try:
            t = lex.get_token()
        except ValueError as err:
            status = r322.lexical_failure_kind(err)
            break
        if t == lex.eof:
            break
        count += 1
        if len(driver) < 14:
            driver.append(t)
        if r321.earlier.SAFE_FLAG.fullmatch(t):
            flags.add(t)
            require(len(flags) <= MAX_SAFE_FLAGS, 'TOO_MANY_ALLOWLISTED_FLAGS')
    else:
        # There may be more tokens; intentionally stop at the token budget.
        status = 'SHLEX_TOKEN_BUDGET_REACHED'
    return {
        'lexical_result': status,
        'lexical_token_count_bounded': count,
        'driver_class': r321._tool_class(driver),
        'allowlisted_flags_from_lexed_tokens': sorted(flags),
        'text_was_executed_or_evaluated': False,
        'complete_historical_shell_command_verified': False,
    }


def triage_neighbors(lines, *, start_line=r321.EXPECTED_LINK_LINE_NUMBER,
                     expected_link_sha256=r321.EXPECTED_LINK_LINE_SHA256):
    require(1 <= start_line < len(lines), 'PINNED_LINK_OR_FOLLOWING_LINE_MISSING')
    first = lines[start_line-1].strip()
    require(len(first) <= OLD_MAX_ONE_LINE_CHARS, 'PINNED_LINK_LINE_TOO_LONG')
    require(digest(first) == expected_link_sha256, 'PINNED_LINK_SHA256_CHANGED')
    require(r33.trailing_unpaired_backslash(first),
            'PINNED_LINK_NOT_UNPAIRED_BACKSLASH_TERMINATED')
    joined = first
    evidence = []
    stop = None
    for index in range(start_line, min(len(lines), start_line+MAX_ADJACENT_LINES)):
        if not r33.trailing_unpaired_backslash(joined):
            break
        neighbor = lines[index]
        require(len(neighbor) <= MAX_EVIDENCE_LINE_CHARS,
                'NEXT_LINE_EXCEEDS_FULL_PINNED_LOG_LIMIT')
        evidence.append({
            'line_number': index + 1,
            'printed_line_sha256': digest(neighbor),
            'character_count': len(neighbor),
            'exceeds_prior_15000_character_limit': len(neighbor) > OLD_MAX_ONE_LINE_CHARS,
            'begins_with_whitespace': neighbor[:1] in (' ', '\t'),
            'ends_with_unpaired_backslash': r33.trailing_unpaired_backslash(neighbor),
            'full_line_not_disclosed': True,
        })
        # No prefix-truncation ever enters the lexer: either join the complete
        # printed physical line, or refuse further joining and report metadata.
        if len(joined) - 1 + len(neighbor) > MAX_LEX_JOIN_CHARS:
            stop = 'PRINTED_NEIGHBOR_EXCEEDS_SAFE_LEX_BOUND'
            break
        joined = joined[:-1] + neighbor

    require(evidence, 'FOLLOWING_LINE_MISSING')
    if stop is None:
        summary = lex_candidate(joined)
    else:
        summary = {
            'lexical_result': 'NOT_LEXED_OVERSIZED_PRINTED_NEIGHBOR',
            'lexical_token_count_bounded': None,
            'driver_class': 'not_reanalyzed',
            'allowlisted_flags_from_lexed_tokens': [],
            'text_was_executed_or_evaluated': False,
            'complete_historical_shell_command_verified': False,
        }
    summary.update({
        'first_line_number': start_line,
        'first_line_sha256': expected_link_sha256,
        'following_line_evidence': evidence,
        'following_line_count_observed': len(evidence),
        'joined_physical_line_count_if_lexed': None if stop else len(evidence) + 1,
        'joined_text_sha256_if_lexed': None if stop else digest(joined),
        'joined_text_character_count_if_lexed': None if stop else len(joined),
        'bounded_lex_stop_reason': stop,
        'max_observed_following_line_character_count': max(x['character_count'] for x in evidence),
        'any_neighbor_exceeds_old_limit': any(x['exceeds_prior_15000_character_limit'] for x in evidence),
        'trailing_backslash_on_last_joined_line': r33.trailing_unpaired_backslash(joined),
        'adjacent_line_limit_reached': (stop is None and len(evidence) == MAX_ADJACENT_LINES
                                        and r33.trailing_unpaired_backslash(joined)),
        'printed_adjacency_does_not_verify_historical_shell_continuation': True,
        'printed_log_not_cryptographically_authenticated': True,
        'raw_command_lines_disclosed': False,
        'source_paths_disclosed': False,
        'untrusted_shell_substitutions_evaluated': False,
    })
    return summary


def analyze(raw, *, expected_hash=r31.EXPECTED_SHA256,
            expected_length=r31.EXPECTED_BYTES,
            expected_link_hash=r321.EXPECTED_LINK_LINE_SHA256,
            expected_link_number=r321.EXPECTED_LINK_LINE_NUMBER):
    # Recheck every previously established pin before using any neighbor.
    baseline = r322.analyze(raw, expected_hash=expected_hash,
                            expected_length=expected_length,
                            expected_link_hash=expected_link_hash,
                            expected_link_number=expected_link_number)
    require(baseline['error_kind'] == 'ESCAPE_AT_END_OF_PRINTED_LINE',
            'PRIOR_LEXICAL_ERROR_CHANGED')
    require(baseline['complete_prefix_tokens_before_error'] == 66,
            'PRIOR_PREFIX_TOKEN_COUNT_CHANGED')
    require(baseline['printed_line_ends_with_unpaired_backslash'],
            'PRIOR_LINK_BACKSLASH_CHANGED')
    require(baseline['link_line_sha256_verified'] and baseline['log_sha256_verified'],
            'PRIOR_LOG_PINS_NOT_VERIFIED')
    lines = r31.ANSI.sub('', raw.decode('utf-8', errors='replace')).splitlines()
    record = triage_neighbors(lines, start_line=expected_link_number,
                              expected_link_sha256=expected_link_hash)
    record.update({
        'log_sha256': hashlib.sha256(raw).hexdigest(),
        'log_bytes': len(raw),
        'prior_r3877_32_2_hash_pins_revalidated': True,
        'historical_builder_complete_link_invocation_verified': False,
        'historical_builder_cflags_ldflags_verified': False,
        'historical_builder_toolchain_versions_verified': False,
        'source_to_binary_reproducibility_verified': False,
    })
    return record


def base():
    result = r33.base()
    result.update(milestone=MILESTONE, result='HOLD',
                  hold_category='NOT_BOOTABLE', immutable_hold='NOT_BOOTABLE',
                  historical_builder_complete_link_invocation_verified=False,
                  historical_builder_compiler_and_linker_invocation_provenance_verified=False,
                  source_to_binary_reproducibility_verified=False,
                  binary_execution_performed=False, boot_performed=False,
                  firmware_write_performed=False, kindle_ssh_sessions=0,
                  new_kindle_binary_installed_or_executed=False,
                  physical_device_access_performed=False, recovery_verified=False)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', help='Existing Mac-local hash-pinned R3877.30 build log')
    args = parser.parse_args(argv)
    result = base()
    exit_code = 2
    try:
        path = Path(args.log)
        require(path.is_file() and not path.is_symlink(), 'LOG_FILE_MISSING_OR_SYMLINK')
        with path.open('rb') as stream:
            raw = stream.read(r31.MAX_BYTES+1)
        record = analyze(raw)
        result['inventory'] = record
        result['result'] = 'PASS_PINNED_LONG_NEIGHBOR_LOG_TRIAGE_ONLY'
        exit_code = 0
    except r31.AuditHold as exc:
        result['hold_category'] = str(exc)
    except (OSError, ValueError, UnicodeError, OverflowError):
        result['hold_category'] = 'LOG_ANALYSIS_ERROR'
    print(json.dumps(result, indent=2, sort_keys=True))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
