#!/usr/bin/env python3
"""Read-only source/evidence integrity check; no services or tests are started."""
import hashlib, json, pathlib, tarfile
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
    seal=json.loads((HERE/'seal.json').read_text())
    for path,digest in seal['bindings'].items():assert sha((ROOT/path).read_bytes())==digest,path
    receipt=json.loads((HERE/'receipt.json').read_text())
    for path,digest in receipt['bindings'].items():assert sha((ROOT/path).read_bytes())==digest,path
    for number in range(1,6):
        out=HERE/f'run-{number}';r=json.loads((out/'receipt.json').read_text())
        assert r['cleanup']['ownedScratchRemoved']
        assert r['status']==('passed' if number==5 else 'failed')
        for command in r['commands']:assert sha((out/command['log']).read_bytes())==command['sha256']
        assert sha((out/'source.tar.gz').read_bytes())==r['sourceArchiveSHA256']
        with tarfile.open(out/'source.tar.gz') as archive:
            expected=json.loads((out/'tested-source.json').read_text())
            members=archive.getmembers();assert len(members)==len(expected)
            for member in members:
                assert member.isfile() and member.name in expected
                assert sha(archive.extractfile(member).read())==expected[member.name]
    r=json.loads((HERE/'run-5/receipt.json').read_text())
    for path,digest in receipt['overlay'].items():
        assert sha((HERE/'candidate'/path).read_bytes())==digest
        assert r['testedSource']['hosted/'+path]==digest
    full=json.loads((HERE/'run-5/full-hosted/receipt.json').read_text())
    assert full['status']=='passed' and all(full['cleanup'].values())
    assert full['inputs']==r['testedSource']
    assert 'Result: 104 passed, 2 skipped' in (HERE/'run-5/full-hosted/tests.log').read_text()
    assert 'Result: 11 passed' in (HERE/'run-5/command-08.log').read_text()
    vectors=json.loads((HERE/'candidate/test/fixtures/audit/coherent-vectors.json').read_text())
    assert len(vectors['cases'])==80 and sum(x['accepted'] for x in vectors['cases'])==10
    chains=json.loads((HERE/'candidate/test/fixtures/audit/retained-chains.json').read_text())['chains']
    assert len(chains)==6 and sum(len(x['rows']) for x in chains)==185
    print(json.dumps({'verified':True,'bindings':len(receipt['bindings']),'overlayFiles':len(receipt['overlay']),
        'focusedTests':11,'hostedPassed':104,'explicitLinuxOnlySkips':2,'capturedActualRows':185,
        'coherentHashVectors':80,'ownedAttemptsCleaned':5,'independentReviewPending':True,'liveIntegrated':False}))
if __name__=='__main__':main()
