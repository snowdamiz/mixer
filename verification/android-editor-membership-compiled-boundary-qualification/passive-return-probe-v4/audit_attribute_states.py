from pathlib import Path
import sys,json,gzip,hashlib,signal
signal.alarm(60)
D=Path(__file__).resolve().parent;Q=D.parent
sys.path.insert(0,str(Q));from classfile import parse
E=D/'attribute-states/run-2'
def ident(p):b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
context=json.loads((Q/'state-qualification/context17-1/product-context.json').read_bytes());classes={}
for rel,expected in context['class_map'].items():
 p=E/'classes'/rel;assert ident(p)==expected;classes[rel[:-6]]=parse(p.read_bytes())
summary=[]
for family in ['commitTextWithAttributes','setComposingTextWithAttributes']:
 path=E/('direct-'+family+'.rows.jsonl.gz');seen=set()
 with gzip.open(path,'rt') as source:
  for row_index,line in enumerate(source):
   row=json.loads(line);state=row['state'];assert state not in seen;seen.add(state);assert row['status']=='passed' and row['outcome_probe_clean'] is True
   own=[o for o in row['actual_native_outcomes'] if o['method']=='BaseInputConnection.'+family]
   refused=state in ['terminal','dirty','stale','changing'];exceptional=state in ['fatal','ordinary-throw-after-callback','fatal-throw-after-callback']
   if refused:assert not own and row['native_target_entries']==0 and row['observed_result'] is False;kind='zero-target-refusal'
   else:
    assert len(own)==1;observed=own[0];assert observed['receiver_identity']==row['original_target'];assert observed['production_frames']
    calls=[]
    for frame in observed['production_frames']:
     name=frame['class'].replace('.','/');compiled=classes[name];method=next(m for m in compiled['methods'] if m['name']==frame['method'] and m['descriptor']==frame['descriptor']);instruction=next(i for i in method['instructions'] if i['bci']==frame['bci']);assert instruction['opcode'] in [182,183,184,185,186];calls.append({'class':name,'class_sha256':context['class_map'][name+'.class']['sha256'],'method':frame['method'],'descriptor':frame['descriptor'],'bci':frame['bci'],'opcode':instruction['opcode'],'target':instruction.get('target')})
    selected=[call for call in calls if call['target'] and call['target'].get('owner')=='android/view/inputmethod/InputConnection' and call['target'].get('name')==('commitText' if family.startswith('commit') else 'setComposingText') and call['target'].get('descriptor')=='(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z'];assert len(selected)==1
    if exceptional:assert observed['completion']=='exception' and observed['original_exception_identity']==row['actual_operation_outcome']['identity'];kind='same-original-exception-no-normal-return'
    else:
     assert observed['completion']=='return' and observed['descriptor']=='(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z' and observed['value']['kind']=='boolean' and type(observed['value']['value']) is bool
     if state in ['current','successor','terminal-before-return','dirty-before-return']:assert observed['value']['value'] is True
     kind='actual-original-typed-boolean'
    summary.append({'family':family,'state':state,'row_index':row_index,'raw_file':str(path.relative_to(D)),'raw_identity':ident(path),'kind':kind,'actual_value':None if exceptional else observed['value'],'actual_enclosing_value':row['actual_operation_outcome'],'exact_own_caller':selected[0]});continue
   summary.append({'family':family,'state':state,'row_index':row_index,'raw_file':str(path.relative_to(D)),'raw_identity':ident(path),'kind':kind})
 assert seen=={'current','successor','terminal','dirty','stale','fatal','changing','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback'}
result={'scope':'Exact two added native return captures and26 direct state observations only; no fullmatrix/closure acceptance','product_context_id':context['context_id'],'controls':len(summary),'normal_captured':sum(x['kind']=='actual-original-typed-boolean' for x in summary),'same_original_exceptions':sum(x['kind']=='same-original-exception-no-normal-return' for x in summary),'zero_target_refusals':sum(x['kind']=='zero-target-refusal' for x in summary),'records':summary}
(D/'attribute-state-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='records'}))
