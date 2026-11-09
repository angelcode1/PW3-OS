"""Synthetic host-only R3877.78 tests; no downloads or Kindle connections."""
from contextlib import redirect_stdout
from pathlib import Path
import hashlib
import io
import json
import struct
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch
import pw3_r3877_78_musl_runtime as m


def arm_elf(*, loader=False, needed=b'libc.musl-armhf.so.1\0'):
    contents = bytearray(1024)
    contents[:16] = b'\x7fELF' + bytes([1, 1, 1, 0]) + bytes(8)
    phnum = 1 if loader else 3
    struct.pack_into('<HHIIIIIHHHHHH', contents, 16, 3, 40, 1, 0x1000,
                     52, 0, 0x05000400, 52, 32, phnum, 0, 0, 0)
    if loader:
        struct.pack_into('<8I', contents, 52, m.PT_LOAD, 0, 0, 0, 1024, 1024, 5, 4096)
    else:
        struct.pack_into('<8I', contents, 52, m.PT_LOAD, 0x100, 0x1000, 0, 0x200, 0x200, 5, 4096)
        interp = b'/lib/ld-musl-armhf.so.1\0'
        contents[0x130:0x130+len(interp)] = interp
        struct.pack_into('<8I', contents, 84, m.PT_INTERP, 0x130, 0x1030, 0, len(interp), len(interp), 4, 1)
        struct.pack_into('<8I', contents, 116, m.PT_DYNAMIC, 0x180, 0x1080, 0, 32, 32, 4, 4)
        struct.pack_into('<II', contents, 0x180, m.DT_STRTAB, 0x10c0)
        struct.pack_into('<II', contents, 0x188, m.DT_STRSZ, len(needed)+1)
        struct.pack_into('<II', contents, 0x190, m.DT_NEEDED, 1)
        contents[0x1c0:0x1c0+len(needed)+1] = b'\0' + needed
    return bytes(contents)


