#!/usr/bin/env python3
"""Seal candidate, preserved assertions, complete consulted input closure and output evidence."""
import difflib,hashlib,json,os,platform,subprocess,tarfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path('/Users/andreyyurlov/Documents/dev/mixer');HERE=Path(__file__).resolve().parent
P=ROOT/'verification/hosted-worker-controller-implementation';R=ROOT/'verification/hosted-worker-controller-implementation-independent-review'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def rec(p,base=ROOT):return {'path':str(p.relative_to(base)),'bytes':p.stat().st_size,'sha256':sha(p)}
def dump(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def digest(files):return hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def archive(path,base,files):
 with tarfile.open(path,'w:gz') as t:
  for e in files:t.add(base/e['path'],arcname=e['path'],recursive=False)
def check(e):
 p=ROOT/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path']
assert sha(P/'receipt.json')=='fb71bcb1cc076b121a26e075c8e1bf8c2703bc5a659686e4a6ae861b855dc68a'
assert sha(R/'receipt.json')=='7e146e6f341afc93dca4f108bbee7ee50f7c4a406eb329bd5fa96405463f5b7e'
pr=json.loads((P/'receipt.json').read_text());rr=json.loads((R/'receipt.json').read_text())
counts={}
for n in ['source-manifest.json','dependency-files.json','jason-beams.json']:
 es=json.loads((P/n).read_text())['files'];counts[n]=len(es)
 for e in es:check(e)
for n,es in [('producer_artifacts',pr['artifacts']),('runtime_inputs',pr['runtime_binary_inputs']),('review_artifacts',rr['artifacts'])]:
 counts[n]=len(es)
 for e in es:check(e)
for c in pr['commands_and_outputs']:
 for key in ['stdout','stderr']:check(c[key])
counts['producer_commands']=len(pr['commands_and_outputs'])
dump(HERE/'originals-post-run-bindings.json',{'status':'passed','counts':counts,'producer_receipt_sha256':sha(P/'receipt.json'),'rejected_review_receipt_sha256':sha(R/'receipt.json'),'original_source_and_evidence_unchanged':True})
files=[rec(p,HERE/'candidate') for p in sorted((HERE/'candidate').rglob('*')) if p.is_file()]
assert len(files)==60
source_digest=digest(files);assert source_digest=='c5848761151f9accfd81eff8292e756cff427e90092d9b7b309b010eb5feb736'
dump(HERE/'source-manifest.json',{'scope':'isolated-V2-candidate-complete-60-record-source-and-fixture-closure','tree_sha256':source_digest,'files':files})
archive(HERE/'source-snapshot.tar.gz',HERE/'candidate',files)
original={e['path']:e for e in json.loads((P/'source-manifest.json').read_text())['files']}
diff=[];changes=[]
for e in files:
 p=HERE/'candidate'/e['path'];before=HERE/'inputs'/e['path'];assert before.is_file()
 if sha(p)!=sha(before):
  changes.append({'path':e['path'],'before':sha(before),'after':sha(p)})
  diff.extend(difflib.unified_diff(before.read_text().splitlines(keepends=True),p.read_text().splitlines(keepends=True),fromfile='original/'+e['path'],tofile='candidate/'+e['path']))
(HERE/'candidate.diff').write_text(''.join(diff));dump(HERE/'changed-files.json',changes)
checks=[]
for name in ['hosted-worker-controller/test/run.mjs','hosted-worker-controller/test/acceptance-driver.mjs','verification/hosted-worker-controller-contract/acceptance.mjs']:
 assert sha(HERE/'candidate'/name)==sha(HERE/'inputs'/name);checks.append({'path':name,'status':'byte-identical','sha256':sha(HERE/'candidate'/name)})
reviewbase=HERE/'inputs/verification/hosted-worker-controller-implementation-independent-review'
for run,name in [('baseline-regressions','regressions.mjs'),('v2-regressions-final','regressions.mjs'),('v2-noncooperative-final','noncooperative.mjs'),('v2-closure-final','closure.mjs')]:
 actual=HERE/'runs'/run/name;assert sha(actual)==sha(reviewbase/name);checks.append({'path':str(actual.relative_to(HERE)),'status':'byte-identical-full-assertion-or-audit-source','sha256':sha(actual)})
assert sha(HERE/'runs/v2-noncooperative-final/fixture-worker.ts')==sha(reviewbase/'noncooperative-worker.ts')
checks.append({'path':'runs/v2-noncooperative-final/fixture-worker.ts','status':'byte-identical-independent-noncooperative-fixture','sha256':sha(reviewbase/'noncooperative-worker.ts')})
dump(HERE/'assertion-preservation.json',{'status':'passed','assertions_rewritten':0,'harness_relocation_diffs':[],'note':'Copied fixtures use their original relative bindings.json/report paths in a fresh run folder; only per-run binding data supplies scratch location. No assertion source edits. Excluded candidate test Worker controls are explicit in candidate.diff.','checks':checks})
commands=[json.loads(p.read_text()) for p in sorted((HERE/'runs').glob('*/command.json'))]
for c in commands:
 for action in c['commands']:
  for key in ['stdout','stderr']:check(action[key])
 for a in c['cleanup']['actions']:
  if 'persist' in a:assert not Path(a['persist']).exists(),a
 assert c['cleanup']['scratch_removed'] and not Path(c['cleanup']['scratch']).exists()
final_runs=['v2-build-final','v2-producer-final','v2-regressions-final','v2-focused-1','v2-noncooperative-final','v2-closure-final','v2-inventory-final']
for name in final_runs:
 c=json.loads((HERE/'runs'/name/'command.json').read_text());assert c['source_tree_sha256']==source_digest and c['exit_code']==0
for name in ['v2-build-final','v2-producer-final','v2-regressions-final','v2-focused-1','v2-closure-final','v2-inventory-final']:
 for e in json.loads((HERE/'runs'/name/'compiled.json').read_text()):
  p=HERE/'candidate/hosted-worker-controller'/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],(name,e['path'])
