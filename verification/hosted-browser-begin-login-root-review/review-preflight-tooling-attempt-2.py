"""Read-only audit of the exact selected independent receipt."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ATTEMPT = ROOT / "verification/hosted-browser-begin-login-review/attempts/20261025T204044.344416Z-pg16-ae7369"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt = ATTEMPT / "receipt.json"
    assert sha(receipt) == "8fb5830f4bb7251e5bc255d2dc42563b99ffce91da3953c3e9286155cdc4efcf"
    data = json.loads(receipt.read_text())
    assert data["execution_completed"] and data["valid_execution_receipt"]
    assert data["all_recorded_invariants_passed"] and data["clean_runtime_output"]
    assert len(data["checks"]) == 34
    assert all(check["invariant_passed"] for check in data["checks"])
    assert not data["selected_source_changes"] and not data["dependency_changes"]
    assert all(data["cleanup"].values()) and all(data["beam_cleanup"].values())
    assert not Path(data["owned_scratch"]).exists()
    counts = {}
    for key, base in [("selected_sources", ROOT), ("review_sources", ROOT),
                      ("dependencies", ROOT), ("outputs", ATTEMPT)]:
        for name, digest in data[key].items():
            assert sha(base / name) == digest, (key, name)
        counts[key] = len(data[key])
    archived = 0
    for key in ["selected_sources", "review_sources"]:
        for name, digest in data[key].items():
            assert sha(ATTEMPT / "inputs" / name) == digest, (key, name)
            archived += 1
    argv = ["docker", "inspect", data["owned_container_id"]]
    result = subprocess.run(argv, capture_output=True)
    (OUT / "review-owned-container-absence.stdout").write_bytes(result.stdout)
    (OUT / "review-owned-container-absence.stderr").write_bytes(result.stderr)
    assert result.returncode == 1 and result.stdout.strip() == b"[]"
    assert ("no such object: " + data["owned_container_id"]) in result.stderr.decode().lower()
    report = {
        "schema": 1,
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "argv": [sys.executable, str(Path(__file__).resolve())],
        "script_sha256": sha(Path(__file__)),
        "python_version": sys.version,
        "revision_context": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "review_receipt": str(receipt.relative_to(ROOT)),
        "review_receipt_sha256": sha(receipt),
        "producer_handoff_sha256": data["producer_handoff_sha256"],
        "bindings": counts,
        "archived_source_bindings": archived,
        "checks": 34,
        "clean_runtime_output": True,
        "beam_cleanup": data["beam_cleanup"],
        "scratch_absent": True,
        "owned_container_absence": {
            "argv": argv, "exit": result.returncode,
            "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
        },
        "status": "selected-review-receipt-integrity-passed-final-review-seal-pending",
        "scope": "Read-only bytes and exact owned resource absence; full browser/provider/startup/native/GA not accepted",
    }
    (OUT / "review-preflight.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"bindings": counts, "archived_sources": archived, "checks": 34, "cleanup": True}))


if __name__ == "__main__":
    main()
