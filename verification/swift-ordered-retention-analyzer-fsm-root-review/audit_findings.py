#!/usr/bin/env python3
"""Read-only audit of the independent first-freeze correction evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "verification/swift-ordered-retention-analyzer-fsm-contract-review"
EXPECTED = "31460ea35508acfc5b0093f5f32874b1baa69f4377285ce4060c503f98d765e6"
raw = (BASE / "findings-freeze1-seal.json").read_bytes()
assert hashlib.sha256(raw).hexdigest() == EXPECTED
seal = json.loads(raw)
assert len(seal["members"]) == len({row["path"] for row in seal["members"]}) == 208
for row in seal["members"]:
    path = ROOT / row["path"]
    assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT)
    data = path.read_bytes()
    assert len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"]
assert sum(row["bytes"] for row in seal["members"]) == 5_273_092
repros = json.loads((BASE / "findings-freeze1-reproductions.json").read_bytes())
assert len(repros) == 5
assert all(row["shape"] is True and row["reason"] == "Observed" and row["type"] > 2**32 - 1 for row in repros[:4])
assert repros[4]["reason"] == "InternalPoisoned" and repros[4]["poisoned_state"] is None
assert repros[4]["finish_cap_boundary"] == "CapCutUnknownTail"
assert repros[4]["fullReplayAccepted"] is False and repros[4]["storedPrefixValidated"] is False
print(json.dumps({
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "python": platform.python_version(),
    "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "command": ["python3", "-B", str(Path(__file__).relative_to(ROOT))],
    "findings_seal_sha256": EXPECTED,
    "verified_members": 208,
    "verified_bytes": 5_273_092,
    "recorded_reproductions": 5,
    "required_corrections": ["R1 source type width", "R2 explicit retained candidate owner and accounting", "R3 poison propagation through finish"],
    "scope": "Contract/model correction evidence only; no Rust implementation or real replay authority",
    "original_producer_freeze_acceptance": False,
    "model_or_product_executed": False,
    "storedPrefixValidated": False,
    "fullReplayAccepted": False,
}, indent=2))
