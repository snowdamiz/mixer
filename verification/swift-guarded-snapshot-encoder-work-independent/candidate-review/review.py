#!/usr/bin/env python3
"""Compact source-custody, independent geometry and additive ledger controls."""
from pathlib import Path
import datetime
import hashlib
import json
import runpy
import subprocess
import sys

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
OWN = OUT.parent
REPO = OWN.parent.parent
AUDIT = REPO / "verification/swift-guarded-snapshot-encoder-work-audit"
ENC = REPO / "verification/swift-guarded-snapshot-encoder-implementation"
PRE = OWN / "preaccess"
findings = []
controls = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def member(path, relative_to):
    data = path.read_bytes()
    return {"path": str(path.relative_to(relative_to)), "bytes": len(data), "sha256": sha(data)}


def check(name, condition, detail=None):
    assert condition, (name, detail)
    controls.append({"name": name, "pass": True, "detail": detail})


def verify_seal(base, expected):
    raw = (base / "seal.json").read_bytes()
    assert sha(raw) == expected
    seal = json.loads(raw)
    assert len(seal["members"]) == seal["member_count"]
    for row in seal["members"]:
        actual = member(base / row["path"], base)
        assert actual == row, (actual, row)
    return {"seal": member(base / "seal.json", REPO), "member_count": len(seal["members"]), "member_bytes": sum(row["bytes"] for row in seal["members"])}


