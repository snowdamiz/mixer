"""One owned pure Python child, minimal environment, 52s + bounded 3s cleanup."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LIMIT = 4_194_304


def row(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    assert len(sys.argv) == 2 and sys.argv[1] in ("preaccess-001", "preaccess-final")
    out = HERE / "commands" / sys.argv[1]
    out.mkdir(parents=True, exist_ok=False)
    source_paths = sorted(p for p in HERE.iterdir() if p.is_file() and p.name in (
        "README.md", "contract.json", "cases.json", "compiler-cases.json", "build_oracles.py",
        "review_preaccess.py", "run_preaccess.py", "check_seal.py"))
    assert len(source_paths) == 8
    source = [row(p) for p in source_paths]
    # Exact source snapshots precede execution; later evidence does not qualify
    # earlier navigation/authoring or infer the environment of any old command.
    for path in source_paths:
        (out / path.name).write_bytes(path.read_bytes())
    tool = Path(sys.executable).resolve()
    env = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
           "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"}
    argv = [str(tool), "-B", str(HERE / "review_preaccess.py"), str(out)]
    plan = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "argv": argv, "cwd": str(ROOT), "environment": env,
            "tool": row(tool), "tool_version": sys.version,
            "source": source, "source_tree_sha256": digest(source),
            "historical_frozen_revision": "9398732c23648a82097d5a72b02b1c77af818e41",
            "execution_seconds_max": 52, "cleanup_seconds_max": 3,
            "stdout_stderr_each_bytes_max": LIMIT, "process_group_owned": True,
            "compiler_native_UI_product_model_execution": False}
    write(out / "plan.json", plan)
    start = time.monotonic()
    reason = None
    with (out / "stdout").open("wb") as stdout, (out / "stderr").open("wb") as stderr:
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        while child.poll() is None:
            if time.monotonic() - start >= 52:
                reason = "deadline"
                break
            if any((out / name).stat().st_size > LIMIT for name in ("stdout", "stderr")):
                reason = "output limit"
                break
            time.sleep(0.02)
        if reason is not None:
            os.killpg(child.pid, signal.SIGKILL)
        code = child.wait(timeout=3)
    try:
        os.killpg(child.pid, 0)
        absent = False
    except ProcessLookupError:
        absent = True
    receipt = {"schema": 1, "exit": code, "stop_reason": reason,
               "elapsed_seconds": time.monotonic() - start, "child_pid": child.pid,
               "owned_pgid": child.pid, "child_reaped": child.poll() is not None,
               "exact_owned_group_absent": absent, "source_after": [row(p) for p in source_paths],
               "tool_after": row(tool), "outputs": [row(out / n) for n in ("stdout", "stderr")],
               "native_UI_capture_compiler_product_processes_started": 0,
               "global_process_inventory": False, "owned_scratch": []}
    receipt["source_unchanged"] = receipt["source_after"] == source
    receipt["tool_unchanged"] = receipt["tool_after"] == plan["tool"]
    write(out / "receipt.json", receipt)
    assert code == 0 and reason is None and absent, receipt
    assert receipt["source_unchanged"] and receipt["tool_unchanged"]
    assert all(x["bytes"] <= LIMIT for x in receipt["outputs"])
    result = json.loads((out / "result.json").read_bytes())
    receipts = [json.loads(p.read_bytes()) for p in sorted((HERE / "commands").glob("*/receipt.json"))]
    write(HERE / "cleanup.json", {"owned_children": len(receipts),
          "all_reaped": all(x["child_reaped"] for x in receipts),
          "exact_owned_groups_absent": all(x["exact_owned_group_absent"] for x in receipts),
          "scratch": [], "compiler_native_UI_capture": 0, "global_inventory": False})
    print(json.dumps({"command": sys.argv[1], "exit": code, "input_members": result["frozen_input_members"],
                      "anchors": result["verified_original_anchors"], "oracle_counts": result["oracle_data_consistency"],
                      "owned_group_absent": absent}, sort_keys=True))


if __name__ == "__main__":
    main()
