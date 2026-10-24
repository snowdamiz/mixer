#!/usr/bin/env python3
"""Read-only frozen packet checker. Starts no process, server or native tool."""
import copy, gzip, hashlib, importlib.util, json, pathlib, sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE/'candidate'))
from inspector import decode, canonical, normalize, validate
EXPECTED_SHA='78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(path):
    path=pathlib.Path(path)
    if path.suffix=='.gz':return gzip.decompress(path.read_bytes())
    return path.read_bytes() if path.exists() else gzip.decompress(path.with_suffix(path.suffix+'.gz').read_bytes())
def js(path):return decode(read(path))
def reject(raw,expected):
    try:validate(raw,expected)
    except ValueError:return
    raise AssertionError('unexpected admission')
def source_manifest(folder,digest):
    source=js(folder/'source-manifest.json');assert sha(canonical(source).encode())==digest
    actual=[]
    for entry in source:
        b=(folder/'source'/entry['path']).read_bytes();assert len(b)==entry['bytes'] and sha(b)==entry['sha256']
        actual.append(entry['path'])
        assert b==(HERE/'candidate'/entry['path']).read_bytes()
    assert set(actual)=={str(p.relative_to(folder/'source')) for p in (folder/'source').rglob('*') if p.is_file()}
def compressed(folder):
    for entry in js(folder/'compression.json'):
        b=(folder/entry['compressed']).read_bytes();raw=gzip.decompress(b)
        assert sha(b)==entry['compressed_sha256'] and sha(raw)==entry['sha256'] and len(raw)==entry['bytes']
def commands(entries):
    for rec in entries:
        if 'stdout' in rec:
            assert sha(rec['stdout'].encode())==rec['stdout_sha256']
            assert sha(rec['stderr'].encode())==rec['stderr_sha256']
        assert rec['exit_code']==0,rec['argv']
