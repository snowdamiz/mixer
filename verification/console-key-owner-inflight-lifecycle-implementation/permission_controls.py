"""Injected no-process checks of the actual custody/native authority branches."""
from pathlib import Path
import errno
import time

import custody
import process_authority

OPERATIONS = ["os.killpg(wrapper_pgid,0)", "os.getpgid(wrapper_pid)", "os.getsid(wrapper_pid)",
              "os.getpgrp(runner)", "os.killpg(wrapper_pgid,SIGTERM)", "os.killpg(wrapper_pgid,SIGKILL)"]


def model_manager(root, config, selected):
    root = Path(root)
    root.mkdir()
    local = {**config, "run_nonce": config["run_nonce"] + "-" + selected}
    manager = custody.Custodian(root / "custody", local, root / "journal.jsonl")
    record = {"run_nonce": local["run_nonce"], "phase": "test", "ordinal": 0, "recipe_id": "version",
              "invocation_nonce": "injected-" + selected, "wrapper_pid": 9000001, "wrapper_pgid": 9000001, "wrapper_sid": 9000001,
              "request_sha256": "0" * 64, "ack_sha256": "1" * 64, "completion_sha256": "", "ack_issued": True,
              "native_started": False, "child_pid": 0, "child_reaped": False, "released": False,
              "group_absent": False, "identity_lost": False, "permission_denied": False, "authority_closed": False,
              "identity_retained": True, "wrapper_exit_observed": False, "closure": "active", "refusal_completion_sha256": ""}
    manager.records[0] = record
    manager.authorities[0] = process_authority.Authority(custody.process_context("custodian", record))
    trace = []
    def callback(operation):
        def invoke(*_args):
            trace.append(operation)
            if operation == selected:
                raise PermissionError(errno.EPERM, "injected process-operation permission refusal")
            if operation == "os.getpgid(wrapper_pid)" or operation == "os.getsid(wrapper_pid)":
                return 9000001
            if operation == "os.getpgrp(runner)":
                return 9000002
            if operation in ["os.killpg(wrapper_pgid,SIGTERM)", "os.killpg(wrapper_pgid,SIGKILL)"]:
                raise AssertionError("injected control attempted an unselected signal")
            return None
        return invoke
    manager.process_callbacks = {name: callback(name) for name in OPERATIONS}
    return manager, record, trace


class SyntheticChild:
    pid = 9000003
    def __init__(self):
        self.calls = []
    def poll(self):
        self.calls.append("poll")
        return None
    def terminate(self):
        self.calls.append("terminate")
        raise PermissionError(errno.EPERM, "injected native terminate refusal")
    def wait(self, _timeout):
        self.calls.append("wait")
        raise AssertionError("native wait after injected permission refusal")
    def kill(self):
        self.calls.append("kill")
        raise AssertionError("alternate native kill after injected permission refusal")


