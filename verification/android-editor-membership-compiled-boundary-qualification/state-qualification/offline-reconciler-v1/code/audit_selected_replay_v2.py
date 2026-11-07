"""Read-only, bounded replay reconciliation. A ledger is not admission or full qualification."""
from pathlib import Path
import argparse, collections, gzip, hashlib, importlib.util, itertools, json, signal, sys

S=Path(__file__).resolve().parents[2];Q=S.parent;R=Q.parents[1]
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
def reject_constant(value):raise ValueError('nonstandard JSON numeric constant '+value)
def loads(value):return json.loads(value,object_pairs_hook=pairs,parse_constant=reject_constant)
def integer(value,message):
 need(type(value)is int and value>=0,message);return value
def canonical(value):return json.dumps(value,separators=(',',':'),ensure_ascii=False).encode()
def frame_key(frame):return (frame['class'].replace('.','/'),frame['method'],frame['descriptor'],integer(frame['bci'],'exact BCI integer'))
RECEIVER_PACKET_SHA256='4fec770228b4420a56bd1ab0c48446a09bfac8037b80c498c412f627abfb81cf'
RECEIVER_SELECTION_SHA256='48c4c286b048934092baf4defeeaa787a6ba6273aed1999bc6221a67dfbcc7a4'
_receiver_api=None
_receiver_policy=None
def receiver_api():
 global _receiver_api,_receiver_policy
 if _receiver_api is None:
  packet=Q/'delegated-overload-association-v2';need(ident(packet/'seal.json')['sha256']==RECEIVER_PACKET_SHA256,'root-selected exact receiver/raw packet');selection=R/'verification/android-editor-boundary-root-review/delegated-receiver-v2-selection.json';need(ident(selection)['sha256']==RECEIVER_SELECTION_SHA256,'root-selected receiver consistency scope')
  seal=loads((packet/'seal.json').read_bytes());members=seal['members'];need({str(path.relative_to(packet))for path in packet.rglob('*')if path.is_file()}=={'seal.json'}|{item['path']for item in members},'closed receiver dependency packet')
  for item in members:need(same(ident(packet/item['path']),{key:item[key]for key in ('bytes','sha256')}),'receiver dependency exact member '+item['path'])
  spec=importlib.util.spec_from_file_location('_selected_receiver_join',packet/'delegated_raw_v2.py');_receiver_api=importlib.util.module_from_spec(spec);spec.loader.exec_module(_receiver_api);_receiver_policy,_=_receiver_api.load_policy()
 return _receiver_api,_receiver_policy

def receiver_row(row):
 api,policy=receiver_api();view=dict(row);view['selected_event']=[]
 try:result=api.validate_receiver_bindings(view,policy)
 except api.DelegatedReceiverRefusal as failure:raise ValueError('actual receiver bridge: '+str(failure))from failure
 if row.get('family')=='setComposingRegionWithAttributes':
  try:api.validate_delegated_raw(row)
  except api.DelegatedReceiverRefusal as failure:raise ValueError('mandatory delegated raw join: '+str(failure))from failure
 return {item['row_identity']:item['global_identity']for item in row['native_receiver_bindings']},result

def native_value(value):
 need(type(value)is dict and type(value.get('kind'))is str,'tagged actual native/public value')
 kind=value['kind']
 if kind in('null','void'):need(set(value)=={'kind'},'empty native value fields')
 elif kind=='boolean':need(set(value)=={'kind','value'}and type(value['value'])is bool,'actual Boolean native value')
 elif kind=='integer':need(set(value)=={'kind','value'}and type(value['value'])is int,'actual integer native value')
 elif kind=='floating':
  import math
  need(set(value)=={'kind','value'}and type(value['value'])is float and math.isfinite(value['value']),'actual finite floating native value')
 elif kind=='character':need(set(value)=={'kind','value'}and type(value['value'])is str and len(value['value'])==1,'actual character native value')
 elif kind=='string':need(set(value)=={'kind','value','identity'}and type(value['value'])is str and type(value['identity'])is str and value['identity'].startswith('java.lang.String@'),'actual immutable String value/identity')
 elif kind=='exception':need(set(value)=={'kind','class','identity'}and all(type(value[key])is str and bool(value[key])for key in('class','identity')),'actual exception class/identity')
 elif kind in('reference','typed-snapshot'):
  need(set(value)==({'kind','class','identity'}if kind=='reference'else{'kind','class','identity','fields'})and type(value['class'])is str and bool(value['class'])and type(value['identity'])is str and value['identity'].startswith(value['class']+'@'),'actual runtime reference class/identity')
  if kind=='typed-snapshot':
   templates={
    'android.view.inputmethod.ExtractedText':[('text','java.lang.CharSequence:string'),('startOffset','int'),('partialStartOffset','int'),('partialEndOffset','int'),('selectionStart','int'),('selectionEnd','int'),('flags','int')],
    'android.view.inputmethod.SurroundingText':[('text','java.lang.CharSequence:string'),('start','int'),('end','int'),('offset','int')],
    'android.view.inputmethod.TextSnapshot':[('text','android.view.inputmethod.SurroundingText')],
    'android.text.SpannableStringBuilder':[('text','java.lang.String'),('spans','ordered-span-records')]}
   need(value['class']in templates,'selected typed snapshot implementation');fields=value['fields'];template=templates[value['class']];need(type(fields)is list and len(fields)==len(template),'complete immutable ordered snapshot fields')
   for field,(name,declared)in zip(fields,template):
    need(type(field)is dict and set(field)=={'field','type','value'}and field['field']==name and field['type']==declared,'exact snapshot field/type/order');actual=field['value']
    if declared=='int':need(type(actual)is int and -(2**31)<=actual<2**31,'snapshot JVM int type/range')
    elif declared=='java.lang.CharSequence:string':need(actual is None or type(actual)is str,'snapshot immutable nullable text')
    elif declared=='java.lang.String':need(type(actual)is str,'snapshot immutable text')
    elif declared=='android.view.inputmethod.SurroundingText':native_value(actual);need(actual['kind']=='null'or actual.get('class')==declared,'snapshot nested declared type')
    elif declared=='ordered-span-records':
     need(type(actual)is list and len(actual)<=4096,'bounded immutable ordered span records')
     for span in actual:
      need(type(span)is list and len(span)==4,'complete immutable span fields')
      for item,(spanname,spantype)in zip(span,[('object','identity'),('start','int'),('end','int'),('flags','int')]):
       need(type(item)is dict and set(item)=={'field','type','value'}and item['field']==spanname and item['type']==spantype,'span exact field/type/order');need((item['value']is None or type(item['value'])is str)if spantype=='identity'else type(item['value'])is int and -(2**31)<=item['value']<2**31,'span exact value type')
 else:raise ValueError('unsupported actual value kind '+kind)
 return value

