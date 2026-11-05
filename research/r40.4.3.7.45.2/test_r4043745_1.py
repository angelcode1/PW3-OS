"""R3745.1 synthetic diagnostics only. Never open the actual PW3 stage."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).parent
NAME='R4043745-1-STATIC-PARSER-FAILURE-TRIAGE-READONLY.py'
spec=importlib.util.spec_from_file_location('r3745_1_test',HERE/NAME)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def inner_raise(exc):
    raise exc

class Pinned(unittest.TestCase):
    def test_original_sha(self):
        self.assertEqual(hashlib.sha256((HERE/m.ORIGINAL).read_bytes()).hexdigest(),m.ORIGINAL_SHA256)
    def test_load_pinned_original(self):
        orig=m.load_original(HERE)
        self.assertTrue(callable(orig.audit))
    def test_modified_file_refused(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t)/m.ORIGINAL).write_bytes(b'altered')
            with self.assertRaises(m.Hold):m.load_original(Path(t))
    def test_symlinked_original_refused(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t)/m.ORIGINAL).symlink_to(HERE/m.ORIGINAL)
            with self.assertRaises(m.Hold):m.load_original(Path(t))
    def test_missing_original_refused(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(m.Hold):m.load_original(Path(t))
    def test_root_directory_hold_safe(self):
        with tempfile.TemporaryDirectory() as t:
            out=m.diagnostic(Path(t)/'missing',HERE)
            self.assertEqual(out['result'],'ORIGINAL_R3745_FAILURE_SITE_CLASSIFIED_ONLY')
            self.assertEqual(out['pinned_parent_hold_category'],'ROOTFS_HOLD')
            self.assertFalse(out['boot_authorized'])

class Redaction(unittest.TestCase):
    def helper(self,exc):
        try:inner_raise(exc)
        except Exception as e:return m.summarize_exception(e)
    def test_no_exception_message(self):
        obj=self.helper(ValueError('SECRET_FULL_STAGE_PATH /private/folder/and-symbol'))
        self.assertNotIn('SECRET_FULL_STAGE_PATH',str(obj))
        self.assertNotIn('/private/',str(obj))
        self.assertEqual(obj['exception_class'],'ValueError')
    def test_runtime_unknown_class(self):
        class StrangeCustom(Exception):pass
        self.assertEqual(self.helper(StrangeCustom('secret'))['exception_class'],'OTHER_EXCEPTION_CLASS_REVIEW')
    def test_no_arbitrary_category(self):
        class Stub(Exception):
            category='/Users/secret/a'
        self.assertEqual(self.helper(Stub())['pinned_parent_hold_category'],'NONE_OR_UNRECOGNIZED')
    def test_known_category_preserved(self):
        self.assertEqual(self.helper(m.Hold('BOUNDS_REVIEW_HOLD'))['pinned_parent_hold_category'],'BOUNDS_REVIEW_HOLD')
    def test_code_category_parent(self):
        class ParentHold(Exception):
            code='PARENT_BOUNDS_HOLD'
        self.assertEqual(self.helper(ParentHold())['pinned_parent_hold_category'],'PARENT_BOUNDS_HOLD')
    def test_untrusted_frame_suppressed(self):
        out=self.helper(RuntimeError('super_secret_function'))
        self.assertEqual(out['pinned_call_frames'],[])
        self.assertEqual(out['last_pinned_frame']['source'],'UNKNOWN')
    def test_no_traceback(self):
        out=self.helper(TypeError('secret'))
        self.assertFalse(out['exception_message_or_traceback_exported'])
        self.assertNotIn('traceback',str(out).lower().replace('exception_message_or_traceback_exported',''))
    def test_boot_never(self):
        out=self.helper(OSError('secret'))
        self.assertFalse(out['boot_authorized'])
        self.assertEqual(out['immutable_hold'],'NOT_BOOTABLE')

class OriginalFailure(unittest.TestCase):
    def test_exception_from_original_error_shape(self):
        class FakeOriginal:
            def load_parent(self,_):return self
            def audit(self,*_):return inner_raise(KeyError('private-secret-name'))
        out=m.diagnostic(Path('/fake'),HERE,FakeOriginal())
        self.assertEqual(out['result'],'ORIGINAL_R3745_FAILURE_SITE_CLASSIFIED_ONLY')
        self.assertEqual(out['exception_class'],'KeyError')
        self.assertNotIn('private-secret-name',str(out))
    def test_parent_hold_indicated(self):
        class ParentError(Exception):
            category='PARENT_IO_HOLD'
        class FakeOriginal:
            def load_parent(self,_):raise ParentError('private')
        out=m.diagnostic(Path('/fake'),HERE,FakeOriginal())
        self.assertEqual(out['pinned_parent_hold_category'],'PARENT_IO_HOLD')
    def test_original_success_remains_hold(self):
        class FakeOriginal:
            def load_parent(self,_):return self
            def audit(self,*_):return {'result':'WEAK_PLT_INITIAL_WORD_GEOMETRY_STATIC_ONLY'}
        out=m.diagnostic(Path('/fake'),HERE,FakeOriginal())
        self.assertEqual(out['result'],'HOLD')
        self.assertEqual(out['hold_category'],'ORIGINAL_R3745_EXCEPTION_NOT_REPRODUCED_HOLD')
    def test_original_other_remains_hold(self):
        class FakeOriginal:
            def load_parent(self,_):return self
            def audit(self,*_):return {'result':'OTHER'}
        out=m.diagnostic(Path('/fake'),HERE,FakeOriginal())
        self.assertEqual(out['hold_category'],'ORIGINAL_R3745_DIFFERENT_RESULT_HOLD')
    def test_deterministic(self):
        class FakeOriginal:
            def load_parent(self,_):return self
            def audit(self,*_):raise AttributeError('private')
        a=m.diagnostic(Path('/fake'),HERE,FakeOriginal())
        b=m.diagnostic(Path('/fake'),HERE,FakeOriginal())
        self.assertEqual(a,b)

class Frames(unittest.TestCase):
    def test_generated_frame_not_exported(self):
        with self.assertRaises(ZeroDivisionError) as ctx:
            1//0
        self.assertEqual(m.sanitized_frames(ctx.exception),[])
    def test_source_identifiers_static(self):
        self.assertEqual(m.ALLOWED_CODE_FILES[m.ORIGINAL],'R3745')
    def test_max_frames_bounded(self):
        self.assertLessEqual(len(m.ALLOWED_CODE_FILES),20)
    def test_synthetic_hold_classification(self):
        obj=m.diagnostic(Path('/does-not-exist'),HERE)
        self.assertEqual(obj['exception_class'],'Hold')
        self.assertEqual(obj['pinned_parent_hold_category'],'ROOTFS_HOLD')
        self.assertTrue(all(f['source'] in m.ALLOWED_CODE_FILES.values() for f in obj['pinned_call_frames']))

if __name__=='__main__':unittest.main()
