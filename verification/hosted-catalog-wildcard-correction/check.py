#!/usr/bin/env python3
"""Read-only packet checker: no subprocess, PostgreSQL, native tools or writes."""
import argparse,difflib,gzip,hashlib,importlib.util,json,os,pathlib,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
UPSTREAM='7e2a24ec2aad45d07d2dd8a5d581fa8df5966e841981d20b27c75acd1de74b40'
CANDIDATE='3760cbfe5bb28407ce58d678eef22b064a960126d659df031cf11007b789d6d8'
EXPECTED='78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):
    p=pathlib.Path(p);return gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
def js(p):return json.loads(read(p))
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def check_command(c,expected_exit=0):
    assert c['exit_code']==expected_exit,c.get('argv')
    assert sha(c['stdout'].encode())==c['stdout_sha256'] and sha(c['stderr'].encode())==c['stderr_sha256']
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');a=ap.parse_args();bindings=0
    if not a.preflight:
        seen=set()
        for e in js(HERE/'artifact-manifest.json')['files']:
            assert e['path'] not in seen;seen.add(e['path']);b=(ROOT/e['path']).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'],e['path']
        owned={str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p!=HERE/'artifact-manifest.json'}
        assert owned=={p for p in seen if p.startswith(str(HERE.relative_to(ROOT))+'/')};bindings=len(seen)
        c=js(HERE/'checker-preflight-command.json');check_command(c);assert c['script_sha256']==sha(pathlib.Path(__file__).read_bytes());assert json.loads(c['stdout'])['preflight']
    r=js(HERE/'receipt.json');assert r['status']=='correction-ready-for-independent-review'
    assert r['candidate_source_digest']==CANDIDATE and r['upstream_candidate_source_digest']==UPSTREAM
    assert not r['root_acceptance'] and not r['ga_acceptance'] and not r['product_startup_inspector'] and not r['independent_correction_review_accepted']
    assert sha((HERE/'inputs/producer/receipt.json').read_bytes())==r['producer_receipt_sha256']=='49ecbed394b965f68f50e242da0103005d3e86fee23a42955fc5530b982f2e22'
    assert sha((HERE/'inputs/review/receipt.json').read_bytes())==r['review_receipt_sha256']=='767f41af29131c12fdb19f72067b8ed535d271279a45324b25a0476095d0bc43'
    upstream_bindings={}
    for name,count in [('producer',277),('review',115)]:
        m=js(HERE/'inputs'/name/'artifact-manifest.json');assert len(m['files'])==count
        for e in m['files']:
            b=(ROOT/e['path']).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'],e['path']
        upstream_bindings[name]=count
    for e in js(HERE/'input-manifest.json'):
        b=(HERE/e['copy']).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'];assert b==(ROOT/e['path']).read_bytes(),e['path']
    source=js(HERE/'source-manifest.json');assert sha(canonical(source).encode())==CANDIDATE
    assert {e['path'] for e in source}=={str(p.relative_to(HERE/'candidate')) for p in (HERE/'candidate').rglob('*') if p.is_file()}
    oldsource=js(HERE/'inputs/producer/source-manifest.json');assert sha(canonical(oldsource).encode())==UPSTREAM
    for e in source:
        b=(HERE/'candidate'/e['path']).read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256']
        old=(ROOT/'verification/hosted-authority-catalog-shape-correction/candidate'/e['path']).read_bytes()
        if e['path']!='raw_validation.py':assert b==old,e['path']
        else:
            s=old.decode().replace('        seen_oids = set()\n','        seen_oids = set()\n        seen_trigger_names = set()\n')
            s=s.replace("            if group == 'triggers':\n","            if group == 'triggers':\n                key = (row['relation_oid'], row['name'])\n                if key in seen_trigger_names:\n                    reject(at + ' duplicate relation/name')\n                seen_trigger_names.add(key)\n")
            s=s.replace("if row[field] is None or (row[field + '_oid'] == 0) != (row[field] == '*'):","if row[field] is None or (row[field + '_oid'] == 0 and row[field] != '*'):")
            assert b==s.encode()
            diff=''.join(difflib.unified_diff(old.decode().splitlines(keepends=True),s.splitlines(keepends=True),fromfile='predecessor/raw_validation.py',tofile='candidate/raw_validation.py'))
            assert diff==(HERE/'implementation.diff').read_text()
    delta=js(HERE/'delta-manifest.json');assert delta['modified']==['raw_validation.py'] and not delta['added'] and not delta['removed'];assert delta['implementation_diff_sha256']==sha((HERE/'implementation.diff').read_bytes())
    assert sha((HERE/'selected-expected.json').read_bytes())==EXPECTED==r['expected_manifest_sha256']
    # Every script adaptation is byte-exact, preserves the frozen original, and
    # records whether it changes only a finding oracle or a harness path/label.
    for script,original,adaptations in [('replay-boundaries.py','inputs/producer/boundary-tests.py',js(HERE/'oracle-adaptations.json')),('replay-extra-probes.py','inputs/review/extra-probes.py',js(HERE/'oracle-adaptations.json')),('replay-name-uniqueness.py','inputs/review/name-uniqueness-probe.py',js(HERE/'uniqueness-adaptations.json'))]:
        old=(HERE/original).read_text();new=old
        for e in adaptations:
            if e.get('script',script)!=script:continue
            assert new.count(e['before'])==1;new=new.replace(e['before'],e['after'])
        assert new==(HERE/script).read_text()
        assert ''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile=original,tofile=script))==(HERE/(script+'.diff')).read_text()
    attempt=HERE/'attempt-1';ar=js(attempt/'receipt.json');assert ar['success'] and ar['source_inputs_and_scripts_unchanged'] and ar['source_digest']==CANDIDATE
    for name in ['run.py','runtime-tests.py','model-tests.py','replay-boundaries.py','replay-extra-probes.py']:assert (HERE/name).read_bytes()==(attempt/('executed-'+name)).read_bytes()
    for c in js(attempt/'commands.json.gz'):check_command(c)
    for e in js(attempt/'compression.json'):
        b=(attempt/e['compressed']).read_bytes();raw=gzip.decompress(b);assert sha(b)==e['compressed_sha256'] and sha(raw)==e['sha256'] and len(raw)==e['bytes']
    tools=js(attempt/'tool-manifest.json');assert '17.11' in tools['postgres']['version'] and '3.14.8' in tools['python3']['version']
    # A read-only replay of every original boundary model against this candidate.
    sys.path.insert(0,str(HERE/'candidate'));os.environ['MIXER_SHAPE_PACKET']=str(HERE)
    boundary=load_module('frozen_corrected_boundaries',HERE/'replay-boundaries.py').execute();recorded=js(attempt/'models/receipt.json')
    for k,v in boundary.items():assert canonical(v)==canonical(recorded[k]),k
    assert boundary['passed'] and [boundary[k]['total'] for k in ['original_126','added_whole_shape','strict_transport','selected_portability']]==[126,1083,8,3]
    assert boundary['original_126']['rejected']==108 and boundary['original_126']['historical_21_now_rejected']==21 and boundary['original_126']['portable_18_admitted']==18
    assert boundary['added_whole_shape']['raw_invalid_rejected']==1036 and boundary['added_whole_shape']['valid_unselected_raw_controls']==47
    # The independent probe has one output-only footer. Remove that exact footer
    # in memory so its full 136-case computation can replay without filesystem IO.
    p=HERE/'replay-extra-probes.py';code=p.read_text();footer="pathlib.Path(a.out).write_text(json.dumps(result,indent=2,ensure_ascii=True)+'\\n');print(json.dumps({k:v for k,v in result.items() if k not in ['cases','transport']},indent=2));sys.exit(0 if result['passed'] else 1)\n"
    assert code.endswith(footer);saved_argv=sys.argv
    try:
        sys.argv=[str(p),'--packet',str(HERE),'--out','unused-read-only'];namespace={'__file__':str(p),'__name__':'frozen_extra_models'};exec(compile(code[:-len(footer)],str(p),'exec'),namespace)
    finally:sys.argv=saved_argv
    extra=namespace['result'];assert canonical(extra)==canonical(js(attempt/'extra-models.json'));assert extra['passed'] and extra['total']==136
    focused=load_module('focused_wildcard_models',HERE/'model-tests.py').execute();assert canonical(focused)==canonical(js(attempt/'focused-models.json'));assert focused['passed'] and focused['total']==24
    unique=load_module('frozen_corrected_uniqueness',HERE/'replay-name-uniqueness.py').execute();assert canonical(unique)==canonical(js(HERE/'name-uniqueness-results.json'));assert unique['historical_malformed_now_rejected']==2 and unique['valid_portability_control']==1
    c=js(HERE/'uniqueness-command.json');check_command(c);assert c['script_sha256']==sha((HERE/'replay-name-uniqueness.py').read_bytes())
    from inspector import validate,normalize,decode
    from raw_validation import validate_raw
    expected=decode((HERE/'selected-expected.json').read_bytes());runtime=js(attempt/'runtime/summary.json');tests=js(attempt/'runtime/tests.json');assert runtime['total']==runtime['passed']==tests['total']==tests['passed']==5 and not runtime['failed']
    counts={'accepted':0,'rejected':0};raws=[]
    for e in runtime['captures']:
        b=read(attempt/'runtime'/e['path']);assert sha(b)==e['raw_json_sha256'] and len(b)==e['bytes'];ob=decode(b);assert ob['label']==e['label'];raw=ob['raw'];before=canonical(raw);validate_raw(raw)
        assert canonical(normalize(raw))==canonical(ob['normalized'])
        try:validate(raw,expected);admitted=True;error=None
        except ValueError as exc:admitted=False;error=str(exc)
        assert admitted==e['expected_selected_admission'] and canonical(raw)==before
        if admitted:assert error==e['selected_error']==None
        else:
            prefix='selected authority mismatch: ';assert error.startswith(prefix) and e['selected_error'].startswith(prefix)
            assert set(error[len(prefix):].split(','))==set(e['selected_error'][len(prefix):].split(','))
        counts['accepted' if admitted else 'rejected']+=1;raws.append(raw)
    assert counts=={'accepted':11,'rejected':7}
    actual=tests['tests'][1]['observation']['actual_startup_rows'];assert len(actual)==4
    assert actual[0]['database_oid']==0 and actual[0]['role_oid']>0 and actual[0]['role']==actual[0]['database']=='*'
    assert actual[1]['database_oid']>0 and actual[1]['role_oid']>0 and actual[1]['role']=='*'
    assert actual[2]['database_oid']>0 and actual[2]['role_oid']==0 and actual[2]['role']==actual[2]['database']=='*'
    assert actual[3]['database_oid']>0 and actual[3]['role_oid']>0 and actual[3]['role']==actual[3]['database']=='*'
    sql=js(attempt/'runtime/sql-commands.json.gz');errors=[e for e in sql if 'sqlstate' in e];assert len(errors)==3 and all(e['sqlstate']=='42710' for e in errors)
    probe=tests['tests'][3]['observation'];assert len(probe['actual_duplicate_name_rejections'])==3 and probe['portable_name_controls']==2
    prior=decode(read(HERE/'inputs/verification/hosted-authority-catalog-review/attempt-2/independent/observations/001.json.gz'))['raw'];names=lambda x:sorted(t['name'] for t in x['enforcement']['triggers'] if t['internal'])
    assert raws[0]['enforcement']['relations'][0]['oid']!=prior['enforcement']['relations'][0]['oid'] and names(raws[0])!=names(prior) and canonical(normalize(raws[0]))==canonical(normalize(prior))
    cleanup=ar['cleanup'];assert cleanup['owned_cluster_stopped'] and cleanup['owned_scratch_removed'] and not pathlib.Path(ar['scratch']).exists()
    assert not cleanup['tcp_listener_opened'] and not cleanup['other_processes_touched'] and not cleanup['native_or_phone_runs']
    failed=js(HERE/'checker-preflight-attempt-1/command.json');check_command(failed,1);assert failed['script_sha256']==sha((HERE/'checker-preflight-attempt-1/check.py').read_bytes())
    assert r['reused_not_freshly_rerun']=={'original_schema_cases':128,'prior_controls':43,'historical_findings_not_security_passes':5,'catalog_correction_cases':67,'ordinary_runtime_cases':19,'ordinary_safe_comparisons':23,'ordinary_drift_rejections':15}
    print(json.dumps({'integrity':'passed','preflight':a.preflight,'bindings':bindings,'upstream_bindings':upstream_bindings,'candidate_source_digest':CANDIDATE,'fresh_models':[126,1083,8,3],'independent_extra_models':136,'focused_models':24,'frozen_uniqueness_replay':{'required_rejections':2,'portable_control':1},'fresh_actual_runtime_cases':5,'safe_comparisons':11,'selected_drift_rejections':7,'actual_duplicate_trigger_SQLSTATE42710_rejections':3,'actual_trigger_name_portability_controls':2,'selected_manifest_and_SQL_unchanged':True,'one_owned_cluster_cleaned':True,'independent_correction_review_accepted':False,'root_acceptance':False,'ga_acceptance':False},indent=2))
if __name__=='__main__':main()
