#!/usr/bin/env python3
"""Freeze a small source-only ownership proposal; never launches a child."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[2]
START = time.monotonic()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def write(relative, value):
    path = PACKET / relative
    if path.exists():
        raise ValueError("refusing to replace proposal member: " + relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if type(value) is bytes else encoded(value))


def main():
    assert not (PACKET / "freeze.json").exists()
    lane = "verification/console-key-owner-inflight-lifecycle-implementation"
    roster = [
        (lane + "/prepared-3/freeze.json", "inputs/prepared-3/freeze.json", "immutable selected unexecuted candidate seal"),
        (lane + "/prepared-3/openssl-wrapper.py", "inputs/prepared-3/openssl-wrapper.py", "native Popen currently precedes durable launch append"),
        (lane + "/prepared-3/runner.py", "inputs/prepared-3/runner.py", "currently retains VM sessions; native group custody gap"),
        (lane + "/executions/candidate-2/test/openssl-started.jsonl", "inputs/candidate-2/openssl-started.jsonl", "exact prior published wrapper/native group record"),
        (lane + "/executions/candidate-2/test/openssl-audit.jsonl", "inputs/candidate-2/openssl-audit.jsonl", "exact completed version result and native wait record"),
        ("verification/console-session-and-checkout-root-review/inflight-candidate-2-openssl-group-cleanup-check.json",
         "inputs/root-review/group-cleanup-check.json", "root later sampled only recorded group; not retroactive containment"),
    ]
    sources = []
    for origin, target, role in roster:
        assert time.monotonic() - START < 55
        source = ROOT / origin
        assert source.is_file() and not source.is_symlink()
        data = source.read_bytes()
        write(target, data)
        sources.append({"origin": origin, "snapshot": target, "bytes": len(data), "sha256": sha(data), "role": role})
    upstream = json.loads((PACKET / "inputs/prepared-3/freeze.json").read_bytes())
    for name in ["openssl-wrapper.py", "runner.py"]:
        entry = next(row for row in upstream["files"] if row["path"] == name)
        selected = next(row for row in sources if row["snapshot"] == "inputs/prepared-3/" + name)
        assert (entry["bytes"], entry["sha256"]) == (selected["bytes"], selected["sha256"])
    official = [
        {"url": "https://raw.githubusercontent.com/erlang/otp/OTP-29.0/erts/emulator/sys/unix/erl_child_setup.c",
         "reviewed_lines": [326, 332], "version": "OTP-29.0 reference; not a byte-identity assertion about installed OTP 29.1.1",
         "summary": "Unix child setup calls setpgrp or setsid before exec; do not infer VM process-group inheritance."},
        {"url": "https://docs.python.org/3.14/library/time.html#time.monotonic",
         "version": "Online Python 3.14.10 docs; runtime remains pinned Python 3.14.8",
         "summary": "monotonic clock is shared across processes on macOS since Python 3.10; monotonic_ns avoids float precision."},
        {"url": "https://docs.python.org/3.14/library/subprocess.html#timeout-behavior",
         "version": "Online Python 3.14.10 docs; no runtime upgrade selected",
         "summary": "Initial process creation cannot be interrupted on many platform APIs, limiting unconditional timeout guarantees."},
    ]
    source_rows = [{"path": row["snapshot"], "bytes": row["bytes"], "sha256": row["sha256"]} for row in sources]
    source_tree = sha(encoded(sorted(source_rows, key=lambda row: row["path"])))
    write("source-bindings.json", {"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "python": sys.version,
        "command": "python3 -B verification/console-key-owner-inflight-lifecycle-implementation/ownership-correction/prepare_contract.py",
        "scope": "Source copies, SHA-256, JSON shape and documentation reads only. No subprocess, wrapper/runner execution, native/compiler/formatter/TLS probe, process inventory or product edit.",
        "selected_source_tree_sha256": source_tree, "sources": sources,
        "official_documentation_read_via_web_tool": official})
    protocol = json.loads((PACKET / "protocol.json").read_bytes())
    assert protocol["implementation_authorized"] is False and protocol["execution_authorized"] is False
    assert protocol["group_policy"]["native_can_start_without_acknowledged_custody"] is False
    assert protocol["group_policy"]["require_wrapper_group_equals_VM_group"] is False
    assert protocol["bounds"]["receipt_seconds"] == 55
    write("audit.json", {"schema": 1, "status": "offline-source-proposal-checks-passed-not-implementation-or-runtime-acceptance",
        "source_snapshots": len(sources), "selected_source_tree_sha256": source_tree,
        "native_compiler_formatter_TLS_runtime_or_probe_invocations": 0,
        "implementation_authorized": False, "execution_authorized": False})
    files = []
    for path in sorted(PACKET.rglob("*")):
        assert not path.is_symlink()
        if path.is_file():
            relative = path.relative_to(PACKET).as_posix()
            assert relative != "freeze.json"
            data = path.read_bytes()
            files.append({"path": relative, "bytes": len(data), "sha256": sha(data)})
    write("freeze.json", {"schema": 1, "status": "frozen-proposed-ownership-contract-awaiting-root-review",
        "sole_excluded_relative_path": "freeze.json", "files": files, "tree_sha256": sha(encoded(files)),
        "selected_source_tree_sha256": source_tree, "implementation_authorized": False, "execution_authorized": False})
    print(json.dumps({"status": "frozen-source-only-ownership-proposal", "files": len(files),
        "selected_source_tree_sha256": source_tree, "freeze_sha256": sha((PACKET / "freeze.json").read_bytes()),
        "implementation_or_execution_authorized": False}, indent=2))


if __name__ == "__main__":
    main()
