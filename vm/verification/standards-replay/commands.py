"""Run trusted host tools in owned process groups and record terminal custody."""

import hashlib
import json
import os
import select
import signal
import subprocess
import tempfile
import time


COMMAND_LIMIT = 348


def digest(data):
    return hashlib.sha256(data).hexdigest()


def publish_json(path, value):
    """Publish a fully written, synced JSON file without replacing a destination."""
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".replay-", mode="w",
                                         encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
            os.link(stream.name, path, follow_symlinks=False)
        os.fsync(directory)
    finally:
        os.close(directory)


def preserve(scratch, filename, evidence):
    try:
        publish_json(scratch / filename, evidence)
    except BaseException as error:
        os.write(2, f"Could not persist {filename}: {error}\n".encode())
    finally:
        os.write(2, f"Preserve replay scratch {scratch}\n".encode())


class OwnedChild(subprocess.Popen):
    def __del__(self):
        # The supervisor owns every reap. Never observe again after a hold.
        pass


class Commands:
    def __init__(self, scratch, env):
        self.scratch = scratch
        self.env = env
        self.rows = []
        self.deadline = time.monotonic() + 240
        self.cancel_signal = None

    def interrupt(self, signum, _frame):
        # Signal handlers must not unwind launch, timeout settlement, or publication.
        self.cancel_signal = signum

    def check_interrupt(self):
        if self.cancel_signal is not None:
            raise InterruptedError(f"signal {self.cancel_signal}")

    def hold(self, row, error, raw):
        row.setdefault("custody", "unknown")
        row.update(error=str(error), output_sha256=digest(raw), output_bytes=len(raw))
        try:
            try:
                (self.scratch / f"{row['name']}.log").write_bytes(raw)
            except OSError as log_error:
                row["log_error"] = str(log_error)
            finally:
                preserve(self.scratch, "HOLD.json", {
                    "scratch": str(self.scratch), "command": row, "prior_commands": self.rows,
                })
        finally:
            os._exit(74)

    def run(self, name, argv, *, cwd=None, timeout=30, expected=0, maximum=512 * 1024):
        self.check_interrupt()
        if len(self.rows) >= COMMAND_LIMIT or time.monotonic() >= self.deadline:
            raise RuntimeError("command count or campaign deadline exceeded")
        cwd = cwd or self.scratch
        argv = list(map(str, argv))
        start = time.monotonic()
        deadline = min(start + timeout, self.deadline)
        row = {
            "name": name, "argv": argv, "cwd": str(cwd), "expected_exit_code": expected,
            "timeout_seconds": timeout, "output_cap_bytes": maximum,
        }
        output = bytearray()
        problem = None
        try:
            child = OwnedChild(
                argv, cwd=cwd, env=self.env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, start_new_session=True,
            )
            row.update(pid=child.pid, pgid=child.pid)
            try:
                while True:
                    self.check_interrupt()
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired(argv, timeout)
                    if not select.select([child.stdout], [], [], min(remaining, 0.2))[0]:
                        continue
                    data = os.read(child.stdout.fileno(), min(65536, maximum + 1 - len(output)))
                    if not data:
                        row["output_eof"] = True
                        break
                    output.extend(data)
                    if len(output) > maximum:
                        problem = "output limit exceeded"
                        break
                while not problem:
                    self.check_interrupt()
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired(argv, timeout)
                    try:
                        child.wait(timeout=min(remaining, 0.2))
                        break
                    except subprocess.TimeoutExpired:
                        continue
            except subprocess.TimeoutExpired:
                problem = "deadline exceeded"
            except InterruptedError as error:
                problem = str(error)

            if problem:
                # Keep the group leader unreaped until after signalling its owned group.
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
                raise RuntimeError("group still present after direct child reap")

            raw = bytes(output[:maximum])
            row.update(output_sha256=digest(raw), output_bytes=len(raw),
                       elapsed_seconds=round(time.monotonic() - start, 6))
            (self.scratch / f"{name}.log").write_bytes(raw)
        except BaseException as error:
            if problem:
                row["problem"] = problem
            self.hold(row, error, bytes(output[:maximum]))

        self.rows.append(row)
        self.check_interrupt()
        if problem or child.returncode != expected:
            raise RuntimeError(
                f"{name}: {problem or f'exit {child.returncode}, expected {expected}'}\n"
                f"{raw[-2000:].decode(errors='replace')}"
            )
        return raw
