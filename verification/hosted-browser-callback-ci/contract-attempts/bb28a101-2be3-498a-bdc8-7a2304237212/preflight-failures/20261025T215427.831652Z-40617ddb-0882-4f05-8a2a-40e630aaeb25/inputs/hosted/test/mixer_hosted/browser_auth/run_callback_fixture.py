#!/usr/bin/env python3
"""Run the exact callback/preauth/begin closure with one owned PostgreSQL 16/17."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[4]
REGISTRY = "verification/hosted-browser-callback-ci/selected-methods.json"
DEPS = ("telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex",
        "jason", "oban", "jose", "mint", "hpax")
IDENTITY = ("encoding", "bounded_json", "trust_snapshot", "manifest", "startup_config",
            "admission", "global_address", "http_freshness", "http_wire_guard",
            "dns_resolver", "bounded_tcp", "jwks_transport", "fetch_flight", "key_owner")
BROWSER = ("vault", "stored_snapshot", "config", "configuration_digest", "custody",
           "runtime_config", "storage_schema", "activation_preparation",
           "activation_preparation_schema", "catalog_manifest", "catalog_manifest_v2",
           "catalog", "relation_manifest", "relation_catalog", "preauth_draft",
           "lifecycle_repo", "callback_draft", "store", "runtime_owner", "protocol")
SOURCES = (["hosted/lib/mixer_hosted/identity/" + p + ".ex" for p in IDENTITY] +
           ["hosted/lib/mixer_hosted/" + p + ".ex" for p in ("runtime_config", "repo")] +
           ["hosted/lib/mixer_hosted/browser_auth/" + p + ".ex" for p in BROWSER] +
           ["hosted/lib/mixer_hosted/customer_artifacts/schema.ex"])
MIGRATIONS = ("20261024000000_add_oban", "20261025000000_add_build_journals",
              "20261025000001_add_build_admission", "20261025000002_add_build_aggregate_limits",
              "20261025000003_add_customer_authorization",
              "20261025000004_add_authorization_state_revisions",
              "20261025000005_add_customer_artifact_storage",
              "20261025000006_add_customer_workspace_discovery",
              "20261025000007_add_browser_sessions",
              "20261025000008_add_browser_activation_preparation")
SUITES = (("preauth", "verification/hosted-browser-preauth-store/live.exs", 55),
          ("begin", "verification/hosted-browser-begin-login/live.exs", 55),
          ("callback", "verification/hosted-browser-callback-storage/live.exs", 110))
FORMAT = ("hosted/lib/mixer_hosted/browser_auth/callback_draft.ex",
          "hosted/lib/mixer_hosted/browser_auth/store.ex",
          "verification/hosted-browser-callback-storage/live.exs",
          "verification/hosted-browser-callback-storage/controls.exs")
RELATION_PINS = {
    "hosted/lib/mixer_hosted/browser_auth/relation_catalog.ex":
        "f71d79b92065d2137363f10de89c137b95ce5758b0e4c21b88faaeb8a779fcfc",
    "hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex":
        "3f83abc969225d07f0569ea0317a80a11371f0068519208d5cf110a6c430d33d",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def tree(manifest):
    return hashlib.sha256(json.dumps(manifest, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def identity(path):
    stat = path.stat()
    return [stat.st_dev, stat.st_ino]


def output_parent(path):
    path = path.expanduser().absolute()
    if ".." in path.parts:
        raise ValueError("output must not contain parent traversal")
    if len(path.parts) < 3 or path in (Path.home(), ROOT, ROOT / "hosted"):
        raise ValueError("output must name a dedicated evidence directory")
    if path in ROOT.parents or ROOT / ".git" == path or ROOT / ".git" in path.parents:
        raise ValueError("output cannot be a repository ancestor or Git metadata")
    evidence = ROOT / "verification/hosted-browser-callback-ci"
    if ROOT in path.parents and path != evidence and evidence not in path.parents:
        raise ValueError("repository output must stay in the owned callback CI evidence directory")
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError("output and its parents must not be symlinks")
        if part.exists() and not part.is_dir():
            raise ValueError("output and its parents must be directories")
    return path


def dependency_manifest(depdirs):
    beams = {str(p.relative_to(ROOT)): sha(p) for d in depdirs if d.is_dir()
             for p in sorted(d.iterdir()) if p.is_file()}
    sources = {}
    for name in DEPS:
        for part in ("lib", "src", "include", "c_src", "mix.exs", "rebar.config", "Makefile"):
            location = ROOT / "hosted/deps" / name / part
            entries = [location] if location.is_file() else sorted(location.rglob("*"))
            for entry in entries:
                if entry.is_file() and not entry.is_symlink():
                    sources[str(entry.relative_to(ROOT))] = sha(entry)
    return {"prepared_ebin": beams, "dependency_sources": sources}


class Attempt:
    def __init__(self, output, pg):
        self.output, self.pg = output, pg
        self.scratch = None
        self.env = {k: v for k, v in os.environ.items()
                    if k in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR")}
        self.env.update(ERL_FLAGS="+S 2:2 +SDcpu 1 +SDio 1", MIX_ENV="test")
        self.receipt = {
            "schema": 1, "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "invocation": [sys.executable, *sys.argv], "commands": [], "cleanup": {},
            "output": str(output), "pg_bin": str(pg), "platform": sys.platform,
            "scope": "Selected actual CallbackDraft/Store, RuntimeOwner/default KeyOwner and "
                     "fixed LifecycleRepo only; unchanged synthetic restricted-role pool2/noqueue "
                     "fixtures. Manual localhost RuntimeConfig bypasses deployment TLS/5432 "
                     "constructor qualification. No provider, HTTP facade, Unit B, full hosted "
                     "application, native runtime, publication, dogfood or GA qualification.",
        }

    def run(self, label, argv, data=None, check=True, timeout=55, cwd=ROOT):
        argv = list(map(str, argv))
        command = {"label": label, "argv": argv, "cwd": str(cwd),
                   "timeout_seconds": timeout}
        self.receipt["commands"].append(command)
        stdout, stderr = b"", b""
        try:
            proc = subprocess.Popen(argv, cwd=cwd, env=self.env,
                                    stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    start_new_session=True)
        except OSError as error:
            stderr = str(error).encode()
            command.update(exit=None, launch_error=type(error).__name__)
        else:
            command["owned_pid"] = proc.pid

            def kill_owned_group():
                returncode = proc.returncode
                if returncode is None:
                    returncode = proc.poll()
                command["child_returncode_before_kill"] = returncode
                if returncode is not None:
                    command["killpg_skipped_reaped"] = True
                    return
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    command["killpg_process_absent"] = True

            try:
                try:
                    stdout, stderr = proc.communicate(data.encode() if data is not None else None,
                                                       timeout=timeout)
                    command["timed_out"] = False
                except subprocess.TimeoutExpired as error:
                    stdout, stderr = error.output or b"", error.stderr or b""
                    command["timed_out"] = True
                    kill_owned_group()
                    stdout, stderr = proc.communicate(timeout=5)
                except BaseException as error:
                    command["interrupted"] = type(error).__name__
                    kill_owned_group()
                    stdout, stderr = proc.communicate(timeout=5)
                    raise
            except BaseException as error:
                command["process_error"] = type(error).__name__
                raise
            finally:
                command["exit"] = proc.returncode
                (self.output / (label + ".stdout")).write_bytes(stdout)
                (self.output / (label + ".stderr")).write_bytes(stderr)
        (self.output / (label + ".stdout")).write_bytes(stdout)
        (self.output / (label + ".stderr")).write_bytes(stderr)
        print(label + ": exit " + str(command["exit"]), flush=True)
        if check and (command["exit"] != 0 or command.get("timed_out")):
            raise RuntimeError(label + " failed")
        return command["exit"], stdout.decode(errors="replace")

    def cleanup(self):
        cleanup = self.receipt["cleanup"]
        scratch = self.scratch
        cleanup["no_native_capture_browser_phone_or_provider_started"] = True
        if scratch is None:
            cleanup["owned_scratch_absent"] = True
            cleanup["postmaster_absent"] = True
            return
        same_scratch = scratch.is_dir() and identity(scratch) == self.receipt["scratch_identity"]
        data = scratch / "data"
        same_data = same_scratch and data.is_dir() and identity(data) == self.receipt.get("data_identity")
        pidfile = data / "postmaster.pid"
        same_pid = same_data and pidfile.is_file() and (
            pidfile.read_text().splitlines()[:4] == self.receipt.get("postmaster_identity"))
        cleanup.update(scratch_identity_preserved=same_scratch,
                       data_identity_preserved=same_data if "data_identity" in self.receipt else True,
                       postmaster_identity_preserved=same_pid if pidfile.exists() else True)
        if same_pid:
            self.run("postgres-stop", [self.pg / "pg_ctl", "-D", data, "-m", "immediate",
                                      "-w", "stop"], check=False, timeout=15)
        if same_data:
            code, _ = self.run("postmaster-status", [self.pg / "pg_ctl", "-D", data,
                                                     "status"], check=False)
            cleanup["postmaster_status_nonrunning"] = code == 3
        cleanup["postmaster_absent"] = not pidfile.exists()
        if same_scratch and all(cleanup.values()):
            shutil.rmtree(scratch)
        cleanup["owned_scratch_absent"] = not scratch.exists()

    def execute(self):
        before, dependencies, depdirs = {}, {}, []
        try:
            registry = json.loads((ROOT / REGISTRY).read_text())
            source_paths = set(SOURCES + list(registry["fixture_sha256"]) + [
                REGISTRY, str(Path(__file__).relative_to(ROOT)), "AGENTS.md", "THIRD_PARTY.yml",
                "hosted/mix.exs", "hosted/mix.lock", "hosted/.tool-versions",
                "hosted/lib/mixer_hosted/authorization/postgres/session.ex",
                ".github/workflows/hosted.yml", "docs/hosted-browser-callback-ci.md",
                "hosted/priv/browser_auth/relation_surface_v1_pg16.json",
                "hosted/priv/browser_auth/relation_surface_v1_pg17.json",
            ] + ["hosted/priv/repo/migrations/" + p + ".exs" for p in MIGRATIONS])
            before = {p: sha(ROOT / p) for p in sorted(source_paths)}
            self.receipt.update(sources=before, source_tree_sha256=tree(before))
            if any(value is None for value in before.values()):
                raise RuntimeError("missing explicit selected input")
            if any(before[p] != h for p, h in (RELATION_PINS | registry["fixture_sha256"]).items()):
                raise RuntimeError("accepted relation or exact selected fixture pin mismatch")
            if [len(registry["methods"][name]) for name, _, _ in SUITES] != [30, 30, 35]:
                raise RuntimeError("expected coordinated exact 30/30/35 method registry")
            for relative in before:
                target = self.output / "inputs" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            depdirs = [ROOT / "hosted/_build/test/lib" / name / "ebin" for name in DEPS]
            if any(not d.is_dir() or not any(d.glob("*.beam")) for d in depdirs):
                raise RuntimeError("prepared locked selected dependency beams required; no compile attempted")
            dependencies = dependency_manifest(depdirs)
            self.receipt.update(dependencies=dependencies, dependency_tree_sha256=tree(dependencies))
            _, revision = self.run("revision", ["git", "rev-parse", "HEAD"])
            _, git_tree = self.run("git-tree", ["git", "rev-parse", "HEAD^{tree}"])
            self.receipt.update(revision=revision.strip(), git_tree=git_tree.strip())
            for label, argv in (("elixir-version", ["elixir", "--version"]),
                                ("mix-version", ["mix", "--version"]),
                                ("python-version", [sys.executable, "--version"]),
                                ("git-version", ["git", "--version"]),
                                ("postgres-version", [self.pg / "postgres", "--version"]),
                                ("initdb-version", [self.pg / "initdb", "--version"]),
                                ("pg-ctl-version", [self.pg / "pg_ctl", "--version"]),
                                ("psql-version", [self.pg / "psql", "--version"])):
                _, version = self.run(label, argv)
                self.receipt.setdefault("versions", {})[label] = version.strip()
            major = self.receipt["versions"]["postgres-version"].split()[2].split(".")[0]
            if major not in ("16", "17"):
                raise RuntimeError("only PostgreSQL 16 and 17 selected relation manifests are qualified")
            self.scratch = Path(tempfile.mkdtemp(prefix="mixer-browser-callback-ci-"))
            self.receipt.update(owned_scratch=str(self.scratch), scratch_identity=identity(self.scratch))
            self.env["ERL_CRASH_DUMP"] = str(self.scratch / "erl.dump")
            self.run("mix-format", ["mix", "format", "--check-formatted"] +
                     [ROOT / p for p in FORMAT], cwd=self.scratch)
            ebin = self.scratch / "ebin"
            ebin.mkdir()
            paths = [arg for d in depdirs for arg in ("-pa", d)]
            compile_code = ("Mix.start(); Mix.env(:test); case Kernel.ParallelCompiler.compile_to_path("
                            "tl(System.argv()),hd(System.argv()),warnings_as_errors: true, "
                            "return_diagnostics: true) do "
                            "{:ok,_,%{compile_warnings: [], runtime_warnings: []}} -> :ok; "
                            "_ -> System.halt(1) end")
            self.run("selected-compile", ["elixir", *paths, "-e", compile_code, ebin, *SOURCES])
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            self.receipt["port"] = port
            self.env.update(PREAUTH_PORT=str(port), PREAUTH_OUTPUT=str(self.output))
            data = self.scratch / "data"
            self.run("initdb", [self.pg / "initdb", "-D", data, "-U", "browser_admin",
                                "-A", "trust", "--no-locale", "-E", "UTF8"])
            self.receipt["data_identity"] = identity(data)
            try:
                self.run("postgres-start", [self.pg / "pg_ctl", "-D", data, "-l",
                         self.output / "postgres.log", "-o",
                         f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC "
                         "-c log_min_messages=panic -c log_min_error_statement=panic "
                         "-c log_parameter_max_length_on_error=0", "-w", "start"])
            finally:
                if (data / "postmaster.pid").is_file():
                    self.receipt["postmaster_identity"] = (data / "postmaster.pid").read_text().splitlines()[:4]
            psql = [self.pg / "psql", "-X", "-q", "-A", "-t", "-h", "127.0.0.1", "-p",
                    port, "-U", "browser_admin", "-d", "postgres", "-v", "ON_ERROR_STOP=1"]
            roles = (("browser_schema_owner", "NOLOGIN"), ("browser_writer", "NOLOGIN"),
                     ("browser_lifecycle", "LOGIN"), ("browser_ordinary", "LOGIN"))
            self.run("roles", psql, data=";".join("CREATE ROLE " + name + " " + login +
                     " NOSUPERUSER NOBYPASSRLS NOINHERIT" for name, login in roles) + ";")
            self.run("database", psql, data="CREATE DATABASE browser_storage OWNER browser_schema_owner;")
            elixir = ["elixir", *paths, "-pa", ebin]
            self.run("install", elixir + ["verification/hosted-browser-begin-login/install.exs"])
            for name, fixture, timeout in SUITES:
                suite_output = self.output / name
                suite_output.mkdir()
                self.env["PREAUTH_OUTPUT"] = str(suite_output)
                self.run(name, elixir + [fixture], timeout=timeout)
                checks = json.loads((suite_output / "checks.json").read_text())
                self.receipt.setdefault("checks", {})[name] = checks
                if ([c["name"] for c in checks] != registry["methods"][name] or
                        any(c.get("passed") is not True for c in checks)):
                    raise RuntimeError(name + " must pass every exact ordered selected method")
                beam = json.loads((suite_output / "beam-cleanup.json").read_text())
                self.receipt.setdefault("beam_cleanup", {})[name] = beam
                if not beam or any(value is not True for value in beam.values()):
                    raise RuntimeError(name + " owned BEAM cleanup failed")
            self.receipt["passed"] = True
        except BaseException as error:
            self.receipt["failure"] = type(error).__name__ + ": " + str(error)
        finally:
            try:
                self.cleanup()
            except BaseException as error:
                self.receipt["cleanup"]["cleanup_completed"] = False
                self.receipt["cleanup_failure"] = type(error).__name__ + ": " + str(error)
            after = {p: sha(ROOT / p) for p in before}
            deps_after = dependency_manifest(depdirs) if dependencies else {}
            self.receipt.update(sources_after=after, source_tree_after_sha256=tree(after),
                                source_changes=[p for p in before if before[p] != after[p]],
                                dependencies_after=deps_after,
                                dependency_tree_after_sha256=tree(deps_after),
                                dependency_changes=dependencies != deps_after)
            self.receipt["success"] = bool(self.receipt.get("passed") and
                all(self.receipt["cleanup"].values()) and not self.receipt["source_changes"] and
                not self.receipt["dependency_changes"])
            self.receipt["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
            self.receipt["outputs"] = {str(p.relative_to(self.output)): sha(p)
                                      for p in sorted(self.output.rglob("*")) if p.is_file()}
            (self.output / "receipt.json").write_text(json.dumps(self.receipt, indent=2, sort_keys=True) + "\n")
            print(self.output, flush=True)
            print(json.dumps({k: self.receipt.get(k) for k in ("success", "failure", "cleanup")}), flush=True)
        return 0 if self.receipt["success"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", required=True, type=Path,
                        help="explicit prepared PostgreSQL 16/17 executable directory")
    parser.add_argument("--output", required=True, type=Path,
                        help="dedicated evidence parent; every run creates a fresh UUID attempt")
    args = parser.parse_args()
    pg = args.pg_bin.expanduser().resolve()
    for name in ("postgres", "initdb", "pg_ctl", "psql"):
        if not (pg / name).is_file() or not os.access(pg / name, os.X_OK):
            parser.error("pg-bin must contain executable " + name)
    try:
        parent = output_parent(args.output)
    except ValueError as error:
        parser.error(str(error))
    attempt = parent / (dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + str(uuid.uuid4()))
    attempt.mkdir(parents=True, exist_ok=False)
    previous = {}
    def interrupted(signum, _frame):
        raise InterruptedError("received signal " + str(signum))
    for signum in (signal.SIGINT, signal.SIGTERM):
        previous[signum] = signal.signal(signum, interrupted)
    try:
        return Attempt(attempt, pg).execute()
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    raise SystemExit(main())
