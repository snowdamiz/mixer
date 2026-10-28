"""Retained direct-child cleanup; starts no process on import."""
import errno
import os
import signal
import time
import traceback


class RetainedChild:
    def __init__(self, child):
        self.child = child
        self.pid = child.pid
        self.pgid = child.pid
        self.sid = child.pid
        self.identity_retained = False
        self.identity_lost = False
        self.permission_denied = False
        self.completed = False
        self.group_gone = False
        self.uncertain = False
        self.mode = "unproven-observe"
        self.signals = []
        self.diagnostics = []
        if self.poll() is None:
            self.live_leader(retaining=True)

    def error(self, call, exc):
        self.uncertain = True
        number = exc.errno if isinstance(exc, OSError) and type(exc.errno) is int else 0
        if number == errno.EPERM:
            # A permission failure is terminal for active cleanup authority.
            # Never retry it through another signal/API or a saved numeric PGID.
            self.permission_denied = True
            self.identity_lost = True
        if len(self.diagnostics) < 32:
            self.diagnostics.append({"call": call, "errno": number, "errno_name": errno.errorcode.get(number, ""),
                "strerror": str(exc.strerror or "") if isinstance(exc, OSError) else "",
                "exception_type": type(exc).__name__, "message": str(exc),
                "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
                "pid": self.pid, "pgid": self.pgid, "sid": self.sid, "at_ns": time.monotonic_ns()})

    def poll(self):
        if self.completed or self.child.returncode is not None:
            self.completed = True
            return self.child.returncode
        if self.permission_denied:
            return None
        try:
            code = self.child.poll()
            if code is not None:
                # Sticky: wait/poll completion permanently forbids active signals.
                self.completed = True
            return code
        except BaseException as exc:
            self.error("subprocess.Popen.poll (waitpid)", exc)
            self.identity_lost = True
            return None

    def live_leader(self, retaining=False):
        if self.completed or self.identity_lost or self.permission_denied or self.group_gone:
            return False
        if self.poll() is not None:
            return False
        if not retaining and not self.identity_retained:
            return False
        try:
            pgid = os.getpgid(self.pid)
        except BaseException as exc:
            self.error("os.getpgid(pid)", exc)
            self.identity_lost = True
            self.poll()
            return False
        try:
            sid = os.getsid(self.pid)
        except BaseException as exc:
            self.error("os.getsid(pid)", exc)
            self.identity_lost = True
            self.poll()
            return False
        if self.pid <= 1 or pgid != self.pgid or sid != self.sid or pgid == os.getpgrp():
            self.identity_lost = True
            self.error("owned PID/PGID/SID comparison", RuntimeError("retained exclusive session leader identity differs"))
            return False
        if self.poll() is not None:
            return False
        self.identity_retained = True
        return True

    def group_absent(self):
        if self.group_gone:
            return True
        if self.permission_denied:
            return False
        try:
            os.killpg(self.pgid, 0)
            return False
        except ProcessLookupError:
            self.group_gone = True
            return True
        except BaseException as exc:
            self.error("os.killpg(pgid, 0)", exc)
            return False

    def service(self, callback):
        try:
            callback()
        except BaseException as exc:
            self.error("owned cleanup service callback", exc)

    def cleanup(self, deadline, callback=lambda: None):
        self.poll()
        if self.completed:
            self.mode = "completed-observe"
        elif self.identity_retained and not self.identity_lost and not self.permission_denied:
            self.mode = "running-retirement"
            for number in [signal.SIGTERM, signal.SIGKILL]:
                if time.monotonic() >= deadline or self.completed or self.permission_denied:
                    break
                if self.group_absent() or not self.live_leader():
                    break
                try:
                    # Both the retained direct child and current PID/PGID/SID
                    # were rechecked. There is no fallback kill by PID/API.
                    os.killpg(self.pgid, number)
                    self.signals.append(int(number))
                except BaseException as exc:
                    self.error("os.killpg(pgid, " + signal.Signals(number).name + ")", exc)
                    break
                until = min(deadline, time.monotonic() + 0.4)
                while time.monotonic() < until and not self.completed and not self.permission_denied:
                    self.service(callback)
                    self.poll()
                    if self.group_absent():
                        break
                    time.sleep(0.005)
                # Once completion is observed, escalation is forbidden even if
                # the saved numeric group still exists.
                if self.completed or self.permission_denied:
                    break
        while time.monotonic() < deadline and not self.permission_denied:
            self.service(callback)
            self.poll()
            absent = self.group_absent()
            if self.completed and absent:
                break
            time.sleep(0.005)
        if not self.completed or not self.group_gone:
            self.error("owned cleanup terminal observation", RuntimeError("direct child wait or group absence unresolved; no numeric-group retry"))
        if self.child.stdout is not None:
            try:
                self.child.stdout.close()
            except BaseException as exc:
                self.error("child.stdout.close", exc)
        return self.snapshot()

    def snapshot(self):
        return {"pid": self.pid, "pgid": self.pgid, "sid": self.sid,
            "identity_retained": self.identity_retained, "identity_lost": self.identity_lost,
            "permission_denied": self.permission_denied, "completed_observed": self.completed,
            "direct_child_reaped": self.completed, "group_absent": self.group_gone,
            "uncertain": self.uncertain, "mode": self.mode, "signals": self.signals,
            "returncode_known": self.completed, "returncode": self.child.returncode if self.completed else 0,
            "diagnostics": self.diagnostics}
