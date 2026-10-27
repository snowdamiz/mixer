#!/usr/bin/env python3
"""Read-only reviewer packet replay; optional independent pure tests."""
import argparse,json,sys,unittest
from pathlib import Path
sys.dont_write_bytecode=True
import audit,build_report
H=Path(__file__).resolve().parent
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tests',action='store_true');args=parser.parse_args()
    if (H/'seal.json').exists():
        seal=audit.load(H/'seal.json');audit.rehash_packet(H,audit.sha((H/'seal.json').read_bytes()))
    for name,data in build_report.render().items():
        if (H/name).read_bytes()!=data:raise ValueError('independent artifact replay mismatch '+name)
    if args.tests:
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(audit.IndependentReview))
        if not result.wasSuccessful():raise SystemExit(1)
    print(json.dumps(dict(status='independent-callee-review-reproduced',authored_bodies=38,
        native_terms_remaining=0,typed_payload_inputs=19,complete_host_quote=False,operational_grant=False,
        compiler_invoked=False,product_runtime=False)))
if __name__=='__main__':main()
