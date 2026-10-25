"""Standalone owned-command diagnostics. No native operation occurs on import.

This module does not select commands, interpret XCTest results, or grant acceptance.
Callers supply the exact argv/cwd/environment and an explicitly owned result root.
"""
from __future__ import annotations

import codecs
import hashlib
import io
import json
import locale
import math
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import sys
import time


SCHEMA = "mixer.apple-command-finalization-observer.1"
MAX_COMMAND_SECONDS = 600
CLEANUP_GRACE_SECONDS = 8
MAX_OUTPUT_BYTES = 32 * 1024 * 1024
_READ_BYTES = 65536


class OutputLimitExceeded(RuntimeError):
    """The command failed closed before returning truncated output."""


def _utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _positive(value, maximum, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + " must be a finite positive number")
    if not math.isfinite(value) or not 0 < value <= maximum:
        raise ValueError(label + " is outside its bounded range")


def _canonical_directory(value, label):
    path = Path(value)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError(label + " must be an absolute canonical path")
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError(label + " must be a directory owned by the current user")
    return path


def _kind(info):
    if stat.S_ISLNK(info.st_mode):
        return "symlink"
    if stat.S_ISREG(info.st_mode):
        return "file"
    if stat.S_ISDIR(info.st_mode):
        return "directory"
    return "special"


def _entry(directory_fd, name):
    try:
        info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return {"exists": False}
    return {"exists": True, "kind": _kind(info), "bytes": info.st_size,
            "mtimeNS": info.st_mtime_ns, "device": info.st_dev, "inode": info.st_ino}


class _ResultMarkers:
    """Only the explicit direct-child bundle and its Info.plist are inspected."""
    def __init__(self, root, bundle):
        self.root = _canonical_directory(root, "owned_result_root")
        self.bundle = Path(bundle)
        if (not self.bundle.is_absolute() or self.bundle.parent != self.root
                or self.bundle.name in ("", ".", "..")
                or self.bundle.suffix != ".xcresult"):
            raise ValueError("result_bundle must be a direct .xcresult child of owned_result_root")
        self.fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)

    def snapshot(self):
        bundle = _entry(self.fd, self.bundle.name)
        result = {"bundle": bundle, "Info.plist": {"exists": False},
                  "markerMeaning": "presence-only; never an official result or test verdict"}
        if not bundle["exists"] or bundle["kind"] != "directory":
            return result
        # O_NOFOLLOW prevents a bundle replaced by a symlink between stat and open.
        descriptor = os.open(self.bundle.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                             dir_fd=self.fd)
        try:
            current = os.fstat(descriptor)
            if (current.st_dev, current.st_ino) != (bundle["device"], bundle["inode"]):
                raise RuntimeError("Owned result bundle identity changed during observation")
            result["Info.plist"] = _entry(descriptor, "Info.plist")
        finally:
            os.close(descriptor)
        return result

    def close(self):
        os.close(self.fd)


