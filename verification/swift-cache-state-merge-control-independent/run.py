#!/usr/bin/env python3
"""Run only the independent Python review and retain both modes' outputs."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
command=[]
for mode, flags in [('normal',[]),('optimized',['-O'])]:
    argv=[sys.executable,'-B',*flags,str(OUT/'check.py')]
    begin=datetime.datetime.now(datetime.UTC).isoformat()
    p=subprocess.run(argv,cwd=ROOT,capture_output=True)
    for kind,data in [('stdout',p.stdout),('stderr',p.stderr)]:
        (OUT/f'{mode}.{kind}.txt').write_bytes(data)
    command.append(dict(mode=mode,argv=argv,started=begin,
        finished=datetime.datetime.now(datetime.UTC).isoformat(),exit_code=p.returncode,
        stdout_sha256=hashlib.sha256(p.stdout).hexdigest(),stderr_sha256=hashlib.sha256(p.stderr).hexdigest()))
    if p.returncode:
        break
receipt=dict(schema=1,python=sys.version,argv=sys.argv,
             source_revision='A433 exact fullsource; unchanged merge fragment bound in source-map.json',
             check_sha256=hashlib.sha256((OUT/'check.py').read_bytes()).hexdigest(),commands=command,
             native_compiler_runtime_UI_capture_process_inventory_Git_or_hosted=False)
(OUT/'command-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt,sort_keys=True))
sys.exit(command[-1]['exit_code'])
