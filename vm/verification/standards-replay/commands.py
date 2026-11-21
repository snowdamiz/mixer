"""Run trusted host tools in owned process groups and record terminal custody."""

import hashlib
import json
import os
import select
import signal
import subprocess
import time


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class OwnedChild(subprocess.Popen):
    def __del__(self):
        # The supervisor owns every reap. Never observe again after a hold.
        pass


class Commands:
    def __init__(self, scratch, cwd, env):
        self.scratch = scratch
        self.cwd = cwd
        self.env = env
        self.rows = []
        self.deadline = time.monotonic() + 240

    def hold(self, row, error):
        row.update(custody="unknown", error=str(error))
        try:
            write_json(self.scratch / "HOLD.json", {
                "scratch": str(self.scratch),
                "command": row,
                "prior_commands": self.rows,
            })
        finally:
            try:
                os.write(2, f"Unknown process custody. Preserve {self.scratch}\n".encode())
            finally:
                os._exit(74)

    def run(self, name, argv, *, timeout=30, expected=0, maximum=512 * 1024):
        if len(self.rows) >= 256 or time.monotonic() >= self.deadline:
            raise RuntimeError("command count or campaign deadline exceeded")
        argv = list(map(str, argv))
        start = time.monotonic()
        deadline = min(start + timeout, self.deadline)
        row = {
            "name": name, "argv": argv, "expected_exit_code": expected,
            "timeout_seconds": timeout, "output_cap_bytes": maximum,
        }
        output = bytearray()
        problem = None
        try:
            child = OwnedChild(
                argv, cwd=self.cwd, env=self.env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, start_new_session=True,
            )
            row.update(pid=child.pid, pgid=child.pid)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([child.stdout], [], [], remaining)[0]:
                    raise subprocess.TimeoutExpired(argv, timeout)
                data = os.read(child.stdout.fileno(), min(65536, maximum + 1 - len(output)))
                if not data:
                    row["output_eof"] = True
                    break
                output.extend(data)
                if len(output) > maximum:
                    problem = "output limit exceeded"
                    break
            if not problem:
                child.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            problem = "deadline exceeded"
        except BaseException as error:
            self.hold(row, error)

        try:
            if problem and child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait(timeout=3)
            row["exit_code"] = child.returncode
            child.stdout.close()
            try:
                os.killpg(child.pid, 0)
            except ProcessLookupError:
                row["custody"] = "child reaped and group absent"
            else:
                self.hold(row, "group still present after direct child reap")
        except BaseException as error:
            self.hold(row, error)

        raw = bytes(output[:maximum])
        row.update(output_sha256=digest(raw), output_bytes=len(raw),
                   elapsed_seconds=round(time.monotonic() - start, 6))
        self.rows.append(row)
        write_json(self.scratch / "commands.json", self.rows)
        (self.scratch / f"{name}.log").write_bytes(raw)
        if problem or child.returncode != expected:
            raise RuntimeError(
                f"{name}: {problem or f'exit {child.returncode}, expected {expected}'}\n"
                f"{raw[-2000:].decode(errors='replace')}"
            )
        return raw
