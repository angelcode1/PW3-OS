#!/usr/bin/env python3
"""R3877.34: exact-hash, two-line *printed candidate* structural inventory.

No guest/device/host binary is executed. Never expands a shell expression, runs
subprocesses, returns the source paths/output names or emits untrusted tokens.
shlex is ONLY a lexical approximation, not a shell interpreter or an attestation
of executed argv. The historical builder/toolchain remain unverified.
"""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import shlex

import pw3_r3877_31_buildlog_audit as r31
import pw3_r3877_32_1_link_lexical_diagnostic as r321
import pw3_r3877_33_1_long_neighbor_triage as r331

MILESTONE = 'R3877.34'
PINNED_SECOND_SHA256 = '9ba3880bd7bbe7ae8431f51e735ceae7649e443ece10361a7cd0e48ff2186fb3'
PINNED_JOINED_SHA256 = '5bfd03a5a13d402b69eab716bd4374a2ee25c90496e6fc362284041489b3e9f0'
PINNED_JOINED_CHARS = 40671
PINNED_LEX_TOKENS = 1494
MAX_TOKENS = 16384
MAX_REPORT_KEYS = 24
KNOWN_SAFE_FLAGS = {
    '-O2', '-O3', '-fPIC', '-fno-asynchronous-unwind-tables',
    '-nostdlib', '-shared', '-Wl,--hash-style=both',
    '-Wl,-soname,libc.musl-armv7.so.1',
}


def require(ok, code):
    if not ok:
        raise r31.AuditHold(code)


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def tokenize_no_execution(text):
    """Bounded Python shlex; not a representation of executed shell argv."""
    require(0 < len(text) <= r331.MAX_LEX_JOIN_CHARS, 'JOINED_TEXT_LIMIT')
    lex = shlex.shlex(io.StringIO(text), posix=True)
    lex.whitespace_split = True
    lex.commenters = ''
    tokens = []
    for _ in range(MAX_TOKENS + 1):
        try:
            t = lex.get_token()
        except ValueError:
            raise r31.AuditHold('JOINED_SHLEX_NOT_COMPLETE') from None
        if t == lex.eof:
            return tokens
        tokens.append(t)
    raise r31.AuditHold('JOINED_TOKEN_BUDGET_REACHED')


def count_structure(tokens):
    """Only aggregate classes. Do not return tokens or file names."""
    require(isinstance(tokens, list) and 0 < len(tokens) <= MAX_TOKENS,
            'INVALID_TOKEN_SEQUENCE')
    require(all(isinstance(t, str) and len(t) <= 16384 for t in tokens),
            'TOKEN_SIZE_OR_TYPE_INVALID')
    cls = Counter()
    output_switch_positions = []
    output_attached_positions = []
    shell_metachar = 0
    shell_expansion_markers = 0
    permitted = set()
    for i, token in enumerate(tokens):
        if token in KNOWN_SAFE_FLAGS:
            permitted.add(token)
        if token == '-o':
            output_switch_positions.append(i)
        elif token.startswith('-o') and len(token) > 2 and not token.startswith('-opt'):
            # '-o<path>' is a possible output switch but cannot be inferred
            # from arbitrary -options; label potential, not proven.
            output_attached_positions.append(i)
        if token in (';', '|', '||', '&&', '<', '>', '>>', '&'):
            shell_metachar += 1
        if any(seq in token for seq in ('$(', '${', '`', '$[')):
            shell_expansion_markers += 1
        if token.endswith('.o') or token.endswith('.lo'):
            cls['object_like'] += 1
        elif token.endswith('.a'):
            cls['static_archive_like'] += 1
        elif token.endswith('.so') or '.so.' in token:
            cls['shared_library_like'] += 1
        elif token.startswith('-l') and len(token) > 2:
            cls['link_by_name_options'] += 1
        elif token.startswith('-L') and len(token) > 2:
            cls['library_search_options'] += 1
        elif token.startswith('-Wl,'):
            cls['linker_pass_through_options'] += 1
        elif token in ('-shared', '-nostdlib'):
            cls['link_mode_options'] += 1
        elif token.startswith('-'):
            cls['other_dash_prefixed_tokens'] += 1
        elif '/' in token:
            cls['other_path_like'] += 1
        else:
            cls['other_tokens'] += 1
    # Check only shape of output placement; never emit the output path.
    output_next_present = [i + 1 < len(tokens) and not tokens[i+1].startswith('-')
                           for i in output_switch_positions]
    categories = {k: cls[k] for k in sorted(cls)}
    require(len(categories) <= MAX_REPORT_KEYS, 'TOO_MANY_CATEGORIES')
    return {
        'lexically_recognized_candidate_token_count': len(tokens),
        'token_classes': categories,
        'explicit_output_switch_count': len(output_switch_positions),
        'explicit_output_switches_have_following_non_option': all(output_next_present),
        'possible_attached_output_option_count_unverified': len(output_attached_positions),
        'printed_shell_metacharacter_token_count': shell_metachar,
        'printed_shell_expansion_marker_token_count': shell_expansion_markers,
        'allowlisted_flags': sorted(permitted),
        'input_file_paths_or_basenames_disclosed': False,
        'output_file_paths_or_basenames_disclosed': False,
        'raw_command_or_tokens_disclosed': False,
        'shell_expressions_evaluated': False,
        'printed_candidate_not_historical_argv_proof': True,
    }