def main():
    m=js(HERE/'artifact-manifest.json');seen=set()
    for entry in m['files']:
        assert entry['path'] not in seen;seen.add(entry['path']);b=(ROOT/entry['path']).read_bytes()
        assert len(b)==entry['bytes'] and sha(b)==entry['sha256'],entry['path']
    actual={str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p!=HERE/'artifact-manifest.json'}
    assert actual=={p for p in seen if p.startswith(str(HERE.relative_to(ROOT))+'/')}
    receipt=js(HERE/'receipt.json');expected=js(HERE/'selected-expected.json')
    assert sha(read(HERE/'selected-expected.json'))==receipt['expected_manifest_sha256']==EXPECTED_SHA
    assert not receipt['root_acceptance'] and not receipt['ga_acceptance'] and not receipt['product_startup_inspector']
    for entry in js(HERE/'input-manifest.json'):
        b=read(HERE/entry['copy']);assert len(b)==entry['bytes'] and sha(b)==entry['sha256']
        assert b==(ROOT/entry['path']).read_bytes(),entry['path']
    upstream=ROOT/'verification/hosted-authority-catalog-correction/candidate'
    upstream_paths={str(p.relative_to(upstream)) for p in upstream.rglob('*') if p.is_file()}
    candidate_paths={str(p.relative_to(HERE/'candidate')) for p in (HERE/'candidate').rglob('*') if p.is_file()}
    assert candidate_paths==upstream_paths|{'raw_validation.py'}
    for path in upstream_paths-{'inspector.py'}:
        assert (upstream/path).read_bytes()==(HERE/'candidate'/path).read_bytes(),path
    old=(upstream/'inspector.py').read_text()
    wired=old.replace('import copy, hashlib, json, pathlib','import copy, hashlib, json, pathlib\nfrom raw_validation import validate_raw').replace('def normalize(raw):\n','def normalize(raw):\n    validate_raw(raw)\n')
    assert wired==(HERE/'candidate/inspector.py').read_text()
    delta=js(HERE/'delta-manifest.json');assert delta['modified']==['inspector.py'] and delta['added']==['raw_validation.py'] and not delta['removed']
    final=HERE/'attempt-1';r=js(final/'receipt.json');assert r['success'] and not r['selection']
    assert r['source_digest']==receipt['candidate_source_digest'];source_manifest(final,r['source_digest']);compressed(final)
    assert (HERE/'run.py').read_bytes()==(final/'driver.py').read_bytes()
    assert (HERE/'independent-runtime.py').read_bytes()==(final/'independent-runtime.py').read_bytes()
    commands(js(final/'commands.json'))
    cleanup=r['cleanup'];assert cleanup['owned_cluster_stopped'] and cleanup['owned_scratch_removed']
    assert not pathlib.Path(r['scratch']).exists() and not cleanup['tcp_listener_opened'] and not cleanup['other_processes_touched'] and not cleanup['native_or_phone_runs']
    assert read(final/'normalized-baseline.json')==read(HERE/'selected-expected.json')
    fresh=js(final/'raw-baseline.json');validate(fresh,expected)
    selected_source=HERE/'inputs/verification/hosted-authority-catalog-review/attempt-2/independent/observations/001.json.gz'
    prior=js(selected_source)['raw'];validate(prior,expected)
    names=lambda x:sorted(t['name'] for t in x['enforcement']['triggers'] if t['internal'])
    assert fresh['enforcement']['relations'][0]['oid']!=prior['enforcement']['relations'][0]['oid']
    assert names(fresh)!=names(prior) and canonical(normalize(fresh))==canonical(normalize(prior))
    for path,count in [('replay/summary.json',128),('review/adversarial/summary.json',48),('corrected/summary.json',67),('independent/summary.json',19)]:
        s=js(final/path);assert s['total']==s['passed']==count and not s['failed']
    old_tests=js(final/'review/adversarial/tests.json')['tests'];gaps=[t for t in old_tests if t['name'].startswith('FINDING ')]
    assert len(gaps)==5 and all(t['passed'] and t['observation']['producer_catalog_equal'] for t in gaps)
    corrected=js(final/'corrected/summary.json');counts={'accepted':0,'rejected':0}
    for entry in corrected['captures']:
        ob=js(final/'corrected'/entry['file']);raw=ob['raw']
        assert canonical(normalize(raw))==canonical(ob['normalized'])
        safe=entry['label'] in ['restored safe control','safe corrected baseline','comparator flag coverage'] or entry['label'].startswith('comparator transport control ')
        if safe:validate(raw,expected);counts['accepted']+=1
        else:reject(raw,expected);counts['rejected']+=1
    independent=js(final/'independent/summary.json');runtime_counts={'accepted':0,'rejected':0}
    safe_labels={'fresh actual runtime connection','internal FK trigger rename preserves selected semantics','same FK recreated with different actual OIDs','safe restoration','unrelated role and different-database defaults remain outside applicable scope','final safe restored state'}
    for entry in independent['captures']:
        b=read(final/'independent'/entry['path']);assert sha(b)==entry['raw_json_sha256'];ob=decode(b);raw=ob['raw']
        assert entry['label']==ob['label'] and canonical(normalize(raw))==canonical(ob['normalized'])
        if entry['label'] in safe_labels:validate(raw,expected);runtime_counts['accepted']+=1
        else:reject(raw,expected);runtime_counts['rejected']+=1
    assert runtime_counts=={'accepted':23,'rejected':15},runtime_counts
    tests=js(final/'independent/tests.json')['tests'];assert len(tests)==19 and all(t['passed'] for t in tests)
    pids=tests[0]['observation']['separate_fresh_runtime_pids'];assert len(pids)==len(set(pids))==3
    for name in ['internal generated trigger name may change without hiding enforcement','same FK recreated under new OIDs retains semantic identity','actual duplicate FK multiplicity rejects']:
        assert any(t['name']==name and t['passed'] for t in tests)
    boundary=HERE/'boundary-attempt-2';br=js(boundary/'receipt.json');assert br['success'] and br['source_unchanged_during_execution']
    assert br['source_digest']==r['source_digest'];source_manifest(boundary,br['source_digest']);commands([js(boundary/'command.json')])
    assert (boundary/'executed-boundary-tests.py').read_bytes()==(HERE/'boundary-tests.py').read_bytes()
    assert (boundary/'executed-driver.py').read_bytes()==(HERE/'run-boundaries.py').read_bytes()
    recorded=js(boundary/'results/receipt.json')
    spec=importlib.util.spec_from_file_location('frozen_shape_boundaries',HERE/'boundary-tests.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    current=module.execute()
    for key,value in current.items():assert canonical(value)==canonical(recorded[key]),key
    assert recorded['passed'] and recorded['original_126']['total']==recorded['original_126']['passed']==126
    assert recorded['original_126']['historical_21_now_rejected']==21 and recorded['original_126']['portable_18_admitted']==18
    assert recorded['added_whole_shape']['total']==recorded['added_whole_shape']['passed']==1083
    assert recorded['strict_transport']['total']==recorded['strict_transport']['passed']==8
    assert recorded['selected_portability']['total']==recorded['selected_portability']['passed']==3
    first=js(HERE/'boundary-attempt-1/receipt.json');assert first['passed'] and first['original_126']['passed']==126 and first['added_whole_shape']['passed']==1063
    source_manifest(HERE/'boundary-attempt-1',r['source_digest'])
    assert sha(read(HERE/'boundary-attempt-1/executed-boundary-tests.py'))==first['script_sha256']
    fields=js(HERE/'raw-field-domains.json')
    for entry in fields['platform_headers']:
        b=(HERE/entry['copy']).read_bytes();assert len(b)==entry['bytes'] and sha(b)==entry['sha256']
    compressed(HERE)
    print(json.dumps({'integrity':'passed','bindings':len(seen),'candidate_source_digest':r['source_digest'],'expected_manifest_unchanged':True,
        'actual_postgresql':{'original':128,'prior_controls':43,'historical_observations_not_security_passes':5,'catalog_corrections':67,'independent_ordinary_runtime':19,
                            'independent_safe_comparisons':runtime_counts['accepted'],'independent_drift_rejections':runtime_counts['rejected']},
        'raw_input_models':{'original_boundary':126,'prior_malformed_now_rejected':21,'OID_portability_admitted':18,'added_whole_shape':1083,'strict_transport':8,'selected_portability':3},
        'original_source_and_SQL_unchanged':True,'one_owned_cluster_cleaned':True,'root_acceptance':False,'product_startup_inspector':False,'ga_acceptance':False},indent=2))
if __name__=='__main__':main()
