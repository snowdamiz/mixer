"""Verify the integrated-source host run and exact reviewed production output."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = HERE / sys.argv[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


receipt = read(RUN / "receipt.json")
assert receipt["status"] == "passed" and receipt["failure"] is None
source = read(RUN / "source-manifest.json")
for name, expected in source.items():
    assert sha(ROOT / name) == expected, name
for command in receipt["commands"]:
    assert command["exitCode"] == 0 and command["processGroupEmpty"] and command["scratchRemoved"]
    assert not command["timedOut"] and not Path(command["scratch"]).exists()
    for stream in ["stdout", "stderr"]:
        assert sha(RUN / command["name"] / stream) == command[stream + "SHA256"]
counts = {}
for name, path, expected in [
    ("original", "original-report.json", 28),
    ("regressions", "regressions-fixture/regression-report.json", 7),
    ("focused", "focused-fixture/focused-report.json", 36),
]:
    result = read(RUN / path)
    assert result["status"] == "passed" and len(result["results"]) == expected
    assert all(row["status"] == "passed" for row in result["results"])
    for entry in result["cleanup"]:
        if "persist" in entry:
            assert not Path(entry["persist"]).exists()
    counts[name] = expected
candidate = ROOT / "verification/hosted-worker-controller-v2/candidate/hosted-worker-controller"
compiled = {}
for path in sorted((candidate / "dist/src").rglob("*")):
    if path.is_file():
        live = ROOT / "hosted-worker-controller" / path.relative_to(candidate)
        assert path.read_bytes() == live.read_bytes()
        compiled[str(live.relative_to(ROOT))] = sha(live)
closure = read(RUN / "production-closure.json")
assert closure["status"] == "passed" and len(closure["files"]) == 9
assert closure["externals"] == ["cloudflare:workers"] and closure["testBundleIncluded"] is False
for row in read(HERE / "source-integration.json")["changedFiles"]:
    assert sha(ROOT / row["path"]) == row["afterSHA256"]
record = {
    "schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve()), sys.argv[1]],
    "python": sys.version, "verifierSHA256": sha(Path(__file__)),
    "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "run": str(RUN.relative_to(ROOT)), "receiptSHA256": sha(RUN / "receipt.json"),
    "sourceFilesVerified": len(source), "testGroupsPassed": counts,
    "compiledReviewedFilesMatched": compiled, "productionClosureFiles": 9,
    "allOwnedCommandGroupsEmpty": True, "allOwnedScratchRemoved": True,
    "status": "integrated-controller-host-runtime-passed", "productionEnabled": False,
    "linuxCIPending": True, "nativeOrCloudOperationalAccepted": False, "gaAccepted": False,
}
output = HERE / (sys.argv[1] + "-binding.json")
assert not output.exists()
output.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"status": record["status"], "testGroupsPassed": counts, "compiledReviewedFilesMatched": len(compiled)}))
