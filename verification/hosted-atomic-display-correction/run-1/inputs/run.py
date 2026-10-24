#!/usr/bin/env python3
"""Bounded disposable Ecto/Postgrex context probe; no live source/build/DB mutation."""
import argparse
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", action="store_true", help="Reproduce the unchanged final reviewer 83-case failures with original codec")
    parser.add_argument("--focused", action="store_true", help="Run only the five added display-correction cases (original assertions excluded, explicitly reported)")
    args = parser.parse_args()
    if args.baseline and args.focused: parser.error("baseline and focused are separate recipes")
    index = 1
    while (HERE / f"run-{index}").exists(): index += 1
    out = HERE / f"run-{index}"
    out.mkdir()
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="mxas-display-correction-", dir="/private/tmp")).resolve()
    project, deps, data, sock = (scratch / x for x in ("project", "deps", "pg", "socket"))
    project.mkdir(); deps.mkdir(); sock.mkdir(mode=0o700)
    commands, packages = [], []
    started, success, error = False, False, None
    proxy = None
    receipt = {"schema": 1, "scope": "PREIMPLEMENTATION synthetic atomic-storage mechanics only; no product authorization, membership migration, HTTP, Neon, native or GA acceptance", "baseline_revision": BASELINE, "started_utc": utc(), "run": out.name, "mode": "baseline" if args.baseline else "focused" if args.focused else "full", "independent_review_pending": True, "root_acceptance": False, "repository_acceptance": False}

    def run(argv, *, cwd=None, env=None, timeout=20, check=True):
        before = time.monotonic()
        item = {"argv": [str(x) for x in argv], "cwd": str(cwd or ROOT), "started_utc": utc(), "timeout_seconds": timeout}
        if env:
            item["environment_overrides"] = {key: env[key] for key in ("MXAS_DEPS", "MIX_DEPS_PATH", "MIX_BUILD_PATH", "MIX_ENV", "MXAS_SOCKET", "MXAS_RESULTS", "ERL_FLAGS", "MXAS_PROXY", "MXAS_ARM", "MXAS_PGDATA", "MXAS_PGLOG", "MXAS_BLOBS", "MXAS_FOCUSED", "GOCACHE", "GOPROXY", "GOSUMDB", "GOTOOLCHAIN") if key in env}
        try:
            result = subprocess.run(item["argv"], cwd=cwd or ROOT, env=env, capture_output=True, text=True, timeout=timeout)
            item.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        except subprocess.TimeoutExpired as exc:
            item.update(returncode=None, timed_out=True, stdout=(exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else exc.stdout, stderr=(exc.stderr or b"").decode() if isinstance(exc.stderr, bytes) else exc.stderr)
            raise
        finally:
            for stream in ("stdout", "stderr"):
                item[stream + "_sha256"] = sha((item.get(stream) or "").encode())
            executable = shutil.which(item["argv"][0])
            if executable:
                actual_executable = pathlib.Path(executable).resolve()
                item["executable"] = {"path": str(actual_executable), "sha256": sha(actual_executable.read_bytes())}
            item["duration_seconds"] = round(time.monotonic() - before, 6)
            commands.append(item)
            (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if check and result.returncode:
            raise RuntimeError(f"command failed: {item['argv']!r}: {result.stderr[-2000:]}")
        return result

    try:
        upstream = json.loads((HERE / "upstream-inputs.json").read_text())
        for item in upstream["files"]:
            content = (ROOT / item["path"]).read_bytes()
            if sha(content) != item["sha256"] or len(content) != item["bytes"]:
                raise RuntimeError("upstream input drift: " + item["path"])
        receipt["verified_upstream_bindings"] = len(upstream["files"])
        receipt["upstream_inputs_sha256"] = sha((HERE / "upstream-inputs.json").read_bytes())
        receipt["observed_head"] = run(["git", "rev-parse", "HEAD"]).stdout.strip()
        receipt["baseline_tree"] = run(["git", "rev-parse", BASELINE + "^{tree}"]).stdout.strip()
        receipt["atomic_contract_input_sha256"] = sha((ROOT / "docs/hosted-atomic-storage-preflight.md").read_bytes())
        inputs=["AGENTS.md","mixer-product-plan.md","docs/hosted-identity-contract.md","docs/hosted-membership-storage-contract.md","docs/hosted-transaction-context-preflight.md","docs/hosted-atomic-storage-preflight.md","docs/hosted-atomic-storage-corrections.md","verification/hosted-atomic-storage-root-review/correction-selection.json","docs/hosted-artifact-admission-contract.md","verification/hosted-transaction-context-root-review/selection.json","verification/hosted-transaction-context-root-review/atomic-writer-direction.json","verification/hosted-artifact-admission-implementation/seal.json","verification/hosted-artifact-admission-review/seal.json","services/release/store.go","services/release/postgres.go","services/protocol/testdata/signed-release-v3.json"]
        inputs += ["docs/hosted-atomic-display-correction-contract.md", "verification/hosted-atomic-storage-root-review/display-correction-direction.json", "docs/hosted-atomic-storage-correction-review.md", "verification/hosted-atomic-storage-correction-review/receipt.json", "verification/hosted-atomic-storage-correction-review/seal.json", "verification/hosted-atomic-storage-correction-review/findings.json", "verification/hosted-atomic-storage-correction-review/retained-row-counterexamples.json"]
        captured=[]
        for name in inputs:
            content=(ROOT/name).read_bytes();target=out/"inputs"/"contracts"/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
            captured.append({"path":name,"sha256":sha(content),"bytes":len(content)})
        (out/"contract-inputs.json").write_text(json.dumps(captured,indent=2)+"\n")
        lock = (HERE / "accepted-baseline.mix.lock").read_text()
        if lock != run(["git", "show", BASELINE + ":hosted/mix.lock"]).stdout: raise RuntimeError("accepted dependency lock drift")
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
        excerpts = []
        for name, rel, first, last, finding in [
            ("ecto", "lib/ecto/repo.ex", 308, 316, "Public dynamic Repo accessors"),
            ("ecto_sql", "lib/ecto/adapters/sql.ex", 1217, 1224, "in_transaction? reflects Ecto connection mode, not server xid"),
            ("ecto_sql", "lib/ecto/adapters/sql.ex", 1472, 1490, "Repo transaction forwards options into DBConnection"),
            ("db_connection", "README.md", 72, 79, "Checkout deadline terminates checked-out connection, not callback"),
            ("db_connection", "lib/db_connection.ex", 1080, 1114, "Nested and outer DBConnection transaction paths"),
            ("db_connection", "lib/db_connection.ex", 1756, 1796, "Callback result still needs commit, closed transaction returns rollback"),
            ("db_connection", "lib/db_connection/holder.ex", 145, 163, "Deleted/error holder rejects subsequent operations"),
            ("db_connection", "lib/db_connection/holder.ex", 222, 230, "Deadline checks exact timer reference"),
            ("db_connection", "lib/db_connection/holder.ex", 245, 248, "Deadline disconnect reaches connection process"),
            ("db_connection", "lib/db_connection/holder.ex", 311, 334, "Queued checkout receive has no timeout; deadline timer starts only on holder transfer"),
            ("db_connection", "lib/db_connection/holder.ex", 441, 456, "Finite timeout and absolute deadline choose earlier; absolute monotonic timer"),
            ("db_connection", "lib/db_connection/connection_pool.ex", 188, 212, "Pool deadline invokes holder disconnect while callback may be waiting"),
            ("postgrex", "lib/postgrex/protocol.ex", 282, 298, "Disconnect cancels request and closes socket"),
        ]:
            path = deps / name / rel
            lines = path.read_text().splitlines()
            excerpts.append({"package": name, "path": rel, "source_sha256": sha(path.read_bytes()), "first_line": first, "last_line": last, "finding": finding, "text": "\n".join(lines[first - 1:last]) + "\n"})
        (out / "primary-source-evidence.json").write_text(json.dumps(excerpts, indent=2) + "\n")
        source_files = []
        for source in sorted((HERE / "probe").rglob("*")):
            if not source.is_file(): continue
            rel = source.relative_to(HERE / "probe")
            if args.baseline:
                if str(rel) == "lib/codec.ex": source = HERE / "upstream/producer-probe/lib/codec.ex"
                if str(rel) == "probe_test.exs": source = HERE / "upstream/reviewer-probe_test.exs"
            target = project / rel
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
            frozen = out / "inputs" / "probe" / rel
            frozen.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, frozen)
            source_files.append({"path": "probe/" + str(rel), "sha256": sha(source.read_bytes()), "bytes": source.stat().st_size})
        shutil.copy2(__file__, out / "inputs/run.py")
        source_files.append({"path": "run.py", "sha256": sha(pathlib.Path(__file__).read_bytes()), "bytes": pathlib.Path(__file__).stat().st_size})
        generator = HERE / "build-display-corpus.py"
        shutil.copy2(generator, out / "inputs/build-display-corpus.py")
        source_files.append({"path": "build-display-corpus.py", "sha256": sha(generator.read_bytes()), "bytes": generator.stat().st_size})
        (out / "source-manifest.json").write_text(json.dumps(source_files, indent=2) + "\n")
        receipt["probe_source_tree_digest"] = sha(json.dumps(source_files, sort_keys=True, separators=(",", ":")).encode())
        run(["initdb", "-D", data, "-U", "preflight_owner", "-A", "trust", "--no-locale", "-E", "UTF8"])
        run(["pg_ctl", "-D", data, "-l", scratch / "postgres.log", "-o", f"-k {sock} -c listen_addresses='' -c unix_socket_permissions=0700 -c max_connections=12 -c log_statement=none -c log_min_error_statement=panic", "start", "-w"])
        started = True
        run(["psql", "-h", sock, "-U", "preflight_owner", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-c", "CREATE DATABASE atomic_preflight"])
        env = os.environ.copy()
        env.update({"MXAS_DEPS": str(deps), "MIX_DEPS_PATH": str(deps), "MIX_BUILD_PATH": str(scratch / "build"), "MIX_ENV": "test", "MXAS_SOCKET": str(sock), "MXAS_RESULTS": str(out / "tests.json"), "ERL_FLAGS": "+S 2:2"})
        run(["psql", "-h", sock, "-U", "preflight_owner", "-d", "atomic_preflight", "-v", "ON_ERROR_STOP=1", "-f", project / "schema.sql"])
        proxy_dir=scratch / "proxy";proxy_dir.mkdir(mode=0o700)
        proxy_argv=[sys.executable,str(project / "proxy.py"),str(sock),str(proxy_dir),str(scratch / "drop-commit"),str(out / "proxy.jsonl")]
        proxy=subprocess.Popen(proxy_argv,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        commands.append({"argv":proxy_argv,"started_utc":utc(),"scope":"owned unix socket COMMIT reply drop fixture"})
        for _ in range(100):
            if (proxy_dir / ".s.PGSQL.5432").exists():break
            time.sleep(0.01)
        else:raise RuntimeError("proxy not ready")
        if args.focused: env["MXAS_FOCUSED"] = "1"
        env.update(MXAS_PROXY=str(proxy_dir),MXAS_ARM=str(scratch / "drop-commit"),MXAS_PGDATA=str(data),MXAS_PGLOG=str(scratch / "postgres.log"),MXAS_BLOBS=str(scratch / "blobs"))
        services = scratch / "services"
        go_files=[]
        for source in sorted((HERE / "legacy-services").rglob("*")):
            if not source.is_file(): continue
            name = "services/" + str(source.relative_to(HERE / "legacy-services"))
            content=source.read_bytes();target=scratch/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
            frozen=out/"inputs"/name;frozen.parent.mkdir(parents=True,exist_ok=True);frozen.write_bytes(content)
            go_files.append({"path":name,"sha256":sha(content),"bytes":len(content)})
        (out/"legacy-source-manifest.json").write_text(json.dumps(go_files,indent=2)+"\n")
        goenv=os.environ.copy();goenv.update(GOCACHE=str(scratch/"go-cache"),GOPROXY="off",GOSUMDB="off",GOTOOLCHAIN="local")
        run(["go","version"])
        run(["go","test","-count=1","-run","^(TestAuditCanonicalHashDoesNotDependOnMapInsertionOrder|TestV3SharedCanonicalAndSignatureVector)$","./release","./protocol"],cwd=services,env=goenv,timeout=120)
        run(["go","run",str(project/"legacy.go"),str(project/"legacy-golden.json")],cwd=services,env=goenv,timeout=120)
        run(["mix", "deps.compile"], cwd=project, env=env, timeout=120)
        test_run = run(["mix", "run", "probe_test.exs"], cwd=project, env=env, timeout=90, check=False)
        tests = {}
        if (out / "tests.json").exists():
            tests = json.loads((out / "tests.json").read_text())
            receipt["test_summary"] = tests.get("summary")
        summary = tests.get("summary", {})
        expected_total = 83 if args.baseline else 88
        expected_failures = 2 if args.baseline else 0
        expected_excluded = 83 if args.focused else 0
        observed_expected = (test_run.returncode == (1 if args.baseline else 0)
                   and summary == {"total": expected_total, "failures": expected_failures, "skipped": 0, "excluded": expected_excluded})
        receipt["expected_baseline_failure_reproduced"] = bool(args.baseline and observed_expected)
        success = bool(observed_expected and not args.baseline)
        catalog = run(["psql", "-h", sock, "-U", "preflight_owner", "-d", "atomic_preflight", "-At", "-v", "ON_ERROR_STOP=1", "-f", project / "catalog.sql"])
        (out / "installed-catalog.json").write_text(json.dumps(json.loads(catalog.stdout), indent=2) + "\n")
        receipt["installed_catalog_sha256"] = sha((out / "installed-catalog.json").read_bytes())
        if not observed_expected: raise RuntimeError(f"unexpected probe result: {test_run.returncode}; {summary}")
    except Exception as exc:
        error = repr(exc)
        print(error, file=sys.stderr)
    finally:
        if proxy is not None:
            proxy.terminate()
            _,proxy_error=proxy.communicate(timeout=5)
            (out / "proxy-stderr.log").write_text(proxy_error)
        cleanup = {"owned_proxy_stopped": proxy is not None and proxy.poll() is not None, "owned_scratch": str(scratch), "started_owned_postgres": started, "other_clusters_touched": False, "native_processes_started": False}
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
    return 0 if (success or receipt.get("expected_baseline_failure_reproduced")) and cleanup["owned_scratch_removed"] else 1

if __name__ == "__main__": sys.exit(main())
