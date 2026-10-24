#!/usr/bin/env python3
"""Freeze only the owned correction packet and its one documentation file."""
import copy,datetime,difflib,hashlib,json,pathlib,re,subprocess
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
DOC=ROOT/'docs/hosted-atomic-storage-corrected-preflight.md'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
final=HERE/'run-6';actual=read(final/'receipt.json');tests=read(final/'tests.json');catalog=read(final/'installed-catalog.json')
assert actual['passed'] and tests['summary']=={'total':73,'failures':0,'skipped':0,'excluded':0}
predecessors=[]
for name in ['hosted-atomic-storage-preflight','hosted-atomic-storage-review']:
 argv=['python3','-B',str(HERE.parent/name/'check.py')]
 result=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,check=True)
 log=HERE/(name+'-integrity.log');log.write_text(result.stdout+result.stderr)
 predecessors.append({'argv':argv,'returncode':result.returncode,'output':str(log.relative_to(ROOT)),'output_sha256':sha(log.read_bytes()),'result':json.loads(result.stdout)})
files=[]
for name,diff_name in [('hosted-atomic-storage-preflight','diff-vs-producer.patch'),('hosted-atomic-storage-review','diff-vs-reviewer.patch')]:
 old=HERE.parent/name/'probe';new=HERE/'probe';pieces=[];delta=[]
 for rel in sorted({str(p.relative_to(old)) for p in old.rglob('*') if p.is_file()}|{str(p.relative_to(new)) for p in new.rglob('*') if p.is_file()}):
  before=(old/rel).read_bytes() if (old/rel).exists() else b'';after=(new/rel).read_bytes() if (new/rel).exists() else b''
  if before!=after:delta.append({'path':rel,'old_sha256':sha(before) if (old/rel).exists() else None,'new_sha256':sha(after) if (new/rel).exists() else None,'old_bytes':len(before),'new_bytes':len(after)})
  pieces.extend(difflib.unified_diff(before.decode().splitlines(keepends=True),after.decode().splitlines(keepends=True),fromfile=str((old/rel).relative_to(ROOT)),tofile=str((new/rel).relative_to(ROOT))))
 (HERE/diff_name).write_text(''.join(pieces));files.append({'baseline':name,'patch':diff_name,'sha256':sha((HERE/diff_name).read_bytes()),'changed_files':delta})
def cases(path):
 s=path.read_text();return [(m.group(1),m.group(0)) for m in re.finditer(r'^  test "([^"]+)" do\n.*?^  end$',s,re.M|re.S)]
original=cases(HERE.parent/'hosted-atomic-storage-preflight/probe/probe_test.exs');review=cases(HERE.parent/'hosted-atomic-storage-review/probe/probe_test.exs');new=cases(HERE/'probe/probe_test.exs');new_by_title=dict(new)
assert len(original)==41 and len(review)==61 and len(new)==73
lineage=[]
for title,body in original:
 candidate=new_by_title[title]
 lineage.append({'id':title.split(' ',1)[0],'title':title,'old_body_sha256':sha(body.encode()),'new_body_sha256':sha(candidate.encode()),'unchanged_body':body==candidate})
assert [x['id'] for x in lineage if not x['unchanged_body']]==['20','39']
review_lineage=[]
for title,body in review:
 if not title.startswith('R'):continue
 ident=title.split(' ',1)[0];candidate_title,candidate=next((t,b) for t,b in new if t.startswith(ident+' '))
 review_lineage.append({'id':ident,'old_title':title,'new_title':candidate_title,'old_body_sha256':sha(body.encode()),'new_body_sha256':sha(candidate.encode()),'unchanged_body':body==candidate,'oracle_correction':ident in ['R03','R06','R07','R08','R09','R10','R11','R19']})
