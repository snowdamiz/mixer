#!/usr/bin/env python3
"""Independent frozen-source headless foundation review; no product edits."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import socket
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
OWNER = ROOT / "verification/phoenix-foundation/candidate-2"
PG = Path("/opt/homebrew/opt/postgresql@17/bin")
commands = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, argv, cwd, env=None, expect=0):
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    log = OUT / "commands" / (name + ".log")
    log.write_bytes(result.stdout)
    commands.append({"name": name, "argv": list(map(str, argv)), "cwd": str(cwd),
                     "started_at_utc": stamp, "exit_code": result.returncode,
                     "expected_exit_code": expect, "output": str(log.relative_to(ROOT)),
                     "sha256": sha(log)})
    if result.returncode != expect:
        raise RuntimeError(f"{name} returned {result.returncode}; inspect {log}")


owner = json.loads((OWNER / "receipt.json").read_text())
assert sha(OWNER / "source.tar.gz") == owner["source_archive_sha256"]
shutil.copyfile(OWNER / "source.tar.gz", OUT / "reviewed-source.tar.gz")
shutil.copyfile(OWNER / "receipt.json", OUT / "owner-candidate-2-receipt.json")
scratch = Path(tempfile.mkdtemp(prefix="mixer-foundation-independent-review-"))
source = scratch / "source"
source.mkdir()
with tarfile.open(OUT / "reviewed-source.tar.gz") as archive:
    archive.extractall(source, filter="data")
assert {str(p.relative_to(source)): sha(p) for p in source.rglob("*") if p.is_file()} == owner["inputs"]
(source / "deps").symlink_to(ROOT / "hosted/deps", target_is_directory=True)
env = {k: v for k, v in os.environ.items() if not k.startswith("MIXER_")}
env.update(MIX_ENV="test", MIX_BUILD_PATH=str(scratch / "build"))
status = "failed"
cleanup = {}
try:
    run("elixir-version", ["elixir", "--version"], source)
    run("postgres-version", [PG / "postgres", "--version"], source)
    run("initdb", [PG / "initdb", "-D", scratch / "data", "-U", "mixer_fixture",
                   "--auth-local=trust", "--auth-host=trust", "--no-locale", "-E", "UTF8"], source)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    run("postgres-start", [PG / "pg_ctl", "-D", scratch / "data", "-l", OUT / "commands/postgres.log",
                           "-o", f"-h 127.0.0.1 -p {port} -k ''", "-w", "start"], source)
    env["MIXER_TEST_DATABASE_PORT"] = str(port)
    run("createdb", [PG / "createdb", "-h", "127.0.0.1", "-p", port, "-U", "mixer_fixture",
                     "mixer_foundation_test"], source)
    run("adversarial-tests", ["mix", "test", OUT / "probes/foundation_adversarial_test.exs",
                              "--warnings-as-errors", "--trace", "--seed", "0"], source, env)
    status = "passed"
finally:
    if (scratch / "data/postmaster.pid").exists():
        try:
            run("postgres-stop", [PG / "pg_ctl", "-D", scratch / "data", "-m", "fast", "-w", "stop"], source)
        except Exception as failure:
            cleanup["stop_error"] = str(failure)
    cleanup["postgres_stopped"] = not (scratch / "data/postmaster.pid").exists()
    unchanged = all(sha(source / name) == digest for name, digest in owner["inputs"].items())
    cleanup["frozen_source_unchanged"] = unchanged
    if cleanup["postgres_stopped"]:
        shutil.rmtree(scratch)
    cleanup["scratch_removed"] = not scratch.exists()
    if not all(cleanup.get(key) for key in ["postgres_stopped", "scratch_removed", "frozen_source_unchanged"]):
        status = "failed"
    receipt = {"schema": 1, "status": status, "source_tree_sha256": owner["source_tree_sha256"],
               "source_archive_sha256": sha(OUT / "reviewed-source.tar.gz"),
               "source_revision": (OWNER / "revision.log").read_text().strip(),
               "independent_probe_sha256": sha(OUT / "probes/foundation_adversarial_test.exs"),
               "commands": commands, "cleanup": cleanup,
               "scope": "Independent frozen candidate-2 foundation review only: actual local HTTP/PostgreSQL, no auth/domain integration or hosted-provider qualification.",
               "limitations": ["Local disposable PostgreSQL fixture uses synthetic trust/nonTLS credentials; no Neon/TLS handshake was exercised.",
                               "Reuses the pinned locally present dependency source; isolated build/output directory, no dependency resolution or product edits.",
                               "No native/UI/device/simulator/emulator use; no production deployment, external messaging or credential changes."]}
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": status, "cleanup": cleanup}))
if status != "passed":
    raise SystemExit(1)
