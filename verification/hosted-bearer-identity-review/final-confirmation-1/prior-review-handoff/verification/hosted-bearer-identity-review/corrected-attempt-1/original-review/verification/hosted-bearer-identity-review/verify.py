#!/usr/bin/env python3
"""Bounded independent host review; no owner/application/provider/database startup."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HOSTED = ROOT / "hosted"
BASE_TESTS = ["test/mixer_hosted_web/bearer_identity_test.exs", "test/mixer_hosted/identity/access_token_verifier_test.exs"]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inventory():
    paths = [*HOSTED.joinpath("lib").rglob("*.ex"), *HOSTED.joinpath("test/support").rglob("*.ex"),
             *HOSTED.joinpath("config").rglob("*.exs"), *[HOSTED / name for name in BASE_TESTS],
             HOSTED / "mix.exs", HOSTED / "mix.lock", HOSTED / "test/test_helper.exs",
             ROOT / "AGENTS.md", ROOT / "PLAN.md", ROOT / "docs/hosted-bearer-identity-transport.md",
             ROOT / "docs/hosted-identity-contract.md", HERE / "independent_controls_test.exs", HERE / "verify.py",
             ROOT / "verification/hosted-bearer-identity-transport/handoff-sha256.json"]
    files = {str(p.relative_to(ROOT)): digest(p) for p in sorted(set(paths))}
    # Dependency trees are independently copied, never compiled in place.
    deps = {str(p.relative_to(HOSTED / "deps")): digest(p) for p in sorted((HOSTED / "deps").rglob("*")) if p.is_file()}
    canonical = json.dumps({"files": files, "dependencies": deps}, sort_keys=True, separators=(",", ":")).encode()
    return {"sha256": hashlib.sha256(canonical).hexdigest(), "files": files, "dependencies": deps}

def main():
    if (HERE / "receipt.json").exists():
        raise SystemExit("Review receipt exists; preserve it and use a new owned attempt directory.")
    record = {"schema": 1, "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "scope": "Independent bounded copied-source bearer Plug review; baseline and seven review groups only. No application/owner/provider/database/network/native/frozen-lane execution.",
              "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "source_before": inventory(), "commands": []}
    seal_path = ROOT / "verification/hosted-bearer-identity-transport/handoff-sha256.json"
    seal = json.loads(seal_path.read_text())
    record["producer_seal"] = {"path": str(seal_path.relative_to(ROOT)), "count": len(seal),
                               "mismatches": [name for name, expected in seal.items() if digest(ROOT / name) != expected]}
    scratch = Path(tempfile.mkdtemp(prefix="owned-review-copy-", dir=HERE))
    copied = scratch / "hosted"
    copied.mkdir()
    try:
        for name in ["lib", "config", "deps"]:
            shutil.copytree(HOSTED / name, copied / name, symlinks=False)
        for name in ["mix.exs", "mix.lock", "test/test_helper.exs", *BASE_TESTS]:
            (copied / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(HOSTED / name, copied / name)
        shutil.copytree(HOSTED / "test/support", copied / "test/support")
        shutil.copy2(HERE / "independent_controls_test.exs", copied / "test/independent_controls_test.exs")
        build = copied / "_build" / ("independent-" + scratch.name.removeprefix("owned-review-copy-"))
        env = dict(os.environ, MIX_ENV="test", MIX_BUILD_PATH=str(build), HEX_OFFLINE="1")
        record["environment"] = {key: env[key] for key in ["MIX_ENV", "MIX_BUILD_PATH", "HEX_OFFLINE"]}
        commands = [["elixir", "--version"], ["mix", "--version"],
                    ["mix", "test", "--no-start", *BASE_TESTS, "--seed", "25067", "--trace"],
                    ["mix", "test", "--no-start", "test/independent_controls_test.exs", "--seed", "25068", "--trace"]]
        for index, argv in enumerate(commands, 1):
            log = HERE / f"command-{index}.log"
            with log.open("wb") as output:
                process = subprocess.run(argv, cwd=copied, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=180)
            record["commands"].append({"argv": argv, "cwd": str(copied), "exit_code": process.returncode,
                                        "raw_output": log.name, "raw_output_sha256": digest(log)})
            print(f"command {index}: exit {process.returncode}; {log.name}", flush=True)
            if process.returncode and index < 4:
                break
    finally:
        record["source_after"] = inventory()
        record["source_stable"] = record["source_before"] == record["source_after"]
        shutil.rmtree(scratch)
        record["cleanup"] = {"owned_copy_path": str(scratch), "removed": not scratch.exists(),
                             "native_instances_started": 0, "network_or_database_started": False,
                             "live_producer_sources_edited": False}
        record["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        record["all_controls_passed"] = len(record["commands"]) == 4 and all(c["exit_code"] == 0 for c in record["commands"]) and record["source_stable"] and not record["producer_seal"]["mismatches"]
        (HERE / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    return 0 if record["all_controls_passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
