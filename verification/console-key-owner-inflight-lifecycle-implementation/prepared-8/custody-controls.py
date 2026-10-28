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
import vm_cleanup
import permission_controls

CASES = ["happy", "no-ack", "journal-failure", "cancel-after-ack", "native-timeout",
         "immutable-and-bindings", "out-of-order", "prepublication", "post-spawn-prepublication",
         "journal-short-write", "journal-zero-write", "journal-fsync-failure", "journal-truncation",
         "completion-acceptance-short-write", "exit-grant-intent-fsync-failure",
         "wrapper-term", "malformed-ack", "replayed-ack"]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    args = parser.parse_args()
    prepared = Path(__file__).resolve().parent
    if prepared.name != "prepared-8" or not sys.dont_write_bytecode:
        raise ValueError("exact prepared-8 Python -B control invocation required")
    plan_path = prepared / "control-plan.json"
    plan = custody.read(plan_path, 1048576)
    release = custody.read(args.release, 16384)
    plan_sha = custody.sha(plan_path.read_bytes())
    if release.get("status") != "root-released-exact-plan" or release.get("single_execution") is not True or release.get("execution_plan_sha256") != plan_sha:
        raise ValueError("exact single-execution control release required")
    if type(plan["limits"]["combined_artifact_bytes"]) is not int or plan["limits"]["combined_artifact_bytes"] != 1048576:
        raise ValueError("exact selected one MiB combined artifact cap required")
    started = time.monotonic()
    work, cleanup, post, terminal = [started + x for x in [40, 46, 52, 55]]
    signals = []
    for number in custody.SIGNALS:
        signal.signal(number, lambda value, _frame: signals.append(value))
    output = prepared.parent / "executions" / "custody-controls-5"
    output.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-custody-controls-", dir="/private/tmp"))
    results = []
    errors = []
    children = []
    managers = []
    preserved = []
    prior_ack = None
    helper_owners = []
    helper_checks = []
    permission_checks = []
    fixture_observations = []
    try:
        for row in plan["tools"]:
            path = Path(row["path"])
            if path.stat().st_size != row["bytes"] or custody.sha(path.read_bytes()) != row["sha256"]:
                raise ValueError("control tool pin differs")
        for row in plan["canonical_inputs"]:
            source = Path(plan["workspace_root"]) / row["path"]
            if source.stat().st_size != row["bytes"] or custody.sha(source.read_bytes()) != row["sha256"]:
                raise ValueError("control selected canonical pin differs")
        for row in plan["prepared_files"]:
            source = prepared / row["path"]
            if custody.sha(source.read_bytes()) != row["sha256"]:
                raise ValueError("control prepared pin differs")
        (scratch / "bin").mkdir()
        for name in ["custody.py", "process_authority.py", "fake-custody-child.py"]:
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
            if case in ["happy", "native-timeout"]:
                helper_marker = case_scratch / "vm-helper-marker"
                helper_command = [plan["python"], "-B", str(scratch / "fake-custody-child.py"),
                                  "normal" if case == "happy" else "timeout", str(helper_marker)]
                helper_environment = {"PATH": "/usr/bin:/bin", "LANG": "en_US.UTF-8", "HOME": str(case_scratch), "TMPDIR": str(case_scratch)}
                custody.publish(case_output / "vm-cleanup-command.json", {"argv": helper_command, "environment": helper_environment, "cwd": str(case_scratch)})
                helper_child = subprocess.Popen(helper_command, env=helper_environment, cwd=case_scratch,
                                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
                helper_owner = vm_cleanup.RetainedChild(helper_child)
                helper_owners.append(helper_owner)
                timed_out = False
                if helper_owner.uncertain:
                    raise ValueError("helper leader identity retention failed")
                if case == "happy":
                    helper_child.wait(timeout=max(0.001, min(1, work - time.monotonic())))
                else:
                    marker_until = min(work, time.monotonic() + 0.5)
                    while not helper_marker.exists() and time.monotonic() < marker_until:
                        time.sleep(0.005)
                    if not helper_marker.exists() or int(helper_marker.read_text()) != helper_child.pid:
                        raise ValueError("running cleanup subcheck lacks exact active child marker")
                    try:
                        helper_child.wait(timeout=0.05)
                    except subprocess.TimeoutExpired:
                        timed_out = True
                    if not timed_out:
                        raise ValueError("running cleanup subcheck did not time out")
                helper_observation = helper_owner.cleanup(min(cleanup, time.monotonic() + 1))
                helper_passed = (helper_observation["direct_child_reaped"] and helper_observation["group_absent"] and
                                 not helper_observation["uncertain"] and not helper_observation["permission_denied"])
                if case == "happy":
                    helper_passed &= helper_observation["mode"] == "completed-observe" and helper_observation["signals"] == []
                else:
                    helper_passed &= (timed_out and helper_observation["mode"] == "running-retirement" and
                                      helper_observation["identity_retained"] and helper_observation["signals"] == [int(signal.SIGTERM)])
                helper_checks.append({"case_id": case, "check": "completed-no-signal" if case == "happy" else "running-timeout",
                                      "passed": bool(helper_passed), "timeout_observed": timed_out, "cleanup": helper_observation})
                if not helper_passed:
                    raise ValueError("shared VM cleanup helper subcheck failed")
            config = {"run_nonce": custody.secrets.token_hex(16), "mode": "controls", "directory": str(case_output / "custody"),
                      "execution_plan_sha256": plan_sha, "work_deadline_ns": int(min(work, time.monotonic() + 4) * 1e9),
                      "cleanup_deadline_ns": int(cleanup * 1e9), "native_seconds": 1,
                      "owned_tmp": str(case_scratch), "control_args": [str(scratch / "fake-custody-child.py"), "timeout" if case in ["native-timeout", "wrapper-term"] else "normal", str(marker)],
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
                permission_checks = permission_controls.run(case_scratch, config)
                custody.publish(case_output / "permission-subchecks.json", permission_checks)
                if len(permission_checks) != 6 or not all(row["passed"] for row in permission_checks):
                    raise ValueError("injected permission/observe-only branch subcheck failed")
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
                manager.finalize()
                snapshot = manager.snapshot()
                custody.publish(case_output / "custody-result.json", snapshot)
                results.append({"case_id": case, "passed": True, "native_started": False, "grants": 0,
                                "groups_absent": True, "wrapper_reaped": True, "uncertain": True, "scratch_preserved": True, "journal_reconciled": False,
                                "signal_delivered": False, "completion_before_exit": False, "fault_observed": True,
                                "fault_operation": "helper", "fault_event": "", "fault_bytes_requested": 0, "fault_bytes_written": 0})
                preserved.append(str(case_scratch))
                continue
            if case == "no-ack":
                manager.close()
            if case == "out-of-order":
                manager.next = 1
            fault = {"triggered": False, "kind": "", "operation": "", "event": "", "requested": 0, "written": 0}
            if case in ["journal-failure", "journal-short-write", "journal-zero-write", "journal-fsync-failure",
                        "completion-acceptance-short-write", "exit-grant-intent-fsync-failure"]:
                def selected_write(fd, data, selected_case=case, selected_fault=fault):
                    entry = json.loads(data)
                    selected_fault["kind"] = entry["event"]
                    target = "completion" if selected_case == "completion-acceptance-short-write" else "registered"
                    if entry["event"] == target and not selected_fault["triggered"]:
                        if selected_case in ["journal-failure", "journal-short-write", "completion-acceptance-short-write"]:
                            count = os.write(fd, data[:max(1, len(data) // 2)])
                            selected_fault.update(triggered=True, operation="write-short", event=entry["event"], requested=len(data), written=count)
                            return count
                        if selected_case == "journal-zero-write":
                            selected_fault.update(triggered=True, operation="write-zero", event=entry["event"], requested=len(data), written=0)
                            return 0
                    return os.write(fd, data)
                def selected_fsync(fd, selected_case=case, selected_fault=fault):
                    target = "exit-grant-intent" if selected_case == "exit-grant-intent-fsync-failure" else "registered"
                    if selected_case in ["journal-fsync-failure", "exit-grant-intent-fsync-failure"] and selected_fault["kind"] == target and not selected_fault["triggered"]:
                        selected_fault.update(triggered=True, operation="fsync-error", event=target)
                        raise OSError(5, "selected journal fsync I/O failure")
                    return os.fsync(fd)
                manager.journal_write = selected_write
                manager.journal_fsync = selected_fsync
            if case in ["malformed-ack", "replayed-ack"]:
                def selected_ack(path, ack, cap, selected_case=case, selected_fault=fault):
                    selected_fault.update(triggered=True, operation="ack-malformed" if selected_case == "malformed-ack" else "ack-replay", event="ack")
                    value = {**ack, "ordinal": True} if selected_case == "malformed-ack" else prior_ack
                    if type(value) is not dict:
                        raise ValueError("prior full ACK unavailable for replay control")
                    return custody.publish(path, value, cap)
                manager.ack_publish = selected_ack
            signal_delivered = False
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
                    if case == "wrapper-term" and not signal_delivered and marker.exists() and manager.records.get(0, {}).get("native_started", False):
                        native_pid = manager.records[0]["child_pid"]
                        if int(marker.read_text()) != native_pid or os.getpgid(native_pid) != child.pid:
                            raise ValueError("selected signal requires exact acknowledged active native child")
                        custody.publish(case_output / "signal.json", {"signal": int(signal.SIGTERM), "wrapper_pid": child.pid,
                                        "native_pid": native_pid, "native_group": child.pid, "at_ns": time.monotonic_ns()})
                        os.kill(child.pid, signal.SIGTERM)
                        signal_delivered = True
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
                manager.observe_wrapper_exit(child.pid, child.returncode)
                if case == "journal-truncation":
                    journal_path = case_output / "custody-journal.jsonl"
                    fd = os.open(journal_path, os.O_WRONLY)
                    try:
                        before = os.fstat(fd).st_size
                        os.ftruncate(fd, max(0, before - 1))
                        os.fsync(fd)
                        fault.update(triggered=True, operation="truncate", event="terminal", requested=before, written=os.fstat(fd).st_size)
                    finally:
                        os.close(fd)
                manager.finalize()
            finally:
                selector.close()
                child.stdout.close()
            (case_output / "stdout.txt").write_bytes(captured)
            snapshot = manager.snapshot()
            custody.publish(case_output / "custody-result.json", snapshot)
            completions = [custody.read(path) for path in (case_output / "custody").glob("*.completion.json")]
            native_started = any(row["native_started"] for row in snapshot["records"]) or any(row["native_started"] for row in completions)
            refused = any(row["permission_denied"] for row in snapshot["records"])
            fixture_code = child.poll()
            fixture_observations.append({"case_id": case, "wrapper_pid": child.pid, "direct_reaped": fixture_code is not None,
                                         "custody_permission_refused": refused, "custody_resolution": "unresolved-refused" if refused else "observed",
                                         "fixture_group_probe_performed": not refused})
            all_absent = not refused and all(row["group_absent"] for row in snapshot["records"]) and custody.absent(child.pid)
            event_names = [entry["event"] for entry in manager.events]
            completion_before_exit = ("completion" in event_names and "exit-grant-intent" in event_names and
                                      event_names.index("completion") < event_names.index("exit-grant-intent"))
            completion_errors = [error for row in completions for error in row["errors"]]
            fully_waited = bool(completions) and all(row["child_reaped"] for row in completions)
            exit_exists = (case_output / "custody/00.exit.json").exists()
            if case == "happy":
                prior_ack = custody.read(case_output / "custody/00.ack.json")
                passed = child.returncode == 0 and manager.grants == 1 and not manager.uncertain and native_started and manager.journal_reconciled and completion_before_exit
            elif case in ["no-ack", "out-of-order", "prepublication"]:
                passed = not marker.exists() and manager.grants == 0 and manager.uncertain
            elif case in ["journal-failure", "journal-short-write", "journal-zero-write", "journal-fsync-failure"]:
                passed = fault["triggered"] and not marker.exists() and manager.grants == 0 and manager.uncertain and not manager.journal_reconciled
            elif case == "journal-truncation":
                passed = fault["triggered"] and manager.grants == 1 and native_started and manager.uncertain and not manager.journal_reconciled and completion_before_exit
            elif case in ["completion-acceptance-short-write", "exit-grant-intent-fsync-failure"]:
                accepted = "completion" in event_names
                passed = (fault["triggered"] and manager.grants == 1 and native_started and fully_waited and manager.uncertain and
                          not manager.journal_reconciled and not exit_exists and accepted == (case == "exit-grant-intent-fsync-failure"))
            elif case in ["malformed-ack", "replayed-ack"]:
                rejection = "ACK field types differ" if case == "malformed-ack" else "ACK binding differs"
                passed = fault["triggered"] and manager.grants == 1 and not marker.exists() and not native_started and manager.uncertain and any(rejection in error for error in completion_errors)
            elif case == "wrapper-term":
                passed = (signal_delivered and manager.grants == 1 and manager.uncertain and native_started and fully_waited and
                          child.returncode != 0 and any("local cancellation" in error for error in completion_errors))
            elif case == "cancel-after-ack":
                passed = manager.grants == 1 and bool(cancelled) and all_absent
            elif case == "native-timeout":
                passed = manager.grants == 1 and manager.uncertain and native_started and child.returncode != 0 and fully_waited
            else:
                passed = manager.grants == 1 and manager.uncertain and len(completions) == 1 and completions[0]["native_started"] and completions[0]["child_pid"] > 1 and completions[0]["child_reaped"]
            keep = manager.uncertain
            if keep:
                preserved.append(str(case_scratch))
            else:
                shutil.rmtree(case_scratch)
            results.append({"case_id": case, "passed": bool(passed and all_absent), "native_started": native_started,
                            "grants": manager.grants, "groups_absent": all_absent, "wrapper_reaped": child.returncode is not None,
                            "uncertain": manager.uncertain, "scratch_preserved": keep,
                            "journal_reconciled": manager.journal_reconciled, "signal_delivered": signal_delivered,
                            "completion_before_exit": completion_before_exit, "fault_observed": fault["triggered"],
                            "fault_operation": fault["operation"], "fault_event": fault["event"],
                            "fault_bytes_requested": fault["requested"], "fault_bytes_written": fault["written"]})
    except BaseException as exc:
        errors.append(type(exc).__name__ + ": " + str(exc))
    finally:
        for owner in helper_owners:
            try:
                helper_terminal = owner.cleanup(cleanup)
                if helper_terminal["uncertain"] or not helper_terminal["direct_child_reaped"] or not helper_terminal["group_absent"]:
                    errors.append("shared helper cleanup: " + json.dumps(helper_terminal, sort_keys=True))
            except BaseException as exc:
                errors.append("shared helper cleanup exception: " + repr(exc))
        for manager in managers:
            try:
                manager.close()
                manager.drain(cleanup)
                manager.finalize()
                result_path = manager.directory.parent / "custody-result.json"
                if not result_path.exists():
                    custody.publish(result_path, manager.snapshot())
            except BaseException as exc:
                errors.append("control custody cleanup: " + repr(exc))
        # Direct children are retained separately by this control launcher. It never
        # invents group custody for an unpublished real System.cmd wrapper.
        for child in children:
            denied = any(record["permission_denied"] for manager in managers for record in manager.records.values() if record["wrapper_pid"] == child.pid)
            if child.poll() is None and denied:
                errors.append("fixture Popen cleanup observes only; Custodian refusal remains unresolved: " + str(child.pid))
                continue
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=max(0.001, cleanup - time.monotonic()))
            if not denied and not custody.absent(child.pid):
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
            if case_output.name in ["happy", "native-timeout"]:
                allowed.add("vm-cleanup-command.json")
            if case_output.name == "wrapper-term":
                allowed.add("signal.json")
            if case_output.name == "immutable-and-bindings":
                allowed.update(["immutable.json", "permission-subchecks.json"])
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
                    if item.stat().st_size > 131072 or total_bytes > plan["limits"]["combined_artifact_bytes"]:
                        errors.append("control artifact byte cap")
        if (sum(row["grants"] for row in results) > plan["maximum_fake_native_grants"] or
                sum(row["native_started"] for row in results) > plan["maximum_custody_fake_native_launches"] or
                sum(row["native_started"] for row in results) + len(helper_owners) > plan["maximum_fake_native_launches"]):
            errors.append("finite control native grant/launch cap")
        complete_helpers = [row["check"] for row in helper_checks] == ["completed-no-signal", "running-timeout"] and all(row["passed"] for row in helper_checks)
        complete_permissions = [row["check"] for row in permission_checks] == plan["synthetic_permission_subchecks"] and all(row["passed"] for row in permission_checks)
        status = "passed" if not errors and [row["case_id"] for row in results] == CASES and all(x["passed"] for x in results) and complete_helpers and complete_permissions else "failed"
        report = {"schema": 1, "status": status, "cases": results, "errors": errors,
                  "preserved_scratch": preserved, "vm_cleanup_subchecks": helper_checks,
                  "permission_subchecks": permission_checks, "fixture_observations": fixture_observations,
                  "elapsed_ms": round((time.monotonic() - started) * 1000)}
        if total_bytes + len(custody.encoded(report)) > plan["limits"]["combined_artifact_bytes"]:
            errors.append("combined control artifacts including terminal report exceed selected cap")
            status = report["status"] = "failed"
        if total_bytes + len(custody.encoded(report)) > plan["limits"]["combined_artifact_bytes"]:
            raise ValueError("no capped terminal report fits; evidence/scratch retained")
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
