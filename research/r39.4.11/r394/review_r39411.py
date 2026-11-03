#!/usr/bin/env python3
"""R39.4.11: require all three distinct original source-bound sidecar reads.

Fresh R25 baseline and untouched original strict R39.4, R39.4.5 and
R39.4.6 are mandatory. R39.4.7--R39.4.10 historical ARM FAILs stay FAIL.
"""
import argparse,json,re
from pathlib import Path
from review_r3946 import review as original_two_cycle
from review_r3945 import GATE as FIRST_GATE, LOADED as FIRST_LOAD
from review_r39410 import SECOND_CTX,SECOND_GATE,SECOND_LOAD
from review_r3947 import TARGET,CLEAN
from review_r3948 import FIRST_CTX
from review_r394 import SAFETY
THIRD_CTX=('R39_4_11_READERUI_INIT_SIDECAR_CONTEXT fm_closed=true '
           'input_cycle2=true prior_document_released=true registered_second_document=true')
THIRD_GATE=('R39_4_11_READERUI_INIT_SIDECAR_GATE exact=true c_pcall=true '
            'docsettings=true readerui_init=true regular_file=true phase3=true')
THIRD_LOAD='R39_4_11_GENUINE_READERUI_INIT_DOCSETTINGS_SIDECAR_RELOADED'

