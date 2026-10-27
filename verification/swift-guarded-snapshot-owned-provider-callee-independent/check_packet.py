"""Read-only complete-membership checker for the independent review."""
import hashlib
import json
from pathlib import Path
import run_review

OWN=Path(__file__).resolve().parent

def main():
    seal=json.loads((OWN/'seal.json').read_text())
    present={str(p.relative_to(OWN)) for p in OWN.rglob('*') if p.is_file()}
    assert present=={r['path'] for r in seal['members']}|{'seal.json'}
    assert len(seal['members'])==seal['member_count']
    assert sum(r['bytes'] for r in seal['members'])==seal['total_bytes']
    for row in seal['members']:
        p=OWN/row['path'];assert not p.is_symlink()
        b=p.read_bytes();assert (len(b),hashlib.sha256(b).hexdigest())==(row['bytes'],row['sha256'])
    current=run_review.custody()
    retained=json.loads((OWN/'final-input-custody.json').read_text())
    assert current['ok'] and current==retained
    print(json.dumps({'status':'independent-review-complete-membership-and-1245-frozen-inputs-match','seal_sha256':hashlib.sha256((OWN/'seal.json').read_bytes()).hexdigest(),'members':seal['member_count'],'bytes':seal['total_bytes'],'candidate_accepted':False}))

if __name__=='__main__':main()
