"""Call-tagged process permission refusal. Import starts no process."""
import errno
import os
import signal
import subprocess
import time
import traceback

MISSING = object()


def diagnostic(context, operation, exc, permission_refused=False):
    number = exc.errno if isinstance(exc, OSError) and type(exc.errno) is int else 0
    return {**context, "operation": operation, "errno": number, "errno_name": errno.errorcode.get(number, ""),
            "strerror": str(exc.strerror or "") if isinstance(exc, OSError) else "",
            "exception_type": type(exc).__name__, "message": str(exc),
            "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            "at_ns": time.monotonic_ns(), "permission_refused": permission_refused}


class OperationFailure(RuntimeError):
    def __init__(self, diagnostic):
        self.diagnostic = diagnostic
        super().__init__(diagnostic["operation"] + ": " + diagnostic["exception_type"] + ": " + diagnostic["message"])


class AuthorityRefused(RuntimeError):
    pass


class Authority:
    def __init__(self, context):
        self.context = dict(context)
        self.permission_refused = False
        self.operations = {}
        self.diagnostics = []

    def call(self, operation, function, *args, missing_ok=False):
        if self.permission_refused:
            raise AuthorityRefused("process authority permanently refused; operation not attempted: " + operation)
        if operation not in self.operations and len(self.operations) >= 16:
            raise RuntimeError("finite process operation identity cap")
        self.operations[operation] = self.operations.get(operation, 0) + 1
        try:
            return function(*args)
        except BaseException as exc:
            if isinstance(exc, ProcessLookupError) and missing_ok:
                return MISSING
            number = exc.errno if isinstance(exc, OSError) and type(exc.errno) is int else 0
            if isinstance(exc, PermissionError) or number in [errno.EPERM, errno.EACCES]:
                self.permission_refused = True
            observation = diagnostic(self.context, operation, exc, self.permission_refused)
            if len(self.diagnostics) < 8:
                self.diagnostics.append(observation)
            raise OperationFailure(observation) from exc

    def snapshot(self):
        return {"permission_refused": self.permission_refused,
                "operations": [{"operation": name, "attempts": count} for name, count in self.operations.items()],
                "diagnostics": list(self.diagnostics)}


def native_group(child, authority, reader=os.getpgid):
    return authority.call("os.getpgid(native_pid)", reader, child.pid, missing_ok=True)


def retire_native(child, authority, cleanup_deadline_ns):
    """No process operation, including poll/wait, follows permission refusal."""
    result = {"child_reaped": False, "exit_code": 125, "errors": []}
    if authority.permission_refused:
        result["errors"].append("native cleanup authority refused; wait remains unresolved")
        return result
    try:
        code = authority.call("Popen.poll(native_pid)", child.poll)
        if code is not None:
            result.update(child_reaped=True, exit_code=code)
            return result
        authority.call("Popen.terminate(native_pid)", child.terminate)
        try:
            code = authority.call("Popen.wait(native_pid,0.2)", child.wait, 0.2)
        except OperationFailure as exc:
            # Timeout is not a permission failure and does not prove completion.
            if exc.diagnostic["exception_type"] != "TimeoutExpired":
                raise
            if authority.permission_refused:
                raise AuthorityRefused("process authority refused before escalation")
            code = authority.call("Popen.poll(native_pid)", child.poll)
            if code is None:
                authority.call("Popen.kill(native_pid)", child.kill)
                code = authority.call("Popen.wait(native_pid,cleanup)", child.wait,
                                      max(0.001, (cleanup_deadline_ns - time.monotonic_ns()) / 1e9))
        result.update(child_reaped=True, exit_code=code)
    except BaseException as exc:
        result["errors"].append("retire-native: " + type(exc).__name__ + ": " + str(exc))
    return result


def refusal_exit_boundary(run_main, is_refused, self_exit):
    """Final boundary: no evidence/diagnostic I/O can precede refused self-exit."""
    result = 125
    try:
        candidate = run_main()
        if type(candidate) is not int:
            raise RuntimeError("wrapper result unavailable; failure exit remains selected")
        result = candidate
        return result
    finally:
        if is_refused():
            self_exit(result)
            raise RuntimeError("nonreturning self-exit callback unexpectedly returned")
