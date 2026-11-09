#!/usr/bin/env python3
"""R3877.27: host-only, memory-only fingerprint of pinned patched musl source.

Every input is first pinned by R3877.26.1. No source extraction, build,
ARM code execution, SSH session, Kindle write, or firmware interaction.
This tool does NOT prove reproducible output bytes from compiled source.
"""
import argparse
import hashlib
import io
import json
import pathlib
import re
import sys
import tarfile

import pw3_r3877_26_aports_input_audit as earlier

MAX_ENTRIES = earlier.MAX_MEMBERS + 16


def enforce(condition, code):
    if not condition:
        raise earlier.AuditHold(code)


def source_tree_manifest(archive, changed_blobs, *, max_archive=earlier.MAX_ARCHIVE):
    """Canonicalize all source tree entries + exactly the patched changes.

    Does not extract archives, follow symlinks, or write any file. A stable
    textual JSON serialization is hashed, not an on-disk tar or ext filesystem.
    """
    enforce(len(archive) < max_archive, 'SOURCE_ARCHIVE_TOO_LARGE')
    entries = {}
    total_bytes = 0
    created_file_count = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tf:
            members = tf.getmembers()
            enforce(len(members) <= earlier.MAX_MEMBERS,
                    'SOURCE_ARCHIVE_TOO_MANY_MEMBERS')
            for m in members:
                fullname = m.name.removeprefix('./').rstrip('/')
                enforce(earlier.valid_rel(fullname), 'SOURCE_UNSAFE_MEMBER_NAME')
                enforce(fullname == 'musl-1.2.6' or
                        fullname.startswith('musl-1.2.6/'),
                        'SOURCE_WRONG_ARCHIVE_PREFIX')
                enforce(fullname not in entries, 'SOURCE_DUPLICATE_MEMBER')
                enforce(m.isfile() or m.isdir() or m.issym(),
                        'SOURCE_UNSUPPORTED_MEMBER_TYPE')
                path = fullname[len('musl-1.2.6/'):]
                if fullname == 'musl-1.2.6':
                    enforce(m.isdir(), 'SOURCE_ROOT_NOT_DIRECTORY')
                    entries[fullname] = ['d']
                    continue
                if m.isfile():
                    enforce(0 <= m.size <= earlier.MAX_FILE,
                            'SOURCE_MEMBER_TOO_LARGE')
                    total_bytes += m.size
                    enforce(total_bytes <= earlier.MAX_UNPACKED,
                            'SOURCE_UNPACKED_TOO_LARGE')
                    b = tf.extractfile(m).read()
                    enforce(len(b) == m.size, 'SOURCE_MEMBER_SHORT_READ')
                    if path in changed_blobs:
                        b = changed_blobs[path]
                    entries[fullname] = ['f', len(b), hashlib.sha256(b).hexdigest(), m.mode & 0o777]
                elif m.isdir():
                    enforce(path not in changed_blobs, 'PATCH_REPLACED_NONFILE')
                    entries[fullname] = ['d', m.mode & 0o777]
                else:
                    enforce(path not in changed_blobs, 'PATCH_REPLACED_SYMLINK')
                    enforce(len(m.linkname) <= 1024 and '\x00' not in m.linkname,
                            'SOURCE_BAD_SYMLINK_TARGET')
                    entries[fullname] = ['l', m.linkname, m.mode & 0o777]
        for path, content in changed_blobs.items():
            full = 'musl-1.2.6/' + path
            enforce(earlier.valid_rel(path), 'PATCH_UNSAFE_TARGET')
            if full not in entries:
                # The prior patch parser must have explicitly created the file.
                entries[full] = ['f', len(content), hashlib.sha256(content).hexdigest(), 0o644]
                created_file_count += 1
            else:
                enforce(entries[full][0] == 'f', 'PATCH_NONFILE_TARGET')
        enforce(len(entries) <= MAX_ENTRIES, 'SOURCE_TOO_MANY_CANONICAL_ENTRIES')
    except (tarfile.TarError, EOFError, OSError) as e:
        raise earlier.AuditHold('SOURCE_TARBALL_PARSE_ERROR') from e
    canonical = [[name, *entries[name]] for name in sorted(entries)]
    canonical_bytes = (json.dumps(canonical, ensure_ascii=True,
                                  separators=(',', ':'), sort_keys=False) + '\n').encode('utf-8')
    return {
        'canonical_patched_source_tree_sha256': hashlib.sha256(canonical_bytes).hexdigest(),
        'canonical_format': 'UTF8_JSON_SORTED_PATH_ENTRIES_V1',
        'entries_hashed': len(entries),
        'regular_files': sum(v[0]=='f' for v in entries.values()),
        'directories': sum(v[0]=='d' for v in entries.values()),
        'symlinks_not_followed': sum(v[0]=='l' for v in entries.values()),
        'source_member_bytes_hashed': total_bytes,
        'new_patch_created_file_count': created_file_count,
    }


