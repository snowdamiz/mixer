#!/usr/bin/env python3
"""Read-only frozen correction integrity. Starts no service and grants no acceptance."""
import difflib,hashlib,json,pathlib,re,subprocess
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_text())
seal=read(HERE/'seal.json');manifest=read(HERE/'artifact-manifest.json')
assert sha((HERE/'artifact-manifest.json').read_bytes())==seal['manifest_sha256']
seen=set()
for f in manifest['files']:
 p=ROOT/f['path'];b=p.read_bytes()
 assert len(b)==f['bytes'] and sha(b)==f['sha256'],f['path']
 assert f['path'] not in seen;seen.add(f['path'])
assert len(seen)==seal['bindings']
receipt=read(HERE/'receipt.json')
assert not any(receipt[k] for k in ['root_acceptance','product_implementation','repository_accepted','migration','http_provider_ga_acceptance','native_or_physical_runs','dependency_additions','commits_created'])
assert receipt['passing_run']=='run-6'
assert receipt['summary']=={'total':73,'failures':0,'skipped':0,'excluded':0}
for name,bindings,digest in [('hosted-atomic-storage-preflight',239,'0f72c5b18c333f74b27f58ff17707fc909175a0c9ea4cf974c3015fb65007d7e'),('hosted-atomic-storage-review',134,'82279360945406d1fa4bce8391a81a4bd1eb4f6b5c081f75e1f4a633c810c79d')]:
 p=HERE.parent/name
 result=subprocess.run(['python3','-B',str(p/'check.py')],cwd=ROOT,capture_output=True,text=True,check=True)
 actual=json.loads(result.stdout)
 assert actual['verified'] and actual['bindings']==bindings and actual['source_tree_digest']==digest
for a in receipt['all_attempts']:
 out=HERE/a['run'];actual=read(out/'receipt.json')
 assert actual['passed']==a['passed'] and actual.get('test_summary')==a['test_summary'] and actual['error']==a['error']
 assert actual['cleanup']==a['cleanup']
 clean=actual['cleanup']
 assert clean['owned_postgres_stopped'] and clean['owned_scratch_removed'] and clean['owned_socket_removed']
 assert not clean['other_clusters_touched'] and not clean['native_processes_started']
 assert not pathlib.Path(clean['owned_scratch']).exists()
 if (out/'proxy.jsonl').exists():assert clean['owned_proxy_stopped']
 else:assert a['run']=='run-1' and not clean['owned_proxy_stopped']
 sources=read(out/'source-manifest.json')
 assert sha(json.dumps(sources,sort_keys=True,separators=(',',':')).encode())==actual['probe_source_tree_digest']==a['source_tree_digest']
 for s in sources:
  assert sha((out/'inputs'/s['path']).read_bytes())==s['sha256']
  if a['run']==receipt['passing_run']:assert sha((HERE/s['path']).read_bytes())==s['sha256']
 for c in read(out/'contract-inputs.json'):
  assert sha((out/'inputs/contracts'/c['path']).read_bytes())==c['sha256']
 assert (out/'dependency-source-manifest.json').read_bytes()==(HERE.parent/'hosted-atomic-storage-preflight/run-8/dependency-source-manifest.json').read_bytes()
 if (out/'tests.json').exists():assert read(out/'tests.json')['summary']==actual['test_summary']
final=HERE/receipt['passing_run'];obs=read(final/'tests.json')['observations']
assert obs['corrected_display_corpus']['invalid']==456 and obs['corrected_display_corpus']['valid']==26
assert obs['corrected_utf8_and_schema_types']['postgres_jsonb_normalizes_raw_exponent_1e0_to_integer1']
assert obs['corrected_utf8_and_schema_types']['elixir_typed_float_rejected']
assert obs['review_expiry_validation_gap']['all_rejected_by_corrected_specimen']
assert obs['review_idempotency_material_gap']['changed_status_and_body_rejected']
assert obs['review_idempotency_event_gap']['wrong_existing_event_rejected']
assert obs['review_closed_display_gap']['same_count_extra_and_missing_null_rejected']
assert obs['review_canonical_display_gap']['leading_zero_integer_rejected']
assert obs['review_predecessor_edge_gap']['coherent_wrong_predecessor_rejected']
assert obs['review_artifact_creation_link_gap']['nonexistent_creation_event_rejected_by_fk']
assert not obs['review_expiry_before_effect_gap']['inserted_after_expiry']
waits=obs['corrected_late_read_waits']+obs['corrected_dml_waits']['rejections']+[obs['corrected_dml_waits']['unexpired_success_control'],obs['corrected_dml_waits']['exact_age45_success_control']]+list(obs['corrected_final_clock_and_deadline'][k] for k in ['new_clock','sql_original_deadline'])
for w in waits:
 assert w['pg_observed_wait']
 for row in w['pg_observed_wait']:
  assert row['head_lock_granted'] and row['policy_lock_granted'] and row['wait_event_type']=='Lock'
  assert row['mode']==('RowExclusiveLock' if w['mode']=='SHARE' else 'AccessShareLock')
 if w['outcome']=='reject':assert w['no_committed_changes']