for e in json.loads((HERE/'runs/v2-noncooperative-final/compiled.json').read_text()):
 if not e['path'].startswith('dist/src/'):continue
 assert sha(HERE/'candidate/hosted-worker-controller'/e['path'])==e['sha256']
baseline=json.loads((HERE/'runs/baseline-regressions/regression-report.json').read_text())
assert [e['id'] for e in baseline['results'] if e['status']=='failed']==['claim-final-authority-epoch-owner-transfer','claim-final-authority-revision-advance','later-effect-clock-sample-must-fence-rollback-before-claim']
results={}
for n,file,count in [('producer','v2-producer-final/producer-report.json',28),('exact_independent','v2-regressions-final/regression-report.json',7),('focused','v2-focused-1/focused-report.json',36)]:
 r=json.loads((HERE/'runs'/file).read_text());assert r['status']=='passed' and len(r['results'])==count and all(x['status']=='passed' for x in r['results']);results[n]=count
noncoop=json.loads((HERE/'runs/v2-noncooperative-final/noncooperative-report.json').read_text());assert noncoop['status']=='passed';results['noncooperative']=1
closure=json.loads((HERE/'runs/v2-closure-final/independent-closure.json').read_text());assert closure['status']=='passed' and len(closure['files'])==9 and closure['externals']==['cloudflare:workers']
inv=json.loads((HERE/'runs/v2-inventory-final/inventory-report.json').read_text());assert inv['status']=='passed' and inv['locked_entries']==58
# Seal every consulted frozen source/fixture plus replay/checker implementation.
input_paths=[p for p in sorted((HERE/'inputs').rglob('*')) if p.is_file()]
input_paths += [HERE/n for n in ['prepare.py','repair.py','run.py','focused.mjs','inventory.mjs','freeze.py','verify_final.py','README.md','initial-command-failures.json','root-decisions.json']]
input_paths.append(ROOT/'docs/hosted-worker-controller-v2.md')
inputs=sorted((rec(p) for p in input_paths),key=lambda x:x['path'])
dump(HERE/'input-closure-manifest.json',{'scope':'complete-consulted-frozen-input-fixture-and-owned-replay-source-closure','tree_sha256':digest(inputs),'files':inputs})
archive(HERE/'input-closure.tar.gz',ROOT,inputs)
cleanup_actions=[a for c in commands for a in c['cleanup']['actions']];ownedpaths=[a['persist'] for a in cleanup_actions if 'persist' in a]
ps=subprocess.run(['/bin/ps','-axo','pid=,ppid=,comm='],capture_output=True,text=True,check=True)
executables=[c['cleanup']['owned_workerd_executable'] for c in commands];matching=[line.strip() for line in ps.stdout.splitlines() if any(line.strip().endswith(exe) for exe in executables)]
assert not matching
cleanup={'status':'passed','run_count':len(commands),'cleanup_actions':len(cleanup_actions),'owned_storage_paths':len(set(ownedpaths)),'all_owned_storage_absent':all(not Path(p).exists() for p in ownedpaths),'owned_SIGKILL_cases':sum(a.get('signal')=='SIGKILL' for a in cleanup_actions),'all_per_command_scratch_removed':all(c['cleanup']['scratch_removed'] for c in commands),'matching_owned_workerd':matching,'process_scan_argv':['/bin/ps','-axo','pid=,ppid=,comm='],'other_projects_modified':False,'native_instances_started':0,'live_provider_cloud_calls':0}
dump(HERE/'cleanup.json',cleanup)
artifacts=[rec(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in ['receipt.json','verify-final.stdout','verify-final.stderr']]
artifacts.append(rec(ROOT/'docs/hosted-worker-controller-v2.md'))
receipt={'schema':2,'created_at':datetime.now(timezone.utc).isoformat(),'status':'frozen-v2-repair-awaiting-independent-review','scope':'isolated-per-operation-R1-R2-worker-SQLite-controller-repair-only','accepted':False,'source_tree_sha256':source_digest,'source_manifest':rec(HERE/'source-manifest.json'),'source_archive':rec(HERE/'source-snapshot.tar.gz'),'input_closure_tree_sha256':digest(inputs),'input_closure_manifest':rec(HERE/'input-closure-manifest.json'),'input_closure_archive':rec(HERE/'input-closure.tar.gz'),'baseline_bindings':json.loads((HERE/'baseline-bindings.json').read_text()),'baseline_reproduced_failures':[x['id'] for x in baseline['results'] if x['status']=='failed'],'final_results':results,'unique_final_groups':sum(results.values()),'production_closure_files':9,'production_externals':['cloudflare:workers'],'production_clock_provider_object_verifier':'unavailable','production_runner_HTTP_test_ingress':False,'root_internal_decisions':rec(HERE/'root-decisions.json'),'dependency_entries':58,'installed_dependency_files_bound':1180,'dependency_installs':0,'dependency_install_scripts_executed':0,'versions':inv['versions'],'platform':platform.platform(),'runtime_inputs':pr['runtime_binary_inputs'],'commands':commands,'artifacts':artifacts,'cleanup':cleanup,'source_revision':'explicit frozen SHA-256 tree; no Git inspected','historical_limits':['The initial direct official-document retrieval failed HTTP 403 before response bytes were available; command/failure is retained and web-tool contract output is sealed.','The first focused run invoked owned focused.mjs directly; the identical fixture was copied into its run directory immediately after execution and is fully sealed. Subsequent runner versions freeze it before execution.','Local workerd output/SQLite and modeled providers do not establish deployed distributed durability, actual ingress, trusted runner, clock or provider qualification.'],'not_verified':['independent-review-and-development-slice-acceptance','complete-controller','pending-registry-scheduler','missed-wake-exhausted-alarm-retries','independent-nonrollbackable-restore-namespace-authority','actual-edge-TLS-header-framing-EOF','qualified-live-clock','real-provider-images-sizing-egress-source-isolation','external-macOS','trusted-one-shot-runner-and-descendant-proof','scoped-source-private-R2-object-result-authorization','whole-domain-resource-limits','Neon-Oban-zero-traffic-operational-SLOs','public-authorization','signing-key-custody-store-customer-GA','immutable-published-FieldLog-dogfood','physical-phone-matrix'],'restrictions':{'originals_unchanged':True,'shared_status_inventory_git_unchanged':True,'other_lanes_unchanged':True,'catalog_authority_driver_not_read_imported_executed':True,'interrupted_outbound_v2_review_not_read_imported_executed':True,'original_transport_vectors_data_only':True,'no_Patch_Skip':True,'no_native_UI_simulators_phones':True,'no_live_provider_deploy_credentials_customers':True}}
dump(HERE/'receipt.json',receipt)
print(json.dumps({'status':receipt['status'],'source_tree_sha256':source_digest,'source_archive_sha256':receipt['source_archive']['sha256'],'input_closure_tree_sha256':receipt['input_closure_tree_sha256'],'receipt_sha256':sha(HERE/'receipt.json'),'changed_records':len(changes),'artifacts':len(artifacts),'input_records':len(inputs),'results':results,'cleanup':cleanup}))
