#!/usr/bin/env python3
"""Freeze only this owned evidence packet after successful pure controls."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
if (HERE/'seal.json').exists():raise SystemExit('already frozen')
results=json.loads((HERE/'verification-results.json').read_bytes())
if results['status']!='pure-component-proposal-controls-pass':raise SystemExit('controls not passing')
for name in ('derive','pure-controls'):
 if json.loads((HERE/'commands'/name/'receipt.json').read_bytes())['exit_code']!=0:raise SystemExit('failed final command')
rows=[]
for p in sorted(HERE.rglob('*')):
 if not p.is_file():continue
 if p.is_symlink() or '__pycache__' in p.parts:raise SystemExit('unexpected alias/cache')
 data=p.read_bytes();rows.append(dict(path=p.relative_to(HERE).as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
value=dict(schema=1,member_count=len(rows),total_bytes=sum(x['bytes'] for x in rows),members=rows,scope='finite exact146 leaf/shell component proposal; independent acceptance, native layouts/callees/drop/backing/root/full-host quote pending',product_runtime=False,compiler=False)
raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode();(HERE/'seal.json').write_bytes(raw)
print(json.dumps(dict(member_count=len(rows),bytes=value['total_bytes'],seal_sha256=hashlib.sha256(raw).hexdigest())))