write(HERE/'probe-delta.json',{'schema':1,'original_source_digest':'0f72c5b18c333f74b27f58ff17707fc909175a0c9ea4cf974c3015fb65007d7e','review_source_digest':'82279360945406d1fa4bce8391a81a4bd1eb4f6b5c081f75e1f4a633c810c79d','original_case_count':41,'review_case_count':20,'correction_case_count':12,'original_cases':lineage,'review_cases':review_lineage,'files':files,'case20_note':'Inherited reviewer-only quiet PostgreSQL restart log settings; all COMMIT-loss/restart/retry assertions remain unchanged.','case39_note':'Only the intentional corrupt-fixture encoder changes to literal set_byte(event_cbor,2,2); writer rejection assertion remains. New typed decoder rejects malformed event2/empty predecessor before encoding.'})
write(HERE/'coordination.json',{'schema':1,'root_selection':'docs/hosted-atomic-storage-corrections.md','root_selection_receipt':'verification/hosted-atomic-storage-root-review/correction-selection.json','ownership':['docs/hosted-atomic-storage-corrected-preflight.md','verification/hosted-atomic-storage-corrected-preflight/**','unique owned disposable local PostgreSQL/scratch resources'],'clarifications':[{'topic':'exact counts','selected':'41 original producer cases and20 independent reviewer cases; stray151 typo is not a requirement'},{'topic':'case39 malformed setup','selected':'Preserve the rejection assertion using explicit test-only malformed bytes; do not weaken the strict decoder'},{'topic':'time relationships','selected':'Authentication completion may be decision+30; no completion<=decision/recorded requirement; recorded>=decision'},{'topic':'JSONB schema representation','selected':'event_from_display(jsonb) validates retained typed JSONB integer representation1. Raw1e0 normalizes to1 before entry and cannot be recovered. Preserve failing run5 lexical oracle, test accepted normalized control and retained noninteger rejection; separate Elixir typed integer1. No raw JSON API or raw-spelling claim.'},{'topic':'privileged offline corruption','selected':'Bounded adjacent-edge/cached semantic checks under immutable runtime rows; no whole-chain scan or proof against coherent offline privileged rewrite'}],'no_other_lane_or_live_sources_owned':True,'fresh_independent_review_required':True})
contract=copy.deepcopy(read(HERE.parent/'hosted-atomic-storage-preflight/contract-manifest.json'))
contract['status']='corrected-specimen-frozen-product-manifest-pending-root-selection'
contract['product']['context_fields']=[x.replace('numeric(20,0)','numeric') for x in contract['product']['context_fields']]
contract['product']['artifact_fields']=[x.replace('numeric(20,0)','numeric') for x in contract['product']['artifact_fields']]
contract['product'].pop('private_codec_manifest',None)
contract['product']['private_helper_selection']='Pending root selection of actual product DDL/identities; no conceptual alias is an installed-object manifest. Complete actual specimen identities/definitions/effective ACLs are bound below.'
contract['product']['codec_note']='Necessary private pure helpers are allowed under AS07. The exact installed specimen manifest is evidence, not a live product migration or inspector.'
contract['specimen']['schema_file']='probe/schema.sql'
contract['specimen']['installed_catalog']='run-6/installed-catalog.json'
contract['specimen']['installed_catalog_sha256']=actual['installed_catalog_sha256']
contract['specimen']['functions']=[{k:f[k] for k in ['identity','owner','prosecdef','provolatile','proparallel','proleakproof','proconfig','acl','acl_entries','effective_execute','definition_sha256']} for f in catalog['functions']]
contract['specimen']['schema_owner_pure_helpers']=[f['identity'] for f in catalog['functions'] if not f['prosecdef']]
contract['specimen']['single_mutation_entry']='mixer_hosted_release.upload_v1(mixer_hosted_release.call_context,mixer_hosted_release.upload_input,mixer_hosted_release.upload_request)'
contract['specimen']['table_constraints_and_columns']='Complete actual catalog; all retained artifact/audit/idempotency fields nonnull, artifact creation actor+event and deferred same-tenant FK; semantic typed/hash/transition/edge checks in fixed writer.'
contract['encodings']['jsonb_boundary']='Exact retained typed JSONB schema integer1 representation; PostgreSQL raw1e0 normalization loses raw spelling before internal helper. No arbitrary public JSON parser.'
contract['encodings']['audit_time_relationship']='completion in decision-45..decision+30; recorded>=decision; no completion<=decision/recorded requirement'
write(HERE/'contract-manifest.json',contract)
attempts=[]
for directory in sorted(HERE.glob('run-*'),key=lambda p:int(p.name.split('-')[1])):
 a=read(directory/'receipt.json');attempts.append({'run':directory.name,'passed':a['passed'],'test_summary':a.get('test_summary'),'source_tree_digest':a['probe_source_tree_digest'],'error':a['error'],'cleanup':a['cleanup']})
