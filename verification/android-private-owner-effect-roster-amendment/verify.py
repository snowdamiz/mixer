#!/usr/bin/env python3
"""Verify custody and exact roster-only classification; no product tests."""
import ast
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
V1_IDS = {"NativeRenderer:L60:C234:1", "NativeRenderer:L61:C242:1",
          "NativeRenderer:L62:C149:1", "NativeRenderer:L62:C454:2", "NativeRenderer:L62:C509:3"}


def ident(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def main():
    receipt = json.loads((BASE / "receipt.json").read_text())
    checks = []

    def check(name, value):
        checks.append({"name": name, "passed": bool(value)})

    for seal in receipt["prior_seals"]:
        path = ROOT / seal["path"]
        data = path.read_bytes()
        check("prior seal binding: " + seal["label"], ident(data)["sha256"] == seal["sha256"])
        manifest = json.loads(data)
        member_base = path.parent if seal["member_paths_relative_to_manifest"] else ROOT
        for name, expected in manifest["files"].items():
            p = member_base / name
            check("preserved member: " + seal["label"] + ":" + name, p.is_file() and not p.is_symlink() and ident(p.read_bytes()) == expected)
        ignored = {path}
        if seal["label"] in ("original-proposal", "correction-1"):
            ignored.add(path.parent / "handoff.sha256")
        excluded_subtree = path.parent / "correction-1" if seal["label"] in ("original-proposal", "original-review") else None
        observed = {p.resolve() for p in path.parent.rglob("*") if p.is_file() and p not in ignored
                    and not (excluded_subtree is not None and p.is_relative_to(excluded_subtree))}
        expected_inside = {(member_base / name).resolve() for name in manifest["files"]
                           if (member_base / name).is_relative_to(path.parent)}
        check("prior directory closure preserved: " + seal["label"], observed == expected_inside)
    for name, expected in receipt["inputs"].items():
        check("input snapshot: " + name, ident((BASE / "inputs" / name).read_bytes()) == expected)
        check("unchanged current input: " + name, ident((ROOT / name).read_bytes()) == expected)
    prior_path = "verification/android-private-owner-effect-integration-proposal/correction-1/required-host-roster.json"
    before = json.loads((BASE / "inputs" / prior_path).read_text())
    after_data = (BASE / "required-host-roster.json").read_bytes()
    after = json.loads(after_data)
    check("amended roster binding", ident(after_data) == receipt["amended_roster"])
    old_rows = before["baseline_callback_barriers"]
    old = {r["id"]: r for r in old_rows}
    v2 = after["baseline_callback_barriers"]
    v1 = after["v1_compile_baseline_only"]
    check("189 distinct historical IDs", len(old_rows) == len(old) == 189)
    check("exact five V1 classifications", {r["id"] for r in v1} == V1_IDS and len(v1) == 5)
    check("exact 184 V2 IDs in prior order", [r["id"] for r in v2] == [r["id"] for r in old_rows if r["id"] not in V1_IDS] and len(v2) == 184)
    check("no other prior roster field changed", all(after[k] == v for k, v in before.items() if k != "baseline_callback_barriers"))
    check("only expected additive fields", set(after) - set(before) == {"v1_compile_baseline_only", "amendment"})
    for r in v2:
        check("entire V2 record unchanged: " + r["id"], r == old[r["id"]])
    for r in v1:
        historical = old[r["id"]]
        check("V1 anchor unchanged: " + r["id"], all(r[k] == v for k, v in historical.items() if k != "required_cases"))
        check("V1 historical evidence retained: " + r["id"], r["historical_record_sha256"] == ident(canonical(historical))["sha256"])
        check("no V2 requirements on V1: " + r["id"], r["V2_semantic_requirements"] == [] and "required_cases" not in r and r["classification"] == "V1 compile/baseline-only")
    b = after["closures"]["B-concrete-renderer-views"]
    check("14 actual closure B subjects retained", len(b["actual_production_sources"]) == 14 and b["actual_production_sources"] == before["closures"]["B-concrete-renderer-views"]["actual_production_sources"])
    check("73 exact closure B substitutes retained", len(b["substitutes"]) == 73 and b["substitutes"] == before["closures"]["B-concrete-renderer-views"]["substitutes"])
    check("explicit ID list exact", (BASE / "v2-semantic-barrier-ids.txt").read_text().splitlines() == [r["id"] for r in v2])
    for r in old_rows:
        raw = (BASE / "inputs" / r["source"]).read_text().splitlines()[r["line"] - 1] if r["source"] in receipt["inputs"] else (ROOT / "verification/android-private-owner-effect-integration-proposal/correction-1/inputs" / r["source"]).read_text().splitlines()[r["line"] - 1]
        check("historical source anchor retained: " + r["id"], raw.strip() == r["source_line"] and raw[r["column"] - 1:].startswith(r["expression"]))
    proof = json.loads((BASE / "classification-proof.json").read_text())
    check("proof exact changed IDs", set(proof["classified_V1_ids"]) == V1_IDS)
    check("proof all V2 records equal", len(proof["unchanged_V2_records"]) == 184 and all(r["full_record_equal"] and r["prior_sha256"] == r["amended_sha256"] for r in proof["unchanged_V2_records"]))
    check("proof all five anchors equal", len(proof["V1_anchor_records"]) == 5 and all(r["anchor_equal"] for r in proof["V1_anchor_records"]))
    check("proof noninventory fields equal", proof["prior_noninventory_fields_sha256"] == proof["amended_noninventory_preexisting_fields_sha256"])
    doc_data = (ROOT / receipt["amendment_document"]["path"]).read_bytes()
    check("amendment document binding", ident(doc_data) == {k: receipt["amendment_document"][k] for k in ("bytes", "sha256")})
    for name in ("capture.py", "verify.py", "seal.py"):
        ast.parse((BASE / name).read_text(), filename=name)
        check("custody script parses: " + name, True)
    result = {"schema": 1, "scope": "bounded-custody-and-roster-classification-only",
              "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python_version": sys.version,
              "checks": checks, "passed": sum(c["passed"] for c in checks), "failed": sum(not c["passed"] for c in checks),
              "product_tests_run": False, "native_or_cross_compile_run": False,
              "implementation_or_contract_acceptance": False}
    (BASE / "source-only-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("scope", "passed", "failed", "product_tests_run")}, sort_keys=True))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
