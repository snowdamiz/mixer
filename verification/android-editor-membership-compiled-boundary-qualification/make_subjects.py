#!/usr/bin/env python3
"""Explicit semantic review obligations joined to actual compiled methods, including scalar-only methods."""
from pathlib import Path
import json,hashlib,collections
D=Path(__file__).resolve().parent;inv=json.loads((D/'host-class-inventory.json').read_bytes())
membership={'preservationMembershipV2','fieldPreservationCapturedV2','preservationProvenanceV2','fieldPreservationIdentityV2','preservationCohortV2','preservationFailureFundedV2','beginFieldPreservationsV2','finishV2','failedV2','validateAttachedV2'}
subjects=[]
for c in inv['classes']:
 for m in c['methods']:
  name=c['class']+'#'+m['name']+m['descriptor'];cats=set()
  if 'NativeEditorConnectionV2' in c['class']:cats.add('direct-editor-and-overload')
  if any(t in c['class'] for t in ('NativeField','FieldPreservation','Replacement','EditorLease','PreservationMembership','AttachmentJournal','NativeState')):cats.add('field-authority-or-reservation')
  if c['source_file']=='NativeRenderer.java' and (m['name'] in membership or 'PreservationMembership' in c['class']):cats.add('exact-membership-and-completion')
  if any(t in m['name'] for t in ('Focus','Visibility','Detached','Attached','editorLoss','onPause','onResume')):cats.add('loss-and-lifecycle')
  if any(t in m['name'] for t in ('scrub','drain','close','failed','uncertain','finish','remember','observe')):cats.add('cleanup-and-first-fatal')
  if c['class']=='dev/mixer/android/NativeRenderer$2' and m['name'] in ('editorLossObservation','editorLossObserved','fieldPreservationBegin','fieldPreservationEnd','replacementEvent','editorEnter','editorLeave','editorDrainBegin','editorDrainEnd','editorReport','editorOperationEnd','editorFinish','editorCloseAllowed','editorDispatchAvailable'):cats.add('actual-renderer-input-authority-endpoint')
  if not cats:continue
  subjects.append({'subject':name,'categories':sorted(cats),'source':c['source'],'source_identity':c['source_identity'],'class_file':c['file'],'class_identity':c['file_identity'],'method_descriptor':m['descriptor'],'method_access':m['access'],'instruction_count':len(m['instructions']),'field_access_instructions':[i for i in m['instructions'] if i['opcode'] in (0xb2,0xb3,0xb4,0xb5)],'invocation_instructions':[i for i in m['instructions'] if 0xb6<=i['opcode']<=0xba],'return_or_throw_instructions':[i for i in m['instructions'] if i['opcode'] in (*range(0xac,0xb2),0xbf)],'exception_table':m['exceptions'],'compiled_identity':'closed parsed classfile; javap independently cross-checks invocation descriptor/BCI/opcode','state_qualification':'pending individual semantic case binding; passing original command coverage is separate'})
assert any('preservationMembershipV2(' in s['subject'] for s in subjects)
result={'schema':1,'scope':'Fresh explicit semantic subject review roster, including scalar-only membership and failure endpoints; not a runtime coverage pass','subjects':subjects,'counts':dict(collections.Counter(cat for s in subjects for cat in s['categories'])),'required_state_obligations':{'callback-boundary':['clean','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback'],'direct-editor':['exact descriptor and overload','natural versus injected compatible successor','changing invalid entry','terminal/dirty/stale pre-entry refusal','wrong thread','unsupported argument/refusal','getter/snapshot identity','no new work after scalar return'],'reservation':['original TRANSACTION token','exact record/view/Editable/Binding','own and foreign loss at each phase','counted busy custody','precommit and held failure','ordered constructor-bound membership','same first fatal','restoration/event reentry','allocation failure source-only pending']},'executable_per_subject_cases_qualified':False}
(D/'subject-obligations.json').write_text(json.dumps(result,indent=2)+'\n');print('semantic subjects',len(subjects),result['counts'])
