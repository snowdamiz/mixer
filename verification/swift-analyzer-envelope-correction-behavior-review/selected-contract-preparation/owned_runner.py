"""Unexecuted future runner source; no CLI and no candidate command embedded.

Qualification and use require root's exact-source admission. Artifact preparation
does not import or execute this module. Only a caller-supplied owned command is
run; this module never discovers processes, deletes scratch or infers test passes.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def _signal_group(pgid: int, sig: int) -> bool:
    try:
        os.killpg(pgid, sig)
        return True
    except ProcessLookupError:
        return False


def _group_exists(pgid: int) -> bool:
    # A targeted liveness check for the newly created owned group only.
    return _signal_group(pgid, 0)


def _wait_group_gone(pgid: int, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while _group_exists(pgid):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(0.025, remaining))
    return True


def _cleanup_owned(proc: subprocess.Popen) -> dict:
    # start_new_session guarantees this child's PID is its owned PGID.
    pgid = proc.pid
    term_sent = False
    kill_sent = False
    if _group_exists(pgid):
        term_sent = _signal_group(pgid, signal.SIGTERM)
    try:
        proc.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        kill_sent = _signal_group(pgid, signal.SIGKILL)
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            # Receipt will prevent scratch release. Do not touch another group.
            return {"owned_pgid": pgid, "term_sent": term_sent, "kill_sent": kill_sent,
                    "direct_child_reaped": False, "owned_group_gone": False,
                    "cleanup_verified": False}
    if not _wait_group_gone(pgid, 0.5):
        kill_sent = _signal_group(pgid, signal.SIGKILL) or kill_sent
    gone = _wait_group_gone(pgid, 2)
    return {"owned_pgid": pgid, "term_sent": term_sent, "kill_sent": kill_sent,
            "direct_child_reaped": proc.returncode is not None,
            "owned_group_gone": gone,
            "cleanup_verified": proc.returncode is not None and gone}


def run_owned(
    argv: list[str], *, executable: str, cwd: Path, artifacts: Path,
    timeout_seconds: float, env: dict[str, str] | None = None,
) -> dict:
    """Run one later-authorized command; return facts, never a pass verdict.

    executable and argv[0] are explicit separately so a later admitted Rustup
    dispatch method can preserve its required compiler argv0. Do not guess it.
    The caller must pin command/source/compiler identities in its own receipt.
    """
    if not argv or not Path(executable).is_absolute() or not cwd.is_absolute():
        raise ValueError("exact command, absolute executable and cwd required")
    if not 0 < timeout_seconds <= 60:
        raise ValueError("one bounded method/compile command needs a deadline <=60s")
    artifacts.mkdir(parents=True, exist_ok=False)
    stdout_path, stderr_path = artifacts / "stdout.bin", artifacts / "stderr.bin"
    start = time.monotonic()
    started_at = datetime.datetime.now(datetime.timezone.utc)
    deadline = start + timeout_seconds
    proc = None
    caught = None
    status = "launch-not-completed"
    cleanup = {"cleanup_verified": True, "reason": "no child launched"}
    with stdout_path.open("xb", buffering=0) as stdout, stderr_path.open("xb", buffering=0) as stderr:
        try:
            proc = subprocess.Popen(
                argv, executable=executable, cwd=cwd, env=env,
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                start_new_session=True, close_fds=True,
            )
            try:
                proc.wait(timeout=max(0, deadline - time.monotonic()))
                status = "completed"
            except subprocess.TimeoutExpired:
                status = "timed-out-unqualified"
        except BaseException as exc:
            caught = exc
            status = "exception-unqualified"
        finally:
            if proc is not None:
                cleanup = _cleanup_owned(proc)
            # Partial streams have always been file-backed. Flush before receipt.
            os.fsync(stdout.fileno())
            os.fsync(stderr.fileno())
    def stream(path: Path) -> dict:
        data = path.read_bytes()
        return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    receipt = {
        "schema": 1,
        "status": status,
        "argv": argv,
        "executable": executable,
        "cwd": str(cwd),
        "started_at": started_at.isoformat(),
        "absolute_deadline_utc": (started_at + datetime.timedelta(seconds=timeout_seconds)).isoformat(),
        "timeout_seconds": timeout_seconds,
        "elapsed_seconds": time.monotonic() - start,
        "returncode": None if proc is None else proc.returncode,
        "exception": None if caught is None else {"type": type(caught).__name__, "message": str(caught)},
        "stdout": stream(stdout_path),
        "stderr": stream(stderr_path),
        "cleanup": cleanup,
        "scratch_release_authorized": cleanup["cleanup_verified"],
        "test_pass_or_implementation_acceptance": False,
        "environment_values_logged": False,
        "unrelated_process_discovery": False,
    }
    receipt_path = artifacts / "receipt.json"
    with receipt_path.open("x") as output:
        json.dump(receipt, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    if not cleanup["cleanup_verified"]:
        raise RuntimeError(f"Owned child cleanup incomplete; preserve {artifacts}")
    if caught is not None:
        raise caught
    return receipt
