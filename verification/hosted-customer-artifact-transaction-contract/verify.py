#!/usr/bin/env python3
"""Check this proposal packet, or explicitly run its future implementation suite.

Packet validation is documentation evidence only. No planned product case is
reported as passed unless an actual implementation suite exists and is run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
DOC = ROOT / "docs/hosted-customer-artifact-transaction-contract.md"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-observed-source", action="store_true")
    parser.add_argument("--run-implementation", action="store_true")
    args = parser.parse_args()
    matrix = json.loads((PACKET / "matrix.json").read_text())
    observed = json.loads((PACKET / "observed-inputs.json").read_text())
    assert matrix["kind"] == "implementation_test_plan_not_test_results"
    assert matrix["schema"] == observed["schema"] == 1
    assert matrix["source_revision"] == observed["base_revision"]
    assert re.fullmatch(r"[0-9a-f]{40}", matrix["source_revision"])
    cases = matrix["required_tests"]
    assert [case["id"] for case in cases] == [f"C{n:02}" for n in range(1, 36)]
    groups = set()
    for case in cases:
        assert case["status"] == "pending_implementation"
        assert case["test_name"].startswith(f"contract {case['id']}: ")
        assert case["assertion"] and case["environment"]
        relative = Path(case["test_file"])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert str(relative).startswith("test/mixer_hosted/")
        assert relative.suffix == ".exs"
        groups.add(case["group"])
    assert groups == {"facade", "storage", "codec", "read"}
    expected_files = list(dict.fromkeys(case["test_file"] for case in cases))
    assert matrix["implementation_command"] == [
        "mix", "test", *expected_files, "--seed", "0", "--warnings-as-errors"
    ]
    assert len(observed["inputs"]) == 21
    for item in observed["inputs"]:
        assert re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
        assert not Path(item["path"]).is_absolute() and ".." not in Path(item["path"]).parts
    if args.check_observed_source:
        drift = [item["path"] for item in observed["inputs"]
                 if hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest()
                 != item["sha256"]]
        assert not drift, f"Observed source changed after review: {drift}"
    for path in [DOC, PACKET / "matrix.json", PACKET / "observed-inputs.json", Path(__file__)]:
        raw = path.read_bytes()
        assert raw.endswith(b"\n"), f"Missing final newline: {path.name}"
        assert all(line == line.rstrip(b" \t") for line in raw.splitlines()), path.name
    if args.run_implementation:
        missing = [name for name in expected_files if not (ROOT / "hosted" / name).is_file()]
        if missing:
            print(json.dumps({"status": "pending_implementation", "missing_suites": missing,
                              "product_cases_passed": 0}, indent=2))
            return 2
        # A declared case name is a coverage inventory check only. Actual runtime
        # assertions and a real PostgreSQL fixture remain review requirements.
        missing_cases = [case["id"] for case in cases if case["test_name"] not in
                         (ROOT / "hosted" / case["test_file"]).read_text()]
        if missing_cases:
            print(json.dumps({"status": "pending_implementation", "missing_cases": missing_cases,
                              "product_cases_passed": 0}, indent=2))
            return 2
        return subprocess.run(matrix["implementation_command"], cwd=ROOT / "hosted").returncode
    print(json.dumps({"status": "contract_packet_valid", "planned_cases": len(cases),
                      "product_cases_passed": 0,
                      "document_sha256": hashlib.sha256(DOC.read_bytes()).hexdigest(),
                      "observed_source_checked": args.check_observed_source}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, ValueError, OSError) as exc:
        print(f"Contract packet invalid: {exc}", file=sys.stderr)
        raise SystemExit(1)
