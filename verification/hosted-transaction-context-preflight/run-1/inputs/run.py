#!/usr/bin/env python3
"""Bounded disposable Ecto/Postgrex context probe; no live source/build/DB mutation."""
import datetime
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
BASELINE = "bc45a20298533b70808607b8228473b1d1efa81d"
NAMES = ("telemetry", "decimal", "jason", "db_connection", "ecto", "postgrex", "ecto_sql")
def sha(data): return hashlib.sha256(data).hexdigest()
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    index = 1
    while (HERE / f"run-{index}").exists(): index += 1
    out = HERE / f"run-{index}"
    out.mkdir()
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="mxtc-", dir="/private/tmp")).resolve()
    project, deps, data, sock = (scratch / x for x in ("project", "deps", "pg", "socket"))
    project.mkdir(); deps.mkdir(); sock.mkdir(mode=0o700)
    commands, packages = [], []
    started, success, error = False, False, None
    receipt = {"schema": 1, "scope": "PREIMPLEMENTATION public Ecto/Postgrex transaction-context seam only; no product authorization, membership migration, HTTP, Neon, native or GA acceptance", "baseline_revision": BASELINE, "started_utc": utc(), "run": out.name}

    def run(argv, *, cwd=None, env=None, timeout=20, check=True):
        before = time.monotonic()
        item = {"argv": [str(x) for x in argv], "cwd": str(cwd or ROOT), "started_utc": utc(), "timeout_seconds": timeout}
        try:
            result = subprocess.run(item["argv"], cwd=cwd or ROOT, env=env, capture_output=True, text=True, timeout=timeout)
            item.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        except subprocess.TimeoutExpired as exc:
            item.update(returncode=None, timed_out=True, stdout=(exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else exc.stdout, stderr=(exc.stderr or b"").decode() if isinstance(exc.stderr, bytes) else exc.stderr)
            raise
        finally:
            item["duration_seconds"] = round(time.monotonic() - before, 6)
            commands.append(item)
            (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if check and result.returncode:
            raise RuntimeError(f"command failed: {item['argv']!r}: {result.stderr[-2000:]}")
        return result

    try:
        receipt["observed_head"] = run(["git", "rev-parse", "HEAD"]).stdout.strip()
        receipt["baseline_tree"] = run(["git", "rev-parse", BASELINE + "^{tree}"]).stdout.strip()
        lock = run(["git", "show", BASELINE + ":hosted/mix.lock"]).stdout
        (out / "accepted-baseline.mix.lock").write_text(lock)
        for argv in (["python3", "--version"], ["elixir", "--version"], ["mix", "--version"], ["postgres", "--version"], ["pg_ctl", "--version"], ["psql", "--version"]):
            run(argv)
        for name in NAMES:
            line = next(x for x in lock.splitlines() if x.startswith(f'  "{name}":'))
            version, inner = re.search(r'\{:hex, :\w+, "([^"]+)", "([0-9a-f]{64})"', line).groups()
            outer = re.findall(r'"([0-9a-f]{64})"', line)[-1]
            archive = pathlib.Path.home() / ".hex/packages/hexpm" / f"{name}-{version}.tar"
            archive_bytes = archive.read_bytes()
            if sha(archive_bytes) != outer: raise RuntimeError(f"accepted package archive checksum mismatch: {name}")
            with tarfile.open(fileobj=io.BytesIO(archive_bytes)) as outer_tar:
                check = outer_tar.extractfile("CHECKSUM").read().decode().strip().lower()
                if check != inner: raise RuntimeError(f"inner checksum mismatch: {name}")
                content = outer_tar.extractfile("contents.tar.gz").read()
            installed = ROOT / "hosted/deps" / name
            files = []
            with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as package:
                for member in package.getmembers():
                    rel = pathlib.PurePosixPath(member.name)
                    if member.isdir(): continue
                    if not member.isfile() or rel.is_absolute() or ".." in rel.parts: raise RuntimeError(f"unsafe member in {name}: {member.name}")
                    expected = package.extractfile(member).read()
                    actual = (installed / member.name).read_bytes()
                    if actual != expected: raise RuntimeError(f"installed source differs from accepted archive: {name}/{member.name}")
                    target = deps / name / member.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(actual)
                    target.chmod(member.mode & 0o777)
                    files.append({"path": member.name, "sha256": sha(actual), "bytes": len(actual)})
            # Only copied archive members enter the scratch dependency tree.
            packages.append({"name": name, "version": version, "accepted_inner_checksum": inner, "archive_sha256": outer, "installed_tree_matches_accepted_archive": True, "copied_files": files})
        (out / "dependency-source-manifest.json").write_text(json.dumps(packages, indent=2) + "\n")
        source_files = []
        for source in sorted((HERE / "probe").rglob("*")):
            if not source.is_file(): continue
            rel = source.relative_to(HERE / "probe")
            target = project / rel
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
            frozen = out / "inputs" / "probe" / rel
            frozen.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, frozen)
            source_files.append({"path": "probe/" + str(rel), "sha256": sha(source.read_bytes()), "bytes": source.stat().st_size})
        shutil.copy2(__file__, out / "inputs/run.py")
        source_files.append({"path": "run.py", "sha256": sha(pathlib.Path(__file__).read_bytes()), "bytes": pathlib.Path(__file__).stat().st_size})
        (out / "source-manifest.json").write_text(json.dumps(source_files, indent=2) + "\n")
        receipt["probe_source_tree_digest"] = sha(json.dumps(source_files, sort_keys=True, separators=(",", ":")).encode())
        run(["initdb", "-D", data, "-U", "preflight_owner", "-A", "trust", "--no-locale", "-E", "UTF8"])
        run(["pg_ctl", "-D", data, "-l", scratch / "postgres.log", "-o", f"-k {sock} -c listen_addresses='' -c unix_socket_permissions=0700 -c max_connections=12 -c log_statement=all", "start", "-w"])
        started = True
        run(["psql", "-h", sock, "-U", "preflight_owner", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-c", "CREATE DATABASE context_preflight"])
        env = os.environ.copy()
        env.update({"MXTC_DEPS": str(deps), "MIX_DEPS_PATH": str(deps), "MIX_BUILD_PATH": str(scratch / "build"), "MIX_ENV": "test", "MXTC_SOCKET": str(sock), "MXTC_RESULTS": str(out / "tests.json"), "ERL_FLAGS": "+S 2:2"})
        run(["mix", "deps.compile"], cwd=project, env=env, timeout=120)
        test_run = run(["mix", "run", "probe_test.exs"], cwd=project, env=env, timeout=90, check=False)
        if (out / "tests.json").exists():
            tests = json.loads((out / "tests.json").read_text())
            receipt["test_summary"] = tests.get("summary")
        success = test_run.returncode == 0
        if not success: raise RuntimeError(f"probe tests exited {test_run.returncode}")
    except Exception as exc:
        error = repr(exc)
        print(error, file=sys.stderr)
    finally:
        cleanup = {"owned_scratch": str(scratch), "started_owned_postgres": started, "other_clusters_touched": False, "native_processes_started": False}
        stop = run(["pg_ctl", "-D", data, "stop", "-m", "immediate", "-w"], check=False) if started else None
        cleanup["owned_postgres_stopped"] = bool(stop and stop.returncode == 0)
        if (scratch / "postgres.log").exists(): shutil.copy2(scratch / "postgres.log", out / "postgres.log")
        if not started or cleanup["owned_postgres_stopped"]:
            shutil.rmtree(scratch)
        cleanup["owned_scratch_removed"] = not scratch.exists()
        cleanup["owned_socket_removed"] = not sock.exists()
        receipt.update(finished_utc=utc(), passed=success, error=error, cleanup=cleanup)
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"run": out.name, "passed": success, "error": error, "cleanup": cleanup}))
    return 0 if success and cleanup["owned_scratch_removed"] else 1

if __name__ == "__main__": sys.exit(main())
