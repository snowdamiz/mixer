from pathlib import Path
import json,re,hashlib,shutil,difflib
D=Path(__file__).resolve().parent;Q=D.parent;R=Q.parents[1];source=Q/'inputs/accepted/host-leaves';out=D/'leaves';out.mkdir(exist_ok=False);roster=['android/view/View.java','android/view/ViewGroup.java','android/widget/TextView.java','android/widget/EditText.java','android/widget/Switch.java','android/view/inputmethod/BaseInputConnection.java'];classes=Q/'state-qualification/context17-1/classes';import sys;sys.path.insert(0,str(Q));from classfile import parse
# A small lexical scanner preserves all original token text and wraps only outer return expressions.
def tokens(s):
 result=[];i=0
 while i<len(s):
  if s[i].isspace():i+=1;continue
  if s.startswith('//',i):j=s.find('\n',i);i=len(s) if j<0 else j;continue
  if s.startswith('/*',i):j=s.find('*/',i+2);assert j>=0;i=j+2;continue
  start=i
  if s[i] in ('"',"'"):
   quote=s[i];i+=1
   while i<len(s):
    if s[i]=='\\':i+=2
    elif s[i]==quote:i+=1;break
    else:i+=1
  elif s[i].isalnum() or s[i] in '_$':
   i+=1
   while i<len(s) and (s[i].isalnum() or s[i] in '_$'):i+=1
  else:i+=1
  result.append((s[start:i],start,i))
 return result
def pair(t,at,left,right):
 assert t[at][0]==left;depth=0
 for j in range(at,len(t)):
  if t[j][0]==left:depth+=1
  if t[j][0]==right:
   depth-=1
   if depth==0:return j
 raise AssertionError('unbalanced '+left)
def params(descriptor):
 p=descriptor[1:descriptor.index(')')];n=0;i=0
 while i<len(p):
  while p[i]=='[':i+=1
  if p[i]=='L':i=p.index(';',i)+1
  else:i+=1
  n+=1
 return n
changes=[]
for rel in roster:
 original=(source/rel).read_text();t=tokens(original);classdata=parse((classes/rel.replace('.java','.class')).read_bytes());methods=[m for m in classdata['methods'] if not m['descriptor'].endswith('V') and m['name'] not in ('<init>','<clinit>') and not m['access']&0x000a];edits=[];methodrows=[];used=set()
 for i,token in enumerate(t):
  if token[0]!='(' or i==0:continue
  name=t[i-1][0];matches=[m for m in methods if m['name']==name]
  if not matches:continue
  close=pair(t,i,'(',')')
  if close+1>=len(t) or t[close+1][0]!='{':continue
  end=pair(t,close+1,'{','}');args=t[i+1:close];arity=0 if not args else 1+sum(x[0]==',' for x in args);matches=[m for m in matches if params(m['descriptor'])==arity];assert len(matches)==1,(rel,name,arity);method=matches[0];body=original[t[close+1][1]:t[end][2]];owns_hook=('done("'+classdata['class'].split('/')[-1]+'.'+name+'")' in body or 'done("'+name+'"' in body or '"beforeReturn"' in body and '"'+classdata['class'].split('/')[-1]+'.'+name+'"' in body)
  nested_region=(rel.endswith('BaseInputConnection.java') and name=='setComposingRegion' and arity==3)
  if not owns_hook and not nested_region:continue
  signature=name+method['descriptor'];assert signature not in used,(rel,signature);used.add(signature);returns=[]
  for k in range(close+2,end):
   if t[k][0]!='return':continue
   j=k+1;paren=bracket=brace=0
   while j<end:
    v=t[j][0]
    if v==';' and paren==bracket==brace==0:break
    if v=='(':paren+=1
    elif v==')':paren-=1
    elif v=='[':bracket+=1
    elif v==']':bracket-=1
    elif v=='{':brace+=1
    elif v=='}':brace-=1
    j+=1
   assert j<end and j>k+1
   start=t[k+1][1];finish=t[j][1];expression=original[start:finish];prefix='dev.mixer.android.NativeOutcomeProbe.returned("'+classdata['class'].split('/')[-1]+'.'+name+'","'+method['descriptor']+'",this,';edits.append((start,finish,prefix+expression+')'));returns.append({'original_expression':expression,'start_offset':start,'end_offset':finish})
  assert returns,(rel,signature);methodrows.append({'method':name,'descriptor':method['descriptor'],'return_sites':returns,'placement':'after existing own beforeReturn hook' if owns_hook else 'after nested two-argument region call completes; explicit three-argument method outcome, not extra hook credit'})
 amended=original
 for start,finish,replacement in sorted(edits,reverse=True):amended=amended[:start]+replacement+amended[finish:]
 p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(amended);d=D/'diffs'/Path(rel+'.diff');d.parent.mkdir(parents=True,exist_ok=True);d.write_text(''.join(difflib.unified_diff(original.splitlines(True),amended.splitlines(True),fromfile='frozen/'+rel,tofile='derivative/'+rel)));changes.append({'path':rel,'methods':methodrows})
probe=Q/'inputs/instrumentation/ConcreteHostProbe.java';original=probe.read_text();amended=original.replace('public static java.util.function.Consumer<Event> auditSink;','public static java.util.function.Consumer<Event> auditSink;\n    private static java.util.function.Consumer<Event> qualificationHook;\n    public static void installQualificationHook(java.util.function.Consumer<Event> value){if(value==null||qualificationHook!=null)throw new IllegalStateException("qualification hook lifetime");qualificationHook=value;}\n    public static void clearQualificationHook(java.util.function.Consumer<Event> value){if(value==null||qualificationHook!=value)throw new IllegalStateException("qualification hook identity");qualificationHook=null;}\n    public static boolean qualificationHookInstalled(){return qualificationHook!=null;}\n    static List<Site> outcomeFrames(){return WALKER.walk(frames->frames.filter(frame->production(frame.getClassName())).limit(24).map(frame->new Site(frame.getClassName(),frame.getMethodName(),frame.getDescriptor(),frame.getByteCodeIndex(),frame.getLineNumber())).toList());}')
old='BiConsumer<String,String> callback=hook;if(callback!=null)callback.accept(method,phase);';new='BiConsumer<String,String> callback=hook;try{if(callback!=null)callback.accept(method,phase);java.util.function.Consumer<Event> qualification=qualificationHook;if(qualification!=null)qualification.accept(event);}catch(RuntimeException|Error failure){NativeOutcomeProbe.hookException(event,failure);throw failure;}';assert amended.count(old)==1;amended=amended.replace(old,new);p=out/'dev/mixer/android/ConcreteHostProbe.java';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(amended);(D/'ConcreteHostProbe.java.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),amended.splitlines(True),fromfile='frozen/direct-allowlist-probe.java',tofile='derivative/ConcreteHostProbe.java')))
(D/'selected-return-sites.json').write_text(json.dumps({'Android_leaves':changes,'product_sources_changed':False,'original_method_returns_evaluated_once':True,'original_hit_and_hook_positions_preserved':True,'new_qualification_hook':'after original event/count/ordinary hook; explicit install/clear; reset existing semantics preserved','exception_scope':'original ordinary/qualification-hook RuntimeException/Error identity captured centrally then same object rethrown; other unobserved native/helper body outcomes remain pending'},indent=2)+'\n');shutil.copy2(R/'verification/android-editor-boundary-root-review/integration-passive-return-probe-preparation.md',D/'root-preparation-authority.md');print('Android leaves',len(changes),'methods',sum(len(x['methods']) for x in changes),'return expressions',sum(len(m['return_sites']) for x in changes for m in x['methods']))
