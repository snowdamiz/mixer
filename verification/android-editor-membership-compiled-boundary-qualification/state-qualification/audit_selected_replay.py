"""Read-only, bounded replay reconciliation. A ledger is not admission or full qualification."""
from pathlib import Path
import argparse, collections, gzip, hashlib, itertools, json, signal, sys

S=Path(__file__).resolve().parent;Q=S.parent;R=Q.parents[1]
sys.path.insert(0,str(Q))
from classfile import parse

STATES=('clean','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback')
CONTEXT='1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd'
def ident(path):
 data=path.read_bytes();return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def need(condition,message):
 if not condition:raise ValueError(message)
def same(left,right):
 if type(left)is not type(right):return False
 if type(left)is dict:return left.keys()==right.keys()and all(same(left[key],right[key])for key in left)
 if type(left)is list:return len(left)==len(right)and all(same(a,b)for a,b in zip(left,right))
 return left==right
def pairs(items):
 out={}
 for key,value in items:
  need(key not in out,'duplicate JSON object key '+key);out[key]=value
 return out
def loads(value):return json.loads(value,object_pairs_hook=pairs)
def integer(value,message):
 need(type(value)is int and value>=0,message);return value
def canonical(value):return json.dumps(value,separators=(',',':'),ensure_ascii=False).encode()
def frame_key(frame):return (frame['class'].replace('.','/'),frame['method'],frame['descriptor'],integer(frame['bci'],'exact BCI integer'))
from delegated_association import validate_row as validate_delegated_row
def delegated_region(row):
 if row.get("family")=="setComposingRegionWithAttributes":validate_delegated_row(row)

