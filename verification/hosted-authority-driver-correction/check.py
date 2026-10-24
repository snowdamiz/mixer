#!/usr/bin/env python3
import hashlib,json,pathlib,tarfile
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
    seal=json.loads((HERE/'seal.json').read_text())
    for p,h in seal['bindings'].items():assert sha((ROOT/p).read_bytes())==h,p
    receipt=json.loads((HERE/'receipt.json').read_text())
    for p,h in receipt['bindings'].items():assert sha((ROOT/p).read_bytes())==h,p
    for n,expected in [(1,56),(2,17)]:
        p=HERE/f'run-{n}';r=json.loads((p/'receipt.json').read_text())
        assert r['success'] and r['driver_tests']=={'passed':expected,'total':expected}
        assert r['cleanup']['owned_cluster_stopped'] and r['cleanup']['owned_scratch_removed']
        for filename,sub in [('input-manifest.json','inputs'),('source-manifest.json','source')]:
            for item in json.loads((p/filename).read_text()):
                b=(p/sub/item['path']).read_bytes();assert len(b)==item['bytes'] and sha(b)==item['sha256']
        for c in json.loads((p/'commands.json').read_text()):assert sha((p/c['log']).read_bytes())==c['sha256']
        with tarfile.open(p/'dependencies.tar.gz') as archive:
            deps=json.loads((p/'dependency-manifest.json').read_text());assert len(deps)==len(archive.getmembers())
            for item in deps:
                b=archive.extractfile(item['path']).read();assert len(b)==item['bytes'] and sha(b)==item['sha256']
        for file in ['coordinator.ex','transport.ex']:
            assert (p/'source/probe/lib'/file).read_bytes()==(HERE/'probe/lib'/file).read_bytes()
        for file in ['schema.sql','functions.sql','catalog.sql','tests.py']:
            assert (p/'source'/file).read_bytes()==(HERE/'baseline/source'/file).read_bytes()
    s=json.loads((HERE/'run-1/original-suite/summary.json').read_text());assert s['passed']==s['total']==128
    x=json.loads((HERE/'run-2/driver-tests.json').read_text());assert all(t['passed'] for t in x['results'])
    obs=x['observations'];assert obs['equal_float_contract']['committed_effects']==0
    values=obs['equal_float_substitutions'];assert len(values)==8 and all(not v['accepted'] and v['loose_equal_original'] and not v['strict_equal_original'] for v in values)
    assert not obs['sensitive_ref']['telemetry_contains_raw'] and not obs['sensitive_ref']['retained_exception_contains_raw']
    before=(HERE/'baseline/source/probe/lib/coordinator.ex').read_text()
    assert before.replace('Process.get(@marker) != c','Process.get(@marker) !== c')==(HERE/'probe/lib/coordinator.ex').read_text()
    before=(HERE/'baseline/source/probe/lib/transport.ex').read_text()
    assert before.replace('def message(e), do: "authority driver rejected: #{e.reason}"','def message(_), do: "authority driver rejected"')==(HERE/'probe/lib/transport.ex').read_text()
    print(json.dumps({'verified':True,'bindings':len(receipt['bindings']),'originalDriver':56,'originalSchema':128,'regressions':17,'typeSubstitutionsRejected':8,'effectsForSubstitutions':0,'ownedRunsCleaned':2,'independentAcceptance':False}))
if __name__=='__main__':main()
