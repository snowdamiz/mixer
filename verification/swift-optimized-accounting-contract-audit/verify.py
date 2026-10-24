#!/usr/bin/env python3
"""Verify the bounded audit packet, not Mixer or any runtime gate."""
from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent
def j(n):return json.loads((P/n).read_text())
for r in j('input-bindings.json'):
 if 'snapshot' in r:
  assert hashlib.sha256((P/r['snapshot']).read_bytes()).hexdigest()==r['sha256'],r['path']
g=j('exact-private-inventory.json');assert len(g)==16 and sum(x['positionCount']for x in g)==704
assert all(len(x['positions'])==x['positionCount']for x in g)
assert all('mirEvidence'in r for x in g for r in x['positions']if r['position']=='source')
s=j('resolution-summary.json');assert sum(x['positions']for x in s if x['status'].startswith('residual'))==248
assert len(j('closure-substitutions.json'))==560
expected_success={'never_inferred','std_tls_optimized_locals','vec_optimized_locals','exact_inference_copy_bound','exact_four_role_classes','borrowed_factory_without_owner'}
rows=j('experiments/suite-summary.json');assert len(rows)==12
for r in rows:
 n=r['name'];case=P/'experiments'/n
 assert hashlib.sha256((case/(n+'.rs')).read_bytes()).hexdigest()==r['sourceSHA256']
 assert (r['exitCode']==0)==(n in expected_success),n
 assert not r['bootstrap']
 if r['exitCode']==0:
  assert r['executionExitCode']==0
  assert hashlib.sha256((case/'optimized.mir').read_bytes()).hexdigest()==r['mirSHA256']
m=(P/'experiments/exact_four_role_classes/optimized.mir').read_text()
assert 'roles_of_return::<!>'in m and 'roles_of_value::<fn() -> ! {never}>'in m
assert 'return_roles::<{closure@'in(P/'experiments/borrowed_factory_without_owner/optimized.mir').read_text()
assert j('experiments/suite-cleanup.json')['removed']
print('AUDIT_PACKET_VERIFIED: 12 bounded experiments; 704 private positions; 248 residual; 560 closure substitutions; no Mixer runtime/accounting acceptance')
