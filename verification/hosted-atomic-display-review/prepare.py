#!/usr/bin/env python3
"""Read-only producer verification and owned exact-input replay preparation."""
import hashlib
import json
import pathlib
import shutil
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / "verification/hosted-atomic-display-correction"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    expected = {
        "receipt.json": "ebecf05358733c2a2069907ecc5e3e693ec9c484e594a8dd10a44eace76f8c91",
        "seal.json": "ae01864e0b82003141d627109c6a37a3a0bb7ec4b384193878b77ed28fa0b0a7",
        "probe/lib/codec.ex": "7152ab6d9c2fec56cd6e707ef09bb4f5fb3a8477edb7b0b5410a884278fe37ee",
    }
    for name, digest in expected.items():
        assert sha((PRODUCER / name).read_bytes()) == digest, name
    checks = []
    for name in ["hosted-atomic-storage-correction-review", "hosted-atomic-display-correction"]:
        argv = ["python3", "-B", str(ROOT / "verification" / name / "check.py")]
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
        checks.append({"argv": argv, "cwd": str(ROOT), "returncode": result.returncode,
                       "stdout": result.stdout, "stderr": result.stderr,
                       "stdout_sha256": sha(result.stdout.encode()),
                       "stderr_sha256": sha(result.stderr.encode())})
        assert result.returncode == 0, checks[-1]
    (HERE / "upstream-validation.json").write_text(json.dumps(checks, indent=2) + "\n")
    names = ["run.py", "accepted-baseline.mix.lock", "upstream-inputs.json", "build-display-corpus.py"]
    trees = ["probe", "legacy-services", "upstream"]
    for name in names:
        assert not (HERE / name).exists(), name
        shutil.copy2(PRODUCER / name, HERE / name)
    for name in trees:
        assert not (HERE / name).exists(), name
        shutil.copytree(PRODUCER / name, HERE / name)
    shutil.copy2(PRODUCER / "run.py", HERE / "replay-runner.py")
    # Freeze the exact candidate and contract closure independently of future lanes.
    inputs = []
    selected = ["docs/hosted-atomic-display-correction-contract.md",
                "verification/hosted-atomic-storage-root-review/display-correction-direction.json",
                "docs/hosted-atomic-display-correction.md",
                "verification/hosted-atomic-storage-correction-review/receipt.json",
                "verification/hosted-atomic-storage-correction-review/seal.json",
                "verification/hosted-atomic-storage-correction-review/findings.json"]
    manifest = json.loads((PRODUCER / "artifact-manifest.json").read_text())
    selected += [item["path"] for item in manifest["files"]]
    selected += [str((PRODUCER / name).relative_to(ROOT)) for name in ["seal.json", "artifact-manifest.json"]]
    selected += [item["path"] for item in json.loads((PRODUCER / "upstream-inputs.json").read_text())["files"]]
    for name in sorted(set(selected)):
        body = (ROOT / name).read_bytes()
        inputs.append({"path": name, "bytes": len(body), "sha256": sha(body)})
    (HERE / "review-inputs.json").write_text(json.dumps({"files": inputs}, indent=2) + "\n")
    print(json.dumps({"producer_bindings": len(manifest["files"]),
                      "upstream_bindings": 488, "review_bindings": len(inputs),
                      "copied_runner_exact": (HERE / "run.py").read_bytes() == (PRODUCER / "run.py").read_bytes(),
                      "producer_frozen_hashes_match": expected}))


if __name__ == "__main__":
    main()
