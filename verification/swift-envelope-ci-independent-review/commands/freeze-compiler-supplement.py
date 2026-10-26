#!/usr/bin/env python3
"""Seal compiler preaccess controls and read only selected identity evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]
PREFIX = "verification/swift-envelope-ci-independent-review/compiler-preaccess-supplement"
ROOT_PACKET = "verification/swift-envelope-ci-root-review/"
EXPECTED = {
    ROOT_PACKET + "compiler-qualification-selection-amendment.json": "b7c482646943a34ffae810cfad38962a4b50a455b37d2deab7ea80e38d805e5b",
    ROOT_PACKET + "test-lint-preaccess-admission.json": "ec2dfd0b6dd748664633760ebc8faa1188fd4eeb237869afd3b2a32e39996826",
    ROOT_PACKET + "prior-ci-toolchain/download-receipt.json": "a6dbff9cb9a277de51a18f106600cbd5ce605218c9abbcb5cd6cd8b02aa89ba7",
    ROOT_PACKET + "prior-ci-toolchain/framing-receipt.json": "f777741dbef498051155f042e7838f6bf23ef7de04ebfa46340e24d042c383af",
    "verification/swift-envelope-ci-independent-review/preaccess-seal.json": "07af3bdb40573f9c566987a5c261c6403e9cb61153f4066f1ab35c44e1c1cc3e",
    "verification/swift-envelope-ci-independent-review/test-lint-preaccess-supplement/seal.json": "04d74cdd7295bf092a072ac64aac83c93f178e37f24f53c9c4a079b60b07a27b",
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
preserved_members = 0
for relative, expected in EXPECTED.items():
    actual = info(relative)
    if actual["sha256"] != expected:
        raise RuntimeError("binding mismatch: " + relative)
    bindings.append(actual)
    if relative.endswith(("/preaccess-seal.json", "/test-lint-preaccess-supplement/seal.json")):
        prior = json.loads((REPO / relative).read_text())
        for member in prior["members"]:
            if info(member["path"]) != member:
                raise RuntimeError("preserved freeze changed: " + member["path"])
            preserved_members += 1
prior_ci = json.loads((REPO / ROOT_PACKET / "prior-ci-toolchain/framing-receipt.json").read_text())
identity = prior_ci["rustc"]["identity"]
if identity["release"] != "1.98.1" or identity["host"] != "aarch64-apple-darwin":
    raise RuntimeError("prior framing identity differs from selected amendment")
plan = json.loads((REPO / PREFIX / "plan.json").read_text())
if [x["id"] for x in plan["controls"]] != [f"T{n:02d}" for n in range(1, 7)]:
    raise RuntimeError("compiler control inventory mismatch")
at = datetime.now(timezone.utc).isoformat()
audit = {
    "schema": 1,
    "at": at,
    "status": "compiler-preaccess-plan-only-no-candidate-access",
    "command": "python3 -B verification/swift-envelope-ci-independent-review/commands/freeze-compiler-supplement.py",
    "python_executable": sys.executable,
    "python_version": sys.version,
    "git_version": git("--version"),
    "source_revision": git("rev-parse", "HEAD"),
    "committed_tree": git("rev-parse", "HEAD^{tree}"),
    "os": platform.system(),
    "os_release": platform.release(),
    "machine": platform.machine(),
    "bindings_verified": bindings,
    "prior_sealed_members_preserved": preserved_members,
    "prior_ci_identity_observed": {"compiler": prior_ci["rustc"], "launcher": prior_ci["rustc_launcher"], "revision_before": prior_ci["revision_before"], "revision_after": prior_ci["revision_after"], "scope": "Prior framing identity only; no envelope qualification."},
    "supplement_controls_planned": 6,
    "candidate_accessed": False,
    "candidate_executed": False,
    "local_1_98_1_queried": False,
    "CI_1_98_1_envelope_qualified": False,
    "errors": [],
}
write(PREFIX + "/input-audit.json", audit)
log = "Verified compiler amendment/admission/prior-CI identity evidence and ten unchanged prior sealed members; six compiler controls planned; no candidate access or execution.\n"
exclusive(PREFIX + "/freeze.stdout", log.encode())
members = [info(relative) for relative in (
    PREFIX + "/plan.json",
    PREFIX + "/README.md",
    "verification/swift-envelope-ci-independent-review/commands/freeze-compiler-supplement.py",
    PREFIX + "/input-audit.json",
    PREFIX + "/freeze.stdout",
)]
seal = {
    "schema": 1,
    "at": at,
    "status": "frozen-compiler-preaccess-supplement-awaiting-root-candidate-admission",
    "compiler_amendment_sha256": EXPECTED[ROOT_PACKET + "compiler-qualification-selection-amendment.json"],
    "member_count": len(members),
    "total_bytes": sum(x["bytes"] for x in members),
    "members": members,
    "supplement_control_count": 6,
    "prior_control_count": 46,
    "candidate_accessed": False,
    "candidate_executed": False,
    "candidate_accepted": False,
    "CI_1_98_1_envelope_qualified": False,
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
