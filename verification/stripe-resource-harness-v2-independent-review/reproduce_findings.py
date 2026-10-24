#!/usr/bin/env python3
"""Host-only reproductions of v2 review findings; all Linux state is mocked.

This imports the sealed Python control source. It does not compile C/NIF/BEAM,
open a socket, send a signal, inspect live /proc, or launch a runtime process.
"""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / "verification/stripe-webhook-linux-resource-harness/v2"
sys.dont_write_bytecode = True
sys.path.insert(0, str(V2))
import run as candidate
import linux_backend as backend

base = candidate.base


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identical_nif_source_binding():
    """The inherited v1 source check is consistent for this sealed version."""
    v1_sha = sha(base.HERE / "control_nif.c")
    v2_sha = sha(V2 / "control_nif.c")
    assert v1_sha == v2_sha
    return {"finding": False, "sourceSha256": v2_sha,
            "v1AndV2NifSourcesByteIdentical": True,
            "interpretation": "inherited source binding is consistent; initial reviewer premise withdrawn"}


def next_row_after_incomplete_cleanup():
    """Exercise main's actual row scheduling with all authority/writes mocked."""
    args = argparse.Namespace(profile=Path("/model/profile"), delegated_cgroup=Path("/model/cgroup"),
                              release=Path("/model/release"), review=Path("/model/review"),
                              execute=True, output=Path("/model/output"))
    calls = []
    def receipt(case, *_args, **_kwargs):
        return {"caseId": case, "status": "unavailable", "cleanup": {"complete": True, "launcherStarts": 0}}
    def row(case, *_args, **_kwargs):
        calls.append(case)
        return {"caseId": case, "status": "failed" if case == "R14" else "unavailable",
                "cleanup": {"complete": False if case == "R14" else True, "launcherStarts": 1}}
    with mock.patch.object(argparse.ArgumentParser, "parse_args", return_value=args), \
         mock.patch.object(candidate, "output_directory", return_value=args.output), \
         mock.patch.object(Path, "mkdir"), mock.patch.object(Path, "write_bytes") as writes, \
         mock.patch.object(base, "linux_capabilities", return_value={"schema": 1}), \
         mock.patch.object(candidate, "check_amendment"), \
         mock.patch.object(base, "profile", return_value={}), \
         mock.patch.object(base, "source_inputs", return_value={}), \
         mock.patch.object(candidate, "require_capabilities"), \
         mock.patch.object(candidate, "validate_release", return_value=({}, "b" * 64)), \
         mock.patch.object(base, "ancestors"), mock.patch.object(candidate, "check_review"), \
         mock.patch.object(base, "receipt", side_effect=receipt), \
         mock.patch.object(candidate, "execute_row", side_effect=row), \
         contextlib.redirect_stdout(io.StringIO()):
        code = candidate.main()
        write_count = writes.call_count
    assert code == 1 and calls == ["R14", "R18"]
    return {"finding": "F1", "reproduced": True, "scope": "actual main scheduler with mocked row execution and writes",
            "r14CleanupComplete": False, "nextExecuteRowCalls": calls, "exitCode": code,
            "modeledWritesSuppressed": write_count, "runtimeRowsExecuted": 0}


def nonleader_namespace_holder_is_missed():
    """A modeled nonleader thread holds a selected netns; leader does not."""
    seen = []
    leader = Path("/proc/123")
    tid = leader / "task/124"
    hidden_namespace = tid / "ns/net"
    def directories(path):
        seen.append(str(path))
        if path == Path("/proc"):
            return iter([leader])
        if path == leader / "fd":
            return iter([])
        if path == leader / "task":
            return iter([leader / "task/123", tid])
        if path == tid / "fd":
            return iter([])
        raise AssertionError("Unexpected directory in bounded /proc model")
    def metadata(path):
        seen.append(str(path))
        return SimpleNamespace(st_ino=777 if path == hidden_namespace else 9)
    with mock.patch.object(Path, "iterdir", autospec=True, side_effect=directories), \
         mock.patch.object(Path, "stat", autospec=True, side_effect=metadata), \
         mock.patch.object(backend.time, "monotonic_ns", return_value=1), \
         mock.patch.object(backend.os, "readlink", side_effect=AssertionError("no leader descriptors")):
        counts = backend.holder_counts({777}, set(), 2)
    assert counts == {"namespaceHolders": 0, "pipeHolders": 0, "socketHolders": 0, "listenerHolders": 0}
    assert str(hidden_namespace) not in seen and str(leader / "task") not in seen
    proof = {"ownedTasks": 0, **counts, "dumpFiles": 0, "identityMatched": 1, "cgroupRemoved": 1,
             "mountTargetRemoved": 1, "controlClosed": 1, "rowScratchRemoved": 1}
    backend.life.validate_cleanup(proof)
    return {"finding": "F2", "reproduced": True, "scope": "actual holder_counts with mocked per-thread proc metadata",
            "modeledOwnedNetnsInode": 777, "modeledHoldingTid": 124,
            "modelHasSurvivingNamespaceHolder": True, "reported": counts,
            "numericCleanupValidatorAccepted": True, "metadataPathsVisited": seen,
            "liveProcQueried": False}


if __name__ == "__main__":
    findings = [next_row_after_incomplete_cleanup(), nonleader_namespace_holder_is_missed()]
    print(json.dumps({"schema": 1, "status": "two-source-defects-reproduced-with-host-models-only",
                      "nifBinding": identical_nif_source_binding(), "findings": findings, "runtimeRowsExecuted": 0,
                      "LinuxEnforcementVerified": False, "compilerRun": False}, indent=2, sort_keys=True))