assert obs['uncertain_commit_restart']['exact_original_retry']
proxy=[json.loads(x) for x in (final/'proxy.jsonl').read_text().splitlines()]
assert any(x.get('dropped')=='COMMIT CommandComplete' and x['server_commit_completed'] and not x['client_ack_sent'] for x in proxy)
commands=read(final/'commands.json')
for prefix in [['go','test'],['go','run'],['mix','deps.compile'],['mix','run']]:
 assert any(c['argv'][:2]==prefix and c['returncode']==0 for c in commands)
catalog=read(final/'installed-catalog.json')
assert sha((final/'installed-catalog.json').read_bytes())==receipt['installed_catalog_sha256']
assert len(catalog['functions'])==22 and len(catalog['tables'])==7 and len(catalog['composites'])==4
assert len(catalog['memberships'])==0
for f in catalog['functions']:
 assert sha(f['definition'].encode())==f['definition_sha256']
 assert not any(x['grantee']=='PUBLIC' for x in f['acl_entries'])
 assert 'search_path=pg_catalog' in f['proconfig']
 if f['identity'].startswith('mixer_hosted_release.') and 'upload_v1(' not in f['identity']:
  assert f['owner']=='mxas_schema' and not f['prosecdef'] and f['provolatile']=='i'
  assert not next(x['execute'] for x in f['effective_execute'] if x['role']=='mxas_runtime')
assert [f['identity'] for f in catalog['functions'] if f['owner']=='mxas_writer']==['mixer_hosted_release.upload_v1(mixer_hosted_release.call_context,mixer_hosted_release.upload_input,mixer_hosted_release.upload_request)']
for type_name,field in [('call_context','expires_at'),('call_context','authentication_completed_at'),('upload_input','payload_size')]:
 t=next(x for x in catalog['composites'] if x['typname']==type_name)
 assert next(x['type'] for x in t['fields'] if x['name']==field)=='numeric'
for t in catalog['tables']:assert t['relrowsecurity'] and t['relforcerowsecurity']
for role in catalog['roles']:
 assert not any(role[x] for x in ['superuser','create_role','create_db','replication','bypass_rls'])
 assert not role['all_memberships']
# Exact baseline diffs include additions; compare regenerated patch bytes.
for name,diff_name in [('hosted-atomic-storage-preflight','diff-vs-producer.patch'),('hosted-atomic-storage-review','diff-vs-reviewer.patch')]:
 old=HERE.parent/name/'probe';new=HERE/'probe';pieces=[]
 for rel in sorted({str(p.relative_to(old)) for p in old.rglob('*') if p.is_file()}|{str(p.relative_to(new)) for p in new.rglob('*') if p.is_file()}):
  a=(old/rel).read_text() if (old/rel).exists() else '';b=(new/rel).read_text() if (new/rel).exists() else ''
  pieces.extend(difflib.unified_diff(a.splitlines(keepends=True),b.splitlines(keepends=True),fromfile=str((old/rel).relative_to(ROOT)),tofile=str((new/rel).relative_to(ROOT))))
 assert ''.join(pieces).encode()==(HERE/diff_name).read_bytes()
for name in ['golden-vectors.json','legacy-golden.json','legacy.go','lib/context.ex','lib/blob.ex','lib/bounds.ex','proxy.py','mix.exs']:
 assert (HERE/'probe'/name).read_bytes()==(HERE.parent/'hosted-atomic-storage-preflight/probe'/name).read_bytes()
assert (HERE/'probe/review-uint64-vectors.json').read_bytes()==(HERE.parent/'hosted-atomic-storage-review/probe/review-uint64-vectors.json').read_bytes()
lineage=read(HERE/'probe-delta.json')
assert lineage['original_case_count']==41 and lineage['review_case_count']==20 and lineage['correction_case_count']==12
assert [x['id'] for x in lineage['original_cases'] if not x['unchanged_body']]==['20','39']
print(json.dumps({'verified':True,'bindings':seal['bindings'],'passing_run':receipt['passing_run'],'summary':receipt['summary'],'source_tree_digest':receipt['probe_source_tree_digest'],'installed_catalog_sha256':receipt['installed_catalog_sha256'],'original_cases':41,'review_cases':20,'new_correction_cases':12,'invalid_display_cases':456,'valid_display_vectors':26,'confirmed_wait_boundaries':len(waits),'owned_cleanup_verified':True,'repository_accepted':False,'root_acceptance':False}))
