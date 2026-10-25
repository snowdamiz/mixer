#!/usr/bin/env python3
"""Preserve existing review output and retire only its stopped, owned scratch.

This does not import the candidate or execute/retry any review test.
"""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
REVIEW = ROOT / "verification/hosted-worker-transport-v2-independent-review"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    target = BASE / "interrupted-review.json"
    if target.exists():
        raise RuntimeError("preserve existing interruption receipt")
    process = subprocess.run(["ps", "-axo", "pid=,ppid=,pgid=,command="], capture_output=True, check=True)
    matches = [line for line in process.stdout.decode().splitlines() if str(REVIEW) in line or "hosted-worker-transport-v2-independent-review" in line]
    if matches:
        raise RuntimeError("review-owned command may still be alive; no cleanup performed")
    files = sorted(p for p in REVIEW.rglob("*") if p.is_file())
    if any(p.is_symlink() for p in files):
        raise RuntimeError("unexpected symlink")
    rows = [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]
    archive = BASE / "interrupted-review-snapshot.tar.gz"
    with tarfile.open(archive, "x:gz") as output:
        for p in files:
            output.add(p, arcname=str(p.relative_to(ROOT)), recursive=False)
    with tarfile.open(archive) as saved:
        for row in rows:
            data = saved.extractfile(row["path"]).read()
            assert len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"]
    removed = []
    for name in ["build", "scratch"]:
        directory = REVIEW / name
        assert not directory.is_symlink()
        if directory.exists():
            shutil.rmtree(directory)
            removed.append(str(directory.relative_to(ROOT)))
    existing = json.loads((REVIEW / "owner-delivery-deadline-observation.json").read_text())
    receipt = {"schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [sys.executable, str(Path(__file__).relative_to(ROOT))], "python": sys.version,
        "scriptSHA256": sha(Path(__file__)), "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "status": "independent-review-interrupted-not-accepted",
        "interruption": "Review agent errored: content flagged for possible cybersecurity risk. Root did not retry or execute further review tests.",
        "preservedObservation": existing, "observationSHA256": sha(REVIEW / "owner-delivery-deadline-observation.json"),
        "interpretation": "Existing isolated control returned a valid observation 81 ms after its deadline; integration remains rejected pending repair and completed acceptance.",
        "archiveSHA256": sha(archive), "files": rows, "cleanup": {"psCommand": ["ps", "-axo", "pid=,ppid=,pgid=,command="], "matchingLiveCommands": [], "removedOwnedScratch": removed, "allSelectedScratchAbsent": all(not (REVIEW / name).exists() for name in ["build", "scratch"])},
        "candidateImportedOrExecutedByFinalizer": False, "additionalTestsExecuted": False, "independentReviewComplete": False, "liveIntegrationAccepted": False, "gaAccepted": False}
    target.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "preservedFiles": len(rows), "cleanup": receipt["cleanup"]}))

if __name__ == "__main__":
    main()
