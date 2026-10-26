"""Admit the frozen R2 reviews without executing any candidate or reviewer code."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def admit(path, expected_digest, count, size):
    raw = (ROOT / path).read_bytes()
    assert digest(raw) == expected_digest, path
    members = json.loads(raw)["members"]
    assert len(members) == count
    seen = set()
    total = 0
    for member in members:
        relative = pathlib.PurePosixPath(member["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert str(relative) not in seen
        seen.add(str(relative))
        data = (ROOT / relative).read_bytes()
        assert len(data) == member["bytes"] and digest(data) == member["sha256"], str(relative)
        total += len(data)
    assert total == size
    return {"path": path, "sha256": expected_digest, "members": count, "bytes": total}


packets = [
    admit("verification/swift-analyzer-envelope-correction-behavior-review/final-review/seal.json",
          "ee8b9ec9ef3b894e6bc40036aa8951528401414933097849f0c2e4a8aa879cff", 118, 2032748),
    admit("verification/swift-ordered-retention-analyzer-envelope-correction-final-accounting-review/seal.json",
          "929593356ebb871f4089e04ad1b71d216880d90a3da5151a5421c50553b985e8", 248, 43000105),
    admit("verification/swift-ordered-retention-analyzer-envelope-correction/seal.json",
          "4ddff8237bd49cab9f6191be89e4764966e1af5dfa686bb931ac1372d1e98df1", 306, 44895898),
]
behavior = ROOT / "verification/swift-analyzer-envelope-correction-behavior-review/final-review"
receipt = json.loads((behavior / "final-receipt.json").read_text())
finding_raw = (behavior / "finding-R2.json").read_bytes()
assert digest(finding_raw) == "8ccca728cc7523b2f0622db35dea665327d5e8bc7179e21dca01818f6bd56098"
finding = json.loads(finding_raw)
assert finding["actual_debit_vector"] == [0, 0, 0, 425, 425, 0, 0, 0, 425, 425]
assert finding["expected_debit_vector"] == [0] * 10
assert not finding["candidate_changed"]
assert receipt["methods_passed"] == 18 and receipt["methods_failed"] == 1
assert receipt["API_positive"] == 1 and receipt["API_expected_negative"] == 8
assert not receipt["implementation_accepted"] and not receipt["all32_passed"]
accounting = json.loads((ROOT / "verification/swift-ordered-retention-analyzer-envelope-correction-final-accounting-review/final-review-receipt.json").read_text())
assert accounting["operation_type_lifetime_bounds_supported"]
assert not accounting["combined_final_source_operation_type_lifetime_proof_accepted"]
assert accounting["operation_rows_checked"] == 116 and accounting["transfer_edges_checked"] == 108
assert receipt["source_sha256"] == accounting["source_sha256"] == finding["source_sha256"] == "7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1"
result = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
    "python_version": sys.version,
    "checker_sha256": digest(pathlib.Path(__file__).read_bytes()),
    "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "scope": "Read-only exact frozen evidence admission; no candidate, model, collector or reviewer execution",
    "packets": packets,
    "verified_members": sum(p["members"] for p in packets),
    "verified_bytes": sum(p["bytes"] for p in packets),
    "source_sha256": receipt["source_sha256"],
    "behavior": {"passed": 18, "failed": 1, "API_positive": 1, "API_expected_negative": 8, "finding": "R2", "finding_sha256": digest(finding_raw)},
    "accounting": {"bounds_supported": True, "rows": 116, "transfer_edges": 108, "combined_acceptance": False},
    "status": "acceptance-withheld-absent-state-debit-correction-required",
    "next_scope": "Separate frozen source, guard funding and caller validator proposal; independent accounting before root selection and corrected runtime replay",
    "main_B471_public425_refund_authorized": False,
    "existing_G112_scope_expanded": False,
    "implementation_accepted": False,
    "native_runtime_or_capture_started": False,
    "GA_gates_promoted": 0,
    "errors": [],
}
(OUT / "final-correction-review-admission.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: result[key] for key in ("verified_members", "verified_bytes", "behavior", "accounting", "status", "errors")}))
