#!/usr/bin/env python3
"""Execute extracted production dispatch + unmodified official wrapper with finite host leaves.

This is a dispatch/control probe. Its target is a JVM proxy, not an Android editor.
No result establishes actual native behavior, native delivery, release, or OTA safety.
"""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
O=Path(__file__).resolve().parents[1]
S=O/'probe-source'; C=O/'probe-classes'; S.mkdir(exist_ok=True); C.mkdir(exist_ok=True)
def write(rel,text):
 p=S/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
def block(text,marker):
 start=text.index(marker);a=text.index('{',start);depth=1;i=a+1
 while depth:
  if text[i]=='{':depth+=1
  elif text[i]=='}':depth-=1
  i+=1
 return text[start:i]
v=(O/'inputs/native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java').read_text()
mutation=block(v,'static final class Mutation {')
create=block(v,'@Override public android.view.inputmethod.InputConnection onCreateInputConnection(EditorInfo info)')
menu=block(v,'@Override public boolean onTextContextMenuItem(int id)')
(O/'extracted-source.json').write_text(json.dumps({'scope':'Exact unchanged selected production source blocks; surrounding leaves are authored finite controls',
 'blocks':[{'marker':marker,'bytes':len(b.encode()),'sha256':hashlib.sha256(b.encode()).hexdigest()} for marker,b in [('Mutation',mutation),('onCreateInputConnection',create),('onTextContextMenuItem',menu)]]},indent=2)+'\n')
write('android/view/inputmethod/InputConnectionWrapper.java',(O/'official/aosp36/InputConnectionWrapper.java').read_text())
inventory=json.loads((O/'method-inventory.json').read_text())
declarations=[]
for m in inventory['methods']:
 declaration=m['declaration'].replace('public default ','public abstract ')
 before,params=declaration.split('(',1);params=params.removesuffix(');')
 declarations.append(before+'('+', '.join(t.strip()+' p'+str(i) for i,t in enumerate(params.split(',')) if t.strip())+');')
write('android/view/inputmethod/InputConnection.java','package android.view.inputmethod; public interface InputConnection {int HANDWRITING_GESTURE_RESULT_UNSUPPORTED=2; @interface CursorUpdateMode {} @interface CursorUpdateFilter {}\n'+'\n'.join(declarations)+'\n}')
for annotation in ['CallbackExecutor','IntRange','NonNull','Nullable']:
 write('android/annotation/'+annotation+'.java','package android.annotation; public @interface '+annotation+' {'+('long from() default 0;' if annotation=='IntRange' else '')+'}')
