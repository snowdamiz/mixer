#!/usr/bin/env python3
"""Read-only hash/cleanup audit of the selected producer packet, not acceptance."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "verification/hosted-browser-begin-login"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_map(values, base):
    for path, digest in values.items():
        assert sha(base / path) == digest, path
    return len(values)


def main():
    handoff = json.loads((BASE / "handoff.json").read_text())
    sealed = 0
    for line in (BASE / "handoff.sha256").read_text().splitlines():
        digest, path = line.split("  ", 1)
        assert sha(ROOT / path) == digest, path
        sealed += 1
    attempt = ROOT / handoff["selected_attempt"]
    assert sha(attempt / "receipt.json") == handoff["selected_receipt_sha256"]
    receipt = json.loads((attempt / "receipt.json").read_text())
    sources = check_map(receipt["sources"], ROOT)
    dependencies = check_map(receipt["dependencies"], ROOT)
    outputs = check_map(receipt["outputs"], attempt)
    assert receipt["passed"] and receipt["success"]
    assert not receipt["source_changes"] and not receipt["dependency_changes"]
    assert all(x["passed"] for x in receipt["checks"])
    assert len(receipt["preauth_regression_checks"]) == 30
    assert all(x["passed"] for x in receipt["preauth_regression_checks"])
    beam = json.loads((attempt / "beam-cleanup.json").read_text())
    assert all(beam.values())
    historical = []
    for path, digest in handoff["historical_receipts"].items():
        source = ROOT / path
        assert sha(source) == digest, path
        value = json.loads(source.read_text())
        assert all(value["cleanup"].values()), path
        assert not Path(value["owned_scratch"]).exists(), path
        historical.append({"receipt": path, "sha256": digest,
                           "passed": value.get("passed"),
                           "owned_scratch_absent": True,
                           "outputs_verified": check_map(value["outputs"], source.parent)})
    report = {
        "schema": 1,
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "argv": [sys.executable, str(Path(__file__).resolve())],
        "python_version": sys.version,
        "script_sha256": sha(Path(__file__)),
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "handoff_sha256": sha(BASE / "handoff.json"),
        "seal_sha256": sha(BASE / "handoff.sha256"),
        "sealed_members": sealed,
        "source_bindings": sources,
        "dependency_bindings": dependencies,
        "output_bindings": outputs,
        "checks": len(receipt["checks"]),
        "preauth_regression_checks": len(receipt["preauth_regression_checks"]),
        "historical_attempts": historical,
        "status": "producer-packet-integrity-passed-independent-runtime-review-pending",
        "scope": "Read-only selected bytes and exact owned scratch absence; no native or process discovery, no product acceptance",
    }
    (OUT / "producer-preflight.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "historical_attempts"}, indent=2))


if __name__ == "__main__":
    main()
