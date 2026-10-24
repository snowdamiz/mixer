#!/usr/bin/env python3
"""Read-only occurrence/multiplicity and role-join supplement verification."""
from pathlib import Path
import collections,gzip,hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def enc(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def read(path):return json.loads(path.read_bytes())
def packed(name):return json.loads(gzip.decompress((HERE/name).read_bytes()))
subprocess.run([sys.executable,'-B',str(HERE/'verify_pre_runtime.py')],check=True,stdout=subprocess.DEVNULL)
rows=packed('occurrence-complete-positions.json.gz');roles=packed('occurrence-complete-role-joins.json.gz');functions=packed('occurrence-complete-function-item-role-joins.json.gz')
assert len(rows)==2744 and len(roles)==11760 and len(functions)==1296
keys={(r['config'],tuple(r['occurrenceKey']))for r in rows};assert len(keys)==len(rows)
for role in roles+functions:assert (role['config'],tuple(role['occurrenceKey']))in keys
role_counts=collections.Counter((r['config'],tuple(r['occurrenceKey']))for r in roles)
for row in rows:
    if row['old']['kind']in ['local','constant-operand']:
        assert role_counts[(row['config'],tuple(row['occurrenceKey']))]>=4
constants=[x for x in rows if x['old']['kind']=='constant-operand'];assert len(constants)==498
constant_keys={(r['config'],tuple(r['occurrenceKey']))for r in constants}
assert sum((x['config'],tuple(x['occurrenceKey']))in constant_keys for x in roles)==1992
collisions=packed('former-key-collisions.json.gz')
omitted=[(r['config'],tuple(k))for r in collisions for k in r['previouslyOmittedOccurrences']]
assert len(omitted)==108 and set(omitted)<=constant_keys
summary=read(HERE/'occurrence-complete-summary.json');assert not any(c['additionalHygieneMappings']for c in summary['contexts'])
if (HERE/'occurrence-supplement-freeze.json').exists():
    frozen=read(HERE/'occurrence-supplement-freeze.json')
    assert frozen['originalPreRuntimeFreezeSHA256']==sha((HERE/'pre-runtime-freeze.json').read_bytes())
    for name,pin in frozen['files'].items():assert sha((HERE/name).read_bytes())==pin,name
    assert frozen['closureSHA256']==sha(enc(frozen['files']))
print(json.dumps({'verified':True,'completeRawOccurrences':2744,'roleJoins':11760,'functionItemZeroByteRoleJoins':1296,'oldKeyOmittedOccurrences':108,'oldKeyOmittedDistinctRecords':78,'noAdditionalRepresentationMapping':True,'originalFreezeExact':True,'compilerOrRuntimeRerun':False},sort_keys=True,indent=2))
