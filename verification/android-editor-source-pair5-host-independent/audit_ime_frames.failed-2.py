#!/usr/bin/env python3
from pathlib import Path
import base64,datetime,json,re
O=Path(__file__).resolve().parent;E=O/'runs/B';text=(E/'bytecode.stdout').read_text()+'\n'+(O/'runs/ime-bytecode-extra/stdout').read_text();methods={};cls=method=desc=None
for line in text.splitlines():
 if line and not line[0].isspace() and line.endswith('{'):
  m=re.search(r'(?:class|interface) ([\w.$]+)',line)
  if m:cls=m.group(1);method=desc=None
 elif line.startswith('  ') and not line.startswith('    ') and '(' in line and line.rstrip().endswith(';'):
  method=line.split('(',1)[0].split()[-1];desc=None
 elif line.strip().startswith('descriptor:'):
  desc=line.strip().split(': ',1)[1];methods[(cls,method,desc)]={}
 elif (m:=re.match(r'^\s+(\d+):\s+(.+)$',line)) and desc:
  methods[(cls,method,desc)][int(m.group(1))]=m.group(2)
r=json.loads((E/'imeControls-rows.json').read_text());rows=r['familyRows'];keys=r['sendKeyRefusals'];states={'current','successor','terminal','dirty','stale','fatal'};families={x['family'] for x in rows};assert len(families)==16 and len(rows)==96
assert len({(x['family'],x['state']) for x in rows})==96 and {x['state'] for x in rows}==states
textfamilies={'commitText','commitTextWithAttributes','setComposingText','setComposingTextWithAttributes','deleteSurroundingText','deleteSurroundingTextInCodePoints','commitCompletion'};natural=textfamilies|{'performEditorAction'};bindings=[]
for x in rows:
 assert x['passed'] and not x['injectionNativeBehaviorClaim'];assert base64.b64decode(x['actualTextUtf8Base64']).decode()==x['actualText'];assert x['sameEditable']
 live=x['state'] in {'current','successor'};entered=live or x['state']=='fatal';frames=x['actualTargetFrames']
 if entered:
  direct=[f for f in frames if f['class'].startswith('dev.mixer.android.NativeEditorConnectionV2$')];assert direct,(x['family'],x['state']);f=direct[0];key=(f['class'],f['method'],f['descriptor']);insn=methods[key][f['bytecodeIndex']];target=x['family'].replace('WithAttributes','');assert 'invokeinterface' in insn and 'android/view/inputmethod/InputConnection.'+target+':' in insn,(x['family'],f,insn)
  assert ('TextAttribute;' in insn)==x['family'].endswith('WithAttributes'),(x['family'],insn)
  assert x['targetEntries']==1;bindings.append({'family':x['family'],'state':x['state'],'exact_caller':f,'actual_instruction':insn})
 else:assert not frames and x['targetEntries']==0 and x['featureTransactions']==0 and not x['publishedSuccessor']
 if live:
  expects=x['family'] in natural or x['state']=='successor';assert x['returned'] and x['escaped'] is None and x['featureTransactions']==int(expects) and x['publishedSuccessor']==expects
  if x['family'] in textfamilies:assert x['actualText']==('AB' if x['family']=='deleteSurroundingTextInCodePoints' else 'hell' if x['family'].startswith('delete') else 'helloz')
 if x['featureTransactions']:
  ev=json.loads(x['eventInput']);assert ev['event']==('submit' if x['family']=='performEditorAction' else 'textChange')
  if ev['event']=='textChange':assert ev['value']==x['actualText']
 assert x['injectedSuccessor']==(x['state']=='successor' and x['family'] not in natural)
 if x['injectedSuccessor']:assert x['injectedProbe']['method']=='InjectedSuccessor.hostReplace' and x['injectedProbe']['phase']=='entry' and x['injectedProbe']['frames']
assert len(bindings)==48 and sum(x['injectedSuccessor'] for x in rows)==8
assert len(keys)==6 and len({x['state'] for x in keys})==6 and all(x['passed'] and not x['fatalHookFired'] for x in keys)
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'passed-fresh-actual-host-row-bytecode-review','families':sorted(families),'states':sorted(states),'rows':96,'direct_actual_adapter_descriptor_BCI_to_invokeinterface_bindings':bindings,'genuine_text_mutator_families':sorted(textfamilies),'genuine_done_submit':True,'separate_labeled_nontext_injections':8,'sendKey_refusal_states':6,'changing_true_guard':'executed unchanged suite separate invalid-entry assertions; no guard clearing in positive family loop','explicit_cursor_initial_0_0_and_nonBMP':'executed suite source assertions plus actual AB and cursor snapshots','scope':'mechanical host leaf evidence only; no native method equivalence or complete compiled boundary coverage','native_equivalence_claim':False}
(O/'ime-frame-audit.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print('PASS 96 family states;48 actual direct adapter descriptor/BCI invokeinterface matches;7 real text mutators+Done;8 labeled injections;6 clean sendKey refusals')