class Audit:
 def __init__(self,run):
  self.run=run;self.receipt=loads((run/'receipt.json').read_bytes());need(self.receipt['all_commands_passed'] is True,'retained failing producer cannot be claimed passing');need(self.receipt['cleanup']['all_children_reaped'] is True and self.receipt['cleanup']['scratch_removed'] is True,'producer cleanup incomplete')
  self.classmap=loads((run/'class-map.json').read_bytes());need(set(self.classmap)=={str(p.relative_to(run/'classes'))for p in (run/'classes').rglob('*.class')},'complete emitted class set')
  reference=Q/'semantic-review-candidate-v1';need(ident(reference/'seal.json')['sha256']=='361412b6ee2124ace685a2242390ece375d0327b119876b13db27dc95ea3f5e6','immutable reference packet identity');seal=loads((reference/'seal.json').read_bytes());members=seal['members'];members={item['path']:{key:item[key]for key in('bytes','sha256')}for item in members}if type(members)is list else members
  for name in('active-semantic-obligations.json','historical189-current-bindings.json'):need(ident(reference/name)==members[name],'immutable reference member identity '+name)
  self.classes={};self.methods={};self.instructions={};self.subjects={x['id']:x for x in loads((reference/'active-semantic-obligations.json').read_bytes())['subjects']};need(len(self.subjects)==280,'immutable full280 inventory')
  context=loads((S/'context17-1/product-context.json').read_bytes());self.productmap=context['class_map'];self.source_hashes={}
  freeze=loads((run/'source-freeze.json').read_bytes());need(freeze['product_context_id']==CONTEXT,'actual product context');need(freeze['passive_derivative_seal']['sha256']=='8501bfa60dbae4c3d90be181e8d4fe1e858d1f59908328c4c9855fe7bc99eff8','selected v4 source derivative')
  for item in freeze['sources']:
   original=R/item['path'];owned=run/original.name;path=owned if original.parent.name=='full-candidate-v1' else original
   need(same(ident(path),{k:item[k]for k in ('bytes','sha256')}),'actual compiled source changed: '+item['path']);self.source_hashes[path.name]=item['sha256']
  for rel,item in self.classmap.items():
   path=run/'classes'/rel;need(same(ident(path),item),'actual class hash mismatch '+rel)
   if rel not in self.productmap:continue
   need(same(item,self.productmap[rel]),'unreviewed product compiler output '+rel);value=parse(path.read_bytes());self.classes[value['class']]=value
   for method in value['methods']:
    key=(value['class'],method['name'],method['descriptor']);self.methods[key]=method
    for instruction in method['instructions']:self.instructions[key+(instruction['bci'],)]=instruction
  need(len(self.classes)==209 and set(self.productmap)<=set(self.classmap),'all exact209 product classes')
  self.historical={x['historical_id']:x for x in loads((reference/'historical189-current-bindings.json').read_bytes())['records']};need(len(self.historical)==189,'immutable full189 history')
  self.editor_replacements={};
  for historical,item in self.historical.items():
   candidates=item['fresh_compiled_candidates']
   if item['disposition']=='replaced-direct-adapter'and len(candidates)==1 and candidates[0]['class'].startswith('dev/mixer/android/NativeEditorConnectionV2$'):
    value=candidates[0];self.editor_replacements[(value['class'],value['method'],value['descriptor'],value['bci'])]=(historical,value)
  need(len(self.editor_replacements)==9,'exact nine editor replacements; tenth drain/close stays in full history')
  self.presence=collections.defaultdict(list);self.native=collections.defaultdict(list);self.finite=collections.defaultdict(list);self.history=collections.defaultdict(list);self.files=[]
 def finite_row(self,row,locator,kind):
  need(type(row)is dict and row.get('subject_id')in self.subjects,'exact finite subject in immutable280 inventory');subject=self.subjects[row['subject_id']];classhash=self.classmap[subject['class']+'.class']['sha256'];need(classhash==subject['class_sha256'],'finite exact class binding')
  if 'class_sha256'in row:need(row['class_sha256']==classhash,'finite claimed class binding')
  if 'source_context'in row:need(row['source_context']==CONTEXT,'finite context binding')
  need((subject['class'],subject['method'],subject['descriptor'])in self.methods,'finite exact method/descriptor')
  if 'actual_method'in row:
   method=row['actual_method'];need(method=={'class':subject['class'].replace('/','.'),'method':subject['method'],'descriptor':subject['descriptor']},'finite actual method tuple')
  if kind in('field','lambda','scalar'):
   need(row['attempt_clean_latched']is True and type(row['native_events'])is int and row['native_events']==0 and type(row['native_outcomes'])is int and row['native_outcomes']==0,'finite capture or zero-native contract');need(type(row['actual_outcome'])is dict and type(row['actual_outcome'].get('kind'))is str,'structured actual typed finite outcome')
   if kind in('lambda','scalar')or subject['method']!='<init>':need(type(row.get('expected_outcome'))is dict,'required independently expected finite outcome')
   if 'expected_outcome'in row:need(same(row['actual_outcome'],row['expected_outcome']),'finite actual typed outcome differs')
   if 'expected_fields'in row:need(same(row['actual_fields'],row['expected_fields']),'finite ordered field/type/value contract')
   if kind=='lambda':need(not subject['invocations'],'no-invoke lambda gained a callable instruction')
  elif kind=='ledger':
   need(row['typed_result']=='void-normal-return'and type(row['leaf_events'])is int and row['leaf_events']==0 and type(row['bridge_effects'])is int and row['bridge_effects']==0 and type(row['checks'])is int and row['checks']>0,'finite ledger normal void/zero-effects contract')
  elif kind=='renderer-predicates':
   need(same(row['actual'],row['expected']),'renderer finite literal outcome');need(row['typed_outcome']in('java.lang.Boolean','throw'),'renderer actual typed completion');need(row['all_snapshots_unchanged']is True and row['snapshot_before_sha256']==row['snapshot_after_sha256'],'renderer immutable snapshot equality');need(same(row['counts_before'],row['counts_after']) and row['native_effects']==0 and row['native_events_before']==row['native_events_after'],'renderer finite counts/no native effects')
  elif kind=='renderer-ledger-constructor':
   need(same(row['actual_after'],row['literal_expected_after']),'renderer ledger/constructor independent literal values');need(row['actual_typed_outcome']['kind']in('void','constructed-reference')and row['actual_typed_outcome']['exception']is None,'renderer finite typed normal completion');need(row['unchanged_non_target_fields_and_containers']is True and same(row['counts_before'],row['counts_after'])and row['native_effects']==0 and row['native_events_before']==row['native_events_after'],'renderer finite unchanged non-target fields/counts/native prefix')
  elif kind=='renderer-state-journal-constructors':
   need(row['native_outcome_capture_clean']is True and row['mutations_restored']is True and row['original_authority_references_preserved']is True and row['no_membership_or_release_authority']is True,'constructor bounded facet contract');need(row['counts_before']==row['counts_after'],'constructor counts unchanged');need(row['enclosing_completion']in('normal-object','exact-exception'),'actual constructor outcome kind')
   if row['native_site_id']is not None:
    need(row['callback_state']in STATES,'constructor canonical state');need(type(row['exact_tuple_hooks'])is list and len(row['exact_tuple_hooks'])==2,'constructor entry/return pair')
    bci=integer(int(row['native_site_id'].split('@')[-1].split(':')[0]),'constructor immutable BCI');allowed=(67,145,222)if subject['class'].endswith('$NativeState')else(184,192);need(bci in allowed,'independent selected constructor tuple');key=(subject['class'],subject['method'],subject['descriptor'],bci);instruction=self.instructions[key];target=instruction['target'];need(row['native_site_id']==row['subject_id']+'@'+str(bci)+':'+instruction['mnemonic']+':'+target['owner']+'#'+target['name']+target['descriptor'],'constructor native-site exact opcode/callee identity')
    for hook in row['exact_tuple_hooks']:
     need(hook['receiver']==hook['original_own_receiver']and hook['phase']in('entry','beforeReturn'),'constructor own receiver/phase');integer(hook['event_index'],'constructor event identity index');need(type(hook['event_reference'])is str and bool(hook['event_reference']),'constructor immutable event reference');need(len(hook['frames'])<24,'constructor selected full filtered stack not capped');actual=self.frames(hook['frames']);need(key in[value[0]for value in actual],'constructor selected frame exact reviewed tuple')
   else:need(row['callback_state']=='finite-no-fabricated-callback','constructor finite no artificial callback')
  elif kind=='field-preservation-replacement':
   need(row['original_required_cases_retained']is True and row['shared_mutations_restored']is True and row['no_native_events']is True and row['no_membership_release_authority']is True and row['counts_before']==row['counts_after'],'four-body selected finite scope')
   need(row['native_callback_state']=='not-applicable-no-fabricated-native-callback','interface observation cannot become native callback credit');oracle=row['independent_expected_before_invocation'];observation=row['input_observation']
   if observation is not None:
    need(observation['method']=='editorLossObservation'and observation['descriptor']=='()J'and type(observation['calls'])is int and observation['calls']in(0,1)and observation['instrumentation_only_no_native_callback']is True,'exact original Input observation')
    if observation['calls']:
     need(type(observation['production_call_frames'])is list and len(observation['production_call_frames'])<24,'complete bounded original Input caller frames');self.frames(observation['production_call_frames'])
   if row['completion']=='exact-actual-input-exception':need(observation is not None and row['exact_exception_reference']==observation['actual_exception_reference']and row['actual_result']is None and observation['actual_return_long']is None,'exact original Input exception propagation; no constructor receiver inferred')
   else:
    need(row['completion']=='normal','actual four-body finite completion')
    if subject['method']=='endReady':need(type(row['actual_result'])is bool and row['actual_result']==oracle['expected']and row['actual_before']==row['actual_after'],'literal endReady truth table and unchanged receiver')
    elif subject['method']=='unchangedLoss':need(type(row['actual_result'])is bool and row['actual_result']==oracle['expected_boolean']and row['actual_before']==row['actual_after']and observation['calls']==oracle['expected_Input_calls'],'literal exact-long/lost short-circuit and unchanged receiver')
    else:
     after=row['actual_after'];need(type(after)is dict and type(row['actual_result'])is str and row['actual_result']==after['reference'],'actual constructed finite reference')
     for key,wanted in oracle.items():
      if key in('all_flags_false','hooks','Input_calls'):continue
      actual=after[key];need(actual==wanted or(wanted is None and actual=='null'),'literal captured constructor field '+key)
     need(after['hooks_values']==[]and type(after['hooks_reference'])is str,'fresh empty constructor hook container')
  self.finite[row['subject_id']].append({**locator,'facet':kind,'case_id':row.get('control_case',row.get('case_id',row.get('sequence'))),'step':row.get('step'),'callback_state':row.get('callback_state'),'class_sha256':classhash,'source_sha256':subject['source_sha256'],'actual_typed_outcome':row.get('actual_outcome',row.get('actual_typed_outcome',row.get('typed_outcome',row.get('typed_result',row.get('enclosing_completion'))))),'scope':'Only the exact executed finite/object/result/callback facet. Original enclosing obligations are retained pending independent disposition.'})
 def finite_files(self):
  specs=[('field-finite.rows.jsonl.gz','field'),('actual-lifecycle-lambdas.json','lambda'),('actual-typed-scalars.json','scalar'),('actual-ledger-results.json','ledger'),('actual-renderer-membership.json','renderer-predicates'),('actual-renderer-ledger-constructor.json','renderer-ledger-constructor'),('actual-renderer-state-journal-constructors.json','renderer-state-journal-constructors'),('actual-field-preservation-replacement.json','field-preservation-replacement')]
  for name,kind in specs:
   path=self.run/name
   if not path.is_file():continue
   signal.alarm(60)
   if name.endswith('.gz'):
    with gzip.open(path,'rt',encoding='utf-8')as source:rows=[loads(line)for line in source]
   else:rows=loads(path.read_bytes())['rows']
   for number,row in enumerate(rows,1):self.finite_row(row,{'file':name,'row':number},kind)
   self.files.append({'file':name,**ident(path),'facet':kind,'finite_invocations':len(rows)});signal.alarm(0)
 def frame(self,frame):
  need(type(frame)is dict,'structured frame');key=frame_key(frame);need(key in self.instructions,'actual frame is absent from exact emitted class: '+str(key));ins=self.instructions[key];need(ins['opcode']in(182,183,184,185,186),'actual frame BCI is not invocation '+str(key));need(type(frame['line'])is int and frame['line']==ins['line'],'actual source line differs from class line table');return key,ins
 def frames(self,frames):
  need(type(frames)is list and 0<len(frames)<=128,'complete nonempty bounded production frames');return [self.frame(frame)for frame in frames]
 def row(self,row,small,locator):
  need(type(row)is dict and type(small)is dict,'structured raw and compact rows');need(row.get('validation_failure')is None,'retained behavior validation failure');need(row.get('outcome_probe_clean',row.get('attempt_clean_latched'))is True,'latched capture failure or hook lifetime');need(row.get('status')!='failed','failed state')
  delegated_region(row)
  sequence=row['native_sequence'];sets=row['frame_sets'];need(type(sequence)is list and type(sets)is list,'structured trace');need(integer(small['native_event_count'],'exact native event count')==len(sequence),'event count changed');digest=hashlib.sha256();counts=collections.Counter()
  for event in sequence:
   need(type(event)is dict and event['phase']in('entry','beforeReturn')and type(event['method'])is str,'structured native event');index=integer(event['frame_set'],'integer frame-set index');need(index<len(sets),'event frame-set bounds');encoded=canonical(event);digest.update(len(encoded).to_bytes(4,'big'));digest.update(encoded);counts[event['method']+'/'+event['phase']]+=1
  need(digest.hexdigest()==small['ordered_native_event_digest'] and same(dict(counts),small['native_event_counts']),'ordered raw event reconciliation')
  points=small['selected_immutable_event_points'];need(type(points)is list,'selected structured event points');selected=set();pairs={}
  if row.get('historical_id'):need(row['selected_hook_fired']is True and len(points)==1 and type(row['selected'])is dict and bool(row['selected']),'historical mandatory actual selected hook')
  elif 'selected_hook_fired'in row:need(type(row['selected_hook_fired'])is bool and len(points)==(1 if row['selected_hook_fired']else 0),'exact public operation selected point/refusal')
  elif 'original_attempt_close'in row:need(len(points)==1,'mandatory actual close selected event')
  for point in points:
   index=integer(point['sequence_index'],'selected exact event index');need(index<len(sequence),'selected event bounds');event=sequence[index];need(point['native_event']==event and point['production_frames']==sets[event['frame_set']],'selected immutable raw event/frame equality');actual_frames=self.frames(point['production_frames']);selected.add(index)
   if row.get('historical_id'):
    historical=row['historical_id'];need(historical in self.historical,'foreign historical id');wanted=self.historical[historical]['fresh_compiled_candidates'];need(len(wanted)==1,'reviewed exact current binding');want=wanted[0];key=(want['class'],want['method'],want['descriptor'],want['bci']);need(key in [value[0]for value in actual_frames],'selected historical caller tuple changed');need(same(row['selected']['caller'],want),'selected historical caller metadata changed');need(self.classmap[want['class']+'.class']['sha256']==want['class_sha256'],'historical class binding changed');need(self.source_hashes[self.classes[want['class']]['source_file']]==want['source_sha256'],'historical source binding changed');ins=self.instructions[key];need(ins['mnemonic']==want['opcode']and same(ins['target'],want['target']),'historical BCI/opcode/callee changed');self.history[historical].append({'state':row['state'],**locator,'event_index':index,'exact_caller':want['id'],'native_completion_scope':'separate actual completion below; no helper return inferred'})
   same_return=index if event['phase']=='beforeReturn' else None
   if event['phase']=='entry':
    for next_index in range(index+1,len(sequence)):
     other=sequence[next_index]
     if all(other[key]==event[key]for key in ('method','receiver_identity','frame_set')):
      if other['phase']=='beforeReturn':same_return=next_index
      break
   pairs[index]=same_return
   for number,(key,ins)in enumerate(actual_frames):
    subject=key[0]+'#'+key[1]+key[2]
    if subject not in self.subjects:continue
    reference={**locator,'state':row['state'],'event_index':index,'native_method':event['method'],'phase':event['phase'],'frame_depth':number,'bci':key[3],'opcode':ins['mnemonic'],'callee':ins['target'],'class_sha256':self.classmap[key[0]+'.class']['sha256'],'source_sha256':self.source_hashes[self.classes[key[0]]['source_file']],'observation_scope':'exact native invocation caller' if number==0 else 'actual enclosing invocation frame only; no method-result or independent callback credit'}
    self.presence[subject].append(reference)
    if number==0:self.native[subject].append(reference)
   first_key=actual_frames[0][0]
   if not row.get('historical_id')and first_key in self.editor_replacements:
    state='clean'if row['state']=='current'else row['state']
    if state in STATES:
     historical,want=self.editor_replacements[first_key];instruction=self.instructions[first_key];need(instruction['mnemonic']==want['opcode']and same(instruction['target'],want['target']),'exact replacement overload target');self.history[historical].append({'state':state,'original_raw_state':row['state'],**locator,'event_index':index,'exact_caller':want['id'],'disposition':'actual per-overload direct adapter lambda; no historical wrapper credit transferred','native_completion_scope':'Actual native/public observations remain separately typed; missing helper results stay pending'})
  need({integer(pair['selected_event_sequence_index'],'pair selected index'):pair['same_invocation_before_return_sequence_index']for pair in small['selected_actual_call_pairs']}==pairs,'exact selected call-pair reconciliation')
  completion_events=selected|{value for value in pairs.values()if value is not None};expected=[]
  method=row.get('selected_leaf')or(row['selected']['native_method']if row.get('historical_id')else 'BaseInputConnection.closeConnection'if 'original_attempt_close'in row else 'BaseInputConnection.'+row['family'])
  receiver=row.get('original_target')or row.get('original_authority',{}).get('receiver')or row.get('selected',{}).get('receiver_authority',{}).get('receiver')
  for completion in row['actual_native_outcomes']:
   index=integer(completion['native_event_sequence_index'],'actual completion integer event index');need(index<len(sequence),'completion event bounds');event=sequence[index];need(completion['method']==event['method']and completion['native_event_phase']==event['phase']and completion['production_frames']==sets[event['frame_set']],'actual completion event/frame join');need(completion['completion']in('return','exception'),'actual completion kind')
   if completion['method']==method and completion['receiver_identity']==receiver and index in completion_events:expected.append(completion)
  need(small['selected_actual_native_completions']==expected,'foreign or neighboring completion borrowed')
  return {'state':row['state'],'historical_id':row.get('historical_id'),'family':row.get('family'),'selected_events':len(points),'selected_native_completions':len(expected),'missing_selected_native_completion':bool(points)and not expected,'native_completion_credit':'actual recorded leaf completion only; enclosing helper and missing body exceptions remain pending'}
 def pairfile(self,path):
  signal.alarm(60);compact=Path(str(path)+'.compact.jsonl');need(compact.is_file(),'complete raw/compact pair');rows=[]
  with gzip.open(path,'rt',encoding='utf-8')as raw,compact.open()as small:
   for number,pair in enumerate(itertools.zip_longest(raw,small),1):
    need(all(value is not None for value in pair),'raw/compact row count differs');need(all(len(value)<=128*1024*1024 for value in pair),'bounded raw row');rows.append(self.row(loads(pair[0]),loads(pair[1]),{'file':path.name,'row':number}))
  self.files.append({'file':path.name,**ident(path),'compact':ident(compact),'rows':rows});signal.alarm(0)
 def require_historical_states(self):
  missing=[];duplicates=[]
  for historical in self.historical:
   counts=collections.Counter(item['state']for item in self.history[historical])
   for state in STATES:
    if counts[state]==0:missing.append([historical,state])
    elif counts[state]!=1:duplicates.append([historical,state,counts[state]])
   need(set(counts)<=set(STATES),'unknown canonical historical state')
  need(not missing and not duplicates,'immutable full189 x exactseven states missing/duplicate: '+str({'missing':missing[:12],'duplicates':duplicates[:12]}))
 def ledger(self):
  output=[]
  for subject,original in self.subjects.items():
   output.append({'original_subject':original,'finite_facets':self.finite[subject],'actual_frame_observations':self.presence[subject],'actual_native_caller_observations':self.native[subject],'original_required_cases_retained':original['required_semantic_cases'],'qualification_status':'pending-source-specific-required-case-and-outcome-review','scope':'Runtime presence does not discharge original obligations. Finite facets and native leaf completions remain separately scoped.'})
  return {'schema':1,'status':'reconciled-read-only-candidate-observations; not-qualified','context_id':CONTEXT,'source_freeze':ident(self.run/'source-freeze.json'),'class_map':ident(self.run/'class-map.json'),'subjects':output,'exact280_ids_retained':True,'historical189':[{'historical_id':key,'original_binding':value,'actual_state_observations':self.history[key],'status':'pending-disposition-and-outcome-review'}for key,value in self.historical.items()],'files':self.files,'execution_closure_and_native_OTA_GA_accepted':False}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--require-historical-states',action='store_true');args=parser.parse_args();run=args.run.resolve();out=args.output.resolve();need(run.is_relative_to(S/'full-candidate-v1'),'owned actual replay input');need(out.is_relative_to(S)and not out.exists(),'new owned output');signal.alarm(60);audit=Audit(run);signal.alarm(0)
 for path in sorted(run.glob('*.rows.jsonl.gz')):
  if Path(str(path)+'.compact.jsonl').is_file():audit.pairfile(path)
 audit.finite_files()
 if args.require_historical_states:audit.require_historical_states()
 value=audit.ledger();value['require_full189_callback_state_roster']=args.require_historical_states;out.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({'files':len(audit.files),'callback_trace_rows':sum(len(x.get('rows',[]))for x in audit.files),'finite_invocations':sum(x.get('finite_invocations',0)for x in audit.files),'subjects_with_finite_facets':sum(bool(x['finite_facets'])for x in value['subjects']),'subjects_with_actual_frames':sum(bool(x['actual_frame_observations'])for x in value['subjects']),'historical_with_actual_states':sum(bool(x['actual_state_observations'])for x in value['historical189']),'status':value['status']}))
if __name__=='__main__':main()
