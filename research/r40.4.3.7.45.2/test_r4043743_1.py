"""R3743.1 synthetic regression: source/provider overlap is real, not fatal.

Only temporary synthetic files, never the R13 stage. NOT_BOOTABLE.
"""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r3743_1_synthetic', HERE/'R4043743-1-OVERLAP-AWARE-EXPORT-SURVEY-READONLY.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
old = m.load_original(HERE)
tspec = importlib.util.spec_from_file_location('r3742_fixture_for_r3743_1', HERE/'test_r4043742.py')
t42 = importlib.util.module_from_spec(tspec)
tspec.loader.exec_module(t42)


def fixture_stage(root, *, overlap=True):
    """12 source filenames, six provider filenames, one deliberately shared."""
    (root/'bin').mkdir()
    (root/'lib').mkdir()
    sources = []
    providers = []
    for i in range(12):
        p = root/'bin'/f'elf-{i:02d}'
        p.write_bytes(b'fixture-source')
        sources.append(p)
    if overlap:
        providers.append(sources[0])
    for i in range(6 if not overlap else 5):
        p = root/'lib'/f'provider-{i:02d}'
        p.write_bytes(b'fixture-provider')
        providers.append(p)
    return sources, providers


def parser_for(names=b'weak_unresolved'):
    def parser(_):
        return {'symbols':[{'name':names,'defined':True,'binding':1,'visibility':0}]}
    parser.hold_types=(ValueError,)
    return parser


class Pins(unittest.TestCase):
    def test_original_sha_pin(self):
        self.assertEqual(hashlib.sha256((HERE/m.ORIGINAL).read_bytes()).hexdigest(),m.ORIGINAL_SHA256)
    def test_original_parent_sha_pin(self):
        self.assertEqual(old.PARENT_SHA256, '4d118c490746d974e9f197db3260a3cb54f2b24b26ecebf82b4a3580b86715ed')
    def test_original_import(self):
        self.assertTrue(callable(old.bounded_elf_inventory))
    def test_missing_original_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(m.Hold) as ctx:m.load_original(Path(d))
            self.assertEqual(ctx.exception.category,'ORIGINAL_R3743_SOURCE_INVALID_HOLD')
    def test_tampered_original_refused(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/m.ORIGINAL).write_text('tampered')
            with self.assertRaises(m.Hold) as ctx:m.load_original(Path(d))
            self.assertEqual(ctx.exception.category,'ORIGINAL_R3743_SOURCE_SHA_HOLD')