def gzip_tar(files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tf:
        for name, data in files.items():
            if isinstance(data, str):
                info = tarfile.TarInfo(name)
                info.type = tarfile.SYMTYPE
                info.linkname = data
                tf.addfile(info)
            else:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class Tests(unittest.TestCase):
    def test_01_loader_abi(self):
        x = m.elf_metadata(arm_elf(loader=True))
        self.assertEqual((x['type'],x['interp'],x['hard_float']), (3,None,True))

    def test_02_busybox_needed(self):
        blob=arm_elf()
        x=m.elf_metadata(blob)
        self.assertEqual(x['interp'], '/lib/ld-musl-armhf.so.1')
        self.assertEqual(m.needed_libraries(blob,x), ['libc.musl-armhf.so.1'])

    def test_03_wrong_cpu(self):
        b=bytearray(arm_elf())
        struct.pack_into('<H', b, 18, 62)
        with self.assertRaises(m.Refused):m.elf_metadata(bytes(b))

    def test_04_soft_float(self):
        b=bytearray(arm_elf())
        struct.pack_into('<I', b, 36, 0x05000000)
        with self.assertRaises(m.Refused):m.elf_metadata(bytes(b))

    def test_05_missing_interp(self):
        with self.assertRaises(m.Refused):m.needed_libraries(arm_elf(loader=True),m.elf_metadata(arm_elf(loader=True)))

    def test_06_prepare_three_regular_files(self):
        tar=gzip_tar({'lib/ld-musl-armhf.so.1':arm_elf(loader=True),'bin/busybox':arm_elf()})
        packed,files,needed=m.prepare(tar)
        self.assertEqual(sorted(files), ['busybox','ld-musl-armhf.so.1','libc.musl-armhf.so.1'])
        self.assertEqual(needed,['libc.musl-armhf.so.1'])
        with tarfile.open(fileobj=io.BytesIO(packed),mode='r:') as tf:
            self.assertTrue(all(x.isfile() for x in tf.getmembers()))
            self.assertEqual(len(tf.getmembers()),3)

    def test_07_symlink_lib(self):
        tar=gzip_tar({'lib/ld-musl-armhf.so.1':'libc.musl-armhf.so.1',
                      'lib/libc.musl-armhf.so.1':arm_elf(loader=True),
                      'bin/busybox':arm_elf()})
        self.assertEqual(len(m.prepare(tar)[1]),3)

    def test_08_symlink_escape_refused(self):
        tar=gzip_tar({'lib/ld-musl-armhf.so.1':'../../etc/passwd','bin/busybox':arm_elf()})
        with self.assertRaises(m.Refused):m.prepare(tar)

    def test_09_wrong_dependency_refused(self):
        tar=gzip_tar({'lib/ld-musl-armhf.so.1':arm_elf(loader=True),
                      'bin/busybox':arm_elf(needed=b'libc.so.6\0')})
        with self.assertRaises(m.Refused):m.prepare(tar)

    def test_10_pinned_sha(self):
        data=gzip_tar({'bin/busybox':arm_elf()})
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/m.ROOTFS_NAME
            p.write_bytes(data)
            with self.assertRaises(m.Refused):m.read_pinned_archive(p)
            with patch.object(m,'ROOTFS_SHA256',hashlib.sha256(data).hexdigest()):
                self.assertEqual(m.read_pinned_archive(p),data)

    def test_11_no_optin_no_ssh_or_tar(self):
        with patch.object(m,'read_pinned_archive',side_effect=AssertionError('must not read')):
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(m.main([]),2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'DEVICE_MUSL_TEST_NOT_AUTHORIZED')

    def test_12_invalid_target(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(m.main(['--acknowledge-single-process-mac-and-kindle-tmpfs',
                                      '--target','root@bad;ls']),2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'TARGET_OR_PORT_INVALID')

    def test_13_ssh_mock_pass(self):
        a=Mock(returncode=0,stdout=m.MARKER.encode(),stderr=b'')
        with patch.object(m,'read_pinned_archive',return_value=b'fake'), \
             patch.object(m,'prepare',return_value=(b'tar',
                 {'ld-musl-armhf.so.1':b'elf','libc.musl-armhf.so.1':b'elf','busybox':b'busy'},
                 ['libc.musl-armhf.so.1'])):
            with redirect_stdout(io.StringIO()) as out:
                code=m.main(['--acknowledge-single-process-mac-and-kindle-tmpfs'],
                            runner=lambda *_a,**_k:a)
        j=json.loads(out.getvalue())
        self.assertEqual(code,0)
        self.assertTrue(j['single_process_musl_verified'])
        self.assertEqual(j['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(j['physical_restore_verified'])

    def test_14_ssh_mock_failure(self):
        a=Mock(returncode=42,stdout=b'',stderr=b'')
        with patch.object(m,'read_pinned_archive',return_value=b'fake'), \
             patch.object(m,'prepare',return_value=(b'tar',
                 {'ld-musl-armhf.so.1':b'elf','libc.musl-armhf.so.1':b'elf','busybox':b'busy'},
                 ['libc.musl-armhf.so.1'])):
            with redirect_stdout(io.StringIO()) as out:
                code=m.main(['--acknowledge-single-process-mac-and-kindle-tmpfs'],
                            runner=lambda *_a,**_k:a)
        self.assertEqual(code,2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'NO_EXECUTABLE_EXISTING_TMPFS')

    def test_15_remote_no_persistent_operations(self):
        s=m.remote_script({'ld-musl-armhf.so.1':b'x', 'libc.musl-armhf.so.1':b'x','busybox':b'y'})
        self.assertNotIn('mount -',s)
        self.assertNotIn('chroot',s)
        self.assertNotIn('mmcblk',s)
        self.assertIn('cleanup || exit 51',s)
        self.assertIn('R3877_78_MUSL_BUSYBOX_OK',s)

    def test_16_no_private_hash_output(self):
        with redirect_stdout(io.StringIO()) as out:
            m.main([])
        self.assertNotIn(m.ROOTFS_SHA256,out.getvalue())

if __name__=='__main__':unittest.main()
