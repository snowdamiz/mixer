#!/usr/bin/env python3
"""Select reviewed literals, never collect a runtime database oracle."""
import base64, hashlib, json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
B=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads((R/p).read_text())
accept=read('verification/hosted-browser-relation-representation-review/root-acceptance.json')
assert accept['status']=='accepted-local-PG16-PG17-representation-only'
matrix_path='verification/hosted-browser-relation-admission-contract/relation-matrix.json'
matrix=read(matrix_path)
review=read('verification/hosted-browser-relation-representation-review/receipt.json')
assert sha(R/'verification/hosted-browser-relation-representation-review/receipt.json')==accept['review_receipt_sha256']
capture='verification/hosted-browser-relation-representation-review/ordinary-source-capture.stdout'
assert sha(R/capture)==review['artifact_sha256'][capture]
functions={}
for line in (R/'verification/hosted-browser-relation-representation-review/ordinary-source-capture.stdout').read_text().splitlines():
    fields=line.split('\t')
    if fields[0]=='function_source': functions[fields[1]]=base64.b64decode(fields[2]).decode()
assert len(functions)==4
sources=read('verification/hosted-browser-relation-admission-contract/source-bindings.json')
# Bind only the accepted semantic closure, never mutable progress metadata.
paths=[p for p in sources if p.startswith('hosted/')]
for packet in accept['producer_packets']:
    receipt=read(packet['receipt'])
    assert sha(R/packet['receipt'])==packet['receipt_sha256']
    frozen_sources=read(str(Path(packet['receipt']).parent/'source-bindings.json'))
    for p in frozen_sources:
        if p.startswith('hosted/') and p not in paths: paths.append(p)
    for p in paths:
        if p in frozen_sources: assert sha(R/p)==frozen_sources[p],p
bindings={p:sha(R/p) for p in sorted(paths) if '/test/' not in p}
proof={'root_acceptance_sha256':sha(R/'verification/hosted-browser-relation-representation-review/root-acceptance.json'),'matrix_sha256':sha(R/matrix_path),'files':{}}
for packet in accept['producer_packets']:
    major=packet['major']; base=Path(packet['receipt']).parent
    oracle_path=str(base/'source-compiled-oracle.json')
    oracle=read(oracle_path)
    for name in ['source-compiled-oracle.json','clean-baseline.json']:
        assert sha(R/base/name)==read(packet['receipt'])['outputs_sha256'][name],name
    assert len(oracle['checks'])==80 and len(oracle['policies'])==32 and len(oracle['defaults'])==3 and len(oracle['predicates'])==1
    clean=read(str(base/'clean-baseline.json'))
    check_keys=[{'relation': ('public.'+c['relation'] if not c['relation'].startswith('public.') else c['relation']), 'expression':c['expression'],'columns':c['columns']} for c in clean['constraints'] if c['contype']=='c']
    assert sorted((c['relation'],c['expression']) for c in check_keys)==sorted((c['relation'],c['expression']) for c in oracle['checks'])
    data={'check_keys':check_keys,'schema':1,'major':int(major),'source_bindings':bindings,'structure':matrix,'expressions':oracle,'trigger_sources':functions,'reviewed_inputs':{'root_acceptance':proof['root_acceptance_sha256'],'matrix':proof['matrix_sha256'],'producer_receipt':packet['receipt_sha256'],'source_compiled_oracle':sha(R/oracle_path),'check_keys_clean_packet':sha(R/base/'clean-baseline.json'),'ordinary_source_capture':sha(R/'verification/hosted-browser-relation-representation-review/ordinary-source-capture.stdout')}}
    path=R/f'hosted/priv/browser_auth/relation_surface_v1_pg{major}.json'
    path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
    proof['files'][str(path.relative_to(R))]=sha(path)
(B/'manifest-derivation.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
print(json.dumps(proof,sort_keys=True))
