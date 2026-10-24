#!/usr/bin/env python3
"""Read-only integrity check; successful gap reproduction is not acceptance."""
import hashlib,json,pathlib,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    manifest=json.loads((HERE/'artifact-manifest.json').read_text());seen=set()
    for ent in manifest['files']:
        assert ent['path'] not in seen;seen.add(ent['path'])
        b=(ROOT/ent['path']).read_bytes();assert len(b)==ent['bytes'] and sha(b)==ent['sha256'],ent['path']
    actual={str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p.name!='artifact-manifest.json'}
    expected={x for x in seen if x.startswith(str(HERE.relative_to(ROOT))+'/')};assert actual==expected,{'extra':sorted(actual-expected),'missing':sorted(expected-actual)}
    receipt=json.loads((HERE/'receipt.json').read_text());assert receipt['status']=='correction-required-before-final-contract-selection'
    replay=json.loads((HERE/'replay/summary.json').read_text());added=json.loads((HERE/'adversarial/summary.json').read_text())
    assert replay['total']==replay['passed']==128 and not replay['failed']
    assert added['total']==added['passed']==48 and not added['failed']
    final=json.loads((HERE/'execution-receipt.json').read_text());assert final['success']
    for p in [HERE/'execution-receipt.json',*(HERE/f'attempt-{i}/execution-receipt.json' for i in [1,2,3])]:
        run=json.loads(p.read_text());assert run['cleanup']['owned_cluster_stopped'] and run['cleanup']['owned_scratch_removed'];assert not pathlib.Path(run['scratch']).exists()
    assert json.loads((HERE/'replay/catalog.json').read_text())==json.loads((HERE/'upstream/producer-catalog.json').read_text())
    assert sha((ROOT/'docs/hosted-authority-schema-contract.md').read_bytes())==receipt['producer']['contract_sha256']
    assert sha((ROOT/'verification/hosted-authority-schema-contract/receipt.json').read_bytes())==receipt['producer']['receipt_sha256']
    assert receipt['product_implementation_accepted'] is False and receipt['ga_acceptance'] is False
    print(json.dumps({'integrity':'passed','bindings':len(seen),'frozen_replay':128,'reviewer_oracles':48,'gap_reproductions':5,'findings':['ASR01','ASR02','ASR03'],'recommendation':receipt['status'],'owned_cleanup':True},indent=2))
if __name__=='__main__':main()
