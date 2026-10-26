#!/usr/bin/env python3
"""Freeze independent pre-access obligations; no candidate import or execution."""
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OWN = Path(__file__).resolve().parent
EXPECTED = {
    "verification/swift-ordered-retention-analyzer-envelope-root-review/implementation-accounting-addendum.json": "242b19079476ab4ee8437f4e7df04d8ebb584e899f7dab7bef537c8330f526dc",
    "verification/swift-ordered-retention-analyzer-envelope-root-review/correction-numeric-contract-selection.json": "199dfa75b024d04eeef28f2f40165115797a0bbb3d09a2405426172d8339867c",
    "verification/swift-ordered-retention-analyzer-envelope-correction/src/envelope.rs": "7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1",
    "verification/swift-ordered-retention-analyzer-envelope-correction/seal.json": "4ddff8237bd49cab9f6191be89e4764966e1af5dfa686bb931ac1372d1e98df1",
    "verification/swift-ordered-retention-analyzer-envelope-correction-final-accounting-review/seal.json": "929593356ebb871f4089e04ad1b71d216880d90a3da5151a5421c50553b985e8",
    "verification/swift-ordered-retention-analyzer-envelope-correction-final-accounting-review/findings.json": "2690663a6fec5e4a8829c23a21f6cf4377d0293c851ecc63287f8574b25c0e7e",
    "verification/swift-ordered-retention-analyzer-envelope-correction-final-accounting-review/commands/closure-1/absence-guard-funding-boundary.json": "ae74db6ec56cee3239bb9dccb49848fd10632b1c4009a9e506c59f5b009a97ba",
    "verification/swift-analyzer-envelope-correction-behavior-review/final-review/seal.json": "ee8b9ec9ef3b894e6bc40036aa8951528401414933097849f0c2e4a8aa879cff",
    "verification/swift-analyzer-envelope-correction-behavior-review/final-review/finding-R2.json": "8ccca728cc7523b2f0622db35dea665327d5e8bc7179e21dca01818f6bd56098",
    "docs/swift-ordered-retention-analyzer-envelope-correction-final-accounting-review.md": "fd22c390cbd821d41aebbea0365cf8ee597a9a0fa01f07bc85dc43c384766497",
}

def digest(data):
    return hashlib.sha256(data).hexdigest()

inputs = []
for name, expected in EXPECTED.items():
    data = (ROOT / name).read_bytes()
    actual = digest(data)
    inputs.append({"path": name, "bytes": len(data), "sha256": actual, "expected_sha256": expected, "matches": actual == expected})
extra = "docs/swift-ordered-retention-analyzer-fsm-contract.md"
extra_bytes = (ROOT / extra).read_bytes()
inputs.append({"path": extra, "bytes": len(extra_bytes), "sha256": digest(extra_bytes), "purpose": "accepted atomic checks and refusal contract; historical numeric estimate is superseded"})
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
baseline = ROOT / "docs/swift-envelope-absent-state-accounting-review.md"
(OWN / "review-baseline.md").write_bytes(baseline.read_bytes())
receipt = {
    "schema": 1,
    "at": datetime.now(timezone.utc).isoformat(),
    "status": "pre-access-preparation-frozen" if all(i.get("matches", True) for i in inputs) else "input-identity-failure",
    "source_revision_context": head,
    "input_identity_digest": digest(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()),
    "command": [sys.executable, str(Path(__file__).resolve())],
    "tool": {"python": platform.python_version(), "executable": sys.executable},
    "inputs": inputs,
    "parent_source_sha256_supplied_by_root": "1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b",
    "prior_packet_full_member_admission": "root-owned; this lane checked only the listed exact source and seal/file identities",
    "observed_failure": "Existing source privately charges425 before absent-length return and caller rejects funded poison0; old F1/R2 remain unmodified.",
    "commands_already_observed": [
        {"command": "cat AGENTS.md", "exit": 0, "scope": "current repository rules and pause"},
        {"command": "rg -n Mixer|envelope|accounting|absent /Users/andreyyurlov/.codex/memories/MEMORY.md", "exit": 0, "scope": "quick memory lookup; no task-specific envelope evidence used"},
        {"command": "git status --short", "exit": 0, "scope": "dirty shared checkout; no files outside assigned ownership modified"},
        {"command": "cat verification/swift-ordered-retention-analyzer-envelope-root-review/implementation-accounting-addendum.json", "exit": 0, "scope": "accepted absent/debit rule"},
        {"command": "cat verification/swift-ordered-retention-analyzer-envelope-root-review/correction-numeric-contract-selection.json verification/swift-ordered-retention-analyzer-envelope-correction-final-accounting-review/findings.json verification/swift-ordered-retention-analyzer-envelope-correction-final-accounting-review/commands/closure-1/absence-guard-funding-boundary.json", "exit": 0, "scope": "selected numbers and failed accounting boundary"},
        {"command": "cat verification/swift-analyzer-envelope-correction-behavior-review/final-review/finding-R2.json", "exit": 0, "scope": "immutable observed absent-state failure"},
        {"command": "sed -n '1,185p' verification/swift-ordered-retention-analyzer-envelope-correction/src/envelope.rs", "exit": 0, "scope": "frozen baseline entry and leaf"},
        {"command": "sed -n '270,335p' verification/swift-ordered-retention-analyzer-envelope-correction/src/envelope.rs", "exit": 0, "scope": "frozen baseline validator and dispatch"},
        {"command": "sed -n '303,326p' docs/swift-ordered-retention-analyzer-fsm-contract.md", "exit": 0, "scope": "accepted candidate/atomicity contract"},
        {"command": "python3 --version", "exit": 0, "output": "Python 3.14.8"},
        {"command": "shasum -a 256 [ten exact inputs enumerated in receipt inputs]", "exit": 0, "scope": "listed identities matched before authoring"}
    ],
    "scope": "Offline source/contract/evidence reads, standard hashing and assigned artifact authoring only; no forthcoming correction candidate access, producer script import/execution, compilation or product runtime.",
    "paused": ["computer use", "capture", "UI", "native runtime", "simulator/emulator", "phones", "process discovery"],
    "acceptance": {"proposal": False, "accounting": False, "behavior": False, "product": False, "GA": False}
}
(OWN / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
members = []
for path in sorted(OWN.iterdir()):
    if path.is_file() and path.name != "seal.json":
        data = path.read_bytes()
        members.append({"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": digest(data)})
seal = {"schema": 1, "status": receipt["status"], "members": members, "member_count": len(members), "total_bytes": sum(m["bytes"] for m in members), "scope": receipt["scope"]}
(OWN / "seal.json").write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": receipt["status"], "seal": str((OWN / "seal.json").relative_to(ROOT)), "seal_sha256": digest((OWN / "seal.json").read_bytes()), "members": len(members), "input_identity_digest": receipt["input_identity_digest"]}, sort_keys=True))
if receipt["status"] != "pre-access-preparation-frozen":
    raise SystemExit(1)
