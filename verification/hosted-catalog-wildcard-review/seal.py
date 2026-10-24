#!/usr/bin/env python3
"""Freeze a self-checking review packet without changing its producer."""
import datetime,hashlib,json,pathlib,subprocess,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];ATTEMPT=HERE/'attempt-1'
def sha(b):return hashlib.sha256(b).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def js(p):return json.loads(p.read_bytes())
ar=js(ATTEMPT/'receipt.json');assert ar['success'] and ar['source_and_inputs_unchanged']
model=js(ATTEMPT/'model-review.json');assert model['all_passed']
runtime=js(ATTEMPT/'runtime/summary.json');assert runtime['total']==runtime['passed']==5
receipt={'schema':1,'status':'independent-review-passed-ACSR01-ACSR02','observed_utc':utc(),'candidate_source_digest':ar['candidate_source_digest'],'producer_receipt_sha256':ar['producer_receipt_sha256'],'expected_manifest_sha256':'78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e','attempt':'attempt-1','attempt_receipt_sha256':sha((ATTEMPT/'receipt.json').read_bytes()),'head':ar['head'],'tree':ar['tree'],'platform':ar['platform'],'input_archive_files':101,'producer_bindings':96,'upstream_bindings':[277,115],'fresh_models':{'original_boundary':126,'added_shape':1083,'transport':8,'selected_portability':3,'independent_extra':136,'focused':24,'frozen_uniqueness_replay':3,'new_independent':133,'predecessor_negative_controls':4},'fresh_actual_postgresql':{'clusters':1,'databases':2,'postgres_version':'17.11','oid_padding_tables':131,'targeted_cases':5,'safe_comparisons':11,'selected_drift_rejections':7,'actual_duplicate_trigger_SQLSTATE42710_rejections':3,'actual_trigger_name_portability_controls':2},'reused_not_freshly_rerun':{'original_schema_cases':128,'prior_controls':43,'historical_findings_not_security_passes':5,'catalog_correction_cases':67,'ordinary_runtime_cases':19,'ordinary_safe_comparisons':23,'ordinary_drift_rejections':15},'independent_review_passed':True,'findings':[],'root_acceptance':False,'product_startup_inspector':False,'ga_acceptance':False,'SQL_normalization_comparator_and_selected_manifest_unchanged':True,'review_execution_failures':0,'discarded_attempts':0,'retained_historical_correction_checker_failures':1,'cleanup':ar['cleanup'],'review_scope':'Only isolated ACSR01/ACSR02 raw-domain correction; root owns selection.','limits':['No malformed actual PostgreSQL catalog or ordinary-runtime authorization bypass was shown.','Original broad schema and ordinary-runtime suites are reused byte-bound evidence, not newly executed here.','133 new cases are model evidence; long resolved-name controls preserve existing text domain and do not claim actual PostgreSQL identifier support.','No live hosted/SQL mutation, startup/current-authority/domain-writer integration, concurrent privileged DDL protection or concurrent-drop index-liveness runtime receipt.','No combined domain schema, provider/HTTP, production, signing/publication, native, physical-phone or GA acceptance.','Phones remain disconnected; final physical qualification remains pending.'],'sealing_command':{'argv':sys.argv,'cwd':str(ROOT)}}
receipt['retained_review_checker_preflight_failures']=1
save(HERE/'receipt.json',receipt)
argv=['python3','-B',str(HERE/'check.py'),'--preflight'];p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True)
c={'argv':argv,'cwd':str(ROOT),'script_sha256':sha((HERE/'check.py').read_bytes()),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'stdout_sha256':sha(p.stdout.encode()),'stderr_sha256':sha(p.stderr.encode())}
target=HERE/'checker-preflight-command.json'
if target.exists():assert js(target)==js(HERE/'checker-preflight-attempt-1/command.json')
save(target,c)
if p.returncode:
    failures=list(HERE.glob('checker-preflight-attempt-*'));failure=HERE/('checker-preflight-attempt-'+str(len(failures)+1));failure.mkdir();(failure/'check.py').write_bytes((HERE/'check.py').read_bytes());save(failure/'command.json',c);print(p.stdout);print(p.stderr);sys.exit(p.returncode)
paths=sorted(p for p in HERE.rglob('*') if p.is_file() and p!=HERE/'artifact-manifest.json')+[ROOT/'docs/hosted-catalog-wildcard-review.md']
entries=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in paths]
save(HERE/'artifact-manifest.json',{'schema':1,'scope':'Frozen independent catalog wildcard/trigger raw-domain review; no startup/GA acceptance','files':entries})
print(json.dumps({'status':receipt['status'],'review_bindings':len(entries),'receipt_sha256':sha((HERE/'receipt.json').read_bytes()),'artifact_manifest_sha256':sha((HERE/'artifact-manifest.json').read_bytes()),'checker_preflight':json.loads(p.stdout)},indent=2))
