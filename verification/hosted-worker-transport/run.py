#!/usr/bin/env python3
"""Collect only the isolated worker-client candidate; no hosted app startup."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import tarfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def command(name, args):
    started = time.monotonic()
    env = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8", "ERL_CRASH_DUMP": "/dev/null", "ERL_CRASH_DUMP_SECONDS": "0"}
    process = subprocess.Popen(args, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = process.communicate(timeout=40)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        out, err = process.communicate()
        (HERE / (name + ".stdout")).write_bytes(out[:2_097_152])
        (HERE / (name + ".stderr")).write_bytes(err[:2_097_152])
        raise RuntimeError("owned command exceeded outer deadline")
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    assert len(out) <= 2_097_152 and len(err) <= 2_097_152
    (HERE / (name + ".stdout")).write_bytes(out)
    (HERE / (name + ".stderr")).write_bytes(err)
    record = {"name": name, "args": args, "cwd": str(ROOT), "exit_code": process.returncode,
      "duration_ms": round((time.monotonic()-started)*1000), "stdout_sha256": sha(HERE/(name+".stdout")),
      "stderr_sha256": sha(HERE/(name+".stderr")), "cleanup": "owned process group disposed"}
    assert process.returncode == 0, "command failed: " + name
    return record

def inputs():
    files = list((HERE/"candidate").rglob("*.ex")) + list((HERE/"candidate").rglob("*.exs"))
    files += list(HERE.glob("*.exs")) + [HERE/"check_vectors.js", HERE/"run.py", HERE/"context-map.json", ROOT/"docs/hosted-worker-transport.md"]
    for dependency in ["mint", "jason", "hpax"]:
        files += [p for p in (ROOT/"hosted/_build/test/lib"/dependency/"ebin").glob("*") if p.is_file()]
    files += [ROOT/p for p in ["hosted/mix.exs", "hosted/mix.lock", "THIRD_PARTY.yml",
      "hosted/deps/mint/lib/mint/http1.ex", "hosted/deps/mint/lib/mint/http.ex",
      "hosted/deps/mint/lib/mint/core/transport/ssl.ex", "hosted/deps/jason/lib/jason.ex", "hosted/deps/jason/lib/decoder.ex"]]
    return sorted(set(files))

def main():
    paths = inputs()
    rows = [{"path": str(p.relative_to(ROOT)), "sha256": sha(p), "size": p.stat().st_size} for p in paths]
    digest = hashlib.sha256(json.dumps(rows, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
    save("source-map.json", {"schema": 1, "source_digest": digest, "sources": rows})
    archive = HERE/"candidate-inputs.tar.gz"
    with tarfile.open(archive, "w:gz") as output:
        for path in paths:
            output.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
    elixir = shutil.which("elixir")
    node = shutil.which("node")
    assert elixir and node
    prefix = [elixir, "--erl", "+S 2:2 +SDcpu 1 +SDio 1"]
    for dependency in ["mint", "jason", "hpax"]:
        prefix += ["-pa", str(ROOT/"hosted/_build/test/lib"/dependency/"ebin")]
    commands = []
    commands.append(command("source-revision", [shutil.which("git"), "rev-parse", "HEAD"]))
    commands.append(command("elixir-version", [elixir, "--version"]))
    commands.append(command("openssl-version", [shutil.which("openssl"), "version"]))
    commands.append(command("final-tests", prefix+[str(HERE/"compile_and_test.exs")]))
    result = json.loads((HERE/"final-tests.stdout").read_text().strip().splitlines()[-1])
    assert result["tests"] == 25 and result["failures"] == 0 and result["skipped"] == 0 and result["excluded"] == 0
    assert result["frozen_modules_loaded"] == []
    commands.append(command("generate-vectors", prefix+["-pa", str(HERE/"build/test"), str(HERE/"generate_vectors.exs")]))
    commands.append(command("check-vectors", [node, str(HERE/"check_vectors.js")]))
    vectors = json.loads((HERE/"check-vectors.stdout").read_text())
    assert vectors["vectors"] == 36
    commands.append(command("production-exports", prefix+[str(HERE/"production_exports.exs")]))
    exports = json.loads((HERE/"production-exports.stdout").read_text())
    assert exports["fixture_start_absent"] and exports["test_helpers_not_compiled"] and exports["frozen_modules_loaded"] == []
    artifacts = [{"path": str(p.relative_to(HERE)), "sha256": sha(p), "size": p.stat().st_size} for p in sorted((HERE/"build").rglob("*.beam"))]
    save("compiled-artifacts.json", {"schema": 1, "artifacts": artifacts})
    assert all(sha(ROOT/row["path"]) == row["sha256"] for row in rows), "candidate/dependency drift"
    save("commands.json", {"schema": 1, "commands": commands})
    shutil.rmtree(HERE/"build")
    save("receipt.json", {"schema": 1, "status": "isolated-client-candidate-awaiting-independent-review",
      "scope": "real-synthetic-TLS-client-only-no-controller-or-hosted-integration",
      "source_revision": (HERE/"source-revision.stdout").read_text().strip(), "platform": platform.platform(),
      "source_digest": digest, "input_count": len(rows), "archive_sha256": sha(archive),
      "commands_sha256": sha(HERE/"commands.json"), "source_map_sha256": sha(HERE/"source-map.json"),
      "compiled_artifacts_sha256": sha(HERE/"compiled-artifacts.json"),
      "cross_runtime_vectors_sha256": sha(HERE/"cross-runtime-vectors.json"), "test_result": result,
      "vectors": vectors, "production_exports": exports,
      "cleanup": {"probe_command_groups_disposed": True, "compiled_build_directory_removed": not (HERE/"build").exists(),
        "synthetic_key_directories_removed": "asserted-in-executable-fixture-setups",
        "socket_process_and_guard_cleanup": "executable-positive-negative-death-controls",
        "native_instances_started": False, "hosted_app_started": False, "cloud_or_database_started": False},
      "production_live_files_changed": [],
      "pending": ["independent implementation replay", "root live source/startup integration", "whole hosted release and CI",
        "hard resource limits and crash/core-dump deployment policy", "real controller persistence and provider execution",
        "source/tenant/artifact/result authority", "Cloudflare/Linux and external macOS isolation", "signing/native/dogfood/GA"]})
    print(json.dumps({"status": "isolated-candidate-passed", "tests": 25, "vectors": 36, "inputs": len(rows), "source_digest": digest}))

if __name__ == "__main__":
    main()
