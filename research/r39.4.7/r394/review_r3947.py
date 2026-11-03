#!/usr/bin/env python3
"""Independent R39.4.7 verifier: two precisely source-bound metadata reads.

Depends on unchanged strict R39.4, R39.4.5 and R39.4.6 reviewers.
No host fixture may upgrade a real ARM failure.
"""
import argparse,json,re
from pathlib import Path
from review_r3946 import review as previous_review
from review_r3945 import GATE as FIRST_GATE, LOADED as FIRST_LOAD
from review_r394 import SAFETY
SECOND_GATE=('R39_4_7_READERUI_SIDECAR_GATE exact=true c_pcall=true '
             'docsettings=true readerui_init=true fresh_write=true '
             'regular_file=true phase2=true')
SECOND_LOAD='R39_4_7_GENUINE_READERUI_DOCSETTINGS_SIDECAR_RELOADED'
TARGET=('R39_4_4_DOFILE_TARGET path_kind=exact_pdf_sidecar '
        'caller_kind=other line=0 cycle=2 events=2 filemanagers=2')
CLEAN=('R39_4_2_SECOND_FILEMANAGER_STATE fm_present=true chooser_present=true '
       'chooser_path_kind=expected stack_depth=1 fm_stack_index=1 '
       'top_widget_present=true top_is_fm=true top_is_second_reader=false '
       'top_is_first_reader=false denied_zero=true')

def review(log,baseline,pins,prior,strict):
    if pins.get('r3947_two_source_bound_sidecar_reads_pinned') is not True:
        raise ValueError('R39.4.7 source hashes and separate reviewer are not pinned')
    old=previous_review(log,baseline,pins,prior,strict)
    if old['verdict']!='R39_4_6_TWO_CYCLE_SIDECAR_REOPEN_ARM_PASS':
        raise ValueError('independent original and R39.4.5/R39.4.6 strict passes required')
    lines=log.splitlines()
    def one(s):
        positions=[i for i,line in enumerate(lines) if line==s]
        if len(positions)!=1:raise ValueError('missing/duplicate strict R39.4.7 marker: '+s)
        return positions[0]
    if sum(line.startswith('R39_4_7_READERUI_SIDECAR_GATE ') for line in lines)!=1:
        raise ValueError('missing/duplicate or unverified second read gate')
    if sum(line.startswith('R39_4_5_SIDECAR_GATE ') for line in lines)!=1:
        raise ValueError('missing/duplicate or unverified first read gate')
    targets=[i for i,line in enumerate(lines) if line.startswith('R39_4_4_DOFILE_TARGET ')]
    if len(targets)!=2 or any(lines[i]!=TARGET for i in targets):
        raise ValueError('not exactly two exact synthetic sidecar target observations')
    inhibited=[i for i,x in enumerate(lines) if x==
        'R39_1_GENUINE_READERUI_INPUT_INHIBIT_REQUESTED_SYNTHETIC_ONLY']
    released=[i for i,x in enumerate(lines) if x==
        'R39_1_GENUINE_READERUI_INPUT_RELEASE_REQUESTED_SYNTHETIC_ONLY']
    if len(inhibited)!=2 or len(released)!=2:
        raise ValueError('both original ReaderUI initialization lifecycles required')
    draws=[i for i,x in enumerate(lines) if re.fullmatch(
        r'R39_4_SECOND_GENUINE_PDF_SCROLL_DRAW_RETURNED page=[12]',x)]
    if len(draws)!=1:raise ValueError('one genuine second PDF scroll draw required')
    if not (
        one('R39_3_FILEMANAGER_ACTIVE_AFTER_HOME') <
        one('R39_4_REOPEN_REQUESTED_FROM_RETURNED_FILEMANAGER') <
        targets[0] < one(FIRST_GATE) < one(FIRST_LOAD) <
        one('R39_4_GENUINE_FILEMANAGER_REOPEN_SCHEDULED') <
        inhibited[1] < targets[1] < one(SECOND_GATE) < one(SECOND_LOAD) <
        released[1] <
        draws[0] <
        one('R39_4_DISTINCT_READERUI_AND_PDF_DOCUMENT_REOPENED') <
        one('R39_4_SECOND_HOME_SENT_THROUGH_REAL_UIMANAGER_INPUT') <
        one('R39_4_6_SECOND_GENUINE_SIDECAR_WRITE_OPEN') <
        one(CLEAN) <
        one('R39_4_SECOND_DOCUMENT_ENGINE_CLOSED_REGISTRY_EMPTY') <
        one('R39_4_FINAL_CLOSE_SENT_TO_SECOND_FILEMANAGER') <
        one('R39_REAL_READER_EXIT_BOUNDARY_PASS')
    ):
        raise ValueError('two source-bound metadata reads or shutdown reordered')
    if any('R23_DENIED_' in x or x.startswith('R39_4_3_FIRST_DENIAL ') or
           'coroutine crashed' in x or 'stack traceback' in x for x in lines):
        raise ValueError('a denied operation or runtime exception forbids PASS')
    return dict(
        verdict='R39_4_7_TWO_SOURCE_BOUND_READS_ARM_PASS',
        first_read_from_returned_filemanager_verified=True,
        second_read_from_original_readerui_init_verified=True,
        two_exact_generated_metadata_reads_ordered_and_counted=True,
        exactly_two_source_bound_home_metadata_write_opens_verified=True,
        independent_original_and_r3945_r3946_reviews_pass=True,
        actual_two_readerui_and_both_home_returns_verified=True,
        final_genuine_filemanager_close_verified=True,
        independent_r25_control_pass=True,
        real_pw3_init=False,physical_display_verified=False,
        complete_dependency_closure_proven=False,global_startup_migrations_executed=False,
        immutable_hold='NOT_BOOTABLE',**{field:False for field in SAFETY})

def main():
    parser=argparse.ArgumentParser()
    for name in ('log','baseline','preflight','previous-r39-3-3','strict-review','out'):
        parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise FileExistsError('R39.4.7 refuses overwrite of any existing evidence')
    try:
        result=review(args.log.read_text(),json.loads(args.baseline.read_text()),
            json.loads(args.preflight.read_text()),
            json.loads(args.previous_r39_3_3.read_text()),
            json.loads(args.strict_review.read_text()))
        status=0
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError,UnicodeError) as e:
        result=dict(verdict='FAIL',error=str(e),immutable_hold='NOT_BOOTABLE',
            **{field:False for field in SAFETY}); status=1
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(result['verdict'])
    return status
if __name__=='__main__':raise SystemExit(main())
