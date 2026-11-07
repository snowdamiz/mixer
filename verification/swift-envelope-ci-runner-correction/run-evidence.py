"""Record correction-owned host commands without ambient process discovery."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import time

PACKET=Path(__file__).resolve().parent
ROOT=PACKET.parents[1]
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(65536),b''):
            h.update(block)
    return h.hexdigest()
def run(name, argv, timeout=180):
    output=PACKET/name
    output.mkdir(exist_ok=False)
    row={'argv':list(map(str,argv)),'cwd':str(ROOT),'started_utc':datetime.now(timezone.utc).isoformat(),
         'python':sys.version,'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
         'source_git_tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),
         'source_files':{p:{'sha256':digest(ROOT/p),'bytes':(ROOT/p).stat().st_size} for p in (
             'scripts/ci/check-analyzer-envelope.py','scripts/ci/tests/test_analyzer_envelope_runner.py',
             'verification/swift-envelope-ci-pack/manifest.json')},
         'timeout_seconds':timeout,'native_runtime_or_capture_started':False,'GA_qualified':False}
    start=time.monotonic()
    with (output/'stdout').open('xb') as stdout,(output/'stderr').open('xb') as stderr:
        try:
            result=subprocess.run(row['argv'],cwd=ROOT,stdout=stdout,stderr=stderr,timeout=timeout)
            row['exit']=result.returncode
        except BaseException as error:
            row['exception']={'type':type(error).__name__,'message':str(error)}
            row['exit']=None
    row['elapsed_seconds']=round(time.monotonic()-start,6)
    row['finished_utc']=datetime.now(timezone.utc).isoformat()
    row['streams']={p:{'bytes':(output/p).stat().st_size,'sha256':digest(output/p)} for p in ('stdout','stderr')}
    (output/'command.json').write_text(json.dumps(row,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'path':str(output),'exit':row['exit'],'elapsed_seconds':row['elapsed_seconds']}),flush=True)
    return row
if __name__=='__main__':
    result=run(sys.argv[1],sys.argv[2:])
    sys.exit(result['exit'] if result['exit'] is not None else 1)
