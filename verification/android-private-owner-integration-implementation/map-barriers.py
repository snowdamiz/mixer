#!/usr/bin/env python3
"""Supplemental exact invocation mapping; execution must independently hit every mapped site."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
ROSTER=ROOT/'verification/android-private-owner-effect-roster-amendment/required-host-roster.json'
def endcall(t,op):
 d=1;i=op+1;q=None
 while d:
  c=t[i]
  if q:
   if c=='\\':i+=2;continue
   if c==q:q=None
  elif c in '\"\'':q=c
  elif c=='(':d+=1
  elif c==')':d-=1
  i+=1
 return i
def class_at(t,at):
 # Class custody only, not an authorization/parser proof.
 tokens=re.finditer(r'\b(?:class|interface|record|enum)\s+(\w+)|[{}]|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/',t)
 stack=[];pending=None
 for m in tokens:
  if m.start()>=at:break
  if m.group(1):pending=m.group(1)
  elif m.group()=='{':stack.append(pending);pending=None
  elif m.group()=='}':
   if stack:stack.pop()
 return '$'.join(x for x in stack if x)
j=json.loads(ROSTER.read_text());result=[]
for r in j['baseline_callback_barriers']:
 old=subprocess.check_output(['git','show','HEAD:'+r['source']],cwd=ROOT,text=True)
 oldlines=old.splitlines(keepends=True);line=oldlines[r['line']-1];start=sum(map(len,oldlines[:r['line']-1]))+r['column']-1
 assert old.startswith(r['expression'],start),(r['id'],line)
 stop=endcall(old,start+len(r['expression'])-1);invocation=old[start:stop];owner=class_at(old,start)
 current=(ROOT/r['source']).read_text();pat=r'\s*'.join(re.escape(x) for x in re.split(r'\s+',invocation.strip()))
 matches=[m for m in re.finditer(pat,current) if class_at(current,m.start())==owner]
 original_matches=[m for m in re.finditer(pat,old) if class_at(old,m.start())==owner]
 ordinal=next((i for i,m in enumerate(original_matches) if m.start()==start),None)
 mapping='exact-invocation-and-class-ordinal'
 if ordinal is not None and len(matches)==len(original_matches):matches=[matches[ordinal]]
 if not matches and 'setOnCheckedChangeListener(' in r['expression']:
  matches=[m for m in re.finditer(re.escape(r['expression']),current) if class_at(current,m.start())==owner]
  mapping='same-listener-registration-entry-with-guarded-callback-body'
 if not matches and r['id'] in ('NativeRenderer:L225:C51:1','NativeRenderer:L238:C9:1','NativeAppearanceViewsV2:L468:C40:1','NativeAppearanceViewsV2:L518:C17:1'):
  explicit=invocation[:-1]+',mutation)'
  pattern=r'\s*'.join(re.escape(x) for x in re.split(r'\s+',explicit.strip()))
  matches=[m for m in re.finditer(pattern,current) if class_at(current,m.start())==owner]
  mapping='same-helper-invocation-with-explicit-original-Mutation-argument'
 # All active renderer sites are after the unchanged V1 section.
 if r['source'].endswith('/NativeRenderer.java'):matches=[m for m in matches if m.start()>current.index('// Ordinary private V2 lane.')]

 # Explicitly report ambiguity. Runtime matching also includes the native method to separate nested forwarding.
 candidates=[{'line':current.count('\n',0,m.start())+1,'column':m.start()-current.rfind('\n',0,m.start()),'text':m.group()} for m in matches]
 result.append({'baseline':r['id'],'source':r['source'],'class':owner,'invocation':invocation,'candidates':candidates,'required_cases':r['required_cases'],'mapping':mapping})
# Multi-call product helpers use distinct first/final lower native anchors. The final
# anchor is equivalent only for the named independently authored fixture branch.
helper={
 'NativeRenderer:L225:C51:1':('View.<init>','View.setOnFocusChangeListener','root','Group',None,'controls root vStack Record: final listener setter, then Java kind tests and scoped=null only'),
 'NativeRenderer:L238:C9:1':('*','View.measure','toggle','NativeSwitch','NativeAppearanceViewsV2:L275:C13:1','controls measure root: final toggle exact-size measure, then checked scalar aggregation only'),
 'NativeRenderer:L240:C56:1':('View.<init>','View.setWillNotDraw',None,'Gate',None,'Gate constructor final native setter then Java constructor return'),
 'NativeAppearanceViewsV2:L468:C40:1':('View.measure','View.layout','section','Group',None,'first controls section child is a Group: outer view.layout returns after all child layouts; remaining branch is non-ScrollView then return'),
 'NativeAppearanceViewsV2:L518:C17:1':('View.measure','View.layout','list','Group','NativeAppearanceViewsV2:L457:C43:1','navigation Group.onLayout: final list content Group.layout returns after all rows; direct scope checks and loop end only before helper return'),
}
constructors={
 'TextView':('TextView.<init>','Android TextView constructor final leaf return then caller direct scope check'),
 'NativeButton':('TextView.setGravity','NativeButton final native gravity setter then direct scope check and return'),
 'NativeField':('EditText.<init>','NativeField after native EditText constructor assigns Record only'),
 'NativeSwitch':('Switch.<init>','NativeSwitch after native Switch constructor allocates pure policy state and assigns Record; no native mutation'),
 'Group':('ViewGroup.setClipToPadding','Group final clip-to-padding setter then direct scope check and return'),
 'NativeScroll':('ScrollView.setVerticalScrollBarEnabled','NativeScroll final scrollbar setter then direct scope check and return'),
}
byid={r['baseline']:r for r in result}
for record in result:
 prefix=record['invocation'].split('(',1)[0];method=prefix.rsplit('.',1)[-1]
 boundary={'entry_native_suffix':method,'return_native_suffix':method,'mode':'direct-platform-call','return_receiver_id':None,'return_receiver_class':None,'return_frame_line':None,'equivalence':'selected direct native method returns; caller immediately checks its original scope'}
 if prefix.startswith('new '):
  name=prefix.split('.')[-1].removeprefix('new ')
  if name in constructors:
   returned,proof=constructors[name];boundary.update(entry_native_suffix='View.<init>',return_native_suffix=returned,mode='product-constructor-final-native-anchor',equivalence=proof)
 if record['baseline'] in helper:
  entry,returned,receiver,receiver_class,frameid,proof=helper[record['baseline']]
  boundary.update(entry_native_suffix=entry,return_native_suffix=returned,return_receiver_id=receiver,return_receiver_class=receiver_class,return_frame_line=None if frameid is None else byid[frameid]['candidates'][0]['line'],mode='product-helper-final-native-anchor',equivalence=proof)
 # Exact declared platform targets avoid confusing nested superclass implementations.
 if prefix.startswith('super.'):
  if record['class'].endswith('$NativeField'):
   targets={'onCreateInputConnection':'EditText','drawableStateChanged':'View','onSelectionChanged':'TextView','performAccessibilityAction':'TextView','onKeyDown':'TextView','onTextContextMenuItem':'TextView'}
   target=targets.get(method,'InputConnectionWrapper');boundary.update(entry_native_suffix=target+'.'+method,return_native_suffix=target+'.'+method)
  elif method=='performClick':boundary.update(entry_native_suffix='Switch.performClick',return_native_suffix='Switch.performClick')
  elif method in ('dispatchDraw','drawChild','dispatchTouchEvent','dispatchKeyEvent') and record['class'].endswith(('$Group','$Gate')):
   boundary.update(entry_native_suffix='ViewGroup.'+method,return_native_suffix='ViewGroup.'+method)
 if record['class'].endswith('$Gate') and method in ('dispatchDraw','dispatchTouchEvent','dispatchKeyEvent'):boundary['return_receiver_class']='Gate'
 if record['baseline']=='NativeAppearanceViewsV2:L483:C34:1':boundary['return_receiver_id']='root'
 if record['baseline']=='NativeAppearanceViewsV2:L487:C28:1':boundary['return_receiver_id']='group'
 if record['baseline']=='NativeAppearanceViewsV2:L491:C13:1':boundary['return_receiver_id']='root'
 if record['baseline'] in ('NativeAppearanceViewsV2:L455:C9:1','NativeAppearanceViewsV2:L456:C9:1'):boundary['return_receiver_id']='root'
 record['boundary']=boundary
# Added forwarding native boundaries in the retained connection wrapper. Existing leaf 3
# closeConnection reaches the BaseInputConnection hook; the wrapper tail is direct return.
source='native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java'
current=(ROOT/source).read_text()
for method,target in [('beginBatchEdit','InputConnectionWrapper'),('endBatchEdit','InputConnectionWrapper'),('clearMetaKeyStates','InputConnectionWrapper'),('closeConnection','BaseInputConnection')]:
 expression='super.'+method+'(';start=current.index(expression);stop=endcall(current,start+len(expression)-1)
 result.append({'baseline':'introduced:NativeAppearanceViewsV2:NativeField.InputConnection.'+method,'source':source,'class':'NativeAppearanceViewsV2$NativeField','invocation':current[start:stop],'candidates':[{'line':current.count('\n',0,start)+1,'column':start-current.rfind('\n',0,start),'text':current[start:stop]}],'required_cases':['clean','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback'],'mapping':'new-forwarding-override','boundary':{'entry_native_suffix':target+'.'+method,'return_native_suffix':target+'.'+method,'return_receiver_id':None,'return_receiver_class':None,'return_frame_line':None,'mode':'direct-platform-delegate' if target=='InputConnectionWrapper' else 'product-helper-final-native-anchor','equivalence':'native delegate hook returns through InputConnectionWrapper direct return with no later work, then original product scope postcheck'}})
expression='onLayout(changed,l,t,right,bottom,mutation)';start=current.index(expression)
result.append({'baseline':'introduced:NativeAppearanceViewsV2:Group.onLayout.scopedForward','source':source,'class':'NativeAppearanceViewsV2$Group','invocation':expression,'candidates':[{'line':current.count('\n',0,start)+1,'column':start-current.rfind('\n',0,start),'text':expression}],'required_cases':['clean','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback'],'mapping':'new-framework-entry-to-explicit-scope-helper','boundary':{'entry_native_suffix':'View.measure','return_native_suffix':'View.layout','return_receiver_id':'section','return_receiver_class':'Group','return_frame_line':None,'mode':'product-helper-final-native-anchor','equivalence':'controls root vStack framework onLayout passes its one captured Mutation; final section Group View.layout returns after every child; original scope require, loop completion, helper return and direct wrapper return only'}})
out=ROOT/'verification/android-private-owner-integration-implementation/barrier-map.json'
out.write_text(json.dumps({'schema':1,'scope':'source mapping only, behavioral cases required separately','records':result},indent=2)+'\n')
missing=[r['baseline'] for r in result if not r['candidates']];ambiguous=[r['baseline'] for r in result if len(r['candidates'])>1]
print(json.dumps({'mapped':len(result)-len(missing),'missing':missing,'ambiguous':ambiguous},indent=2))