if __name__ == "__main__":
    assert not (OUT / "seal.json").exists(), "review seal is immutable"
    release = REPO / "verification/swift-semantic-adapter-root-review/guarded-snapshot-encoder-work-independent-release.json"
    assert sha(release.read_bytes()) == "c89dadb70bd9cbc4f350b873ca6cb68eb189fe196e6afb881bd0e951bc6d025d"
    producer_before = verify_seal(AUDIT, "ef906a8ec95d956898347bca67658ffac82a506be66b204d35893c23acfcfdd0")
    preaccess = verify_seal(PRE, "1ae47e24a54b8a08d9019b7498db336a189ec0f1ec0ec7e550ffe4f074774997")
    sources = json.loads((AUDIT / "input-custody.json").read_bytes())["reads"]
    read_sources = []
    for row in sources:
        if row["path"].startswith(str(ENC.relative_to(REPO)) + "/source/vm/") or row["path"].endswith("/host/encoder.rs"):
            actual = member(REPO / row["path"], REPO)
            assert actual == row
            read_sources.append(actual)
    host = (ENC / "host/encoder.rs").read_text()
    lines = host.splitlines()
    check("F1 source receiver present", "self.provenance" in lines[198])
    check("F2 outer propagation present", lines[393].strip().endswith(")?;"))
    original = json.loads((AUDIT / "cost-ledger.json").read_bytes())
    fixed = original["fixed_initialization"]
    provenance = next(row for row in fixed if row["lines"] == "199-205")
    validation = next(row for row in fixed if row["lines"] == "394")
    caller = {"receiver_fetch": 1, "slice": 1, "try_into_length": 1, "try_into_result": 1,
              "expect": 1, "map_err": 3, "outer_question": 2}
    corrected_provenance = original["helpers"]["provenance"] + sum(caller.values())
    corrected_validation = original["helpers"]["runtime_validation"] + 2 * (1 + 7 + 2) + 2
    deltas = {"F1": corrected_provenance - provenance["credits"], "F2": corrected_validation - validation["credits"]}
    check("F1 additive receiver action", deltas["F1"] == 1, caller)
    check("F2 additive propagation actions", deltas["F2"] == 2)
    corrected_fixed = sum(row["credits"] for row in fixed) + sum(deltas.values())
    check("corrected named fixed ledger", corrected_fixed == 14224)
    check("omitted F1 mutation fails exact caller coverage", sum(caller.values()) - caller["receiver_fetch"] < sum(caller.values()))
    check("omitted F2 mutation fails exact caller coverage", corrected_validation - 2 < corrected_validation)
    check("record maximum retained", original["record_branches"]["import"] == 29 + 20 + 2 * 27 + 21 + 15 == 139)
    check("block coefficients retained", original["next_block"]["fixed"] == 26 and original["next_block"]["iteration_coefficient"] == 68 and original["next_block"]["directory_probe"] == 39)
    findings = [
        {"id": "F1", "kind": "omitted named-source ledger action", "source": "host/encoder.rs:199-205", "term": provenance["name"], "original": provenance["credits"], "corrected": corrected_provenance, "delta": deltas["F1"], "reason": "self.provenance receiver fetch required by convention", "numerical_total_underbound_proven": False},
        {"id": "F2", "kind": "omitted named-source ledger actions", "source": "host/encoder.rs:394", "term": validation["name"], "original": validation["credits"], "corrected": corrected_validation, "delta": deltas["F2"], "reason": "outer validate_runtime(...)? inspect plus extraction/propagation", "numerical_total_underbound_proven": False},
    ]
    # These functions are independent integer models only. The released Python
    # module is loaded without calling main, controls, inputs, witness or save.
    independent = runpy.run_path(str(PRE / "arithmetic_controls.py"))
    producer = runpy.run_path(str(AUDIT / "audit.py"))
    retained = json.loads((PRE / "arithmetic-results.json").read_bytes())
    independent_profiles = [row["detail"]["counts"] for row in retained["checks"] if isinstance(row.get("detail"), dict) and "counts" in row["detail"]]
    profiles = independent_profiles + [(independent["CAPS"][0] - r,) + independent["CAPS"][1:] for r in range(8)]
    profiles += [(r, 3, 2, 1, 4, 3, 2, 5, 1) for r in range(56)]
    for index, counts in enumerate(profiles):
        a = independent["closed_total"](counts)
        b = producer["closed"](counts[0], counts[1:])
        check(f"independent-candidate geometry {index}", a["extent"] == b["E"] and a["blocks"] == b["B"] and a["source_steps"] == b["C"] and a["records"][1:] == b["W_sid"] and a["splits"][1:] == b["K_sid"] and a["record_visits"] == b["W"] and a["probes"] == b["D"])
    check("preaccess independent profile count", len(independent_profiles) == 268)
    check("total compact geometry cross-check count", len(profiles) == 332)
    # All original 305 controls are preserved; no script or result is rewritten.
    check("all retained independent controls passed", retained["check_count"] == 305 and all(row["pass"] for row in retained["checks"]))
    staged = OWN / "producer-replay-temporary.stdout"
    staged.rename(OUT / "producer-replay.stdout")
    replay = json.loads((OUT / "producer-replay.stdout").read_bytes())
    check("single read-only producer replay", replay["fixed"] == 14221 and replay["per_call_ceiling"] == 291214)
    producer_after = verify_seal(AUDIT, "ef906a8ec95d956898347bca67658ffac82a506be66b204d35893c23acfcfdd0")
    check("candidate unchanged through review", producer_before == producer_after)
    check("preaccess unchanged through review", preaccess == verify_seal(PRE, "1ae47e24a54b8a08d9019b7498db336a189ec0f1ec0ec7e550ffe4f074774997"))
    dump(OUT / "review.json", {"schema": 1, "status": "two-additive-ledger-corrections-required-no-numerical-total-underbound-demonstrated", "release": member(release, REPO), "producer": producer_after, "preaccess": preaccess, "source_identities": read_sources, "findings": findings, "original_fixed": 14221, "proposed_corrected_fixed": corrected_fixed, "block_formula_unchanged": "26+68I+39D+139W+Q", "complete_work_formula_selected": False, "operational_grant_selected": False, "controls": controls, "control_count": len(controls), "retained_preaccess_controls": 305, "independent_geometry_profiles_compared": len(profiles), "producer_replay": replay, "pending": ["root review of separate additive correction", "caller/control/writer/stop/arithmetic/cleanup terms", "operational work/storage admission", "paused native and GA qualification"]})
    dump(OUT / "receipt.json", {"schema": 1, "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(), "python": sys.version, "commands": [{"command": "python3 verification/swift-guarded-snapshot-encoder-work-audit/audit.py > verification/swift-guarded-snapshot-encoder-work-independent/producer-replay-temporary.stdout", "exit_code": 0, "retained_output": "producer-replay.stdout"}, {"command": "python3 verification/swift-guarded-snapshot-encoder-work-independent/candidate-review/review.py", "exit_code": 0}], "scope": "source reads, immutable custody, Python arithmetic and one read-only producer replay", "engine_compiler_writer_native_runtime_executed": False, "process_inventory": "not attempted", "cleanup": "No compiled products, VM/writer harnesses, disposable native instances, UI or capture processes were created. Temporary stdout moved into this packet. No broader cleanup claim."})
    members = [member(p, OUT) for p in sorted(OUT.rglob("*")) if p.is_file()]
    dump(OUT / "seal.json", {"schema": 1, "scope": "independent released encoder-only work source review; two additive ledger gaps", "members": members, "member_count": len(members), "bytes": sum(row["bytes"] for row in members), "tree_sha256": sha(json.dumps(members, sort_keys=True, separators=(",", ":")).encode())})
    print(json.dumps({"seal": member(OUT / "seal.json", REPO), "members": len(members), "controls": len(controls), "geometry_profiles": len(profiles), "findings": deltas, "proposed_fixed": corrected_fixed}))
