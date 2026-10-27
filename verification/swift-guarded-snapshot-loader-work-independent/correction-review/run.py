#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,subprocess,sys,time
D=Path(__file__).resolve().parent
command=[sys.executable,str(D/'audit.py')]
started=time.monotonic()
result=subprocess.run(command,capture_output=True,text=True,timeout=60)
(D/'stdout').write_text(result.stdout)
(D/'stderr').write_text(result.stderr)
receipt=dict(command=command,python=sys.version,script_sha256=hashlib.sha256((D/'audit.py').read_bytes()).hexdigest(),exit_code=result.returncode,elapsed_seconds=time.monotonic()-started,stdout_sha256=hashlib.sha256(result.stdout.encode()).hexdigest(),stderr_sha256=hashlib.sha256(result.stderr.encode()).hexdigest(),child_waited=True,scope='owned pure independent correction analysis and pure receiver/resolver regression; no frozen write-effect script replay')
(D/'command-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if result.returncode:raise SystemExit(result.stderr)
print(result.stdout.strip())
