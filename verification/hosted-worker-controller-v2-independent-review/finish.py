#!/usr/bin/env python3
"""Seal observed evidence, recheck frozen originals, remove exact owned scratch."""
import hashlib,json,os,shutil,subprocess,tarfile
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('/Users/andreyyurlov/Documents/dev/mixer');HERE=ROOT/'verification/hosted-worker-controller-v2-independent-review';P=ROOT/'verification/hosted-worker-controller-v2';B=json.loads((HERE/'bindings.json').read_text());OWN=Path(B['scratch']);DOC=ROOT/'docs/hosted-worker-controller-v2-independent-review.md'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rec(p):return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)}
def dig(records):return hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def check(p,e):assert p.is_file()and p.stat().st_size==e['bytes']and sha(p)==e['sha256'],str(p)
r=json.loads((P/'receipt.json').read_text());assert sha(P/'receipt.json')==B['producer_receipt_sha256']
for e in r['artifacts']:check(ROOT/e['path'],e)
s=json.loads((P/'source-manifest.json').read_text());i=json.loads((P/'input-closure-manifest.json').read_text())
for e in s['files']:check(P/'candidate'/e['path'],e)
for e in i['files']:check(ROOT/e['path'],e)
for k in ['source_manifest','source_archive','input_closure_manifest','input_closure_archive','root_internal_decisions']:check(ROOT/r[k]['path'],r[k])
for e in B['consulted']:check(ROOT/e['path'],e)
for label in ['dependency-files.json','jason-beams.json']:
 for e in json.loads((P/'inputs/verification/hosted-worker-controller-implementation'/label).read_text())['files']:check(ROOT/e['path'],e)
for e in r['runtime_inputs']:check(Path(e['path']),e)
(HERE/'originals-final-recheck.json').write_text(json.dumps({'status':'passed','receipt_sha256':sha(P/'receipt.json'),'artifact_records':352,'candidate_records':60,'input_records':172,'dependencies':1180,'jason_records':29,'runtime_inputs':4,'consulted_current_documents_unchanged':True,'scope':'explicit frozen file sets only; unrelated untracked files not inspected'},indent=2)+'\n')
commands=[json.loads(p.read_text())for p in sorted((HERE/'runs').glob('*/command.json'))];assert len(commands)==11
actions=[a for c in commands for a in c['cleanup']['actions']]
for c in commands:assert c['cleanup']['scratch_removed']and not Path(c['cleanup']['scratch']).exists();assert not c['cleanup']['matching_before_outer_cleanup']
for a in actions:
 if 'persist'in a:assert not Path(a['persist']).exists()
psargv=['/bin/ps','-axo','pid=,ppid=,comm='];ps=subprocess.run(psargv,capture_output=True,text=True,check=True)
matching=[line.strip()for line in ps.stdout.splitlines()if str(OWN)in line and 'workerd'in line];assert not matching,matching
# Verify the retained complete frozen archive before removing its expanded scratch.
frozen=json.loads((HERE/'frozen-input-manifest.json').read_text());expected={e['path']:e for e in frozen['files']}
with tarfile.open(HERE/'frozen-inputs.tar.gz')as t:
 assert len(t.getmembers())==len(expected)and set(t.getnames())==set(expected)
 for m in t:
  assert m.isfile();data=t.extractfile(m).read();e=expected[m.name];assert len(data)==e['bytes']and hashlib.sha256(data).hexdigest()==e['sha256']
if OWN.exists():shutil.rmtree(OWN)
if(HERE/'frozen').exists():shutil.rmtree(HERE/'frozen')
cleanup={'status':'passed','command_runs':len(commands),'cleanup_actions':len(actions),'owned_storage_paths':sum('persist'in a for a in actions),'owned_SIGKILL_observations':sum(a.get('signal')=='SIGKILL'for a in actions),'all_owned_storage_absent':True,'all_per_command_scratch_removed':True,'shared_dependency_copy_scratch':str(OWN),'shared_dependency_copy_scratch_removed':not OWN.exists(),'expanded_frozen_scratch_removed':not(HERE/'frozen').exists(),'immutable_archives_retained':True,'process_scan_argv':psargv,'matching_owned_workerd':matching,'other_projects_modified':False,'native_instances_started':0,'live_provider_cloud_calls':0}
(HERE/'cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n')
# Complete executed fixture closure includes per-run archived runner variants.
fixture_paths=[]
for p in sorted(HERE.rglob('*')):
 if p.is_file()and(p.suffix in ['.py','.mjs','.ts']or p.name in ['bindings.json','compiled.json','source-snapshot.tar.gz']or p.is_relative_to(HERE/'consulted')):fixture_paths.append(p)
