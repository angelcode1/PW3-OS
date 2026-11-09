"""Host-only synthetic tests for R3877.91.5 report consistency checker."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("r915_verify", Path(__file__).with_name("verify_report.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def fixture():
    return {
        "milestone":"R3877.91.5",
        "result":"HOST_RELOCATION_SCOPE_MODEL_COMPLETE",
        "immutable_hold":"NOT_BOOTABLE",
        "mode":"HOST_ONLY_NO_STAGED_EXECUTION",
        "gnu_boundary_elfs":64,
        "gnu_library_edges_modeled":181,
        "relocation_entries_inspected":68516,
        "relocation_imports_unique_by_object":5114,
        "potential_model_scope_gaps_total":412,
        "potential_model_scope_gaps_not_shown":352,
        "objects_without_relocation_sections":0,
        "device_accessed":False,
        "stage_modified":False,
        "staged_elf_executed":False,
        "actual_loader_resolution_verified":False,
        "symbol_binding_verified_by_runtime":False,
        "model_validation_only":True,
        "parser_errors":[],
        "status_counts":dict(mod.CATEGORIES),
        "potential_model_scope_gaps":[{"symbol":"luaL_checkinteger"} for _ in range(60)],
    }

class CheckEvidence(unittest.TestCase):
    def test_valid_synthetic_report(self):
        self.assertEqual(mod.problems(fixture()), [])
    def test_rejects_bootable_claim(self):
        x=fixture();x["immutable_hold"]="BOOTABLE"
        self.assertTrue(mod.problems(x))
    def test_rejects_changed_category_counts(self):
        x=fixture();x["status_counts"]["NOT_IN_DIRECT_NEEDED_SCOPE"]=411
        self.assertTrue(mod.problems(x))
    def test_rejects_device_access(self):
        x=fixture();x["device_accessed"]=True
        self.assertTrue(mod.problems(x))
    def test_rejects_non_lua_visible_example(self):
        x=fixture();x["potential_model_scope_gaps"][0]["symbol"]="other"
        self.assertTrue(mod.problems(x))

if __name__ == "__main__":
    unittest.main()
