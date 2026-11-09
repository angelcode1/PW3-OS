"""R3877.60.2: host-only, fail-closed Docker image VOLUME classification tests.

No real Docker, ARM execution, filesystem mount, SSH or device access.
"""
import io
import json
import inspect
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import pw3_r3877_60_2_qemu_enosys as m

ID='sha256:'+'a'*64
NAME='b'*64
DECL='/proc/sys/fs/binfmt_misc'


def image(volumes=None):
    return {'Id':ID, 'Config':{'Volumes':volumes if volumes is not None else {}}}


def info(mounts=None):
    return {
      'Image':ID,'State':{'Status':'created','Running':False},
      'Path':'/bin/true','Args':[],
      'Config':{'User':'65534:65534','Entrypoint':['/bin/true']},
      'HostConfig':{'NetworkMode':'none','Privileged':False,'ReadonlyRootfs':True,
          'Binds':None,'Mounts':None,'VolumesFrom':None,'Tmpfs':None,
          'Devices':None,'DeviceRequests':None,'CapDrop':['ALL'],
          'SecurityOpt':['no-new-privileges'],'PidsLimit':32,'Memory':134217728},
      'Mounts':[] if mounts is None else mounts,
    }


def vol(name=NAME,dest=DECL,kind='volume',driver='local',src=None):
    return {'Type':kind,'Name':name,'Driver':driver,'Destination':dest,
            'Source':src if src is not None else '/var/lib/docker/volumes/'+name+'/_data',
            'RW':True,'Mode':'','Propagation':''}


