import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SRC = HERE / 'R4043762-PUBLIC-WARIO-KERNEL-REFERENCE-READONLY.py'
spec = importlib.util.spec_from_file_location('r3762_fixed', SRC)
r3762 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r3762)

def reference():
    return (HERE / 'imx60_wario_defconfig').read_bytes()

class MixedCaseConfigurationRegressions(unittest.TestCase):
    def test_real_reference_vfpv3_enabled_exact_case(self):
        fields = r3762.parse_configuration(reference())
        self.assertEqual(fields.get('CONFIG_VFPv3'), 'ENABLED')
        groups, drift = r3762.report_feature_groups(fields)
        self.assertEqual(groups['CPU_INSTRUCTION_SET']['CONFIG_VFPv3'], 'ENABLED')
        self.assertEqual(drift, 0)

    def test_mixed_case_disabled_option_is_not_undeclared(self):
        original = reference()
        self.assertEqual(original.count(b'CONFIG_VFPv3=y'), 1)
        changed = original.replace(b'CONFIG_VFPv3=y', b'# CONFIG_VFPv3 is not set')
        fields = r3762.parse_configuration(changed)
        self.assertEqual(fields.get('CONFIG_VFPv3'), 'NOT_SET')
        groups, drift = r3762.report_feature_groups(fields)
        self.assertEqual(groups['CPU_INSTRUCTION_SET']['CONFIG_VFPv3'], 'NOT_SET')
        self.assertGreater(drift, 0)

    def test_uppercase_variant_cannot_substitute_for_vfpv3(self):
        original = reference()
        changed = original.replace(b'CONFIG_VFPv3=y', b'CONFIG_VFPV3=y')
        fields = r3762.parse_configuration(changed)
        self.assertEqual(fields.get('CONFIG_VFPV3'), 'ENABLED')
        self.assertNotEqual(fields.get('CONFIG_VFPv3'), 'ENABLED')
        _, drift = r3762.report_feature_groups(fields)
        self.assertGreater(drift, 0)

    def test_mixed_case_conflicting_duplicate_is_rejected(self):
        original = reference()
        changed = original + b'\n# CONFIG_VFPv3 is not set\n'
        with self.assertRaises(r3762.Hold):
            r3762.parse_configuration(changed)
