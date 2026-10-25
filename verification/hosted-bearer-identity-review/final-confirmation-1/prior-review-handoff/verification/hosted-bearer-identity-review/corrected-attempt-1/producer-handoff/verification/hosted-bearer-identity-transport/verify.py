#!/usr/bin/env python3
"""Run only the ordinary bearer HTTP and pure access-token verifier tests."""

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
TESTS = [
    "test/mixer_hosted_web/bearer_identity_test.exs",
    "test/mixer_hosted/identity/access_token_verifier_test.exs",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_inventory():
    # Root confirmed these are accepted live compiler inputs, separate from all
    # frozen verification lanes. Do not discover or load external fixtures.
    paths = [
        *HOSTED.joinpath("lib").rglob("*.ex"),
        *HOSTED.joinpath("test/support").rglob("*.ex"),
        *[HOSTED / name for name in TESTS],
        HOSTED / "test/test_helper.exs",
        HOSTED / "mix.exs",
        HOSTED / "mix.lock",
        ROOT / "docs/hosted-identity-contract.md",
        HOSTED / "deps/plug/lib/plug/conn.ex",
        HOSTED / "deps/plug/lib/plug/conn/utils.ex",
        HOSTED / "deps/plug/lib/plug/request_id.ex",
    ]
    inventory = {str(path.relative_to(ROOT)): digest(path) for path in sorted(set(paths))}
    canonical = json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()
    return {"sha256": hashlib.sha256(canonical).hexdigest(), "files": inventory}


def main():
    if (HERE / "receipt.json").exists():
        attempts = HERE / "prior-attempts"
        attempts.mkdir(exist_ok=True)
        previous = attempts / str(len(list(attempts.iterdir())) + 1)
        previous.mkdir()
        for path in [HERE / "receipt.json", *HERE.glob("command-*.log")]:
            shutil.move(path, previous / path.name)

    # Pinned JOSE expects the default _build/<environment>/lib/<app> depth
    # when Mix creates its relative include link. Keep isolation at that depth.
    build = Path(tempfile.mkdtemp(prefix="bearer-identity-", dir=HOSTED / "_build"))
    env = dict(os.environ, MIX_BUILD_PATH=str(build), MIX_ENV="test")
    record = {
        "schema": 1,
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Host-only ordinary Plug bearer identity and pure AccessTokenVerifier; no router, database, owner startup, JWKS, provider, native or frozen-lane execution.",
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_before": source_inventory(),
        "environment": {"MIX_ENV": "test", "MIX_BUILD_PATH": str(build)},
        "commands": [],
    }
    try:
        commands = [
            ["elixir", "--version"],
            ["mix", "--version"],
            ["mix", "format", "--check-formatted", "lib/mixer_hosted_web/plugs/bearer_identity.ex", TESTS[0]],
            ["mix", "test", "--no-start", *TESTS, "--seed", "6750", "--trace"],
        ]
        for index, argv in enumerate(commands):
            log = HERE / f"command-{index + 1}.log"
            with log.open("wb") as output:
                process = subprocess.run(argv, cwd=HOSTED, env=env, stdout=output, stderr=subprocess.STDOUT)
            record["commands"].append({
                "argv": argv,
                "cwd": str(HOSTED),
                "exit_code": process.returncode,
                "raw_output": log.name,
                "raw_output_sha256": digest(log),
            })
            print(f"command {index + 1}: exit {process.returncode}; {log.name}", flush=True)
            if process.returncode:
                break
    finally:
        record["source_after"] = source_inventory()
        record["source_stable"] = record["source_before"] == record["source_after"]
        shutil.rmtree(build)
        record["cleanup"] = {"owned_build_path": str(build), "removed": not build.exists(), "native_instances_started": 0, "network_or_database_started": False}
        record["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        record["passed"] = len(record["commands"]) == 4 and all(c["exit_code"] == 0 for c in record["commands"]) and record["source_stable"]
        (HERE / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
