"""Read-only custody preflight; all seal paths are repository-relative."""
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
SEAL = ROOT / "verification/android-copied-sdk-appearance-contract/seal.json"
expected = "e08abcacc8421eb2415daa259cf0f9d67a9e2fafa7a879f0b95f574866f62ffb"
assert hashlib.sha256(SEAL.read_bytes()).hexdigest() == expected
data = json.loads(SEAL.read_text())
errors = []
total = 0
for name, metadata in data["files"].items():
    contents = (ROOT / name).read_bytes()
    total += len(contents)
    if len(contents) != metadata["bytes"] or hashlib.sha256(contents).hexdigest() != metadata["sha256"]:
        errors.append(name)
result = {
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "kind": "Read-only root frozen proposal preflight",
    "command": [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
    "python_version": sys.version,
    "checker_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
    "seal_sha256": expected,
    "members": len(data["files"]),
    "bytes": total,
    "errors": errors,
    "contract_selected": False,
    "implementation_selected": False,
    "GA_qualified": False,
}
(OUT / "preflight.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
assert not errors
