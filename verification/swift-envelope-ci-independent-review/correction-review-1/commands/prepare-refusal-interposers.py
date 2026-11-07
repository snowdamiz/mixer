#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import sys

ROUND=Path(__file__).resolve().parents[1]
(ROUND/'blackbox-records').mkdir()
original=(ROUND/'commands/refusal-interposer.py').read_text()
records=[]
for mode in ('identity','api'):
    path=ROUND/('blackbox-'+mode+'-toolchain')/'bin/rustc';path.parent.mkdir(parents=True)
    data=original.replace("ROUND=Path('REPLACED_ROUND')",'ROUND=Path('+repr(str(ROUND))+')').replace("MODE='REPLACED_MODE'",'MODE='+repr(mode))
    path.write_text('#!'+sys.executable+'\n'+'\n'.join(data.splitlines()[1:])+'\n');path.chmod(0o755)
    records.append({'mode':mode,'path':str(path.relative_to(ROUND)),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
with (ROUND/'blackbox-interposers.json').open('x') as stream:json.dump({'scope':'Independent runner refusal fixtures only; API uses valid actual identity, identity stops before compilation.','interposers':records},stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps({'prepared':2},sort_keys=True))