def native_completion(item):
 need(type(item)is dict and type(item.get('completion'))is str,'actual native completion object');native_value(item['value'])
 if item['completion']=='exception':
  need(item['value']=={'kind':'null'}and item['descriptor']=='hook-exception'and all(type(item[key])is str and bool(item[key])for key in('original_exception_class','original_exception_identity')),'actual observed original hook exception without scalar inference');return {'kind':'exception','class':item['original_exception_class'],'identity':item['original_exception_identity'],'observation':'hook exception; normal native body outcome pending'}
 need(item['completion']=='return'and item['original_exception_class']is None and item['original_exception_identity']is None,'actual normal return has no exception');descriptor=item['descriptor'];need(type(descriptor)is str and descriptor.startswith('(')and descriptor.count(')')==1,'actual JVM native return descriptor');result=descriptor.split(')',1)[1];kind=item['value']['kind']
 allowed={'V':{'null'},'Z':{'boolean'},'B':{'integer'},'S':{'integer'},'I':{'integer'},'J':{'integer'},'F':{'floating'},'D':{'floating'},'C':{'character'}}
 need(kind in(allowed[result]if result in allowed else{'null','reference','typed-snapshot','string'}if result.startswith(('L','['))else set()),'actual observed value matches original JVM return kind')
 if result in('B','S','I','J'):
  bits={'B':8,'S':16,'I':32,'J':64}[result];need(-(2**(bits-1))<=item['value']['value']<2**(bits-1),'actual primitive integer return range')
 return {'kind':'void'}if result=='V'else item['value']

SINGLE_STATE_DRIVER_SHA256='35517ace555f55a81ff105faf10775768ac6154fabdad8ea90e5dbda83b1f1a6'

def selected_packet(path,seal_sha,selection,selection_sha):
 need(ident(path/'seal.json')['sha256']==seal_sha and ident(selection)['sha256']==selection_sha,'root-selected exact finite reference identity');seal=loads((path/'seal.json').read_bytes());members=seal['members'];need({str(item.relative_to(path))for item in path.rglob('*')if item.is_file()}=={'seal.json'}|{item['path']for item in members},'closed selected finite reference')
 for item in members:need(same(ident(path/item['path']),{key:item[key]for key in('bytes','sha256')}),'selected finite reference exact member '+item['path'])
 return seal

