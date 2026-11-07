#!/usr/bin/env python3
"""Bounded CLI, timeout and actual owned-PG cleanup contracts for the CI runner."""
import argparse
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from unittest import mock
import uuid

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "hosted/test/mixer_hosted/browser_auth/run_callback_fixture.py"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", required=True, type=Path)
    args = parser.parse_args()
    pg = args.pg_bin.resolve()
    spec = importlib.util.spec_from_file_location("callback_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = Path(__file__).parent / "contract-attempts" / str(uuid.uuid4())
    output.mkdir(parents=True)
    checks, commands = [], []
    source_paths = [RUNNER, Path(__file__).resolve(), ROOT / module.REGISTRY,
                    ROOT / ".github/workflows/hosted.yml", ROOT / "docs/hosted-browser-callback-ci.md"]
    before = {str(p.relative_to(ROOT)): module.sha(p) for p in source_paths}

    def check(name, condition):
        checks.append({"name": name, "passed": condition is True})
        if condition is not True:
            raise AssertionError(name)

    def command(name, argv, env=None):
        proc = subprocess.run(list(map(str, argv)), env=env, cwd=ROOT,
                              capture_output=True, timeout=15)
        (output / (name + ".stdout")).write_bytes(proc.stdout)
        (output / (name + ".stderr")).write_bytes(proc.stderr)
        commands.append({"label": name, "argv": proc.args, "exit": proc.returncode,
                         "cwd": str(ROOT), "timeout_seconds": 15})
        return proc

    def cli(name, argv, env=None):
        return command(name, [sys.executable, "-B", RUNNER, *argv], env=env)

    attempt = None
    try:
        revision = command("revision", ["git", "rev-parse", "HEAD"]).stdout.decode().strip()
        git_tree = command("git-tree", ["git", "rev-parse", "HEAD^{tree}"]).stdout.decode().strip()
        command("postgres-version", [pg / "postgres", "--version"])
        command("git-version", ["git", "--version"])
        check("help exits zero", cli("help", ["--help"]).returncode == 0)
        check("missing explicit arguments fail", cli("missing-arguments", []).returncode == 2)
        rejected = output / "invalid-pg-output"
        check("invalid PG fails before output allocation", cli("invalid-pg", ["--pg-bin",
              output / "absent-pg", "--output", rejected]).returncode == 2 and not rejected.exists())
        check("root output rejected", cli("root-output", ["--pg-bin", pg,
              "--output", "/"]).returncode == 2)
        check("repository output rejected", cli("repository-output", ["--pg-bin", pg,
              "--output", ROOT]).returncode == 2)
        link = output / "output-link"
        link.symlink_to(output, target_is_directory=True)
        check("symlink output parent rejected", cli("symlink-output", ["--pg-bin", pg,
              "--output", link / "child"]).returncode == 2 and not (output / "child").exists())
        link.unlink()
        check("parent traversal rejected", cli("traversal-output", ["--pg-bin", pg,
              "--output", str(output) + "/../sibling"]).returncode == 2)
        attempt = module.Attempt(output / "owned-failure", pg)
        attempt.output.mkdir()
        check("selectors and path overrides absent", all(key not in attempt.env for key in
              ("CALLBACK_CASE", "ELIXIR_ERL_OPTIONS", "ERL_LIBS", "MIX_PATH", "DATABASE_URL")))
        code, _ = attempt.run("timed-out-owned-command", [sys.executable, "-c",
                              "import time; time.sleep(30)"], timeout=0.05, check=False)
        check("timeout terminates owned child and records nonzero", code != 0 and
              attempt.receipt["commands"][-1]["timed_out"] is True)
        popen = subprocess.Popen

        def exited_child(first_error):
            def start(*argv, **kwargs):
                proc = popen(*argv, **kwargs)
                proc.wait(timeout=5)
                communicate = proc.communicate
                raised = False
                def late_communicate(*args, **options):
                    nonlocal raised
                    if not raised:
                        raised = True
                        raise first_error
                    return communicate(*args, **options)
                proc.communicate = late_communicate
                return proc
            return start

        raw = [sys.executable, "-c", "import sys; print('raw-out'); print('raw-err', file=sys.stderr)"]
        with mock.patch.object(module.subprocess, "Popen", exited_child(subprocess.TimeoutExpired(raw, 0.05))):
            attempt.run("exited-child-timeout-race", raw, timeout=0.05, check=False)
        race = attempt.receipt["commands"][-1]
        check("already exited timeout child is reaped with raw output", race.get("killpg_process_absent") is True and
              race["exit"] == 0 and race["timed_out"] is True and "launch_error" not in race and
              (attempt.output / "exited-child-timeout-race.stdout").read_text() == "raw-out\n" and
              (attempt.output / "exited-child-timeout-race.stderr").read_text() == "raw-err\n")
        try:
            with mock.patch.object(module.subprocess, "Popen", exited_child(KeyboardInterrupt())):
                attempt.run("exited-child-interruption-race", raw, check=False)
        except KeyboardInterrupt:
            race = attempt.receipt["commands"][-1]
            check("already exited interrupted child retains output and original error", race.get("killpg_process_absent") is True and
                  race["exit"] == 0 and race["interrupted"] == "KeyboardInterrupt" and
                  "launch_error" not in race and
                  (attempt.output / "exited-child-interruption-race.stdout").read_text() == "raw-out\n" and
                  (attempt.output / "exited-child-interruption-race.stderr").read_text() == "raw-err\n")
        else:
            check("already exited interrupted child retains output and original error", False)
        attempt.run("true-launch-failure", [output / "absent-executable"], check=False)
        check("true launch failure distinguished from child collection", attempt.receipt["commands"][-1].get("launch_error") ==
              "FileNotFoundError" and "process_error" not in attempt.receipt["commands"][-1])
        attempt.scratch = Path(tempfile.mkdtemp(prefix="mixer-browser-callback-ci-contract-"))
        attempt.receipt.update(owned_scratch=str(attempt.scratch),
                               scratch_identity=module.identity(attempt.scratch))
        data = attempt.scratch / "data"
        attempt.run("initdb", [pg / "initdb", "-D", data, "-U", "browser_admin", "-A",
                              "trust", "--no-locale", "-E", "UTF8"])
        attempt.receipt["data_identity"] = module.identity(data)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        attempt.receipt["port"] = port
        try:
            attempt.run("postgres-start", [pg / "pg_ctl", "-D", data, "-l", output / "postgres.log",
                        "-o", f"-h 127.0.0.1 -p {port} -k ''", "-w", "start"])
        finally:
            if (data / "postmaster.pid").is_file():
                attempt.receipt["postmaster_identity"] = (data / "postmaster.pid").read_text().splitlines()[:4]
        try:
            attempt.run("forced-command-failure", [sys.executable, "-c", "raise SystemExit(7)"])
        except RuntimeError:
            check("command failure is propagated", True)
        else:
            check("command failure is propagated", False)
        finally:
            attempt.cleanup()
        check("actual PostgreSQL failure cleanup is complete", all(attempt.receipt["cleanup"].values()))
        no_tools = dict(os.environ, PATH=str(output / "empty-path"))
        failed_parent = output / "preflight-failures"
        check("missing selected tool makes a retained failed attempt", cli("missing-tool-first",
              ["--pg-bin", pg, "--output", failed_parent], env=no_tools).returncode == 1)
        first = next(failed_parent.iterdir())
        first_hash = module.sha(first / "receipt.json")
        check("second invocation creates a separate retained failed attempt", cli("missing-tool-second",
              ["--pg-bin", pg, "--output", failed_parent], env=no_tools).returncode == 1)
        retained = list(failed_parent.iterdir())
        check("failed attempts preserve prior receipt bytes", len(retained) == 2 and
              first_hash == module.sha(first / "receipt.json"))
        check("preflight failures allocate no scratch or PG", all(
              json.loads((p / "receipt.json").read_text())["cleanup"] == {
                  "no_native_capture_browser_phone_or_provider_started": True,
                  "owned_scratch_absent": True, "postmaster_absent": True} for p in retained))
    except BaseException as error:
        checks.append({"name": "unexpected failure", "passed": False,
                       "error": type(error).__name__ + ": " + str(error)})
    finally:
        if attempt and attempt.scratch and attempt.scratch.exists():
            attempt.cleanup()
        after = {str(p.relative_to(ROOT)): module.sha(p) for p in source_paths}
        checks.append({"name": "contract source bytes unchanged", "passed": before == after})
        receipt = {"schema": 1, "scope": __doc__, "python": sys.version,
                   "revision": locals().get("revision"), "git_tree": locals().get("git_tree"),
                   "sources": before, "sources_after": after,
                   "source_tree_sha256": module.tree(before), "source_tree_after_sha256": module.tree(after),
                   "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "invocation": [sys.executable, *sys.argv], "commands": commands,
                   "runner_sha256": module.sha(RUNNER), "checks": checks,
                   "owned_failure_attempt": attempt.receipt if attempt else None,
                   "success": bool(checks) and all(c["passed"] for c in checks)}
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        print(output)
        print(json.dumps({"success": receipt["success"], "checks": len(checks)}))
    return 0 if receipt["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
