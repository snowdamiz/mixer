package dev.mixer.android;

import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.FrameLayout;
import android.view.inputmethod.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Runs complete copied Mixer bodies with mechanical Android/JNI leaves. No Android runtime claim. */
public final class EditorImplementationTests {
    private EditorImplementationTests() {}
    private static byte[] descriptor;
    private static int checks,groups;
    private static final class Fatal extends Error {private static final long serialVersionUID=1L;Fatal(String message){super(message);}}
    private static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    private static Object field(Object target,String name){try{Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(target);}catch(ReflectiveOperationException e){throw new AssertionError(e);}}
    private static void set(Object target,String name,Object value){try{Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);f.set(target,value);}catch(ReflectiveOperationException e){throw new AssertionError(e);}}
    private static void call(Object target,String name,Class<?>[] types,Object... args){try{Method m=target.getClass().getDeclaredMethod(name,types);m.setAccessible(true);m.invoke(target,args);}catch(InvocationTargetException e){if(e.getCause() instanceof Error fatal)throw fatal;if(e.getCause() instanceof RuntimeException ordinary)throw ordinary;throw new AssertionError(e.getCause());}catch(ReflectiveOperationException e){throw new AssertionError(e);}}
    private static void write(StringBuilder out,Object value){if(value instanceof List<?> values){out.append('[');for(int i=0;i<values.size();i++){if(i>0)out.append(',');write(out,values.get(i));}out.append(']');}else if(value instanceof Map<?,?> values){out.append('{');boolean comma=false;for(var entry:values.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,entry.getKey());out.append(':');write(out,entry.getValue());}out.append('}');}else Json.write(out,value);}
    private static byte[] packet(long revision,String text){
        Object node=Json.map("id","field","kind","textField","properties",Json.map("label","Entry","value",text),"children",List.of(),"actions",List.of(Json.map("id","changed","event","textChange"),Json.map("id","done","event","submit")));
        StringBuilder out=new StringBuilder();write(out,Json.map("schemaVersion",new Json.Num("1"),"document",Json.map("schemaVersion",new Json.Num("1"),"revision",new Json.Num(Long.toString(revision)),"root",node),"identities",List.of(Json.map("id","field","generation",new Json.Num("1")))));return out.toString().getBytes(StandardCharsets.UTF_8);
    }
    private static final class Fixture implements AutoCloseable {
        final Activity activity=new Activity();final FrameLayout root=new FrameLayout(activity);final NativeOwnerV2 owner;final Handler queue;
        final NativeRenderer renderer;final NativeAppearanceViewsV2.NativeField edit;
        Fixture(){this(packet(1,"hello"));}Fixture(byte[] initial){ConcreteHostProbe.reset();android.widget.TextView.accessibilitySetTextBehavior=0;activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);root.hostAttach(new Object());NativeBridge.reset();NativeBridge.preparedPacket=initial;owner=new NativeOwnerV2(activity,root);queue=(Handler)field(owner,"handler");owner.onResume();owner.start();queue.drainAll(6);check(owner.hasCommittedPresentation(),"fixture presentation: "+owner.cleanupLedger().primary());renderer=(NativeRenderer)field(field(owner,"coordinator"),"renderer");edit=(NativeAppearanceViewsV2.NativeField)renderer.view("field");edit.requestFocus();ConcreteHostProbe.reset();}
        NativeOwnerV2.Fence fence(){return (NativeOwnerV2.Fence)field(owner,"fence");}
        InputConnection connection(){InputConnection value=edit.onCreateInputConnection(new EditorInfo());check(value!=null,"connection created");return value;}
        BaseInputConnection target(){return (BaseInputConnection)edit.lastConnection;}
        @Override public void close(){ConcreteHostProbe.hook=null;try{owner.close();queue.drainAll(8);}catch(RuntimeException|Error expected){/* focused controls assert retained terminal identities before fixture retirement */}ConcreteHostProbe.reset();}
    }
    private static void group(String name,Runnable test){test.run();groups++;System.out.println("PASS "+name);}
    private static void baseline(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();Object editable=f.edit.getText();check(c.getHandler()==null,"handler null");
        check(c.setSelection(1,1),"selection");check(c.setComposingRegion(0,1),"composition");check(c.finishComposingText(),"finish");
        check(c.beginBatchEdit()&&c.endBatchEdit(),"batch");check(c.clearMetaKeyStates(0),"meta");
        check(c.getCursorCapsMode(3)==3,"caps");check(c.getSelectedText(0)!=null,"selected");check(c.getTextBeforeCursor(1,0)!=null,"before");check(c.getTextAfterCursor(1,0)!=null,"after");
        check(c.getExtractedText(new ExtractedTextRequest(),0)!=null,"nonmonitor extraction");check(c.getSurroundingText(1,1,0)!=null,"surrounding");check(c.takeSnapshot()!=null,"snapshot");
        check(c.requestCursorUpdates(0)&&c.requestCursorUpdates(0,0),"cursor disable");check(c.reportFullscreenMode(false),"fullscreen disable");check(c.setImeConsumesInput(false),"consumes");
        check(f.edit.getText()==editable,"Editable identity preserved");check(f.target().closeCalls==0,"healthy not closed");
    }}
    private static void descriptorControls(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();int methods=0;
        for(Method m:InputConnection.class.getMethods()){
            if(m.getDeclaringClass()!=InputConnection.class||Modifier.isStatic(m.getModifiers()))continue;
            methods++;try{Method actual=c.getClass().getMethod(m.getName(),m.getParameterTypes());check(actual.getDeclaringClass()!=InputConnection.class,"default inherited: "+m);}
            catch(NoSuchMethodException e){throw new AssertionError(e);}
            Object[] args=new Object[m.getParameterCount()];Class<?>[] types=m.getParameterTypes();
            for(int i=0;i<types.length;i++){Class<?> t=types[i];args[i]=t==int.class?0:t==boolean.class?false:null;}
            // Every descriptor must refuse off-main before state or native side effects, except constant getHandler.
            int before=ConcreteHostProbe.events().size();Looper.hostSetMain(false);
            try{Object result=m.invoke(c,args);check(m.getName().equals("getHandler")&&result==null,"offmain did not refuse "+m);}
            catch(InvocationTargetException e){check(e.getCause() instanceof IllegalStateException,"offmain failure type "+m);}
            catch(IllegalAccessException e){throw new AssertionError(e);}
            finally{Looper.hostReset();}
            check(ConcreteHostProbe.events().size()==before,"offmain native side effect "+m);
        }
        check(methods==38,"all 38 SDK descriptors accounted, got "+methods);check(!(c instanceof InputConnectionWrapper),"direct adapter");
    }}
    private static void refusalPolicies(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();int nativeCalls=f.target().mutations;
        check(!c.sendKeyEvent(null)&&!c.performEditorAction(5)&&!c.requestCursorUpdates(1)&&!c.requestCursorUpdates(0,1),"unsafe transport refusal");
        check(c.getExtractedText(new ExtractedTextRequest(),1)==null&&!c.performSpellCheck(),"monitor/spell refusal");
        check(!c.commitContent(null,0,null)&&!c.commitCorrection(null)&&!c.performPrivateCommand(null,null)&&!c.replaceText(0,0,"x",1,null)&&!c.previewHandwritingGesture(null,null),"unsupported refusal");
        int[] result={-1};c.performHandwritingGesture(null,Runnable::run,v->result[0]=v);check(result[0]==InputConnection.HANDWRITING_GESTURE_RESULT_UNSUPPORTED,"gesture constant");
        c.requestTextBoundsInfo(null,Runnable::run,v->result[0]=v.getResultCode());check(result[0]==TextBoundsInfoResult.CODE_UNSUPPORTED,"bounds constant");
        check(f.target().mutations==nativeCalls,"refusals have no target call");
    }}
    private static void creatorSerialization(){try(Fixture f=new Fixture()){
        EditorInfo nestedInfo=new EditorInfo();nestedInfo.inputType=99;int before=f.edit.connectionAcquisitions;boolean[] fired={false};
        ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("EditText.onCreateInputConnection")&&phase.equals("entry")){fired[0]=true;check(f.edit.onCreateInputConnection(nestedInfo)==null,"nested creator null");check(nestedInfo.inputType==99,"nested output untouched");}};
        InputConnection c=f.connection();ConcreteHostProbe.hook=null;check(fired[0]&&f.edit.connectionAcquisitions==before+1,"one native creator");
        BaseInputConnection old=f.target();InputConnection next=f.connection();check(old.closeCalls==1,"old target closes once before successor");int calls=f.target().mutations;c.closeConnection();check(f.target().mutations==calls,"stale close local only");check(!c.setSelection(0,0)&&next.setSelection(0,0),"old refused successor usable");
    }}
    private static void lifecycle(){String[] hooks={"focus","windowFocus","windowVisibility","aggregate","visibility","detach"};for(String hook:hooks)try(Fixture f=new Fixture()){
        InputConnection c=f.connection();BaseInputConnection target=f.target();boolean[] seen={false};String nativeHook=switch(hook){case "focus"->"View.onFocusChanged";case "windowFocus"->"View.onWindowFocusChanged";case "windowVisibility"->"View.onWindowVisibilityChanged";case "aggregate"->"View.onVisibilityAggregated";case "visibility"->"View.onVisibilityChanged";default->"View.onDetachedFromWindow";};
        ConcreteHostProbe.hook=(method,phase)->{if(!seen[0]&&method.equals(nativeHook)&&phase.equals("entry")){seen[0]=true;check(f.renderer.editorDisposalBusyV2(),"standalone lifecycle counted before super");check(!c.setSelection(0,0),"retired adapter blocked inside super");check(f.edit.onCreateInputConnection(new EditorInfo())==null,"nested successor blocked");check(target.closeCalls==0,"old close waits for native suffix");}};
        switch(hook){case "focus"->f.edit.clearFocus();case "windowFocus"->f.edit.onWindowFocusChanged(false);case "windowVisibility"->call(f.edit,"onWindowVisibilityChanged",new Class<?>[]{int.class},View.INVISIBLE);case "aggregate"->f.edit.onVisibilityAggregated(false);case "visibility"->call(f.edit,"onVisibilityChanged",new Class<?>[]{View.class,int.class},f.edit,View.INVISIBLE);default->call(f.edit,"onDetachedFromWindow",new Class<?>[]{});}
        ConcreteHostProbe.hook=null;check(seen[0]&&target.closeCalls==1&&!f.renderer.editorDisposalBusyV2(),"lifecycle exact close after suffix");
        check(f.edit.onCreateInputConnection(new EditorInfo())==null,"loss latch survives stale native getters");check(!c.setSelection(0,0),"old adapter remains revoked");
    }}
    private static void retireInsideDelegate(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();BaseInputConnection target=f.target();boolean[] fired={false};
        ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("BaseInputConnection.setSelection")&&phase.equals("entry")){fired[0]=true;f.edit.clearFocus();check(target.closeCalls==0,"no recursive close inside unfinished delegate");check(f.renderer.editorDisposalBusyV2(),"delegate remains busy");}};
        check(!c.setSelection(1,1),"revoked delegate result refused");ConcreteHostProbe.hook=null;check(target.closeCalls==1,"outer unwind closes once");
    }}
    private static void plainThrow(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();RuntimeException original=new IllegalStateException("native plain failure");boolean[] fired={false};
        ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("BaseInputConnection.beginBatchEdit")&&phase.equals("entry")){fired[0]=true;throw original;}};
        try{c.beginBatchEdit();throw new AssertionError("plain native throw hidden");}catch(RuntimeException actual){check(actual==original,"ordinary original identity");}
        ConcreteHostProbe.hook=null;check(f.target().closeCalls==1&&f.fence().terminal,"plain throw retires and closes");check(f.edit.onCreateInputConnection(new EditorInfo())==null,"throw quarantined");check(!f.renderer.editorDisposalBusyV2(),"finite failure clears busy");
    }}
    private static void ownerCloseInsideDelegate(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();BaseInputConnection target=f.target();boolean[] fired={false};
        ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("BaseInputConnection.beginBatchEdit")&&phase.equals("entry")){fired[0]=true;f.owner.close();check(NativeBridge.destroyCalls==0,"engine disposal deferred on editor frame");check(target.closeCalls==0,"target not recursively closed");}};
        check(!c.beginBatchEdit(),"owner revoked result");ConcreteHostProbe.hook=null;check(target.closeCalls==1,"target drains after delegate");check(NativeBridge.destroyCalls==0,"no synchronous owner resume after final clear");f.queue.drainAll(8);check(NativeBridge.destroyCalls==1,"accepted async owner cleanup resumes");
    }}
    private static void compatibleEcho(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();Object editable=f.edit.getText();check(c.setSelection(1,1),"echo initial selection");
        NativeBridge.preparedPacket=packet(2,"hXello");check(c.commitText("X",1),"synchronous compatible Binding echo acknowledged");
        check(f.edit.getText()==editable&&f.edit.getText().toString().equals("hXello"),"echo preserves same Editable/value");
        check(f.edit.getSelectionStart()==2&&f.target().closeCalls==0,"echo preserves native selection and target");
        check(c.setComposingRegion(0,1),"preseal composition");int cs=BaseInputConnection.getComposingSpanStart(f.edit.getText());
        f.owner.onPause();check(f.target().closeCalls==0,"temporary seal does not close");check(!c.setSelection(0,0),"temporary sealed input refuses");
        f.owner.onResume();f.queue.drainAll(8);check(f.edit.getText()==editable&&BaseInputConnection.getComposingSpanStart(f.edit.getText())==cs,"temporary seal preserves Editable/composition");
        check(c.setSelection(1,1),"same adapter usable after actual owner resumption");
    }}
    private static void allMutatingDescriptors(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();check(c.setSelection(0,0),"mutator selection");
        NativeBridge.preparedPacket=packet(2,"hello");check(c.commitText("",1),"commit descriptor");
        NativeBridge.preparedPacket=packet(3,"hello");check(c.setComposingText("",1),"compose descriptor");
        NativeBridge.preparedPacket=packet(4,"hello");check(c.commitText("",1,new TextAttribute()),"commit attributes descriptor");
        NativeBridge.preparedPacket=packet(5,"hello");check(c.setComposingText("",1,new TextAttribute()),"compose attributes descriptor");
        check(c.setComposingRegion(0,1,new TextAttribute()),"region attributes descriptor");check(c.finishComposingText(),"finish descriptor");
        NativeBridge.preparedPacket=packet(6,"hello");check(c.deleteSurroundingText(0,0),"delete descriptor");
        NativeBridge.preparedPacket=packet(7,"hello");check(c.deleteSurroundingTextInCodePoints(0,0),"codepoint delete descriptor");
        NativeBridge.preparedPacket=packet(8,"hello");check(c.commitCompletion(new CompletionInfo(1,0,"")),"completion descriptor");
        check(!c.performContextMenuAction(0),"context direct descriptor");
        NativeBridge.preparedPacket=packet(9,"hello");check(c.performEditorAction(EditorInfo.IME_ACTION_DONE),"configured Done descriptor");
    }}
    private static void staleDescriptors(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();c.closeConnection();int before=f.target().mutations;
        for(Method m:InputConnection.class.getMethods()){
            if(m.getDeclaringClass()!=InputConnection.class||Modifier.isStatic(m.getModifiers()))continue;
            Object[] args=new Object[m.getParameterCount()];Class<?>[] types=m.getParameterTypes();
            for(int i=0;i<types.length;i++)args[i]=types[i]==int.class?0:types[i]==boolean.class?false:null;
            try{m.invoke(c,args);}catch(ReflectiveOperationException e){throw new AssertionError("stale descriptor "+m,e);}
        }
        check(f.target().mutations==before,"all stale descriptors have zero native target dispatch");
    }}
    private static void noCallAndQuerySnapshots(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();BaseInputConnection target=f.target();int before=target.mutations;
        check(!c.commitText("\ud800",1)&&!c.setSelection(-1,0)&&!c.deleteSurroundingText(-1,0),"invalid arguments refused");
        check(target.mutations==before&&target.closeCalls==0&&!f.fence().terminal,"no-call refusal does not fabricate cleanup uncertainty");
        boolean[] fired={false};ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("BaseInputConnection.getTextBeforeCursor")&&phase.equals("beforeReturn")){fired[0]=true;f.edit.setSelection(1,1);}};
        check(c.getTextBeforeCursor(1,0)==null,"query changed snapshot discarded");ConcreteHostProbe.hook=null;check(target.closeCalls==0,"changed query snapshot alone is not fabricated close");
        CharSequence hostile=new CharSequence(){public int length(){return 1;}public char charAt(int i){return 'X';}public CharSequence subSequence(int a,int b){return "X";}@Override public String toString(){f.edit.setSelection(2,2);return "X";}};
        before=target.mutations;check(!c.commitText(hostile,1),"reentrant argument changes snapshot");check(target.mutations==before,"snapshot rechecked immediately before delegate");
    }}
    private static void scrubbed(EditorInfo info){
        check(info.inputType==0&&info.imeOptions==0&&info.actionId==0&&info.initialSelStart==-1&&info.initialSelEnd==-1&&info.initialCapsMode==0,"failed public scalar scrub");
        check(info.actionLabel==null&&info.label==null&&info.hintText==null&&info.extras==null&&info.contentMimeTypes==null&&info.hintLocales==null&&info.privateImeOptions==null,"failed public payload scrub");
        check(info.hostSurrounding()==null&&info.gestures.isEmpty()&&info.previews.isEmpty(),"private surrounding and gesture scrub");check("kept.package".equals(info.packageName)&&info.fieldId==42,"framework identities preserved");
    }
    private static EditorInfo output(){EditorInfo info=new EditorInfo();info.packageName="kept.package";info.fieldId=42;info.actionId=123;info.label="label";info.actionLabel="action";info.hintText="hint";info.privateImeOptions="private";info.extras=new android.os.Bundle();info.contentMimeTypes=new String[]{"text/plain"};return info;}
    private static void editorInfoNullAndThrow(){
        try(Fixture f=new Fixture()){EditorInfo info=output();android.widget.EditText.creatorNull=true;try{check(f.edit.onCreateInputConnection(info)==null,"native null result");}finally{android.widget.EditText.creatorNull=false;}scrubbed(info);check(f.target().closeCalls==0,"null return never fabricates a returned target");}
        try(Fixture f=new Fixture()){EditorInfo info=output();RuntimeException original=new IllegalStateException("creator hides allocated target");boolean[] fired={false};ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("EditText.onCreateInputConnection")&&phase.equals("beforeReturn")){fired[0]=true;throw original;}};
            try{f.edit.onCreateInputConnection(info);throw new AssertionError("creator throw hidden");}catch(RuntimeException actual){check(actual==original,"creator failure identity");}ConcreteHostProbe.hook=null;scrubbed(info);check(f.target().closeCalls==0,"inaccessible creator target never fabricated close");check(field(field(f.edit,"attempt"),"close").toString().equals("FAILED_UNCERTAIN"),"creator uncertain disposition");}
    }
    private static void editorInfoLateInvalidation(){try(Fixture f=new Fixture()){
        EditorInfo info=output();boolean[] fired={false};ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("EditText.onCreateInputConnection")&&phase.equals("beforeReturn")){fired[0]=true;f.edit.clearFocus();}};
        check(f.edit.onCreateInputConnection(info)==null,"late creator revoked");ConcreteHostProbe.hook=null;scrubbed(info);check(f.target().closeCalls==1,"known late target exact closed");
    }}
    private static void editorInfoSetterReentry(){try(Fixture f=new Fixture()){
        EditorInfo info=output();boolean[] fired={false};ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("EditorInfo.setSupportedHandwritingGestures")&&phase.equals("beforeReturn")){fired[0]=true;check(f.edit.onCreateInputConnection(new EditorInfo())==null,"setter nested creator serialized");f.edit.setSelection(1,1);}};
        check(f.edit.onCreateInputConnection(info)==null,"setter changing snapshot cannot return adapter");ConcreteHostProbe.hook=null;scrubbed(info);check(f.target().closeCalls==1,"setter invalidation closes exact target");
    }}
    private static void finalizationOutputScrub(){try(Fixture f=new Fixture()){
        EditorInfo info=output();boolean[] fired={false},scrubBusy={false};ConcreteHostProbe.hook=(method,phase)->{
            if(!fired[0]&&method.equals("EditorInfo.setSupportedHandwritingGesturePreviews")&&phase.equals("beforeReturn")){fired[0]=true;set(f.renderer,"outstandingEditorNativeCalls",0);}
            if(fired[0]&&method.equals("EditorInfo.setInitialSurroundingText")&&phase.equals("entry")){scrubBusy[0]=true;check(f.renderer.editorDisposalBusyV2(),"post-editorLeave-failure output setter remains disposal busy");check(f.edit.onCreateInputConnection(new EditorInfo())==null,"finishing scrub cannot admit successor");}
        };
        try{f.edit.onCreateInputConnection(info);throw new AssertionError("corrupt final exit returned adapter");}catch(RuntimeException expected){check(expected.getMessage().contains("lease exit"),"final exit surfaced");}ConcreteHostProbe.hook=null;scrubbed(info);check(scrubBusy[0],"post-finalization scrub actually executed");check(f.fence().terminal,"postassignment final failure terminal");check(!f.renderer.editorDisposalBusyV2(),"creator finishing clears last");
    }}
    private static void leaseBoundEveryUse(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();boolean[] fired={false};ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("BaseInputConnection.beginBatchEdit")&&phase.equals("entry")){fired[0]=true;f.owner.close();NativeAppearanceViewsV2.Mutation captured=f.edit.record.mutation();check(captured.editorLease!=null,"cleanup Mutation carries exact captured lease");int count=(Integer)field(f.renderer,"v2RosterCount");set(f.renderer,"v2RosterCount",0);try{captured.require();throw new AssertionError("fence-wide cleanup authorized missing roster");}catch(IllegalStateException expected){check(expected.getMessage().contains("exact editor"),"per-use roster binding");}set(f.renderer,"v2RosterCount",count);captured.require();}};
        check(!c.beginBatchEdit(),"retired result");ConcreteHostProbe.hook=null;check(f.target().closeCalls==1,"valid retained exact cleanup still closes");
    }}
    private static void callbackPostcheck(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();boolean[] fired={false};ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("TextView.onSelectionChanged")&&phase.equals("entry")){fired[0]=true;c.closeConnection();check(f.target().closeCalls==0,"live callback keeps original exact lease through native super");}};
        check(!c.setSelection(1,1),"callback retirement refuses result");ConcreteHostProbe.hook=null;check(f.target().closeCalls==1&&!f.fence().terminal,"exact callback postcheck accepts authorized old suffix");
    }}
    private static void hiddenDetachSuffix(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();boolean[] hidden={false};f.edit.hostPlatformDetach(()->{hidden[0]=true;check(f.edit.isAttachedToWindow(),"host intentionally retains stale attach getter through hidden suffix");check(f.edit.onCreateInputConnection(new EditorInfo())==null,"loss latches deny successor before hidden suffix");try{call(f.edit,"onSelectionChanged",new Class<?>[]{int.class,int.class},0,0);throw new AssertionError("unknown hidden callback accepted");}catch(RuntimeException expected){check(expected.getMessage().contains("unknown retired"),"hidden unknown callback records uncertainty");}});
        check(hidden[0]&&!c.setSelection(0,0)&&f.fence().terminal,"hidden suffix cannot get blanket cleanup authority");check(f.target().closeCalls==1,"hidden suffix did not retry target close");
    }}
    private static void fatalOrdering(){for(boolean primaryFatal:new boolean[]{false,true})try(Fixture f=new Fixture()){
        InputConnection c=f.connection();RuntimeException ordinary=new IllegalStateException("primary ordinary");Fatal first=new Fatal("primary fatal"),later=new Fatal("cleanup fatal");boolean[] fired={false};
        ConcreteHostProbe.hook=(method,phase)->{if(method.equals("BaseInputConnection.beginBatchEdit")&&phase.equals("entry")&&!fired[0]){fired[0]=true;if(primaryFatal)throw first;throw ordinary;}if(method.equals("BaseInputConnection.closeConnection")&&phase.equals("entry"))throw later;};
        try{c.beginBatchEdit();throw new AssertionError("fatal hidden");}catch(Fatal actual){check(actual==(primaryFatal?first:later),"first observed fatal wins over ordinary and later fatal");}
        ConcreteHostProbe.hook=null;check(f.renderer.cleanupLedger().primary()==(primaryFatal?first:ordinary),"original primary retained before cleanup");check(f.renderer.cleanupLedger().firstFatal()==(primaryFatal?first:later),"renderer first fatal matches");check(!f.renderer.editorDisposalBusyV2(),"fatal finite path clears busy");
    }}
    private static void handlerRejection(){for(boolean throwing:new boolean[]{false,true})try(Fixture f=new Fixture()){
        InputConnection c=f.connection();boolean[] fired={false};ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("BaseInputConnection.beginBatchEdit")&&phase.equals("entry")){fired[0]=true;if(throwing)f.queue.postFailure=new IllegalStateException("post rejected by throw");else f.queue.postResult=false;f.owner.close();}};
        try{c.beginBatchEdit();}catch(RuntimeException expected){check(f.fence().terminal,"post throw terminal retained");}ConcreteHostProbe.hook=null;
        check(f.target().closeCalls==1,"exact target finite drain despite rejected scheduling");check(NativeBridge.destroyCalls==0&&f.queue.queued()==0,"no autonomous owner retry fabricated");check(field(f.owner,"pendingCloseResource")!=null,"pending exact disposal resource retained");
    }}
    private static void serialAndDepthExhaustion(){
        try(Fixture f=new Fixture()){f.connection();f.fence().sealSerial=Long.MAX_VALUE;set(f.renderer.cleanupLedger(),"consumedSerial",Long.MAX_VALUE);f.owner.onPause();check(f.target().closeCalls==1,"terminal editor sweep precedes serial early return");}
        try(Fixture f=new Fixture()){f.connection();set(f.edit,"depth",16);int nativeBefore=ConcreteHostProbe.count("View.onWindowFocusChanged","entry");try{f.edit.onWindowFocusChanged(false);throw new AssertionError("exhausted lifecycle depth accepted");}catch(RuntimeException expected){check(expected.getMessage().contains("depth exhausted"),"depth overflow terminal");}check(ConcreteHostProbe.count("View.onWindowFocusChanged","entry")==nativeBefore,"overflow no native super");check(f.fence().terminal,"depth terminal");set(f.edit,"depth",0);}
    }
    private static void retainedRosterDisappearance(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();boolean[] fired={false};ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("BaseInputConnection.beginBatchEdit")&&phase.equals("beforeReturn")){fired[0]=true;set(f.renderer,"v2RosterCount",0);}};
        try{c.beginBatchEdit();throw new AssertionError("roster disappeared without failure");}catch(RuntimeException expected){check(expected.getMessage().contains("exact editor"),"retained-roster disappearance fails closed");}ConcreteHostProbe.hook=null;check(f.target().closeCalls==0,"foreign roster does not gain target close authority");check(field(field(f.edit,"attempt"),"close").toString().equals("FAILED_UNCERTAIN"),"roster loss uncertain close");
    }}
    private static void lifecycleReturnAndGain(){for(String nativePhase:new String[]{"entry","beforeReturn"})try(Fixture f=new Fixture()){
        InputConnection c=f.connection();BaseInputConnection old=f.target();boolean[] fired={false};ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("View.onWindowFocusChanged")&&phase.equals(nativePhase)){fired[0]=true;check(f.renderer.editorDisposalBusyV2(),"lifecycle busy at "+nativePhase);check(f.edit.onCreateInputConnection(new EditorInfo())==null,"lifecycle gain cannot create inside native frame");check(old.closeCalls==0,"lifecycle close follows suffix");}};
        f.edit.onWindowFocusChanged(false);ConcreteHostProbe.hook=null;check(old.closeCalls==1,"lifecycle closed once");f.edit.onWindowFocusChanged(true);check(!c.setSelection(0,0),"gain never revives old adapter");check(f.edit.onCreateInputConnection(new EditorInfo())!=null,"actual gain plus current facts admits fresh attempt");
    }}
    private static void lifecycleAndWidgetThrow(){for(String route:new String[]{"lifecycle","key","menu","accessibility"})try(Fixture f=new Fixture()){
        f.connection();RuntimeException original=new IllegalStateException("plain native "+route);String wanted=switch(route){case "lifecycle"->"View.onWindowFocusChanged";case "key"->"TextView.onKeyDown";case "menu"->"TextView.onTextContextMenuItem";default->"TextView.performAccessibilityAction";};boolean[] fired={false};
        ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals(wanted)&&phase.equals("entry")){fired[0]=true;throw original;}};
        try{switch(route){case "lifecycle"->f.edit.onWindowFocusChanged(true);case "key"->f.edit.onKeyDown(0,new android.view.KeyEvent(android.view.KeyEvent.ACTION_DOWN,0));case "menu"->f.edit.onTextContextMenuItem(0);default->f.edit.performAccessibilityAction(0,null);}throw new AssertionError("native failure hidden "+route);}catch(RuntimeException actual){check(actual==original,"native "+route+" original observed first");}
        ConcreteHostProbe.hook=null;check(f.target().closeCalls==1&&f.fence().terminal&&!f.renderer.editorDisposalBusyV2(),"plain "+route+" failure retires and finite drain");
    }}
    private static void constructorAndAbsentTarget(){try(Fixture f=new Fixture()){
        check(f.edit.connectionAcquisitions==0,"superclass constructor virtual callbacks cannot create target");check(field(f.edit,"attempt")==null,"bootstrap cannot fabricate attempt");
        boolean[] busy={false};ConcreteHostProbe.hook=(method,phase)->{if(method.equals("View.onWindowFocusChanged")&&phase.equals("entry"))busy[0]=f.renderer.editorDisposalBusyV2();};
        f.edit.onWindowFocusChanged(false);ConcreteHostProbe.hook=null;check(busy[0]&&!f.renderer.editorDisposalBusyV2(),"no-target lifecycle still owns counted platform suffix");check(f.edit.lastConnection==null,"absent target has no fabricated close");
        f.edit.onWindowFocusChanged(true);f.connection();
    }}
    private static void offmainFieldEntries(){try(Fixture f=new Fixture()){
        f.connection();Runnable[] routes={()->f.edit.onCreateInputConnection(new EditorInfo()),()->f.edit.onWindowFocusChanged(false),()->f.edit.onVisibilityAggregated(false),()->call(f.edit,"onDetachedFromWindow",new Class<?>[]{}),()->call(f.edit,"onAttachedToWindow",new Class<?>[]{}),()->call(f.edit,"onFocusChanged",new Class<?>[]{boolean.class,int.class,android.graphics.Rect.class},false,0,null),()->call(f.edit,"onWindowVisibilityChanged",new Class<?>[]{int.class},View.INVISIBLE),()->call(f.edit,"onVisibilityChanged",new Class<?>[]{View.class,int.class},f.edit,View.INVISIBLE),()->call(f.edit,"onSelectionChanged",new Class<?>[]{int.class,int.class},0,0),()->call(f.edit,"drawableStateChanged",new Class<?>[]{}),()->f.edit.setText("x"),()->f.edit.onKeyDown(0,null),()->f.edit.performAccessibilityAction(0,null),()->f.edit.onTextContextMenuItem(0)};
        for(Runnable route:routes){int before=ConcreteHostProbe.events().size();Looper.hostSetMain(false);try{route.run();throw new AssertionError("offmain field route accepted");}catch(IllegalStateException expected){check(true,"offmain refusal");}finally{Looper.hostReset();}check(ConcreteHostProbe.events().size()==before,"offmain field zero native effect");}
        check(!f.fence().terminal&&f.target().closeCalls==0,"offmain refusal cannot mutate retirement");
    }}
    private static void fullscreenAndReadRoutes(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();int before=f.target().mutations;check(c.reportFullscreenMode(true)&&c.reportFullscreenMode(false),"both fullscreen booleans delegated");check(f.target().mutations==before+2,"two exact native fullscreen calls");
        check(c.getSelectedText(1)!=null&&c.getTextBeforeCursor(20000,1)!=null&&c.getTextAfterCursor(20000,1)!=null&&c.getSurroundingText(20000,20000,1)!=null,"native read flags and large nonnegative requests retained");
        c.closeConnection();before=f.target().mutations;check(!c.reportFullscreenMode(true)&&!c.reportFullscreenMode(false),"closed fullscreen refuses both");check(f.target().mutations==before,"closed fullscreen no target call");
    }}
    private static void perUseEditableBinding(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();boolean[] fired={false};ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("BaseInputConnection.beginBatchEdit")&&phase.equals("entry")){
            fired[0]=true;NativeAppearanceViewsV2.Mutation captured=f.edit.record.mutation();check(captured.editorLease!=null,"live callback Mutation is tuple-bound");captured.require();
            try{Field text=android.widget.TextView.class.getDeclaredField("text");text.setAccessible(true);Object old=text.get(f.edit);text.set(f.edit,new android.text.Editable("replacement"));try{captured.require();throw new AssertionError("reused Mutation ignored Editable replacement");}catch(IllegalStateException expected){check(expected.getMessage().contains("exact editor"),"each Mutation use verifies Editable");}text.set(f.edit,old);}catch(ReflectiveOperationException e){throw new AssertionError(e);}
            captured.require();
        }};check(c.beginBatchEdit(),"captured lease can continue exact restored tuple in authored control");ConcreteHostProbe.hook=null;
    }}
    private static void centralDisposalGuard(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();Object coordinator=field(f.owner,"coordinator");boolean[] fired={false};
        ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("BaseInputConnection.beginBatchEdit")&&phase.equals("entry")){fired[0]=true;call(coordinator,"disposeOnce",new Class<?>[]{});check(!(Boolean)field(coordinator,"disposed")&&NativeBridge.destroyCalls==0,"central direct disposal refuses before disposition/session consumption");}};
        check(c.beginBatchEdit(),"ordinary feature/native entry remains healthy while editor busy");ConcreteHostProbe.hook=null;check(!f.fence().terminal,"busy disposal no-op not false success");
    }}
    private static void creatorSetterFatalAndCloseReentry(){try(Fixture f=new Fixture()){
        EditorInfo info=output();Fatal first=new Fatal("metadata first fatal"),later=new Fatal("close later fatal");boolean[] fired={false};
        ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("EditorInfo.setSupportedHandwritingGestures")&&phase.equals("entry")){fired[0]=true;throw first;}if(method.equals("BaseInputConnection.closeConnection")&&phase.equals("entry"))throw later;};
        try{f.edit.onCreateInputConnection(info);throw new AssertionError("metadata fatal hidden");}catch(Fatal actual){check(actual==first,"first metadata fatal retained over cleanup");}ConcreteHostProbe.hook=null;scrubbed(info);check(!f.renderer.editorDisposalBusyV2(),"metadata fatal cleanup clears busy");
    }}
    private static void closeReentryAndNoRetry(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();BaseInputConnection old=f.target();boolean[] fired={false};
        ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("BaseInputConnection.closeConnection")&&phase.equals("entry")){fired[0]=true;check(f.renderer.editorDisposalBusyV2(),"cleanup busy before native close");c.closeConnection();check(f.edit.onCreateInputConnection(new EditorInfo())==null,"close reentry no successor");check(!c.setSelection(0,0),"closing dispatch denied");f.owner.close();check(NativeBridge.destroyCalls==0,"cleanup reentry central disposal deferred");}};
        c.closeConnection();ConcreteHostProbe.hook=null;check(old.closeCalls==1,"recursive close consumed exactly once");check(NativeBridge.destroyCalls==0,"no sync disposal after cleanup final clear");f.queue.drainAll(8);check(NativeBridge.destroyCalls==1,"async closes owner after cleanup");
    }}
    private static void successfulCommitInterval(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();NativeBridge.preparedPacket=packet(2,"hello");boolean[] commit={false};int[] illegal={0};
        ConcreteHostProbe.hook=(method,phase)->{if(method.equals("NativeBridge.commitV2")&&phase.equals("beforeReturn")){commit[0]=true;return;}if(commit[0]&&f.fence().commitFinish)illegal[0]++;};
        check(c.performEditorAction(EditorInfo.IME_ACTION_DONE),"Done successful feature commit");ConcreteHostProbe.hook=null;check(commit[0]&&illegal[0]==0,"no controlled native/getter/callback work after successful commit before finish");
    }}
    private static void scrubAfterCloseCallback(){try(Fixture f=new Fixture()){
        EditorInfo info=output();boolean[] revoked={false},repopulated={false};
        ConcreteHostProbe.hook=(method,phase)->{if(!revoked[0]&&method.equals("EditText.onCreateInputConnection")&&phase.equals("beforeReturn")){revoked[0]=true;f.edit.clearFocus();}
            if(!repopulated[0]&&method.equals("BaseInputConnection.closeConnection")&&phase.equals("beforeReturn")){repopulated[0]=true;info.initialSelStart=info.initialSelEnd=0;info.hintText="late secret";info.setInitialSurroundingText("late secret");check(f.renderer.editorDisposalBusyV2(),"native close callback remains busy");}};
        check(f.edit.onCreateInputConnection(info)==null,"late close invalidation returns null");ConcreteHostProbe.hook=null;check(repopulated[0],"late output repopulation control reached");scrubbed(info);check(!f.renderer.editorDisposalBusyV2(),"creator guard clears after final output scrub");
    }}
    private static void sameHookRecursion(){try(Fixture f=new Fixture()){
        f.connection();boolean[] fired={false};ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("View.onWindowFocusChanged")&&phase.equals("entry")){fired[0]=true;f.edit.onWindowFocusChanged(false);}};
        try{f.edit.onWindowFocusChanged(false);throw new AssertionError("recursive native hook escaped bound");}catch(RuntimeException expected){check(expected.getMessage().contains("recursive editor hook"),"same hook recursion terminal");}ConcreteHostProbe.hook=null;check(ConcreteHostProbe.count("View.onWindowFocusChanged","entry")==1,"same-hook refused before second native super");check(f.target().closeCalls==1&&!f.renderer.editorDisposalBusyV2(),"recursive finite unwind closes once");
    }}
    private static void absentEditableAndExecutorFailures(){
        try(Fixture f=new Fixture()){try{Field text=android.widget.TextView.class.getDeclaredField("text");text.setAccessible(true);text.set(f.edit,null);}catch(ReflectiveOperationException e){throw new AssertionError(e);}try{f.edit.onWindowFocusChanged(false);throw new AssertionError("absent Editable admitted lifecycle lease");}catch(RuntimeException expected){check(expected.getMessage().contains("Editable unavailable"),"absent Editable explicit uncertainty");}check(f.edit.lastConnection==null&&f.fence().terminal,"no invented target or close from missing Editable");}
        try(Fixture f=new Fixture()){InputConnection c=f.connection();int before=f.target().mutations;Fatal fatal=new Fatal("caller executor fatal");try{c.requestTextBoundsInfo(null,task->{throw fatal;},value->{});throw new AssertionError("executor fatal hidden");}catch(Fatal actual){check(actual==fatal,"caller executor fatal preserved");}List<Runnable> pending=new ArrayList<>();int[] result={-1};c.performHandwritingGesture(null,pending::add,value->result[0]=value);Looper.hostSetMain(false);try{pending.get(0).run();}finally{Looper.hostReset();}check(result[0]==InputConnection.HANDWRITING_GESTURE_RESULT_UNSUPPORTED,"unsupported callback executes without editor thread/state access");check(f.target().mutations==before&&!f.fence().terminal,"unsupported callback has no target or retirement side effect");}
    }
    private static void entryGetterFailureIdentity(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();RuntimeException original=new IllegalStateException("entered getter failure");boolean[] fired={false};ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("TextView.getEditableText")&&phase.equals("entry")&&f.renderer.editorDisposalBusyV2()){fired[0]=true;throw original;}};
        try{c.beginBatchEdit();throw new AssertionError("entered getter failure converted to refusal");}catch(RuntimeException actual){check(actual==original,"entered getter original failure surfaces");}ConcreteHostProbe.hook=null;check(f.target().closeCalls==1&&f.fence().terminal,"entered getter retires known target");
    }}
    private static void positiveEditorInfo(){try(Fixture f=new Fixture()){
        EditorInfo info=new EditorInfo();info.imeOptions=EditorInfo.IME_ACTION_DONE|EditorInfo.IME_FLAG_NAVIGATE_NEXT|EditorInfo.IME_FLAG_NAVIGATE_PREVIOUS;
        InputConnection c=f.edit.onCreateInputConnection(info);check(c!=null,"native metadata returns same admitted attempt");check(info.initialSelStart==f.edit.getSelectionStart()&&info.initialSelEnd==f.edit.getSelectionEnd(),"success initial selection exact");
        check((info.imeOptions&(EditorInfo.IME_FLAG_NAVIGATE_NEXT|EditorInfo.IME_FLAG_NAVIGATE_PREVIOUS))==0,"refused navigation advertisements cleared");check((info.imeOptions&EditorInfo.IME_FLAG_NO_EXTRACT_UI)!=0&&(info.imeOptions&EditorInfo.IME_FLAG_NO_FULLSCREEN)!=0,"nonmonitor/fullscreen hints");check(info.gestures.isEmpty()&&info.previews.isEmpty()&&info.stylus,"gestures empty while generic stylus remains enabled");
    }}
    private static void replacementWitnesses(){for(boolean active:new boolean[]{false,true})try(Fixture f=new Fixture()){
        InputConnection c=active?f.connection():null;Object old=f.edit.getText();android.os.Bundle arguments=new android.os.Bundle();arguments.putCharSequence(android.view.accessibility.AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,"updated");Throwable returned=null;boolean result=false;
        try{result=f.edit.performAccessibilityAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT,arguments);}catch(RuntimeException|Error failure){returned=failure;}
        check(returned instanceof IllegalStateException&&!result&&f.fence().terminal,"known ACTION_SET_TEXT compatibility failure is retained, active="+active);
        if(active){check(f.edit.getText()==old&&f.edit.getText().toString().equals("hello")&&f.target().closeCalls==1,"active replacement refused before new Editable; exact predecessor closed");check(!c.setSelection(0,0),"failed replacement adapter permanently revoked");}
        else check(f.edit.getText()==old&&f.edit.getText().toString().equals("hello")&&f.edit.lastConnection==null,"fresh replacement refused by active native frame before replacement; no invented target");
        System.out.println("KNOWN_COMPATIBILITY_FAILURE ACTION_SET_TEXT active="+active+" returned="+returned.getClass().getSimpleName()+":"+returned.getMessage()+" value="+f.edit.getText()+" EditableReplaced="+(f.edit.getText()!=old)+" targetCloseCalls="+(f.edit.lastConnection==null?0:f.target().closeCalls)+" terminal="+f.fence().terminal);
    }}
    private static android.os.Bundle replacementPayload(CharSequence value){android.os.Bundle bundle=new android.os.Bundle();bundle.putCharSequence(android.view.accessibility.AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,value);return bundle;}
    private static boolean replace(Fixture f,CharSequence value,long revision){NativeBridge.preparedPacket=packet(revision,value.toString());return f.edit.performAccessibilityAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT,replacementPayload(value));}
    private static void replacementPositiveCases(){for(String mode:new String[]{"fresh","active","closed"})try(Fixture f=new Fixture()){
        InputConnection old=mode.equals("fresh")?null:f.connection();BaseInputConnection target=mode.equals("fresh")?null:f.target();if(mode.equals("closed"))old.closeConnection();
        Object original=f.edit.getEditableText();int events=NativeBridge.prepareCalls;
        check(replace(f,"updated",2),"valid ACTION_SET_TEXT succeeds mode="+mode);
        check(f.edit.getEditableText()!=original&&f.edit.getEditableText().toString().equals("updated"),"one native new Editable/value");check(f.edit.getSelectionStart()==7&&f.edit.getSelectionEnd()==7,"native post-setter selection suffix");
        check(NativeBridge.prepareCalls==events+1,"one synchronous feature transaction");check(!f.fence().terminal&&!f.renderer.editorDisposalBusyV2(),"healthy replacement remains live and clears busy");
        if(target!=null){check(target.closeCalls==1,"exact predecessor closed once");check(!old.setSelection(0,0),"old adapter never revived");}
        Object next=f.edit.getEditableText();InputConnection c=f.connection();check(c.setSelection(1,1)&&f.edit.getEditableText()==next,"later fresh connection uses Enew");
    }}
    private static void replacementSameEmptyAnnotationAndFreshUnfocused(){
        for(String value:new String[]{"hello","","🙂 text"})try(Fixture f=new Fixture()){
            InputConnection old=f.connection();BaseInputConnection target=f.target();Object before=f.edit.getEditableText();int setters=ConcreteHostProbe.count("TextView.setText","entry"),events=NativeBridge.prepareCalls;
            check(replace(f,value,2),"same/empty/Unicode replacement success");check(f.edit.getEditableText()!=before,"explicit action calls native setter even equal/empty");check(ConcreteHostProbe.events().stream().filter(e->e.receiver==f.edit&&e.method.equals("TextView.setText")&&e.phase.equals("entry")).count()==1,"one native replacement setter on exact field, regardless detached shadow optimization");
            check(f.edit.getSelectionStart()==value.length()&&f.edit.getSelectionEnd()==value.length(),"default movement0 and native nonempty end suffix");check(NativeBridge.prepareCalls==events+1&&target.closeCalls==1&&!old.beginBatchEdit(),"one event and permanently consumed predecessor");
        }
        try(Fixture f=new Fixture()){
            android.text.Editable source=new android.text.Editable("annotated");android.text.Annotation span=new android.text.Annotation("language","en");source.setSpan(span,0,9,17);Object[] newBuffer={null};
            ConcreteHostProbe.hook=(method,phase)->{if(method.equals("TextView.performAccessibilityAction")&&phase.equals("beforeReturn"))newBuffer[0]=f.edit.getEditableText();};
            check(replace(f,source,2),"Annotation replacement accepted");ConcreteHostProbe.hook=null;check(f.edit.getEditableText()==newBuffer[0],"compatible event Binding echo preserves Enew");check(f.edit.getEditableText().getSpanStart(span)==0&&f.edit.getEditableText().getSpanEnd(span)==9&&f.edit.getEditableText().getSpanFlags(span)==17,"Annotation spans survive owned snapshot/native setter/echo");
        }
        try(Fixture f=new Fixture()){f.edit.focused=false;check(replace(f,"unfocused",2),"fresh never-focused field accessibility replacement");check(!f.fence().terminal&&f.edit.getSelectionStart()==9,"fresh unfocused native result");}
    }
    private static void replacementOrderingAndSuffix(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();BaseInputConnection old=f.target();Object before=f.edit.getEditableText();boolean[] nativeEntry={false},movement={false},suffix={false};int[] directAfterEvent={0};boolean[] event={false};
        ConcreteHostProbe.hook=(method,phase)->{
            if(method.equals("NativeBridge.prepareV2")&&phase.equals("entry")){event[0]=true;check(field(f.edit,"replacement")==null&&!f.renderer.editorDisposalBusyV2(),"replacement guard released before ordinary event transaction");}
            if(method.equals("TextView.getEditableText")&&phase.equals("entry")&&event[0]&&ConcreteHostProbe.lastEvent().receiver==f.edit&&ConcreteHostProbe.lastEvent().productionFrames.get(0).methodName().equals("replaceAccessibility"))directAfterEvent[0]++;
            if(method.equals("TextView.performAccessibilityAction")&&phase.equals("entry")){nativeEntry[0]=true;check(old.closeCalls==1&&f.edit.getEditableText()==before&&f.edit.record.editorCallbackLease==null,"old exact close and scope restoration precede accessibility super");}
            Object operation=field(f.edit,"replacement");
            if(operation!=null&&method.equals("TextView.onSelectionChanged")&&phase.equals("entry")){
                check(f.renderer.editorDisposalBusyV2(),"replacement selection continuation counted busy");
                if((Boolean)field(operation,"setterActive")){movement[0]=true;check(field(operation,"nextEditable")==f.edit.getEditableText(),"movement first observes Enew before watcher");}
                else {suffix[0]=true;check((Boolean)field(operation,"nativeExecuting"),"end-selection after setter remains inside whole accessibility super");}
                check(!c.setSelection(0,0)&&f.edit.onCreateInputConnection(new EditorInfo())==null,"no target dispatch/creation in replacement callback");check(!f.edit.performAccessibilityAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT,replacementPayload("nested")),"nested replacement refuses before super");
                try{f.edit.record.mutation().requireMutation();throw new AssertionError("field-only replacement authorized bind/layout");}catch(IllegalStateException expected){check(true,"no bind authority");}
            }
        };
        check(replace(f,"updated",2),"ordered native replacement succeeds");ConcreteHostProbe.hook=null;check(nativeEntry[0]&&movement[0]&&suffix[0]&&event[0]&&directAfterEvent[0]==0,"whole native algorithm covered, then scalar-only post-event return");
    }}
    private static void replacementInvalidAndMutablePayload(){try(Fixture f=new Fixture()){
        InputConnection c=f.connection();BaseInputConnection old=f.target();Object before=f.edit.getEditableText();int nativeCalls=ConcreteHostProbe.count("TextView.performAccessibilityAction","entry");
        for(CharSequence value:new CharSequence[]{null,"\ud800","x".repeat(16385)})check(!f.edit.performAccessibilityAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT,replacementPayload(value)),"invalid replacement clean refusal");
        android.text.Editable styled=new android.text.Editable("x");styled.setSpan(new Object(),0,1,0);check(!f.edit.performAccessibilityAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT,replacementPayload(styled)),"unsupported span clean refusal");
        check(old.closeCalls==0&&f.edit.getEditableText()==before&&!f.fence().terminal&&ConcreteHostProbe.count("TextView.performAccessibilityAction","entry")==nativeCalls&&c.setSelection(0,0),"invalid proposal preserves healthy predecessor and has no native action");
        android.os.Bundle original=new android.os.Bundle();boolean[] copied={false};CharSequence mutable=new CharSequence(){public int length(){return 5;}public char charAt(int i){return "owned".charAt(i);}public CharSequence subSequence(int a,int b){return "owned".substring(a,b);}@Override public String toString(){copied[0]=true;original.putCharSequence(android.view.accessibility.AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,"evil");check(!c.beginBatchEdit()&&f.edit.onCreateInputConnection(new EditorInfo())==null,"SNAPSHOTTING denies nested native entry");check(!f.edit.performAccessibilityAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT,replacementPayload("nested")),"SNAPSHOTTING nested replacement denied");return "owned";}};
        original.putCharSequence(android.view.accessibility.AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,mutable);NativeBridge.preparedPacket=packet(2,"owned");check(f.edit.performAccessibilityAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT,original),"owned stable snapshot passed to super");check(copied[0]&&f.edit.getEditableText().toString().equals("owned")&&old.closeCalls==1,"mutable Bundle source cannot swap validated native payload");
    }}
    private static void replacementNativeRefusalAndPartial(){for(int behavior:new int[]{1,2,3,4})try(Fixture f=new Fixture()){
        InputConnection c=f.connection();BaseInputConnection old=f.target();Object before=f.edit.getEditableText();int events=NativeBridge.prepareCalls;android.widget.TextView.accessibilitySetTextBehavior=behavior;
        boolean result=false;Throwable escaped=null;try{result=replace(f,"updated",2);}catch(RuntimeException|Error failure){escaped=failure;}
        if(behavior==1){check(!result&&escaped==null&&!f.fence().terminal&&f.edit.getEditableText()==before,"clean false without setter is ordinary refusal");check(f.connection()!=null,"clean native refusal permits later fresh connection");}
        else check(!result&&escaped instanceof IllegalStateException&&f.fence().terminal,"true without setter/partial false/second setter is uncertainty");
        check(old.closeCalls==1&&!c.beginBatchEdit()&&NativeBridge.prepareCalls==events,"no old target replay or event on native refusal/partial failure");
    }}
    private static void replacementIdentityAndLifecycleFailure(){for(String mode:new String[]{"second","revert","secondSetter","loss","owner"})try(Fixture f=new Fixture()){
        InputConnection oldAdapter=f.connection();BaseInputConnection old=f.target();Object oldEditable=f.edit.getEditableText();boolean[] fired={false};int events=NativeBridge.prepareCalls;
        ConcreteHostProbe.hook=(method,phase)->{Object operation=field(f.edit,"replacement");if(!fired[0]&&operation!=null&&method.equals("TextView.onSelectionChanged")&&phase.equals("entry")&&(Boolean)field(operation,"setterActive")){
            fired[0]=true;switch(mode){case "second", "revert"->{try{Field text=android.widget.TextView.class.getDeclaredField("text");text.setAccessible(true);text.set(f.edit,mode.equals("revert")?oldEditable:new android.text.SpannableStringBuilder("updated"));}catch(ReflectiveOperationException e){throw new AssertionError(e);}}case "secondSetter"->f.edit.setText("updated");case "loss"->f.edit.clearFocus();default->{f.owner.close();check(NativeBridge.destroyCalls==0,"owner cleanup deferred through replacement suffix");}}
        }};
        try{replace(f,"updated",2);throw new AssertionError("replacement identity/loss failure returned success "+mode);}catch(RuntimeException expected){check(fired[0]&&f.fence().terminal,"replacement mismatch/loss terminal");}ConcreteHostProbe.hook=null;
        check(old.closeCalls==1&&!oldAdapter.setSelection(0,0)&&NativeBridge.prepareCalls==events&&!f.renderer.editorDisposalBusyV2(),"no old-target close against Enew, no event, finite busy clear");
    }}
    private static void replacementThrowAndFinalReentry(){for(String stage:new String[]{"close","setter","suffix","final","event"})try(Fixture f=new Fixture()){
        f.connection();BaseInputConnection old=f.target();RuntimeException failure=new IllegalStateException("replacement "+stage+" failure");boolean[] fired={false};int events=NativeBridge.prepareCalls;
        ConcreteHostProbe.hook=(method,phase)->{if(fired[0])return;Object operation=field(f.edit,"replacement");boolean selected=switch(stage){case "close"->method.equals("BaseInputConnection.closeConnection")&&phase.equals("entry");case "setter"->method.equals("TextView.setText")&&phase.equals("entry");case "suffix"->operation!=null&&method.equals("TextView.setSelection")&&phase.equals("entry")&&!(Boolean)field(operation,"setterActive");case "final"->operation!=null&&method.equals("TextView.getEditableText")&&phase.equals("beforeReturn")&&!(Boolean)field(operation,"nativeExecuting")&&field(operation,"stage").toString().equals("NATIVE");default->method.equals("NativeBridge.prepareV2")&&phase.equals("entry");};
            if(selected){fired[0]=true;if(stage.equals("final")||stage.equals("event")){f.owner.close();if(stage.equals("final"))check(NativeBridge.destroyCalls==0,"final getter still replacement busy");}else throw failure;}
        };
        boolean result=false;Throwable escaped=null;try{result=replace(f,"updated",2);}catch(RuntimeException|Error actual){escaped=actual;}ConcreteHostProbe.hook=null;
        check(fired[0]&&!result&&f.fence().terminal&&!f.renderer.editorDisposalBusyV2(),"failure/reentry stage handled "+stage);
        if(!stage.equals("final")&&!stage.equals("event"))check(escaped==failure,"original native replacement failure identity");
        check(old.closeCalls<=1,"one old close attempt only");check(NativeBridge.prepareCalls==events+(stage.equals("event")?1:0),"no pre-completion event");
    }}
    private static final class PoisonInfo extends EditorInfo {
        int calls;
        @Override public void setSupportedHandwritingGesturePreviews(Set<Class<? extends PreviewableHandwritingGesture>> values){calls++;super.setSupportedHandwritingGesturePreviews(values);inputType=99;hintText="repopulated";initialSelStart=initialSelEnd=0;super.setInitialSurroundingText("private");super.setSupportedHandwritingGestures(List.of(SelectGesture.class));super.setSupportedHandwritingGesturePreviews(Set.of(SelectGesture.class));}
        @Override public List<Class<? extends HandwritingGesture>> getSupportedHandwritingGestures(){calls++;return super.getSupportedHandwritingGestures();}
    }
    private static void metadataClassPolicyAndPostchecks(){
        for(boolean active:new boolean[]{false,true})try(Fixture f=new Fixture()){
            InputConnection old=active?f.connection():null;PoisonInfo info=new PoisonInfo();info.inputType=77;info.hintText="caller-owned";info.initialSelStart=info.initialSelEnd=0;info.setInitialSurroundingText("caller-private");int effects=ConcreteHostProbe.events().size(),acquired=f.edit.connectionAcquisitions;
            check(f.edit.onCreateInputConnection(info)==null,"EditorInfo subclass clean pre-effect refusal");check(info.calls==0&&info.inputType==77&&info.hintText.equals("caller-owned")&&info.hostSurrounding().equals("caller-private"),"unsupported subclass output never read/mutated/scrubbed");check(ConcreteHostProbe.events().size()==effects&&f.edit.connectionAcquisitions==acquired&&!f.fence().terminal,"class policy precedes live getters/native creator");
            if(active)check(f.target().closeCalls==0&&old.setSelection(0,0),"unsupported subclass does not revoke healthy connection");
        }
        try(Fixture f=new Fixture()){
            EditorInfo info=output();boolean[] fired={false};ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("EditorInfo.setSupportedHandwritingGesturePreviews")&&phase.equals("beforeReturn")){fired[0]=true;info.gestures=List.of(SelectGesture.class);info.previews=Set.of(SelectGesture.class);}};
            check(f.edit.onCreateInputConnection(info)==null,"ordinary output postchecks reject reintroduced supported gesture advertisements");ConcreteHostProbe.hook=null;scrubbed(info);check(f.target().closeCalls==1,"invalid metadata retires known target exactly once");
        }
        try(Fixture f=new Fixture()){
            EditorInfo info=output();android.widget.EditText.creatorNull=true;ConcreteHostProbe.hook=(method,phase)->{if(method.equals("EditorInfo.setSupportedHandwritingGesturePreviews")&&phase.equals("beforeReturn")){info.inputType=99;info.hintText="repopulated-output";info.initialSelStart=info.initialSelEnd=0;info.setInitialSurroundingText("private-surrounding-output");}};
            try{check(f.edit.onCreateInputConnection(info)==null,"ordinary native-null scrub");}finally{android.widget.EditText.creatorNull=false;ConcreteHostProbe.hook=null;}scrubbed(info);
        }
    }
    private static void independentTupleGetterRegressions(){
        try(Fixture f=new Fixture()){
            InputConnection c=f.connection();boolean[] outer={false},inner={false},accepted={false};ConcreteHostProbe.hook=(method,phase)->{if(!outer[0]&&method.equals("BaseInputConnection.beginBatchEdit")&&phase.equals("entry")){
                outer[0]=true;f.owner.close();NativeAppearanceViewsV2.Mutation captured=f.edit.record.mutation();int saved=(Integer)field(f.renderer,"v2RosterCount");ConcreteHostProbe.hook=(nested,at)->{if(!inner[0]&&nested.equals("TextView.getEditableText")&&at.equals("beforeReturn")){inner[0]=true;set(f.renderer,"v2RosterCount",0);}};
                try{captured.require();accepted[0]=true;}catch(IllegalStateException expected){accepted[0]=false;}finally{set(f.renderer,"v2RosterCount",saved);ConcreteHostProbe.hook=null;}
            }};c.beginBatchEdit();ConcreteHostProbe.hook=null;check(outer[0]&&inner[0]&&!accepted[0],"callable passive getter roster loss rejected in same captured Mutation use");
        }
        for(boolean swapTarget:new boolean[]{false,true})try(Fixture f=new Fixture()){
            InputConnection c=f.connection();BaseInputConnection old=f.target(),foreign=new BaseInputConnection(f.edit,true);Object attempt=field(f.edit,"attempt");boolean[] fired={false};int saved=(Integer)field(f.renderer,"v2RosterCount");
            ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("TextView.getEditableText")&&phase.equals("beforeReturn")&&ConcreteHostProbe.lastEvent().productionFrames.stream().anyMatch(frame->frame.methodName().equals("drain"))){fired[0]=true;if(swapTarget)set(attempt,"target",foreign);else set(f.renderer,"v2RosterCount",0);}};
            try{c.closeConnection();throw new AssertionError("getter-corrupted close accepted");}catch(IllegalStateException expected){check(true,"exact close precondition failed before dispatch");}ConcreteHostProbe.hook=null;set(f.renderer,"v2RosterCount",saved);
            check(fired[0]&&old.closeCalls==0&&foreign.closeCalls==0,"post-getter exact check prevents old/foreign dispatch after tuple loss");
        }
    }
    private static byte[] twoFields(long revision,String first,String second){
        Object field=Json.map("id","field","kind","textField","properties",Json.map("label","Entry","value",first),"children",List.of(),"actions",List.of(Json.map("id","changed","event","textChange"),Json.map("id","done","event","submit")));
        Object other=Json.map("id","other","kind","textField","properties",Json.map("label","Other","value",second),"children",List.of(),"actions",List.of(Json.map("id","otherChanged","event","textChange"),Json.map("id","otherDone","event","submit")));
        Object root=Json.map("id","root","kind","vStack","properties",Map.of(),"children",List.of(field,other),"actions",List.of());StringBuilder out=new StringBuilder();write(out,Json.map("schemaVersion",new Json.Num("1"),"document",Json.map("schemaVersion",new Json.Num("1"),"revision",new Json.Num(Long.toString(revision)),"root",root),"identities",List.of(Json.map("id","root","generation",new Json.Num("1")),Json.map("id","field","generation",new Json.Num("2")),Json.map("id","other","generation",new Json.Num("3")))));return out.toString().getBytes(StandardCharsets.UTF_8);
    }
    private static void replacementOwnVersusForeignDrain(){try(Fixture f=new Fixture(twoFields(1,"hello","other"))){
        f.connection();BaseInputConnection old=f.target();NativeAppearanceViewsV2.NativeField other=(NativeAppearanceViewsV2.NativeField)f.renderer.view("other");other.requestFocus();InputConnection otherConnection=other.onCreateInputConnection(new EditorInfo());check(otherConnection!=null,"second actual admitted field");BaseInputConnection foreign=(BaseInputConnection)other.lastConnection;
        CharSequence payload=new CharSequence(){public int length(){return 7;}public char charAt(int i){return "updated".charAt(i);}public CharSequence subSequence(int a,int b){return "updated".substring(a,b);}@Override public String toString(){
            NativeAppearanceViewsV2.Replacement operation=(NativeAppearanceViewsV2.Replacement)field(f.edit,"replacement");NativeAppearanceViewsV2.NativeField.Attempt predecessor=(NativeAppearanceViewsV2.NativeField.Attempt)field(f.edit,"attempt"),otherAttempt=(NativeAppearanceViewsV2.NativeField.Attempt)field(other,"attempt");
            check(!f.edit.record.input.editorCloseAllowed(f.edit.record,predecessor),"SNAPSHOTTING grants no close permission");operation.stage=NativeAppearanceViewsV2.Replacement.Stage.CLOSING;
            check(f.edit.record.input.editorCloseAllowed(f.edit.record,predecessor)&&!other.record.input.editorCloseAllowed(other.record,otherAttempt),"only captured own Eold predecessor may close during reservation");
            NativeAppearanceViewsV2.EditorLease forged=new NativeAppearanceViewsV2.EditorLease(other,otherAttempt,other.getEditableText(),NativeAppearanceViewsV2.Mutation.live(f.fence()),null,"close");
            try{other.record.input.editorDrainBegin(other.record,forged);throw new AssertionError("foreign drain began under replacement");}catch(RuntimeException expected){check(foreign.closeCalls==0,"foreign drain rejected before close/disposition");}
            operation.stage=NativeAppearanceViewsV2.Replacement.Stage.SNAPSHOTTING;return "updated";
        }};
        NativeBridge.preparedPacket=twoFields(2,"updated","other");check(f.edit.performAccessibilityAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT,replacementPayload(payload)),"own replacement still succeeds");check(old.closeCalls==1&&foreign.closeCalls==0&&otherConnection.setSelection(0,0),"own predecessor consumed, foreign healthy connection preserved");
    }}
    private static void replacementCleanupFatalAndHandlerFailure(){
        try(Fixture f=new Fixture()){
            f.connection();Fatal first=new Fatal("old close fatal"),later=new Fatal("terminal scheduling fatal");boolean[] fired={false};ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("BaseInputConnection.closeConnection")&&phase.equals("entry")){fired[0]=true;f.queue.postFailure=later;throw first;}};
            try{replace(f,"updated",2);throw new AssertionError("replacement predecessor fatal hidden");}catch(Fatal actual){check(actual==first,"first native predecessor fatal wins over reporting/scheduling fatal");}ConcreteHostProbe.hook=null;check(!f.renderer.editorDisposalBusyV2()&&f.edit.getEditableText().toString().equals("hello"),"fatal prevents native replacement and clears busy last");
        }
        try(Fixture f=new Fixture()){
            f.connection();boolean[] fired={false};ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("TextView.onSelectionChanged")&&phase.equals("entry")&&field(f.edit,"replacement")!=null){fired[0]=true;f.queue.postResult=false;f.owner.close();check(NativeBridge.destroyCalls==0,"rejected async post cannot consume owner while replacement busy");}};
            try{replace(f,"updated",2);throw new AssertionError("replacement owner retirement returned success");}catch(RuntimeException expected){check(f.fence().terminal,"owner retirement retained");}ConcreteHostProbe.hook=null;check(f.queue.queued()==0&&field(f.owner,"pendingCloseResource")!=null&&NativeBridge.destroyCalls==0,"Handler rejection remains pending, no autonomous retry fabricated");
        }
    }
    private static void foreignEntryExclusionAndLaterEntry(){try(Fixture f=new Fixture(twoFields(1,"hello","other"))){
        NativeAppearanceViewsV2.NativeField other=(NativeAppearanceViewsV2.NativeField)f.renderer.view("other");f.edit.focused=false;other.requestFocus();InputConnection c=other.onCreateInputConnection(new EditorInfo());check(c!=null,"focused foreign connection admitted");check(!f.edit.hasFocus()&&other.hasFocus(),"unfocused accessible A with focused healthy B");BaseInputConnection target=(BaseInputConnection)other.lastConnection;
        CharSequence payload=new CharSequence(){public int length(){return 7;}public char charAt(int i){return "updated".charAt(i);}public CharSequence subSequence(int a,int b){return "updated".substring(a,b);}@Override public String toString(){int effects=ConcreteHostProbe.events().size(),mutations=target.mutations;EditorInfo info=new EditorInfo();info.inputType=99;
            check(!c.beginBatchEdit()&&!c.setSelection(0,0),"foreign adapter new entry cleanly refused");check(other.onCreateInputConnection(info)==null&&info.inputType==99,"foreign creator refuses before output/revocation");check(!other.performAccessibilityAction(0,null)&&!other.onTextContextMenuItem(0)&&!other.onKeyDown(0,new android.view.KeyEvent(android.view.KeyEvent.ACTION_DOWN,0)),"foreign widget entries refused before native effects");
            check(!other.performAccessibilityAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT,replacementPayload("nested")),"foreign second replacement refused before native effects");check(ConcreteHostProbe.events().size()==effects&&target.mutations==mutations&&target.closeCalls==0&&!f.fence().terminal,"scalar reservation exclusion has no getters/target/retirement effects");return "updated";
        }};
        NativeBridge.preparedPacket=twoFields(2,"updated","other");check(f.edit.performAccessibilityAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT,replacementPayload(payload)),"own reserved replacement succeeds");check(c.setSelection(0,0)&&target.closeCalls==0,"foreign adapter remains healthy after reservation");EditorInfo next=new EditorInfo();check(other.onCreateInputConnection(next)!=null&&target.closeCalls==1,"later fresh foreign entry admitted normally");
    }}
    private static void foreignLossStillLatches(){try(Fixture f=new Fixture(twoFields(1,"hello","other"))){
        f.connection();BaseInputConnection own=f.target();NativeAppearanceViewsV2.NativeField other=(NativeAppearanceViewsV2.NativeField)f.renderer.view("other");other.requestFocus();InputConnection c=other.onCreateInputConnection(new EditorInfo());BaseInputConnection foreign=(BaseInputConnection)other.lastConnection;
        CharSequence payload=new CharSequence(){public int length(){return 7;}public char charAt(int i){return "updated".charAt(i);}public CharSequence subSequence(int a,int b){return "updated".substring(a,b);}@Override public String toString(){other.onWindowFocusChanged(false);return "updated";}};
        try{f.edit.performAccessibilityAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_SET_TEXT,replacementPayload(payload));throw new AssertionError("foreign actual loss hidden by reservation");}catch(RuntimeException expected){check((Boolean)field(other,"windowFocusLost")&&f.fence().terminal,"foreign actual loss remains latched and recorded");}
        check(own.closeCalls==0&&foreign.closeCalls==0&&!c.beginBatchEdit()&&!f.renderer.editorDisposalBusyV2(),"reservation granted no foreign close; finite refusal clears busy");f.queue.drainAll(8);check(own.closeCalls==1&&foreign.closeCalls==1,"accepted asynchronous disposal later drains exact unchanged buffers");
    }}
    public static void main(String[] args)throws Exception {
        descriptor=Files.readAllBytes(Path.of(args[0]));
        group("complete-source-baseline",EditorImplementationTests::baseline);
        group("all-descriptor-offmain-and-no-default",EditorImplementationTests::descriptorControls);
        group("selected-refusals",EditorImplementationTests::refusalPolicies);
        group("creator-serialization-and-successor-close",EditorImplementationTests::creatorSerialization);
        group("standalone-lifecycle-loss-latches",EditorImplementationTests::lifecycle);
        group("delegate-retirement-exact-unwind",EditorImplementationTests::retireInsideDelegate);
        group("unrequested-native-throw",EditorImplementationTests::plainThrow);
        group("owner-disposal-async-resumption",EditorImplementationTests::ownerCloseInsideDelegate);
        group("compatibleEcho",EditorImplementationTests::compatibleEcho);
        group("allMutatingDescriptors",EditorImplementationTests::allMutatingDescriptors);
        group("staleDescriptors",EditorImplementationTests::staleDescriptors);
        group("noCallAndQuerySnapshots",EditorImplementationTests::noCallAndQuerySnapshots);
        group("editorInfoNullAndThrow",EditorImplementationTests::editorInfoNullAndThrow);
        group("editorInfoLateInvalidation",EditorImplementationTests::editorInfoLateInvalidation);
        group("editorInfoSetterReentry",EditorImplementationTests::editorInfoSetterReentry);
        group("finalizationOutputScrub",EditorImplementationTests::finalizationOutputScrub);
        group("leaseBoundEveryUse",EditorImplementationTests::leaseBoundEveryUse);
        group("callbackPostcheck",EditorImplementationTests::callbackPostcheck);
        group("hiddenDetachSuffix",EditorImplementationTests::hiddenDetachSuffix);
        group("fatalOrdering",EditorImplementationTests::fatalOrdering);
        group("handlerRejection",EditorImplementationTests::handlerRejection);
        group("serialAndDepthExhaustion",EditorImplementationTests::serialAndDepthExhaustion);
        group("retainedRosterDisappearance",EditorImplementationTests::retainedRosterDisappearance);
        group("lifecycleReturnAndGain",EditorImplementationTests::lifecycleReturnAndGain);
        group("lifecycleAndWidgetThrow",EditorImplementationTests::lifecycleAndWidgetThrow);
        group("constructorAndAbsentTarget",EditorImplementationTests::constructorAndAbsentTarget);
        group("offmainFieldEntries",EditorImplementationTests::offmainFieldEntries);
        group("fullscreenAndReadRoutes",EditorImplementationTests::fullscreenAndReadRoutes);
        group("perUseEditableBinding",EditorImplementationTests::perUseEditableBinding);
        group("centralDisposalGuard",EditorImplementationTests::centralDisposalGuard);
        group("creatorSetterFatalAndCloseReentry",EditorImplementationTests::creatorSetterFatalAndCloseReentry);
        group("closeReentryAndNoRetry",EditorImplementationTests::closeReentryAndNoRetry);
        group("successfulCommitInterval",EditorImplementationTests::successfulCommitInterval);
        group("scrubAfterCloseCallback",EditorImplementationTests::scrubAfterCloseCallback);
        group("sameHookRecursion",EditorImplementationTests::sameHookRecursion);
        group("absentEditableAndExecutorFailures",EditorImplementationTests::absentEditableAndExecutorFailures);
        group("entryGetterFailureIdentity",EditorImplementationTests::entryGetterFailureIdentity);
        group("positiveEditorInfo",EditorImplementationTests::positiveEditorInfo);
        group("replacementPositiveCases",EditorImplementationTests::replacementPositiveCases);
        group("replacementSameEmptyAnnotationAndFreshUnfocused",EditorImplementationTests::replacementSameEmptyAnnotationAndFreshUnfocused);
        group("replacementOrderingAndSuffix",EditorImplementationTests::replacementOrderingAndSuffix);
        group("replacementInvalidAndMutablePayload",EditorImplementationTests::replacementInvalidAndMutablePayload);
        group("replacementNativeRefusalAndPartial",EditorImplementationTests::replacementNativeRefusalAndPartial);
        group("replacementIdentityAndLifecycleFailure",EditorImplementationTests::replacementIdentityAndLifecycleFailure);
        group("replacementThrowAndFinalReentry",EditorImplementationTests::replacementThrowAndFinalReentry);
        group("metadataClassPolicyAndPostchecks",EditorImplementationTests::metadataClassPolicyAndPostchecks);
        group("independentTupleGetterRegressions",EditorImplementationTests::independentTupleGetterRegressions);
        group("replacementOwnVersusForeignDrain",EditorImplementationTests::replacementOwnVersusForeignDrain);
        group("replacementCleanupFatalAndHandlerFailure",EditorImplementationTests::replacementCleanupFatalAndHandlerFailure);
        group("foreignEntryExclusionAndLaterEntry",EditorImplementationTests::foreignEntryExclusionAndLaterEntry);
        group("foreignLossStillLatches",EditorImplementationTests::foreignLossStillLatches);
        System.out.println("PASS "+groups+" actual-complete-source groups / "+checks+" assertions; original ACTION_SET_TEXT failures retained as historical evidence only; controlled authored Android/JNI leaves only");
    }
}
