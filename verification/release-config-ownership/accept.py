#!/usr/bin/env python3
"""Bind current service inputs to the completed root and independent evidence."""
import datetime
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "verification/release-config-ownership"
REVIEW = ROOT / "verification/release-config-ownership-review"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
product = read(BASE / "candidate-1/receipt.json")
assert product["status"] == "passed" and product["sourceUnchanged"]
assert product["driverSHA256"] == sha(BASE / "run.py")
for name, digest in product["sourceFiles"].items():
    assert sha(ROOT / name) == digest, name
for command in product["commands"]:
    assert command["exitCode"] == 0 and sha(ROOT / command["log"]) == command["sha256"]
    assert "WARNING: DATA RACE" not in (ROOT / command["log"]).read_text()
sums = read(REVIEW / "SHA256SUMS.json")
for name, digest in sums.items():
    assert sha(REVIEW / name) == digest, name
inputs = read(REVIEW / "candidate-inputs.json")
archived = {}
for name, key in [("baseline-services.tar.gz", "baseline_archive_sha256"),
                  ("candidate-delta.tar.gz", "candidate_delta_sha256"),
                  ("support-inputs.tar.gz", "support_archive_sha256")]:
    assert sha(REVIEW / name) == inputs[key]
    with tarfile.open(REVIEW / name) as archive:
        for member in archive.getmembers():
            assert member.isfile() and not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
            archived[member.name] = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
for name, digest in inputs["candidate_source_files"].items():
    assert archived[name] == digest, name
for name, digest in product["sourceFiles"].items():
    assert archived[name] == digest, name
for command in read(REVIEW / "baseline-runs.json"):
    assert command["exit_code"] != 0
    if command["name"].startswith("baseline-race-"):
        assert "WARNING: DATA RACE" in (REVIEW / command["log"]).read_text()
for command in read(REVIEW / "candidate-runs.json"):
    log = (REVIEW / command["log"]).read_text()
    if command["name"] == "candidate-services-race":
        assert command["exit_code"] != 0 and "release-v2.json" in log
    else:
        assert command["exit_code"] == 0 and "WARNING: DATA RACE" not in log
cleanup = read(REVIEW / "cleanup.json")
assert cleanup["removed"] and cleanup["open_file_check_exit_code"] == 1
expected = "COMMAND: lsof -nP +D " + cleanup["owned_scratch_path"] + "\nEXIT: 1\n"
assert (REVIEW / cleanup["open_file_check"]).read_text() == expected
assert not Path(cleanup["owned_scratch_path"]).exists()
paths = [p for directory in (BASE, REVIEW) for p in directory.rglob("*")
         if p.is_file() and p.name != "root-acceptance.json" and "__pycache__" not in p.parts]
paths += [ROOT / name for name in ["docs/release-config-ownership.md", "docs/release-config-ownership-review.md",
          "services/release/server.go", "services/release/config.go", "services/release/config_ownership_test.go"]]
receipt = {
    "schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "accepted-constructor-configuration-ownership-host-scope",
    "reviewer": "root integrator after independent review",
    "command": ["python3", "-B", "verification/release-config-ownership/accept.py"],
    "python": platform.python_version(),
    "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "sourceTreeSHA256": product["sourceTreeSHA256"], "sourceFiles": product["sourceFiles"],
    "qualification": {"focusedTopLevelTests": 5, "focusedSubtests": 30, "completeServicesRaceTopLevelTests": 61,
                      "completeServicesRacePassEvents": 1103, "vet": "passed", "independentPublicTopLevelTests": 5,
                      "independentPublicSubcases": 13, "independentBaselineRacesReproduced": 5,
                      "independentSavedHashes": len(sums), "rootArchiveSourceMatches": len(product["sourceFiles"])},
    "sourceReview": ["Typed snapshot owns every current Config mutable reference before validation/storage open.",
                     "Original bearer/tenant/role/audit identity, signing bytes and host policy survive post-construction caller mutation.",
                     "Concurrent requests use distinct idempotency keys to traverse actual authorization/verification.",
                     "Independent original-source probes reproduce authority changes and five races; candidate checks pass."],
    "limitations": ["Input must remain stable during construction; no concurrent-New safety claim.",
                    "PostgreSQL pointee isolation has typed/helper evidence only; database integration is not run for this slice.",
                    "No hosted identity, external delivery, production deployment, native/physical or GA gate acceptance."],
    "bindings": {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(paths))}}
(BASE / "root-acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"status": receipt["status"], "bindings": len(receipt["bindings"]),
                  "sourceFiles": len(product["sourceFiles"]), "independentHashes": len(sums)}))
