"""Preserve each pure-host attempt and its exact executable helper sources."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent;R=D.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    name=sys.argv[1];outdir=D/'commands'/name;outdir.mkdir(parents=True,exist_ok=False)
    sources=[]
    for p in sorted(D.glob('*.py')):
        b=p.read_bytes();(outdir/p.name).write_bytes(b);sources.append(dict(path=p.name,bytes=len(b),sha256=sha(b)))
    argv=[sys.executable,'-B',str(D/'review.py')]+(['--check'] if '--check' in sys.argv else []);env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
    start=time.monotonic();p=subprocess.run(argv,cwd=R,env=env,capture_output=True,timeout=30)
    outputs={}
    for label,b in [('stdout',p.stdout),('stderr',p.stderr)]:
        (outdir/label).write_bytes(b);outputs[label]=dict(bytes=len(b),sha256=sha(b))
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
    rec=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),argv=argv,cwd=str(R),environment=env,python_version=sys.version,
      python_executable=sys.executable,python_executable_sha256=sha(Path(sys.executable).read_bytes()),git_revision=revision,elapsed_seconds=time.monotonic()-start,
      exit_code=p.returncode,outputs=outputs,helper_sources=sources,compiler=False,runtime=False,global_process_inventory=False)
    (outdir/'receipt.json').write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n');print(p.stdout.decode(),end='');print(p.stderr.decode(),file=sys.stderr,end='');sys.exit(p.returncode)
if __name__=='__main__':main()
