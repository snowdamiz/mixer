#!/usr/bin/env python3
"""Seal only this owned offline packet. Root separately releases/selects it."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import sys

D = Path(__file__).resolve().parent
if (D / "seal.json").exists(): raise SystemExit("already-frozen")
history = []
for p in sorted((D / "commands").glob("attempt-*/receipt.json")):
    receipt = json.loads(p.read_text())
    history.append({"path": str(p.relative_to(D)), "returncode": receipt["returncode"],
        "argv": receipt["argv"], "receipt_sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
(D / "attempt-history.json").write_text(json.dumps({"schema": 1, "attempts": history,
    "failures_preserved": sum(x["returncode"] != 0 for x in history),
    "failure_scope": {"attempt-001": "wrong expected source literal for index formula; corrected to128+64",
        "attempt-005": "checker admitted bool True as int1 through Python equality; canonical JSON comparison now rejects"}}, indent=2, sort_keys=True) + "\n")
(D / "cleanup.json").write_text(json.dumps({"schema": 1,
    "compiler_or_product_runtime_started": False, "native_UI_or_capture_started": False,
    "global_process_inventory_performed": False, "persistent_owned_processes": 0,
    "temporary_native_instances": 0, "temporary_compiler_or_native_scratch": 0,
    "python_children_waited": True, "other_projects_processes_or_data_modified": False,
    "ownership": "Only this verification directory was written; no Git/root metadata/frozen inputs changed"}, indent=2, sort_keys=True) + "\n")
(D / "freeze-receipt.json").write_text(json.dumps({"schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "argv": [sys.executable, str(Path(__file__).resolve())],
    "tool_version": platform.python_version(), "tool": sys.executable,
    "tool_sha256": hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),
    "source_tree_sha256": "690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185",
    "scope": "seal owned source/offline evidence only; no root selection or operational authority"}, indent=2, sort_keys=True) + "\n")
members = []
for p in sorted(D.rglob("*")):
    if p.is_dir(): continue
    if p.is_symlink(): raise SystemExit("symlink-not-allowed")
    if p.name == "seal.json": continue
    if "__pycache__" in p.parts: raise SystemExit("unexpected-bytecode")
    raw = p.read_bytes()
    members.append({"path": str(p.relative_to(D)), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
seal = {"schema": 1, "status": "frozen-source146-interface-amendment-candidate-unselected",
    "members": members, "member_count": len(members), "bytes": sum(x["bytes"] for x in members),
    "source_tree_sha256": "690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185",
    "host_tree_sha256": "027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2",
    "root_selected_nine": True, "root_selected_fourteen": False,
    "accepted_bound": False, "operational_grant": False}
raw = (json.dumps(seal, indent=2, sort_keys=True) + "\n").encode()
(D / "seal.json").write_bytes(raw)
print(json.dumps({"seal_sha256": hashlib.sha256(raw).hexdigest(), "members": len(members), "bytes": seal["bytes"]}))
