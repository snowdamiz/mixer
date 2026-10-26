#!/usr/bin/env python3
"""Record only own bounded Python model commands and output; no product tools."""
import datetime, hashlib, json, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(b): return hashlib.sha256(b).hexdigest()
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
out=HERE/'commands'/stamp; out.mkdir(parents=True)
commands=[]
for name,args in [('build',['-B',str(HERE/'build.py')]),('check',['-B',str(HERE/'check.py')]),('check-optimized',['-O','-B',str(HERE/'check.py')])]:
    argv=[sys.executable]+args
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    result=subprocess.run(argv,cwd=HERE.parents[1],capture_output=True,timeout=30)
    (out/(name+'.stdout')).write_bytes(result.stdout); (out/(name+'.stderr')).write_bytes(result.stderr)
    row={'argv':argv,'started':started,'finished':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':result.returncode,'tool_version':sys.version,'script_sha256':sha(Path(args[-1]).read_bytes()),'stdout_path':str((out/(name+'.stdout')).relative_to(HERE)),'stdout_sha256':sha(result.stdout),'stderr_path':str((out/(name+'.stderr')).relative_to(HERE)),'stderr_sha256':sha(result.stderr)}
    commands.append(row)
    if result.returncode!=0:
        (out/'receipt.json').write_text(json.dumps({'commands':commands,'failed':True},indent=2)+'\n')
        raise SystemExit(result.returncode)
source=HERE/'source/cache_state.rs.txt'
receipt={'commands':commands,'source_sha256':sha(source.read_bytes()),'input_tree_digest':json.loads((HERE/'inputs.json').read_text())['tree_digest'],'failed':False,'scope':'own Python source/math; no Rust/compiler/product/native/UI/capture/process-inventory/Git/hosted operations'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
(HERE/'latest-run.json').write_text(json.dumps({'path':str(out.relative_to(HERE)),'receipt_sha256':sha((out/'receipt.json').read_bytes())},indent=2)+'\n')
print(json.dumps({'commands':len(commands),'exit_codes':[x['exit_code'] for x in commands],'receipt':str((out/'receipt.json').relative_to(HERE)),'source_sha256':receipt['source_sha256']},indent=2))
