"""Bounded offline subprocess receipts. Starts no Android or capture process."""
import datetime
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

OWN = Path(__file__).resolve().parent
ROOT = OWN.parents[1]
entries = []
for name, script in (("custody", "verify_inputs.py"), ("model", "protocol_controls.py")):
    argv = [sys.executable, "-B", str(OWN / script)]
    start = time.monotonic()
    at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60, check=False)
    for suffix, content in (("stdout", result.stdout), ("stderr", result.stderr)):
        (OWN / "commands" / (name + "." + suffix)).write_bytes(content)
    entries.append({"name": name, "argv": argv, "cwd": str(ROOT), "started": at,
                    "timeout_seconds": 60, "elapsed_seconds": time.monotonic() - start,
                    "exit_code": result.returncode, "child_reaped": True,
                    "stdout": "commands/" + name + ".stdout",
                    "stderr": "commands/" + name + ".stderr",
                    "script_sha256": hashlib.sha256((OWN / script).read_bytes()).hexdigest()})
    if result.returncode:
        break
receipt = {"schema": 1, "scope": "Offline immutable-input hashing and independent abstract protocol controls",
           "python_version": sys.version, "python_executable": sys.executable,
           "python_executable_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
           "os": platform.platform(), "commands": entries,
           "product_source_compiled_or_executed": False,
           "native_ui_capture_or_process_inventory": False,
           "scratch_created": False, "owned_native_instances_started": 0,
           "cleanup": "Both bounded children synchronously reaped; no scratch/native instance created",
           "success": len(entries) == 2 and all(e["exit_code"] == 0 for e in entries)}
(OWN / "execution-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"success": receipt["success"], "commands": len(entries)}))
raise SystemExit(0 if receipt["success"] else 1)
