#!/usr/bin/env python3
"""Seal the isolated candidate after successful immutable attempt 7."""
import copy,datetime,gzip,hashlib,json,pathlib,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];RUN=HERE/'attempt-7'
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def js(p):return json.loads(p.read_bytes())
assert js(RUN/'receipt.json')['success']
sys.path.insert(0,str(HERE/'inputs/oracle'))
import inspector
baseline=(HERE/'component/priv/selected-expected.json').read_bytes();profile=(HERE/'component/priv/observer-profile.json').read_bytes()
old=inspector.decode(baseline);expected=inspector.decode(profile);delta=js(HERE/'observer-profile-delta.json');reconstructed=copy.deepcopy(old)
assert sha(baseline)==delta['baseline_sha256']=='78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e'
assert len(delta['operations'])==1 and delta['operations'][0]['path']==['legacy','database','acl']
assert reconstructed['legacy']['database']['acl']==delta['operations'][0]['from'];reconstructed['legacy']['database']['acl']=delta['operations'][0]['to'];assert reconstructed==expected
assert profile==(json.dumps(reconstructed,sort_keys=True,indent=2)+'\n').encode()
assert sha(profile)=='a63e1af41935f1a283618d2601e1b072762355059ca25b3782df6518da02d395'
raw=inspector.decode(gzip.decompress((RUN/'evidence/baseline-capture.json.gz').read_bytes()))
assert inspector.validate(raw,expected)==expected
try:inspector.validate(raw,old)
except ValueError as exc:old_error=str(exc)
else:raise AssertionError('original baseline silently accepted observer CONNECT')
star=inspector.decode(gzip.decompress((RUN/'evidence/literal-star-capture.json.gz').read_bytes()));inspector.validate_raw(star)
try:inspector.validate(star,expected)
except ValueError as exc:star_error=str(exc)
else:raise AssertionError('literal-star drift admitted')
save(HERE/'actual-oracle-parity.json',{'schema':1,'actual_component_profile_passes_original_python_normalizer_and_comparator':True,'old_baseline_rejects_observer_connect':True,'old_baseline_error':old_error,'literal_star_raw_valid':True,'literal_star_profile_rejected':True,'literal_star_error':star_error,'normalized_canonical_sha256':sha(inspector.canonical(inspector.normalize(raw)).encode())})
start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();argv=['python3','-B','verification/hosted-catalog-root-acceptance/verify.py'];p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=30);assert p.returncode==0;assert json.loads(p.stdout)['upstreamBindings']==245
save(HERE/'upstream-verification.json',{'argv':argv,'cwd':str(ROOT),'started_utc':start,'seconds':time.monotonic()-t,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'stdout_sha256':sha(p.stdout.encode()),'stderr_sha256':sha(p.stderr.encode()),'scope':'read-only verification of reused original suites, not fresh runtime execution'})
sources=[]
for f in sorted((HERE/'component').rglob('*')):
 if f.is_file():sources.append({'path':str(f.relative_to(HERE)),'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())})
tested={x['path']:x for x in js(RUN/'source-manifest.json') if x['path'].startswith('component/')}
assert {x['path']:x for x in sources}==tested
save(HERE/'candidate-source-manifest.json',sources)
observations=[js(f) for f in sorted((RUN/'evidence').glob('*-outcome.json'))];assert len(observations)==17 and all(x['passed'] for x in observations)
for name in ['elixir-models.json','transport-models.json','atom-models.json','canonical-models.json']:assert js(RUN/'evidence'/name)['passed']
assert js(RUN/'evidence/elixir-models.json')['total']==1257
attempts=[js(HERE/f'attempt-{i}/receipt.json') for i in range(1,8)];assert [x['success'] for x in attempts]==[False]*6+[True];assert all(all(x['cleanup'].values()) if False else x['cleanup']['owned_cluster_stopped'] and x['cleanup']['owned_scratch_removed'] for x in attempts)
receipt={'schema':1,'status':'isolated-component-and-observer-profile-ready-for-independent-review','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'api':'MixerHosted.CatalogInspector.verify(catalog_repo, runtime_repo)','final_attempt':'attempt-7','final_attempt_receipt_sha256':sha((RUN/'receipt.json').read_bytes()),'source_digest':js(RUN/'receipt.json')['source_digest'],'component_source_digest':sha(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()),'dependency_digest':js(RUN/'receipt.json')['dependency_digest'],'baseline_sha256':sha(baseline),'observer_profile_sha256':sha(profile),'original_capture_SQL_and_schema_unchanged':True,'qualified_session_is_explicit_semantic_delta':True,'original_selected_baseline_rejects_new_observer_CONNECT':True,'model_groups':4,'unique_differential_raw_models':1257,'malformed_transport_and_resource_cases':19,'transport_boundary_controls':3,'unknown_atom_controls':250,'canonical_scalar_vectors':19,'canonical_normalized_array_vectors':1,'actual_postgres_test_groups':17,'actual_ddl_ACL_variants':8,'actual_observer_variants':13,'actual_runtime_permission_denials_42501':3,'catalog_counts':{'relations':14,'constraints':89,'indexes':26,'triggers':74},'source_revision':js(RUN/'receipt.json')['head'],'source_tree':js(RUN/'receipt.json')['tree'],'postgres_version':'17.11','fixture_clusters_total':4,'fresh_final_clusters':1,'fixture_padding_tables':173,'preserved_failed_attempts':6,'preserved_command_preflight_mistakes':2,'discarded_attempts':0,'immediate_backend_cleanup_on_unavailable_return':False,'pool_quarantines_deleted_holder_before_async_backend_retirement':True,'cleanup_1000ms_is_test_observation_only':True,'reused_not_freshly_executed':{'schema_cases':128,'prior_controls':43,'historical_observations_not_security_passes':5,'catalog_correction_cases':67,'ordinary_runtime_cases':19,'ordinary_safe_comparisons':23,'ordinary_drift_rejections':15},'read_only_upstream_bindings':245,'read_only_root_bindings':6,'cleanup':js(RUN/'receipt.json')['cleanup'],'independent_review_accepted':False,'root_accepted':False,'hosted_installed':False,'production_provisioned':False,'ga_accepted':False,'limitations':['Authority-only isolated observer-profile candidate, not product startup or request admission.','No observer production provisioning/credential/pool/supervisor lifecycle selection.','Two checked-out connections and repeatable-read execution do not prove atomic cross-connection admission or privileged DDL exclusion.','PostgreSQL constructs JSON/text before output cap; no universal server allocation/work bound.','Node/container/string caps apply after JSON parser allocation; byte/depth guard precedes parsing.','Unavailable can return while original backend retirement is asynchronous; immediate aborted PID state and later absence are separately preserved.','New observer CONNECT profile, component and provider lifecycle disposition require independent review/root acceptance.','Combined domain/Oban, driver/writer, HTTP/provider, production, signing/publication, customer, native/physical-phone and GA gates remain pending.']}
save(HERE/'receipt.json',receipt)
artifacts=[]
for f in sorted(HERE.rglob('*')):
 if f.is_file() and f.name not in ['artifact-manifest.json','receipt.json'] or f.is_file() and f.parent!=HERE and f.name=='receipt.json':
  artifacts.append({'path':str(f.relative_to(ROOT)),'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())})
for name in ['docs/hosted-catalog-inspector-contract.md','docs/hosted-catalog-inspector-implementation.md']:
 f=ROOT/name;artifacts.append({'path':name,'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())})
save(HERE/'artifact-manifest.json',artifacts);receipt['artifact_manifest_sha256']=sha((HERE/'artifact-manifest.json').read_bytes());receipt['artifact_bindings']=len(artifacts);save(HERE/'receipt.json',receipt)
print(json.dumps({'sealed':True,'artifact_bindings':len(artifacts),'component_source_digest':receipt['component_source_digest'],'receipt_sha256':sha((HERE/'receipt.json').read_bytes())},indent=2))
