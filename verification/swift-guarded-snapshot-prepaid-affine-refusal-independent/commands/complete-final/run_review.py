"""Own bounded process group, exact environment, complete frozen-input custody."""
import datetime
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from custody import HERE, ROOT, custody, review_sources, row, tree, write


def main():
    label, *selectors = sys.argv[1:]
    assert label.isascii() and label.replace("-", "").isalnum()
    assert selectors and all(s.startswith("review_controls") for s in selectors)
    destination = HERE / "commands" / label
    destination.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    before, sources = custody(), review_sources()
    for entry in sources:
        path = ROOT / entry["path"]
        (destination / path.name).write_bytes(path.read_bytes())
    write(destination / "input-before.json", before)
    tool = Path(sys.executable).resolve()
    env = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
           "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"}
    argv = [str(tool), "-B", "-m", "unittest", "-v", *selectors]
    write(destination / "plan.json", {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "argv": argv, "cwd": str(HERE), "environment_exact": env,
        "parent_argv": [str(tool), "-B", str(Path(__file__).resolve()), *sys.argv[1:]],
        "parent_environment_exact": dict(os.environ), "tool": {**row(tool), "version": sys.version},
        "source": sources, "source_tree_sha256": tree(sources), "input_members": len(before),
        "source_revision_from_frozen_root_release_only": "9398732c23648a82097d5a72b02b1c77af818e41",
        "candidate_seal": "2270f59809b80c49df907a7ea9c20faf4dd45735cabad275ae61065efc19c50b",
        "deadline_seconds": 55, "scope": "independently authored synthetic host controls; no old test/fixture imports, native/compiler/product/UI/capture/Git/global inventory"})
    child = None
    stdout = stderr = b""
    timed_out = absent = reaped = False
    try:
        child = subprocess.Popen(argv, cwd=HERE, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 start_new_session=True)
        try:
            stdout, stderr = child.communicate(timeout=55)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate(timeout=5)
        reaped = child.returncode is not None
    finally:
        if child is not None and child.returncode is None:
            os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate(timeout=5)
            reaped = child.returncode is not None
        if child is not None:
            try:
                os.killpg(child.pid, 0)
            except ProcessLookupError:
                absent = True
        (destination / "stdout").write_bytes(stdout)
        (destination / "stderr").write_bytes(stderr)
        after, sources_after = custody(), review_sources()
        write(destination / "input-after.json", after)
        receipt = {"schema": 1, "elapsed_seconds": time.monotonic() - start,
            "exit": child.returncode if child is not None else None, "timed_out": timed_out,
            "owned_pid_pgid": child.pid if child is not None else None, "child_reaped": reaped,
            "owned_group_absent": absent, "inputs_unchanged": before == after, "input_members": len(before),
            "source_before": sources, "source_after": sources_after, "source_unchanged": sources == sources_after,
            "tool_after": row(tool), "outputs": [row(destination / n) for n in
                ("stdout", "stderr", "input-before.json", "input-after.json")], "owned_scratch": [],
            "native_compiler_product_UI_capture_processes_started": 0, "global_process_inventory": False}
        write(destination / "receipt.json", receipt)
    print(__import__("json").dumps({k: receipt[k] for k in ("exit", "elapsed_seconds", "input_members",
        "inputs_unchanged", "source_unchanged", "child_reaped", "owned_group_absent")}))
    return int(not (receipt["exit"] == 0 and not timed_out and absent and reaped and before == after and sources == sources_after))


if __name__ == "__main__":
    raise SystemExit(main())
