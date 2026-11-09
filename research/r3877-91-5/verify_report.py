#!/usr/bin/env python3
"""Read-only, narrow R3877.91.5 host report consistency check.

This checks the JSON evidence's internal accounting. It does NOT audit ELF
bytes, verify external provenance, execute any stage content or authorize boot.
"""
import json
from pathlib import Path
import sys

CATEGORIES = {
    "MODEL_DIRECT_DEP_MATCH": 1107,
    "MODEL_MATCH": 3266,
    "NOT_IN_DIRECT_NEEDED_SCOPE": 412,
    "WEAK_OPTIONAL_IMPORT": 329,
}

def problems(report):
    errors = []
    expected = {
        "milestone": "R3877.91.5",
        "result": "HOST_RELOCATION_SCOPE_MODEL_COMPLETE",
        "immutable_hold": "NOT_BOOTABLE",
        "mode": "HOST_ONLY_NO_STAGED_EXECUTION",
        "gnu_boundary_elfs": 64,
        "gnu_library_edges_modeled": 181,
        "relocation_entries_inspected": 68516,
        "relocation_imports_unique_by_object": 5114,
        "potential_model_scope_gaps_total": 412,
        "potential_model_scope_gaps_not_shown": 352,
        "objects_without_relocation_sections": 0,
        "device_accessed": False,
        "stage_modified": False,
        "staged_elf_executed": False,
        "actual_loader_resolution_verified": False,
        "symbol_binding_verified_by_runtime": False,
        "model_validation_only": True,
        "parser_errors": [],
        "status_counts": CATEGORIES,
    }
    for k, value in expected.items():
        if report.get(k) != value:
            errors.append(k + ": expected observed value differs")
    if sum(report.get("status_counts", {}).values()) != 5114:
        errors.append("symbol classification sum differs")
    examples = report.get("potential_model_scope_gaps")
    if not isinstance(examples, list) or len(examples) != 60:
        errors.append("expected 60 displayed diagnostic examples")
    elif not all(isinstance(item, dict) and isinstance(item.get("symbol"), str) for item in examples):
        errors.append("invalid displayed diagnostic examples")
    if not errors and not all(x["symbol"].startswith(("lua_", "luaL_")) for x in examples):
        errors.append("visible examples are not all Lua C API symbols")
    return errors

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: verify_report.py <r3877_91_5_host.json>", file=sys.stderr)
        return 2
    try:
        source = Path(argv[0]).read_text(encoding="utf-8").replace("\u00a0", " ")
        report = json.loads(source[source.index("{"):source.rindex("}") + 1])
    except (OSError, ValueError, KeyError) as exc:
        print("HOLD: report unreadable:", type(exc).__name__, file=sys.stderr)
        return 2
    issues = problems(report)
    if issues:
        print("HOLD: discrepancies:", "; ".join(issues))
        return 2
    print("PASS: R3877.91.5 report shape and accounting match recorded evidence")
    print("NOT_BOOTABLE; no runtime or source authenticity verification performed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
