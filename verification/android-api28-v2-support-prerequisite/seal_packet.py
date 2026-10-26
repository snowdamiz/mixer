#!/usr/bin/env python3
"""Run only this packet's offline checks, retain streams, then seal exact members."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOC = "docs/android-api28-v2-support-prerequisite.md"


def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def run(number, script, *extra):
    command = [sys.executable, str(HERE / script), *extra]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=30)
    stem = f"command-{number}"
    (HERE / (stem + ".stdout.txt")).write_text(result.stdout)
    (HERE / (stem + ".stderr.txt")).write_text(result.stderr)
    return {"argv": command, "cwd": str(ROOT), "exit_code": result.returncode,
            "stdout": stem + ".stdout.txt", "stderr": stem + ".stderr.txt"}


def seal():
    members = [p for p in HERE.rglob("*") if p.is_file() and p.name != "manifest.json"]
    members.append(ROOT / DOC)
    files = {str(p.relative_to(ROOT)): identity(p.read_bytes()) for p in sorted(members)}
    write("manifest.json", {"schema": 1, "algorithm": "sha256", "self_excluded": "manifest.json",
                           "scope": "Exact proposal/source packet only; no implementation or qualification authority.", "files": files})


if __name__ == "__main__":
    for name in ("build_spec.py", "check_packet.py", "seal_packet.py"):
        ast.parse((HERE / name).read_text(), filename=name)
    commands = [run(1, "build_spec.py"), run(2, "check_packet.py"), run(3, "check_packet.py", "--live-sources")]
    if commands[0]["exit_code"] != 0 or commands[1]["exit_code"] != 0:
        raise SystemExit("Proposal data/default consistency check failed; retained command streams.")
    source = json.loads((HERE / "source-map.json").read_text())
    drift = []
    for relative, frozen in source["files"].items():
        current = identity((ROOT / relative).read_bytes())
        if current != frozen:
            drift.append({"path": relative, "frozen": frozen, "live": current})
    write("live-drift.json", {"observed_at_utc": datetime.now(timezone.utc).isoformat(), "files_checked": len(source["files"]),
                             "drift": drift, "scope": "Concurrent root metadata drift is preserved; frozen source identities are never refreshed silently."})
    # Precreate the final command streams so manifest membership stays fixed.
    (HERE / "command-4.stdout.txt").write_text("")
    (HERE / "command-4.stderr.txt").write_text("")
    receipt = {
        "schema": 1, "at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed-frozen-source-spec-consistency-only; live-source-drift-preserved" if drift else "passed-source-spec-consistency-only",
        "command": [sys.executable, str(HERE / "seal_packet.py")], "commands": commands,
        "tools": {"python": sys.version, "python_executable": sys.executable, "platform": platform.platform()},
        "source_map_sha256": source["source_map_sha256"], "source_files": len(source["files"]),
        "accepted_context_revision": source["accepted_context_revision"],
        "live_HEAD_inspected": False, "live_drift_paths": [item["path"] for item in drift],
        "python_source_AST_parse": {"files": 3, "status": "passed; syntax only, not product tests"},
        "source_discovery": "Read named product/contract files and direct references only. Initial broad filename discovery was truncated; no discovered frozen verification implementation was imported or executed.",
        "official_findings": "official-findings.json; primary Android reference retrieved by web search/open/find; selected fact paraphrases, not full archived pages",
        "scope": "Proposal data and finite offline source/spec consistency only. No production implementation changes or release authority.",
        "flags": {"implementation_selected": False, "public_V2_selected": False, "native_compiler_run": False,
                  "native_runtime_or_UI_or_capture_started": False, "process_inventory_run": False,
                  "phone_run": False, "git_commit_push_or_publication_run": False,
                  "dependencies_or_credentials_changed": False, "customer_action_run": False, "GA_qualified": False},
        "pause": "Computer use/capture/native runtime/UI/process inventories paused; phones disconnected. No cleanup action needed because this lane started no such processes.",
        "negative_controls_scope": "Six in-memory specification mutations must reject; not six product/native behavioral cases.",
        "limitations": ["API28-35 rendering remains rejected; unavailable required accessibility observations unresolved.",
                        "Private C5 acceptance is inherited only for its exact prior development scope.",
                        "All new native compiler/runtime/effect/TalkBack/parity/public/FieldLog/OTA/signing/store/operations/GA gates remain pending.",
                        "Independent implementation review and explicit root source/profile selection remain pending."],
    }
    write("receipt.json", receipt)
    seal()
    last = run(4, "check_packet.py", "--manifest")
    if last["exit_code"] != 0:
        raise SystemExit("First sealed check failed; inspect retained streams.")
    receipt["commands"].append(last)
    write("receipt.json", receipt)
    seal()
    # Recheck the final seal without changing any member afterwards. Output is
    # deterministic and must equal the already retained command-4 stdout/stderr.
    result = subprocess.run(last["argv"], cwd=ROOT, text=True, capture_output=True, timeout=30)
    if result.returncode != 0 or result.stdout != (HERE / last["stdout"]).read_text() or result.stderr != (HERE / last["stderr"]).read_text():
        raise SystemExit("Final sealed check failed or changed; final packet is not accepted.")
    print(result.stdout, end="")
    print(json.dumps({"manifest_sha256": identity((HERE / "manifest.json").read_bytes())["sha256"], "live_drift_paths": receipt["live_drift_paths"]}, sort_keys=True))
