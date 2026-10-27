#!/usr/bin/env python3
"""Exact additive delta review; only immutable sources and Python arithmetic."""
from pathlib import Path
import copy
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
BASE = REPO / "verification/swift-guarded-snapshot-encoder-work-audit"
CORR = REPO / "verification/swift-guarded-snapshot-encoder-work-correction"
ENC = REPO / "verification/swift-guarded-snapshot-encoder-implementation"
PRE = OWN / "preaccess"
ORIGINAL_REVIEW = OWN / "candidate-review"
checks, repeated = [], []


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def member(path, root):
    data = path.read_bytes()
    return {"path": str(path.relative_to(root)), "bytes": len(data), "sha256": sha(data)}


def check(name, condition, detail=None, original=False):
    assert condition, (name, detail)
    (repeated if original else checks).append({"name": name, "pass": True, "detail": detail})


def verify(base, expected):
    raw = (base / "seal.json").read_bytes()
    assert sha(raw) == expected
    seal = json.loads(raw)
    assert len(seal["members"]) == seal["member_count"]
    for row in seal["members"]:
        assert member(base / row["path"], base) == row
    return {"seal": member(base / "seal.json", REPO), "member_count": len(seal["members"]), "member_bytes": sum(row["bytes"] for row in seal["members"]), "tree_sha256": seal["tree_sha256"]}


