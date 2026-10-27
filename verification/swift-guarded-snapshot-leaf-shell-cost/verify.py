#!/usr/bin/env python3
"""Read-only complete seal verification and deterministic pure controls."""
from pathlib import Path
import hashlib,json,sys,unittest
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
seal=json.loads((HERE/'seal.json').read_bytes())
paths={r['path'] for r in seal['members']}
actual={p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and p.name!='seal.json'}
if actual!=paths or len(paths)!=seal['member_count']:raise SystemExit('packet closure differs')
for row in seal['members']:
 p=HERE/row['path'];b=p.read_bytes()
 if p.is_symlink() or len(b)!=row['bytes'] or hashlib.sha256(b).hexdigest()!=row['sha256']:raise SystemExit('sealed member differs '+row['path'])
if sum(r['bytes'] for r in seal['members'])!=seal['total_bytes']:raise SystemExit('byte dimensions differ')
import test_cost
run=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(test_cost.LeafShellControls))
if not run.wasSuccessful():raise SystemExit(1)
print(json.dumps(dict(sealed_members=len(paths),sealed_bytes=seal['total_bytes'],pure_methods=run.testsRun,compiler=False,product_runtime=False,read_only=True)))
