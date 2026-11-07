from pathlib import Path
import json,hashlib,shutil,datetime,collections
D=Path(__file__).resolve().parent;Q=D.parent;E=Q/'semantic-review-candidate-v1'
if E.exists():raise SystemExit('refuse replacing frozen review packet')
E.mkdir()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
inv=json.loads((D/'context17-1/product-class-inventory.json').read_bytes())
old=json.loads((Q/'subject-obligations.json').read_bytes())
membership={'preservationMembershipV2','fieldPreservationCapturedV2','preservationProvenanceV2','fieldPreservationIdentityV2','preservationCohortV2','preservationFailureFundedV2','beginFieldPreservationsV2','finishV2','failedV2','validateAttachedV2'}
profiles={
 'direct-editor-and-overload':['current-exact-original-result','compatible-successor-same-original-scope','terminal-before-entry-refuses','dirty-before-entry-refuses','stale-before-entry-refuses','changing-before-entry-refuses','wrong-thread-refuses','unsupported-argument-refuses','ordinary-after-callback-exact-identity','fatal-after-callback-first-fatal','cleanup-once-balanced'],
 'field-authority-or-reservation':['original-transaction-or-presentation-identities','own-loss-entry-and-return','foreign-loss-entry-and-return','counted-busy-custody','precommit-cohort-order-and-constructor-membership','held-failure-retains-funded-custody','restoration-and-event-reentry','first-fatal-and-balanced-release'],
 'exact-membership-and-completion':['ordered-constructor-bound-membership','duplicate-or-foreign-state-refuses','no-tail-callback-before-complete-roster','held-failure-funded-membership','same-first-fatal','allocation-failure-source-proof-only-pending-runtime'],
 'loss-and-lifecycle':['current-gates-and-original-identities','own-loss-closes-authority','foreign-loss-cannot-authorize-successor','entry-and-return-reentry','terminal-and-dirty-gates','balanced-cleanup-first-fatal'],
 'cleanup-and-first-fatal':['original-obligation-retained','ordinary-primary-preserved','first-fatal-exact-identity','reentrant-cleanup-refuses-new-work','counted-busy-balanced','target-close-once-or-explicit-held-pending'],
 'actual-renderer-input-authority-endpoint':['actual-callback-subject-identities','original-scope-not-successor-authority','own-and-foreign-loss','reservation-count-exact','exception-and-first-fatal-disposition','finite-busy-release']}
subjects=[]
for c in inv['classes']:
 for m in c['methods']:
  cats=set()
  if 'NativeEditorConnectionV2' in c['class']:cats.add('direct-editor-and-overload')
  if any(t in c['class'] for t in ('NativeField','FieldPreservation','Replacement','EditorLease','PreservationMembership','AttachmentJournal','NativeState')):cats.add('field-authority-or-reservation')
  if c['source_file']=='NativeRenderer.java' and (m['name'] in membership or 'PreservationMembership' in c['class']):cats.add('exact-membership-and-completion')
  if any(t in m['name'] for t in ('Focus','Visibility','Detached','Attached','editorLoss','onPause','onResume')):cats.add('loss-and-lifecycle')
  if any(t in m['name'] for t in ('scrub','drain','close','failed','uncertain','finish','remember','observe')):cats.add('cleanup-and-first-fatal')
  if c['class']=='dev/mixer/android/NativeRenderer$2' and m['name'] in ('editorLossObservation','editorLossObserved','fieldPreservationBegin','fieldPreservationEnd','replacementEvent','editorEnter','editorLeave','editorDrainBegin','editorDrainEnd','editorReport','editorOperationEnd','editorFinish','editorCloseAllowed','editorDispatchAvailable'):cats.add('actual-renderer-input-authority-endpoint')
  if not cats:continue
  subjects.append({'id':c['class']+'#'+m['name']+m['descriptor'],'class':c['class'],'method':m['name'],'descriptor':m['descriptor'],'categories':sorted(cats),'source_sha256':c['source_identity']['sha256'],'class_sha256':c['file_identity']['sha256'],'required_semantic_cases':sorted({s for cat in cats for s in profiles[cat]}),'callback_state_rule':'Every actual callback-bearing invocation requires clean, terminal-at-entry, terminal-before-return, dirty-at-entry, dirty-before-return, ordinary-throw-after-callback, fatal-throw-after-callback. Scalar-only subjects require actual enclosing typed outcome or separately reviewed scalar controls; no fabricated native callback.','state_qualification':'pending per-subject exact executable case binding','invocations':[i for i in m['instructions'] if 0xb6<=i['opcode']<=0xba],'returns_and_throws':[i for i in m['instructions'] if i['opcode'] in (*range(0xac,0xb2),0xbf)]})
assert len(subjects)==280,(len(subjects),'full immutable semantic roster changed')
save(E/'active-semantic-obligations.json',{'schema':'mixer.android.semantic-review-candidate.v1','context_id':'1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd','root_selected':False,'qualification_status':'draft-full-roster-pending-state-qualification','subjects':subjects,'category_counts':dict(collections.Counter(cat for s in subjects for cat in s['categories'])),'scope':'All 280 semantic subjects retained. Category profiles are review obligations, not self-authorizing behavior claims. Native/OTA/GA pending.'})
for src,dest in [(D/'context17-1/legacy189-bindings.json','historical189-current-bindings.json'),(D/'context17-1/product-context.json','product-context.json'),(Q/'interface-v3/reference-obligations.json','reference-obligations.json'),(Q/'root-count-amendment.md','count-amendment.md')]:
 if src.exists():shutil.copy2(src,E/dest)
shutil.copytree(Q/'inputs/accepted/source',E/'accepted-source')
shutil.copy2(__file__,E/'release_semantic_roster.py')
(E/'README.md').write_text('This read-only proposed review packet preserves all 189 historical V2 dispositions, all 280 semantic subjects, exact descriptor set 38 and separately required five V1 positives. It does not qualify behavior. The actual JDK17 no-g context is separate from historical JDK25 -g receipts. Historical mappings have one exact current compiled candidate each; nine replaced wrapper sites and the eligible focus-restoration branch need distinct executable witnesses. The category profiles state required semantic cases; only actual callback-bearing sites receive seven callback-state obligations. Scalar-only subjects cannot gain callback or return credit from adjacent hooks. Exact per-subject state-case joins remain pending and cannot be deleted to achieve a pass. Accepted product bodies remain unchanged.\n')
members=[{'path':str(p.relative_to(E)),**ident(p)} for p in sorted(E.rglob('*')) if p.is_file()]
save(E/'manifest.json',{'members':members,'member_count':len(members),'member_bytes':sum(x['bytes'] for x in members)})
members.append({'path':'manifest.json',**ident(E/'manifest.json')});members.sort(key=lambda x:x['path'])
save(E/'seal.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'frozen-review-candidate; no behavioral acceptance','members':members,'member_count':len(members),'member_bytes':sum(x['bytes'] for x in members)})
print(json.dumps({'path':str(E),'seal':ident(E/'seal.json'),'members':len(members)}))
