from pathlib import Path
import hashlib,json,subprocess,time,sys,datetime,re
D=Path(__file__).resolve().parent
assert not (D/'review-seal.json').exists()
def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
start=time.monotonic();result=subprocess.run([sys.executable,str(D/'analyze.py')],cwd=D,text=True,capture_output=True,timeout=60)
(D/'analysis.stdout').write_text(result.stdout);(D/'analysis.stderr').write_text(result.stderr)
save(D/'analysis-receipt.json',{'command':[sys.executable,str(D/'analyze.py')],'timeout_seconds':60,'exit':result.returncode,'elapsed_seconds':time.monotonic()-start,'reaped':True,'python':sys.version,'python_executable':ident(Path(sys.executable)),'source':ident(D/'analyze.py'),'stdout':ident(D/'analysis.stdout'),'stderr':ident(D/'analysis.stderr')});assert result.returncode==0
run_names=['host-1','cross-1','controls-1','selected-1','selected-2'];records=[]
for name in run_names:
 run=D/'runs'/name;commands=json.loads((run/'commands.json').read_text());receipt=json.loads((run/'receipt.json').read_text())
 assert receipt['cleanup']['scratch_removed'] and receipt['cleanup']['children_reaped']
 for row in commands:
  assert row['timeout_seconds']==60 and row['reaped'] and not row['timed_out']
  for stream in ('stdout','stderr'):assert ident(run/(row['name']+'.'+stream))==row[stream]
  stdout=(run/(row['name']+'.stdout')).read_text();counts=re.findall(r' / (\d+) assertions',stdout)
  records.append({'run':name,'command':row['name'],'exit':row['exit'],'assertions':int(counts[-1]) if counts else None,'stdout':row['stdout'],'stderr':row['stderr']})
 assert not list(run.glob('owned-*'))
failures=[r for r in records if r['exit']]
assert [(r['run'],r['command']) for r in failures]==[('host-1','frozen-independent-identity-matrix'),('selected-1','selected-own-forward-native')]
assert len(records)==118
selected=[r for r in records if r['run']!='selected-1' and (r['run'],r['command'])!=('host-1','frozen-independent-identity-matrix')]
assert len(selected)==114 and all(r['exit']==0 for r in selected)
prepared=[r for r in selected if r['run']=='controls-1' and r['command'].startswith('prepared-independent-')];assert len(prepared)==16
original=[r for r in selected if r['command'].startswith('frozen-independent-')];assert len(original)==17
producer_new=[r for r in selected if r['run']=='host-1' and r['command'].startswith('membership-')];assert len(producer_new)==6 and sum(r['assertions'] for r in producer_new)==45255
for p in (D/'independent-controls').glob('*.java'):
 pre=D.parent/'preaccess/controls'/p.name
 if pre.exists():assert p.read_bytes()==pre.read_bytes()
