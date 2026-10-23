#!/usr/bin/env python3
"""Bind observed host evidence without converting scope gaps into dynamic passes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads((ROOT/p).read_text())
canonical='verification/android-binding-stage4/runs/release-repaired-2/receipt.json'
base=read(canonical);base_source=Path(base['commands'][0]['cwd'])
product={p:d for p,d in base['source_files'].items() if p.startswith('capability-activation/Sources/MixerCapabilityActivation/') or p.startswith('native/android/signed-guest-ui/') or p.startswith('verification/android-binding-stage4/host-bridge/')}
for p,d in product.items():assert sha(ROOT/p)==d==sha(base_source/p),p
for p in ['transport.c','internal.h','include/mixer_ui_transport.h']:
 relative='native/android/signed-guest-ui/transport/'+p
 assert hashlib.sha256(subprocess.check_output(['git','show','d6505ac:'+relative],cwd=ROOT)).hexdigest()==product[relative]
contracts=['docs/android-signed-ui-binding-contract.md','docs/android-binding-stage4-seams.md','verification/android-binding-stage4-acceptance.json','verification/android-binding-stage4-contract/acceptance-matrix.json','verification/android-binding-stage4/host-bridge-contract.md','docs/android-binding-stage4-join-admission-addendum.md','verification/android-binding-stage4-join-admission/acceptance.json','docs/android-binding-stage4-host-scope-addendum.md']
expected={'docs/android-binding-stage4-join-admission-addendum.md':'8993c847984861bca4dd45a61f85eb711163f7c5e2d2bbed46bfd01d255820cb','verification/android-binding-stage4-join-admission/acceptance.json':'8c446cf9e263113877dba3750c41b42571cae13cc4546ffa40135017bb81258c','docs/android-binding-stage4-host-scope-addendum.md':'41946b0f773dd29280986c72d0526cd6cfc4b9d672015b83a4612c3e24d9247a'}
for p,d in expected.items():assert sha(ROOT/p)==d,p
seal={'schema_version':1,'status':'ready_for_independent_host_scope_review','completed_utc':datetime.now(timezone.utc).isoformat(),'canonical_source_receipt':canonical,'canonical_source_receipt_sha256':sha(ROOT/canonical),'canonical_source_manifest_sha256':base['source_tree_sha256'],'source_export':str(base_source),'product_and_fixed_fixture_files':product,'contracts_and_separate_amendments':{p:sha(ROOT/p) for p in contracts},'receipts':{},'debugger_proofs':{},'full_original_dynamic_matrix_pass':False,'normal_android_signed_ui_enabled':False,'native_witness_authority':False,'physical_devices_executed':False,'scope':'Actual private standalone host Swift/C binding prerequisite. Type-separated host receipts share the real common permit/Task.value, actual fixed native cleanup/return fences/destructor. No JNI/Looper/widgets/draw/health, signed core/Prepared integration or release authority.'}
def verify_build(path):
 r=read(path);source=Path(r['commands'][0]['cwd'])
 for p,d in product.items():assert r['source_files'].get(p)==d==sha(source/p),path+': '+p
 return r
def record(path,kind):
 r=read(path)
 for c in r.get('commands',[]):
  log=c.get('log');digest=c.get('log_sha256',c.get('sha256'))
  if log and digest:assert sha(ROOT/log)==digest,path+': '+log
 for p,d in r.get('artifacts',{}).items():assert sha(ROOT/p)==d,path+': '+p
 seal['receipts'][path]={'sha256':sha(ROOT/path),'kind':kind,'result':r.get('result',r.get('status'))}
 return r
modes=['debug','release','tsan']
for mode in modes:
 for suffix,kind,count in [('repaired-2','ordinary',39),('probe-repaired-3','actual-forwarded-C-boundary',10)]:
  path='verification/android-binding-stage4/runs/'+mode+'-'+suffix+'/receipt.json';r=record(path,kind);verify_build(path);assert len(r['cases_executed'])==count
 for suffix,kind in [('regression-'+mode+'-repaired-2','common-Apple-portable-regressions'),('supplemental-'+mode+'-final-1','additional-original-matrix-C-boundaries')]:
  path='verification/android-binding-stage4/runs/'+suffix+'/receipt.json';r=record(path,kind);assert 'passed' in r['result'];assert sha(ROOT/r['reference'])==r['reference_sha256']
for suffix,kind in [('symbols-repaired-2','product-only-symbol-controls-and-six-negative-links'),('android-repaired-2','official-API30-full-module-strict-native-link')]:
 path='verification/android-binding-stage4/runs/'+suffix+'/receipt.json';r=record(path,kind);assert 'passed' in r.get('result',r.get('status',''));assert sha(ROOT/r['reference'])==r['reference_sha256']
normal=['post-store','setup-alias','bind-return','waiter-exhaustion','progress-token-exhaustion','progress-sequence-exhaustion','gate-order']
for mode in modes:
 names={case:'lldb-'+mode+'-repaired-2' for case in normal}
 if mode!='release':names['lifetime-exhaustion']='lldb-'+mode+'-repaired-2'
 names['cancel-accepted']='lldb-'+mode+'-cancel-repaired-4' if mode!='release' else 'lldb-release-global-cancel-7'
 names['progress-tail']='lldb-'+mode+'-repaired-2' if mode!='release' else 'lldb-release-progress-repaired-4'
 names['reservation-hold']='lldb-'+mode+'-reservation-final-3' if mode!='release' else 'lldb-release-reservation-final-4'
 names['cleanup-wrong-entry']='lldb-'+mode+'-matrix-final-1'
 names['cleanup-wrong-generation']='lldb-'+mode+'-generation-final-2'
 names['stale-cleanup-replay']='lldb-'+mode+'-stale-final-3'
 for case,directory in names.items():
  actual='lifetime-exhaustion-after-cycle' if case=='lifetime-exhaustion' and mode=='release' else case
  folder='verification/android-binding-stage4/runs/'+directory;proof_path=folder+'/'+actual+'.json';r=read(proof_path);assert r['result']=='passed',proof_path
  launcher=record(folder+'/receipt.json','LLDB-instrumented-mode-specific')
  build=verify_build(launcher['reference']);assert sha(ROOT/launcher['reference'])==launcher['reference_sha256']
  key=mode+'/'+case;seal['debugger_proofs'][key]={'path':proof_path,'sha256':sha(ROOT/proof_path),'launcher_receipt':folder+'/receipt.json','launcher_contains_other_failed_attempts':'failed' in launcher.get('result',''),'build_receipt':launcher['reference'],'mode':mode,'instrumented':True}
failed_counter='verification/android-binding-stage4/runs/lldb-release-lifetime-final-6'
failed=read(failed_counter+'/lifetime-exhaustion-after-cycle.json');assert failed['result']=='failed'
launcher=record(failed_counter+'/receipt.json','retained-failed-optimized-Release-private-counter-inspection')
verify_build(launcher['reference']);assert sha(ROOT/launcher['reference'])==launcher['reference_sha256']
seal['mode_limitations']={'release/lifetime-exhaustion':{'status':'dynamic_failure-injection_not_executed','failed_attempt':failed_counter+'/lifetime-exhaustion-after-cycle.json','failed_attempt_sha256':sha(ROOT/(failed_counter+'/lifetime-exhaustion-after-cycle.json')),'reason':'Actual private static storage and initialized class reference were located, but optimized Release debug type has no usable field location. No guessed heap offset or counter write was performed. Actual Debug/TSan counter exhaustion proofs remain distinct; Release source audit is not a dynamic pass.'}}
ci_path='verification/android-binding-ci/qualified-1/receipt.json'
ci_sha='f1afd01d5e14084076ac20bcf23ff68abb3213d5d48e102f3c71c9f657d51efd'
assert sha(ROOT/ci_path)==ci_sha
seal['root_fresh_source_CI']={'path':ci_path,'sha256':ci_sha,'scope':'Separate root-owned fresh SwiftPM Debug/Release/TSan qualification;39 ordinary scenarios each, exact SDK dependencies rebuilt and locked clean. This does not replace the literal/debugger matrix or confer JNI qualification.','accountable_acceptance':'root pending independent final host/CI review'}
seal['tooling_files']={str(p.relative_to(ROOT)):sha(p) for p in HERE.iterdir() if p.is_file() and p.name not in ['evidence.json','acceptance-results.json']}
seal['limitations']=['TSan rebuilds actual activation/transport/fixed fixture but retained real SDK prerequisite objects are not TSan-instrumented; root fresh-SwiftPM CI receipts are a separate qualification.','LLDB and symbol-renaming C wrappers are separate instrumented executions; ordinary results are not inferred from them.','Actual inherited TaskExecutor investigation failed and is retained; earlier scheduler hold occurs before terminal store and is narrower than the successful literal post-store proofs.','Positive visible-window regression remains skipped; physical devices remain disconnected and pending.','S4-21 dynamic stale JNI event/probe/attachment delivery remains pending stage5. There is no corresponding host submission API.','S4-29 optimized Release Swift lifetime-counter exhaustion remains dynamically unexecuted: exact initialized storage was located but no usable field debug type was available. Debug/TSan actual exhaustion passed. No Release dynamic pass is inferred.','No caller numeric cleanup-serial input exists. Checked exhaustion and replay of a genuine immutable different-facade cleanup are distinct executed cases; private final-once construction and lookup-disable are source/type checks.']
original=read('verification/android-binding-stage4-contract/acceptance-matrix.json')
observed={
1:('post-store; actual common Task.value; no-hold ordinary controls','All three modes park actual presentation worker after terminal store and unlock, before actual Task return. Earlier pre-store scheduler proof is historical only.'),
2:('single-join, wrong-final-owner, ordinary/testable negatives','64 concurrent finish reentries during actual native hold; immutable exact result; wrong/missing owners cannot consume matching permits.'),
3:('destructor, drop-prepared, drop-transferred, drop-bound-late','Actual resource deinit is held after C facade reclaim; capacity stays occupied; abandonment scalar-closes/quarantines and retains actual resource chain.'),
4:('setup-alias, helper-alias, leased-ingress, ui-leave','Actual setup strong local and leased UI helper are held independently; real helper return precedes counted decrement and C leave.'),
5:('fast, rendezvous-reuse','Real complete precedes real request return; actual successor waiter after C slot reuse rejects stale owner, duplicate/wrong waiter and wrong kind.'),
6:('request-rejection, cancel-accepted','Actual C BUSY rejection; separately cancel exact owned real Task after accepted native RETIRE is held, then original native release and Task.value/final cleanup.'),
7:('lost-before','Actual first BUSY return held before progress registration while real fences advance.'),
8:('lost-after','Actual mandatory second reclaim held after exact progress registration; original operation/result forwarded once.'),
9:('no-progress','Actual two reclaim attempts remain parked with one continuation while later callback is held; only real later progress completes.'),
10:('capacity, gate-order, reservation-hold','Concurrent16/17 ordinary admission; held actual reserved Swift record/C-ID-zero boundary; actual second caller blocks behind admission. After original resumes unchanged all16 real owners publish and destruct. This does not claim15 simultaneously blocked cooperative workers.'),
11:('facade-acquire-failure, endpoint-acquire-failure, c-facade-exhaustion','Actual empty rollback and live-facade uncertainty. Actual checked facade exhaustion creates sticky fault before any facade identity; proven-empty obligation returns without nonexistent consumer join.'),
12:('cancelled-preparation, bind-failure, acquisition failures','Actual post-acquire cancellation joins the already-created prebind Task in the same preparation frame. Source audit identifies cancellation as the recoverable post-task preparation boundary; other sealed invariant failures are not invented as success-capable injection points.'),
13:('close-before-bind, setup-alias, bind-return','Close before bind, during actual setup helper, and after bind gate immediately before returned installation; exact caller ownership remains necessary.'),
14:('fallback, fallback-ids, fallback-before-fence, post-store','Real fallback uses fresh owner/lifetime/tuple and old immutable result. Actual successor admission is rejected while old native finish is held. Separate literal Task-return hold verifies same common join; signed concrete-attempt fallback integration remains stage6.'),
15:('queued-close, helper-alias','Queued hinted PRESENT becomes one RETIRE without extra hint; claimed PRESENT close causes exactly one later RETIRE from the same Task.'),
16:('fault-write, fault-read, fault-leave, late-progress-fault, fault-after-join','Actual syscall faults fan out across prebind/delivery/native states. Fault-before-join admission leaves C joined0; genuine already-admitted joined1 cannot release uncertain ownership after later fault.'),
17:('failed-retire, partial-retire, missing-native, acquisition controls','Actual failed/partial fixed cleanup and real missing native owner never become successful final evidence or known-empty cleanup.'),
18:('late-before','Final close before actual helper final-decision sample clears exact final state in the same real entry without unnecessary terminal endpoint.'),
19:('late-after, late-after-completion, after-reclaim','Separate actual final-close latches after nonfinal decision, after real Swift completion with C completion tail held, and after endpoint absence; one sequential terminal endpoint completes real cleanup.'),
20:('terminal-capacity, terminal-retire-failure','Actual terminal endpoint capacity failure and actual terminal cleanup failure stay immutable/pinned;64 concurrent reentries create no retries.'),
21:('after-reclaim, fallback-ids, privacy negatives','Actual between-attempt scalar close, terminal cleanup and fresh facade-long tuple IDs. No host event/probe/attachment submission API grants stale-token authority; dynamic native stale delivery is pending stage5.'),
22:('leased-ingress, nested','Actual C INGRESS/CLEANUP before weak promotion; pending/no-pending-byte nested callback rejection, wrong thread rejection, counted UI alias and reentrant close postcheck.'),
23:('helper-alias, ui-leave, completion, no-progress, late-entry','Independent actual inner helper, Swift-before-leave, completion, platform and later-callback return holds; no synthetic return fence.'),
24:('late-entry','Endpoint absent while later accepted real CLEANUP holds a newer entry fence; lookup disabled prevents resource promotion; facade waits actual later return.'),
25:('progress-tail, progress','Actual real continuation resume and consumed local/outgoing copy coexist with final destruction. Release uses exact frozen loop register/memory and later ARC-release bindings; all modes resume original native worker unchanged.'),
26:('cleanup-wrong-facade, cleanup-wrong-endpoint, cleanup-wrong-lifetime, cleanup-wrong-entry, cleanup-wrong-generation, stale-cleanup-replay, partial-retire, cleanup-exhaustion','Actual wrong key/entry/native generation reject at existing boundaries after real clear. Genuine immutable cleanup from a completed different facade is replayed without field construction/mutation and rejected. Numeric serial-input API is absent; actual exhaustion and final-once source/type checks remain distinct.'),
27:('ordinary-private-types, testable-sealed-authority, root independent authority clients','Actual host linkage; incompatible common/Apple receipt and installation types; private raw lifetime/permit and sealed constructors reject; root reviews closed backend Apple guards before permit/receipt construction.'),
28:('ui-leave, late-entry, destructor, stale-cleanup-replay','Actual helper/entry tails held before destruction and lookup-disabled late CLEANUP cannot promote resources. Atomic evidence/lookup-disable is one real record lock operation; retained final shells are scalar.'),
29:('c-facade-exhaustion, c-endpoint-exhaustion, c-entry-exhaustion, cleanup-exhaustion, lifetime-exhaustion, waiter-exhaustion, progress-token-exhaustion, progress-sequence-exhaustion','Actual C identity/entry overflow and other checked Swift counters fail closed in all three modes. Actual Swift lifetime-counter exhaustion passed Debug/TSan. Optimized Release lifetime-counter injection was not executed: initialized exact storage was located but no usable debug field location was available; its source audit and retained failed attempt are not a dynamic pass.'),
30:('cycles, capacity, single-join','64 repeated actual fallback/close cycles, fixed C occupancy/waiter maxima, actual warmed/final process FD/thread inventory and actual native allocation/destructor counts. Swift runtime worker-thread variation is reported, not mistaken for owner threads.'),
31:('common-xctests, apple-models, portable-tests','Full activation rebuilt with unchanged existing concrete Apple/Prepared/core source plus scoped common backend. Existing actual Task/move/observation regressions pass; portable preparation rejects. Positive visible window remains skipped.'),
32:('product-only symbols, six required-symbol omission links, official API30 strict link','Actual product-only Swift/C objects exclude verification exports/controls; each omitted required hook/native helper fails real link. Official Swift6.3.3/NDK API30 compiles full actual modules and strictly links actual immutable VM/host fixture; no device/Looper/JNI claim.')}
rows=[]
for entry in original['cases']:
 number=int(entry['id'][3:]);cases,note=observed[number]
 row=dict(entry);row.update({'host_result':'evidence_bound_for_review' if number!=21 else 'host_scope_evidence_bound_dynamic_native_subcase_pending','executed_evidence':cases,'observed_scope':note,'required_modes':['debug','release','tsan'],'source_or_type_checks_remain_distinct':True})
 if number==21:row['dynamic_pending_stage5']=['Stale JNI input/event, probe and attachment delivery through real future native submission APIs.']
 if number==29:
  row['host_result']='host_scope_evidence_bound_optimized_Release_lifetime_counter_subcase_unexecuted'
  row['mode_limitations']={'release/lifetime-exhaustion':seal['mode_limitations']['release/lifetime-exhaustion']}
 rows.append(row)
assert len(rows)==32
matrix={'schema_version':1,'status':'bound_observed_host_evidence_for_independent_review','canonical_receipt':canonical,'canonical_receipt_sha256':sha(ROOT/canonical),'scope_addendum_sha256':expected['docs/android-binding-stage4-host-scope-addendum.md'],'join_admission_addendum_sha256':expected['docs/android-binding-stage4-join-admission-addendum.md'],'full_original_dynamic_matrix_pass':False,'cases':rows,'separate_pending_gates':original['separate_pending_gates'],'note':'Scenario counts are not a full original dynamic32 pass. Root owns acceptance; S4-21 native dynamic delivery and unavailable numeric-serial input remain explicitly distinguished. Every selected proof retains its own mode/source/binary/driver scope in evidence.json.'}
(HERE/'acceptance-results.json').write_text(json.dumps(matrix,indent=2)+'\n')
seal['acceptance_results_sha256']=sha(HERE/'acceptance-results.json')
(HERE/'evidence.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps({'evidence_sha256':sha(HERE/'evidence.json'),'matrix_sha256':sha(HERE/'acceptance-results.json'),'source_manifest_sha256':base['source_tree_sha256'],'status':seal['status']}))
