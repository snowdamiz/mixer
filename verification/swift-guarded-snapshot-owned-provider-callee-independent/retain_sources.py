"""Retain exact reviewer-program preimages named by historical receipts."""
import hashlib
import json
from pathlib import Path

OWN = Path(__file__).resolve().parent
ROOT = OWN.parents[1]

def main():
    count = 0
    for receipt_path in sorted((OWN / 'commands').glob('*/receipt.json')):
        receipt = json.loads(receipt_path.read_text())
        target = receipt_path.parent / 'source-programs'
        target.mkdir(exist_ok=True)
        for record in receipt['source_files']:
            body = (ROOT / record['path']).read_bytes()
            if hashlib.sha256(body).hexdigest() != record['sha256']:
                # The only historical source edit so far was correcting this
                # exact envelope exclusion after a child-free preflight failure.
                if receipt_path.parent.name != 'source-trace-01' or Path(record['path']).name != 'run_review.py':
                    raise AssertionError('unrecoverable historical source preimage')
                body = body.replace(b" - {'seal.json'}", b" - {'seal.json', 'freeze-receipt.json'}")
            assert len(body) == record['bytes'] and hashlib.sha256(body).hexdigest() == record['sha256']
            (target / Path(record['path']).name).write_bytes(body)
            count += 1
    print(json.dumps({'historical_exact_source_preimages_retained':count,'historical_recovery_is_digest_verified':True}))

if __name__ == '__main__': main()