class VolumeSafetyTests(unittest.TestCase):
    def assert_held(self, bad, image_config=None, reason=None):
        p=m.image_declared_anonymous_volumes(bad,image_config or image({DECL:{}}),'/usr/bin/qemu-arm')
        self.assertFalse(p['verified'])
        if reason:self.assertEqual(p['reason'],reason)
        return p

    def test_01_preflight_zero_docker(self):
        with patch.object(m.base,'docker',side_effect=AssertionError('Docker accessed')):
            out=io.StringIO()
            with redirect_stdout(out):self.assertEqual(m.main([]),2)
        self.assertFalse(json.loads(out.getvalue())['docker_used'])
        self.assertEqual(json.loads(out.getvalue())['milestone'],'R3877.60.2')

    def test_02_pinned_bytes(self):self.assertTrue(m.verify_pins())
    def test_03_no_mount_allowed(self):
        p=m.image_declared_anonymous_volumes(info(),image(),'/usr/bin/qemu-arm')
        self.assertTrue(p['verified']);self.assertTrue(p['mounts_absent'])
        self.assertEqual(p['anonymous_volume_names'],[])
    def test_04_declared_anonymous_volume_allowed(self):
        p=m.image_declared_anonymous_volumes(info([vol()]),image({DECL:{}}),'/usr/bin/qemu-arm')
        self.assertTrue(p['verified']);self.assertFalse(p['mounts_absent'])
        self.assertEqual(p['anonymous_volume_names'],[NAME])
    def test_05_applet_path_overlapped(self):self.assert_held(info([vol(dest='/usr')]),image({'/usr':{}}),'VOLUME_OBSCURES_PINNED_EXECUTABLE')
    def test_06_file_path_overlapped(self):self.assert_held(info([vol(dest='/usr/bin/qemu-arm')]),image({'/usr/bin/qemu-arm':{}}),'VOLUME_OBSCURES_PINNED_EXECUTABLE')
    def test_07_bind_must_hold(self):self.assert_held(info([vol(kind='bind')]),reason='NONLOCAL_VOLUME_OR_HOST_BIND')
    def test_08_named_volume_must_hold(self):self.assert_held(info([vol(name='user-data')]),reason='NAMED_OR_INVALID_VOLUME')
    def test_09_external_driver_must_hold(self):self.assert_held(info([vol(driver='local_other')]),reason='NONLOCAL_VOLUME_OR_HOST_BIND')
    def test_10_unexpected_destination_must_hold(self):self.assert_held(info([vol(dest='/etc')]),reason='VOLUME_DESTINATION_NOT_DECLARED')
    def test_11_unexpected_source_must_hold(self):self.assert_held(info([vol(src='/Users/private')]),reason='VOLUME_SOURCE_NOT_DOCKER_MANAGED')
    def test_12_explicit_binds_must_hold(self):
        bad=info([vol()]);bad['HostConfig']['Binds']=['/Users/secret:/work']
        self.assert_held(bad,reason='EXPLICIT_MOUNT_CONFIGURATION_PRESENT')
    def test_13_explicit_mounts_must_hold(self):
        bad=info([vol()]);bad['HostConfig']['Mounts']=[{'Type':'volume'}]
        self.assert_held(bad,reason='EXPLICIT_MOUNT_CONFIGURATION_PRESENT')
    def test_14_volumes_from_must_hold(self):
        bad=info([vol()]);bad['HostConfig']['VolumesFrom']=['secret']
        self.assert_held(bad,reason='EXPLICIT_MOUNT_CONFIGURATION_PRESENT')
    def test_15_tmpfs_must_hold(self):
        bad=info([vol()]);bad['HostConfig']['Tmpfs']={'/tmp':''}
        self.assert_held(bad,reason='EXPLICIT_MOUNT_CONFIGURATION_PRESENT')
    def test_16_no_declared_volume_must_hold(self):
        self.assert_held(info([vol()]),image(),reason='MOUNT_NOT_ONE_TO_ONE_WITH_IMAGE_VOLUMES')
    def test_17_duplicate_volume_must_hold(self):
        self.assert_held(info([vol(),vol()]),reason='MOUNT_NOT_ONE_TO_ONE_WITH_IMAGE_VOLUMES')
    def test_18_none_rw_must_hold(self):
        bad=vol();bad.pop('RW');self.assert_held(info([bad]),reason='VOLUME_RW_METADATA_UNVERIFIED')
    def test_19_bad_image_config_must_hold(self):
        self.assert_held(info([vol()]),{'Id':ID,'Config':None},reason='IMAGE_VOLUME_DECLARATIONS_UNVERIFIED')
    def test_20_refuse_root_image_volume(self):
        with self.assertRaisesRegex(m.Hold,'UNSAFE'):
            m.declared_volume_destinations(image({'/':{}}))
    def test_21_refuse_traversal_image_volume(self):
        with self.assertRaisesRegex(m.Hold,'UNSAFE'):
            m.declared_volume_destinations(image({'/tmp/../etc':{}}))
    def test_22_refuse_too_many_image_volumes(self):
        with self.assertRaisesRegex(m.Hold,'INVALID'):
            m.declared_volume_destinations(image({('/a%d'%i):{} for i in range(17)}))
    def test_23_refuse_non_dict_image_volumes(self):
        with self.assertRaisesRegex(m.Hold,'INVALID'):
            m.declared_volume_destinations(image(['/tmp']))
    def test_24_report_was_sanitized(self):
        bad=info([vol()]);bad['Mounts'][0]['Source']='/Users/mysensitivepath'
        att=m.auxiliary_attestation(bad,ID,image({DECL:{}}),'/usr/bin/qemu-arm')
        self.assertFalse(att['all_verified']);self.assertIn('mounts_satisfy_strict_anonymous_image_volume_policy',att['failed_checks'])
        self.assertNotIn('/Users/',json.dumps(att));self.assertNotIn(NAME,json.dumps(att))
    def test_25_true_volume_report_is_explicit(self):
        att=m.auxiliary_attestation(info([vol()]),ID,image({DECL:{}}),'/usr/bin/qemu-arm')
        self.assertTrue(att['all_verified']);self.assertEqual(att['anonymous_image_declared_volume_count'],1)
        self.assertFalse(att['mounts_absent']);self.assertEqual(att['mount_classification'],'IMAGE_DECLARED_ANONYMOUS_LOCAL_VOLUMES')
        self.assertNotIn(NAME,json.dumps(att))
    def test_26_must_verify_image_identity(self):
        x=info([vol()]);x['Image']='bad'
        a=m.auxiliary_attestation(x,ID,image({DECL:{}}),'/usr/bin/qemu-arm')
        self.assertIn('image_id_matches_pin',a['failed_checks'])
    def test_27_preserve_readonly_and_seccomp(self):
        x=info([vol()]);x['HostConfig']['ReadonlyRootfs']=False
        x['HostConfig']['SecurityOpt']=['no-new-privileges','seccomp=unconfined']
        a=m.auxiliary_attestation(x,ID,image({DECL:{}}),'/usr/bin/qemu-arm')
        self.assertIn('rootfs_is_readonly',a['failed_checks'])
        self.assertIn('default_seccomp_not_overridden',a['failed_checks'])
    def test_28_require_helper_raises_for_unknown_mount(self):
        report={'auxiliary_container_isolation':{}}
        with self.assertRaisesRegex(m.Hold,'HELPER_CONTAINER_ISOLATION_UNVERIFIED'):
            m.require_auxiliary_attestation(report,'helper',info([vol(kind='bind')]),ID,image({DECL:{}}),'/usr/bin/qemu-arm')
    def test_29_require_helper_accepts_verified_anon(self):
        report={'auxiliary_container_isolation':{}}
        self.assertTrue(m.require_auxiliary_attestation(report,'helper',info([vol()]),ID,image({DECL:{}}),'/usr/bin/qemu-arm'))
    def test_30_no_explicit_mount_flags(self):
        for argv in (m.auxiliary_create('test','aux','linux/arm64'),m.create_guest(['/bin/busybox','true'],False)):
            self.assertNotIn('--mount',argv);self.assertNotIn('-v',argv);self.assertNotIn('--volume',argv)
    def test_31_cleanup_removes_anonymous_volumes(self):
        code=inspect.getsource(m.run)
        self.assertIn("['rm','-f','-v',cid]",code)
        self.assertIn("['volume','inspect',name]",code)
        self.assertIn("'anonymous_volume_cleanup_verified'",code)
    def test_32_no_host_mounts_claim_without_policy(self):
        code=inspect.getsource(m.run)
        self.assertIn("require_auxiliary_attestation(r,'helper'",code)
        self.assertIn("require_auxiliary_attestation(r,'preparation'",code)
    def test_33_named_source_not_accepted_by_empty_image(self):
        self.assert_held(info([vol()]),image(),reason='MOUNT_NOT_ONE_TO_ONE_WITH_IMAGE_VOLUMES')
    def test_34_wrong_type_tmpfs_must_hold(self):
        self.assert_held(info([vol(kind='tmpfs')]),reason='NONLOCAL_VOLUME_OR_HOST_BIND')
    def test_35_bad_anonymous_name_hex_must_hold(self):
        self.assert_held(info([vol(name='g'*64)]),reason='NAMED_OR_INVALID_VOLUME')