class _Stream:
    def __init__(self, name, pipe, output, encoding, limit):
        self.name, self.pipe, self.limit = name, pipe, limit
        self.log = (output / (name + ".log")).open("xb", buffering=0)
        self.decoder = io.IncrementalNewlineDecoder(codecs.getincrementaldecoder(encoding)("strict"), True)
        self.text_buffer = io.StringIO()
        self.hash = hashlib.sha256()
        self.observed = self.retained = 0
        self.first_data = self.last_data = self.eof_at = None
        self.eof = self.failed = False
        self.line_tail = ""
        self.suite = None
        self.errors = []

    def state(self):
        return {"observedBytes": self.observed, "retainedBytes": self.retained,
                "retainedSHA256": self.hash.hexdigest(), "firstDataSeconds": self.first_data,
                "lastDataSeconds": self.last_data, "eof": self.eof,
                "eofSeconds": self.eof_at, "readerFailed": self.failed,
                "readerErrors": self.errors}

    def text(self):
        return self.text_buffer.getvalue()

    def _decoded(self, raw, final=False):
        decoded = self.decoder.decode(raw, final=final)
        self.text_buffer.write(decoded)
        lines = (self.line_tail + decoded).split("\n")
        self.line_tail = lines.pop()[-4096:]
        if final and self.line_tail:
            lines.append(self.line_tail)
        for line in lines:
            for disposition in ("passed", "failed"):
                prefix = "Test Suite 'Selected tests' " + disposition + " at "
                if line.startswith(prefix) and line.endswith(".") and self.suite is None:
                    # Diagnostic text recognition has no influence on command acceptance.
                    self.suite = {"line": line[:4096], "dispositionText": disposition}

    def read_once(self, now, selector, *, cleanup=False):
        try:
            raw = os.read(self.pipe.fileno(), _READ_BYTES)
            if not raw:
                self.eof, self.eof_at = True, now
                selector.unregister(self.pipe)
                if not self.failed:
                    self._decoded(b"", final=True)
                return
            self.observed += len(raw)
            self.first_data = now if self.first_data is None else self.first_data
            self.last_data = now
            retained = raw[:max(0, self.limit - self.retained)]
            pending = memoryview(retained)
            while pending:
                written = self.log.write(pending)
                if not written:
                    raise OSError("Raw log write made no progress")
                self.hash.update(pending[:written])
                self.retained += written
                pending = pending[written:]
            if self.observed > self.limit:
                raise OutputLimitExceeded(self.name + " exceeded " + str(self.limit) + " bytes")
            if not self.failed:
                self._decoded(raw)
        except BlockingIOError:
            return
        except BaseException as failure:
            self.failed = True
            if not self.errors:
                self.errors.append({"type": type(failure).__name__, "message": str(failure)[:1024],
                                    "elapsedSeconds": now})
            if not cleanup:
                raise

    def close(self):
        self.pipe.close()
        self.log.close()


