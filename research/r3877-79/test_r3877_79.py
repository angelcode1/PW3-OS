"""Synthetic host-only tests of R3877.79 (no device / network)."""
import contextlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import pw3_r3877_79_koreader_entrypoint as m


def elf(*, machine=40, flags=0x05000400, interpreter=b'/lib/ld-linux-armhf.so.3\0', entry=0x1000):
    b=bytearray(512)
    b[:16]=b'\x7fELF'+bytes([1,1,1,0])+bytes(8)
    struct.pack_into('<HHIIIIIHHHHHH',b,16,2,machine,1,entry,52,0,flags,52,32,1,0,0,0)
    struct.pack_into('<8I',b,52,3,128,0,0,len(interpreter),len(interpreter),4,1)
    b[128:128+len(interpreter)]=interpreter
    return bytes(b)

class Tests(unittest.TestCase):
    def test_01_eabi_arm_glibc(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'luajit';p.write_bytes(elf())
            x=m.inspect_elf(p)
            self.assertEqual(x['interpreter_class'],'GLIBC_ARM_LOADER')
            self.assertTrue(x['arm_hard_float'] and x['arm_eabi5'])

    def test_02_musl(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'luajit';p.write_bytes(elf(interpreter=b'/lib/ld-musl-armhf.so.1\0'))
            self.assertEqual(m.inspect_elf(p)['interpreter_class'],'MUSL_LOADER')

    def test_03_nonarm(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'luajit';p.write_bytes(elf(machine=62))
            self.assertEqual(m.inspect_elf(p)['machine'],'OTHER')

    def test_04_malformed_elf_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'luajit';p.write_bytes(b'\x7fELF')
            with self.assertRaises(m.Refused): m.inspect_elf(p)

    def test_05_nonelf_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test';p.write_bytes(b'abc')
            self.assertIsNone(m.inspect_elf(p))

    def test_06_stage_scans_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'rootfs/bin';p.mkdir(parents=True)
            (p/'luajit').write_bytes(elf())
            (p/'other').write_bytes(elf())
            result=m.inventory(Path(d)/'rootfs')
            self.assertEqual(result['counts']['arm_elf_seen'],2)
            self.assertEqual(result['counts']['candidate_elf_count'],1)
            self.assertEqual(result['candidate_elfs'][0]['relative_path'],'bin/luajit')

    def test_07_symlinks_not_followed(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)/'rootfs';base.mkdir()
            (base/'outside').symlink_to('/etc')
            (base/'luajit').symlink_to('/etc/passwd')
            result=m.inventory(base)
            self.assertEqual(result['counts']['symlinks_skipped'],2)
            self.assertEqual(result['counts']['candidate_symlink_names'],1)

    def test_08_missing_stage_fails(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(m.Refused): m.inventory(Path(d)/'absent')

    def test_09_default_does_not_scan(self):
        with patch.object(m,'inventory',side_effect=AssertionError('no scan')):
            with contextlib.redirect_stdout(io.StringIO()) as o:
                self.assertEqual(m.main(['--stage','/not-there']),2)
        self.assertEqual(json.loads(o.getvalue())['hold_category'],
                         'EXPLICIT_LOCAL_STAGE_INSPECTION_OPT_IN_REQUIRED')

    def test_10_explicit_scan_pass_but_not_boot(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)/'rootfs';base.mkdir()
            (base/'luajit').write_bytes(elf())
            with contextlib.redirect_stdout(io.StringIO()) as o:
                self.assertEqual(m.main(['--stage',str(base),
                    '--acknowledge-local-readonly-stage-inspection']),2)
            j=json.loads(o.getvalue())
            self.assertEqual(j['immutable_hold'],'NOT_BOOTABLE')
            self.assertEqual(j['hold_category'],'KO_READER_NATIVE_ENTRYPOINT_SELECTED_FOR_FUTURE_REVIEW')
            self.assertFalse(j['device_execution_performed'])

    def test_11_no_arm_entrypoint(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)/'rootfs';base.mkdir()
            (base/'luajit').write_bytes(elf(machine=62))
            with contextlib.redirect_stdout(io.StringIO()) as o:
                m.main(['--stage',str(base),'--acknowledge-local-readonly-stage-inspection'])
            self.assertEqual(json.loads(o.getvalue())['hold_category'],'NO_ARM_ENTRYPOINT_CANDIDATE_IDENTIFIED')

if __name__=='__main__':unittest.main()
