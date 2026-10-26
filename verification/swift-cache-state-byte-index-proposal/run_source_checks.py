"""Preserve each source-only Python attempt and its complete raw output."""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys
root=Path(__file__).resolve().parent
stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
attempt=root/"attempts"/stamp
attempt.mkdir()
(attempt/"source_checks.py").write_bytes((root/"source_checks.py").read_bytes())
command=[sys.executable,"-B",str(root/"source_checks.py")]
start=dict(command=command,cwd=str(root),python=sys.version,
    source_script_sha256=hashlib.sha256((root/"source_checks.py").read_bytes()).hexdigest(),
    scope="Python custody, source assembly, finite arithmetic/order/range models; no Rust/compiler/native runtime",at=stamp)
(attempt/"start.json").write_text(json.dumps(start,indent=2)+"\n")
result=subprocess.run(command,cwd=root,capture_output=True)
(attempt/"stdout").write_bytes(result.stdout)
(attempt/"stderr").write_bytes(result.stderr)
(attempt/"result.json").write_text(json.dumps(dict(exit_code=result.returncode,
    stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),stderr_sha256=hashlib.sha256(result.stderr).hexdigest()),indent=2)+"\n")
sys.stdout.buffer.write(result.stdout)
sys.stderr.buffer.write(result.stderr)
raise SystemExit(result.returncode)
