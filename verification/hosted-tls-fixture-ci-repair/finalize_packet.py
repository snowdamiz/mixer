#!/usr/bin/env python3
"""Bind immutable matrix attempts, preserving pre-test collector failures."""
import hashlib
import json
from pathlib import Path
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads((OUT / path).read_text())


def save(path, data):
    with (OUT / path).open("x") as target:
        target.write(json.dumps(data, indent=2, sort_keys=True) + "\n")


passing = {"macos": ("macos-final-canonical", 45), "linux": ("linux-final", 46)}
observations = {}
for platform, (run, count) in passing.items():
    receipt = read(f"{run}/receipt.json")
    cleanup = read(f"{run}/cleanup.json")
    log = (OUT / run / "tests.log").read_text()
    assert receipt["status"] == "passed" and receipt["inputsUnchanged"]
    assert f"Result: {count} passed\n" in log
    assert cleanup["scratchRemoved"] and not cleanup["ownedContainerRetained"]
    assert cleanup["historicalIdentityPacketUnchanged"] and cleanup["originalCIFailureUnchanged"]
    assert cleanup["preexistingContainerIDs"] == cleanup["preexistingContainerIDsStillPresent"]
    if platform == "linux":
        probe = '%{system_tmp_dir: "/tmp", private_tmp_exists: false, fixture_directories: []}'
        assert log.count(probe) == 2
    observations[platform] = {"run": run, "passed": count, "invalid": 0, "skipped": 0,
                             "testsOutputSHA256": sha(OUT / run / "tests.log"),
                             "receiptSHA256": sha(OUT / run / "receipt.json"),
                             "cleanupSHA256": sha(OUT / run / "cleanup.json")}

mac = read("macos-final-canonical/receipt.json")
linux = read("linux-final/receipt.json")
for key in ("sourceRevision", "sourceTreeDigest", "dependencyTreeDigest", "fixtureSHA256"):
    assert mac[key] == linux[key]
assert sha(ROOT / "hosted/test/support/identity_tls_fixture.ex") == mac["fixtureSHA256"]
original = mac["originalFailure"]
assert sha(ROOT / original["path"]) == original["sha256"]
production_diff = subprocess.check_output(
    ["git", "diff", "--name-only", mac["sourceRevision"], "--", "hosted/lib", "hosted/config",
     "hosted/mix.exs", "hosted/mix.lock"], cwd=ROOT, text=True)
assert not production_diff.strip()

save("receipt.json", {
    "scope": "Test-only TLS fixture temporary-directory portability; exact unchanged accepted identity matrix snapshots",
    "status": "passed component matrix; independent root acceptance and CI rerun are separate",
    "sourceRevision": mac["sourceRevision"], "sourceTreeDigest": mac["sourceTreeDigest"],
    "dependencyTreeDigest": mac["dependencyTreeDigest"], "fixtureSHA256": mac["fixtureSHA256"],
    "productionSourcesUnchangedAgainstParentRevision": True,
    "originalFailure": original, "passingMatrix": observations,
    "preservedPreTestCollectorFailures": [
        {"run": "macos", "runner": "run_matrix_attempt_1.py", "runnerSHA256": sha(OUT / "run_matrix_attempt_1.py"),
         "reason": "JOSE include symlink missing before tests; external build path and /var alias snapshot layout"},
        {"run": "macos-final", "runner": "run_matrix_attempt_2.py", "runnerSHA256": sha(OUT / "run_matrix_attempt_2.py"),
         "reason": "JOSE include symlink still missing before tests; conventional build path alone did not resolve /var alias"}
    ],
    "finalCollector": {"path": "run_matrix.py", "sha256": sha(OUT / "run_matrix.py"),
                       "repair": "Canonicalize owned scratch with Path.resolve before compiling dependencies"},
    "documentationSHA256": sha(ROOT / "docs/hosted-tls-fixture-ci-repair.md"),
    "limits": ["No physical devices", "No store or GA acceptance", "No production/provider/customer execution",
               "No full hosted/release/database or rerun GitHub CI result in this packet",
               "Subsequent root receipt-output hygiene changes are outside the tested snapshots"],
})
files = {str(p.relative_to(ROOT)): sha(p) for p in sorted(OUT.rglob("*")) if p.is_file()}
files["docs/hosted-tls-fixture-ci-repair.md"] = sha(ROOT / "docs/hosted-tls-fixture-ci-repair.md")
files["hosted/test/support/identity_tls_fixture.ex"] = mac["fixtureSHA256"]
save("evidence-manifest.json", {
    "files": files,
    "treeDigest": hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    "algorithm": "SHA-256 per file; tree SHA-256 of sorted-key compact UTF-8 JSON file-hash map",
})
print(json.dumps({"fixtureSHA256": mac["fixtureSHA256"], "sourceTreeDigest": mac["sourceTreeDigest"],
                  "evidenceTreeDigest": read("evidence-manifest.json")["treeDigest"],
                  "macOS": 45, "Linux": 46}, indent=2))
