#!/usr/bin/env python3
"""R3877.18.2: classify strict ELF candidate misses; no target writes.

One explicitly authorized SSH connection reads only fixed KOReader/system ELF
files. All parsing and classification runs on Mac; no Kindle binaries installed.
"""
import argparse,json,sys
import pw3_r3877_17_2_single_ssh_audit as transport
import r3877_18_1_ssh_diagnostic as diag
import r3877_18_2_scope_classifier as scope

class Hold(Exception):pass

def main(argv=None):
    ap=argparse.ArgumentParser(description='R3877.18.2 ELF global-scope candidate classification')
    ap.add_argument('--target')
    ap.add_argument('-p','--port',type=int,default=2222)
    ap.add_argument('--connect-timeout',type=int,default=20)
    ap.add_argument('--authorize-live-readonly-ssh',action='store_true')
    ap.add_argument('--probe-ssh-only',action='store_true')
    args=ap.parse_args(argv)
    out={'milestone':'R3877.18.2','result':'HOLD',
         'hold_category':'EXPLICIT_READONLY_SSH_AUTHORIZATION_REQUIRED',
         'immutable_hold':'NOT_BOOTABLE',
         'authorized_live_readonly_ssh':args.authorize_live_readonly_ssh,
         'ssh_sessions_requested':0,'app_and_stock_binary_contents_transferred':False,
         'personal_files_transferred':False,'device_files_written':False,
         'firmware_write_performed':False,'boot_performed':False,
         'new_target_binaries_installed_or_executed':False,
         'original_r13_stage_accessed':False,'koreader_dependency_closure_verified':False,
         'target_musl_runtime_verified':False,'target_kernel_syscall_compatibility_verified':False,
         'recovery_verified':False}
    if args.authorize_live_readonly_ssh:
        try:
            if args.target!=transport.EXPECTED_TARGET:raise Hold('UNEXPECTED_SSH_TARGET')
            if not 1<=args.port<=65535:raise Hold('SSH_PORT_INVALID')
            if not 5<=args.connect_timeout<=60:raise Hold('SSH_CONNECT_TIMEOUT_INVALID')
            out['ssh_sessions_requested']=1
            if args.probe_ssh_only:
                out['ssh_probe']=diag.probe_ssh_only(args.target,args.port,args.connect_timeout)
                out['result']='PASS_SSH_HANDSHAKE_ONLY';out['hold_category']='NOT_BOOTABLE'
            else:
                raw=diag.one_session_collect(args.target,args.port,args.connect_timeout)
                af,sf=transport.parse_concatenated_archives(raw)
                out['app_and_stock_binary_contents_transferred']=True
                out['inventory']=scope.analyze(af,sf)
                out['result']='PASS_SCOPE_CLASSIFICATION_METADATA_ONLY'
                out['hold_category']='NOT_BOOTABLE'
        except (Hold,scope.ScopeHold,transport.Hold,diag.Hold) as e:
            out['hold_category']=e.category if isinstance(e,(transport.Hold,diag.Hold)) else str(e)
            if isinstance(e,(transport.Hold,diag.Hold)):out.update(e.evidence)
        except Exception as e:
            out['hold_category']='UNEXPECTED_'+type(e).__name__
    print(json.dumps(out,sort_keys=True,indent=2))
    return 0 if out['result'].startswith('PASS_') else 2

if __name__=='__main__':sys.exit(main())
