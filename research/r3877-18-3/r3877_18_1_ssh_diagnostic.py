"""SSH error diagnostics for R3877.18.1. Never logs or stores archive contents.

The probe and collection are distinct, user-selected operations. Each uses
exactly one SSH invocation. No automatic retries or host-side modifications.
"""
import hashlib
import subprocess
import pw3_r3877_17_2_single_ssh_audit as original

class Hold(Exception):
    def __init__(self, category, **evidence):
        super().__init__(category)
        self.category=category
        self.evidence=evidence

def _ssh_prefix(target, port, connect_timeout):
    if target != original.EXPECTED_TARGET:
        raise Hold('UNEXPECTED_SSH_TARGET')
    if not 1 <= port <= 65535 or not 5 <= connect_timeout <= 60:
        raise Hold('INVALID_SSH_OPTION')
    return ['ssh','-T','-p',str(port),'-o',f'ConnectTimeout={connect_timeout}',
            '-o','ConnectionAttempts=1','--',target]

def _run(target,port,connect_timeout,command,stdin_data=None):
    cmd = _ssh_prefix(target,port,connect_timeout)+[command]
    try:
        cp=subprocess.run(cmd,input=stdin_data,capture_output=True,timeout=180)
    except subprocess.TimeoutExpired as e:
        raise Hold('SSH_COMMAND_TIMEOUT',ssh_command_timeout_seconds=180) from e
    except OSError as e:
        raise Hold('SSH_COMMAND_LAUNCH_FAILED',error_type=type(e).__name__) from e
    if cp.returncode:
        raw=cp.stderr
        # Reporting only classes, lengths and hashes; no raw stderr, stdout or ELF bytes.
        raise Hold('SSH_COLLECTION_FAILED',ssh_exit_code=cp.returncode,
            ssh_error_class=original.classify_ssh_error(raw,cp.returncode),
            ssh_stderr_bytes=len(raw),ssh_stderr_sha256=hashlib.sha256(raw).hexdigest(),
            ssh_partial_stdout_bytes=len(cp.stdout),
            ssh_partial_stdout_present=bool(cp.stdout))
    return cp.stdout

def probe_ssh_only(target,port,connect_timeout):
    data=_run(target,port,connect_timeout,
              "printf 'R3877_18_1_SSH_READY\\n'; uname -r; uname -m")
    if len(data)>1024:
        raise Hold('SSH_PROBE_OUTPUT_TOO_LARGE',ssh_probe_stdout_bytes=len(data))
    text=data.decode('utf-8','replace')
    lines=text.strip().splitlines()
    if lines != ['R3877_18_1_SSH_READY','3.0.35-lab126','armv7l']:
        raise Hold('SSH_PROBE_UNEXPECTED_TARGET_RESPONSE',ssh_probe_stdout_bytes=len(data))
    return {'probe':'READONLY_UNAME_ONLY','kernel_release':'3.0.35-lab126',
            'machine':'armv7l','ssh_handshake_and_command_completed':True,
            'archive_transfer_attempted':False}

def one_session_collect(target,port,connect_timeout):
    raw=_run(target,port,connect_timeout,'sh -s',original.TARGET_SCRIPT.encode('ascii'))
    if not raw or len(raw)>original.MAX_COMBINED_ARCHIVE:
        raise Hold('COMBINED_ARCHIVE_EMPTY_OR_TOO_LARGE',archive_stdout_bytes=len(raw))
    return raw
