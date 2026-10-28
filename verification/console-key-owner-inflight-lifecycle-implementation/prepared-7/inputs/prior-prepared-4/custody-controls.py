#!/usr/bin/env python3
"""Separately released fake-child controls; no Elixir, TLS or real OpenSSL."""
from pathlib import Path
import hashlib
import json
import os
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import custody

CASES = ["happy", "no-ack", "journal-failure", "cancel-after-ack", "native-timeout",
         "immutable-and-bindings", "out-of-order", "prepublication", "post-spawn-prepublication"]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    args = parser.parse_args()
    prepared = Path(__file__).resolve().parent
    if prepared.name != "prepared-4" or not sys.dont_write_bytecode:
        raise ValueError("exact prepared-4 Python -B control invocation required")
    plan_path = prepared / "control-plan.json"
    plan = custody.read(plan_path, 1048576)
    release = custody.read(args.release, 16384)
    plan_sha = custody.sha(plan_path.read_bytes())
    if release.get("status") != "root-released-exact-plan" or release.get("single_execution") is not True or release.get("execution_plan_sha256") != plan_sha:
        raise ValueError("exact single-execution control release required")
    started = time.monotonic()
    work, cleanup, post, terminal = [started + x for x in [40, 46, 52, 55]]
    signals = []
    for number in custody.SIGNALS:
        signal.signal(number, lambda value, _frame: signals.append(value))
    output = prepared.parent / "executions" / "custody-controls-1"
    output.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-custody-controls-", dir="/private/tmp"))
    results = []
    errors = []
    children = []
    managers = []
    preserved = []
    try:
        for row in plan["tools"]:
            path = Path(row["path"])
            if path.stat().st_size != row["bytes"] or custody.sha(path.read_bytes()) != row["sha256"]:
                raise ValueError("control tool pin differs")
        for row in plan["prepared_files"]:
            source = prepared / row["path"]
            if custody.sha(source.read_bytes()) != row["sha256"]:
                raise ValueError("control prepared pin differs")
        (scratch / "bin").mkdir()
        for name in ["custody.py", "fake-custody-child.py"]:
            shutil.copyfile(prepared / name, scratch / name)
        shutil.copyfile(prepared / "bin/openssl", scratch / "bin/openssl")
        (scratch / "bin/openssl").chmod(0o700)
        for case in CASES:
            if time.monotonic() >= work or signals:
                raise TimeoutError("control work deadline/signal")
            case_output = output / case
            case_output.mkdir()
            case_scratch = scratch / case
            case_scratch.mkdir()
            marker = case_scratch / "native-marker"
            config = {"run_nonce": custody.secrets.token_hex(16), "mode": "controls", "directory": str(case_output / "custody"),
                      "execution_plan_sha256": plan_sha, "work_deadline_ns": int(min(work, time.monotonic() + 4) * 1e9),
                      "cleanup_deadline_ns": int(cleanup * 1e9), "native_seconds": 1,
                      "owned_tmp": str(case_scratch), "control_args": [str(scratch / "fake-custody-child.py"), "timeout" if case == "native-timeout" else "normal", str(marker)],
                      "pause_before_spawn_ms": 200 if case == "cancel-after-ack" else 0,
                      "fail_before_publish": case == "prepublication", "fail_after_spawn": case == "post-spawn-prepublication"}
            for role, path in [("wrapper", scratch / "bin/openssl"), ("interpreter", Path(plan["python"])), ("native", Path(plan["python"]))]:
                config[role + "_path"] = str(path)
                config[role + "_sha256"] = custody.sha(path.read_bytes())
            cancelled = []
            manager = custody.Custodian(case_output / "custody", config, case_output / "custody-journal.jsonl", lambda case_cancelled=cancelled: bool(signals or case_cancelled))
            managers.append(manager)
            config_path = case_scratch / "config.json"
            custody.publish(config_path, config, 16384)
            if case == "immutable-and-bindings":
                target = case_output / "immutable.json"
                first = {"first": True}
                custody.publish(target, first)
                rejected = 0
                try:
                    custody.publish(target, {"first": False})
                except FileExistsError:
                    rejected += 1
                for phase, nonce in [("prod", config["run_nonce"]), ("test", "cross-run")]:
                    request = {"phase": phase, "run_nonce": nonce, "recipe_id": "version", "invocation_nonce": "a" * 32,
                               "ordinal": 0, "wrapper_pid": 2, "wrapper_pgid": 2, "wrapper_sid": 2,
                               "published_ns": time.monotonic_ns(), "argv": config["control_args"]}
                    for role in ["wrapper", "interpreter", "native"]:
                        request[role + "_path"] = config[role + "_path"]
                        request[role + "_sha256"] = config[role + "_sha256"]
                    try:
                        custody.validate_request(request, config)
                    except ValueError as exc:
                        assert "run/phase" in str(exc)
                        rejected += 1
                assert custody.read(target) == first and rejected == 3
                terminal_record = {"group_absent": True}
                assert manager.inspect(terminal_record) is False
                original_absent, original_identity = custody.absent, custody.identity_live
                try:
                    custody.absent = lambda _pgid: False
                    custody.identity_live = lambda *_args: (_ for _ in ()).throw(AssertionError("lost identity re-armed"))
                    assert manager.inspect({"group_absent": False, "wrapper_pgid": 999999, "identity_lost": True}) is False
                finally:
                    custody.absent, custody.identity_live = original_absent, original_identity
                manager.fail("selected metadata rejection control", uncertain=True)
                snapshot = manager.snapshot()
                custody.publish(case_output / "custody-result.json", snapshot)
                results.append({"case_id": case, "passed": True, "native_started": False, "grants": 0,
                                "groups_absent": True, "wrapper_reaped": True, "uncertain": True, "scratch_preserved": True})
                preserved.append(str(case_scratch))
                continue
            if case == "no-ack":
                manager.close()
            if case == "out-of-order":
                manager.next = 1
            if case == "journal-failure":
                original_event = manager.event
                def selected_failure(kind, ordinal=-1, detail=""):
                    if kind == "registered":
                        raise OSError("selected journal failure before ACK")
                    return original_event(kind, ordinal, detail)
                manager.event = selected_failure
            environment = {"PATH": "/usr/bin:/bin", "LANG": "en_US.UTF-8", "HOME": str(case_scratch), "TMPDIR": str(case_scratch),
                           "MIXER_CUSTODY_CONFIG": str(config_path), "MIXER_OPENSSL_STARTED": str(case_output / "native-started.jsonl"),
                           "MIXER_OPENSSL_AUDIT": str(case_output / "native-audit.jsonl")}
            command = [str(scratch / "bin/openssl"), *config["control_args"]]
            custody.publish(case_output / "command.json", {"argv": command, "environment": environment})
            child = subprocess.Popen(command, env=environment, cwd=scratch, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
            children.append(child)
            selector = selectors.DefaultSelector()
            captured = bytearray()
            try:
                selector.register(child.stdout, selectors.EVENT_READ)
                until = min(work, time.monotonic() + 5)
                while time.monotonic() < until and child.poll() is None:
                    manager.service()
                    if case == "cancel-after-ack" and manager.grants and not cancelled:
                        cancelled.append(True)
                        manager.close()
                    for key, _ in selector.select(0.005):
                        chunk = os.read(key.fileobj.fileno(), 4096)
                        captured.extend(chunk)
                        if len(captured) > 65536:
                            raise ValueError("control stdout cap")
                if case == "prepublication":
                    manager.fail("selected prepublication failure; no containment claim")
                manager.drain(cleanup)
                child.wait(timeout=max(0.001, cleanup - time.monotonic()))
                manager.service()
            finally:
                selector.close()
                child.stdout.close()
            (case_output / "stdout.txt").write_bytes(captured)
            snapshot = manager.snapshot()
            custody.publish(case_output / "custody-result.json", snapshot)
            completions = [custody.read(path) for path in (case_output / "custody").glob("*.completion.json")]
            native_started = any(row["native_started"] for row in snapshot["records"]) or any(row["native_started"] for row in completions)
            all_absent = all(row["group_absent"] for row in snapshot["records"]) and custody.absent(child.pid)
            if case == "happy":
                passed = child.returncode == 0 and manager.grants == 1 and not manager.uncertain and native_started
            elif case in ["no-ack", "journal-failure", "out-of-order", "prepublication"]:
                passed = not marker.exists() and manager.grants == 0 and manager.uncertain
            elif case == "cancel-after-ack":
                passed = manager.grants == 1 and bool(cancelled) and all_absent
            elif case == "native-timeout":
                passed = manager.grants == 1 and manager.uncertain and native_started and child.returncode != 0
            else:
                passed = manager.grants == 1 and manager.uncertain and len(completions) == 1 and completions[0]["native_started"] and completions[0]["child_pid"] > 1 and completions[0]["child_reaped"]
            keep = manager.uncertain
            if keep:
                preserved.append(str(case_scratch))
            else:
                shutil.rmtree(case_scratch)
            results.append({"case_id": case, "passed": bool(passed and all_absent), "native_started": native_started,
                            "grants": manager.grants, "groups_absent": all_absent, "wrapper_reaped": child.returncode is not None,
                            "uncertain": manager.uncertain, "scratch_preserved": keep})
    except BaseException as exc:
        errors.append(type(exc).__name__ + ": " + str(exc))
    finally:
        for manager in managers:
            try:
                manager.close()
                manager.drain(cleanup)
                result_path = manager.directory.parent / "custody-result.json"
                if not result_path.exists():
                    custody.publish(result_path, manager.snapshot())
            except BaseException as exc:
                errors.append("control custody cleanup: " + repr(exc))
        # Direct children are retained separately by this control launcher. It never
        # invents group custody for an unpublished real System.cmd wrapper.
        for child in children:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=max(0.001, cleanup - time.monotonic()))
            if not custody.absent(child.pid):
                errors.append("exact control wrapper group remains: " + str(child.pid))
        if time.monotonic() >= post or signals:
            errors.append("control deadline/signal")
        if {path.name for path in output.iterdir()} != set(CASES):
            errors.append("exact control case directory membership differs")
        total_bytes = 0
        for case_output in output.iterdir():
            if case_output.name not in CASES or case_output.is_symlink() or not case_output.is_dir():
                errors.append("unexpected control output root member")
                continue
            allowed = {"custody", "custody-journal.jsonl", "custody-result.json", "command.json", "stdout.txt",
                       "native-started.jsonl", "native-audit.jsonl"}
            if case_output.name == "immutable-and-bindings":
                allowed.add("immutable.json")
            for member in case_output.iterdir():
                if member.name not in allowed or member.is_symlink():
                    errors.append("unexpected control case output member")
                files = list(member.iterdir()) if member.name == "custody" and member.is_dir() else [member]
                if len(files) > 104:
                    errors.append("control spool member cap")
                for item in files:
                    if item.is_symlink() or not item.is_file():
                        errors.append("nonordinary control artifact")
                        continue
                    total_bytes += item.stat().st_size
                    if item.stat().st_size > 131072 or total_bytes > 1048576:
                        errors.append("control artifact byte cap")
        status = "passed" if not errors and len(results) == len(CASES) and all(x["passed"] for x in results) else "failed"
        report = {"schema": 1, "status": status, "cases": results, "errors": errors,
                  "preserved_scratch": preserved, "elapsed_ms": round((time.monotonic() - started) * 1000)}
        import importlib.util
        spec = importlib.util.spec_from_file_location("control_artifact_validation", prepared / "artifact-validation.py")
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        validator.validate(report, custody.read(prepared / "control-artifact-schema.json"))
        custody.publish(output / "control-results.json", report)
        if not preserved and not errors:
            shutil.rmtree(scratch)
        if time.monotonic() >= terminal:
            raise TimeoutError("control terminal deadline")
        print(json.dumps({"status": status, "receipt": str(output / "control-results.json")}))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
