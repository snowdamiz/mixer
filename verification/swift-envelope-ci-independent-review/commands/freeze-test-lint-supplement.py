#!/usr/bin/env python3
"""Freeze the isolated lint plan without reading candidate paths."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]
PREFIX = "verification/swift-envelope-ci-independent-review/test-lint-preaccess-supplement"
EXPECTED = {
    "verification/swift-envelope-ci-root-review/test-lint-selection-amendment.json": "1684fb9a329809c8c5bb9a4af20bbceaa7e4d68123a77e54a1115e3534277e52",
    "verification/swift-envelope-ci-root-review/independent-preaccess-admission.json": "00b5c6dff6013cf762fe2b4dbdef236a8377f4d59311eaaf45d6e19d8142d9d6",
    "verification/swift-envelope-ci-independent-review/preaccess-seal.json": "07af3bdb40573f9c566987a5c261c6403e9cb61153f4066f1ab35c44e1c1cc3e",
}


def info(relative):
    raw = (REPO / relative).read_bytes()
    return {"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def exclusive(relative, raw):
    with (REPO / relative).open("xb") as stream:
        stream.write(raw)


def write(relative, value):
    exclusive(relative, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


bindings = []
for relative, expected in EXPECTED.items():
    actual = info(relative)
    if actual["sha256"] != expected:
        raise RuntimeError("binding mismatch: " + relative)
    bindings.append(actual)
base = json.loads((REPO / "verification/swift-envelope-ci-independent-review/preaccess-seal.json").read_text())
for item in base["members"]:
    if info(item["path"]) != item:
        raise RuntimeError("base preaccess member changed: " + item["path"])
plan = json.loads((REPO / PREFIX / "plan.json").read_text())
if [x["id"] for x in plan["controls"]] != [f"L{n:02d}" for n in range(1, 7)]:
    raise RuntimeError("supplement control inventory mismatch")
at = datetime.now(timezone.utc).isoformat()
audit = {
    "schema": 1,
    "at": at,
    "status": "preaccess-lint-supplement-preparation-only",
    "command": "python3 -B verification/swift-envelope-ci-independent-review/commands/freeze-test-lint-supplement.py",
    "python_executable": sys.executable,
    "python_version": sys.version,
    "git_version": git("--version"),
    "source_revision": git("rev-parse", "HEAD"),
    "committed_tree": git("rev-parse", "HEAD^{tree}"),
    "os": platform.system(),
    "os_release": platform.release(),
    "machine": platform.machine(),
    "bindings_verified": bindings,
    "base_members_verified_unchanged": len(base["members"]),
    "supplement_controls_planned": 6,
    "candidate_accessed": False,
    "candidate_executed": False,
    "scope": "Selection and independent future control plan only; no candidate or original diagnostic reproduction.",
    "errors": [],
}
write(PREFIX + "/input-audit.json", audit)
log = "Verified lint amendment, preaccess admission and unchanged original five-member freeze; six supplemental controls planned; no candidate access or execution.\n"
exclusive(PREFIX + "/freeze.stdout", log.encode())
members = [info(relative) for relative in (
    PREFIX + "/plan.json",
    PREFIX + "/README.md",
    "verification/swift-envelope-ci-independent-review/commands/freeze-test-lint-supplement.py",
    PREFIX + "/input-audit.json",
    PREFIX + "/freeze.stdout",
)]
seal = {
    "schema": 1,
    "at": at,
    "status": "frozen-preaccess-lint-supplement-awaiting-root-candidate-admission",
    "base_preaccess_seal_sha256": EXPECTED["verification/swift-envelope-ci-independent-review/preaccess-seal.json"],
    "selected_amendment_sha256": EXPECTED["verification/swift-envelope-ci-root-review/test-lint-selection-amendment.json"],
    "member_count": len(members),
    "total_bytes": sum(x["bytes"] for x in members),
    "members": members,
    "supplement_control_count": 6,
    "base_control_count": 40,
    "candidate_accessed": False,
    "candidate_executed": False,
    "candidate_accepted": False,
    "storedPrefixValidated": False,
    "fullReplayAccepted": False,
    "semanticMetricsValid": False,
    "GA_qualified": False,
    "excluded": [PREFIX + "/seal.json", PREFIX + "/seal.sha256"],
}
write(PREFIX + "/seal.json", seal)
digest = info(PREFIX + "/seal.json")["sha256"]
exclusive(PREFIX + "/seal.sha256", (digest + "  " + PREFIX + "/seal.json\n").encode())
print(log, end="")
print(json.dumps({"seal_sha256": digest, "members": len(members), "member_bytes": seal["total_bytes"], "supplement_controls": 6}, sort_keys=True))
