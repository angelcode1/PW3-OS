"""Synthetic offline tests of R3877.83. No network, Kindle or ELF execution."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch
import pw3_r3877_83_glibc_luajit_smoke as m

OPTS = b'--inhibit-rpath --library-path --inhibit-cache --list'


def synthetic_review():
    return {'counts':{'required_versions':13,'matched_versions':13,
                      'missing_versions':0,'versions_without_definition_table':0},
            'arm_vfp_warnings':[],
            'objects':{
                'luajit':{'float_e_flags':'soft','arm_vfp_args':{'status':'TAG_ABSENT'},
                          'rpath_resolution_categories':['UNSAFE_OR_UNKNOWN_RPATH'], 'has_pt_interp':True},
                **{name:{'float_e_flags':'soft','arm_vfp_args':{'status':'TAG_ABSENT'},
                         'has_pt_interp':False} for name in m.NAMES}}}


def prepare_files(root):
    for name, rel in [('luajit',m.APP)]+[(x,f'{m.LIB_PREFIX}/{x}') for x in m.NAMES]:
        p=root / rel
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes((name.encode()+b':'+OPTS) if name=='ld-linux.so.3' else name.encode())

class Tests(unittest.TestCase):
    def test_01_default_no_stage_or_ssh(self):
        with patch.object(m,'validate_stage',side_effect=AssertionError('should not scan')):
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(m.main(['--stage','/absent']),2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'LIVE_SINGLE_PROCESS_OPT_IN_REQUIRED')

    def test_02_pinned_prior_source_hashes(self):
        self.assertEqual(set(m.PRIOR_SOURCE_SHA256),set(['pw3_r3877_81_glibc_closure.py','pw3_r3877_82_version_abi_audit.py']))
        for name, sha in m.PRIOR_SOURCE_SHA256.items():
            self.assertEqual(m.digest((Path(m.__file__).parent/name).read_bytes()),sha)

    def test_03_stage_host_check_holds(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'root';root.mkdir();prepare_files(root)
            with patch.object(m.r82,'inspect',return_value=synthetic_review()),patch.object(m.r81,'raw_file',side_effect=lambda p:p.read_bytes()):
                with redirect_stdout(io.StringIO()) as out:
                    code=m.main(['--stage',str(root),'--review-only'],runner=lambda *a,**k:None)
        result=json.loads(out.getvalue())
        self.assertEqual(code,2)
        self.assertTrue(result['offline_validation_passed'])
        self.assertEqual(result['result'],'HOLD')
        self.assertFalse(result['device_execution_attempted'])

    def test_04_missing_symbol_version_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'root';root.mkdir();prepare_files(root)
            review=synthetic_review();review['counts']['missing_versions']=1
            with patch.object(m.r82,'inspect',return_value=review):
                with self.assertRaises(m.Hold) as ctx:m.validate_stage(str(root))
        self.assertEqual(str(ctx.exception),'ABI_OR_SYMBOL_VERSION_PREFLIGHT_UNRESOLVED')

    def test_05_wrong_float_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'root';root.mkdir();prepare_files(root)
            review=synthetic_review();review['objects']['libm.so.6']['float_e_flags']='hard'
            with patch.object(m.r82,'inspect',return_value=review):
                with self.assertRaises(m.Hold) as ctx:m.validate_stage(str(root))
        self.assertEqual(str(ctx.exception),'FLOAT_ABI_FLAGS_NOT_MATCHED')

    def test_06_arm_vfp_hard_tag_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'root';root.mkdir();prepare_files(root)
            review=synthetic_review();review['objects']['luajit']['arm_vfp_args']={'status':'VFP_AAPCS'}
            with patch.object(m.r82,'inspect',return_value=review):
                with self.assertRaises(m.Hold) as ctx:m.validate_stage(str(root))
        self.assertEqual(str(ctx.exception),'ARM_VFP_ABI_NOT_REVIEWED')

    def test_07_symlink_provider_parent_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'root';root.mkdir();prepare_files(root)
            (root/'opt/koreader-compat/gnu/lib/libm.so.6').unlink()
            (root/'opt/koreader-compat/gnu/lib/libm.so.6').symlink_to('/etc/passwd')
            with patch.object(m.r82,'inspect',return_value=synthetic_review()):
                with patch.object(m.r81,'raw_file',side_effect=lambda p:p.read_bytes() if not p.is_symlink() else (_ for _ in ()).throw(m.r81.Refused('SYMLINK'))):
                    with self.assertRaises(m.Hold): m.validate_stage(str(root))

    def test_08_restrict_loader_options(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'root';root.mkdir();prepare_files(root)
            (root/f'{m.LIB_PREFIX}/ld-linux.so.3').write_bytes(b'not-supported')
            with patch.object(m.r82,'inspect',return_value=synthetic_review()),patch.object(m.r81,'raw_file',side_effect=lambda p:p.read_bytes()):
                with self.assertRaises(m.Hold) as ctx:m.validate_stage(str(root))
        self.assertEqual(str(ctx.exception),'LOADER_OPTION_STRING_UNVERIFIED')

    def test_09_bundle_bare_names_and_regular(self):
        objs={'luajit':b'app',**{n:n.encode() for n in m.NAMES}}
        tar=m.bundle_tar(objs)
        with tarfile.open(fileobj=io.BytesIO(tar),mode='r:') as t:
            self.assertEqual(set(x.name for x in t),set(objs))
            self.assertTrue(all(x.isfile() and '/' not in x.name and x.uid==0 for x in t.getmembers()))

    def test_10_remote_is_tmpfs_only_and_inhibit_rpath(self):
        x=m.remote_shell({'luajit':b'x',**{n:b'x' for n in m.NAMES}})
        self.assertIn('--inhibit-rpath "luajit:$work/luajit"',x)
        self.assertEqual(x.count('--inhibit-rpath "luajit:$work/luajit"'),2)
        self.assertIn('--list "$work/luajit"',x)
        self.assertIn('=> $work/',x)
        self.assertIn('case "$mp:$kind" in /tmp:tmpfs',x)
        self.assertNotIn('mount -',x)
        self.assertNotIn('chroot',x)
        self.assertNotIn('mmcblk',x)
        self.assertNotIn('initctl',x)

    def _mock_main(self,returncode=0,output=m.MARKER):
        objs={'luajit':b'abc',**{n:OPTS+n.encode() for n in m.NAMES}}
        with patch.object(m,'validate_stage',return_value=(objs,synthetic_review())):
            with redirect_stdout(io.StringIO()) as out:
                code=m.main(['--stage','/exists','--acknowledge-one-shot-kindle-glibc-test'],
                            runner=lambda *a,**k:Mock(returncode=returncode,stdout=output,stderr=b''))
        return code,json.loads(out.getvalue())

    def test_11_native_success_not_bootable(self):
        rc,j=self._mock_main()
        self.assertEqual(rc,0)
        self.assertTrue(j['lua_native_execution_verified'])
        self.assertEqual(j['result'],'PASS_GLIBC_LUAJIT_SINGLE_PROCESS')
        self.assertEqual(j['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(j['koreader_gui_started'])
        self.assertFalse(j['firmware_write_performed'])

    def test_12_false_marker_refused(self):
        rc,j=self._mock_main(output=m.MARKER+b'other')
        self.assertEqual(rc,2)
        self.assertFalse(j['lua_native_execution_verified'])

    def test_13_bad_loader_resolution_hold(self):
        rc,j=self._mock_main(returncode=51,output=b'')
        self.assertEqual(rc,2)
        self.assertEqual(j['hold_category'],'DYNAMIC_LOADER_PROVIDER_NOT_IN_RAM')

    def test_14_timeout_unverified_cleanup(self):
        with patch.object(m,'validate_stage',return_value=({'luajit':b'x',**{n:b'x' for n in m.NAMES}},synthetic_review())):
            def timedout(*a,**k):raise subprocess.TimeoutExpired('ssh',75)
            with redirect_stdout(io.StringIO()) as out:
                rc=m.main(['--stage','/not-here','--acknowledge-one-shot-kindle-glibc-test'],runner=timedout)
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'SSH_OR_TIMEOUT_CLEANUP_UNVERIFIED')

    def test_15_reject_target_injection(self):
        with redirect_stdout(io.StringIO()) as out:
            rc=m.main(['--stage','/not-here','--acknowledge-one-shot-kindle-glibc-test', '--target','root@site;touch /tmp/bad'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'TARGET_OR_PORT_INVALID')

    def test_16_exclusive_modes(self):
        with redirect_stdout(io.StringIO()) as out:
            rc=m.main(['--stage','/not-here','--review-only','--acknowledge-one-shot-kindle-glibc-test'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'MUTUALLY_EXCLUSIVE_MODES')

    def test_17_readonly_staged_host_not_print_path(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'root';root.mkdir();prepare_files(root)
            with patch.object(m.r82,'inspect',return_value=synthetic_review()),patch.object(m.r81,'raw_file',side_effect=lambda p:p.read_bytes()):
                with redirect_stdout(io.StringIO()) as out:
                    m.main(['--stage',str(root),'--review-only'])
        self.assertNotIn(d,out.getvalue())

    def test_18_inhibit_real_sanitized_shell(self):
        s=m.remote_shell({'luajit':b'abc',**{n:b'xyz' for n in m.NAMES}})
        # shell syntax only; no execution of remote script.
        cp=subprocess.run(['sh','-n'],input=s,text=True,capture_output=True)
        self.assertEqual(cp.returncode,0,cp.stderr)

if __name__=='__main__':unittest.main()
