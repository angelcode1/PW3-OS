#!/usr/bin/env python3
"""Pin separate R39.4 overlay and prior R39.3.3 runtime evidence without changing R39.3.3.
Reuses and executes the complete R39.3.3 source/fixture/R37/R38/R39.1/R39.2.4 checks.
"""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'r39'))
import check_inputs as prior
R394_PINS={'r394/loop_guard.lua': 'd35b7a5f6e2bb531b7880604b9cf115d00fc87f50bd48b3d10424030a6fa6ea6', 'r394/readerui_activation.lua': '0a396bb187530930077d63f0efeb751a1af036963826a54cb904818c824cf32a', 'r394/01_readerui_activation.lua': 'ddd1e2233f3420196f74eaf8da04d72b4422d00d7d1e2956a935ce53f7d69b2b', 'r394/probe_in_container.sh': 'cdc991b1b719535d3a324f355f18e6d9f9db0cf8e0894293893e0e19282149fa', 'r394/review_r394.py': 'b2d7a44f1acedeb6ec9899074e91bb0f4d3a4fed63b15d0816ff9d7b99d51e57', 'r394/fixtures/r39-original-two-pages.pdf': '17f2bf493433c9664457dd51f0e3e31e2f67b88b0480f97a3ed9dc2ade7170db'} # independently sha-pinned new overlay
PRIOR_R3933_SENTINEL_SHA256='0495144ebea105d337ea0bcf0b7009bcb679b3dcaafaa22f2ed3a48753f1dbb6'
SAFETY=('boot_authorized','device_access_authorized','firmware_write_authorized','hardware_write_authorized','file_removal_authorized')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inspect(stage,core,r37,r38,here,previous,previous_page,previous_r3933):
    here=Path(here)
    old=prior.inspect(stage,core,r37,r38,here,previous,previous_page)
    if old['verdict']!='R39_PINNED_SOURCES_AND_TWO_PAGE_FIXTURE_PASS':
        raise ValueError('R39.3.3 original source preflight failed')
    for rel,h in R394_PINS.items():
        p=here/rel
        if p.is_symlink() or not p.is_file() or p.stat().st_size>=500000 or sha(p)!=h:
            raise ValueError('R39.4 overlay source hash differs: '+rel)
    if sha(here/'r394/analyze_second_filemanager.py')!='16b17453bfe1c8539c434c6ae5db97c6452e8ffbd00d854c033c8cbeb05ead2e':
        raise ValueError('R39.4.2 diagnostic analyzer source hash differs')
    if sha(here/'r394/analyze_denial_provenance.py')!='a74b0e7af52e9b291d10a341e6e9ae505fe947a4d2eaef34ff2c5270dd18569b':
        raise ValueError('R39.4.3 denial analyzer source hash differs')
    if sha(here/'r394/analyze_dofile_target.py')!='dc54bb8cc05efdd1bd85ef8ba6ccf414001d01617fc0e1a4b5674c8bd118153b':
        raise ValueError('R39.4.4 dofile target analyzer source hash differs')
    if sha(here/'r394/review_r3945.py')!='8e28fb054aacc0ed4999deafd6b909ce5d88791a7e32451ea0e66c7d2cd322e0':
        raise ValueError('R39.4.5 source-bound sidecar reviewer hash differs')
    if sha(here/'r394/review_r3946.py')!='58587bd90bf6bd56c626d39fdc5690775ac5cf8bed9a152ba69de369822d74ef':
        raise ValueError('R39.4.6 independent two-cycle reviewer hash differs')
    if sha(here/'r394/review_r3947.py')!='07e116b0c26f84bb3ef218b9dd80b09bfede3cfe1e0a3018fbaecb47e4f09e73':
        raise ValueError('R39.4.7 two-read strict reviewer hash differs')
    if sha(here/'r394/review_r3948.py')!='9ff7bf9333514de53e2c3290f97df206b87e6552efdb9506716d290e83588896':
        raise ValueError('R39.4.8 phase-bound independent reviewer hash differs')
    if sha(Path(previous_r3933))!=PRIOR_R3933_SENTINEL_SHA256:
        raise ValueError('R39.4 expected exact user-side R39.3.3 sentinel reviewer hash')
    witness=json.loads(Path(previous_r3933).read_text())
    if witness.get('verdict')!='R39_3_3_HOME_ENGINE_SENTINEL_ARM_PASS' or witness.get('immutable_hold')!='NOT_BOOTABLE':
        raise ValueError('R39.4 prior R39.3.3 actual ARM sentinel PASS required')
    for field in ('genuine_pdf_engine_raw_instance_slot_cleared','document_registry_no_remaining_refs_verified','genuine_filemanager_return_verified','independent_r25_baseline_control_pass'):
        if witness.get(field) is not True:raise ValueError('R39.4 missing prior user-side ARM proof: '+field)
    for f in SAFETY:
        if witness.get(f) is not False:raise ValueError('R39.4 prior sentinel safety hold missing: '+f)
    return dict(verdict='R39_4_PINNED_SOURCES_PASS',
        r394_new_overlay_sha256_verified=True,r3941_repeat_input_lifecycle_fix_pinned=True,r3942_second_filemanager_snapshot_pinned=True,r3943_denial_provenance_pinned=True,r3944_dofile_target_pinned=True,r3945_source_bound_sidecar_pinned=True,r3946_two_home_sidecar_write_pinned=True,r3947_two_source_bound_sidecar_reads_pinned=True,r3948_phase_specific_filemanager_pinned=True,r394_pins=R394_PINS,
        inherited_r3933_source_preflight=old['verdict'],
        prior_actual_r3933_arm_verified=True,
        prior_r3933_sentinel_sha256=PRIOR_R3933_SENTINEL_SHA256,arm_run_proven=False,
        **{f:False for f in SAFETY},immutable_hold='NOT_BOOTABLE')
def main():
    ap=argparse.ArgumentParser()
    for name in ('stage','core','r37-summary','r38-reconciled','here','previous-r39-review','previous-r39-page-turn-review','previous-r39-3-3'):
        ap.add_argument('--'+name,required=True,type=Path)
    ap.add_argument('--out',type=Path)
    ap.add_argument('--check-only',action='store_true')
    a=ap.parse_args()
    if not a.check_only:
        if a.out is None or a.out.exists() or a.out.is_symlink():raise FileExistsError('R39.4 refuses existing report')
        for d in (a.stage,a.core,a.here):
            if a.out.resolve()==d.resolve() or d.resolve() in a.out.resolve().parents:
                raise ValueError('R39.4 output inside source tree forbidden')
    o=inspect(a.stage,a.core,a.r37_summary,a.r38_reconciled,a.here,a.previous_r39_review,a.previous_r39_page_turn_review,a.previous_r39_3_3)
    if not a.check_only:a.out.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')
    print(o['verdict'])
if __name__=='__main__':main()
