#!/usr/bin/env python3
"""R3877.33: static triage of a printed, backslash-ended public log line.

For research/educational use only. No shell evaluation, substitution,
execution, Docker, SSH, firmware/device writes, or raw command disclosure.
Joining printed neighboring lines is a lexical experiment, NOT evidence of
how the historical shell or build worker executed the link invocation.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shlex

import pw3_r3877_31_buildlog_audit as r31
import pw3_r3877_32_1_link_lexical_diagnostic as r321
import pw3_r3877_32_2_link_error_taxonomy as r322

MILESTONE = 'R3877.33'
MAX_ADJACENT_LINES = 5
MAX_JOIN_CHARS = 80000
MAX_ONE_LINE_CHARS = 15000
MAX_TOKENS = 4096
MAX_FLAGS = 32


def require(value, hold):
    if not value:
        raise r31.AuditHold(hold)


def trailing_unpaired_backslash(s):
    return (len(s) - len(s.rstrip('\\'))) % 2 == 1


def lex_only(s):
    """Return bounded, sanitized statistics. Never return shell argv tokens."""
    require(len(s) <= MAX_JOIN_CHARS, 'JOINED_LINE_TOO_LONG')
    lexer = shlex.shlex(io.StringIO(s), posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ''
    toks = []
    failure = None
    for _ in range(MAX_TOKENS + 1):
        try:
            token = lexer.get_token()
        except ValueError as exc:
            failure = r322.lexical_failure_kind(exc)
            break
        if token == lexer.eof:
            break
        toks.append(token)
    else:
        raise r31.AuditHold('JOINED_TOO_MANY_TOKENS')
    flags = sorted({x for x in toks if r321.earlier.SAFE_FLAG.fullmatch(x)})
    require(len(flags) <= MAX_FLAGS, 'JOINED_TOO_MANY_SAFE_FLAGS')
    return {
        'lexical_result': failure or 'SHLEX_TOKENIZED_ONLY',
        'shlex_token_count': len(toks),
        'driver_class': r321._tool_class(toks),
        'allowlisted_flags': flags,
        'text_was_executed_or_evaluated': False,
        'complete_historical_shell_command_verified': False,
    }


def triage_neighbors(lines, *, start_line=r321.EXPECTED_LINK_LINE_NUMBER,
                     expected_link_sha256=r321.EXPECTED_LINK_LINE_SHA256):
    require(1 <= start_line <= len(lines), 'PINNED_LINK_LINE_MISSING')
    first = lines[start_line - 1].strip()
    require(len(first) <= MAX_ONE_LINE_CHARS, 'PINNED_LINE_TOO_LONG')
    require(hashlib.sha256(first.encode()).hexdigest() == expected_link_sha256,
            'PINNED_LINK_SHA256_CHANGED')
    require(trailing_unpaired_backslash(first), 'PINNED_LINK_LINE_NOT_BACKSLASH_TERMINATED')
    require(start_line < len(lines), 'FOLLOWING_LINE_MISSING')
    sample = first
    neighbor_evidence = []
    for idx in range(start_line, min(len(lines), start_line+MAX_ADJACENT_LINES)):
        if not trailing_unpaired_backslash(sample):
            break
        nextline = lines[idx]  # preserve indentation; never execute or interpolate
        require(len(nextline) <= MAX_ONE_LINE_CHARS, 'NEXT_LINE_TOO_LONG')
        neighbor_evidence.append({
            'line_number': idx+1,
            'printed_line_sha256': hashlib.sha256(nextline.encode()).hexdigest(),
            'character_count': len(nextline),
            'ends_with_unpaired_backslash': trailing_unpaired_backslash(nextline),
        })
        # Shell's backslash-newline transformation as a *hypothetical* lexical
        # interpretation of two printed log lines. It is NOT executed.
        sample = sample[:-1] + nextline
        require(len(sample) <= MAX_JOIN_CHARS, 'JOINED_LINE_TOO_LONG')
    report = lex_only(sample)
    require(neighbor_evidence, 'FOLLOWING_LINE_MISSING')
    report.update({
        'first_line_number': start_line,
        'first_line_sha256': expected_link_sha256,
        'joined_physical_line_count': 1 + len(neighbor_evidence),
        'following_line_evidence': neighbor_evidence,
        'joined_text_sha256': hashlib.sha256(sample.encode()).hexdigest(),
        'joined_text_character_count': len(sample),
        'still_ends_with_unpaired_backslash': trailing_unpaired_backslash(sample),
        'line_limit_reached': len(neighbor_evidence) == MAX_ADJACENT_LINES and trailing_unpaired_backslash(sample),
        'next_line_is_not_authenticated_as_historical_shell_continuation': True,
        'printed_lines_cannot_prove_historical_builder_argv': True,
        'raw_command_lines_disclosed': False,
        'input_paths_disclosed': False,
        'untrusted_shell_substitutions_evaluated': False,
    })
    return report


def analyze(raw, *, expected_hash=r31.EXPECTED_SHA256,
            expected_length=r31.EXPECTED_BYTES,
            expected_link_hash=r321.EXPECTED_LINK_LINE_SHA256,
            expected_link_number=r321.EXPECTED_LINK_LINE_NUMBER):
    baseline = r322.analyze(raw, expected_hash=expected_hash,
                            expected_length=expected_length,
                            expected_link_hash=expected_link_hash,
                            expected_link_number=expected_link_number)
    require(baseline['error_kind'] == 'ESCAPE_AT_END_OF_PRINTED_LINE',
            'PRIOR_LEXER_ERROR_CHANGED')
    require(baseline['complete_prefix_tokens_before_error'] == 66,
            'PRIOR_LINK_PREFIX_COUNT_CHANGED')
    require(baseline['printed_line_ends_with_unpaired_backslash'],
            'PRIOR_LINK_ESCAPE_STATE_CHANGED')
    require(baseline['link_line_sha256_verified'] and baseline['log_sha256_verified'],
            'PRIOR_LOG_IDENTITY_UNVERIFIED')
    lines = r31.ANSI.sub('', raw.decode('utf-8', errors='replace')).splitlines()
    report = triage_neighbors(lines, start_line=expected_link_number,
                              expected_link_sha256=expected_link_hash)
    report.update({
        'log_sha256': hashlib.sha256(raw).hexdigest(),
        'log_bytes': len(raw),
        'hash_pins_and_prior_classifications_rechecked': True,
        'historical_builder_toolchain_versions_verified': False,
        'historical_builder_cflags_ldflags_verified': False,
        'historical_builder_complete_link_invocation_verified': False,
        'public_build_log_signature_verified': False,
        'source_to_binary_reproducibility_verified': False,
    })
    return report


def base():
    d = r322.base()
    d.update(milestone=MILESTONE, result='HOLD', hold_category='NOT_BOOTABLE',
             immutable_hold='NOT_BOOTABLE', binary_execution_performed=False,
             firmware_write_performed=False, new_kindle_binary_installed_or_executed=False,
             kindle_ssh_sessions=0, physical_device_access_performed=False,
             recovery_verified=False, source_to_binary_reproducibility_verified=False,
             historical_builder_complete_link_invocation_verified=False)
    return d


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('log', help='Previously downloaded R3877.30 public log on the Mac')
    opts = p.parse_args(argv)
    result = base()
    rc = 2
    try:
        path = Path(opts.log)
        require(path.is_file() and not path.is_symlink(), 'LOG_FILE_MISSING_OR_SYMLINK')
        with path.open('rb') as fp:
            raw = fp.read(r31.MAX_BYTES + 1)
        result['inventory'] = analyze(raw)
        result['result'] = 'PASS_PINNED_ADJACENT_LOG_LINE_LEXICAL_TRIAGE_ONLY'
        rc = 0
    except r31.AuditHold as exc:
        result['hold_category'] = str(exc)
    except (OSError, ValueError, OverflowError, UnicodeError):
        result['hold_category'] = 'LOG_ANALYSIS_ERROR'
    print(json.dumps(result, indent=2, sort_keys=True))
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