class Audit:
 def __init__(self,run,recovery=None):
  self.run=run;self.receipt=loads((run/'receipt.json').read_bytes());self.recovery=recovery;self.recovery_files=[];self.excluded_parent_files=set();self.recovery_binding=None;self.v1=[];self.external_finite=[];need(self.receipt['all_commands_passed']is True or recovery is not None,'retained failing producer needs explicit bounded recovery, never a parent pass');need(self.receipt['cleanup']['all_children_reaped'] is True and self.receipt['cleanup']['scratch_removed'] is True,'producer cleanup incomplete')
  self.classmap=loads((run/'class-map.json').read_bytes());need(set(self.classmap)=={str(p.relative_to(run/'classes'))for p in (run/'classes').rglob('*.class')},'complete emitted class set')
  reference=Q/'semantic-review-candidate-v1';need(ident(reference/'seal.json')['sha256']=='361412b6ee2124ace685a2242390ece375d0327b119876b13db27dc95ea3f5e6','immutable reference packet identity');seal=loads((reference/'seal.json').read_bytes());members=seal['members'];members={item['path']:{key:item[key]for key in('bytes','sha256')}for item in members}if type(members)is list else members
  for name in('active-semantic-obligations.json','historical189-current-bindings.json','product-context.json','reference-obligations.json'):need(ident(reference/name)==members[name],'immutable reference member identity '+name)
  self.classes={};self.methods={};self.instructions={};self.subjects={x['id']:x for x in loads((reference/'active-semantic-obligations.json').read_bytes())['subjects']};need(len(self.subjects)==280,'immutable full280 inventory')
  context=loads((reference/'product-context.json').read_bytes());self.productmap=context['class_map'];self.source_hashes={}
  freeze=loads((run/'source-freeze.json').read_bytes());need(freeze['product_context_id']==CONTEXT,'actual product context');need(freeze['passive_derivative_seal']['sha256']=='8501bfa60dbae4c3d90be181e8d4fe1e858d1f59908328c4c9855fe7bc99eff8','selected v4 source derivative')
  for item in freeze['sources']:
   original=R/item['path'];owned=run/original.name;path=owned if owned.is_file()else original
   need(same(ident(path),{k:item[k]for k in ('bytes','sha256')}),'actual compiled source changed: '+item['path']);self.source_hashes[path.name]=item['sha256']
  need({name:self.source_hashes.get(name)for name in context['source_map']}=={name:value['sha256']for name,value in context['source_map'].items()},'all immutable exact16 source identities')
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
  immutable=loads((reference/'reference-obligations.json').read_bytes());expected38=immutable['exact38_descriptors'];need(type(expected38)is list and len(expected38)==38 and len(set(expected38))==38,'immutable exact descriptor set38')
  interface=parse((run/'classes/android/view/inputmethod/InputConnection.class').read_bytes());actual38={method['name']+method['descriptor']for method in interface['methods']if not method['name'].startswith('<')and not(method['access']&8)};need(actual38==set(expected38),'exact SDK-facing38 descriptor set; count alone is insufficient');self.descriptor38=[]
  for descriptor in sorted(actual38):
   current='dev/mixer/android/NativeEditorConnectionV2$Api34';found=None
   while current in self.classes:
    for method in self.classes[current]['methods']:
     if method['name']+method['descriptor']==descriptor and method['access']&1 and not(method['access']&8):found=(current,method);break
    if found is not None:break
    current=self.classes[current]['super']
   need(found is not None and found[0].startswith('dev/mixer/android/NativeEditorConnectionV2$')and not(found[1]['access']&1024),'actual concrete direct adapter resolution for '+descriptor);owner,method=found;self.descriptor38.append({'descriptor':descriptor,'declaring_class':owner,'class_sha256':self.classmap[owner+'.class']['sha256'],'source_sha256':self.source_hashes[self.classes[owner]['source_file']],'scope':'actual compiled method resolution; behavioral outcomes remain separately joined'})
  failed={item['label']:item for item in self.receipt['commands']if item['exit']!=0 or item['timeout']}
  if recovery is None:need(not failed and self.receipt['all_commands_passed']is True,'all actual parent child results must pass')
  else:
   need(bool(failed)and self.receipt['all_commands_passed']is False,'explicit recovery only for retained failed parent');need(recovery.is_relative_to(S),'owned bounded recovery input');rr=loads((recovery/'receipt.json').read_bytes());ref=loads((recovery/'parent-reference.json').read_bytes());closure=loads((recovery/'execution-closure.json').read_bytes());driver_map=loads((recovery/'driver-class-map.json').read_bytes());need(rr['status']=='passed-unchanged-body-single-state-recovery'and rr['all_commands_passed']is True and rr['all_children_reaped']is True and rr['scratch_removed']is True and rr['failed_parent_promoted']is False,'separate successful bounded recovery, no parent promotion')
   need(same(ref['receipt'],ident(run/'receipt.json'))and same(ref['class_map'],ident(run/'class-map.json'))and same(ref['source_freeze'],ident(run/'source-freeze.json'))and same(ref['failed_children'],failed),'exact failed-parent source/class/child receipt binding');need(all(item['timeout']is True and item['reaped']is True and type(item['timeout_seconds'])is int and item['timeout_seconds']==60 and label.startswith('boundary-')for label,item in failed.items()),'only failed bounded historical children may be recovered')
   need(ident(recovery/'LegacyBoundarySingleState.java')['sha256']==SINGLE_STATE_DRIVER_SHA256,'exact additional unchanged-body driver source');need(set(driver_map)=={'dev/mixer/android/LegacyBoundarySingleState.class'}and not(set(driver_map)&set(self.classmap)),'one additional driver class with no shadowing');need({str(path.relative_to(recovery/'driver-classes'))for path in(recovery/'driver-classes').rglob('*')if path.is_file()}==set(driver_map),'closed additional driver class set')
   for relative,expected in driver_map.items():need(same(ident(recovery/'driver-classes'/relative),expected),'actual additional driver class bytes')
   need(same(closure['parent_class_map'],self.classmap)and same(closure['additional_driver_class_map'],driver_map)and same(closure['driver_source'],ident(recovery/'LegacyBoundarySingleState.java'))and same(closure['original_source_freeze'],ident(run/'source-freeze.json'))and same(closure['tools'],freeze['tools']),'distinct exact recovery execution closure')
   command_labels={'java-version','javac-version','compile-single-state-driver'}|{label+'-'+state for label in failed for state in STATES};commands=rr['commands'];need(len(commands)==len(command_labels)and{item['label']for item in commands}==command_labels and all(type(item['exit'])is int and item['exit']==0 and item['timeout']is False and item['reaped']is True and type(item['timeout_seconds'])is int and item['timeout_seconds']==60 for item in commands),'complete exact bounded recovery command/state set')
   for label in failed:
    self.excluded_parent_files.add(label+'.rows.jsonl.gz');binding=loads((run/(label+'.binding.json')).read_bytes())['records'][0];need(same(ident(recovery/(label+'.binding.json')),ident(run/(label+'.binding.json'))),'recovery unchanged original binding file')
    for state in STATES:self.recovery_files.append((recovery/(label+'-'+state+'.rows.jsonl.gz'),binding['historical_id'],state))
   need({path.name for path in recovery.glob('*.rows.jsonl.gz')}=={path.name for path,identity,state in self.recovery_files},'closed exact recovered raw state file set');self.recovery_binding={'receipt':ident(recovery/'receipt.json'),'execution_closure':ident(recovery/'execution-closure.json'),'additional_driver_class_map':driver_map,'failed_parent_retained':True,'excluded_partial_files':[{'file':name,**ident(run/name)}for name in sorted(self.excluded_parent_files)]}
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
   need(same(row['actual'],row['expected']),'renderer finite literal outcome');need(row['typed_outcome']in('java.lang.Boolean','throw'),'renderer actual typed completion');need(row['all_snapshots_unchanged']is True and row['snapshot_before_sha256']==row['snapshot_after_sha256'],'renderer immutable snapshot equality');need(same(row['counts_before'],row['counts_after']) and integer(row['native_effects'],'finite native effects integer')==0 and integer(row['native_events_before'],'finite native prefix integer')==integer(row['native_events_after'],'finite native suffix integer'),'renderer finite counts/no native effects')
  elif kind=='renderer-ledger-constructor':
   need(same(row['actual_after'],row['literal_expected_after']),'renderer ledger/constructor independent literal values');need(row['actual_typed_outcome']['kind']in('void','constructed-reference')and row['actual_typed_outcome']['exception']is None,'renderer finite typed normal completion');need(row['unchanged_non_target_fields_and_containers']is True and same(row['counts_before'],row['counts_after'])and integer(row['native_effects'],'finite native effects integer')==0 and integer(row['native_events_before'],'finite native prefix integer')==integer(row['native_events_after'],'finite native suffix integer'),'renderer finite unchanged non-target fields/counts/native prefix')
  elif kind=='renderer-state-journal-constructors':
   need(row['native_outcome_capture_clean']is True and row['mutations_restored']is True and row['original_authority_references_preserved']is True and row['no_membership_or_release_authority']is True,'constructor bounded facet contract');need(same(row['counts_before'],row['counts_after']),'constructor counts unchanged');need(row['enclosing_completion']in('normal-object','exact-exception'),'actual constructor outcome kind')
   if row['native_site_id']is not None:
    need(row['callback_state']in STATES,'constructor canonical state');need(type(row['exact_tuple_hooks'])is list and len(row['exact_tuple_hooks'])==2,'constructor entry/return pair')
    bci=integer(int(row['native_site_id'].split('@')[-1].split(':')[0]),'constructor immutable BCI');allowed=(67,145,222)if subject['class'].endswith('$NativeState')else(184,192);need(bci in allowed,'independent selected constructor tuple');key=(subject['class'],subject['method'],subject['descriptor'],bci);instruction=self.instructions[key];target=instruction['target'];need(row['native_site_id']==row['subject_id']+'@'+str(bci)+':'+instruction['mnemonic']+':'+target['owner']+'#'+target['name']+target['descriptor'],'constructor native-site exact opcode/callee identity')
    for hook in row['exact_tuple_hooks']:
     need(hook['receiver']==hook['original_own_receiver']and hook['phase']in('entry','beforeReturn'),'constructor own receiver/phase');integer(hook['event_index'],'constructor event identity index');need(type(hook['event_reference'])is str and bool(hook['event_reference']),'constructor immutable event reference');need(len(hook['frames'])<24,'constructor selected full filtered stack not capped');actual=self.frames(hook['frames']);need(key in[value[0]for value in actual],'constructor selected frame exact reviewed tuple')
   else:need(row['callback_state']=='finite-no-fabricated-callback','constructor finite no artificial callback')
  elif kind=='field-preservation-replacement':
   need(row['original_required_cases_retained']is True and row['shared_mutations_restored']is True and row['no_native_events']is True and row['no_membership_release_authority']is True and same(row['counts_before'],row['counts_after']),'four-body selected finite scope')
   need(row['native_callback_state']=='not-applicable-no-fabricated-native-callback','interface observation cannot become native callback credit');oracle=row['independent_expected_before_invocation'];observation=row['input_observation']
   if observation is not None:
    need(observation['method']=='editorLossObservation'and observation['descriptor']=='()J'and type(observation['calls'])is int and observation['calls']in(0,1)and observation['instrumentation_only_no_native_callback']is True,'exact original Input observation')
    if observation['calls']:
     need(type(observation['production_call_frames'])is list and len(observation['production_call_frames'])<24,'complete bounded original Input caller frames');self.frames(observation['production_call_frames'])
   if row['completion']=='exact-actual-input-exception':need(observation is not None and row['exact_exception_reference']==observation['actual_exception_reference']and row['actual_result']is None and observation['actual_return_long']is None,'exact original Input exception propagation; no constructor receiver inferred')
   else:
    need(row['completion']=='normal','actual four-body finite completion')
    if subject['method']=='endReady':need(type(row['actual_result'])is bool and row['actual_result']==oracle['expected']and same(row['actual_before'],row['actual_after']),'literal endReady truth table and unchanged receiver')
    elif subject['method']=='unchangedLoss':need(type(row['actual_result'])is bool and row['actual_result']==oracle['expected_boolean']and same(row['actual_before'],row['actual_after'])and same(observation['calls'],oracle['expected_Input_calls']),'literal exact-long/lost short-circuit and unchanged receiver')
    else:
     after=row['actual_after'];need(type(after)is dict and type(row['actual_result'])is str and row['actual_result']==after['reference'],'actual constructed finite reference')
     for key,wanted in oracle.items():
      if key in('all_flags_false','hooks','Input_calls'):continue
      actual=after[key];need(actual==wanted or(wanted is None and actual=='null'),'literal captured constructor field '+key)
     need(after['hooks_values']==[]and type(after['hooks_reference'])is str,'fresh empty constructor hook container')
  self.finite[row['subject_id']].append({**locator,'facet':kind,'case_id':row.get('control_case',row.get('case_id',row.get('sequence'))),'step':row.get('step'),'callback_state':row.get('callback_state'),'class_sha256':classhash,'source_sha256':subject['source_sha256'],'actual_typed_outcome':row.get('actual_outcome',row.get('actual_typed_outcome',row.get('typed_outcome',row.get('typed_result',row.get('enclosing_completion'))))),'scope':'Only the exact executed finite/object/result/callback facet. Original enclosing obligations are retained pending independent disposition.'})
 def v1_file(self):
  path=self.run/'v1-exact-five.json';need(path.is_file(),'fresh separate five V1 positives required');packet=R/'verification/android-editor-membership-qualification-independent/v1-positive-preparation';selected_packet(packet,'d982305bafe8abcfc6945ea37ca8ff908aa748f00dfcad7e303517b327d74c8f',R/'verification/android-editor-boundary-root-review/five-v1-positive-selection.json','6fac4c3e42768235bec2a1e22398859c6638a44b59ecf1d7af945dcd7022dd0f');approved=loads((packet/'run-1/bound-five-v1-proposal.json').read_bytes());actual=loads(path.read_bytes());need(same(approved['product_class_map'],self.productmap),'V1 approved exact product209 context');expectedrows=[{key:value for key,value in row.items()if key!='caller'}for row in approved['rows']];need(same(actual['rows'],expectedrows)and same(actual['event_sequence'],approved['event_sequence']),'fresh V1 receiver/frame/count/content/enclosing outcome equal exact root-selected witness contract');need({integer(row['bci'],'V1 BCI integer')for row in actual['rows']}=={111,220,262,381,398}and len(actual['rows'])==5,'exact distinct five V1 callers')
  for row,expected in zip(actual['rows'],approved['rows']):
   caller=expected['caller'];key=(caller['class'],caller['method'],caller['descriptor'],caller['bci']);need(key in self.instructions,'V1 exact actual compiled caller');instruction=self.instructions[key];need(instruction['mnemonic']==caller['opcode']and same(instruction['target'],caller['callee'])and self.classmap[caller['class']+'.class']['sha256']==caller['class_sha256']and self.source_hashes[self.classes[caller['class']]['source_file']]==caller['source_sha256'],'V1 exact source/class/descriptor/BCI/opcode/callee');need(row['authority_mode']=='LEGACY_V1'and row['captured_attempt_identity']is None and row['v2_fence']is None,'V1 cannot borrow V2 authority')
   self.v1.append({'id':row['id'],'caller':caller,'actual_entry':row['entry'],'actual_before_return':row['before_return'],'actual_enclosing_result':row['enclosing_result'],'identity_namespace':'separate actual V1 witness IdentityHashMap # identities; no transfer to V2 @ identities','scope':'Root-selected five separate V1 positive controls. Actual enclosing normal legacy-apply result and receiver/content/count/fullframes; no V2 callback/authority or unobserved helper return credit.'})
  self.files.append({'file':path.name,**ident(path),'facet':'separate-five-V1-positives','positive_sites':5})
 def selected_field_observation(self):
  packet=R/'verification/android-field-preservation-observation-controls';selected_packet(packet,'02f4a046dd7f10266e17b804c6b86bd857f19807306bcf17214f9d5914e81250',R/'verification/android-editor-boundary-root-review/field-observation-host-acceptance.json','a13a548a9ebd2cb8398719013e4aff7dc51ac0deab7de9dc5679c3c0a0f2768b');joins=loads((packet/'finite-facet-joins.json').read_bytes());result=loads((packet/'run-3/actual-results.json').read_bytes());original=loads((packet/'inputs/exact-four-subject-contracts.json').read_bytes());need(joins['source_context']==result['source_context']==CONTEXT and same(result['actual_original_boundary_counts'],[2,2,3])and same(result['actual_final_counts'],[0,0,0])and result['original_edit_completed_after_restores']is True and result['failure_latch_clear']is True,'selected external finite source context and original edit restoration');need(type(result['rows'])is list and len(result['rows'])==56 and result['checks']==731,'exact root-selected finite56 observations')
  selected={item['id']:item for item in original['subjects']};need(len(selected)==4 and all(same(item,self.subjects[key])for key,item in selected.items()),'all four whole original semantic records unchanged');seen=set()
  for join in joins['subjects']:
   subject=join['subject_id'];need(subject in selected and join['class_sha256']==self.classmap[selected[subject]['class']+'.class']['sha256']and join['source_sha256']==selected[subject]['source_sha256'],'selected four finite source/class joins');need([item['case']for item in join['original_required_semantic_cases']]==selected[subject]['required_semantic_cases'],'all original eight cases retained pending')
   for index in join['actual_row_indexes']:
    index=integer(index,'selected actual finite row index');need(index not in seen and index<len(result['rows']),'unique exact selected finite row');seen.add(index);row=result['rows'][index];need(row['subject_id']==subject and row['class_sha256']==join['class_sha256']and row['original_eight_cases_retained_without_discharge']is True and row['restored_before_original_edit_resumes']is True and row['no_membership_release_authority']is True and same(row['counts_before'],[2,2,3])and same(row['counts_after'],[2,2,3]),'source-bound finite row/restoration/no authority transfer');method=selected[subject]['method']
    if row['actual_method_completion']=='exception':need(row['actual_result']is None and type(row['exact_exception_reference'])is str and row['exact_exception_reference']!='null'and type(row['exception_type'])is str,'actual exact finite exception identity');outcome={'kind':'exception','class':row['exception_type'],'identity':row['exact_exception_reference']}
    else:
     need(row['actual_method_completion']=='normal','explicit actual finite method completion')
     if method=='tuple':need(type(row['actual_result'])is bool,'actual tuple scalar result');outcome={'kind':'boolean','value':row['actual_result']}
     elif method in('capture','exact'):need(row['actual_result']is None,'actual reflected JVM void completion');outcome={'kind':'void'}
     else:need(type(row['actual_result'])is dict and row['actual_result']['field_lease']==row['actual_before']['reference'],'actual returned Mutation exact field lease');outcome={'kind':'typed-observed-Mutation','fields':row['actual_result']}
    for observed in row['actual_native_getter_outcomes']:
     parsed=self.frames(observed['production_frames']);need(('dev/mixer/android/NativeAppearanceViewsV2$FieldPreservation','exact','()V',40)in[key for key,instruction in parsed],'actual exact getter BCI source join')
    self.finite[subject].append({'input_path':str((packet/'run-3/actual-results.json').relative_to(R)),'row':index+1,'facet':'root-selected-external-finite-field-observation','case_id':row['finite_case'],'class_sha256':join['class_sha256'],'source_sha256':join['source_sha256'],'actual_typed_outcome':outcome,'scope':'Consumed root-reviewed external fresh finite evidence; not a new producer invocation. Original eight cases, exact subject Input counts/BCIs, enclosing/allocation/authority obligations remain pending.','limits':['Final Record.view/Input unchanged; seven separately observed original Input returns are not subject invocation counts.','Shared.events literal zero proves no event-restoration coverage.','Fixture close catches exceptions; full post-disposal state is unasserted.']})
  need(seen==set(range(56)),'complete56 exact selected external finite row joins');self.external_finite.append({'packet':'verification/android-field-preservation-observation-controls','seal_sha256':'02f4a046dd7f10266e17b804c6b86bd857f19807306bcf17214f9d5914e81250','root_acceptance_sha256':'a13a548a9ebd2cb8398719013e4aff7dc51ac0deab7de9dc5679c3c0a0f2768b','finite_invocations':56,'scope':'separate selected external finite facets; no own fresh-replay or complete execution closure claim'})
 def public_finite_files(self):
  families={}
  for item in self.descriptor38:
   descriptor=item['descriptor'];name=descriptor.split('(',1)[0];family=name
   if name in('commitText','setComposingText','setComposingRegion')and'Landroid/view/inputmethod/TextAttribute;'in descriptor:family=name+'WithAttributes'
   if descriptor=='requestCursorUpdates(II)Z':family='requestCursorUpdatesFiltered'
   need(family not in families,'unique exact public descriptor family');families[family]=item
  need(len(families)==38,'exact public family set38')
  path=self.run/'direct-finite-38.rows.jsonl.gz'
  if path.is_file():
   signal.alarm(60);refusals={'sendKeyEvent','commitContent','commitCorrection','performPrivateCommand','performSpellCheck','replaceText','previewHandwritingGesture','performHandwritingGesture','requestTextBoundsInfo'};invalid={'commitText','commitTextWithAttributes','setComposingText','setComposingTextWithAttributes','setComposingRegion','setComposingRegionWithAttributes','deleteSurroundingText','deleteSurroundingTextInCodePoints','setSelection','performEditorAction','commitCompletion','requestCursorUpdates','requestCursorUpdatesFiltered','getTextBeforeCursor','getTextAfterCursor','getExtractedText','getSurroundingText'};expected={(family,'wrong-thread')for family in families}
   expected|={(family,state)for family in refusals|{'getHandler'}for state in('current','terminal','dirty','stale','changing')};expected|={(family,'invalid-argument')for family in invalid};expected|={(family,'null-executor')for family in('performHandwritingGesture','requestTextBoundsInfo')};seen=set()
   with gzip.open(path,'rt')as stream:
    for number,line in enumerate(stream,1):
     row=loads(line);key=(row['family'],row['state']);need(key in expected and key not in seen,'exact unique direct finite descriptor/case');seen.add(key);binding=families[row['family']];descriptor=binding['descriptor'];name=descriptor.split('(',1)[0];signature=descriptor[len(name):];need(same(row['actual_method'],{'class':binding['declaring_class'].replace('/','.'),'method':name,'descriptor':signature}),'actual full direct public method/descriptor/class');need(row.get('status')=='passed-finite-typed-case'and 'validation_failure'in row and row['validation_failure']is None,'finite public validation result');need(integer(row['native_target_delta'],'finite target count')==0 and integer(row['jni_prepare_delta'],'finite prepare count')==0 and integer(row['jni_commit_delta'],'finite commit count')==0,'finite zero native target/feature forwarding');events=integer(row['native_events'],'finite actual native getter count');outcome=row['actual_outcome'];need(type(outcome)is dict,'finite actual typed public outcome')
     callbacks=[]
     if row['state']=='wrong-thread'and row['family']!='getHandler':need(set(outcome)=={'kind','class','identity','message'}and outcome['kind']=='exception'and outcome['class']=='java.lang.IllegalStateException'and type(outcome['identity'])is str and bool(outcome['identity'])and type(outcome['message'])is str,'actual off-main original guard exception')
     else:
      expected_kind='null'if name=='getHandler'or(row['state']=='invalid-argument'and not signature.endswith('Z'))else'void'if signature.endswith('V')else'boolean';literal={'kind':expected_kind,**({'value':False}if expected_kind=='boolean'else{})};need(same(outcome,literal),'literal exact finite public refusal/null/void result')
      if row['state']not in('wrong-thread','null-executor')and name in('performHandwritingGesture','requestTextBoundsInfo'):callbacks=['executor',{'kind':'integer','value':2}if name=='performHandwritingGesture'else{'kind':'TextBoundsInfoResult','code':3,'bounds_null':True}]
     need(same(row['actual_callbacks'],callbacks)and same(row['expected_callbacks'],callbacks),'literal typed unsupported callback value/order')
     if row['state']!='invalid-argument':need(events==0,'finite pre-public/constant body zero native leaf events')
     subject=binding['declaring_class']+'#'+descriptor;need(subject in self.subjects,'finite public exact immutable subject');self.finite[subject].append({'file':path.name,'row':number,'facet':'exact-public-descriptor-finite-guard-or-refusal','case_id':row['state'],'family':row['family'],'class_sha256':binding['class_sha256'],'source_sha256':binding['source_sha256'],'actual_typed_outcome':outcome,'actual_callbacks':callbacks,'native_getter_events':events,'scope':'Exact finite public guard/argument/constant-refusal case only. Getter events are not native target forwarding. Original semantic/enclosing cases remain pending.'})
   need(seen==expected,'complete immutable direct finite38 case set');self.files.append({'file':path.name,**ident(path),'facet':'exact38-public-finite','finite_invocations':len(seen)});signal.alarm(0)
  path=self.run/'unsupported-callbacks.rows.jsonl.gz'
  if path.is_file():
   signal.alarm(60);expected={(family,boundary,state)for family in('handwriting','bounds')for boundary in('executor','receiver')for state in STATES};seen=set()
   with gzip.open(path,'rt')as stream:
    for number,line in enumerate(stream,1):
     row=loads(line);key=(row['family'],row['boundary'],row['state']);need(key in expected and key not in seen,'exact unique unsupported callback case');seen.add(key);method='performHandwritingGesture'if row['family']=='handwriting'else'requestTextBoundsInfo';binding=families[method];descriptor=binding['descriptor'];subject=binding['declaring_class']+'#'+descriptor;callbacks=['executor',{'kind':'integer','value':2}if row['family']=='handwriting'else{'kind':'TextBoundsInfoResult','code':3,'bounds_null':True}];need(same(row['actual_callbacks'],callbacks)and same(row['expected_callbacks'],callbacks),'source literal unsupported callback value/order');native_value(row['actual_enclosing_outcome']);need(same(row['actual_enclosing_outcome'],row['expected_enclosing_outcome']),'actual original public void/exception identity');need(row['status']=='passed-constant-unsupported-callback-state'and row['validation_failure']is None and row['attempt_clean_latched']is True and row['no_feature_transaction']is True and integer(row['native_unsupported_forward_count'],'unsupported native forward count')==0,'constant unsupported callback capture/no-feature/no-native forwarding')
     if row['state'].endswith('throw-after-callback'):need(row['actual_enclosing_outcome']['kind']=='exception'and row['actual_enclosing_outcome']['class']==('java.lang.IllegalStateException'if row['state'].startswith('ordinary')else'dev.mixer.android.UnsupportedCallbackStates$Fatal'),'original source-authored callback exception')
     else:need(same(row['actual_enclosing_outcome'],{'kind':'void'}),'actual normal unsupported public void completion')
     frames=row['selected_callback_frames'];need(type(frames)is list and len(frames)==2 and[point['phase']for point in frames]==['entry','beforeReturn'],'actual unsupported callback entry/return pair');wanted=[(binding['declaring_class'],method,descriptor[len(method):],18 if row['family']=='handwriting'else 30)]
     if row['boundary']=='receiver':wanted.insert(0,(binding['declaring_class'],'lambda$performHandwritingGesture$0'if row['family']=='handwriting'else'lambda$requestTextBoundsInfo$1','(Ljava/util/function/IntConsumer;)V'if row['family']=='handwriting'else'(Ljava/util/function/Consumer;Landroid/view/inputmethod/TextBoundsInfoResult;)V',2))
     for point in frames:need([key for key,ins in self.frames(point['frames'])]==wanted,'exact per-overload complete executor/consumer callback source chain')
     self.finite[subject].append({'file':path.name,'row':number,'facet':'constant-unsupported-executor-consumer-callback','case_id':row['boundary']+'/'+row['state'],'class_sha256':binding['class_sha256'],'source_sha256':binding['source_sha256'],'actual_typed_outcome':row['actual_enclosing_outcome'],'actual_callbacks':callbacks,'actual_callback_frames':frames,'scope':'Ordinary JVM executor/consumer callback and enclosing public result. No field/attempt authority, native Android leaf, lambda method-exit, or allocated callback-object identity credit; original cases remain pending.'})
   need(seen==expected,'complete exact unsupported2 x boundaries2 x states7');self.files.append({'file':path.name,**ident(path),'facet':'unsupported-callback','finite_invocations':len(seen)});signal.alarm(0)
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
  need('validation_failure'in row and row['validation_failure']is None,'required explicit behavior validation outcome')
  need(type(row.get('status'))is str and row['status']in('passed','passed-close-state','passed-callback-scope-state; outcome-review-required'),'exact supported candidate row status')
  if 'cleanup_failure'in row:need(row['cleanup_failure']is None,'retained cleanup failure')
  bindings,receiver_report=receiver_row(row)
  for completion in row['actual_native_outcomes']:native_completion(completion)
  for name in('actual_operation_outcome','actual_enclosing_outcome','enclosing_actual_outcome'):
   if name in row:native_value(row[name])
  if row.get('historical_id'):need(row['enclosing_actual_outcome']['kind']in('void','exception'),'unchanged historical scenario has actual enclosing void or original exception')
  if 'original_attempt_close'in row:need(row['actual_enclosing_outcome']['kind']in('void','exception'),'close has actual enclosing void or original exception')
  for name,value in row.items():
   if name not in('native_sequence','frame_sets','actual_native_outcomes'):need(name in small and same(value,small[name]),'raw/compact original field changed: '+name)
  need(small.get('complete_raw_trace_retained')is True,'required retained raw backing')
  sequence=row['native_sequence'];sets=row['frame_sets'];need(type(sequence)is list and type(sets)is list,'structured trace');need(integer(small['native_event_count'],'exact native event count')==len(sequence),'event count changed');digest=hashlib.sha256();counts=collections.Counter()
  for event in sequence:
   need(type(event)is dict and event['phase']in('entry','beforeReturn')and type(event['method'])is str,'structured native event');index=integer(event['frame_set'],'integer frame-set index');need(index<len(sets),'event frame-set bounds');encoded=canonical(event);digest.update(len(encoded).to_bytes(4,'big'));digest.update(encoded);counts[event['method']+'/'+event['phase']]+=1
  need(digest.hexdigest()==small['ordered_native_event_digest'] and same(dict(counts),small['native_event_counts']),'ordered raw event reconciliation')
  points=small['selected_immutable_event_points'];need(type(points)is list,'selected structured event points');selected=set();pairs={}
  rawpoints=[]
  if 'selected'in row:
   need(type(row['selected'])is dict,'selected historical event structure')
   if row['selected']:rawpoints.append(row['selected'])
  if 'selected_event'in row:
   value=row['selected_event'];need(type(value)in(list,dict),'selected direct/close event structure');rawpoints.extend(value if type(value)is list else[value])
  expectedpoints=[]
  for rawpoint in rawpoints:
   need(type(rawpoint)is dict,'raw selected event object');index=integer(rawpoint['sequence_index'],'raw selected exact event index');need(index<len(sequence),'raw selected event bounds');event=sequence[index];need(integer(rawpoint['frame_set'],'raw selected exact frame index')==event['frame_set'],'raw selected event/frame association')
   wanted=(rawpoint['receiver_authority']['receiver']if row.get('historical_id')else row['original_target']);need(bindings[event['receiver_identity']]==wanted,'selected raw receiver maps to captured original object')
   if row.get('historical_id'):need(rawpoint['receiver_identity']==event['receiver_identity'],'historical selected exact ordinal receiver')
   elif 'authority'in rawpoint:need(rawpoint['authority']['receiver']==wanted,'direct selected captured receiver authority')
   expectedpoints.append({'sequence_index':index,'native_event':event,'production_frames':sets[event['frame_set']]})
  need(same(points,expectedpoints),'exact raw selected event points and compact projection')
  if row.get('historical_id'):need(row['selected_hook_fired']is True and len(points)==1 and type(row['selected'])is dict and bool(row['selected']),'historical mandatory actual selected hook')
  elif 'selected_hook_fired'in row:need(type(row['selected_hook_fired'])is bool and len(points)==(1 if row['selected_hook_fired']else 0),'exact public operation selected point/refusal')
  elif 'original_attempt_close'in row:need(len(points)==1,'mandatory actual close selected event')
  for point in points:
   index=integer(point['sequence_index'],'selected exact event index');need(index<len(sequence),'selected event bounds');event=sequence[index];need(same(point['native_event'],event)and same(point['production_frames'],sets[event['frame_set']]),'selected immutable raw event/frame equality');actual_frames=self.frames(point['production_frames']);selected.add(index)
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
  actualpairs={};need(type(small['selected_actual_call_pairs'])is list,'structured selected call pairs')
  for pair in small['selected_actual_call_pairs']:
   need(type(pair)is dict,'selected call pair object');index=integer(pair['selected_event_sequence_index'],'pair selected index');need(index not in actualpairs,'duplicate selected call pair');actualpairs[index]=pair
  expectedpairs={index:{'selected_event_sequence_index':index,'selected_phase':sequence[index]['phase'],'same_invocation_before_return_sequence_index':returned,'method':sequence[index]['method'],'receiver_identity':sequence[index]['receiver_identity'],'production_frames':sets[sequence[index]['frame_set']]}for index,returned in pairs.items()}
  need(same(actualpairs,expectedpairs),'exact full selected call-pair reconciliation')
  completion_events=selected|{value for value in pairs.values()if value is not None};expected=[]
  method=row.get('selected_leaf')or(row['selected']['native_method']if row.get('historical_id')else 'BaseInputConnection.closeConnection'if 'original_attempt_close'in row else 'BaseInputConnection.'+row['family'])
  receiver=row.get('original_target')or row.get('original_authority',{}).get('receiver')or row.get('selected',{}).get('receiver_authority',{}).get('receiver')
  for completion in row['actual_native_outcomes']:
   index=integer(completion['native_event_sequence_index'],'actual completion integer event index');need(index<len(sequence),'completion event bounds');event=sequence[index];need(completion['method']==event['method']and completion['native_event_phase']==event['phase']and same(completion['production_frames'],sets[event['frame_set']]),'actual completion event/frame join');need(completion['completion']in('return','exception'),'actual completion kind')
   if completion['method']==method and completion['receiver_identity']==receiver and index in completion_events:expected.append(completion)
  need(same(small['selected_actual_native_completions'],expected),'foreign or neighboring completion borrowed')
  return {**receiver_report,'state':row['state'],'historical_id':row.get('historical_id'),'family':row.get('family'),'selected_events':len(points),'selected_native_completions':len(expected),'missing_selected_native_completion':bool(points)and not expected,'actual_selected_native_typed_outcomes':[native_completion(item)for item in expected],'native_completion_credit':'actual recorded leaf completion only; enclosing helper and missing body exceptions remain pending'}
 def pairfile(self,path):
  signal.alarm(60);compact=Path(str(path)+'.compact.jsonl');need(compact.is_file(),'complete raw/compact pair');rows=[]
  with gzip.open(path,'rt',encoding='utf-8')as raw,compact.open()as small:
   for number,pair in enumerate(itertools.zip_longest(raw,small),1):
    need(all(value is not None for value in pair),'raw/compact row count differs');need(all(len(value)<=128*1024*1024 for value in pair),'bounded raw row');rows.append(self.row(loads(pair[0]),loads(pair[1]),{'file':path.name,'row':number}))
  self.files.append({'file':path.name,'input_path':str(path.relative_to(R)),**ident(path),'compact':ident(compact),'rows':rows});signal.alarm(0)
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
  return {'schema':2,'auditor_source':ident(Path(__file__).resolve()),'python':sys.version,'python_executable':sys.executable,'argv':sys.argv,'receiver_packet_sha256':RECEIVER_PACKET_SHA256,'receiver_root_selection_sha256':RECEIVER_SELECTION_SHA256,'status':'reconciled-read-only-candidate-observations; not-qualified','context_id':CONTEXT,'source_freeze':ident(self.run/'source-freeze.json'),'class_map':ident(self.run/'class-map.json'),'separate_five_V1_positives':self.v1,'selected_external_finite_facets':self.external_finite,'bounded_recovery':self.recovery_binding,'exact38_compiled_bindings':self.descriptor38,'subjects':output,'exact280_ids_retained':True,'historical189':[{'historical_id':key,'original_binding':value,'actual_state_observations':self.history[key],'status':'pending-disposition-and-outcome-review'}for key,value in self.historical.items()],'files':self.files,'execution_closure_and_native_OTA_GA_accepted':False}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--require-historical-states',action='store_true');parser.add_argument('--recovery',type=Path);args=parser.parse_args();run=args.run.resolve();out=args.output.resolve();need(run.is_relative_to(Q),'owned actual replay input');need(out.is_relative_to(S)and not out.exists(),'new owned output');signal.alarm(60);audit=Audit(run,args.recovery.resolve()if args.recovery else None);signal.alarm(0)
 for path in sorted(run.glob('*.rows.jsonl.gz')):
  if path.name not in audit.excluded_parent_files and Path(str(path)+'.compact.jsonl').is_file():
   audit.pairfile(path)
   if len(audit.files)%20==0:print('reconciled raw/compact files',len(audit.files),flush=True)
 for path,historical,state in audit.recovery_files:
  audit.pairfile(path);rows=audit.files[-1]['rows'];need(len(rows)==1 and rows[0]['historical_id']==historical and rows[0]['state']==state,'exact unchanged single-state recovery row')
 audit.finite_files()
 audit.public_finite_files()
 audit.v1_file()
 audit.selected_field_observation()
 if args.require_historical_states:audit.require_historical_states()
 value=audit.ledger();value['require_full189_callback_state_roster']=args.require_historical_states;out.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({'files':len(audit.files),'callback_trace_rows':sum(len(x.get('rows',[]))for x in audit.files),'finite_invocations':sum(x.get('finite_invocations',0)for x in audit.files),'subjects_with_finite_facets':sum(bool(x['finite_facets'])for x in value['subjects']),'subjects_with_actual_frames':sum(bool(x['actual_frame_observations'])for x in value['subjects']),'historical_with_actual_states':sum(bool(x['actual_state_observations'])for x in value['historical189']),'status':value['status']}))
if __name__=='__main__':main()
