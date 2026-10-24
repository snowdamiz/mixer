#!/usr/bin/env python3
"""Read-only independent correction review checker; no subprocess or writes."""
import argparse,difflib,gzip,hashlib,importlib.util,json,pathlib,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];FROZEN=HERE/'frozen';PACKET=FROZEN/'verification/hosted-catalog-wildcard-correction';ATTEMPT=HERE/'attempt-1'
CANDIDATE='3760cbfe5bb28407ce58d678eef22b064a960126d659df031cf11007b789d6d8';RECEIPT='cc82538ba0709c831cf2b0579109a93cd419a972318fb84576e8ec03071d295f';EXPECTED='78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
def js(p):return json.loads(read(p))
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def command(c,code=0):
    assert c['exit_code']==code,c.get('argv');assert sha(c['stdout'].encode())==c['stdout_sha256'] and sha(c['stderr'].encode())==c['stderr_sha256']
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');args=ap.parse_args();bindings=0
    if not args.preflight:
        seen=set()
        for e in js(HERE/'artifact-manifest.json')['files']:
            assert e['path'] not in seen;seen.add(e['path']);b=(ROOT/e['path']).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'],e['path']
        owned={str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p!=HERE/'artifact-manifest.json'}
        assert owned=={p for p in seen if p.startswith(str(HERE.relative_to(ROOT))+'/')};bindings=len(seen)
        c=js(HERE/'checker-preflight-command.json');command(c);assert c['script_sha256']==sha(pathlib.Path(__file__).read_bytes()) and json.loads(c['stdout'])['preflight']
    inputs=js(HERE/'input-manifest.json');assert len(inputs)==101
    for e in inputs:
        b=(HERE/e['copy']).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'];assert b==(ROOT/e['path']).read_bytes(),e['path']
    correction_manifest=js(PACKET/'artifact-manifest.json');assert len(correction_manifest['files'])==96
    for e in correction_manifest['files']:
        b=(FROZEN/e['path']).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes']
    assert sha((PACKET/'receipt.json').read_bytes())==RECEIPT
    r=js(HERE/'receipt.json');assert r['status']=='independent-review-passed-ACSR01-ACSR02' and r['independent_review_passed']
    assert r['candidate_source_digest']==CANDIDATE and r['producer_receipt_sha256']==RECEIPT and r['findings']==[]
    assert not r['root_acceptance'] and not r['ga_acceptance'] and not r['product_startup_inspector']
    source=js(PACKET/'source-manifest.json');assert sha(canonical(source).encode())==CANDIDATE
    assert {e['path'] for e in source}=={str(p.relative_to(PACKET/'candidate')) for p in (PACKET/'candidate').rglob('*') if p.is_file()}
    for e in source:
        b=(PACKET/'candidate'/e['path']).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes']
        old=(ROOT/'verification/hosted-authority-catalog-shape-correction/candidate'/e['path']).read_bytes()
        if e['path']!='raw_validation.py':assert b==old,e['path']
        else:
            assert old==(FROZEN/'verification/hosted-authority-catalog-shape-correction/candidate/raw_validation.py').read_bytes()
            new=old.decode().replace('        seen_oids = set()\n','        seen_oids = set()\n        seen_trigger_names = set()\n')
            new=new.replace("            if group == 'triggers':\n","            if group == 'triggers':\n                key = (row['relation_oid'], row['name'])\n                if key in seen_trigger_names:\n                    reject(at + ' duplicate relation/name')\n                seen_trigger_names.add(key)\n")
            new=new.replace("if row[field] is None or (row[field + '_oid'] == 0) != (row[field] == '*'):","if row[field] is None or (row[field + '_oid'] == 0 and row[field] != '*'):")
            assert b==new.encode();assert ''.join(difflib.unified_diff(old.decode().splitlines(keepends=True),new.splitlines(keepends=True),fromfile='predecessor/raw_validation.py',tofile='candidate/raw_validation.py'))==(PACKET/'implementation.diff').read_text()
    assert sha((PACKET/'selected-expected.json').read_bytes())==EXPECTED
    assert (PACKET/'selected-expected.json').read_bytes()==(PACKET/'inputs/producer/selected-expected.json').read_bytes()==(PACKET/'inputs/selected-expected.json').read_bytes()
    for name,count in [('producer',277),('review',115)]:
        manifest=js(PACKET/'inputs'/name/'artifact-manifest.json');assert len(manifest['files'])==count
        for e in manifest['files']:
            b=(ROOT/e['path']).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'],e['path']
    # Every correction oracle adaptation has an exact diff and frozen original.
    for script,original,changes in [('replay-boundaries.py','inputs/producer/boundary-tests.py',js(PACKET/'oracle-adaptations.json')),('replay-extra-probes.py','inputs/review/extra-probes.py',js(PACKET/'oracle-adaptations.json')),('replay-name-uniqueness.py','inputs/review/name-uniqueness-probe.py',js(PACKET/'uniqueness-adaptations.json'))]:
        old=(PACKET/original).read_text();new=old
        for e in changes:
            if e.get('script',script)!=script:continue
            assert new.count(e['before'])==1;new=new.replace(e['before'],e['after'])
        assert new==(PACKET/script).read_text()
        assert ''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile=original,tofile=script))==(PACKET/(script+'.diff')).read_text()
    ar=js(ATTEMPT/'receipt.json');assert ar['success'] and ar['source_and_inputs_unchanged'] and ar['candidate_source_digest']==CANDIDATE and ar['producer_receipt_sha256']==RECEIPT and ar['oid_padding_tables']==131
    assert ar['hosted-catalog-wildcard-correction']['bindings']==96 and ar['hosted-authority-catalog-shape-correction']['bindings']==277 and ar['hosted-authority-catalog-shape-review']['review_bindings']==115
    assert sha((ATTEMPT/'receipt.json').read_bytes())==r['attempt_receipt_sha256']
    commands=js(ATTEMPT/'commands.json.gz')
    for c in commands:command(c)
    assert len([c for c in commands if c['argv'][0]=='initdb'])==1 and len([c for c in commands if c['argv'][0]=='createdb'])==2
    for e in js(ATTEMPT/'compression.json'):
        b=(ATTEMPT/e['compressed']).read_bytes();raw=gzip.decompress(b);assert sha(b)==e['compressed_sha256'] and sha(raw)==e['sha256'] and len(raw)==e['bytes']
    for name in ['prepare.py','run.py','model-review.py']:assert (HERE/name).read_bytes()==(ATTEMPT/('executed-'+name)).read_bytes()
    assert (ATTEMPT/'executed-runtime-tests.py').read_bytes()==(PACKET/'runtime-tests.py').read_bytes()
    tools=js(ATTEMPT/'tool-manifest.json');assert '17.11' in tools['postgres']['version'] and '3.14.8' in tools['python3']['version']
    # Independently recompute the original oracles and new targeted models.
    model=load('independent_domain_models',HERE/'model-review.py').execute();assert canonical(model)==canonical(js(ATTEMPT/'model-review.json'))
    assert model['all_passed'] and model['independent_total']==133 and len(model['predecessor_negative_controls'])==4
    fm=model['frozen_oracles'];assert [fm[k]['total'] for k in ['original_126','added_whole_shape','strict_transport','selected_portability']]==[126,1083,8,3]
    assert fm['original_126']['rejected']==108 and fm['original_126']['historical_21_now_rejected']==21 and fm['original_126']['portable_18_admitted']==18
    assert fm['added_whole_shape']['raw_invalid_rejected']==1036 and fm['added_whole_shape']['valid_unselected_raw_controls']==47
    assert fm['independent_extra_total']==136 and fm['focused_total']==24 and fm['uniqueness']['historical_malformed_now_rejected']==2 and fm['uniqueness']['valid_portability_control']==1
    from inspector import decode,validate,normalize
    from raw_validation import validate_raw
    expected=decode((PACKET/'selected-expected.json').read_bytes());runtime=js(ATTEMPT/'runtime/summary.json');tests=js(ATTEMPT/'runtime/tests.json');assert runtime['total']==runtime['passed']==tests['total']==tests['passed']==5 and not runtime['failed']
    counts={'accepted':0,'rejected':0};raws=[]
    for e in runtime['captures']:
        b=read(ATTEMPT/'runtime'/e['path']);assert sha(b)==e['raw_json_sha256'] and len(b)==e['bytes'];ob=decode(b);assert ob['label']==e['label'];raw=ob['raw'];before=canonical(raw);validate_raw(raw)
        assert canonical(normalize(raw))==canonical(ob['normalized'])
        try:validate(raw,expected);admitted=True;error=None
        except ValueError as exc:admitted=False;error=str(exc)
        assert admitted==e['expected_selected_admission'] and canonical(raw)==before
        if admitted:assert error==e['selected_error']==None
        else:
            prefix='selected authority mismatch: ';assert error.startswith(prefix) and e['selected_error'].startswith(prefix);assert set(error[len(prefix):].split(','))==set(e['selected_error'][len(prefix):].split(','))
        counts['accepted' if admitted else 'rejected']+=1;raws.append(raw)
    assert counts=={'accepted':11,'rejected':7} and len(raws)==18
    actual=tests['tests'][1]['observation']['actual_startup_rows'];assert len(actual)==4
    assert [(e['database_oid']>0,e['role_oid']>0) for e in actual]==[(False,True),(True,True),(True,False),(True,True)]
    assert actual[0]['database']==actual[0]['role']=='*' and actual[1]['role']=='*' and actual[1]['database']=='authority_contract' and actual[2]['database']==actual[2]['role']==actual[3]['database']==actual[3]['role']=='*'
    assert {e['role_oid'] for e in actual if e['role_oid']}=={17096} and {e['database_oid'] for e in actual if e['database']=='*' and e['database_oid']}=={17095}
    sql=js(ATTEMPT/'runtime/sql-commands.json.gz');errors=[e for e in sql if 'sqlstate' in e];assert len(errors)==3 and all(e['sqlstate']=='42710' for e in errors)
    assert ['ALTER TRIGGER' in e['sql'] for e in errors]==[True,True,False] and errors[2]['sql'].startswith('CREATE TRIGGER lifecycle_guard')
    assert any('CREATE ROLE "*" NOLOGIN' in e['sql'] for e in sql) and any('ALTER DATABASE "*" SET application_name' in e['sql'] for e in sql)
    trigger=tests['tests'][3]['observation'];assert trigger['portable_name_controls']==2 and len(trigger['actual_duplicate_name_rejections'])==3
    prior=decode(read(PACKET/'attempt-1/runtime/001.json.gz'))['raw'];names=lambda r:sorted(t['name'] for t in r['enforcement']['triggers'] if t['internal'])
    assert raws[0]['enforcement']['relations'][0]['oid']!=prior['enforcement']['relations'][0]['oid'] and names(raws[0])!=names(prior) and canonical(normalize(raws[0]))==canonical(normalize(prior))==canonical(expected)
    cleanup=ar['cleanup'];assert cleanup['owned_cluster_stopped'] and cleanup['owned_scratch_removed'] and not pathlib.Path(ar['scratch']).exists()
    assert not cleanup['tcp_listener_opened'] and not cleanup['other_processes_touched'] and not cleanup['native_or_phone_runs']
    # Retain the producer's one historical checker-preflight failure separately.
    command(js(PACKET/'checker-preflight-attempt-1/command.json'),1)
    assert r['review_execution_failures']==r['discarded_attempts']==0 and r['retained_historical_correction_checker_failures']==1
    assert r['reused_not_freshly_rerun']=={'original_schema_cases':128,'prior_controls':43,'historical_findings_not_security_passes':5,'catalog_correction_cases':67,'ordinary_runtime_cases':19,'ordinary_safe_comparisons':23,'ordinary_drift_rejections':15}
    print(json.dumps({'integrity':'passed','preflight':args.preflight,'review_bindings':bindings,'producer_bindings':96,'upstream_bindings':[277,115],'candidate_source_digest':CANDIDATE,'all_original_model_oracles_replayed':True,'original_model_counts':[126,1083,8,3,136,24,3],'new_independent_models':133,'preserved_negative_controls':4,'fresh_targeted_postgresql_cases':5,'fresh_safe_comparisons':11,'fresh_selected_rejections':7,'actual_duplicate_name_SQLSTATE42710_rejections':3,'actual_name_portability_controls':2,'SQL_normalization_comparator_selected_manifest_unchanged':True,'independent_review_passed':True,'findings':[],'one_owned_cluster_cleaned':True,'root_acceptance':False,'product_startup_inspector':False,'ga_acceptance':False},indent=2))
if __name__=='__main__':main()
