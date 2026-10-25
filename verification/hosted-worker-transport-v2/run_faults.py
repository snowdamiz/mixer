#!/usr/bin/env python3
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
prefix = [shutil.which("elixir"), "--erl", "+S 2:2 +SDcpu 1 +SDio 1"]
for dependency in ["mint", "jason", "hpax"]:
    prefix += ["-pa", str(HERE/"locked/hosted/_build/test/lib"/dependency/"ebin")]
prefix += [str(HERE/"compile_and_test.exs"), "fault"]
results = []
label = sys.argv[1] if len(sys.argv) == 2 else "attempt-3"
assert label.startswith("attempt-") and all(c.isalnum() or c == "-" for c in label)
for path in sorted((HERE/"candidate/test/fault_cases").glob("*_test.exs")):
    name = path.name.removesuffix("_test.exs")
    args = prefix + [name]
    started = time.monotonic()
    environment = {"PATH": os.environ["PATH"], "LANG": "C.UTF-8", "ERL_CRASH_DUMP": "/dev/null", "ERL_CRASH_DUMP_SECONDS": "0"}
    p = subprocess.Popen(args, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = p.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, err = p.communicate()
    finally:
        try: os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError: pass
    (HERE/(label+"-"+name+".stdout")).write_bytes(out[:2_097_152])
    (HERE/(label+"-"+name+".stderr")).write_bytes(err[:2_097_152])
    row = {"case": name, "args": args, "exit_code": p.returncode, "duration_ms": round((time.monotonic()-started)*1000), "cleanup": "owned fresh BEAM command group disposed"}
    results.append(row)
    print(json.dumps({"case": name, "exit_code": p.returncode}), flush=True)
(HERE/(label+"-fault-commands.json")).write_text(json.dumps(results, indent=2)+"\n")
raise SystemExit(0 if all(row["exit_code"] == 0 for row in results) else 1)
