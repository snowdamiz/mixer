#!/opt/homebrew/opt/python@3.14/bin/python3.14
"""Frozen bounded original/corrected CI regression; requires root's plan release."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PLAN = OUT / "execution-plan.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(entry):
    path = Path(entry["path"])
    if not path.is_absolute():
        path = ROOT / path
    if path.stat().st_size != entry["bytes"] or sha(path) != entry["sha256"]:
        raise RuntimeError("frozen input changed: " + entry["path"])
    return path


def main():
    began = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()
    for name in ("regression-receipt.json", "regression.stdout.txt", "bootstraps"):
        if (OUT / name).exists():
            raise SystemExit("refusing to overwrite retained evidence: " + name)
    plan = json.loads(PLAN.read_text())
    release_path = OUT / "host-execution-release.json"
    if not release_path.exists():
        raise SystemExit("root compiler/runtime release is required")
    release = json.loads(release_path.read_text())
    if release.get("released") is not True or release.get("execution_plan_sha256") != sha(PLAN):
        raise SystemExit("root release does not bind this frozen plan")
    if sha(Path(__file__)) != plan["runner_sha256"]:
        raise SystemExit("runner changed after plan freeze")
    inputs = plan["tool_files"] + plan["sources"] + plan["tests"] + plan["support_files"]
    inputs += [entry for dep in plan["dependencies"] for entry in dep["files"]]
    output = bytearray()
    phases = []
    scratch_path = None
    scratch_removed = False
    status = "not-started"
    error = None
    postrun_changes = []
    copy_count = 0
    bootstraps = OUT / "bootstraps"
    process = None
    current = None
    work_deadline = began + plan["limits"]["work_wall_seconds"]
    final_deadline = began + plan["limits"]["total_wall_seconds"]

    def remaining_work():
        remaining = work_deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("overall work deadline reached")
        return remaining

    def group_present(stage):
        try:
            os.killpg(current["owned_pgid"], 0)
            present = True
        except ProcessLookupError:
            present = False
        current["exact_owned_group_checks"].append({"stage": stage, "pgid": current["owned_pgid"], "present": present})
        return present

    def cleanup_owned():
        nonlocal process
        if process is None:
            return
        limit = min(final_deadline, time.monotonic() + plan["limits"]["owned_cleanup_seconds"])
        if group_present("before-cleanup"):
            try:
                os.killpg(current["owned_pgid"], signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(timeout=max(0.001, limit - time.monotonic()))
        current["exit_code"] = process.returncode
        current["direct_child_reaped"] = True
        while group_present("after-reap") and time.monotonic() < limit:
            time.sleep(min(0.01, max(0, limit - time.monotonic())))
        current["owned_group_absent"] = not current["exact_owned_group_checks"][-1]["present"]
        if process.stdout:
            process.stdout.close()
        process = None
        if not current["owned_group_absent"]:
            raise RuntimeError("owned process group survived cleanup budget")

    def copy(entry, target):
        nonlocal copy_count
        remaining_work()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(verify(entry), target)
        if target.stat().st_size != entry["bytes"] or sha(target) != entry["sha256"]:
            raise RuntimeError("copied input mismatch")
        copy_count += 1
        return str(target)

    try:
        for entry in inputs:
            remaining_work()
            verify(entry)
        with tempfile.TemporaryDirectory(prefix="mixer-dead-admission-ci-") as temporary:
            scratch = Path(temporary)
            scratch_path = str(scratch)
            app_ebin = scratch / "app-ebin"
            app_ebin.mkdir()
            dep_paths, dep_beams, checks = [], [], []
            quoted = lambda value: json.dumps(value, ensure_ascii=False)
            for dep in plan["dependencies"]:
                ebin = scratch / "deps" / dep["name"] / "ebin"
                ebin.mkdir(parents=True)
                dep_paths.append(str(ebin))
                for entry in dep["files"]:
                    target = ebin / Path(entry["path"]).name
                    copy(entry, target)
                    if target.suffix == ".beam":
                        dep_beams.append(str(target))
                name = dep["name"]
                checks.append(f'case Application.load(:{name}) do :ok -> :ok; {{:error, {{:already_loaded, :{name}}}}} -> :ok; _ -> raise "dependency metadata unavailable" end\ntrue = to_string(Application.spec(:{name}, :vsn)) == {quoted(dep["version"])}')
            sources = [copy(entry, scratch / entry["path"]) for entry in plan["sources"]]
            tests = [copy(entry, scratch / entry["path"]) for entry in plan["tests"]]
            original = copy(plan["support_files"][0], scratch / "original-tests/browser_workspace_dispatcher_test.exs")
            template = verify(plan["support_files"][1]).read_text()
            bootstraps.mkdir()
            env = {key: os.environ[key] for key in ("HOME", "USER", "TMPDIR") if key in os.environ}
            env.update(plan["environment"])
            status = "running"
            for spec in plan["phases"]:
                remaining_work()
                test_paths = tests if spec["name"] == "corrected-absent" else [original if spec["name"] == "original-dead" else tests[-1]]
                replacements = {
                    "@@DEPENDENCY_PATHS@@": quoted(dep_paths),
                    "@@DEPENDENCY_BEAMS@@": quoted(dep_beams),
                    "@@DEPENDENCY_CHECKS@@": "\n".join(checks),
                    "@@PHASE_NAME@@": quoted(spec["name"]),
                    "@@APP_EBIN@@": quoted(str(app_ebin)),
                    "@@CANONICAL_TEST_PATHS@@": quoted(tests),
                    "@@SOURCE_PATHS@@": quoted(sources),
                    "@@POINTER_MODE@@": ":" + spec["pointer_mode"],
                    "@@TEST_PATHS@@": quoted(test_paths),
                    "@@EXPECTED_TOTAL@@": str(spec["expected_total"]),
                    "@@EXPECTED_FAILURES@@": str(spec["expected_failures"]),
                    "@@EXPECTED_DISPATCH@@": ":" + spec["expected_dispatch"],
                }
                script = template
                for token, value in replacements.items():
                    script = script.replace(token, value)
                if "@@" in script:
                    raise RuntimeError("unsubstituted bootstrap token")
                script_path = scratch / (spec["name"] + ".exs")
                script_path.write_text(script)
                with (bootstraps / (spec["name"] + ".exs.txt")).open("x") as retained:
                    retained.write(script)
                argv = [plan["elixir_executable"], "--no-color", "--erl", "+S 2:2 +A 2", str(script_path)]
                phase_begin = time.monotonic()
                current = {"name": spec["name"], "argv": argv, "bootstrap_sha256": sha(script_path), "owned_pid": None, "owned_pgid": None, "exit_code": None, "direct_child_reaped": False, "owned_group_absent": False, "exact_owned_group_checks": []}
                phases.append(current)
                process = subprocess.Popen(argv, cwd=scratch, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
                current["owned_pid"] = current["owned_pgid"] = process.pid
                selector = selectors.DefaultSelector()
                selector.register(process.stdout, selectors.EVENT_READ)
                phase_deadline = min(work_deadline, phase_begin + spec["work_seconds"])
                phase_output = bytearray()
                try:
                    while selector.get_map():
                        if time.monotonic() >= phase_deadline:
                            raise TimeoutError("phase work deadline reached")
                        for key, _ in selector.select(timeout=min(0.05, max(0, phase_deadline - time.monotonic()))):
                            chunk = os.read(key.fileobj.fileno(), 65536)
                            if not chunk:
                                selector.unregister(key.fileobj)
                                continue
                            available = plan["limits"]["combined_output_bytes"] - len(output)
                            output.extend(chunk[:available])
                            phase_output.extend(chunk[:available])
                            if len(chunk) > available:
                                raise RuntimeError("combined output limit reached")
                        if process.poll() is not None and group_present("leader-exited"):
                            try:
                                os.killpg(current["owned_pgid"], signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                    process.wait(timeout=max(0.001, phase_deadline - time.monotonic()))
                finally:
                    selector.close()
                    cleanup_owned()
                    current["elapsed_seconds"] = round(time.monotonic() - phase_begin, 3)
                    current["output_bytes"] = len(phase_output)
                    current["output_sha256"] = hashlib.sha256(phase_output).hexdigest()
                if current["exit_code"] != 0 or ("PHASE_PASS " + spec["name"]).encode() not in phase_output:
                    raise RuntimeError("phase did not satisfy regression assertions")
                current["status"] = "passed"
            status = "passed"
    except BaseException as caught:
        status = "failed"
        error = type(caught).__name__ + ": " + str(caught)
    finally:
        try:
            cleanup_owned()
        except BaseException as caught:
            status = "cleanup-failed"
            error = type(caught).__name__ + ": " + str(caught)
        scratch_removed = scratch_path is not None and not Path(scratch_path).exists()
        if scratch_path and not scratch_removed:
            status = "scratch-cleanup-failed"
        for entry in inputs:
            try:
                verify(entry)
            except (RuntimeError, OSError):
                postrun_changes.append(entry["path"])
        if postrun_changes:
            status = "original-input-changed"
        elapsed = round(time.monotonic() - began, 3)
        if elapsed > plan["limits"]["total_wall_seconds"]:
            status = "total-wall-limit-exceeded"
        with (OUT / "regression.stdout.txt").open("xb") as retained:
            retained.write(output)
        receipt = {"schema": 1, "status": status, "started_at": started_at, "elapsed_seconds": elapsed, "error": error, "runner_argv": plan["runner_argv"], "runner_python_version": sys.version, "execution_plan_sha256": sha(PLAN), "source_revision": plan["source_revision"], "source_tree": plan["source_tree"], "source_closure_sha256": plan["source_closure_sha256"], "scratch": scratch_path, "scratch_removed": scratch_removed, "copied_inputs_verified": copy_count, "postrun_original_inputs_verified": len(inputs) - len(postrun_changes), "postrun_original_changes": postrun_changes, "phases": phases, "output_bytes": len(output), "output_sha256": hashlib.sha256(output).hexdigest(), "limits": plan["limits"], "pending": plan["pending"], "no_native_capture_database_container_network_resources_started": True}
        with (OUT / "regression-receipt.json").open("x") as retained:
            retained.write(json.dumps(receipt, indent=2) + "\n")
        sys.stdout.buffer.write(output)
        print(json.dumps({"status": status, "elapsed_seconds": elapsed, "scratch_removed": scratch_removed, "phase_count": len(phases), "output_bytes": len(output), "error": error}))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
