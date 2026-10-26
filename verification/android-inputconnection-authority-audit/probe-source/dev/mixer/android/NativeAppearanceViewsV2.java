package dev.mixer.android;
import android.view.inputmethod.*;
import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.*;
class OwnerLifecycleV2 {static final class Token {}}
class NativeOwnerV2 {static final class Fence {boolean terminal,drawAllowed=true,inputAllowed=true;OwnerLifecycleV2.Token operation,presentation=new OwnerLifecycleV2.Token();}}
class NativeEnvironmentV2 {static boolean main=true;static void requireMain(){if(!main)throw new IllegalStateException("finite off-main");}}
public class NativeAppearanceViewsV2 {
static final class Mutation {
        enum Mode { TRANSACTION, LIVE_PRESENTATION, CLEANUP }
        final Mode mode;
        final NativeOwnerV2.Fence fence;
        final OwnerLifecycleV2.Token token;
        private Mutation(Mode mode, NativeOwnerV2.Fence fence, OwnerLifecycleV2.Token token) {
            this.mode=mode; this.fence=fence; this.token=token;
        }
        static Mutation transaction(NativeOwnerV2.Fence fence, OwnerLifecycleV2.Token token) {
            Mutation result=new Mutation(Mode.TRANSACTION,fence,token); result.require(); return result;
        }
        static Mutation live(NativeOwnerV2.Fence fence) {
            Mutation result=new Mutation(Mode.LIVE_PRESENTATION,fence,fence.presentation); result.require(); return result;
        }
        static Mutation cleanup(NativeOwnerV2.Fence fence) { return new Mutation(Mode.CLEANUP,fence,null); }
        boolean current() {
            return mode==Mode.CLEANUP ? !fence.drawAllowed&&!fence.inputAllowed :
                !fence.terminal&&token!=null&&(mode==Mode.TRANSACTION ? token==fence.operation : token==fence.presentation&&fence.drawAllowed);
        }
        void require() {
            if(mode==Mode.CLEANUP) {
                if(fence.drawAllowed||fence.inputAllowed)throw new IllegalStateException("cleanup requires sealed authority");
            } else if(fence.terminal||token==null||(mode==Mode.TRANSACTION ? token!=fence.operation :
                token!=fence.presentation||!fence.drawAllowed))throw new IllegalStateException("V2 mutation authority lost");
        }
        void requireMutation() {
            if(mode==Mode.CLEANUP)throw new IllegalStateException("cleanup cannot authorize V2 bind/layout");
            require();
        }
        boolean result(boolean result) {
            // Observe the original captured scope after the delegate. A completed result is not a new mutation.
            if(mode!=Mode.LIVE_PRESENTATION){require();return result;}
            boolean same=!fence.terminal&&token!=null&&token==fence.presentation&&fence.drawAllowed;
            if(same)return result;
            // A synchronous accepted feature event can publish a successor before the delegate returns.
            // No native call, event, mutation, or replacement scope is acquired on this return path.
            return token!=null&&!fence.terminal&&fence.drawAllowed&&fence.presentation!=null&&token!=fence.presentation&&result;
        }
        <T> T result(T result) { require(); return result; }
    }
static final class Input {boolean admitted=true; int entries; boolean open(Record r){NativeEnvironmentV2.requireMain();entries++;return admitted&&!r.fence.terminal&&r.fence.inputAllowed;}}
static final class Record {final Input input=new Input();final NativeOwnerV2.Fence fence=new NativeOwnerV2.Fence();Mutation mutation(){NativeEnvironmentV2.requireMain();return Mutation.live(fence);}}
static class BaseField {InputConnection next; int widgetCalls;public InputConnection onCreateInputConnection(EditorInfo info){return next;} public boolean onTextContextMenuItem(int id){widgetCalls++;return true;} android.content.Context getContext(){return null;}}
static final class NativeField extends BaseField {final Record record=new Record(); boolean focused=true;boolean hasFocus(){return focused;} boolean proposal(CharSequence value,boolean composing){return record.input.open(record)&&hasFocus();}static boolean plainProposal(CharSequence value,boolean composing){return true;}static boolean validBuffer(String value){return true;}
@Override public android.view.inputmethod.InputConnection onCreateInputConnection(EditorInfo info){NativeEnvironmentV2.requireMain();
            if(record==null||!record.input.open(record))return null;Mutation mutation=record.mutation();mutation.require();
            android.view.inputmethod.InputConnection nativeConnection=super.onCreateInputConnection(info);mutation.require();if(nativeConnection==null)return null;
            return new android.view.inputmethod.InputConnectionWrapper(nativeConnection,false){
                private boolean open(){return record.input.open(record)&&hasFocus();}
                @Override public boolean beginBatchEdit(){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return mutation.result(super.beginBatchEdit());}
                @Override public boolean endBatchEdit(){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return mutation.result(super.endBatchEdit());}
                @Override public boolean clearMetaKeyStates(int states){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return mutation.result(super.clearMetaKeyStates(states));}
                @Override public void closeConnection(){NativeEnvironmentV2.requireMain();if(!open())return;Mutation mutation=record.mutation();mutation.require();super.closeConnection();mutation.require();}
                @Override public boolean commitText(CharSequence text,int position){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return proposal(text,false)&&mutation.result(super.commitText(text,position));}
                @Override public boolean setComposingText(CharSequence text,int position){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return proposal(text,true)&&mutation.result(super.setComposingText(text,position));}
                @Override public boolean commitText(CharSequence text,int position,android.view.inputmethod.TextAttribute attributes){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return proposal(text,false)&&mutation.result(super.commitText(text,position,attributes));}
                @Override public boolean setComposingText(CharSequence text,int position,android.view.inputmethod.TextAttribute attributes){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return proposal(text,true)&&mutation.result(super.setComposingText(text,position,attributes));}
                @Override public boolean setComposingRegion(int start,int end){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return open()&&mutation.result(super.setComposingRegion(start,end));}
                @Override public boolean setComposingRegion(int start,int end,android.view.inputmethod.TextAttribute attributes){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return open()&&mutation.result(super.setComposingRegion(start,end,attributes));}
                @Override public boolean finishComposingText(){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return open()&&mutation.result(super.finishComposingText());}
                @Override public boolean deleteSurroundingText(int before,int after){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return open()&&mutation.result(super.deleteSurroundingText(before,after));}
                @Override public boolean deleteSurroundingTextInCodePoints(int before,int after){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return open()&&mutation.result(super.deleteSurroundingTextInCodePoints(before,after));}
                @Override public boolean setSelection(int start,int end){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return open()&&mutation.result(super.setSelection(start,end));}
                @Override public boolean performEditorAction(int action){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return open()&&mutation.result(super.performEditorAction(action));}
                @Override public boolean sendKeyEvent(android.view.KeyEvent event){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();int value=event.getUnicodeChar();
                    return open()&&(event.getAction()!=android.view.KeyEvent.ACTION_DOWN||value==0||Character.isValidCodePoint(value)&&proposal(new String(Character.toChars(value)),false))&&mutation.result(super.sendKeyEvent(event));}
                @Override public boolean replaceText(int start,int end,CharSequence text,int position,android.view.inputmethod.TextAttribute attributes){NativeEnvironmentV2.requireMain();return false;}
                @Override public boolean performPrivateCommand(String action,android.os.Bundle data){NativeEnvironmentV2.requireMain();return false;}
                @Override public boolean setImeConsumesInput(boolean consumes){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return open()&&mutation.result(super.setImeConsumesInput(consumes));}
                @Override public void performHandwritingGesture(android.view.inputmethod.HandwritingGesture gesture,java.util.concurrent.Executor executor,java.util.function.IntConsumer result){NativeEnvironmentV2.requireMain();if(executor!=null&&result!=null)executor.execute(()->result.accept(android.view.inputmethod.InputConnection.HANDWRITING_GESTURE_RESULT_UNSUPPORTED));}
                @Override public boolean previewHandwritingGesture(android.view.inputmethod.PreviewableHandwritingGesture gesture,android.os.CancellationSignal cancellation){NativeEnvironmentV2.requireMain();return false;}
                @Override public boolean commitCompletion(android.view.inputmethod.CompletionInfo value){NativeEnvironmentV2.requireMain();if(!open())return false;Mutation mutation=record.mutation();mutation.require();return value!=null&&proposal(value.getText(),false)&&mutation.result(super.commitCompletion(value));}
                @Override public boolean commitCorrection(android.view.inputmethod.CorrectionInfo value){NativeEnvironmentV2.requireMain();return false;}
                @Override public boolean commitContent(android.view.inputmethod.InputContentInfo content,int flags,android.os.Bundle options){NativeEnvironmentV2.requireMain();return false;}
            };
        }
@Override public boolean onTextContextMenuItem(int id){NativeEnvironmentV2.requireMain();
            if(record==null||!record.input.open(record))return false;
            if(id==android.R.id.paste||id==android.R.id.pasteAsPlainText){
                android.content.ClipboardManager clipboard=getContext().getSystemService(android.content.ClipboardManager.class);
                android.content.ClipData clip=clipboard==null?null:clipboard.getPrimaryClip();if(clip==null)return false;
                StringBuilder proposed=new StringBuilder();for(int i=0;i<clip.getItemCount();i++){if(i>0)proposed.append('\n');CharSequence item=clip.getItemAt(i).coerceToText(getContext());if(!plainProposal(item,false))return false;proposed.append(item);}
                if(!proposal(proposed,false))return false;
            }
            Mutation mutation=record.mutation();mutation.require();return mutation.result(super.onTextContextMenuItem(id));
        }
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
