#!/usr/bin/env python3
"""Rebuild this review's isolated source closure without modifying the checkout.

The baseline is intentionally expected to fail the ownership contract. Its race
probes must also report DATA RACE. Candidate checks must pass. Go dependencies
are pinned by the archived go.mod/go.sum; a populated module cache is required
when network access is unavailable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(archive: str, destination: Path) -> None:
    with tarfile.open(ROOT / archive) as source:
        source.extractall(destination, filter="data")


def run(command: list[str], cwd: Path, expected_failure: bool = False,
        race_required: bool = False, required_output: str = "") -> bool:
    print("COMMAND:", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    print(result.stdout, end="", flush=True)
    expected = result.returncode != 0 if expected_failure else result.returncode == 0
    return (expected and (not race_required or "WARNING: DATA RACE" in result.stdout)
            and required_output in result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["baseline", "candidate", "all"], default="all", nargs="?")
    args = parser.parse_args()
    inputs = json.loads((ROOT / "candidate-inputs.json").read_text())
    archives = {
        "baseline-services.tar.gz": inputs["baseline_archive_sha256"],
        "candidate-delta.tar.gz": inputs["candidate_delta_sha256"],
        "support-inputs.tar.gz": inputs["support_archive_sha256"],
    }
    for name, expected in archives.items():
        if digest(ROOT / name) != expected:
            raise SystemExit("Archive digest mismatch: " + name)
    for name, expected in inputs["review_probe_sha256"].items():
        if digest(ROOT / name) != expected:
            raise SystemExit("Review probe digest mismatch: " + name)

    success = True
    with tempfile.TemporaryDirectory(prefix="mixer-config-ownership-reproduce-") as temporary:
        for mode in (["baseline", "candidate"] if args.mode == "all" else [args.mode]):
            source = Path(temporary) / mode
            source.mkdir()
            extract("baseline-services.tar.gz", source)
            if mode == "candidate":
                extract("candidate-delta.tar.gz", source)
                extract("support-inputs.tar.gz", source)
                for name, expected in inputs["candidate_source_files"].items():
                    if digest(source / name) != expected:
                        raise SystemExit("Candidate source digest mismatch: " + name)
                for name, expected in inputs["support_files"].items():
                    if digest(source / name) != expected:
                        raise SystemExit("Support input digest mismatch: " + name)
                shutil.copy2(ROOT / "config_snapshot_internal_test.go",
                             source / "services/release/independent_snapshot_review_test.go")
            probe = source / "services/reviewprobe"
            probe.mkdir()
            shutil.copy2(ROOT / "config_ownership_public_test.go", probe)
            cwd = source / "services"
            if mode == "baseline":
                success &= run(["go", "test", "-count=1", "-v", "./reviewprobe", "-run",
                                "TestPublicConfig(Token|Trust|Host|V3)"], cwd, expected_failure=True,
                               required_output="reader after caller elevates role: HTTP 201")
                for field in ["token", "root-slice", "root-key", "host-slice", "host-map"]:
                    success &= run(["go", "test", "-race", "-count=1", "-v", "./reviewprobe", "-run",
                                    "TestPublicConfigConcurrentCallerMutationAfterConstruction/" + field + "$"],
                                   cwd, expected_failure=True, race_required=True)
            else:
                success &= run(["go", "test", "-race", "-count=1", "-v", "./reviewprobe"], cwd)
                success &= run(["go", "test", "-race", "-count=1", "-v", "./release", "-run",
                                "Test(ConfigOwnership|IndependentSnapshot)"], cwd)
                success &= run(["go", "test", "-race", "-count=1", "./..."], cwd)
                success &= run(["go", "vet", "./..."], cwd)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