def analyze(raw, *, expected_hash=r31.EXPECTED_SHA256,
            expected_length=r31.EXPECTED_BYTES,
            link_line_number=r321.EXPECTED_LINK_LINE_NUMBER,
            link_line_hash=r321.EXPECTED_LINK_LINE_SHA256,
            next_line_hash=PINNED_SECOND_SHA256,
            joined_hash=PINNED_JOINED_SHA256,
            joined_chars=PINNED_JOINED_CHARS,
            expected_tokens=PINNED_LEX_TOKENS):
    prior = r331.analyze(raw, expected_hash=expected_hash,
                         expected_length=expected_length,
                         expected_link_hash=link_line_hash,
                         expected_link_number=link_line_number)
    require(prior['lexical_result'] == 'SHLEX_TOKENIZED_CANDIDATE_ONLY',
            'PRIOR_JOINED_LINE_NOT_TOKENIZED')
    require(prior['following_line_count_observed'] == 1,
            'PRIOR_NEIGHBOR_COUNT_CHANGED')
    require(prior['following_line_evidence'][0]['printed_line_sha256'] == next_line_hash,
            'NEXT_LINE_SHA256_CHANGED')
    require(prior['joined_text_sha256_if_lexed'] == joined_hash,
            'JOINED_TEXT_SHA256_CHANGED')
    require(prior['joined_text_character_count_if_lexed'] == joined_chars,
            'JOINED_TEXT_CHARACTER_COUNT_CHANGED')
    require(prior['lexical_token_count_bounded'] == expected_tokens,
            'PRIOR_JOINED_TOKEN_COUNT_CHANGED')
    require(prior['driver_class'] == 'cc', 'PRIOR_PRINTED_DRIVER_CHANGED')
    lines = r31.ANSI.sub('', raw.decode('utf-8', errors='replace')).splitlines()
    require(1 <= link_line_number < len(lines), 'PINNED_LINES_NOT_AVAILABLE')
    first = lines[link_line_number - 1].strip()
    second = lines[link_line_number]
    require(sha(first) == link_line_hash, 'FIRST_LINK_LINE_HASH_CHANGED')
    require(sha(second) == next_line_hash, 'SECOND_LINK_LINE_HASH_CHANGED')
    require(r331.r33.trailing_unpaired_backslash(first), 'FIRST_LINK_ESCAPE_MISSING')
    joined = first[:-1] + second
    require(sha(joined) == joined_hash, 'JOINED_HASH_CHANGED')
    require(len(joined) == joined_chars, 'JOINED_LENGTH_CHANGED')
    require(not r331.r33.trailing_unpaired_backslash(joined), 'JOINED_CONTINUATION_UNRESOLVED')
    tokens = tokenize_no_execution(joined)
    require(len(tokens) == expected_tokens, 'FULL_CANDIDATE_TOKEN_COUNT_CHANGED')
    require(r321._tool_class(tokens[:14]) == 'cc', 'CANDIDATE_DRIVER_CHANGED')
    counters = count_structure(tokens)
    # Explicitly retain all provenance and safety holds, even with good shape.
    return {
        'log_bytes': len(raw),
        'log_sha256': hashlib.sha256(raw).hexdigest(),
        'first_printed_line_number': link_line_number,
        'second_printed_line_number': link_line_number+1,
        'first_line_sha256': link_line_hash,
        'second_line_sha256': next_line_hash,
        'joined_text_sha256': joined_hash,
        'joined_text_character_count': joined_chars,
        'joined_physical_lines': 2,
        'driver_class': 'cc',
        **counters,
        'historical_builder_complete_link_invocation_verified': False,
        'historical_builder_cflags_ldflags_verified': False,
        'historical_builder_toolchain_versions_verified': False,
        'public_build_log_signature_verified': False,
        'source_to_binary_reproducibility_verified': False,
        'kindle_ssh_sessions': 0,
    }


def base():
    return {
        'milestone': MILESTONE,
        'result': 'HOLD',
        'hold_category': 'NOT_BOOTABLE',
        'immutable_hold': 'NOT_BOOTABLE',
        'kindle_ssh_sessions': 0,
        'binary_execution_performed': False,
        'boot_performed': False,
        'firmware_write_performed': False,
        'new_kindle_binary_installed_or_executed': False,
        'physical_device_access_performed': False,
        'historical_builder_machine_identity_verified': False,
        'historical_builder_compiler_and_linker_invocation_provenance_verified': False,
        'historical_builder_complete_link_invocation_verified': False,
        'historical_builder_cflags_ldflags_verified': False,
        'historical_builder_toolchain_versions_verified': False,
        'source_to_binary_reproducibility_verified': False,
        'target_musl_runtime_verified': False,
        'public_build_log_signature_verified': False,
        'recovery_verified': False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('log', help='Existing hash-pinned R3877.30 musl build log on the Mac')
    a = p.parse_args(argv)
    result = base()
    code = 2
    try:
        path = Path(a.log)
        require(path.is_file() and not path.is_symlink(), 'LOG_FILE_MISSING_OR_SYMLINK')
        with path.open('rb') as f:
            raw = f.read(r31.MAX_BYTES + 1)
        result['inventory'] = analyze(raw)
        result['result'] = 'PASS_PINNED_TWO_LINE_LINK_CANDIDATE_STRUCTURE_ONLY'
        code = 0
    except r31.AuditHold as e:
        result['hold_category'] = str(e)
    except (OSError, ValueError, UnicodeError, OverflowError):
        result['hold_category'] = 'LOG_STRUCTURE_ANALYSIS_ERROR'
    print(json.dumps(result, sort_keys=True, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