def run(root, config):
    results = []
    for name, selected in [("custodian-probe-EPERM", "os.killpg(wrapper_pgid,0)"),
                           ("custodian-TERM-EPERM", "os.killpg(wrapper_pgid,SIGTERM)")]:
        manager, record, trace = model_manager(Path(root) / name, config, selected)
        try:
            if name == "custodian-probe-EPERM":
                manager.inspect(record)
            else:
                manager.drain(time.monotonic() + 0.01)
        except process_authority.OperationFailure:
            pass
        before = list(trace)
        manager.service()
        manager.inspect(record)
        manager.drain(time.monotonic() + 0.01)
        manager.finalize()
        evidence = manager.authorities[0].snapshot()
        passed = (record["permission_denied"] and record["authority_closed"] and record["identity_lost"] and
                  manager.uncertain and not manager.journal_reconciled and not record["group_absent"] and trace == before and
                  len(evidence["diagnostics"]) == 1 and evidence["diagnostics"][0]["operation"] == selected and
                  "os.killpg(wrapper_pgid,SIGKILL)" not in trace)
        results.append({"check": name, "injected": True, "processes_started": 0, "passed": bool(passed),
                        "fixture_cleanup": "synthetic-no-OS-child", "custody_state": "unresolved-refused",
                        "operations_before_refusal": before, "operations_after_refusal": trace[len(before):],
                        "process": evidence, "custody_record": [manager.snapshot()["records"][0]], "native_wait_known": False, "clean_custody": False})
    context = {"source": "wrapper", "run_nonce": config["run_nonce"], "phase": "test", "ordinal": 0,
               "recipe_id": "version", "invocation_nonce": "injected-native", "wrapper_pid": 9000001,
               "wrapper_pgid": 9000001, "wrapper_sid": 9000001, "native_pid": 9000003}
    for name in ["wrapper-getpgid-EPERM", "wrapper-terminate-EPERM"]:
        child = SyntheticChild()
        authority = process_authority.Authority(context)
        if name == "wrapper-getpgid-EPERM":
            def denied(_pid):
                raise PermissionError(errno.EPERM, "injected native group lookup refusal")
            try:
                process_authority.native_group(child, authority, denied)
            except process_authority.OperationFailure:
                pass
            before = list(child.calls)
            retired = process_authority.retire_native(child, authority, time.monotonic_ns() + 10000000)
        else:
            retired = process_authority.retire_native(child, authority, time.monotonic_ns() + 10000000)
            before = list(child.calls)
        process_authority.retire_native(child, authority, time.monotonic_ns() + 10000000)
        blocked = []
        try:
            authority.call("alternate-process-route", lambda: blocked.append(True))
        except process_authority.AuthorityRefused:
            pass
        evidence = authority.snapshot()
        expected = [] if name == "wrapper-getpgid-EPERM" else ["poll", "terminate"]
        passed = authority.permission_refused and not retired["child_reaped"] and child.calls == expected == before and not blocked and len(evidence["diagnostics"]) == 1
        results.append({"check": name, "injected": True, "processes_started": 0, "passed": bool(passed),
                        "fixture_cleanup": "synthetic-no-OS-child", "custody_state": "unresolved-refused",
                        "operations_before_refusal": before, "operations_after_refusal": child.calls[len(before):],
                        "process": evidence, "custody_record": [], "native_wait_known": False, "clean_custody": False})
    manager, record, trace = model_manager(Path(root) / "released-observe-only", config, "none")
    record.update(released=True, authority_closed=True, closure="released-observe", completion_sha256="2" * 64)
    manager.observe_wrapper_exit(record["wrapper_pid"], 0)
    manager.inspect(record)
    manager.drain(time.monotonic() + 0.01)
    manager.finalize()
    passed = (record["authority_closed"] and record["wrapper_exit_observed"] and record["closure"] == "exited-observe" and
              not record["group_absent"] and not record["permission_denied"] and manager.uncertain and not manager.journal_reconciled and
              bool(trace) and all(name == "os.killpg(wrapper_pgid,0)" for name in trace))
    results.append({"check": "released-observe-only", "injected": True, "processes_started": 0, "passed": bool(passed),
                    "fixture_cleanup": "synthetic-no-OS-child", "custody_state": "unresolved-observe",
                    "operations_before_refusal": trace, "operations_after_refusal": [], "process": manager.authorities[0].snapshot(),
                    "custody_record": [manager.snapshot()["records"][0]], "native_wait_known": False, "clean_custody": False})
    authority = process_authority.Authority({**context, "invocation_nonce": "injected-exceptional-tail"})
    child = SyntheticChild()
    retained = [child]
    def refuse():
        raise PermissionError(errno.EPERM, "injected refusal before exceptional evidence tail")
    try:
        authority.call("injected-refusal-before-tail", refuse)
    except process_authority.OperationFailure:
        pass
    exit_checks = []
    class SelectedExit(BaseException):
        def __init__(self, code):
            self.code = code
    for operation in ["child.stdout.close", "stderr.diagnostic-write"]:
        ordinary = []
        exit_codes = []
        def failed_tail(selected=operation):
            assert retained == [child] and authority.permission_refused
            raise OSError("injected exceptional tail: " + selected)
        def selected_self_exit(code):
            assert retained == [child] and authority.permission_refused
            exit_codes.append(code)
            raise SelectedExit(code)
        def ordinary_finalization():
            ordinary.append(True)
            child.poll()
        try:
            process_authority.refusal_exit_boundary(failed_tail, lambda: authority.permission_refused, selected_self_exit)
        except SelectedExit as selected:
            code = selected.code
        except BaseException:
            code = -1
            ordinary_finalization()
        else:
            code = -1
            ordinary_finalization()
        exit_checks.append({"operation": operation, "self_exit_selected": exit_codes == [125] and code == 125,
                            "exit_code": code, "ordinary_finalization_ran": bool(ordinary),
                            "process_callback_attempts": len(child.calls), "child_retained": retained == [child]})
    passed = (authority.permission_refused and retained == [child] and not child.calls and
              len(exit_checks) == 2 and all(row["self_exit_selected"] and not row["ordinary_finalization_ran"] and row["child_retained"] for row in exit_checks))
    results.append({"check": "wrapper-exceptional-tail", "injected": True, "processes_started": 0, "passed": bool(passed),
                    "fixture_cleanup": "synthetic-no-OS-child", "custody_state": "unresolved-refused",
                    "operations_before_refusal": ["injected-refusal-before-tail"], "operations_after_refusal": [],
                    "process": authority.snapshot(), "custody_record": [], "native_wait_known": False, "clean_custody": False,
                    "exit_boundary_checks": exit_checks})
    for row in results:
        row.setdefault("exit_boundary_checks", [])
    return results