def review(log,baseline,pins,prior,strict):
    if pins.get('r39411_readerui_init_third_read_pinned') is not True:
        raise ValueError('R39.4.11 source-pinned third ReaderUI metadata read required')
    old=original_two_cycle(log,baseline,pins,prior,strict)
    if old['verdict']!='R39_4_6_TWO_CYCLE_SIDECAR_REOPEN_ARM_PASS':
        raise ValueError('original R39.4 / R39.4.5 / R39.4.6 strict reviewers must PASS')
    lines=log.splitlines()
    def one(s):
        matches=[i for i,x in enumerate(lines) if x==s]
        if len(matches)!=1:raise ValueError('missing/duplicate strict R39.4.11 marker: '+s)
        return matches[0]
    expected_prefixes={
        'R39_4_4_DOFILE_TARGET ':3,
        'R39_4_5_SIDECAR_GATE ':1,
        'R39_4_10_PDFDOCUMENT_SIDECAR_CONTEXT ':1,
        'R39_4_10_PDFDOCUMENT_SIDECAR_GATE ':1,
        'R39_4_11_READERUI_INIT_SIDECAR_CONTEXT ':1,
        'R39_4_11_READERUI_INIT_SIDECAR_GATE ':1,
    }
    for prefix,count in expected_prefixes.items():
        if sum(x.startswith(prefix) for x in lines)!=count:
            raise ValueError('wrong number of source-bound observations: '+prefix)
    targets=[i for i,x in enumerate(lines) if x.startswith('R39_4_4_DOFILE_TARGET ')]
    if len(targets)!=3 or any(lines[i]!=TARGET for i in targets):
        raise ValueError('exactly three original disposable PDF sidecar observations required')
    prohibited=('R39_4_7_READERUI_SIDECAR_GATE ',
                'R39_4_8_READERUI_SIDECAR_CONTEXT ',
                'R39_4_9_REGISTRY_PROVIDER_SIDECAR_GATE ',
                'R39_4_9_REGISTRY_PROVIDER_SIDECAR_CONTEXT ')
    if any(x.startswith(prohibited) for x in lines):
        raise ValueError('obsolete sidecar consumer claim must not be relabeled PASS')
    inh=[i for i,x in enumerate(lines) if x=='R39_1_GENUINE_READERUI_INPUT_INHIBIT_REQUESTED_SYNTHETIC_ONLY']
    rel=[i for i,x in enumerate(lines) if x=='R39_1_GENUINE_READERUI_INPUT_RELEASE_REQUESTED_SYNTHETIC_ONLY']
    if len(inh)!=2 or len(rel)!=2:
        raise ValueError('exactly two genuine ReaderUI Input lifecycles required')
    draws=[i for i,x in enumerate(lines) if re.fullmatch(r'R39_4_SECOND_GENUINE_PDF_SCROLL_DRAW_RETURNED page=[12]',x)]
    if len(draws)!=1:raise ValueError('exactly one genuine reopened PDF draw required')
    if not (
        one('R39_3_FILEMANAGER_ACTIVE_AFTER_HOME') <
        one('R39_4_REOPEN_REQUESTED_FROM_RETURNED_FILEMANAGER') <
        targets[0] < one(FIRST_CTX) < one(FIRST_GATE) < one(FIRST_LOAD) <
        one('R39_4_GENUINE_FILEMANAGER_REOPEN_SCHEDULED') <
        targets[1] < one(SECOND_CTX) < one(SECOND_GATE) < one(SECOND_LOAD) <
        inh[1] < targets[2] < one(THIRD_CTX) < one(THIRD_GATE) < one(THIRD_LOAD) <
        rel[1] < draws[0] <
        one('R39_4_DISTINCT_READERUI_AND_PDF_DOCUMENT_REOPENED') <
        one('R39_4_SECOND_HOME_SENT_THROUGH_REAL_UIMANAGER_INPUT') <
        one('R39_4_6_SECOND_GENUINE_SIDECAR_WRITE_OPEN') <
        one(CLEAN) <
        one('R39_4_SECOND_DOCUMENT_ENGINE_CLOSED_REGISTRY_EMPTY') <
        one('R39_4_FINAL_CLOSE_SENT_TO_SECOND_FILEMANAGER') <
        one('R39_REAL_READER_EXIT_BOUNDARY_PASS')):
        raise ValueError('three original read phases / two writes / final close reordered')
    if any('R23_DENIED_' in x or x.startswith('R39_4_3_FIRST_DENIAL ') or
           'coroutine crashed' in x or 'stack traceback' in x for x in lines):
        raise ValueError('denied operation or runtime exception invalidates PASS')
    return dict(verdict='R39_4_11_THREE_SOURCE_BOUND_READS_ARM_PASS',
        genuine_filemanager_provider_read_verified=True,
        genuine_pdfdocument_constructor_read_verified=True,
        genuine_readerui_init_read_verified=True,
        exact_generated_metadata_three_reads_and_two_write_opens_verified=True,
        second_document_registry_ref_and_distinct_engine_source_verified=True,
        two_home_returns_and_final_filemanager_close_verified=True,
        independent_original_strict_and_r3945_r3946_reviews_pass=True,
        independent_r25_baseline_control_pass=True,
        prior_r3947_through_r39410_arm_failures_preserved=True,
        physical_display_verified=False,global_startup_migrations_executed=False,
        complete_dependency_closure_proven=False,real_pw3_init=False,
        immutable_hold='NOT_BOOTABLE',**{x:False for x in SAFETY})

def main():
    ap=argparse.ArgumentParser()
    for arg in ('log','baseline','preflight','previous-r39-3-3','strict-review','out'):
        ap.add_argument('--'+arg,required=True,type=Path)
    a=ap.parse_args()
    if a.out.exists() or a.out.is_symlink():
        raise FileExistsError('R39.4.11 refuses overwrite of existing evidence')
    try:
        result=review(a.log.read_text(),json.loads(a.baseline.read_text()),
                      json.loads(a.preflight.read_text()),
                      json.loads(a.previous_r39_3_3.read_text()),
                      json.loads(a.strict_review.read_text()))
        code=0
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError,UnicodeError) as e:
        result=dict(verdict='FAIL',error=str(e),immutable_hold='NOT_BOOTABLE',
                    **{x:False for x in SAFETY})
        code=1
    a.out.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(result['verdict'])
    return code
if __name__=='__main__':raise SystemExit(main())
