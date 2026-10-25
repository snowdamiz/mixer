#!/usr/bin/env python3
"""Replay frozen worker client inputs only; never start the hosted application."""
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
PRODUCER = ROOT / "verification/hosted-worker-transport"
EXPECTED_DIGEST = "9d561357f923df55ef5ec7f55d321d6f973dc6f22e2d9f2af35d9907541b8499"
EXPECTED_ARCHIVE = "4d231490a8fefca6be3cd1e6a263c95374fc50782a0cb93b8bc0cef2598bac56"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def command(name, args, timeout=60):
    env = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8", "ERL_CRASH_DUMP": "/dev/null", "ERL_CRASH_DUMP_SECONDS": "0"}
    started = time.monotonic()
    timed_out = False
    with (HERE / (name + ".stdout")).open("wb") as out, (HERE / (name + ".stderr")).open("wb") as err:
        proc = subprocess.Popen(args, cwd=HERE, env=env, stdout=out, stderr=err, start_new_session=True)
        try:
            proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    assert (HERE / (name + ".stdout")).stat().st_size <= 2_097_152 and (HERE / (name + ".stderr")).stat().st_size <= 2_097_152
    return {"name": name, "args": args, "cwd": str(HERE), "exit_code": proc.returncode,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "stdout_sha256": sha(HERE / (name + ".stdout")), "stderr_sha256": sha(HERE / (name + ".stderr")),
            "cleanup": "owned process group disposed", "outer_timeout": timed_out}

def main():
    source_map = json.loads((PRODUCER / "source-map.json").read_text())
    rows = source_map["sources"]
    digest = hashlib.sha256(json.dumps(rows, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
    assert digest == source_map["source_digest"] == EXPECTED_DIGEST and len(rows) == 86
    archive = PRODUCER / "candidate-inputs.tar.gz"
    assert sha(archive) == EXPECTED_ARCHIVE
    frozen = {str(p.relative_to(PRODUCER)): sha(p) for p in PRODUCER.rglob("*") if p.is_file()}
    target = HERE / "inputs"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir()
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        assert {m.name for m in members} == {r["path"] for r in rows}
        for member in members:
            assert member.isfile() and not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
            path = target / member.name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(tar.extractfile(member).read())
    assert all(sha(target / r["path"]) == r["sha256"] for r in rows)
    save("input-binding.json", {"schema": 1, "source_digest": digest, "archive_sha256": EXPECTED_ARCHIVE,
        "source_revision": "44048403df8c5571d29b9558474edfaa8265787f", "input_count": len(rows), "sources": rows})
    elixir = shutil.which("elixir")
    assert elixir
    prefix = [elixir, "--erl", "+S 2:2 +SDcpu 1 +SDio 1"]
    for dep in ["mint", "jason", "hpax"]:
        prefix += ["-pa", str(target / "hosted/_build/test/lib" / dep / "ebin")]
    records = [command("elixir-version", [elixir, "--version"]), command("openssl-version", [shutil.which("openssl"), "version"])]
    records.append(command("producer-replay", prefix + [str(HERE / "compile_and_test.exs"), "baseline"]))
    records.append(command("independent-tests", prefix + [str(HERE / "compile_and_test.exs"), "independent"]))
    save("commands.json", {"schema": 1, "commands": records})
    assert all(r["exit_code"] == 0 for r in records), "test failure retained in outputs"
    assert all(sha(PRODUCER / p) == h for p, h in frozen.items()), "producer changed during independent replay"
    compiled = [{"path": str(p.relative_to(HERE)), "sha256": sha(p), "size": p.stat().st_size} for p in sorted((HERE / "build").rglob("*.beam"))]
    save("compiled-artifacts.json", {"schema": 1, "artifacts": compiled})
    shutil.rmtree(HERE / "build")
    shutil.rmtree(target)
    save("replay-summary.json", {"schema": 1, "platform": platform.platform(), "source_digest": digest,
        "archive_sha256": EXPECTED_ARCHIVE, "input_count": len(rows), "producer_immutable": True,
        "baseline": json.loads((HERE / "producer-replay.stdout").read_text().strip().splitlines()[-1]),
        "independent": json.loads((HERE / "independent-tests.stdout").read_text().strip().splitlines()[-1]),
        "commands_sha256": sha(HERE / "commands.json"), "input_binding_sha256": sha(HERE / "input-binding.json"),
        "compiled_artifacts_sha256": sha(HERE / "compiled-artifacts.json"),
        "cleanup": {"owned_command_groups_disposed": True, "build_directory_removed": True, "extracted_input_directory_removed": True,
            "cloud_database_hosted_app_native_started": False}})
    print(json.dumps({"status": "independent-replay-complete", "source_digest": digest}))

if __name__ == "__main__":
    main()