old=(D/'independent-controls/IndependentPreservationCompletionControls.java').read_text();new=(D/'selected-controls/SelectedIdentityMembershipReviewControls.java').read_text();assert new.replace('SelectedIdentityMembershipReviewControls','IndependentPreservationCompletionControls').replace('"membership"})','"membership", "forward"})')==old
assert new.count('"membership", "forward"')==0
assert ident(D/'selected-controls/preservation-membership-forward-expectation-amendment.md')['sha256']=='7a61365486865d37b21d8e7462f6951d49d6b27826af6a962b94503c848a434c'
summary={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verdict':'scoped-positive-independent-host-source-review','root_acceptance_pending':True,'scope':'Selected exact ordered constructor/captured-scope membership; ordinary reachability/exploit and arbitrary private corruption recovery unestablished','candidate_seal_sha256':'620bfefe8cde4b63c2101db76af991fcc1933276f9c1e8d8d1aa1e3db8f0bf0e','product_tree':'a5e4888b96995bf768062bd9c2f1573dc440a4fe22270a205ab5550e79f625e4','complete_host_tree':'3ea68dc45ab5235edde6bdaea9b38045e6d60c6f8ae54583b5544a9e00c4d021','preaccess_seal_sha256':'1890771da4c76e8010a196a7cd2f5c4a9ebdef2f915878367e079c1c7accd863','independently_rehashed_candidate_members':13430,'independently_rehashed_preaccess_members':305,'only_product_delta':'NativeRenderer.java;15otherproduct/original86leaves/JNI/prior8tests unchanged','recorded_compiler_JVM_D8_disassembly_children':len(records),'selected_passed_commands':len(selected),'original52_groups_assertions':722,'producer_new_membership_groups':6,'producer_new_observed_assertions':45255,'unchanged_original_FH_C01_C02':True,'unchanged_PC_C16':'Pass335; FAILED_DONE/terminal/shared2/preservation2/candidateHeld2; actual A/C still held and C registered/busy after real B unwind','unchanged_independent_completion_groups_passed':17,'prepared_membership_groups':len(prepared),'prepared_membership_observed_assertions':sum(r['assertions'] for r in prepared),'selected_identity_derivative_assertions':17263,'selected_own_forward':['native:30direct+1249unchanged-helper','commit:29direct+1249unchanged-helper'],'root_selected_exact_forward_amendment_sha256':'7a61365486865d37b21d8e7462f6951d49d6b27826af6a962b94503c848a434c','original_identity_matrix_failed_historical_expectation_retained':True,'other_original_identity_rows_and_assertions_unchanged':True,'raw_failures':failures,'new_membership_allocation_failure':'Source+actual bytecode disposition only; no exact OOME-at-new injection claim','fresh_sdk37_javac_and_D8_min28':True,'actual_healthy_tail_instructions':{'finish':121,'Begin':31},'same_source_independent_compiled_artifacts_match_final_producer':True,'cleanup':'Every owned compiler/JVM/D8/disassembler child bounded60s/reaped; all owned scratch removed; classes/dex retained intentionally as evidence','native_UI_capture_or_process_inventory_started_or_queried':False,'canonical_native_OTA_release_or_GA_accepted':False,'limitations':['root canonical/source-pair5 integration decision separate','native/IME/EditorInfo/batch/selection/composition/focus/detach/accessibility/TalkBack/OEM/API28-35 not run','exact selection-getter callbacks remain unmodeled at unchanged leaves; adversarial Editable is host model','no arbitrary reflection/Unsafe or asynchronous VM interruption recovery guarantee','physical devices disconnected and all native/UI/capture tests paused','immutable separate-repository FieldLog/release/OTA/operations/GA pending']}
save(D/'summary.json',summary);save(D/'command-outcomes.json',records)
cases=json.loads((D.parent/'preaccess/controls.json').read_text())['cases'];coverage=[]
for c in cases:
 name=c['selection'];command='frozen-independent-journal-membership' if name=='unchanged-PC-C16' else 'prepared-independent-'+name
 row=next(r for r in selected if r['run']=='controls-1' and r['command']==command)
 coverage.append({**c,'candidate_status':'passed-unchanged','evidence':'runs/controls-1/'+command+'.stdout','assertions':row['assertions']})
save(D/'coverage.json',{'schema':1,'preaccess_cases':coverage,'source_obligations':{'PM-S01':['admission.json','independent-source-delta.json'],'PM-S02':['review.md','independent-source-delta.json','independent-bytecode-proof.json'],'PM-S03':['review.md','runs/controls-1/prepared-independent-captured-substitution.stdout','runs/host-1/membership-precommit-membership.stdout','runs/host-1/membership-endpoint-membership.stdout'],'PM-S04':['runs/controls-1/prepared-independent-reporter-reentry.stdout','runs/host-1/membership-report-reentry-membership.stdout','runs/selected-2/selected-own-forward-native.stdout','runs/selected-2/selected-own-forward-commit.stdout'],'PM-S05':['independent-bytecode-proof.json','independent-source-delta.json'],'PM-S06':['command-outcomes.json','independent-output-comparison.json','selected-controls/exact-derivative-check.json']},'selected_prior_row_classification':'Only exact own-forward inert-first-failed expectation superseded by root; unchanged original remains failed. All other identity assertions retained in exact derivative and pass; isolated own-forward native/commit and restored-boolean replay separately pass.'})
print(json.dumps({'verdict':summary['verdict'],'commands':len(records),'selected_passed_commands':len(selected),'prepared16_assertions':summary['prepared_membership_observed_assertions'],'other_original17_assertions':sum(r['assertions'] for r in original),'failures_retained':len(failures)},indent=2))
