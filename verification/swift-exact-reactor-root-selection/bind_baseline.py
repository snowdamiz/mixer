"""Select the current committed VM baseline for an isolated diagnostic harness."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
MANIFEST = ROOT / "verification/swift-lifecycle-linux-fixture-repair/candidate-manifest.json"
EXPECTED = "6d4b1deed091d6c0f0a2ae0c101c98afbd0e27fdc3c2b2992a999e08565a3fe8"
TARGET = ROOT / "compiler/experiments/fieldlog-reactor/local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm"
TARGET_SHA = "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert digest(MANIFEST) == EXPECTED
manifest = json.loads(MANIFEST.read_bytes())
assert len(manifest) == 132
for name, expected in manifest.items():
    path = ROOT / "vm" / name
    assert not Path(name).is_absolute() and ".." not in Path(name).parts
    assert path.is_file() and not path.is_symlink() and digest(path) == expected, name
assert TARGET.stat().st_size == 53_777_114 and digest(TARGET) == TARGET_SHA
changes = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no", "--", "vm"], cwd=ROOT)
assert not changes.strip(), "VM has uncommitted changes"
record = {
    "schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version,
    "verifierSHA256": digest(Path(__file__)),
    "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
    "baselineManifest": str(MANIFEST.relative_to(ROOT)), "baselineManifestSHA256": EXPECTED,
    "baselineFilesVerified": 132, "baselineCommit": "50f70a798fea43e1e77b1d95faa1bbda3fc029e0",
    "historicalBaselineDrift": "The old 64a3d9c5 closure predates the committed test-only Linux deadline repair in control.rs and lifecycle_tests.rs. All current files match the independently reviewed 6d4b1dee candidate.",
    "target": str(TARGET.relative_to(ROOT)), "targetBytes": 53_777_114, "targetSHA256": TARGET_SHA,
    "scope": "Current baseline selected for isolated harness preparation; exact execution awaits root inspection of harness and bounded command.",
    "productionEngineChangesAuthorized": False, "budgetWideningAuthorized": False,
    "exactExecutionAuthorized": False, "fullSLMatrixAccepted": False, "gaAccepted": False,
}
target = BASE / "baseline.json"
assert not target.exists(), "preserve existing selection"
target.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"baselineFilesVerified": 132, "targetBytes": 53_777_114, "exactExecutionAuthorized": False}))
