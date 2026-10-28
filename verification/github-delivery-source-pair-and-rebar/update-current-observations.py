"""One-shot sanitized FieldLog status addendum; never executes saved review helpers."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import platform
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
OBS = ROOT / 'verification/console-session-and-checkout-root-review'
NOW = datetime.now(timezone.utc).isoformat()

def load(p): return json.loads(p.read_bytes())
def save(p,v):
    with p.open('x') as f: json.dump(v,f,indent=2); f.write('\n')
def row(p):
    b=p.read_bytes(); return {'path':str(p.relative_to(ROOT)), 'bytes':len(b), 'sha256':hashlib.sha256(b).hexdigest()}
def binding(p):
    b=p.read_bytes(); return {'name':p.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
assert not (OUT/'current-observations-addendum.json').exists(), 'One-shot; do not replay'
bp=Path('/Users/andreyyurlov/Documents/dev/fieldlog/.codex-public-baseline-ci-review/review-receipt.json')
ip=Path('/Users/andreyyurlov/Documents/dev/fieldlog/.codex-public-fields-integration/receipt.json')
b=load(bp); i=load(ip)
assert binding(bp)['sha256']=='7bb06c466ae3e18cd51801d24a213485d569ea300489dd9fea8a605b35ea5a6b'
assert binding(ip)['sha256']=='e1d4441fcfc06469b639c41c8db646479cbadadba1179007df4168b211837991'
assert b['runID']==40762789024 and (b['tests']['started'],b['tests']['passed'],b['tests']['failed'])==(26,25,1)
assert b['remoteCleanup']['verified'] and len(b['remoteCleanup']['commands'])==16
assert i['commit']=='4d17c92656d3a7574506f06414bc2f08af469122' and i['run']['databaseId']==40765792113
assert i['pathsCommitted']==12 and i['authoredTests']==38 and i['locallyExecutedTests']==0
baseline={
 'schema':1,'at':NOW,'scope':'Sanitized saved host-result review only; source, raw logs, local evidence and signed artifact URLs excluded',
 'repository':'snowdamiz/fieldlog','private':False,'commit':b['app']['revision'],'tree':b['app']['tree'],
 'run_id':b['runID'],'run_url':'https://github.com/snowdamiz/fieldlog/actions/runs/40762789024',
 'status':'reviewed failed host tests; no development acceptance','source_entries_verified':42,
 'all_artifact_source_entries_match_commit_objects':b['app']['allArtifactSourceEntriesMatchCommitObjects'],
 'host':{k:b['workflow'][k] for k in ['Xcode','AppleSwift','host']},
 'tests':{k:b['tests'][k] for k in ['expected','started','passed','failed','buildSucceeded','commandExitCode']},
 'first_failure':'The responsible value is preserved verbatim; one test expected trimming. The assertion was selected for correction without changing persistence behavior.',
 'public_SDK':b['publicSDK'],'unreached_checks':b['unreachedChecks'],
 'new_remote_commands':16,'all_new_remote_command_cleanup_verified':True,'remote_signals_sent':0,
 'source_review_receipt':binding(bp),'historical_pending_observation_preserved':True,
 'prior_local_compiler_cleanup_hold_unchanged':True,'local_compiler_native_UI_capture_or_custody_actions':False,
 'published_package_D_milestone_or_GA_accepted':False}
delivery={
 'schema':1,'at':NOW,'scope':'Sanitized saved source delivery and dispatch observation only; no FieldLog source, diff, raw log, local evidence or signed artifact URL copied',
 'repository':'snowdamiz/fieldlog','private':False,'commit':i['commit'],'tree':i['tree'],'parent':i['parent'],
 'paths_committed':i['pathsCommitted'],'public_SDK_pin':i['publicSDKPin'],
 'run':i['run'],'dispatches_made':i['dispatchesMade'],'authored_host_tests':38,'locally_executed_tests':0,
 'observed_host_test_passes':None,'status':'source delivered; exact-commit host CI in progress at saved observation',
 'source_reviewed':True,'applied_and_pushed':True,'source_delivery_receipt':binding(ip),
 'all_own_new_commands_reaped_and_groups_absent':i['allOwnNewCommandsReapedAndGroupsAbsent'],
 'local_compiler_or_native_runtime_launched':False,'prior_held_resources_probed_or_touched':False,
 'limitations':i['limitations'],'host_or_native_published_package_D_milestone_or_GA_accepted':False}
bpath=OBS/'fieldlog-public-baseline-result.json'; ipath=OBS/'fieldlog-public-fields-delivery-observation.json'
save(bpath,baseline);save(ipath,delivery)
refs={'baseline_host_result':row(bpath),'public_fields_delivery':row(ipath)}
w=load(ROOT/'work-graph.json');g=load(ROOT/'gates/ga.json')
a=w['packages'][16]['activePublicSDKFlow']
a['current_public_host_result']=baseline
a['current_public_fields_delivery']=delivery
a['current_public_status_receipts']=refs
a['public_SDK_adoption_draft_state']['historical_observation']=True
a['public_SDK_adoption_current_state']={'files':12,'authored_tests':38,'source_reviewed':True,'applied':True,'pushed':True,'host_result':'pending at saved in-progress observation','locally_executed_tests':0,'commit':i['commit'],'run_id':40765792113}
for ref in refs.values():
 if ref['path'] not in w['packages'][16]['evidence']: w['packages'][16]['evidence'].append(ref['path'])
r=w['fieldlogRepository']['remoteDelivery']
old={k:v for k,v in r.items() if k not in ['priorPrivateHostWorkflow','priorPublicBaselineWorkflow']}
r['priorPublicBaselineWorkflow']=old
r.update({'codeRevision':i['commit'],'documentationRevision':i['commit'],'hostWorkflowRun':40765792113,'hostTestsExecuted':None,'expectedHostTests':38,'state':'12 reviewed source paths pushed publicly; exact-commit host CI in progress at saved observation','sanitizedStatusReceipt':refs['public_fields_delivery'],'priorPublicBaselineResult':refs['baseline_host_result']})
comparison=w['packages'][7]['empiricalCacheDeadlineCampaign']['architecture_comparison']
comparison['review_status_addendum']={'original_review':'R1 capacity/identity stop and R2 fuel consistency require correction','corrected_pure_controls':38,'correction_status':'under independent review','compiled_or_runtime_runs':0,'runtime_or_delivery_selected':False}
g['gates'][1]['empiricalCacheDeadlineCampaign']['architecture_comparison']=comparison
for n in [5,10,31]:
 g['gates'][n]['currentFieldLogHostObservation']=refs
 if n==10:
  for ref in refs.values():
   if ref['path'] not in g['gates'][n]['evidence']:g['gates'][n]['evidence'].append(ref['path'])
assert len(w['packages'])==18 and len(g['gates'])==38
assert sum(x['status']=='running' for x in g['gates'])==8
assert sum(x['status']=='planned' for x in g['gates'])==30
assert sum(x['status']=='verified' for x in g['gates'])==0
for p,d in [(ROOT/'work-graph.json',w),(ROOT/'gates/ga.json',g)]:p.write_text(json.dumps(d,indent=2)+'\n')
text=('Current delivery addendum: FieldLog public baseline `4062256` built successfully and ran all 26 host tests: 25 passed and one failed because the test expected trimmed text while persistence preserves it. All 42 captured source entries match the commit; the fetched SDK is `d8c6965a`, tree `76261ef6219ef09713f6a76708d783c48d88a20a`. Post-test consumed-SDK, after-lock and final source checks were not reached, so this is not an accepted host slice. All 16 new remote command groups closed. The reviewed 12-path public-fields integration is now committed and pushed as `4d17c926`, tree `c1a7af912e145556491aadb33a90ddac785e88c1`; its single exact-commit host run `40765792113` was in progress at the saved observation, with 38 authored tests and no local compiler run. The earlier pending/draft observations remain historical. Sanitized current observations are [the baseline result](verification/console-session-and-checkout-root-review/fieldlog-public-baseline-result.json) and [the source delivery](verification/console-session-and-checkout-root-review/fieldlog-public-fields-delivery-observation.json). The architecture comparison correction has 38 pure controls and remains under independent review after capacity/identity-stop and fuel-consistency findings; it has zero compiled/runtime runs and is excluded from this delivery. Native/capture, all local custody and UnitA holds remain active; gates remain 8 running, 30 planned, 0 verified.\n\n')
for name,anchor in [('PLAN.md','## Resumed checkpoint\n\n'),('STATUS.md','Checkpoint `56ff14c`')]:
 p=ROOT/name;s=p.read_text();assert 'Current delivery addendum:' not in s
 if name=='PLAN.md':s=s.replace(anchor,anchor+text,1)
 else:s=s.replace(anchor,text+anchor,1)
 p.write_text(s)
save(OUT/'current-observations-addendum.json',{'schema':1,'at':NOW,'command':['python3','-B',str(Path(__file__).relative_to(ROOT))],'tool':{'python':platform.python_version()},'base':'56ff14c925168284761c5aca4f0bd4129cf3c995','tree':'75989099938ed5256c4144cbc9e62979ee323183','observations':refs,'metadata':[row(ROOT/p) for p in ['PLAN.md','STATUS.md','work-graph.json','gates/ga.json']],'historical_checkpoint_and_receipts_preserved':True,'compiled_native_runtime_capture_or_custody_actions':False,'GA_accepted':False})
print(json.dumps({'metadata_updated':4,'new_sanitized_observations':2,'GA_verified':0}))
