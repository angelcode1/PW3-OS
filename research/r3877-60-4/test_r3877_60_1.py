"""R3877.60.1 auxiliary-container isolation attestation: offline synthetic tests."""
import json
import io
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
import pw3_r3877_60_1_qemu_enosys as m


def good_info(image_id):
    return {
      'Image':image_id,'State':{'Status':'created','Running':False},
      'Path':'/bin/true','Args':[],
      'Config':{'User':'65534:65534','Entrypoint':['/bin/true']},
      'Mounts':[],
      'HostConfig':{
        'NetworkMode':'none','Privileged':False,'ReadonlyRootfs':True,
        'Binds':None,'Devices':None,'DeviceRequests':None,
        'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges'],
        'PidsLimit':32,'Memory':134217728},
    }

class AuxiliaryTests(unittest.TestCase):
    def setUp(self): self.id='sha256:'+'a'*64
    def test_01_default_invokes_no_docker(self):
        with patch.object(m.base,'docker',side_effect=AssertionError('unexpected Docker')):
            buf=io.StringIO()
            with redirect_stdout(buf): self.assertEqual(m.main([]),2)
            j=json.loads(buf.getvalue())
            self.assertEqual(j['result'],'HOLD')
            self.assertEqual(j['milestone'],'R3877.60.1')
            self.assertFalse(j['docker_used'])
    def test_02_pin_verification(self): self.assertTrue(m.verify_pins())
    def test_03_helper_positive(self):
        a=m.auxiliary_attestation(good_info(self.id),self.id)
        self.assertTrue(a['all_verified']);self.assertEqual(a['failed_checks'],[])
        self.assertEqual(len(a['checks']),17)
    def test_04_false_image(self):self.reject('Image','different','image_id_matches_pin')
    def test_05_running(self):self.reject('State.Running',True,'running_is_false')
    def test_06_status(self):self.reject('State.Status','running','status_is_created')
    def test_07_privileged(self):self.reject('HostConfig.Privileged',True,'privileged_is_false')
    def test_08_network(self):self.reject('HostConfig.NetworkMode','bridge','network_is_none')
    def test_09_mount(self):self.reject('Mounts',[{'Type':'volume'}],'mounts_absent')
    def test_10_bind(self):self.reject('HostConfig.Binds',['/private'],'binds_absent')
    def test_11_device(self):self.reject('HostConfig.Devices',[{}],'devices_absent')
    def test_12_device_requests(self):self.reject('HostConfig.DeviceRequests',[{}],'device_requests_absent')
    def test_13_readonly(self):self.reject('HostConfig.ReadonlyRootfs',False,'rootfs_is_readonly')
    def test_14_capdrop(self):self.reject('HostConfig.CapDrop',[],'all_capabilities_dropped')
    def test_15_new_privs(self):self.reject('HostConfig.SecurityOpt',[],'no_new_privileges')
    def test_16_seccomp_replace(self):self.reject('HostConfig.SecurityOpt',['no-new-privileges','seccomp=unconfined'],'default_seccomp_not_overridden')
    def test_17_pids(self):self.reject('HostConfig.PidsLimit',64,'pids_limit_32')
    def test_18_memory(self):self.reject('HostConfig.Memory',0,'memory_limit_128m')
    def test_19_uid(self):self.reject('Config.User','0:0','user_is_unprivileged')
    def test_20_entrypoint(self):self.reject('Config.Entrypoint',['/sbin/init'],'entrypoint_is_bin_true')
    def test_21_path(self):self.reject('Path','/bin/sh','entrypoint_is_bin_true')
    def test_22_invalid_inspect(self):
        with self.assertRaisesRegex(m.Hold,'INSPECT_INVALID'):m.auxiliary_attestation([],self.id)
    def test_23_missing_fields_fail_closed(self):
        a=m.auxiliary_attestation({},self.id)
        self.assertFalse(a['all_verified']);self.assertGreater(len(a['failed_checks']),8)
    def test_24_aux_cli_flags(self):
        for ref,platform in [('test/arch','linux/arm64'),('test/arm','linux/arm/v7')]:
            a=m.auxiliary_create(ref,'local-test',platform)
            for flag,value in [('--network','none'),('--user','65534:65534'),('--memory','128m'),('--pids-limit','32'),('--security-opt','no-new-privileges'),('--cap-drop','ALL')]:
                self.assertEqual(a[a.index(flag)+1],value)
            self.assertIn('--read-only',a);self.assertNotIn('--privileged',a)
            self.assertNotIn('--mount',a);self.assertNotIn('--volume',a)
            self.assertEqual(a[-1],ref)
    def test_25_report_failure_is_sanitized(self):
        info=good_info(self.id);info['Mounts']=[{'Source':'/very/private/path','Type':'bind'}]
        r={'auxiliary_container_isolation':{}}
        with self.assertRaisesRegex(m.Hold,'HELPER_CONTAINER_ISOLATION_UNVERIFIED'):
            m.require_auxiliary_attestation(r,'helper',info,self.id)
        a=r['auxiliary_container_isolation']['helper']
        self.assertEqual(a['failed_checks'],['mounts_absent'])
        self.assertNotIn('/very/private/path',json.dumps(a))
    def test_26_prep_failure(self):
        info=good_info(self.id);info['HostConfig']['Privileged']=True
        r={'auxiliary_container_isolation':{}}
        with self.assertRaisesRegex(m.Hold,'PREPARATION_CONTAINER_ISOLATION_UNVERIFIED'):
            m.require_auxiliary_attestation(r,'preparation',info,self.id)
    def test_27_report_pass(self):
        r={'auxiliary_container_isolation':{}}
        self.assertTrue(m.require_auxiliary_attestation(r,'helper',good_info(self.id),self.id))
        self.assertTrue(r['auxiliary_container_isolation']['helper']['all_verified'])
    def test_28_disallow_wrong_label(self):
        with self.assertRaisesRegex(m.Hold,'LABEL_INVALID'):
            m.require_auxiliary_attestation({},'guest',good_info(self.id),self.id)
    def test_29_no_explicit_seccomp_override(self):
        a=m.auxiliary_create('x','y','linux/arm64')
        self.assertNotIn('seccomp=unconfined',a)
    def test_30_output_no_raw_inspect(self):
        a=m.auxiliary_attestation(good_info(self.id),self.id)
        self.assertFalse(a['raw_inspect_metadata_published'])
        self.assertNotIn(self.id,json.dumps(a))
    def reject(self,path,value,key):
        info=good_info(self.id)
        obj=info;parts=path.split('.')
        for part in parts[:-1]:obj=obj[part]
        obj[parts[-1]]=value
        a=m.auxiliary_attestation(info,self.id)
        self.assertFalse(a['all_verified']);self.assertIn(key,a['failed_checks'])

if __name__=='__main__': unittest.main()
