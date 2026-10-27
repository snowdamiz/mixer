"""Seal only this review after offline replay; no compiler or test runtime."""
from pathlib import Path
import json
import sys
sys.dont_write_bytecode = True
from review import HERE, sha, canonical, row
from verify import main

main()
members = [row(p.relative_to(HERE).as_posix(), p.read_bytes())
    for p in sorted(HERE.rglob('*')) if p.is_file() and p.name != 'seal.json']
value = dict(schema=1, scope='independent frozen exact146 private typed composition; metadata, focused layouts and synthetic controls only',
    member_count=len(members), bytes=sum(m['bytes'] for m in members),
    members_sha256=sha(canonical(members)), members=members)
path = HERE/'seal.json'
if path.exists(): assert json.loads(path.read_bytes()) == value
else: path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(seal_sha256=sha(path.read_bytes()), members=len(members), bytes=value['bytes'])))
