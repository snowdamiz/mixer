#!/usr/bin/env python3
"""Read-only frozen independent review checker; starts and changes nothing."""
import copy,gzip,hashlib,json,pathlib,subprocess,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE/'attempt-2/source'))
from inspector import validate,normalize,decode,canonical
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):
    p=pathlib.Path(p)
    return p.read_bytes() if p.exists() else gzip.decompress(p.with_suffix(p.suffix+'.gz').read_bytes())
def js(p):return decode(read(p))
def rejected(raw,expected):
    try:validate(raw,expected)
    except ValueError:return
    raise AssertionError('unexpected selected admission')
def main():
    manifest=js(HERE/'artifact-manifest.json');seen=set()
    for entry in manifest['files']:
        path=entry['path'];assert path not in seen;seen.add(path);b=(ROOT/path).read_bytes()
        assert len(b)==entry['bytes'] and sha(b)==entry['sha256'],path
    actual={str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p!=HERE/'artifact-manifest.json'}
    expected_paths={p for p in seen if p.startswith(str(HERE.relative_to(ROOT))+'/')}
    assert actual==expected_paths,{'extra':sorted(actual-expected_paths),'missing':sorted(expected_paths-actual)}
    receipt=js(HERE/'receipt.json');assert receipt['recommendation']=='correction-required-before-final-contract-selection'
    assert receipt['findings']==['ACR01'] and not receipt['root_acceptance'] and not receipt['ga_acceptance']
    cleanups=[]
    for name,success,passed in [('attempt-1',False,20),('attempt-2',True,21)]:
        folder=HERE/name;r=js(folder/'receipt.json');assert r['success']==success
        assert r['candidate_source_digest']=='8448b889f9050f9f160b8982bc929e1eacb5ca0c522cd3c7358404b331c987a0'
        for entry in js(folder/'input-manifest.json'):
            b=read(HERE/entry['copy']);assert len(b)==entry['bytes'] and sha(b)==entry['sha256']
            assert b==(ROOT/entry['path']).read_bytes(),entry['path']
        sm=js(folder/'source-manifest.json');assert sha(canonical(sm).encode())==r['candidate_source_digest']
        for ent in sm:
            b=(folder/'source'/ent['path']).read_bytes();assert len(b)==ent['bytes'] and sha(b)==ent['sha256']
        for cleanup_receipt in [r,js(folder/'fresh-replay/receipt.json')]:
            cleanup=cleanup_receipt['cleanup'];assert cleanup['owned_cluster_stopped'] and cleanup['owned_scratch_removed']
            assert not pathlib.Path(cleanup_receipt['scratch']).exists();assert not cleanup['tcp_listener_opened'];cleanups.append(cleanup)
        replay=folder/'fresh-replay'
        for sub,count in [('replay/summary.json',128),('review/adversarial/summary.json',48),('corrected/summary.json',67)]:
            s=js(replay/sub);assert s['total']==s['passed']==count and not s['failed']
        s=js(folder/'independent/summary.json');assert s['total']==21 and s['passed']==passed
        tests=js(folder/'independent/tests.json')['tests']
        if not success:
            failures=[t for t in tests if not t['passed']];assert len(failures)==1
            assert failures[0]['name']=='unrelated defaults do not contaminate applicable selection'
            assert '25001' in failures[0]['error'] and 'CREATE DATABASE' in failures[0]['error']
        else:assert not s['failed']
    source=HERE/'attempt-2/source';assert (HERE/'adversarial.py').read_bytes()==(HERE/'attempt-2/executed-adversarial.py').read_bytes()
    assert (HERE/'run.py').read_bytes()==(HERE/'attempt-2/executed-driver.py').read_bytes()
    expected=js(HERE/'attempt-2/inputs/verification/hosted-authority-catalog-correction/selected-expected.json')
    assert sha(read(HERE/'attempt-2/inputs/verification/hosted-authority-catalog-correction/selected-expected.json'))=='78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e'
    final=HERE/'attempt-2';s=js(final/'independent/summary.json');counts={'safe':0,'actual_rejections':0,'model_rejections':0,'malformed_admissions':0}
    safe_labels={'fresh actual runtime connection','internal FK trigger rename preserves selected semantics','same FK recreated with different actual OIDs','safe restoration','unrelated role and different-database defaults remain outside applicable scope','raw comparator model source','strict transport rejection source','final safe restored state'}
    for entry in s['captures']:
        b=gzip.decompress((final/'independent'/entry['path']).read_bytes());assert sha(b)==entry['raw_json_sha256'];ob=decode(b);raw=ob['raw'];label=entry['label'];assert label==ob['label']
        if 'normalized' in ob:assert canonical(normalize(raw))==canonical(ob['normalized'])
        if label in safe_labels:validate(raw,expected);counts['safe']+=1
        elif label.startswith('malformed ignored raw field '):validate(raw,expected);counts['malformed_admissions']+=1
        elif label.startswith('strict negative '):rejected(raw,expected);counts['model_rejections']+=1
        else:rejected(raw,expected);counts['actual_rejections']+=1
    assert counts=={'safe':25,'actual_rejections':15,'model_rejections':8,'malformed_admissions':10},counts
    fresh=js(final/'fresh-replay/raw-baseline.json')
    independent=decode(gzip.decompress((final/'independent/observations/001.json.gz').read_bytes()))['raw']
    validate(fresh,expected);validate(independent,expected)
    assert fresh['enforcement']['relations'][0]['oid']!=independent['enforcement']['relations'][0]['oid']
    names=lambda r:sorted(t['name'] for t in r['enforcement']['triggers'] if t['internal'])
    assert names(fresh)!=names(independent)
    domain=js(final/'domain-probes.json');assert domain['total']==126 and domain['admitted_malformed']==21 and domain['rejected']==87 and domain['valid_uint32_OID_portability_controls']==18
    assert domain['script_sha256']==sha((HERE/'domain-probes.py').read_bytes())
    for c in domain['cases']:
        raw=copy.deepcopy(independent);rows=raw['enforcement'][c['group']]
        if c['label']=='required nonempty internal text':row=next(r for r in rows if r['internal'])
        elif c['label']=='nonzero trigger association OID':row=next(r for r in rows if r['internal'] and bool(r[c['field']]))
        else:row=rows[0]
        row[c['field']]=c['value']
        if c['admitted']:validate(raw,expected)
        else:rejected(raw,expected)
        assert c['contract_gap']==(c['admitted'] and not c['domain_valid'])
    fields=js(HERE/'raw-field-domains.json');assert set(fields['enforcement_groups'])==set(independent['enforcement'])
    for group,rows in independent['enforcement'].items():
        if rows:assert set(fields['enforcement_groups'][group])==set(rows[0]),group
    assert set(fields['fresh_session'])==set(independent['fresh_session'])
    for entry in fields['platform_headers']:
        b=(HERE/entry['copy']).read_bytes();assert sha(b)==entry['sha256'] and len(b)==entry['bytes']
    for entry in js(HERE/'compression.json'):
        b=(HERE/entry['compressed']).read_bytes();decoded=gzip.decompress(b)
        assert sha(b)==entry['compressed_sha256'] and sha(decoded)==entry['sha256'] and len(decoded)==entry['bytes']
    p=subprocess.run(['python3','-B',ROOT/'verification/hosted-authority-catalog-correction/check.py'],cwd=ROOT,capture_output=True,text=True)
    assert p.returncode==0,p.stderr;upstream=decode(p.stdout);assert upstream['bindings']==789
    print(json.dumps({'integrity':'passed','bindings':len(seen),'producer_bindings':789,'fresh_replay':{'original':128,'prior_controls':43,'historical_gap_reproductions_not_security_passes':5,'correction':67},'independent_observations':21,'actual_runtime_cases':19,'actual_drift_rejections':15,'safe_capture_comparisons':25,'model_negative_rejections':8,'initial_malformed_admissions':10,'boundary_cases':126,'boundary_malformed_admissions':21,'finding':'ACR01','recommendation':receipt['recommendation'],'all_four_owned_clusters_cleaned':len(cleanups)==4,'product_startup_inspector':False,'root_acceptance':False,'ga_acceptance':False},indent=2))
if __name__=='__main__':main()