commands=read(final/'commands.json');versions=[{k:c[k] for k in ['argv','stdout','stderr','returncode']} for c in commands if c['argv'] in [['python3','--version'],['elixir','--version'],['mix','--version'],['postgres','--version'],['pg_ctl','--version'],['psql','--version'],['go','version']]]
receipt={'schema':1,'status':'producer-correction-candidate-frozen-pending-fresh-independent-review','frozen_utc':now(),'scope':'Synthetic local PostgreSQL17+actualEcto corrected internal writer/display/blob primitive only; no product authorization/repository/migration/provider/GA acceptance','passing_run':'run-6','observed_execution_head':actual['observed_head'],'probe_source_tree_digest':actual['probe_source_tree_digest'],'installed_catalog_sha256':actual['installed_catalog_sha256'],'documentation_sha256':sha(DOC.read_bytes()),'summary':tests['summary'],'original_cases':41,'independent_review_cases':20,'new_correction_cases':12,'invalid_display_cases':456,'valid_display_boundaries':26,'independent_uint64_vectors':120,'all_attempts':attempts,'tool_versions':versions,'dependency_baseline':actual['baseline_revision'],'dependency_additions':False,'predecessor_integrity_checks':predecessors,'root_acceptance':False,'product_implementation':False,'repository_accepted':False,'migration':False,'http_provider_ga_acceptance':False,'native_or_physical_runs':False,'commits_created':False,'all_owned_cleanup_verified':True,'limitations':['Synthetic fixed tenant/target RLS, two principals and single policy lock; no full authoritative profile/principal/family/organization/project lock seam or membership/credential integration.','Opaque synthetic artifact inputs; no actual signed v3 admission or HTTP repository composition.','No live product migration/DDL/private helper manifest/startup inspector accepted; actual specimen catalog only.','JSONB cannot recover discarded raw JSON exponent spelling; retained integer1 representation and Elixir typed integer1 are the selected boundaries.','Bounded immediate predecessor checks are not whole-history or coherent privileged offline rewrite proof; cached original-key provenance against coherent privileged row rewrite requires external commitment.','Controlled completed-server-COMMIT acknowledgement loss only; arbitrary cancellation/provider/WAL timing pending; COMMIT can complete just after expiry.','Existing local blob trusted single-process/directory and Agent reference-cap limitations unchanged; no power-loss/R2/multi-host or HTTP pre-mailbox/cancellation qualification.','No Oban/domain-job atomicity, Neon/R2/Cloudflare, Linux service CI, customer/FieldLog/external/accountable GA or native/physical qualification; physical phones remain deferred.']}
write(HERE/'receipt.json',receipt)
write(HERE/'review-handoff.json',{'schema':1,'candidate_receipt':'receipt.json','source_digest':actual['probe_source_tree_digest'],'immutable_run_source':'run-6/inputs/probe','runner':'run-6/inputs/run.py','independent_generator':'run-6/inputs/build-display-corpus.py','catalog':'run-6/installed-catalog.json','catalog_sha256':actual['installed_catalog_sha256'],'documentation':str(DOC.relative_to(ROOT)),'documentation_sha256':sha(DOC.read_bytes()),'selected_corrections':['AS01','AS02','AS03','AS04','AS05','AS06','AS07'],'fresh_reviewer_must_copy_to_new_owned_paths':True,'producer_frozen_no_review_mutation':True,'repository_acceptance_pending_root':True})
# Seal all retained owned files plus the single owned documentation file. Output
# manifests/seal/check results exclude themselves to avoid a self-reference cycle.
entries=[]
for path in sorted([DOC]+[p for p in HERE.rglob('*') if p.is_file() and p.name not in ['artifact-manifest.json','seal.json','check-output.json']]):
 b=path.read_bytes();entries.append({'path':str(path.relative_to(ROOT)),'sha256':sha(b),'bytes':len(b)})
write(HERE/'artifact-manifest.json',{'schema':1,'files':entries})
write(HERE/'seal.json',{'schema':1,'frozen_utc':now(),'manifest_sha256':sha((HERE/'artifact-manifest.json').read_bytes()),'bindings':len(entries),'source_tree_digest':actual['probe_source_tree_digest'],'documentation_sha256':sha(DOC.read_bytes()),'root_acceptance':False})
print(json.dumps({'frozen':True,'bindings':len(entries),'source_digest':actual['probe_source_tree_digest'],'receipt_sha256':sha((HERE/'receipt.json').read_bytes()),'seal_sha256':sha((HERE/'seal.json').read_bytes()),'doc_sha256':sha(DOC.read_bytes())}))
