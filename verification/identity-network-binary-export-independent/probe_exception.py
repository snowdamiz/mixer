#!/usr/bin/env python3
"""In-process fake of inherited post-EOF wait exception; never launches a child."""
import importlib.util
import json
from pathlib import Path
import signal
import sys
import tempfile
from types import SimpleNamespace
from unittest import mock

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("binary_export_independent_review", BASE / "review.py")
review = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = review
spec.loader.exec_module(review)
c = review.subject

class Pipe:
    def __init__(self, fd):
        self.fd, self.closed = fd, False
    def fileno(self):
        return self.fd
    def close(self):
        self.closed = True

class Process:
    def __init__(self):
        self.stdout, self.stderr, self.stdin = Pipe(9001), Pipe(9002), None
        self.returncode, self.terminated, self.waits = None, False, 0
    def wait(self, timeout):
        self.waits += 1
        if self.waits == 1:
            raise c.subprocess.TimeoutExpired("inert-post-EOF-process", timeout)
        self.returncode = -15
        return -15
    def poll(self):
        return self.returncode
    def terminate(self):
        self.terminated = True
    def kill(self):
        raise AssertionError("unneeded inert kill")

class Selector:
    def __init__(self):
        self.entries = {}
    def __enter__(self):
        return self
    def __exit__(self, *unused):
        pass
    def register(self, pipe, event, kind):
        self.entries[pipe.fd] = SimpleNamespace(fileobj=pipe, data=kind)
    def unregister(self, pipe):
        del self.entries[pipe.fd]
    def get_map(self):
        return self.entries
    def select(self, timeout):
        return [(entry, 0) for entry in list(self.entries.values())]

def main():
    signal.alarm(15)
    payload = b"\x00\x80\xffinert-buffered-output"
    reads = {9001: [payload, b""], 9002: [b""]}
    process = Process()
    with tempfile.TemporaryDirectory(dir=review.SCRATCH, prefix="exception-") as directory:
        root = Path(directory) / "root"
        root.mkdir()
        with mock.patch.dict("os.environ", {"GITHUB_RUN_ID": "92001", "GITHUB_RUN_ATTEMPT": "1"}):
            collector = c.Collector(root, Path(directory) / "out", "a" * 40)
        collector.execute = lambda owned, argv, timeout, **options: collector.command(argv, timeout, **options)
        with mock.patch.object(c.subprocess, "Popen", return_value=process) as popen, mock.patch.object(c.selectors, "DefaultSelector", Selector), mock.patch.object(c.os, "set_blocking"), mock.patch.object(c.os, "read", side_effect=lambda fd, size: reads[fd].pop(0)):
            try:
                collector.copy_file_out(SimpleNamespace(cid="c" * 64, role="prepare"), "/workspace/downloads/hex.ez", 4096)
            except c.subprocess.TimeoutExpired:
                failed = True
            else:
                raise AssertionError("must fail on post-EOF wait timeout")
        row = json.loads((collector.output / "logs/0001.json").read_bytes())
        assert row["stdout_complete"] is False and row["stderr_complete"] is False
        assert process.terminated and process.waits == 2 and popen.call_count == 1
        assert not (collector.output / "bootstrap-exports/hex-actual.bin").exists()
        assert not (collector.output / "bootstrap-exports/hex-actual.json").exists()
        result = {"schema": 1, "probe": "inherited post-EOF process.wait TimeoutExpired before binary_path persistence", "inert_buffered_bytes": len(payload), "actual_external_processes_started": 0, "actual_os_descriptors_accessed": 0, "command_failed": failed, "stdout_complete": row["stdout_complete"], "stderr_complete": row["stderr_complete"], "capture_present": False, "capture_receipt_present": False, "false_success": False, "qualification": "nonblocking residual of unchanged command exception behavior; no claim that every transport exception retains bytes; selected completed-export host-size/hash rejection does retain bytes"}
    review.SCRATCH.rmdir()
    result["owned_scratch_cleaned"] = True
    review.dump(BASE / "exception-probe.json", result)
    print(json.dumps(result, sort_keys=True))

if __name__ == "__main__":
    try:
        main()
    finally:
        review.guards.close()
