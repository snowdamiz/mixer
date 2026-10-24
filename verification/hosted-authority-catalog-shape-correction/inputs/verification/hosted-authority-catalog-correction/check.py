#!/usr/bin/env python3
"""Read-only integrity/selection checker; boots nothing and writes nothing."""
import copy,gzip,hashlib,json,pathlib,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE/'candidate'))
from inspector import normalize,validate,canonical,decode
def sha(b):return hashlib.sha256(b).hexdigest()
def read(path):
    path=pathlib.Path(path)
    return path.read_bytes() if path.exists() else gzip.decompress(path.with_suffix(path.suffix+'.gz').read_bytes())
def js(path):return decode(read(path))
def reject(raw,expected):
    try:validate(raw,expected)
    except ValueError:return
    raise AssertionError('expected fail-closed rejection')
def main():
    m=js(HERE/'artifact-manifest.json');seen=set()
    for ent in m['files']:
        assert ent['path'] not in seen;seen.add(ent['path']);b=(ROOT/ent['path']).read_bytes()
        assert len(b)==ent['bytes'] and sha(b)==ent['sha256'],ent['path']
    actual={str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p!=HERE/'artifact-manifest.json'}
    expected_paths={p for p in seen if p.startswith(str(HERE.relative_to(ROOT))+'/')}
    assert actual==expected_paths,{'extra':sorted(actual-expected_paths),'missing':sorted(expected_paths-actual)}
    receipt=js(HERE/'receipt.json');expected=js(HERE/'selected-expected.json')
    assert sha((HERE/'selected-expected.json').read_bytes())==receipt['expected_manifest_sha256']=='78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e'
    for ent in js(HERE/'input-manifest.json'):
        assert read(HERE/ent['copy'])==read(ROOT/ent['path'])
        assert sha(read(HERE/ent['copy']))==ent['sha256']
    frozen=HERE/'candidate/frozen'
    for ent in js(HERE/'upstream/producer-source-manifest.json'):
        assert sha((frozen/pathlib.Path(ent['path']).name).read_bytes())==ent['sha256']
    assert (frozen/'reviewer.py').read_bytes()==(ROOT/'verification/hosted-authority-schema-review/adversarial.py').read_bytes()
    assert js(HERE/'upstream/producer-receipt.json')['source_digest']=='ebaae05f782695d3cd9d1fcedc535f0b47cdb736167384b7dc6d8a09fa16b0de'
    for entry in receipt['attempts']:
        folder=HERE/entry['path'];r=js(folder/'receipt.json');assert r['success']==entry['success']
        assert r['cleanup']['owned_cluster_stopped'] and r['cleanup']['owned_scratch_removed'] and not pathlib.Path(r['scratch']).exists()
        assert not r['cleanup']['tcp_listener_opened'] and not r['cleanup']['other_processes_touched'] and not r['cleanup']['native_or_phone_runs']
        source=js(folder/'source-manifest.json');assert sha(canonical(source).encode())==r['source_digest']
        for ent in source:
            b=(folder/'source'/ent['path']).read_bytes();assert len(b)==ent['bytes'] and sha(b)==ent['sha256']
        for ent in js(folder/'compression.json'):
            b=(folder/ent['compressed']).read_bytes();raw=gzip.decompress(b)
            assert sha(b)==ent['compressed_sha256'] and sha(raw)==ent['sha256'] and len(raw)==ent['bytes']
        if (folder/'normalized-baseline.json').exists() or (folder/'normalized-baseline.json.gz').exists():
            assert read(folder/'normalized-baseline.json')==(HERE/'selected-expected.json').read_bytes()
            validate(js(folder/'raw-baseline.json'),expected)
        if 'driver_sha256' in r:assert sha((folder/'driver.py').read_bytes())==r['driver_sha256']
    final=HERE/receipt['final_run'];r=js(final/'receipt.json');assert r['success']
    assert r['source_digest']==receipt['candidate_source_digest']
    for ent in js(final/'source-manifest.json'):
        assert (HERE/'candidate'/ent['path']).read_bytes()==(final/'source'/ent['path']).read_bytes()
    assert (final/'driver.py').read_bytes()==(HERE/'run.py').read_bytes()
    replay=js(final/'replay/summary.json');review=js(final/'review/adversarial/summary.json');corrected=js(final/'corrected/summary.json')
    assert replay['passed']==replay['total']==128 and not replay['failed']
    assert review['passed']==review['total']==48 and not review['failed']
    review_tests=js(final/'review/adversarial/tests.json')['tests']
    gaps=[t for t in review_tests if t['name'].startswith('FINDING ')];assert len(gaps)==5
    assert all(t['observation']['producer_catalog_equal'] for t in gaps)
    assert corrected['passed']==corrected['total']==receipt['correction_cases']==67 and not corrected['failed']
    assert corrected['skipped']==corrected['excluded']==0
    correction_tests=js(final/'corrected/tests.json')['tests']
    corrected_gaps=[t for t in correction_tests if t['name'].startswith('corrected historical gap ') or t['name']=='corrected parameter ASR03 direct dangerous SET']
    assert len(corrected_gaps)==5 and all(t['passed'] and t['observation']['corrected_rejected'] for t in corrected_gaps)
    alter_system=[t for t in correction_tests if t['name'] in ['corrected parameter direct ALTER SYSTEM','corrected parameter PUBLIC ALTER SYSTEM','corrected parameter reachable ALTER SYSTEM']]
    assert len(alter_system)==3 and all(t['observation']['actual_runtime_ALTER_SYSTEM_and_reset'] for t in alter_system)
    invalid=next(t for t in correction_tests if t['name']=='corrected invalid unready required index via ordinary concurrent DDL')['observation']
    assert invalid['same_required_index_identity_and_definition'] and not invalid['valid'] and not invalid['ready'] and invalid['live']
    immediate=next(t for t in correction_tests if t['name']=='corrected non-immediate unique index via ordinary DDL')['observation']
    assert immediate['witness']['actual_immediate_false']
    rejected_captures=accepted_captures=0
    for entry in corrected['captures']:
        ob=js(final/'corrected'/entry['file']);raw=ob['raw'];assert canonical(normalize(raw))==canonical(ob['normalized'])
        safe=entry['label'] in ['restored safe control','safe corrected baseline','comparator flag coverage'] or entry['label'].startswith('comparator transport control ')
        if safe:validate(raw,expected);accepted_captures+=1
        else:reject(raw,expected);rejected_captures+=1
    # Portable identities must actually survive changed cluster OIDs/names.
    selected=js(HERE/'selection-2/raw-baseline.json');fresh=js(final/'raw-baseline.json')
    assert selected['enforcement']['relations'][0]['oid']!=fresh['enforcement']['relations'][0]['oid']
    names=lambda x:sorted(t['name'] for t in x['enforcement']['triggers'] if t['internal'])
    assert names(selected)!=names(fresh)
    assert canonical(normalize(selected))==canonical(normalize(fresh))
    # Entrypoint remains executable and rejects malformed shape/multiplicity.
    for group in ['relations','constraints','indexes','triggers','parameter_effective','parameter_public','role_config']:
        raw=copy.deepcopy(fresh);raw['enforcement'][group].pop();reject(raw,expected)
    raw=copy.deepcopy(fresh);t=copy.deepcopy(next(t for t in raw['enforcement']['triggers'] if t['internal']));t['oid']+=100000;raw['enforcement']['triggers'].append(t);reject(raw,expected)
    for text in ['{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}','{"x":']:
        try:decode(text)
        except ValueError:continue
        raise AssertionError('malformed JSON admitted')
    print(json.dumps({'integrity':'passed','bindings':len(seen),'producer_replay':128,'review_controls':43,'historical_gap_observations':5,'gap_observations_are_not_security_passes':True,'correction_cases':corrected['passed'],'actual_catalog_rejections':rejected_captures,'safe_catalog_comparisons':accepted_captures,'fresh_cluster_stability':True,'all_owned_cleanup':True,'root_acceptance':False,'product_startup_inspector':False},indent=2))
if __name__=='__main__':main()
