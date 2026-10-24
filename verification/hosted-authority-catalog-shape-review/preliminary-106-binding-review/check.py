#!/usr/bin/env python3
"""Read-only independent review checker: no subprocess, server or file writes."""
import gzip,hashlib,importlib.util,json,os,pathlib,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];ATTEMPT=HERE/'attempt-1';PRODUCER=ROOT/'verification/hosted-authority-catalog-shape-correction'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):
    p=pathlib.Path(p)
    return gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes() if p.exists() else gzip.decompress(p.with_suffix(p.suffix+'.gz').read_bytes())
def js(p):return json.loads(read(p))
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def main():
    manifest=js(HERE/'artifact-manifest.json');seen=set()
    for e in manifest['files']:
        assert e['path'] not in seen;seen.add(e['path']);b=(ROOT/e['path']).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'],e['path']
    assert {str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p.name!='artifact-manifest.json'}=={p for p in seen if p.startswith(str(HERE.relative_to(ROOT))+'/') and not p.endswith('/artifact-manifest.json')}
    upstream=js(ATTEMPT/'inputs/artifact-manifest.json');assert len(upstream['files'])==277
    for e in upstream['files']:
        b=(ROOT/e['path']).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'],e['path']
    for e in js(ATTEMPT/'input-manifest.json'):
        b=(ATTEMPT/e['copy']).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'];assert b==(ROOT/e['path']).read_bytes()
    source=js(ATTEMPT/'source-manifest.json');assert sha(canonical(source).encode())=='7e2a24ec2aad45d07d2dd8a5d581fa8df5966e841981d20b27c75acd1de74b40'
    for e in source:
        b=(ATTEMPT/'candidate'/e['path']).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'];assert b==(PRODUCER/'candidate'/e['path']).read_bytes()==(ATTEMPT/'inputs/candidate'/e['path']).read_bytes()
    previous=ROOT/'verification/hosted-authority-catalog-correction/candidate'
    old=(previous/'inspector.py').read_text();wired=old.replace('import copy, hashlib, json, pathlib','import copy, hashlib, json, pathlib\nfrom raw_validation import validate_raw').replace('def normalize(raw):\n','def normalize(raw):\n    validate_raw(raw)\n')
    assert wired==(ATTEMPT/'candidate/inspector.py').read_text()
    for p in previous.rglob('*'):
        if p.is_file() and p.name!='inspector.py':assert p.read_bytes()==(ATTEMPT/'candidate'/p.relative_to(previous)).read_bytes()
    assert sha((ATTEMPT/'inputs/receipt.json').read_bytes())=='49ecbed394b965f68f50e242da0103005d3e86fee23a42955fc5530b982f2e22'
    expected=read(ATTEMPT/'inputs/selected-expected.json');assert sha(expected)=='78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e'
    receipt=js(ATTEMPT/'receipt.json');assert receipt['success'] and receipt['source_and_inputs_unchanged'];assert receipt['producer_check']['bindings']==277
    for e in js(ATTEMPT/'commands.json'):
        assert e['exit_code']==0 and sha(e['stdout'].encode())==e['stdout_sha256'] and sha(e['stderr'].encode())==e['stderr_sha256']
    for e in js(ATTEMPT/'compression.json'):
        b=(ATTEMPT/e['compressed']).read_bytes();raw=gzip.decompress(b);assert sha(b)==e['compressed_sha256'] and sha(raw)==e['sha256'] and len(raw)==e['bytes']
    for f,snapshot in [('run.py','executed-driver.py'),('extra-probes.py','executed-extra-probes.py'),('extra-runtime.py','executed-extra-runtime.py')]:assert (HERE/f).read_bytes()==(ATTEMPT/snapshot).read_bytes()
    os.environ['MIXER_SHAPE_PACKET']=str(ATTEMPT/'inputs')
    spec=importlib.util.spec_from_file_location('review_frozen_boundaries',ATTEMPT/'inputs/boundary-tests.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    recorded=js(ATTEMPT/'model-replay/receipt.json');fresh=module.execute()
    for k,v in fresh.items():assert canonical(v)==canonical(recorded[k]),k
    assert fresh['passed'];assert fresh['original_126']['rejected']==108 and fresh['original_126']['historical_21_now_rejected']==21 and fresh['original_126']['portable_18_admitted']==18
    assert [fresh[k]['total'] for k in ['original_126','added_whole_shape','strict_transport','selected_portability']]==[126,1083,8,3]
    extra=js(ATTEMPT/'extra-models.json');assert extra['passed'] and extra['total']==136 and all(e['passed'] for e in extra['cases']+extra['transport'])
    from inspector import decode,validate,normalize
    from raw_validation import validate_raw,GROUPS,SESSION_FIELDS
    audit=js(HERE/'domain-review.json');assert set(audit['enforcement'])==set(GROUPS)
    for g,fields in GROUPS.items():assert set(audit['enforcement'][g])==set(fields)
    assert set(audit['fresh_session'])==set(SESSION_FIELDS)
    runtime=js(ATTEMPT/'runtime/summary.json');assert runtime['total']==runtime['passed']==19 and not runtime['failed']
    safe_labels={'fresh actual runtime connection','internal FK trigger rename preserves selected semantics','same FK recreated with different actual OIDs','safe restoration','unrelated role and different-database defaults remain outside applicable scope','final safe restored state'};counts={'accepted':0,'rejected':0}
    for e in runtime['captures']:
        b=read(ATTEMPT/'runtime'/e['path']);assert sha(b)==e['raw_json_sha256'];ob=decode(b);assert ob['label']==e['label']
        assert canonical(normalize(ob['raw']))==canonical(ob['normalized'])
        if ob['label'] in safe_labels:validate(ob['raw'],decode(expected));counts['accepted']+=1
        else:
            try:validate(ob['raw'],decode(expected))
            except ValueError:counts['rejected']+=1
            else:raise AssertionError('drift admitted')
    assert counts=={'accepted':23,'rejected':15}
    tests=js(ATTEMPT/'runtime/tests.json')['tests'];pids=tests[0]['observation']['separate_fresh_runtime_pids'];assert len(pids)==len(set(pids))==3
    new=js(ATTEMPT/'extra-runtime/summary.json');assert new['total']==new['passed']==1 and not new['failed']
    raw=[]
    for e in new['captures']:
        b=read(ATTEMPT/'extra-runtime'/e['path']);assert sha(b)==e['sha256'];raw.append(decode(b)['raw'])
    for i in [0,3]:validate(raw[i],decode(expected))
    prior=decode(read(ATTEMPT/'inputs/inputs/verification/hosted-authority-catalog-review/attempt-2/independent/observations/001.json.gz'))['raw']
    assert raw[0]['enforcement']['relations'][0]['oid']!=prior['enforcement']['relations'][0]['oid']
    names=lambda x:sorted(t['name'] for t in x['enforcement']['triggers'] if t['internal'])
    assert names(raw[0])!=names(prior) and canonical(normalize(raw[0]))==canonical(normalize(prior))
    validate_raw(raw[1]);actual=next(r for r in raw[2]['enforcement']['startup_defaults'] if r['role']=='*');assert actual['role_oid']==17807>0 and actual['database_oid']==16384 and actual['config']==['application_name=review']
    try:validate_raw(raw[2])
    except ValueError as e:assert str(e)=='malformed raw value: startup_defaults[0] wildcard association role'
    else:raise AssertionError('finding reproduction absent')
    cleanup=receipt['cleanup'];assert cleanup['owned_cluster_stopped'] and cleanup['owned_scratch_removed'] and not pathlib.Path(receipt['scratch']).exists()
    assert not cleanup['tcp_listener_opened'] and not cleanup['other_processes_touched'] and not cleanup['native_or_phone_runs']
    review=js(HERE/'receipt.json');assert review['status']=='independent-review-frozen-with-ACSR01' and not review['root_acceptance'] and not review['ga_acceptance'] and not review['product_startup_inspector']
    print(json.dumps({'integrity':'passed','review_bindings':len(seen),'producer_bindings':277,'candidate_source_digest':receipt['source_digest'],'selected_manifest_unchanged':True,'fresh_models':[126,1083,8,3],'independent_extra_models':136,'fresh_actual_ordinary_cases':19,'fresh_safe_comparisons':23,'fresh_drift_rejections':15,'actual_domain_finding':'ACSR01 valid-unselected asterisk role falsely rejects','reused_actual_counts':[128,43,5,67],'one_owned_cluster_cleaned':True,'root_acceptance':False,'product_startup_inspector':False,'ga_acceptance':False},indent=2))
if __name__=='__main__':main()
