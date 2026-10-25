#!/usr/bin/env python3
"""Independent narrow re-review of the corrected sealed bearer prerequisite."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
HOSTED = ROOT / "hosted"
ORIGINAL_CONTROL = HERE.parent / "independent_controls_test.exs"
BASE_TESTS = ["test/mixer_hosted_web/bearer_identity_test.exs", "test/mixer_hosted/identity/access_token_verifier_test.exs"]
EXPECTED_SEAL = "7e79a878f7e15ddf8893af8581ea9f6a22273fbb17b93313b609d8fce1b4a4f7"

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inventory():
    paths = [*HOSTED.joinpath("lib").rglob("*.ex"), *HOSTED.joinpath("test/support").rglob("*.ex"),
             *HOSTED.joinpath("config").rglob("*.exs"), *[HOSTED / name for name in BASE_TESTS],
             HOSTED / "mix.exs", HOSTED / "mix.lock", HOSTED / "test/test_helper.exs",
             ROOT / "AGENTS.md", ROOT / "PLAN.md", ROOT / "docs/hosted-bearer-identity-transport.md",
             ROOT / "docs/hosted-identity-contract.md", ORIGINAL_CONTROL, HERE / "additional_controls_test.exs", HERE / "verify.py",
             ROOT / "verification/hosted-bearer-identity-transport/handoff-sha256.json"]
    files = {str(p.relative_to(ROOT)): digest(p) for p in sorted(set(paths))}
    deps = {str(p.relative_to(HOSTED / "deps")): digest(p) for p in sorted((HOSTED / "deps").rglob("*")) if p.is_file()}
    canonical = json.dumps({"files": files, "dependencies": deps}, sort_keys=True, separators=(",", ":")).encode()
    return {"sha256": hashlib.sha256(canonical).hexdigest(), "files": files, "dependencies": deps}

def main():
    if (HERE / "receipt.json").exists():
        raise SystemExit("Receipt exists; preserve this attempt.")
    seal_path = ROOT / "verification/hosted-bearer-identity-transport/handoff-sha256.json"
    assert digest(seal_path) == EXPECTED_SEAL
    seal = json.loads(seal_path.read_text())
    mismatches = [name for name, expected in seal.items() if digest(ROOT / name) != expected]
    assert not mismatches, mismatches
    record = {"schema": 1, "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "scope": "Independent corrected candidate copied-source bearer Plug and pure verifier only; original seven review groups plus three narrow parameter/duplicate groups. No owner/application/provider/database/network/native/frozen-lane execution.",
              "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "entry_command": ["python3", str(Path(__file__).resolve().relative_to(ROOT))],
              "python_version": sys.version, "platform": platform.platform(),
              "source_before": inventory(), "commands": [],
              "producer_seal": {"sha256": EXPECTED_SEAL, "members": len(seal), "mismatches": mismatches},
              "original_controls_sha256": digest(ORIGINAL_CONTROL)}
    scratch = Path(tempfile.mkdtemp(prefix="owned-corrected-copy-", dir=HERE))
    copied = scratch / "hosted"
    copied.mkdir()
    try:
        for name in ["lib", "config", "deps"]:
            shutil.copytree(HOSTED / name, copied / name, symlinks=False)
        for name in ["mix.exs", "mix.lock", "test/test_helper.exs", *BASE_TESTS]:
            (copied / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(HOSTED / name, copied / name)
        shutil.copytree(HOSTED / "test/support", copied / "test/support")
        shutil.copy2(ORIGINAL_CONTROL, copied / "test/original_independent_controls_test.exs")
        shutil.copy2(HERE / "additional_controls_test.exs", copied / "test/additional_controls_test.exs")
        for name in ["hosted/lib/mixer_hosted_web/plugs/bearer_identity.ex", "hosted/test/mixer_hosted_web/bearer_identity_test.exs", "docs/hosted-bearer-identity-transport.md"]:
            destination = HERE / "candidate" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, destination)
        build = copied / "_build" / ("independent-" + scratch.name.removeprefix("owned-corrected-copy-"))
        env = dict(os.environ, MIX_ENV="test", MIX_BUILD_PATH=str(build), HEX_OFFLINE="1")
        record["environment"] = {key: env[key] for key in ["MIX_ENV", "MIX_BUILD_PATH", "HEX_OFFLINE"]}
        commands = [["elixir", "--version"], ["mix", "--version"],
                    ["mix", "test", "--no-start", *BASE_TESTS, "--seed", "25167", "--trace"],
                    ["mix", "test", "--no-start", "test/original_independent_controls_test.exs", "--seed", "25168", "--trace"],
                    ["mix", "test", "--no-start", "test/additional_controls_test.exs", "--seed", "25169", "--trace"]]
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
        record["all_controls_passed"] = len(record["commands"]) == 5 and all(c["exit_code"] == 0 for c in record["commands"]) and record["source_stable"]
        (HERE / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    return 0 if record["all_controls_passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
