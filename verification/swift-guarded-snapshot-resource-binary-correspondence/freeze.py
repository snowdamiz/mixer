"""Seal this evidence directory; --verify is read-only and replayable."""
import hashlib
import json
from pathlib import Path
import sys

D=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    rows=[]
    for path in sorted(D.rglob('*')):
        if '__pycache__' in path.parts or path==D/'seal.json':continue
        assert not path.is_symlink()
        if path.is_file():
            b=path.read_bytes();rows.append(dict(path=str(path.relative_to(D)),bytes=len(b),sha256=sha(b)))
    result=dict(schema=1,members=rows,member_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),scope='Bounded offline resource binary correspondence; no actual caller/executable or whole-host acceptance')
    if '--verify' in sys.argv:assert json.loads((D/'seal.json').read_text())==result
    else:
        assert not (D/'seal.json').exists()
        (D/'seal.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(status='passed',seal_sha256=sha((D/'seal.json').read_bytes()),members=len(rows),bytes=result['total_bytes'])))
if __name__=='__main__':main()