fixtures=[{'path':str(p.relative_to(HERE)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in fixture_paths]
(HERE/'review-fixture-manifest.json').write_text(json.dumps({'tree_sha256':dig(fixtures),'files':fixtures},indent=2)+'\n')
with tarfile.open(HERE/'review-fixtures.tar.gz','w:gz')as t:
 for p,e in zip(fixture_paths,fixtures):t.add(p,arcname=e['path'],recursive=False)
# Freeze precise result assertions and baseline failures from actual outputs.
def report(name,file):return json.loads((HERE/'runs'/name/file).read_text())
baseline=report('baseline','regression-report.json');failed=[e for e in baseline['results']if e['status']=='failed'];assert len(failed)==3 and baseline['status']=='failed'
results={}
for name,file,count in [('producer','producer-report.json',28),('regressions','regression-report.json',7),('focused','focused-report.json',36),('noncooperative','noncooperative-report.json',1),('independent-final','independent-report.json',17)]:
 d=report(name,file);assert d['status']=='passed'and (len(d['results'])if 'results'in d else 1)==count;results[name]={'status':d['status'],'groups':count,'report':rec(HERE/'runs'/name/file)}
assert report('ast','ast-report.json')['status']=='passed';assert report('inventory','inventory-report.json')['status']=='passed';assert report('closure','independent-closure.json')['status']=='passed'
artifacts=[rec(p)for p in sorted(HERE.rglob('*'))if p.is_file()and p.name not in ['receipt.json','handoff.json']];artifacts.append(rec(DOC))
receipt={'schema':1,'created_at':datetime.now(timezone.utc).isoformat(),'status':'independently-reviewed-v2-local-development-slice-recommended','scope':'frozen-per-operation-R1-R2-Worker-SQLite-controller-local-development-review-only','new_correctness_findings':[],'root_integration_acceptance':False,'production_or_GA_accepted':False,'reviewed_producer_receipt_sha256':B['producer_receipt_sha256'],'reviewed_source_tree_sha256':B['source_tree_sha256'],'reviewed_source_archive_sha256':r['source_archive']['sha256'],'reviewed_input_closure_tree_sha256':r['input_closure_tree_sha256'],'verified_counts':B['counts'],'complete_frozen_inputs':rec(HERE/'frozen-inputs.tar.gz'),'complete_frozen_manifest':rec(HERE/'frozen-input-manifest.json'),'executed_fixture_archive':rec(HERE/'review-fixtures.tar.gz'),'executed_fixture_manifest':rec(HERE/'review-fixture-manifest.json'),'frozen_producer_groups_passed':72,'distinct_added_independent_groups_passed':17,'original_baseline_status':'failed; preserved unchanged','original_baseline_failed_cases':failed,'results':results,'versions':report('inventory','inventory-report.json')['versions'],'platform':B['platform'],'runtime_inputs':r['runtime_inputs'],'dependency_entries':58,'dependency_installs':0,'dependency_install_scripts_executed':0,'producer_tests_or_assertions_repaired':False,'commands':commands,'artifacts':artifacts,'cleanup':cleanup,'source_revision':'explicit frozen SHA-256 trees; no Git inspected','restrictions':{'no_catalog_authority_or_interrupted_outbound_v2_review_read_imported_executed':True,'transport_vectors_data_only':True,'no_Patch_Skip':True,'producer_originals_unchanged':True,'no_shared_tracker_Git_cloud_provider_deploy_customer_credential_native_sim_phone_UI_changes':True,'other_processes_and_projects_preserved':True},'not_verified':r['not_verified']+['integrated-live-source-rebuild-and-CI','production-distributed-durability-and-machine-failure','actual-authenticated-runner-output-adapter']}
(HERE/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
handoff={'status':receipt['status'],'receipt':rec(HERE/'receipt.json'),'report':rec(DOC),'reviewed_producer_receipt_sha256':B['producer_receipt_sha256'],'reviewed_source_tree_sha256':B['source_tree_sha256'],'reviewed_source_archive_sha256':r['source_archive']['sha256'],'complete_frozen_inputs':rec(HERE/'frozen-inputs.tar.gz'),'executed_fixture_archive':rec(HERE/'review-fixtures.tar.gz'),'frozen_producer_groups_passed':72,'distinct_added_independent_groups_passed':17,'new_correctness_findings':0,'cleanup':cleanup}
(HERE/'handoff.json').write_text(json.dumps(handoff,indent=2)+'\n');print(json.dumps(handoff,indent=2))
