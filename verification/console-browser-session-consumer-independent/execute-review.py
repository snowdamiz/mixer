"""Execute only the allocated independent compiler/probe groups with owned cleanup."""
from __future__ import annotations
import datetime
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
SCRATCH = OWN / "scratch"
NODE = shutil.which("node")
LIMIT = 262144
CAP = 55
PHASE = sys.argv[1]
assert PHASE in {"compile", "protocol", "solid", "solid-so09"}
assert NODE
oracle = OWN / "preaccess-oracles.md"
assert hashlib.sha256(oracle.read_bytes()).hexdigest() == "58969cf14bb489ff3d3ddce7b2963ee3d762b153facc344beb4bd933a9491f36"
release = json.loads((ROOT / "verification/console-session-and-checkout-root-review/session-consumer-frozen-release.json").read_bytes())
manifest_path = ROOT / release["source_manifest"]["path"]
assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == release["source_manifest"]["sha256"]
manifest = json.loads(manifest_path.read_bytes())

def validate_inputs():
    rows = []
    for item in manifest["files"]:
        raw = (ROOT / item["path"]).read_bytes()
        assert len(raw) == item["bytes"]
        assert hashlib.sha256(raw).hexdigest() == item["sha256"], item["path"]
        rows.append(item)
    return rows

before = validate_inputs()
if PHASE == "compile":
    assert not SCRATCH.exists()
    SCRATCH.mkdir()
    (SCRATCH / "package.json").write_text('{"type":"module"}\n')
    (SCRATCH / "node_modules").symlink_to(ROOT / "console/node_modules", target_is_directory=True)
commands = {
    "compile": [NODE, str(ROOT / "console/node_modules/typescript/bin/tsc"),
        "src/state/browser-session-binding.ts", "src/state/workspace-binding.ts",
        "--target", "ES2022", "--module", "ESNext", "--moduleResolution", "Bundler",
        "--strict", "--skipLibCheck", "--noUncheckedIndexedAccess", "--exactOptionalPropertyTypes",
        "--outDir", str(SCRATCH / "modules")],
    "protocol": [NODE, "--test", str(OWN / "protocol-controller.test.mjs")],
    "solid": [NODE, "--conditions=browser", "--test", str(OWN / "solid.test.mjs")],
    "solid-so09": [NODE, "--conditions=browser", "--test", "--test-name-pattern", "^SO09 ", str(OWN / "solid.test.mjs")],
}
cwd = ROOT / "console" if PHASE == "compile" else ROOT
attempt = OWN / f"run-{PHASE}"
assert not attempt.exists(), "Do not overwrite prior evidence or silently replay allocated commands"
attempt.mkdir()
started = time.monotonic()
process = subprocess.Popen(commands[PHASE], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
pgid = process.pid
selector = selectors.DefaultSelector()
selector.register(process.stdout, selectors.EVENT_READ, "stdout")
selector.register(process.stderr, selectors.EVENT_READ, "stderr")
output = {"stdout": bytearray(), "stderr": bytearray()}
reason = None
while selector.get_map():
    if time.monotonic() - started >= CAP:
        reason = "55-second wall cap"
        break
    for key, _ in selector.select(0.1):
        data = os.read(key.fileobj.fileno(), 8192)
        if not data:
            selector.unregister(key.fileobj)
            continue
        output[key.data].extend(data)
        if len(output[key.data]) > LIMIT:
            reason = "262144-byte per-stream output cap"
            break
    if reason:
        break
if reason:
    try: os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError: pass
    try: process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        try: os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError: pass
process.wait(timeout=2)
try:
    os.killpg(pgid, 0)
    group_absent = False
except ProcessLookupError:
    group_absent = True
if not group_absent:
    try: os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError: pass
    for _ in range(20):
        try: os.killpg(pgid, 0)
        except ProcessLookupError:
            group_absent = True
            break
        time.sleep(0.05)
after = validate_inputs()
for name, data in output.items():
    (attempt / f"{name}.txt").write_bytes(data[:LIMIT])
emitted = []
if (SCRATCH / "modules").exists():
    for path in sorted((SCRATCH / "modules").rglob("*.js")):
        raw = path.read_bytes()
        emitted.append({"path": str(path.relative_to(OWN)), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
record = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "phase": PHASE, "argv": commands[PHASE], "cwd": str(cwd), "pid": process.pid,
    "pgid": pgid, "wall_cap_seconds": CAP, "per_stream_output_cap_bytes": LIMIT,
    "wall_seconds": round(time.monotonic() - started, 3), "exit_code": process.returncode,
    "cap_stop_reason": reason, "captured_group_absent": group_absent,
    "source_digest": manifest["source_digest_sha256"], "source_files_verified_before_and_after": len(before),
    "unchanged": before == after, "node_executable": NODE,
    "typescript_version": json.loads((ROOT / "console/node_modules/typescript/package.json").read_bytes())["version"],
    "solid_version": json.loads((ROOT / "console/node_modules/solid-js/package.json").read_bytes())["version"],
    "emitted_modules": emitted,
    "outputs": {name: {"bytes": len(data), "sha256": hashlib.sha256(data[:LIMIT]).hexdigest()} for name, data in output.items()},
}
(attempt / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({key: record[key] for key in ["phase", "exit_code", "wall_seconds", "cap_stop_reason", "captured_group_absent", "source_files_verified_before_and_after", "unchanged"]}))
print(output["stdout"].decode(errors="replace")[-16000:])
if output["stderr"]: print(output["stderr"].decode(errors="replace")[-8000:])
sys.exit(0 if process.returncode == 0 and not reason and group_absent else 1)
