#!/usr/bin/env python3
"""R3745.1: sanitized, read-only exception-site diagnostics for original R3745.

Does NOT fix/mask the original historical HOLD or execute any staged ELF.
Only fixed source-code identifiers, source line numbers and exception classes
are emitted, never paths, symbols, addresses, stage contents or exceptions.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ORIGINAL='R4043745-WEAK-PLT-INITIAL-TARGET-READONLY.py'
ORIGINAL_SHA256='c3b95955df80e896196887fe922acd253d26948728939f1ea8349782feb73794'
ALLOWED_CODE_FILES={
    'R4043726-INTERP-GUEST-RESOLVE-READONLY.py':'R3726',
    'R4043727-INTERP-ABSENT-ALTERNATIVES-READONLY.py':'R3727',
    'R4043733-INTERP-LAYOUT-READONLY.py':'R3733',
    'R4043734-FUTURE-MAPPING-SIMULATION-READONLY.py':'R3734',
    'R4043735-PT-LOAD-PREFLIGHT-READONLY.py':'R3735',
    'R4043736-DYNAMIC-RELOCATION-READONLY.py':'R3736',
    'R4043737-ARM-RELOCATION-SYMBOL-READONLY.py':'R3737',
    'R4043738-NEEDED-LIBRARY-CANDIDATES-READONLY.py':'R3738',
    'R4043739-NEEDED-TRANSITIVE-SONAME-READONLY.py':'R3739',
    'R4043740-SYMBOL-NAME-VERSION-READONLY.py':'R3740',
    'R4043741-GNU-SYMBOL-VERSION-CANDIDATES-READONLY.py':'R3741',
    'R4043741-1-LOCAL-VERSION-REVIEW-READONLY.py':'R3741.1',
    'R4043742-UNRESOLVED-WEAK-RELOCATION-READONLY.py':'R3742',
    'R4043743-STAGED-ELF-WEAK-EXPORT-SURVEY-READONLY.py':'R3743',
    'R4043743-1-OVERLAP-AWARE-EXPORT-SURVEY-READONLY.py':'R3743.1',
    'R4043744-WEAK-RELOCATION-SLOT-PREFLIGHT-READONLY.py':'R3744',
    ORIGINAL:'R3745',
}
CLASS_ALLOW={
    'Hold','AttributeError','KeyError','TypeError','ValueError','IndexError',
    'AssertionError','RuntimeError','OverflowError','ZeroDivisionError',
    'UnboundLocalError','NameError','FileNotFoundError','PermissionError',
    'IsADirectoryError','NotADirectoryError','OSError','error','RecursionError',
    'ImportError','ModuleNotFoundError','EOFError','StopIteration',
}
_SAFE=re.compile(r'^[A-Z0-9_]{1,96}$')
_FN=re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,79}$')

class Hold(Exception):
    def __init__(self,code):
        self.code=code
        super().__init__(code)


def load_original(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('PARENT_DIRECTORY_INVALID_HOLD')
    path=folder/ORIGINAL
    if path.is_symlink() or not path.is_file():
        raise Hold('ORIGINAL_R3745_SOURCE_MISSING_HOLD')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=ORIGINAL_SHA256:
        raise Hold('ORIGINAL_R3745_SOURCE_SHA_HOLD')
    spec=importlib.util.spec_from_file_location('pinned_original_r3745_for_triage',path)
    if not spec or not spec.loader:
        raise Hold('ORIGINAL_R3745_IMPORT_HOLD')
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def sanitized_frames(exc):
    """Only static allowlisted source module IDs and function/line numbers."""
    frames=[]
    tb=exc.__traceback__
    while tb is not None:
        code=tb.tb_frame.f_code
        filename=code.co_filename
        # No original host path is included, even for unknown stack frames.
        base=Path(filename).name
        if base in ALLOWED_CODE_FILES:
            func=code.co_name
            frames.append({
                'source':ALLOWED_CODE_FILES[base],
                'function':func if _FN.fullmatch(func) else 'UNKNOWN_FUNCTION',
                'line':min(max(tb.tb_lineno,0),99999),
            })
        tb=tb.tb_next
    # Bounded frame data, never raw strings or tracebacks.
    return frames[-6:]


def summarize_exception(exc):
    """Do not access/print repr, args, str, chained exceptions, or paths."""
    typ=type(exc).__name__
    if typ not in CLASS_ALLOW:typ='OTHER_EXCEPTION_CLASS_REVIEW'
    # Classify only public audit constant HOLD codes, never arbitrary strings.
    raw=getattr(exc,'category',None)
    if raw is None:raw=getattr(exc,'code',None)
    hold_code=raw if isinstance(raw,str) and _SAFE.fullmatch(raw) else 'NONE_OR_UNRECOGNIZED'
    frames=sanitized_frames(exc)
    return {
        'milestone':'R40.4.3.7.45.1',
        'result':'ORIGINAL_R3745_FAILURE_SITE_CLASSIFIED_ONLY',
        'original_r3745_hold_category_preserved':'UNEXPECTED_STATIC_PARSER_HOLD',
        'exception_class':typ,
        'pinned_parent_hold_category':hold_code,
        'last_pinned_frame':frames[-1] if frames else {'source':'UNKNOWN','function':'UNKNOWN','line':0},
        'pinned_call_frames':frames,
        'original_source_unchanged_and_sha_pinned':True,
        'exception_message_or_traceback_exported':False,
        'stage_paths_or_symbol_names_exported':False,
        'stage_modified':False,
        'runtime_loader_verified':False,
        'guest_interpreter_path_resolved':False,
        'boot_authorized':False,
        'firmware_write_authorized':False,
        'prune_authorized':False,
        'immutable_hold':'NOT_BOOTABLE',
    }


def diagnostic(root,folder,orig=None):
    try:
        original=orig if orig is not None else load_original(folder)
        parent=original.load_parent(folder)
        result=original.audit(root,folder,parent)
    except Exception as exc:
        return summarize_exception(exc)
    # A change to the stage or source lineage can make original hold vanish.
    # Fail closed rather than declaring a previous error fixed or bootable.
    return {
        'milestone':'R40.4.3.7.45.1',
        'result':'HOLD',
        'hold_category':'ORIGINAL_R3745_EXCEPTION_NOT_REPRODUCED_HOLD' if result.get('result')=='WEAK_PLT_INITIAL_WORD_GEOMETRY_STATIC_ONLY' else 'ORIGINAL_R3745_DIFFERENT_RESULT_HOLD',
        'original_r3745_hold_category_preserved':'UNEXPECTED_STATIC_PARSER_HOLD',
        'boot_authorized':False,'prune_authorized':False,
        'immutable_hold':'NOT_BOOTABLE',
    }


def main():
    p=argparse.ArgumentParser(description='R3745.1 sanitized exception triage; NOT_BOOTABLE')
    p.add_argument('--rootfs',type=Path,required=True)
    p.add_argument('--parent-dir',type=Path,required=True)
    args=p.parse_args()
    out=diagnostic(args.rootfs,args.parent_dir)
    print(json.dumps(out,sort_keys=True))
    return 0 if out['result']=='ORIGINAL_R3745_FAILURE_SITE_CLASSIFIED_ONLY' else 2

if __name__=='__main__':
    raise SystemExit(main())