if __name__=='__main__':unittest.main()

# Deliberately keep lifecycle fake at module scope; no real Docker calls.
class CleanupLifecycleTests(unittest.TestCase):
    def _run_mock(self,volume_inspect_returns_exists=False,helper_type='volume'):
        from types import SimpleNamespace
        image_helper=image({DECL:{}})
        image_helper.update({'Id':ID,'RepoDigests':[m.base.HELPER_DIGEST],
                             'Architecture':'arm64','Os':'linux'})
        image_parent=image()
        image_parent.update({'Id':m.base.PARENT_ID,'Architecture':'arm','Os':'linux','Variant':'v7'})
        cid='c'*64; calls=[]
        def fake_docker(argv, **kwargs):
            calls.append(tuple(argv))
            if argv[0]=='version':return SimpleNamespace(stdout=json.dumps({'Arch':'arm64'}),stderr='',returncode=0)
            if argv[0]=='info':return SimpleNamespace(stdout=json.dumps(['name=seccomp,profile=builtin']),stderr='',returncode=0)
            if argv[0]=='create':return SimpleNamespace(stdout=cid+'\n',stderr='',returncode=0)
            if argv[0]=='cp':raise m.base.Hold('SYNTHETIC_STOP_BEFORE_GUEST_EXECUTION')
            if argv[:2]==['rm','-f']:
                return SimpleNamespace(stdout=cid,stderr='',returncode=0)
            if argv[:2]==['container','inspect']:
                return SimpleNamespace(stdout='',stderr='Error: No such container: '+cid,returncode=1)
            if argv[:2]==['volume','inspect']:
                if volume_inspect_returns_exists:return SimpleNamespace(stdout='[]',stderr='',returncode=0)
                return SimpleNamespace(stdout='',stderr='Error: No such volume: '+NAME,returncode=1)
            raise AssertionError('Unexpected Docker argv: '+repr(argv))
        def fake_image_info(ref):
            if ref==m.base.PARENT:return image_parent
            if ref==m.base.HELPER:return image_helper
            raise AssertionError(ref)
        def fake_container_inspect(kind,ident):
            self.assertEqual(kind,'container');self.assertEqual(ident,cid)
            sample=info([vol(kind=helper_type)])
            sample['Image']=ID
            return sample
        with patch.object(m.base,'docker',side_effect=fake_docker),\
             patch.object(m.base,'image_info',side_effect=fake_image_info),\
             patch.object(m.base,'inspect',side_effect=fake_container_inspect):
            report=m.run(False)
        return report,calls
    def test_36_verified_volume_cleanup_fails_after_test_copy_hold(self):
        r,calls=self._run_mock()
        self.assertEqual(r['hold_category'],'SYNTHETIC_STOP_BEFORE_GUEST_EXECUTION')
        self.assertTrue(r['auxiliary_container_isolation']['helper']['all_verified'])
        self.assertEqual(r['image_declared_anonymous_volume_count'],1)
        self.assertTrue(r['anonymous_volume_cleanup_verified'])
        self.assertTrue(r['all_created_containers_removed'])
        self.assertIn(('rm','-f','-v','c'*64),calls)
        self.assertIn(('volume','inspect',NAME),calls)
        self.assertFalse(r['arm_guest_execution_performed'])
    def test_37_volume_still_present_means_cleanup_unverified(self):
        r,_=self._run_mock(volume_inspect_returns_exists=True)
        self.assertFalse(r['anonymous_volume_cleanup_verified'])
        self.assertEqual(r['result'],'HOLD')
    def test_38_unclassified_mount_never_accepted(self):
        r,calls=self._run_mock(helper_type='bind')
        self.assertEqual(r['hold_category'],'HELPER_CONTAINER_ISOLATION_UNVERIFIED')
        self.assertFalse(r['anonymous_volume_cleanup_verified'])
        self.assertTrue(r['unclassified_mounts_require_manual_review'])
        self.assertNotIn(('volume','inspect',NAME),calls)
        self.assertTrue(r['all_created_containers_removed'])
    def test_39_unusual_volume_mode_refused(self):
        item=vol();item['Mode']='some-option'
        x=m.image_declared_anonymous_volumes(info([item]),image({DECL:{}}),'/usr/bin/qemu-arm')
        self.assertEqual(x['reason'],'VOLUME_MODE_UNEXPECTED')
