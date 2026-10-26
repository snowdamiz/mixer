#!/usr/bin/env python3
"""Summarize this lane's actual final receipt without granting integration authority."""
import hashlib,json,pathlib,sys
from datetime import datetime,timezone
HERE=pathlib.Path(__file__).resolve().parent
FINAL='runs/rust-1-99-final2/receipt.json'
def need(v,m):
 if not v:raise RuntimeError(m)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):(HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
r=json.loads((HERE/FINAL).read_bytes());need(r['status']=='passed-host-fixture-check'and not r['errors'],'Final receipt not passed')
need(r['runner']['sha256']==sha(HERE/'check_cache_state.py'),'Runner changed')
method_counts={};api={};file_counts={}
for mode,x in r['modes'].items():
 method_counts[mode]={k:v['count']for k,v in x['methods'].items()};need(method_counts[mode]=={'host':84,'producer':108,'independent':98,'controls':94},'Method closure')
 spans=sum(len(d['primary'])for p in x['api']for d in p.get('diagnostics',[]));positives=sum(p.get('executed',False)for p in x['api']);need(len(x['api'])==25 and positives==2 and spans==38,'API closure')
 api[mode]={'dispositions':25,'positive_executions':positives,'negative_diagnostic_dispositions':23,'exact_primary_spans':spans}
 c=x['host_File_cases'];need(len(c)==31 and sum(z['aggregate_present']for z in c)==29 and len(x['host_layouts'])==23,'File/layout closure')
 need([{k:v for k,v in z.items()if k!='capture_tree_sha256'}for z in c]==[{k:v for k,v in z.items()if k!='capture_tree_sha256'}for z in x['controls_File_cases']],'Host and full derivative actual File results differ')
 file_counts[mode]={'distinct_cases':31,'public':29,'public_full32':27,'public_outer_errors_no_aggregate':2,'private_poison_full32':2,'private_public_reachability_credit':0,'host_and_controls_captures_agree':True,'layouts':23}
need(len(r['commands'])==103 and all(c['child_returned']and c['owned_group_gone']and not c['timed_out']and not c['output_capped']for c in r['commands']),'Command closure')
need(r['cleanup']['removed']and all(v['passed']for v in r['postflight'].values()),'Postflight/cleanup')
controls=(HERE/'runner-controls-final.stderr').read_text();need('Ran 22 tests' in controls and controls.endswith('OK\n'),'Focused controls incomplete')
controls_receipt={'command':['python3','-B','verification/swift-cache-state-ci-preparation/test_runner.py'],'tool':{'path':sys.executable,'resolved_path':str(pathlib.Path(sys.executable).resolve()),'sha256':sha(pathlib.Path(sys.executable).resolve()),'version':sys.version},'runner_sha256':sha(HERE/'check_cache_state.py'),'test_source_sha256':sha(HERE/'test_runner.py'),'stdout_sha256':sha(HERE/'runner-controls-final.stdout'),'stderr_sha256':sha(HERE/'runner-controls-final.stderr'),'exit':0,'methods':22,'scope':'Focused host runner controls, including path/source/manifest/diagnostic/layout/case-count/environment/fixed compiler identity, actual owned timeout/output cap/descendant cleanup and hash-before-delete; no native runtime/UI/capture or broad process discovery'}
save('runner-controls-receipt.json',controls_receipt)
proof={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-B',str(pathlib.Path(__file__).resolve())],'python':sys.version,'builder_sha256':sha(pathlib.Path(__file__).resolve()),'status':'isolated closed fixture CI candidate qualified on observed local compiler; independent runner review pending','final_receipt':FINAL,'final_receipt_sha256':sha(HERE/FINAL),'source_revision':r['source_revision'],'source_tree':r['source_tree'],'runner_sha256':r['runner']['sha256'],'pack_manifest_sha256':r['pack_manifest_sha256'],'pack_tree_sha256':r['pack_tree_sha256'],'compiler':r['rustc'],'method_counts':method_counts,'base_normalized_distinct_methods_per_mode':122,'private_additional_methods_per_mode':10,'combined_distinct_methods_per_mode':132,'duplicated_common_methods_per_pair':84,'test_method_invocations_per_mode':384,'API':api,'File_and_layouts':file_counts,'owned_commands':103,'active_seconds':r['active_elapsed_seconds'],'total_seconds':r['elapsed_seconds'],'longest_child_seconds':max(c['elapsed_seconds']for c in r['commands']),'per_child_limit_seconds':60,'active_deadline_seconds':600,'cleanup_allowance_seconds':60,'products_hashed_before_removal':len(r['cleanup']['products_hashed_before_removal']),'all_owned_groups_returned':True,'scratch_removed':True,'source_tool_pack_output_postflight_passed':True,'full_derived_source_count':len(r['derivative']['source_rows']),'focused_runner_controls':22,'historical_full_producer_Debug_60s_timeout_remains_failed':True,'performance_equivalence_claimed':False,'failed_candidate_retained':'runs/rust-1-99-attempt1/receipt.json','superseded_pass_retained':'runs/rust-1-99-attempt2/receipt.json','checkout_identity_failure_retained':'runs/rust-1-99-final/receipt.json','Rust_1_98_1_qualification_pending':True,'canonical_CI_or_engine_integration_selected':False,'arbitrary_public_File_reachability_qualified':False,'native_runtime_UI_capture_or_device_used':False,'GA_qualified':False}
save('qualification.json',proof)
x=json.loads((HERE/'authoring-corrections.json').read_bytes());x['first_final']={'status':'failed-closed-checkout-identity','receipt':'runs/rust-1-99-final/receipt.json','before_revision':json.loads((HERE/'runs/rust-1-99-final/receipt.json').read_bytes())['source_revision'],'after_revision':json.loads((HERE/'runs/rust-1-99-final/receipt.json').read_bytes())['source_revision_after'],'cause':'Root committed while this invocation was active; no candidate/source/pack/tool changes; all fixture checks and owned cleanup passed, but complete invocation remains failed','runner_changed_for_retry':False};save('authoring-corrections.json',x)
readme=f'''# Closed scalar-cursor cache-state CI candidate

This isolated candidate passes the exact selected three-file safe-File fixture
closure on actual Rust {r['rustc']['identity']['release']} / aarch64-apple-darwin.
Its final unchanged runner completed 103 owned commands in {r['elapsed_seconds']:.3f}s
(active {r['active_elapsed_seconds']:.3f}s; longest child {proof['longest_child_seconds']:.3f}s),
within fixed 600-second active / 60-second cleanup and 60-second child limits.
The source is unchanged f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b,
including its historical comments. The parent analyzer and envelope are exact.

The closed pack contains 86 members / 8,836,866 bytes, including 78 selected
source/fixture files (17 original source/oracles, 25 API sources, 34 historical
framing vectors/sidecars, two selected private control sources). Manifest
`{r['pack_manifest_sha256']}` and tree
`{r['pack_tree_sha256']}` are pinned in the runner. No predecessor/failure tree
or historical runner is imported or executed. Existing framing/envelope CI
packs/runners/tests are unchanged.

Per Debug and optimized mode, fresh exact inventories execute 84 host, 108
producer, 98 inherited-independent, and 94 full derivative methods. Their
common overlap is 84; the base normalized union is 122. Three additional
producer private controls and seven independent methods bring the distinct
union to 132, with 384 method invocations per mode. The derivative copies all
17 exact source/oracle files plus two control sources and appends only the
fixed cfg(test) module declarations. All 94 derivative methods run, with zero
ignored/filtered tests. Exact 19-file derived source inventories match before
and after execution. Debug producer's 108 methods run as 17 exact named roots
(each 107 filtered) plus the 91-method embedded group (17 filtered), with disjoint
complete coverage. The original producer single-command 60-second timeout
remains failed historical evidence; grouped coverage is not performance equivalence.

Per mode all 25 API dispositions pass: two positive executions and 23 intended
compile refusals with all 38 exact primary source spans. The independently
predeclared API contract's two authoring expectation corrections are retained
in the independent lane; this pack pins its validated final probe bytes/contract.
All 23 complete accounting layouts match the fixed inventory, including the
488-byte aggregate and Result. Host and full derivative executions capture the
same 31 distinct exact File cases: 29 public cases (27 full32 plus two outer
errors without aggregate) and two private injected poison cases. Complete
result first lines and every input/report hash match. Dynamic input stamp
observations are retained as observed values. The ten added private methods
also check fixed finite output counters and independent complete layout values;
none grants general public File reachability credit.

Twenty-two focused runner controls pass. Every owned child/group returned,
all {proof['products_hashed_before_removal']} final compiler products were hashed before deletion,
and owned scratch is absent. Verified content retention preserves test data and
errors by hash; commands retain raw stdout/stderr, exact argv, tool versions,
PID/PGID, source revision/tree, outputs and terminal exits. Pre/post checks bind
runner, interpreter and compiler launchers, actual compiler, full closed pack,
full derived sources and output identity. Caller compiler/test/scratch hooks
are scrubbed and RUSTUP_AUTO_INSTALL=0 is forced before launcher commands.
The scope assumes a quiescent trusted checkout and makes no adversarial custody claim.

The first candidate failed before inherited API compilation because a fixed
probe identifier contained a slash in an owned command/product name; raw
failure and the exact failed runner are retained under runs/rust-1-99-attempt1.
The corrected complete success runs/rust-1-99-attempt2 is superseded by stricter
source/output/negative-child checks. The first final invocation passed all
fixture checks but remains failed because root changed HEAD/tree during it;
runs/rust-1-99-final preserves this checkout-identity failure. Root then held Git
mutations and the unchanged final runner passed under runs/rust-1-99-final2.
No engine or pack source changed between these attempts.

This candidate is now ready for fresh independent runner review. Rust 1.98.1
remains pending; no toolchain installation or fallback search occurred. The
source feature prerequisite slice::as_chunks stabilized in Rust 1.88 per official
documentation, but that is not a whole-closure compiler qualification.
Canonical CI integration/workflow placement is not selected. Root must reserve
the full eleven-minute allowance in the chosen 30-minute job and assess actual
job timing (current Swift core about12m24s incl checkout; capability about18m30s).
No source-work/logical-lifetime proof is newly measured here; root's conditional
source model remains separate from compiler ABI/stack/allocator/RSS claims.
No arbitrary public File admission, live VM/target, native runtime/UI/capture,
phones, signing/store, immutable published-package separate-repository FieldLog,
customer/operational or GA gate is qualified. Phones remain disconnected and
native runtime/UI/capture remains paused.

For read-only closure verification run python3 -B verify_seal.py. Never replay
writing runners/builders inside this frozen packet. For independent actual
execution, copy only exact check_cache_state.py and the complete pack directory
to a separately owned directory under the same original repository, and create
an empty runs directory there. Supply the existing actual compiler path and a
fresh output directly under that copy's runs directory. No pack/hash/readiness/
budget/expectation override exists. The runner derives ROOT as HERE.parents[1];
for a nested owned copy that may be the original repository's verification
directory. The four git rev-parse commands remain read-only and discover the
same original Git checkout through parent directories. Do not initialize,
modify, or replace Git, and do not bypass before/after checkout identity checks.
Coordinate a quiescent repository with root for the complete invocation.
'''
(HERE/'README.md').write_text(readme)
print(json.dumps({'status':proof['status'],'commands':103,'total_seconds':proof['total_seconds'],'longest_child_seconds':proof['longest_child_seconds'],'distinct_methods_per_mode':132,'API_dispositions':50,'products_hashed_removed':proof['products_hashed_before_removal']}))
