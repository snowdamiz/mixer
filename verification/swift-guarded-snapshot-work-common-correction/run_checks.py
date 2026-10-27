"""Record a bounded finite source-check command and its exact outputs."""
from pathlib import Path
import gzip
import json
import os
import sys
sys.dont_write_bytecode=True
from prepare import HERE,ROOT,sha,write
from run import bounded

assert not (HERE/'seal.json').exists()
folder=HERE/'commands/finite-source-controls';folder.mkdir(parents=True,exist_ok=False)
argv=[sys.executable,str(HERE/'check.py')]
env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
out,err,receipt=bounded(argv,env,ROOT,30)
(folder/'stdout.gz').write_bytes(gzip.compress(out,mtime=0));(folder/'stderr').write_bytes(err)
receipt.update(schema=1,python_version=sys.version,environment=env,
    source_files={n:sha((HERE/n).read_bytes()) for n in ['check.py','prepare.py','run.py','source-manifest.json']},
    scope='finite source, MIR equality, attribution, existing evidence and cleanup controls; no product runtime',
    stdout_sha256=sha(out),stderr_sha256=sha(err))
(folder/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(out.decode(),end='')
assert receipt['exit_code']==0 and receipt['owned_group_absent'] and not receipt['timed_out'],err.decode()
