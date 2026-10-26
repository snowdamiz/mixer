"""Run the new CI recipe locally with retained exact host-only evidence."""
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "local"
OUT.mkdir(exist_ok=False)
JDK = Path("/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home").resolve(strict=True)
rows = [
    ("orchestration", ["native/android/tests/run-private-owner-host.py", "--closure", "A"]),
    ("renderer", ["native/android/tests/run-private-owner-host.py", "--closure", "B"]),
    ("observer", ["native/android/tests/run-environment-observer-host.py"]),
]


def identity(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


inputs = [".github/workflows/verify.yml", "THIRD_PARTY.yml", *[row[1][0] for row in rows], "verification/android-private-owner-effect-roster-amendment/required-host-roster.json", "verification/android-private-owner-integration-implementation/barrier-map.json"]
bound = {p: identity(ROOT / p) for p in inputs}
receipt = {"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "argv": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version, "head_context_only": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "source_bindings": bound, "JDK": str(JDK), "commands": [], "status": "running", "scope": "local actual host recipe; Linux/JDK17 CI outcome pending; no new independent product acceptance", "native_capture_UI_or_process_inventory": False}
try:
    for name, arguments in rows:
        argv = [sys.executable, "-B", *arguments, "--jdk", str(JDK), "--evidence", str(OUT / name)]
        output = OUT / (name + ".stdout")
        errors = OUT / (name + ".stderr")
        start = time.monotonic()
        row = {"name": name, "argv": argv, "cwd": str(ROOT), "started_at": datetime.now(timezone.utc).isoformat(), "timeout_seconds": 420}
        with output.open("wb") as stdout, errors.open("wb") as stderr:
            child = subprocess.Popen(argv, cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
            row["owned_pid"] = child.pid
            try:
                while child.poll() is None:
                    if time.monotonic() - start > 420 or output.stat().st_size > 2_000_000 or errors.stat().st_size > 2_000_000:
                        row["deadline_or_output_limit"] = True
                        os.killpg(child.pid, signal.SIGKILL)
                        break
                    time.sleep(0.05)
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        row.update({"exit": child.returncode, "finished_at": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": time.monotonic() - start, "stdout": identity(output), "stderr": identity(errors), "child_reaped": True})
        receipt["commands"].append(row)
        (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        if child.returncode or row.get("deadline_or_output_limit"):
            raise RuntimeError(name + " failed; preserved raw streams")
        print(name + ": " + output.read_text().strip(), flush=True)
    assert all(identity(ROOT / p) == expected for p, expected in bound.items())
    receipt["source_stable"] = True
    receipt["status"] = "passed-local-host-recipe"
except BaseException as error:
    receipt["status"] = "failed"
    receipt["failure"] = {"type": type(error).__name__, "message": str(error)}
    raise
finally:
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
