#!/usr/bin/env python3
"""Preserve each independent Python-only audit attempt, including failures."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
p=Path(__file__).resolve().parent
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
a=p/'attempts'/stamp;a.mkdir(parents=True)
script=p/'review.py';data=script.read_bytes();(a/'review.py').write_bytes(data)
start={'at':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-B',str(script)],
       'python':sys.version,'script_sha256':hashlib.sha256(data).hexdigest(),
       'source_revision_context':'d275c072b6c89b8e99213e4eb4dafdc4722f5f40',
       'live_tree_clean_claim':False,'product_compiler_runtime_native_capture_execution':False}
(a/'start.json').write_text(json.dumps(start,indent=2)+'\n')
r=subprocess.run(start['command'],capture_output=True)
(a/'stdout').write_bytes(r.stdout);(a/'stderr').write_bytes(r.stderr)
result={'at':datetime.now(timezone.utc).isoformat(),'exit_code':r.returncode,
        'stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),
        'stderr_sha256':hashlib.sha256(r.stderr).hexdigest()}
(a/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'attempt':str(a),'result':result},indent=2))
print(r.stdout.decode(),end='');print(r.stderr.decode(),end='',file=sys.stderr)
sys.exit(r.returncode)
