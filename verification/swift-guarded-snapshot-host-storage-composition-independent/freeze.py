"""Freeze this independently owned packet only."""
from pathlib import Path
import datetime, hashlib, json
HERE=Path(__file__).resolve().parent
def main():
    assert not (HERE/'seal.json').exists(),'already frozen'
    rows=[]
    for path in sorted(HERE.rglob('*')):
        assert not path.is_symlink(),path
        if not path.is_file():continue
        assert '__pycache__' not in path.parts and path.suffix!='.pyc',path
        data=path.read_bytes();rows.append({'path':str(path.relative_to(HERE)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
            'host_tree_sha256':'027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2',
            'member_count':len(rows),'member_bytes':sum(x['bytes'] for x in rows),'members':rows,
            'scope':'independently reviewed conditional logical storage interface; no actual root policy or whole grant'}
    data=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode();(HERE/'seal.json').write_bytes(data)
    print(json.dumps({'seal_sha256':hashlib.sha256(data).hexdigest(),'members':len(rows),'bytes':result['member_bytes']}))
if __name__=='__main__':main()
