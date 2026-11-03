#!/usr/bin/env python3
"""R39.4.8: verify the FileManager-active first sidecar read separately from
ReaderUI-init's FileManager-closed second read. The parent reviewers are strict.
"""
import argparse,json
from pathlib import Path
from review_r3947 import review as prior_review,FIRST_GATE,FIRST_LOAD,SECOND_GATE,SECOND_LOAD
from review_r394 import SAFETY
FIRST_CTX=('R39_4_8_RETURNED_FM_SIDECAR_CONTEXT present=true '
           'active=true first_document_released=true')
SECOND_CTX='R39_4_8_READERUI_SIDECAR_CONTEXT fm_closed=true input_cycle2=true'

def review(log,baseline,pins,prior,strict):
    if pins.get('r3948_phase_specific_filemanager_pinned') is not True:
        raise ValueError('R39.4.8 source-pinned phase correction required')
    old=prior_review(log,baseline,pins,prior,strict)
    if old['verdict']!='R39_4_7_TWO_SOURCE_BOUND_READS_ARM_PASS':
        raise ValueError('R39.4.7 and all preceding independent strict reviewers must PASS')
    lines=log.splitlines()
    def once(s):
        indexes=[i for i,x in enumerate(lines) if x==s]
        if len(indexes)!=1:raise ValueError('missing/duplicate audited R39.4.8 marker: '+s)
        return indexes[0]
    for prefix in ('R39_4_8_RETURNED_FM_SIDECAR_CONTEXT ',
                   'R39_4_8_READERUI_SIDECAR_CONTEXT '):
        if sum(x.startswith(prefix) for x in lines)!=1:
            raise ValueError('missing or duplicate R39.4.8 FM state marker: '+prefix)
    paints=[i for i,x in enumerate(lines) if x in (
        'R39_4_SECOND_GENUINE_PDF_SCROLL_DRAW_RETURNED page=1',
        'R39_4_SECOND_GENUINE_PDF_SCROLL_DRAW_RETURNED page=2')]
    if len(paints)!=1:
        raise ValueError('exactly one real second PDF draw required')
    if not (once('R39_4_REOPEN_REQUESTED_FROM_RETURNED_FILEMANAGER') <
            once(FIRST_CTX) < once(FIRST_GATE) < once(FIRST_LOAD) <
            once('R39_4_GENUINE_FILEMANAGER_REOPEN_SCHEDULED') <
            once(SECOND_CTX) < once(SECOND_GATE) < once(SECOND_LOAD) < paints[0] <
            once('R39_4_SECOND_HOME_SENT_THROUGH_REAL_UIMANAGER_INPUT') <
            once('R39_4_FINAL_CLOSE_SENT_TO_SECOND_FILEMANAGER') <
            once('R39_REAL_READER_EXIT_BOUNDARY_PASS')):
        raise ValueError('R39.4.8 returned FileManager/ReaderUI sidecar phases reordered')
    return dict(verdict='R39_4_8_FILEMANAGER_PHASE_BOUND_SIDECAR_ARM_PASS',
        first_sidecar_read_while_genuine_returned_filemanager_active=True,
        second_sidecar_read_after_filemanager_closed_in_original_readerui=True,
        all_prior_reviewers_independently_pass=True,
        two_pdf_lifecycles_with_final_genuine_filemanager_close_verified=True,
        independent_r25_control_pass=True,real_pw3_init=False,
        physical_display_verified=False,complete_dependency_closure_proven=False,
        immutable_hold='NOT_BOOTABLE',**{f:False for f in SAFETY})

def main():
    p=argparse.ArgumentParser()
    for n in ('log','baseline','preflight','previous-r39-3-3','strict-review','out'):
        p.add_argument('--'+n,required=True,type=Path)
    a=p.parse_args()
    if a.out.exists() or a.out.is_symlink():
        raise FileExistsError('R39.4.8 refuses overwrite of prior evidence')
    try:
        obj=review(a.log.read_text(),json.loads(a.baseline.read_text()),
            json.loads(a.preflight.read_text()),json.loads(a.previous_r39_3_3.read_text()),
            json.loads(a.strict_review.read_text()))
        exit_status=0
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError,UnicodeError) as exc:
        obj=dict(verdict='FAIL',error=str(exc),immutable_hold='NOT_BOOTABLE',
                 **{f:False for f in SAFETY});exit_status=1
    a.out.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
    print(obj['verdict'])
    return exit_status
if __name__=='__main__':raise SystemExit(main())
