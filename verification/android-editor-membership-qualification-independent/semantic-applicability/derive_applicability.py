#!/usr/bin/env python3
"""Source/actual-bytecode applicability candidates; preserves every proposed280 ID."""
from pathlib import Path
import hashlib,importlib.util,json,sys,collections
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent;R=D.parent;P=R/'semantic-review/input';C=R/'derivative-review/run-corrected/classes'
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('applicability_classfile',R/'preaccess/interface-v3/classfile.py');cf=importlib.util.module_from_spec(spec);spec.loader.exec_module(cf)
original=json.loads((P/'active-semantic-obligations.json').read_bytes());reference=json.loads((P/'reference-obligations.json').read_bytes())
classes={}
for p in C.rglob('*.class'):
 c=cf.parse(p.read_bytes())
 if c['source_file'] in reference['exact16_source_map']:classes[c['class']]=(p,c)
rows=[]
for s in original['subjects']:
 p,c=classes[s['class']];m=next(v for v in c['methods'] if v['name']==s['method'] and v['descriptor']==s['descriptor'])
 assert identity(p)['sha256']==s['class_sha256'];source=P/'accepted-source'/c['source_file'];assert identity(source)==reference['exact16_source_map'][c['source_file']]
 calls=[i for i in m['instructions'] if 0xb6<=i['opcode']<=0xba];profile='pending-source-specific-callback-or-enclosing-outcome-review';cases=['Keep all original categories and required cases pending source-backed per-case disposition. No removal or behavior credit.'];reason='Contains actual invocations; no no-callback inference is made from an adjacent event, name or static identity.'
 witness_lines=sorted({v['line'] for v in m['lines']});lines=source.read_text().splitlines();excerpt=[{'line':n,'text':lines[n-1]} for n in witness_lines if 0<n<=len(lines)]
 if m['access']&0x0400:
  profile='abstract-interface-contract-no-body';reason='The emitted method is ACC_ABSTRACT and has no Code body. Source declares an interface contract; an actual concrete implementation/dispatch must supply behavioral evidence.'
  cases=['Preserve exact interface descriptor and bind each selected actual implementing receiver/class/method.','No abstract-body invocation or native callback result may be invented; implementation source/state qualification remains separate and required.']
 elif c['access']&0x4000:
  profile='generated-enum-value-support';reason='Actual class is ACC_ENUM. The source enum declares finite constants; values/valueOf/$values/constructors/class initialization implement enum data, not field scope or native cleanup.'
  cases=['Exact declaration-order names/ordinals and constant identities.','values and $values return fresh arrays with original constant identities; caller array mutation cannot change later values.','valueOf exact identity for each name; missing name IllegalArgumentException and null name NullPointerException.','Constructor/class initialization are covered by actual enclosing enum constant initialization; no fabricated independent constructor native hook.','No field/candidate/preservation authority and no native target-close obligation belongs to these helpers.']
 elif c['super']=='java/lang/Record' and not calls and len(m['instructions'])==3 and m['instructions'][1]['mnemonic']=='getfield':
  profile='record-field-accessor';reason='Emitted body is aload_0/getfield/typed-return; exact source record component is data access. A diagnostic field named closeFailure does not throw its stored Throwable or perform cleanup.'
  cases=['Return exact stored primitive/reference, including null and Error-as-data identity.','Use distinct instances with different field values to reject constant or neighboring-field substitution.','No state/counter/native-event/target-close effect; no callback-induced first fatal can be inferred from this body.']
 elif c['source_file']=='AppearanceGeometryV2.java' and m['name']=='close':
  profile='geometry-command-factory';reason='Source105 returns new Command(Op.close,List.of()); emitted calls are List.of and Command constructor. This closes a path command, with no resource or lifecycle close.'
  cases=['Actual result is Command with op==Op.close and zero points.','Two calls allocate distinct equal Commands; immutable empty points cannot be mutated.','No native hook, authority, target-close, first-fatal cleanup or busy-count claim.','Allocation failure is not runtime-injected and remains explicitly pending; do not fabricate cleanup behavior.']
 elif c['source_file']=='NativeEditorConnectionV2.java' and m['name']=='getHandler':
  profile='bootstrap-constant-null-any-thread';reason='Source53-54 explicitly permits any-thread bootstrap and forbids state reads. Actual body is aconst_null/areturn; no main-thread guard or native target call exists.'
  cases=['Actual null return on owner thread and a bounded separate JVM thread.','Original field/attempt/target references and all counters remain unchanged; zero native/probe events.','Wrong-thread refusal, dirty/terminal native callbacks and delegated getHandler outcome are inapplicable to this constant body; preserve this subject with exact null oracle.']
 elif c['source_file']=='NativeEditorConnectionV2.java' and m['name']=='<init>':
  profile='adapter-construction-identity';reason='Source constructor stores captured field/attempt/target or delegates through fixed superclass constructor chain; outer private utility constructor only invokes Object.<init>.'
  cases=['Exact captured field/attempt/target references (target==attempt.target at construction), including then-mutated attempt.target without rebinding original target.','Subtype constructor preserves Base references and correct concrete API class.','Private outer constructor has only normal enclosing/class-shape proof; no native callback, dispatch or cleanup authority is manufactured.']
 elif c['source_file']=='NativeEditorConnectionV2.java' and (m['name']=='no' or len(calls)==1 and calls[0].get('target',{}).get('name')=='no' and calls[0]['target']['owner'].startswith('dev/mixer/android/NativeEditorConnectionV2')):
  profile='thread-guarded-explicit-refusal';reason='Source no() requires main then returns false; these exact methods only call no() and never forward target/native input.'
  cases=['Main-thread actual false with no target forwarding or native event.','Wrong-thread requireMain throws before an input effect; retain exact exception type/identity as supported by the enclosing guard test.','Arguments including null/unsupported values cannot create successor authority or native callback credit.']
 elif m['name']=='<init>' and calls and all(i.get('target',{}).get('owner') in ('java/lang/Object','java/lang/Record') and i['target']['name']=='<init>' for i in calls):
  profile='local-constructor-identity';reason='Actual body invokes only Object/Record constructor and field/constant assignments. Captured identity construction is meaningful but has no own native callback.'
  cases=['Exact constructor-owned reference/position identities and default phase/revocation/count state.','No externally borrowed field scope, replacement Mutation or native count is created.','Cover actual enclosing use and immutable membership provenance; no invented beforeReturn native hook.']
 elif not calls:
  profile='local-scalar-reference-or-ledger';reason='Actual method has no invoke instruction. Source/bytecode can read/write fields, branch, return or throw existing identity; seven native callback states cannot be inferred for its own body.'
  cases=['Finite source predicate/field-write/return/throw branches with exact before/after identities and counts.','No native callback/target-close/event may be manufactured; qualify actual enclosing callbacks separately.']
  if m['name'] in ('remember','rememberV2','observe'):
   profile='local-first-failure-ledger';cases=['Null behavior exactly as source; retain any scalar diagnostics flag update.','First ordinary/primary identity is retained; later ordinary does not replace it.','First Error identity is retained independently of primary; later Error does not replace first fatal.','No native cleanup occurs in this body; actual caller cleanup/exception propagation needs its own cases.']
  elif m['name']=='surface':cases=['No stored failure returns void.','Stored ordinary RuntimeException rethrows that same object.','Stored first fatal wins and rethrows that same Error even when primary ordinary exists.','No new event, count release or target close is manufactured.']
  elif m['name']=='onStack':cases=['Exact this found at head/interior/last admitted position returns true; absent/foreign returns false.','Walk is capped at16 actual lease nodes, including cycle/over-depth refusal; no owner/count mutation.']
  elif m['name']=='revoke':cases=['terminal=true sets permanent; terminal=false preserves it.','Own attempt revoked; NOT_REQUESTED becomes DEFERRED, other close state preserved.','CLOSING/QUARANTINED phase retained; other phases become DRAINING.','No native callback, target close or count release is claimed.']
  elif m['name'].startswith('lambda$'):
   if len(m['instructions'])==1 and m['instructions'][0]['opcode']==0xb1:
    profile='empty-lifecycle-lambda';reason='Actual synthetic lambda body consists only of return. Source notification supplies an empty action separately from the real superclass forward.';cases=['Actual enclosing notification preserves empty action with no effect.','Real superclass-forward sibling lambda is separately callback-bearing; no hook credit is borrowed for this empty body.']
   else:
    profile='local-notification-state-action';reason='Actual synthetic lambda contains scalar field/branch operations and no invocation. Source notification uses it to update local lifecycle flags; it is not empty and has no own native callback.';cases=['Verify exact local flag assignments and conditions shown in source witness.','Preserve placement relative to enclosing notification and actual superclass forward; no own callback or target-close is invented.']
  elif c['access']&0x0200:
   profile='interface-default-local-body';cases=['Exact default body scalar/no-op behavior where that body actually executes.','Concrete renderer override/dispatch remains separate; default source cannot authorize current actual renderer outcome.']
 elif c['source_file']=='OwnerLifecycleV2.java':
  profile='lifecycle-decision-model-with-guard';reason='This source is a host decision model. Source returns bounded Decision lists and updates identities, not Android cleanup effects. Public drain/close include the actual ThreadCheck.requireOwner callback; its behavior cannot be erased.'
  cases=['Exact tokens/facts/phase/epoch/primary and bounded action list before/after each actual branch.','Foreign/replayed owner/drain tokens produce source-specified inert output.','Actual ThreadCheck guard succeeds or throws before model effects where invoked; private helper callers establish the guard.','CLOSE/UNREGISTER/CANCEL decisions are commands for another runner; no physical native-close or callback-count credit here.','Use actual closed ArrayList/record input call paths; do not infer purity for arbitrary hostile List implementations.']
 row={k:s[k] for k in ('id','class','method','descriptor','categories','required_semantic_cases','source_sha256','class_sha256')}
 row.update({'proposed_applicability':profile,'reason':reason,'source_file':c['source_file'],'source_witness':excerpt,'actual_invocations':calls,'actual_instructions':m['instructions'],'required_finite_or_enclosing_cases':cases,'selection_status':'pending-independent-root-policy-selection','native_callback_state_deletion_authorized':False,'behavior_accepted':False});rows.append(row)
assert len(rows)==280 and {r['id'] for r in rows}=={s['id'] for s in original['subjects']}
summary=dict(collections.Counter(r['proposed_applicability'] for r in rows))
save(D/'applicability-checklist.json',{'schema':1,'input_roster':identity(P/'active-semantic-obligations.json'),'exact280_ids_retained':True,'root_selected':False,'profiles':summary,'subjects':rows,'scope':'Source-backed per-body applicability/case checklist only. Categories/IDs/cases are retained pending explicit root policy selection; no roster reduction or behavioral matrix credit.'})
print(json.dumps({'subjects':len(rows),'profiles':summary,'root_selected':False}))