write('com/android/internal/util/Preconditions.java','package com.android.internal.util; public final class Preconditions {public static int checkArgumentNonnegative(int n){if(n<0)throw new IllegalArgumentException();return n;}}')
write('dev/mixer/android/NativeAppearanceViewsV2.java','''package dev.mixer.android;
import android.view.inputmethod.*;
import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.*;
class OwnerLifecycleV2 {static final class Token {}}
class NativeOwnerV2 {static final class Fence {boolean terminal,drawAllowed=true,inputAllowed=true;OwnerLifecycleV2.Token operation,presentation=new OwnerLifecycleV2.Token();}}
class NativeEnvironmentV2 {static boolean main=true;static void requireMain(){if(!main)throw new IllegalStateException("finite off-main");}}
public class NativeAppearanceViewsV2 {
'''+mutation+'''
static final class Input {boolean admitted=true; int entries; boolean open(Record r){NativeEnvironmentV2.requireMain();entries++;return admitted&&!r.fence.terminal&&r.fence.inputAllowed;}}
static final class Record {final Input input=new Input();final NativeOwnerV2.Fence fence=new NativeOwnerV2.Fence();Mutation mutation(){NativeEnvironmentV2.requireMain();return Mutation.live(fence);}}
static class BaseField {InputConnection next; int widgetCalls;public InputConnection onCreateInputConnection(EditorInfo info){return next;} public boolean onTextContextMenuItem(int id){widgetCalls++;return true;} android.content.Context getContext(){return null;}}
static final class NativeField extends BaseField {final Record record=new Record(); boolean focused=true;boolean hasFocus(){return focused;} boolean proposal(CharSequence value,boolean composing){return record.input.open(record)&&hasFocus();}static boolean plainProposal(CharSequence value,boolean composing){return true;}static boolean validBuffer(String value){return true;}
'''+create+'\n'+menu+'''
}
static int checks;static void check(boolean b,String s){checks++;if(!b)throw new AssertionError(s);}
static final class Target implements InvocationHandler {int calls,closes,begins,ends;boolean closed;String mode="";final NativeField field;final String id;Target(NativeField f,String id){field=f;this.id=id;}InputConnection proxy(){return (InputConnection)Proxy.newProxyInstance(InputConnection.class.getClassLoader(),new Class<?>[]{InputConnection.class},this);}
public Object invoke(Object p,Method m,Object[] a){calls++;String n=m.getName();if(n.equals("closeConnection")){closes++;closed=true;return null;}if(n.equals("performContextMenuAction")){begins++;field.onTextContextMenuItem((int)a[0]);ends++;return true;}if(mode.equals("lose")&&n.equals("getTextBeforeCursor"))field.record.input.admitted=false;
if(n.equals("requestTextBoundsInfo")){((Executor)a[1]).execute(()->((Consumer<Object>)a[2]).accept(null));return null;}
if(n.equals("getTextBeforeCursor")||n.equals("getTextAfterCursor")||n.equals("getSelectedText"))return id;
if(m.getReturnType()==boolean.class)return true;if(m.getReturnType()==int.class)return 9;return null;}}
static Object[] args(Method m,Atomic callback){Class<?>[] t=m.getParameterTypes();Object[] a=new Object[t.length];for(int i=0;i<t.length;i++){if(t[i]==int.class)a[i]=0;else if(t[i]==boolean.class)a[i]=false;else if(t[i]==Executor.class)a[i]=(Executor)Runnable::run;else if(t[i]==Consumer.class)a[i]=(Consumer<Object>)(x->callback.count++);}return a;}
static final class Atomic {int count;}
public static void main(String[] argv)throws Exception {
NativeField f=new NativeField();Target first=new Target(f,"first");f.next=first.proxy();InputConnection c=f.onCreateInputConnection(null);
Set<String> inherited=Set.of("getCursorCapsMode","getExtractedText","getHandler","getSelectedText","getSurroundingText","getTextAfterCursor","getTextBeforeCursor","performContextMenuAction","performSpellCheck","reportFullscreenMode","requestCursorUpdates","requestTextBoundsInfo","takeSnapshot");
int inheritedCount=0;Atomic callback=new Atomic();
f.record.input.admitted=false;
for(Method m:InputConnection.class.getMethods())if(inherited.contains(m.getName())){
 if(m.getName().equals("performContextMenuAction"))continue;
 NativeEnvironmentV2.main=false;int before=first.calls;m.invoke(c,args(m,callback));check(first.calls==before+1,"inherited blocked unexpectedly "+m);inheritedCount++;
}
check(inheritedCount==13,"descriptor overload coverage");check(callback.count==1,"inherited bounds callback did not run off-main/stale");
int before=first.calls;boolean rejected=false;try{c.beginBatchEdit();}catch(IllegalStateException expected){rejected=true;}check(rejected&&first.calls==before,"explicit route missing main check");
NativeEnvironmentV2.main=true;before=f.widgetCalls;check(c.performContextMenuAction(1),"official menu delegate result");check(first.begins==1&&first.ends==1&&f.widgetCalls==before,"widget barrier bypass or missed preceding/following batch");
f.record.input.admitted=true;first.mode="lose";check(c.getTextBeforeCursor(1,0).equals("first")&&!f.record.input.admitted,"inherited read return did not escape after reentry");first.mode="";
f.record.input.admitted=true;f.focused=false;before=first.calls;check(!c.commitText("x",1)&&first.calls==before,"focus-lost explicit commit forwarded");f.focused=true;check(c.commitText("x",1)&&first.calls==before+1,"recovered focus dispatch absent");
c.closeConnection();check(first.closes==1,"close missing");before=first.calls;check(c.commitText("x",1)&&first.calls==before+1,"proxy revoked after close; expected present defect");
Target second=new Target(f,"second");f.next=second.proxy();InputConnection newer=f.onCreateInputConnection(null);before=first.calls;check(c.commitText("x",1)&&first.calls==before+1&&second.calls==0,"old proxy did not retain original native target after new creation");
boolean immutable=false;try{((InputConnectionWrapper)c).setTarget(second.proxy());}catch(SecurityException expected){immutable=true;}check(immutable,"official setTarget mutability changed");
check(newer.commitText("x",1)&&second.calls==1,"new connection broken");
System.out.println("PASS extracted current dispatch controls checks="+checks+"; inherited descriptors=14 including menu; actual Android behavior unrun");
}}
''')
sdk='/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar'
commands=[]
for cmd in [
 ['/opt/homebrew/opt/openjdk/bin/javac','-version'],
 ['/opt/homebrew/opt/openjdk/bin/java','-version'],
 ['/opt/homebrew/opt/openjdk/bin/javac','-cp',sdk,'-d',str(C),*[str(p) for p in sorted(S.rglob('*.java'))]],
 ['/opt/homebrew/opt/openjdk/bin/java','-cp',str(C)+':'+sdk,'dev.mixer.android.NativeAppearanceViewsV2']]:
 r=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE); n=len(commands)+1
 (O/f'logs/probe-{n}.stdout.txt').write_text(r.stdout);(O/f'logs/probe-{n}.stderr.txt').write_text(r.stderr)
 commands.append({'argv':cmd,'exit':r.returncode,'stdout':f'logs/probe-{n}.stdout.txt','stderr':f'logs/probe-{n}.stderr.txt'})
 if r.returncode:break
(O/'probe-receipt.json').write_text(json.dumps({'python':sys.version,'commands':commands,'scope':'Unmodified extracted production dispatch blocks and unmodified official API36 wrapper with finite authored JVM target/control leaves; not full product or Android runtime','native_runtime':'pending paused'},indent=2)+'\n')
print(json.dumps(commands,indent=2));sys.exit(r.returncode)
