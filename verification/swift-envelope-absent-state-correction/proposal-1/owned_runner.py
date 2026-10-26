#!/usr/bin/env python3
"""Bounded custody for proposal metadata/standard-library checks, never Rust."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
name = sys.argv[1]
argv = sys.argv[2:]
allowed = (
    argv == [sys.executable, "--version"]
    or argv == ["/usr/bin/git", "--version"]
    or argv == ["/usr/bin/git", "rev-parse", "HEAD"]
    or argv == [sys.executable, str(OUT / "prepare_proposal.py")]
    or argv == [sys.executable, str(OUT / "check_proposal.py")]
)
assert allowed, "Only proposal authoring/metadata/check commands are permitted"
dest = OUT / "commands" / name
dest.mkdir(parents=True, exist_ok=False)
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
clock = time.monotonic()
child = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
timed_out = False
try:
    stdout, stderr = child.communicate(timeout=45)
except subprocess.TimeoutExpired:
    timed_out = True
    os.killpg(child.pid, signal.SIGKILL)
    stdout, stderr = child.communicate(timeout=5)
(dest / "stdout.bin").write_bytes(stdout)
(dest / "stderr.bin").write_bytes(stderr)
hashes = {}
for rel in ["prepare_proposal.py", "check_proposal.py", "src/envelope.rs", "src/analyzer.rs"]:
    p = OUT / rel
    if p.exists():
        hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
tree = [{"path":n,"sha256":h} for n,h in sorted(hashes.items())]
receipt = {"schema":1,"argv":argv,"cwd":str(ROOT),"started_at":start,
    "elapsed_seconds":round(time.monotonic()-clock,6),"deadline_seconds":45,
    "own_child_pid":child.pid,"own_child_new_session":True,"timed_out":timed_out,
    "returncode":child.returncode,"stdout_bytes":len(stdout),"stderr_bytes":len(stderr),
    "stdout_sha256":hashlib.sha256(stdout).hexdigest(),"stderr_sha256":hashlib.sha256(stderr).hexdigest(),
    "python":sys.version,"python_executable":sys.executable,"source_inputs":tree,
    "source_tree_sha256":hashlib.sha256(json.dumps(tree,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
    "scope":"standard-library proposal authoring/hash/arithmetic or metadata only; no corrected candidate compile/runtime",
    "child_reaped":child.returncode is not None,"scratch_created":False,"cleanup":"no scratch; only owned child session managed"}
(dest / "receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps({"command":name,"returncode":child.returncode,"timed_out":timed_out,
    "stdout":stdout.decode(errors="replace"),"stderr":stderr.decode(errors="replace")},sort_keys=True))
sys.exit(0 if child.returncode == 0 and not timed_out else 1)