def reconstruct_changed_blobs(archive, patch_inputs):
    diffs=[(name, earlier.parse_patch(raw)) for name,raw in patch_inputs]
    old_files = {path for _, chunks in diffs for path, create, _ in chunks if not create}
    src, count=earlier.tar_source_files(archive, old_files)
    targets=set()
    hunk_records=[]
    for name, chunks in diffs:
        targets.update(earlier.apply_patch_chunks(chunks, src, hunk_audit=hunk_records, patch_name=name))
    return {x:src[x] for x in sorted(targets)},count,hunk_records


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir',required=True)
    p.add_argument('--manifest', default=str(pathlib.Path(__file__).with_name(earlier.MANIFEST_NAME)))
    p.add_argument('--expected-patched',default=str(pathlib.Path(__file__).with_name('R3877_27_EXPECTED_PATCHED_SHA256.json')))
    args=p.parse_args(argv)
    out={'milestone':'R3877.27','result':'HOLD', 'hold_category':'INPUTS_NOT_VERIFIED',
         'immutable_hold':'NOT_BOOTABLE','kindle_ssh_sessions':0,'physical_device_access_performed':False,
         'firmware_write_performed':False,'new_kindle_binary_installed_or_executed':False,
         'boot_performed':False,'original_r13_stage_accessed':False,'recovery_verified':False,
         'patched_source_to_binary_reproducibility_verified':False,
         'signed_loader_rebuild_performed':False, 'target_musl_runtime_verified':False,
         'source_tree_fingerprint_verified':False}
    status=2
    try:
        manifest=earlier.load_manifest(pathlib.Path(args.manifest))
        raw,_=earlier.check_inputs(pathlib.Path(args.source_dir),manifest)
        pin=json.loads(pathlib.Path(args.expected_patched).read_text('utf-8'))
        earlier.ensure(pin.get('milestone')=='R3877.27' and pin.get('source_git_snapshot')==manifest['aports_commit'], 'EXPECTED_PATCHED_HEADER_MISMATCH')
        expected=pin['expected']
        earlier.ensure(isinstance(expected,dict) and len(expected)==7 and
                      all(earlier.valid_rel(p) and re.fullmatch(r'[a-f0-9]{64}',v) for p,v in expected.items()),
                      'EXPECTED_PATCHED_FORMAT_INVALID')
        patch_inputs=[(e['name'],raw[e['name']]) for e in manifest['entries'] if e['role']=='patch']
        changed,pre_members,hunks = reconstruct_changed_blobs(raw[manifest['source_tarball']],patch_inputs)
        got={p:hashlib.sha256(b).hexdigest() for p,b in changed.items()}
        earlier.ensure(got==expected,'PATCHED_FILE_SHA256_BASELINE_MISMATCH')
        tree=source_tree_manifest(raw[manifest['source_tarball']],changed)
        out['inventory']={
            'pinned_aports_snapshot':manifest['aports_commit'],
            'upstream_tar_sha512_verified':True,
            'aports_patches_sha512_verified':True,
            'patch_target_baseline_sha256_match':True,
            'patch_changed_file_count':len(changed),
            'patch_hunk_count':len(hunks),
            'original_tar_members_checked':pre_members,
            **tree,
            'build_toolchain_pinned':False,
            'alpine_build_environment_equivalence_verified':False,
            'binary_reproducibility_verified':False,
        }
        out.update(result='PASS_PINNED_PATCHED_SOURCE_TREE_FINGERPRINT_ONLY', hold_category='NOT_BOOTABLE',source_tree_fingerprint_verified=True)
        status=0
    except (earlier.AuditHold,ValueError,KeyError,UnicodeError,TypeError,OSError,MemoryError) as e:
        out['hold_category']=(str(e) if isinstance(e,earlier.AuditHold) else 'HOST_AUDIT_INPUT_OR_PARSE_ERROR')[:140]
    print(json.dumps(out,indent=2,sort_keys=True))
    return status

if __name__ == '__main__':
    sys.exit(main())
