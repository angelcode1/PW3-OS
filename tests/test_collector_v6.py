import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).with_name('pw3_collect_v6_hostcap.py')
spec = importlib.util.spec_from_file_location('pw3_v6', SCRIPT)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

class CollectorV6Tests(unittest.TestCase):
    def test_dry_run_and_version(self):
        a = subprocess.run([sys.executable, str(SCRIPT)],capture_output=True,text=True,check=True)
        self.assertIn('DRY_RUN_ONLY',a.stdout)
        b = subprocess.run([sys.executable, str(SCRIPT),'--version'],capture_output=True,text=True,check=True)
        self.assertIn('PW3-V6-HOSTCAP-20261101',b.stdout)

    def test_remote_is_static_read_only(self):
        self.assertEqual(len(m.PROBES),17)
        for cmd in m.PROBES.values():
            for forbidden in ['head -c','grep -E','dd ','mount ','rm ','lipc-', '/mnt/us', 'reboot', 'echo >', 'printf >']:
                self.assertNotIn(forbidden,cmd)
        self.assertFalse(any("cat " + v in " ".join(m.PROBES.values()) for v in m.OPTIONAL_FILES))
        self.assertNotIn('set -f',m.probe_script('input_nodes.txt'))
        self.assertIn('/dev/input/event*', m.probe_script('input_nodes.txt'))

    def test_host_port_validation(self):
        for host,port in [('bad host',2222),('-bad',2222),('127.0.0.1',0),('127.0.0.1',65536)]:
            with self.assertRaises(ValueError):
                m.remote_ssh(host,port,'uname -r')

    def test_bounded_stream_short(self):
        r = m.run_bounded([sys.executable,'-c',"import sys; sys.stdout.write('abc'); sys.stderr.write('warning')"], 'ignored')
        self.assertEqual(r.returncode,0)
        self.assertEqual(r.stdout,b'abc')
        self.assertEqual(r.stderr,b'warning')
        self.assertFalse(r.over_limit)

    def test_bounded_stream_large(self):
        r = m.run_bounded([sys.executable,'-c',"import sys; sys.stdout.write('x'*100000); sys.stdout.flush()"], 'ignored',timeout=5)
        self.assertTrue(r.over_limit)
        self.assertEqual(len(r.stdout),m.MAX_BYTES)

    def test_bounded_stream_timeout(self):
        with self.assertRaises(TimeoutError):
            m.run_bounded([sys.executable,'-c','import time; time.sleep(2)'], 'ignored',timeout=0.1)

    def test_fixed_optional_file_list(self):
        script = m.file_script('/etc/fstab')
        self.assertIn('if [ -L "$p" ]', script)
        self.assertIn('wc -c',script)
        with self.assertRaises(AssertionError):
            m.file_script('/mnt/us/notes.txt')

    def test_fake_ssh_end_to_end(self):
        with tempfile.TemporaryDirectory() as folder:
            td=Path(folder)
            ssh=td/'ssh'
            ssh.write_text('#!/usr/bin/env python3\nimport sys\ns=sys.stdin.read()\n'
                'if "uname -r" in s: print("3.0.35-lab126")\n'
                'elif "uname -a" in s: print("Linux mock 3.0.35-lab126")\n'
                'elif "ls -1 /lib/ /usr/lib/" in s: print("liblipc.so\\nlibpthread.so\\npassword.txt")\n'
                'else: print("MOCK READ ONLY CONTENT")\n')
            ssh.chmod(0o755)
            dest=td/'evidence.zip'
            env=dict(os.environ, PATH=str(td)+os.pathsep+os.environ.get('PATH',''))
            r=subprocess.run([sys.executable,str(SCRIPT),'--collect','--out',str(dest)],
                             env=env,capture_output=True,text=True,timeout=20)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertIn('COLLECTED: 17 ERRORS: 0',r.stdout)
            with zipfile.ZipFile(dest) as z:
                self.assertIsNone(z.testzip())
                manifest=json.loads(z.read('MANIFEST.json'))
                self.assertEqual(len(manifest['entries']),17)
                self.assertEqual(manifest['collector_revision'],m.COLLECTOR_REV)
                self.assertEqual(z.read('diagnostics/kernel_release.txt'),b'3.0.35-lab126\n')
                self.assertNotIn(b'password',z.read('diagnostics/library_names.txt'))
            r2=subprocess.run([sys.executable,str(SCRIPT),'--collect','--out',str(dest)],
                              env=env,capture_output=True,text=True,timeout=20)
            self.assertNotEqual(r2.returncode,0)
            self.assertIn('refusing to overwrite',r2.stderr)

if __name__ == '__main__':
    unittest.main()
