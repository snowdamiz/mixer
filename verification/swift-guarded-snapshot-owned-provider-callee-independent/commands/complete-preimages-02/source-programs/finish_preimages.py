import hashlib
import json
from pathlib import Path

OWN=Path(__file__).resolve().parent
ROOT=OWN.parents[1]

def main():
    available={hashlib.sha256(p.read_bytes()).hexdigest():p.read_bytes() for p in (OWN/'commands').glob('*/source-programs/*.py')}
    available.update({hashlib.sha256(p.read_bytes()).hexdigest():p.read_bytes() for p in OWN.glob('*.py')})
    count=0
    for path in (OWN/'commands').glob('*/receipt.json'):
        receipt=json.loads(path.read_text())
        for row in receipt['source_files']:
            body=available[row['sha256']]
            assert len(body)==row['bytes']
            dest=path.parent/'source-programs'/Path(row['path']).name
            dest.parent.mkdir(exist_ok=True)
            if dest.exists():assert dest.read_bytes()==body
            else:dest.write_bytes(body);count+=1
    print(json.dumps({'missing_exact_historical_source_preimages_filled':count}))

if __name__=='__main__':main()