if __name__ == "__main__":
    assert not (OUT / "seal.json").exists(), "immutable review must not be overwritten"
    identities = {
        "base": (BASE, "ef906a8ec95d956898347bca67658ffac82a506be66b204d35893c23acfcfdd0"),
        "correction": (CORR, "5f999a20a05e53a45b5427e6647f15e73b7056d8a260d82b8c06fa9b08388435"),
        "preaccess": (PRE, "1ae47e24a54b8a08d9019b7498db336a189ec0f1ec0ec7e550ffe4f074774997"),
        "original_review": (ORIGINAL_REVIEW, "2fda433b6963c0f5005bd12a2e3021bb0da082ef90c40efb44d860cda74e97d7"),
    }
    before = {name: verify(path, digest) for name, (path, digest) in identities.items()}
    check("correction exact 15-member byte roster", before["correction"]["member_count"] == 15 and before["correction"]["member_bytes"] == 76535)
    correction_seal = json.loads((CORR / "seal.json").read_bytes())
    computed_tree = sha(json.dumps(correction_seal["members"], sort_keys=True, separators=(",", ":")).encode())
    check("correction canonical roster preimage", computed_tree == before["correction"]["tree_sha256"] == "bdaabbee179eb256ee98ce03d3d96a33219e46d19fd749a14bb3b55ce30fafd7")
    replacements = [
        ('"199-205", provenance+9', '"199-205", provenance+10'),
        ('"394", runtime_validation+20', '"394", runtime_validation+22'),
        ('assert fixed == 14221, fixed', 'assert fixed == 14224, fixed'),
        ('return 14221 + 26*', 'return 14224 + 26*'),
        ('"python3 verification/swift-guarded-snapshot-encoder-work-audit/audit.py"', '"python3 verification/swift-guarded-snapshot-encoder-work-correction/audit.py"'),
    ]
    expected_script = (BASE / "audit.py").read_text()
    for old, new in replacements:
        check("unique exact script replacement: " + old, expected_script.count(old) == 1)
        expected_script = expected_script.replace(old, new)
    check("script exactly five reviewed replacements", expected_script.encode() == (CORR / "audit.py").read_bytes())
    for name in ["cost-convention.md", "geometry.md", "input-custody.json"]:
        check("unchanged " + name, (BASE / name).read_bytes() == (CORR / name).read_bytes())
    old_ledger = json.loads((BASE / "cost-ledger.json").read_bytes())
    ledger = json.loads((CORR / "cost-ledger.json").read_bytes())
    expected_ledger = copy.deepcopy(old_ledger)
    changes = [("provenance bridge, region conversion and error propagation", 1), ("runtime validation and two count conversions", 2)]
    for name, delta in changes:
        rows = [row for row in expected_ledger["fixed_initialization"] if row["name"] == name]
        check("unique named ledger row " + name, len(rows) == 1)
        rows[0]["credits"] += delta
    expected_ledger["fixed_total"] += 3
    check("ledger exactly two named rows plus total", expected_ledger == ledger)
    check("unchanged full dynamic ledger and getter convention", ledger["next_block"] == old_ledger["next_block"] and (CORR / "cost-convention.md").read_bytes() == (BASE / "cost-convention.md").read_bytes())
    old_results = json.loads((BASE / "results.json").read_bytes())
    results = json.loads((CORR / "results.json").read_bytes())
    expected_results = copy.deepcopy(old_results)
    for row in expected_results["frozen_actual_artifacts"]:
        row["comparison"]["encoder_only_bound"] += 3
    expected_results["independent_maximum_envelope"]["comparison"]["encoder_only_bound"] += 3
    check("results exactly three encoder bounds plus three", expected_results == results and len(expected_results["frozen_actual_artifacts"]) == 2)
    failure = json.loads((CORR / "finalization-attempt-1.json").read_bytes())
    check("root finalization failure retained separately", failure["status"] == "failed-root-finalization-before-writes" and failure["exit"] == 1 and not failure["source_or_work_formula_changed"])
    # Re-run the original independent 347 expectations, using the corrected
    # geometry module and fresh seal verification rather than invoking a writer.
    host = (ENC / "host/encoder.rs").read_text().splitlines()
    check("F1 source receiver present", "self.provenance" in host[198], original=True)
    check("F2 outer propagation present", host[393].strip().endswith(")?;"), original=True)
    caller = {"receiver_fetch": 1, "slice": 1, "try_into_length": 1, "try_into_result": 1, "expect": 1, "map_err": 3, "outer_question": 2}
    new_provenance = ledger["helpers"]["provenance"] + sum(caller.values())
    new_validation = ledger["helpers"]["runtime_validation"] + 2 * (1 + 7 + 2) + 2
    old_provenance = next(row["credits"] for row in old_ledger["fixed_initialization"] if row["lines"] == "199-205")
    old_validation = next(row["credits"] for row in old_ledger["fixed_initialization"] if row["lines"] == "394")
    check("F1 additive receiver action", new_provenance - old_provenance == 1, original=True)
    check("F2 additive propagation actions", new_validation - old_validation == 2, original=True)
    check("corrected named fixed ledger", ledger["fixed_total"] == sum(row["credits"] for row in ledger["fixed_initialization"]) == 14224, original=True)
    check("omitted F1 mutation fails exact caller coverage", sum(caller.values()) - caller["receiver_fetch"] < sum(caller.values()), original=True)
    check("omitted F2 mutation fails exact caller coverage", new_validation - 2 < new_validation, original=True)
    check("record maximum retained", ledger["record_branches"]["import"] == 29 + 20 + 2 * 27 + 21 + 15 == 139, original=True)
    check("block coefficients retained", ledger["next_block"]["fixed"] == 26 and ledger["next_block"]["iteration_coefficient"] == 68 and ledger["next_block"]["directory_probe"] == 39, original=True)
    check("corrected caller rows cover both findings", next(row["credits"] for row in ledger["fixed_initialization"] if row["lines"] == "199-205") == new_provenance and next(row["credits"] for row in ledger["fixed_initialization"] if row["lines"] == "394") == new_validation)
    independent = runpy.run_path(str(PRE / "arithmetic_controls.py"))
    corrected = runpy.run_path(str(CORR / "audit.py"))
    retained = json.loads((PRE / "arithmetic-results.json").read_bytes())
    profiles = [row["detail"]["counts"] for row in retained["checks"] if isinstance(row.get("detail"), dict) and "counts" in row["detail"]]
    check("preaccess independent profile count", len(profiles) == 268, original=True)
    profiles += [(independent["CAPS"][0] - r,) + independent["CAPS"][1:] for r in range(8)]
    profiles += [(r, 3, 2, 1, 4, 3, 2, 5, 1) for r in range(56)]
    for index, counts in enumerate(profiles):
        a, b = independent["closed_total"](counts), corrected["closed"](counts[0], counts[1:])
        check(f"independent-candidate geometry {index}", a["extent"] == b["E"] and a["blocks"] == b["B"] and a["source_steps"] == b["C"] and a["records"][1:] == b["W_sid"] and a["splits"][1:] == b["K_sid"] and a["record_visits"] == b["W"] and a["probes"] == b["D"], original=True)
    check("total compact geometry cross-check count", len(profiles) == 332, original=True)
    check("all retained independent controls passed", retained["check_count"] == 305 and all(row["pass"] for row in retained["checks"]), original=True)
    command = [sys.executable, "verification/swift-guarded-snapshot-encoder-work-correction/audit.py"]
    replay = subprocess.run(command, cwd=REPO, text=True, capture_output=True, timeout=30)
    (OUT / "producer-replay.stdout").write_text(replay.stdout)
    (OUT / "producer-replay.stderr").write_text(replay.stderr)
    summary = json.loads(replay.stdout)
    check("single read-only producer replay", replay.returncode == 0 and not replay.stderr and summary["fixed"] == 14224 and summary["per_call_ceiling"] == 291214, original=True)
    after = {name: verify(path, digest) for name, (path, digest) in identities.items()}
    check("candidate unchanged through review", before["base"] == after["base"] and before["correction"] == after["correction"], original=True)
    check("preaccess unchanged through review", before["preaccess"] == after["preaccess"], original=True)
    original = json.loads((ORIGINAL_REVIEW / "review.json").read_bytes())
    check("original 347 expectation identities reproduced", len(repeated) == original["control_count"] == 347 and {row["name"] for row in repeated} == {row["name"] for row in original["controls"]})
    check("all four frozen packets unchanged", before == after)
    dump(OUT / "review.json", {"schema": 1, "status": "accept-exact-additive-encoder-only-correction", "inputs": after, "fixed": 14224, "fixed_delta": 3, "block_unchanged": "26+68I+39D+139W+Q", "original_expectations_freshly_reproduced": repeated, "original_expectation_count": len(repeated), "additional_correction_controls": checks, "additional_correction_control_count": len(checks), "replay_summary": summary, "findings_closed": ["F1 provenance receiver fetch +1", "F2 runtime validation outer propagation +2"], "original_failures_preserved": True, "numerical_prior_total_underbound_proven": False, "operational_work_or_storage_grant_selected": False, "pending": ["caller/control/writer/stop/accounting/cleanup terms", "complete operational work/storage admission", "paused native and GA qualification"]})
    dump(OUT / "receipt.json", {"schema": 1, "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(), "python": sys.version, "command": "python3 verification/swift-guarded-snapshot-encoder-work-independent/correction-review/review.py", "corrected_replay_command": command, "exit_code": 0, "corrected_replay_exit_code": replay.returncode, "source_tree": "447719d8fef2928674d9d196266408ca72c70ce152cf0251807d2c3bcd7e7c43", "scope": "immutable exact delta, source action coverage and read-only Python arithmetic", "engine_vm_compiler_writer_native_ui_capture_executed": False, "process_inventory": "not attempted", "cleanup": "Only short-lived Python source/arithmetic commands. No native instances, compiled products or persistent harnesses created. All original frozen packets unchanged."})
    members = [member(p, OUT) for p in sorted(OUT.rglob("*")) if p.is_file()]
    dump(OUT / "seal.json", {"schema": 1, "scope": "accepted exact +3 encoder logical-work additive correction only", "members": members, "member_count": len(members), "bytes": sum(row["bytes"] for row in members), "tree_sha256": sha(json.dumps(members, sort_keys=True, separators=(",", ":")).encode())})
    print(json.dumps({"status": "accept-exact-additive-encoder-only-correction", "seal": member(OUT / "seal.json", REPO), "members": len(members), "original_controls_reproduced": len(repeated), "additional_controls": len(checks)}))
