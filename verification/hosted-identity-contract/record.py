#!/usr/bin/env python3
"""Record bounded declaration/host-reference checks; no hosted auth implementation."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def command(name: str, argv: list[str], cwd: Path, expected: int = 0) -> dict:
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    clock = time.monotonic()
    try:
        run = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=180)
        code, stdout, stderr, timed_out = run.returncode, run.stdout, run.stderr, False
    except subprocess.TimeoutExpired as failure:
        code, stdout, stderr, timed_out = None, failure.stdout or b"", failure.stderr or b"", True
    log = OUT / "commands" / name
    log.parent.mkdir(parents=True, exist_ok=True)
    log.with_suffix(".stdout").write_bytes(stdout)
    log.with_suffix(".stderr").write_bytes(stderr)
    result = {
        "name": name,
        "command": argv,
        "working_directory": str(cwd),
        "started_at_utc": started,
        "elapsed_seconds": round(time.monotonic() - clock, 3),
        "exit_code": code,
        "expected_exit_code": expected,
        "timed_out": timed_out,
        "passed": code == expected and not timed_out,
        "stdout": str(log.with_suffix(".stdout").relative_to(ROOT)),
        "stdout_sha256": digest(stdout),
        "stderr": str(log.with_suffix(".stderr").relative_to(ROOT)),
        "stderr_sha256": digest(stderr),
    }
    if name == "forged-identity-negative":
        result["expected_diagnostic_found"] = (
            b"key :role not found" in stderr
            and b"MixerHostedContractSpecimen.ForbiddenRoleClaim.forged/0" in stderr
        )
        result["passed"] = result["passed"] and result["expected_diagnostic_found"]
    if name == "contract-whitespace":
        result["expected_clean_output"] = not stdout and not stderr
        result["passed"] = result["passed"] and result["expected_clean_output"]
    print(json.dumps(result), flush=True)
    return result


manifest = json.loads((OUT / "input-manifest.json").read_text())
drift_review = json.loads((OUT / "plan-drift-review.json").read_text())
manifest_valid = digest(json.dumps(manifest["inputs"], sort_keys=True, separators=(",", ":")).encode()) == manifest["input_manifest_sha256"]
input_checks = []
for entry in manifest["inputs"]:
    captured = (OUT / "inputs" / entry["path"]).read_bytes()
    current = (ROOT / entry["path"]).read_bytes()
    current_hash = digest(current)
    matched = current_hash == entry["sha256"]
    reviewed = entry["path"] == drift_review["path"] and current_hash == drift_review["reviewed_final_sha256"]
    input_checks.append({
        "path": entry["path"], "snapshot_valid": digest(captured) == entry["sha256"],
        "current_sha256": current_hash, "current_matches_snapshot": matched,
        "current_input_reviewed": matched or reviewed,
    })

results = []
for name, argv, cwd, expected in [
    ("python-version", ["python3", "--version"], ROOT, 0),
    ("elixir-version", ["elixir", "--version"], ROOT, 0),
    ("go-version", ["go", "version"], ROOT, 0),
    ("git-version", ["git", "--version"], ROOT, 0),
    ("declaration-tests", ["elixir", str(OUT / "contract_specimen_test.exs")], ROOT, 0),
    ("forged-identity-negative", ["elixir", str(OUT / "forged_identity_negative.exs")], ROOT, 1),
    ("go-reference-race", ["go", "test", "-race", "./release", "-run",
                            "TestConfigOwnership|TestTenantRBACAndNoCredentialPublicPath", "-count=1"],
     ROOT / "services", 0),
    ("contract-whitespace", ["git", "diff", "--no-index", "--check", "--", "/dev/null",
                              "docs/hosted-identity-contract.md"], ROOT, 1),
]:
    results.append(command(name, argv, cwd, expected))

artifact_paths = [ROOT / "docs/hosted-identity-contract.md"] + [
    p for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "receipt.json"
]
artifacts = [
    {"path": str(p.relative_to(ROOT)), "sha256": digest(p.read_bytes()), "bytes": p.stat().st_size}
    for p in artifact_paths
]
receipt = {
    "schema": 1,
    "scope": "Hosted identity contract + Elixir declaration feasibility + existing Go host regressions only",
    "captured_input_revision": manifest["source_revision"],
    "final_observed_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "input_manifest_sha256": manifest["input_manifest_sha256"],
    "input_manifest_valid": manifest_valid,
    "input_checks": input_checks,
    "input_drift_reviews": [drift_review],
    "commands": results,
    "artifacts": artifacts,
    "all_expected_results": manifest_valid and all(x["passed"] for x in results) and all(
        x["snapshot_valid"] and x["current_input_reviewed"] for x in input_checks
    ),
    "limitations": [
        "Declaration tests verify only module/type/data-shape feasibility; no authentication or authorization is implemented.",
        "The expected Elixir compile failure is a field-shape check, not an unforgeability or isolation proof.",
        "Go race tests exercise the existing local service; no new hosted integration, provider, SQL membership or deployment was tested.",
        "No mocks are counted as integration or gate evidence; no production or GA gate is passed.",
        "Native UI/runtime, simulator/emulator and device activity are paused and were not attempted.",
        "No cloud/identity provider, real credentials, external messages, migration, commit or push was performed by this lane.",
        "Current source revision may advance through other active lanes; per-file snapshot hashes bind the reviewed input.",
    ],
    "cleanup": "No simulator, emulator, UI frontend, database instance or provider resource was started. Test subprocesses exited.",
}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
raise SystemExit(0 if receipt["all_expected_results"] else 1)