class OverlapFixture(unittest.TestCase):
    def test_historical_original_overlap_hold_reproduced(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,prov=fixture_stage(root)
            with self.assertRaises(old.Hold) as ctx:
                old.bounded_elf_inventory(root,t42.p26,src,prov,parser_for())
            self.assertEqual(ctx.exception.category,'SOURCE_PROVIDER_OVERLAP_HOLD')
    def test_new_inventory_accepts_shared_file_and_excludes_it_once(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,prov=fixture_stage(root)
            (root/'extra').write_bytes(t42.t40.fixture())
            exports,counters=m.overlap_aware_inventory(root,t42.p26,src,prov,parser_for(),old)
            self.assertEqual(counters['source_provider_overlap_regular_files'],1)
            self.assertEqual(counters['excluded_unique_source_or_provider_regular_files'],17)
            self.assertEqual(counters['other_regular_stage_files_seen'],1)
            self.assertEqual(counters['additional_dynamic_elf_parsed'],1)
            self.assertEqual(exports[b'weak_unresolved'],{root/'extra'})
    def test_shared_source_and_provider_never_classified_as_additional(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,prov=fixture_stage(root)
            called=[]
            def parser(path):called.append(path);return {'symbols':[]}
            parser.hold_types=(ValueError,)
            exports,count=m.overlap_aware_inventory(root,t42.p26,src,prov,parser,old)
            self.assertEqual(called,[])
            self.assertFalse(exports)
            self.assertEqual(count.get('additional_dynamic_elf_parsed',0),0)
    def test_nonoverlap_refused_to_preserve_historical_hold(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,prov=fixture_stage(root,overlap=False)
            with self.assertRaises(m.Hold) as ctx:
                m.overlap_aware_inventory(root,t42.p26,src,prov,parser_for(),old)
            self.assertEqual(ctx.exception.category,'ORIGINAL_SOURCE_PROVIDER_OVERLAP_NOT_REPRODUCED_HOLD')
    def test_duplicate_source_entry_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,prov=fixture_stage(root)
            src[-1]=src[0]
            with self.assertRaises(m.Hold) as ctx:
                m.overlap_aware_inventory(root,t42.p26,src,prov,parser_for(),old)
            self.assertEqual(ctx.exception.category,'SOURCE_OR_PROVIDER_DUPLICATE_HOLD')
    def test_wrong_count_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,prov=fixture_stage(root)
            with self.assertRaises(m.Hold) as ctx:
                m.overlap_aware_inventory(root,t42.p26,src[:-1],prov,parser_for(),old)
            self.assertEqual(ctx.exception.category,'SOURCE_PROVIDER_COUNT_CHANGED_HOLD')
    def test_outside_stage_source_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'root';root.mkdir();src,prov=fixture_stage(root)
            out=Path(d)/'outside';out.write_bytes(b'x')
            src[1]=out
            with self.assertRaises(m.Hold) as ctx:
                m.overlap_aware_inventory(root,t42.p26,src,prov,parser_for(),old)
            self.assertEqual(ctx.exception.category,'SOURCE_PROVIDER_OUTSIDE_ROOT_HOLD')
    def test_symlinked_excluded_source_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,prov=fixture_stage(root)
            src[1].unlink();src[1].symlink_to(src[0])
            with self.assertRaises(m.Hold) as ctx:
                m.overlap_aware_inventory(root,t42.p26,src,prov,parser_for(),old)
            self.assertEqual(ctx.exception.category,'SOURCE_PROVIDER_REGULAR_FILE_CHANGED_HOLD')
    def test_parser_refusal_preserved_not_no_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,prov=fixture_stage(root)
            (root/'extra').write_bytes(t42.t40.fixture())
            def parser(_):raise ValueError('synthetic unsupported ELF')
            parser.hold_types=(ValueError,)
            exports,counts=m.overlap_aware_inventory(root,t42.p26,src,prov,parser,old)
            self.assertFalse(exports)
            self.assertEqual(counts['additional_dynamic_elf_parser_refusals'],1)
    def test_unexpected_parser_error_propagates(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,prov=fixture_stage(root)
            (root/'extra').write_bytes(t42.t40.fixture())
            def parser(_):raise RuntimeError('bad program')
            parser.hold_types=(ValueError,)
            with self.assertRaises(RuntimeError):
                m.overlap_aware_inventory(root,t42.p26,src,prov,parser,old)
    def test_extra_file_symlink_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,prov=fixture_stage(root)
            (root/'extra').write_bytes(t42.t40.fixture())
            (root/'link').symlink_to('extra')
            exports,counts=m.overlap_aware_inventory(root,t42.p26,src,prov,parser_for(),old)
            self.assertEqual(counts['additional_dynamic_elf_parsed'],1)
            self.assertEqual(len(exports[b'weak_unresolved']),1)
    def test_aggregates_contain_no_paths_or_symbols(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,prov=fixture_stage(root)
            (root/'very_private').write_bytes(t42.t40.fixture())
            exports,counts=m.overlap_aware_inventory(root,t42.p26,src,prov,parser_for(b'private_symbol'),old)
            self.assertNotIn('very_private',str(counts))
            self.assertNotIn('private_symbol',str(counts))
            self.assertEqual(counts['source_provider_overlap_regular_files'],1)
    def test_diff_from_source_set_union_equation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src,prov=fixture_stage(root)
            _,counts=m.overlap_aware_inventory(root,t42.p26,src,prov,parser_for(),old)
            self.assertEqual(counts['excluded_unique_source_or_provider_regular_files'],12+6-1)


if __name__=='__main__':unittest.main()
