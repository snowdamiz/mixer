#!/usr/bin/env python3
"""Retain the ordinary contract inputs used before the producer source freeze."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "preparation"
FILES = [
    "AGENTS.md",
    "PLAN.md",
    "docs/hosted-identity-contract.md",
    "docs/hosted-customer-authorization.md",
    "docs/hosted-customer-authorization-correction.md",
    "docs/hosted-customer-authorization-correction-review.md",
    "hosted/lib/mixer_hosted/authorization/policy.ex",
    "hosted/lib/mixer_hosted/authorization/repository.ex",
    "hosted/lib/mixer_hosted/authorization/scope.ex",
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/mix.lock",
]
if OUT.exists():
    raise SystemExit("preparation already exists; preserve historical input bytes")
OUT.mkdir(parents=True)
manifest = []
for name in FILES:
    data = (ROOT / name).read_bytes()
    target = OUT / "inputs" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    manifest.append({"path": name, "bytes": len(data),
                     "sha256": hashlib.sha256(data).hexdigest()})
versions = []
env = dict(os.environ, ERL_FLAGS="+S 2:2")
for cmd in [["elixir", "--version"], ["psql", "--version"],
            ["pg_ctl", "--version"], ["python3", "--version"]]:
    run = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    versions.append({"command": cmd, "exit_code": run.returncode,
                     "stdout": run.stdout, "stderr": run.stderr})
digest = hashlib.sha256(json.dumps(manifest, sort_keys=True,
                                  separators=(",", ":")).encode()).hexdigest()
(OUT / "receipt.json").write_text(json.dumps({
    "status": "contract_preparation_only",
    "source_revision": "cb56d4b9d979ffc02554be991466a180e7882cd3",
    "source_revision_authority": "supplied by root; not queried by this script",
    "command": ["python3", str(Path(__file__).resolve())],
    "platform": platform.platform(), "versions": versions,
    "inputs": manifest, "input_manifest_sha256": digest,
    "database_executed": False, "candidate_source_read": False,
    "native_instances_created": False,
    "git_mutations": False,
    "limits": ["no candidate acceptance", "no database evidence",
               "time checks use facade captured now, not a new trusted clock"]
}, indent=2) + "\n")
print(json.dumps({"status": "contract_preparation_only",
                  "input_count": len(manifest), "input_digest": digest}))