def observe_command(argv, *, cwd, env, output_dir, owned_result_root, result_bundle,
                    timeout=600, check=True, poll_interval=0.25, post_suite_grace=10,
                    max_output_bytes_per_stream=MAX_OUTPUT_BYTES, encoding=None):
    """Run the exact supplied command, recording diagnostics without accepting tests.

    Return the Commands.run-compatible (code, stdout.strip(), stderr.strip()) tuple.
    `check=True` raises AssertionError for nonzero exit. TimeoutExpired, decoding,
    observer, and output-limit failures propagate after bounded owned-group cleanup.
    No subprocess is used for observation. Environment values are never recorded.
    """
    argv = [str(value) for value in argv]
    if not argv or any("\x00" in value for value in argv):
        raise ValueError("argv must be nonempty and contain no NUL")
    _positive(timeout, MAX_COMMAND_SECONDS, "timeout")
    _positive(poll_interval, 1, "poll_interval")
    if poll_interval < 0.01:
        raise ValueError("poll_interval must be at least 0.01 seconds")
    _positive(post_suite_grace, MAX_COMMAND_SECONDS, "post_suite_grace")
    if (isinstance(max_output_bytes_per_stream, bool)
            or not isinstance(max_output_bytes_per_stream, int)
            or not 0 < max_output_bytes_per_stream <= MAX_OUTPUT_BYTES):
        raise ValueError("max_output_bytes_per_stream must be in [1, 33554432]")
    cwd = _canonical_directory(cwd, "cwd")
    output = Path(output_dir)
    parent = _canonical_directory(output.parent, "output_dir parent")
    if not output.is_absolute() or output.parent != parent or output.name in ("", ".", ".."):
        raise ValueError("output_dir must be an absent direct child of a canonical directory")
    encoding = encoding or ("utf-8" if sys.flags.utf8_mode else locale.getencoding())
    codecs.lookup(encoding)
    markers = _ResultMarkers(owned_result_root, result_bundle)
    try:
        if markers.snapshot()["bundle"]["exists"]:
            raise ValueError("owned result bundle must be absent before command launch")
        output.mkdir(mode=0o700, exist_ok=False)
    except BaseException:
        markers.close()
        raise
    timeline = (output / "timeline.jsonl").open("x", encoding="utf-8")
    selector = selectors.DefaultSelector()
    started = time.monotonic()
    command_deadline = started + timeout
    events = 0
    process = None
    streams = {}
    suite_at = post_suite = child_exit_at = None
    next_sample = started
    cleanup = {"attempted": False, "complete": None, "targetPID": None, "targetProcessGroup": None,
               "graceSecondsPerSignal": CLEANUP_GRACE_SECONDS, "signals": []}
    summary = {"schema": SCHEMA, "argv": argv, "cwd": str(cwd), "environmentRecorded": False,
               "environmentMode": "inherited" if env is None else "exact-supplied-mapping",
               "outputDir": str(output), "resultBundle": str(markers.bundle),
               "ownedResultRoot": str(markers.root), "timeoutSeconds": timeout,
               "pollIntervalSeconds": poll_interval, "postSuiteGraceSeconds": post_suite_grace,
               "maxOutputBytesPerStream": max_output_bytes_per_stream,
               "encoding": encoding, "newlineMode": "universal-newlines",
               "captureMode": "single-reader-PIPE; bounded raw-byte logs",
               "startNewSession": True, "startedUTC": _utc(), "PID": None,
               "processGroup": None, "successInferredFromConsoleOrMarkers": False,
               "nativeAcceptanceGranted": False, "cleanup": cleanup, "outcome": None}

    def record(kind, **values):
        nonlocal events
        event = {"kind": kind, "utc": _utc(), "elapsedSeconds": time.monotonic() - started, **values}
        timeline.write(json.dumps(event, sort_keys=True) + "\n")
        timeline.flush()
        events += 1

    def cleanup_record(kind, **values):
        try:
            record(kind, **values)
        except BaseException as write_failure:
            summary.setdefault("diagnosticWriteErrors", []).append({
                "type": type(write_failure).__name__, "message": str(write_failure)[:1024]})

    def owned_group_state():
        if process is None:
            return {"state": "not-started"}
        observed = {"targetProcessGroup": process.pid,
                    "elapsedSeconds": time.monotonic() - started,
                    "method": "signal-0-to-recorded-owned-PGID-only"}
        try:
            os.killpg(process.pid, 0)
            observed["state"] = "present-or-zombies"
        except ProcessLookupError:
            observed["state"] = "absent"
        except OSError as probe_failure:
            observed.update(state="unknown", failureType=type(probe_failure).__name__,
                            message=str(probe_failure)[:1024])
        return observed

    def state():
        return {"mainProcessExitCode": None if process is None else process.returncode,
                "mainProcessExitObservedSeconds": child_exit_at,
                "ownedProcessGroup": owned_group_state(),
                "streams": {name: value.state() for name, value in streams.items()},
                "resultMarkers": markers.snapshot()}

    def read_ready(wait, cleanup_mode=False):
        for key, _ in selector.select(wait):
            stream = key.data
            was_eof = stream.eof
            stream.read_once(time.monotonic() - started, selector, cleanup=cleanup_mode)
            if stream.eof and not was_eof:
                (cleanup_record if cleanup_mode else record)("stream-eof", stream=stream.name,
                                                            **stream.state())

    def observe_exit(cleanup_mode=False):
        nonlocal child_exit_at
        if process is not None and process.poll() is not None and child_exit_at is None:
            child_exit_at = time.monotonic() - started
            (cleanup_record if cleanup_mode else record)("main-process-exit", exitCode=process.returncode,
                streams={name: value.state() for name, value in streams.items()})

    def wait_for_cleanup(seconds):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            observe_exit(True)
            group = owned_group_state()
            cleanup["lastGroupObservation"] = group
            if (process.returncode is not None and all(value.eof for value in streams.values())
                    and group["state"] == "absent"):
                return True
            read_ready(min(poll_interval, max(0, until - time.monotonic())), True)
        observe_exit(True)
        group = owned_group_state()
        cleanup["lastGroupObservation"] = group
        return (process.returncode is not None and all(value.eof for value in streams.values())
                and group["state"] == "absent")

    def cleanup_owned_group():
        if process is None:
            return
        cleanup.update(attempted=True, targetPID=process.pid, targetProcessGroup=process.pid)
        for sig in (signal.SIGTERM, signal.SIGKILL):
            sent = {"signal": sig.name, "elapsedSeconds": time.monotonic() - started}
            try:
                os.killpg(process.pid, sig)
                sent["status"] = "sent-to-owned-process-group"
            except ProcessLookupError:
                sent["status"] = "owned-process-group-absent"
            except OSError as failure:
                sent.update(status="signal-failed", failureType=type(failure).__name__, message=str(failure))
            cleanup["signals"].append(sent)
            cleanup_record("cleanup-signal", **sent)
            try:
                if wait_for_cleanup(CLEANUP_GRACE_SECONDS):
                    cleanup["complete"] = True
                    return
            except BaseException as wait_failure:
                cleanup.setdefault("waitErrors", []).append({
                    "type": type(wait_failure).__name__, "message": str(wait_failure)[:1024]})
        cleanup["complete"] = False

    failure = None
    try:
        # Binary pipes have exactly one reader. Explicit incremental decoding below
        # retains Popen(text=True)'s strict decoding and newline normalization.
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        summary.update(PID=process.pid, processGroup=process.pid,
                       processGroupSource="start_new_session=True; PGID equals owned child PID")
        record("command-started", PID=process.pid, processGroup=process.pid)
        for name in ("stdout", "stderr"):
            value = _Stream(name, getattr(process, name), output, encoding, max_output_bytes_per_stream)
            streams[name] = value
            os.set_blocking(value.pipe.fileno(), False)
            selector.register(value.pipe, selectors.EVENT_READ, value)
        while True:
            observe_exit()
            now = time.monotonic()
            if suite_at is None:
                for name, value in streams.items():
                    if value.suite is not None:
                        suite_at = now - started
                        record("selected-suite-console-line", stream=name, **value.suite,
                               meaning="diagnostic-only; command still requires exit and both EOFs")
                        break
            if now >= command_deadline:
                raise subprocess.TimeoutExpired(argv, timeout,
                    output=(output / "stdout.log").read_bytes(),
                    stderr=(output / "stderr.log").read_bytes())
            if process.returncode is not None and all(value.eof for value in streams.values()):
                break
            if suite_at is not None and post_suite is None and now - started >= suite_at + post_suite_grace:
                post_suite = {"observedSeconds": now - started, **state()}
                record("post-suite-grace-capture", **post_suite)
            if now >= next_sample:
                record("sample", **state())
                next_sample = now + poll_interval
            wake = min(command_deadline, next_sample)
            if suite_at is not None and post_suite is None:
                wake = min(wake, started + suite_at + post_suite_grace)
            read_ready(max(0, wake - time.monotonic()))
        summary["outcome"] = "command-exited-and-streams-EOF"
        if check and process.returncode != 0:
            raise AssertionError("Command failed: " + repr(argv))
    except BaseException as caught:
        failure = caught
        summary["outcome"] = "command-failed"
        summary["failure"] = {"type": type(caught).__name__, "message": str(caught)[:4096]}
        try:
            # A nonzero completed command needs no signal. Inherited open pipes do:
            # the owned group may remain live after its leader has exited.
            if process is not None and (process.poll() is None
                    or any(not value.eof for value in streams.values())
                    or owned_group_state()["state"] != "absent"):
                cleanup_owned_group()
        except BaseException as cleanup_failure:
            cleanup.update(complete=False, failureType=type(cleanup_failure).__name__,
                           message=str(cleanup_failure)[:4096])
    finally:
        try:
            observe_exit()
            summary.update(elapsedSeconds=time.monotonic() - started, endedUTC=_utc(),
                           exitCode=None if process is None else process.returncode,
                           mainProcessExitObservedSeconds=child_exit_at,
                           selectedSuiteObservedSeconds=suite_at,
                           postSuiteCapture=post_suite,
                           streams={name: value.state() for name, value in streams.items()},
                           ownedProcessGroup=owned_group_state(),
                           resultMarkers=markers.snapshot())
            record("command-finalized", outcome=summary["outcome"], exitCode=summary["exitCode"])
        except BaseException as finalization_failure:
            summary["observerFinalizationFailure"] = {"type": type(finalization_failure).__name__,
                                                      "message": str(finalization_failure)[:4096]}
            if failure is None:
                failure = finalization_failure
                summary["outcome"] = "observer-failed"
        finally:
            summary["timelineEvents"] = events
            for value in streams.values():
                value.close()
            if process is not None:
                for name in ("stdout", "stderr"):
                    pipe = getattr(process, name)
                    if pipe is not None and not pipe.closed:
                        pipe.close()
            selector.close()
            timeline.close()
            markers.close()
            try:
                (output / "observer.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            except BaseException as write_failure:
                if failure is None:
                    failure = write_failure
                else:
                    failure.add_note("Observer receipt write failed: " + repr(write_failure))
    if failure is not None:
        raise failure
    return process.returncode, streams["stdout"].text().strip(), streams["stderr"].text().strip()
