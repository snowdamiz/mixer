package dev.mixer.android;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

/** Independent reflected invariant injections; these are not public exploit claims. */
public final class AdditionalReplacementControls {
    private AdditionalReplacementControls() {}
    private static byte[] descriptor;
    private static int checks;
    private static final class Fatal extends Error {private static final long serialVersionUID=1L;Fatal(String text){super(text);}}
    private static void check(boolean yes,String text){checks++;if(!yes)throw new AssertionError(text);}
    private static Object get(Object target,String name){try{Field field=target.getClass().getDeclaredField(name);field.setAccessible(true);return field.get(target);}catch(ReflectiveOperationException bad){throw new AssertionError(bad);}}
    private static void put(Object target,String name,Object value){try{Field field=target.getClass().getDeclaredField(name);field.setAccessible(true);field.set(target,value);}catch(ReflectiveOperationException bad){throw new AssertionError(bad);}}
    private static void write(StringBuilder out,Object value){if(value instanceof List<?> values){out.append('[');for(int i=0;i<values.size();i++){if(i>0)out.append(',');write(out,values.get(i));}out.append(']');}else if(value instanceof Map<?,?> values){out.append('{');boolean comma=false;for(var entry:values.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,entry.getKey());out.append(':');write(out,entry.getValue());}out.append('}');}else Json.write(out,value);}
    private static byte[] packet(long revision,String text){Object node=Json.map("id","field","kind","textField","properties",Json.map("label","Entry","value",text),"children",List.of(),"actions",List.of(Json.map("id","changed","event","textChange")));StringBuilder out=new StringBuilder();write(out,Json.map("schemaVersion",new Json.Num("1"),"document",Json.map("schemaVersion",new Json.Num("1"),"revision",new Json.Num(Long.toString(revision)),"root",node),"identities",List.of(Json.map("id","field","generation",new Json.Num("1")))));return out.toString().getBytes(StandardCharsets.UTF_8);}
    private static Object node(String id,String value){return Json.map("id",id,"kind","textField","properties",Json.map("label",id,"value",value),"children",List.of(),"actions",List.of(Json.map("id",id+"Changed","event","textChange")));}
    private static byte[] pairPacket(long revision,String a,String b){Object node=Json.map("id","root","kind","vStack","properties",Json.map(),"children",List.of(node("field",a),node("other",b)),"actions",List.of());StringBuilder out=new StringBuilder();write(out,Json.map("schemaVersion",new Json.Num("1"),"document",Json.map("schemaVersion",new Json.Num("1"),"revision",new Json.Num(Long.toString(revision)),"root",node),"identities",List.of(Json.map("id","root","generation",new Json.Num("1")),Json.map("id","field","generation",new Json.Num("2")),Json.map("id","other","generation",new Json.Num("3")))));return out.toString().getBytes(StandardCharsets.UTF_8);}
    private static final class Fixture implements AutoCloseable {
        final NativeOwnerV2 owner;final Handler queue;final NativeRenderer renderer;final NativeAppearanceViewsV2.NativeField field,other;
        Fixture(){this(false);}Fixture(boolean pair){ConcreteHostProbe.reset();Activity activity=new Activity();FrameLayout root=new FrameLayout(activity);activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);root.hostAttach(new Object());NativeBridge.reset();NativeBridge.preparedPacket=pair?pairPacket(1,"hello","other"):packet(1,"hello");owner=new NativeOwnerV2(activity,root);queue=(Handler)get(owner,"handler");owner.onResume();owner.start();queue.drainAll(6);check(owner.hasCommittedPresentation(),"fixture: "+owner.cleanupLedger().primary());renderer=(NativeRenderer)get(get(owner,"coordinator"),"renderer");field=(NativeAppearanceViewsV2.NativeField)renderer.view("field");other=pair?(NativeAppearanceViewsV2.NativeField)renderer.view("other"):null;field.requestFocus();ConcreteHostProbe.reset();}
        InputConnection connect(){InputConnection connection=field.onCreateInputConnection(new EditorInfo());check(connection!=null,"ordinary creator");return connection;}
        BaseInputConnection target(){return (BaseInputConnection)field.lastConnection;}
        NativeOwnerV2.Fence fence(){return (NativeOwnerV2.Fence)get(owner,"fence");}
        boolean replace(){NativeBridge.preparedPacket=packet(2,"changed");Bundle arguments=new Bundle();arguments.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,"changed");return field.performAccessibilityAction(AccessibilityNodeInfo.ACTION_SET_TEXT,arguments);}
        @Override public void close(){ConcreteHostProbe.hook=null;try{owner.close();queue.drainAll(8);}catch(RuntimeException|Error expected){/* invariant disposition asserted before cleanup */}ConcreteHostProbe.reset();}
    }
    private static void finalBalance(){for(boolean fatal:new boolean[]{false,true})for(boolean callbackCount:new boolean[]{false,true})try(Fixture f=new Fixture()){
        f.connect();int events=NativeBridge.prepareCalls;Fatal first=new Fatal("independent first native fatal");NativeAppearanceViewsV2.Replacement[] operation={null};boolean[] hit={false},busyAtReport={false};
        ConcreteHostProbe.hook=(method,phase)->{
            if(!hit[0]&&method.equals("TextView.setText")&&phase.equals("entry")){
                hit[0]=true;operation[0]=(NativeAppearanceViewsV2.Replacement)get(f.field,"replacement");check(operation[0]!=null&&f.renderer.editorDisposalBusyV2(),"native setter has reservation");
                if(callbackCount)operation[0].callbacks=1;else put(f.field,"depth",1);
                if(fatal)throw first;
            }
            if(method.equals("Handler.post")&&phase.equals("entry"))busyAtReport[0]|=f.renderer.editorDisposalBusyV2();
        };
        Throwable escaped=null;try{f.replace();}catch(RuntimeException|Error expected){escaped=expected;}ConcreteHostProbe.hook=null;
        check(hit[0]&&escaped!=null,"unbalanced suffix surfaced");if(fatal)check(escaped==first,"earlier native fatal wins end invariant failure");
        check(f.fence().terminal&&NativeBridge.prepareCalls==events&&NativeBridge.destroyCalls==0,"no event/owner destroy after unbalanced native suffix");
        check(f.renderer.editorDisposalBusyV2()&&get(f.renderer,"editorReplacement")==operation[0],"exact unbalanced reservation retained");
        check(get(f.field,"replacement")==null&&f.field.record.replacementCallback==null,"field callback permission dropped despite retained terminal custody");
        check(busyAtReport[0],"reporting/scheduling observed before busy clear");
        if(callbackCount)operation[0].callbacks=0;else put(f.field,"depth",0);
        f.field.record.input.replacementEnd(f.field.record,operation[0]);check(!f.renderer.editorDisposalBusyV2()&&NativeBridge.destroyCalls==0,"explicit host repair clears scalars without synchronous owner resume");
    }}
    private static void tupleAfterGetter(){for(boolean changeTarget:new boolean[]{false,true})try(Fixture f=new Fixture()){
        InputConnection adapter=f.connect();BaseInputConnection original=f.target(),foreign=new BaseInputConnection(f.field,true);Object attempt=get(f.field,"attempt");int roster=(Integer)get(f.renderer,"v2RosterCount");boolean[] fired={false};
        ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&method.equals("TextView.getEditableText")&&phase.equals("beforeReturn")&&ConcreteHostProbe.lastEvent().productionFrames.stream().anyMatch(frame->frame.methodName().equals("drain"))){fired[0]=true;if(changeTarget)put(attempt,"target",foreign);else put(f.renderer,"v2RosterCount",0);}};
        Throwable escaped=null;try{adapter.closeConnection();}catch(RuntimeException|Error expected){escaped=expected;}ConcreteHostProbe.hook=null;
        check(fired[0]&&escaped instanceof IllegalStateException,"post-getter exact tuple refusal");check(original.closeCalls==0&&foreign.closeCalls==0,"neither stale nor substituted target dispatched");
        put(f.renderer,"v2RosterCount",roster);put(attempt,"target",original);
    }}
    private static void capturedTarget(){try(Fixture f=new Fixture()){
        InputConnection adapter=f.connect();BaseInputConnection original=f.target(),foreign=new BaseInputConnection(f.field,true);Object attempt=get(f.field,"attempt");boolean[] hit={false};
        ConcreteHostProbe.hook=(method,phase)->{if(!hit[0]&&method.equals("BaseInputConnection.closeConnection")&&phase.equals("entry")){hit[0]=true;check(ConcreteHostProbe.lastEvent().receiver==original,"captured target receives close");put(attempt,"target",foreign);}};
        Throwable escaped=null;try{adapter.closeConnection();}catch(RuntimeException|Error expected){escaped=expected;}ConcreteHostProbe.hook=null;
        check(hit[0]&&escaped instanceof IllegalStateException&&original.closeCalls==1&&foreign.closeCalls==0,"mid-close target substitution cannot redirect or fabricate return");
        check(f.fence().terminal&&get(attempt,"close")==NativeAppearanceViewsV2.NativeField.Close.FAILED_UNCERTAIN,"target corruption honestly uncertain");put(attempt,"target",original);
    }}
    private static void focusHistory(){try(Fixture f=new Fixture()){
        InputConnection old=f.connect();BaseInputConnection target=f.target();f.field.clearFocus();check(target.closeCalls==1&&!old.beginBatchEdit()&&!f.fence().terminal,"completed actual focus loss retires only predecessor");
        boolean result=f.replace();System.out.println("OBSERVATION previously-focused-unfocused ACTION_SET_TEXT result="+result+" focusLost="+get(f.field,"focusLost")+" hasFocus="+f.field.hasFocus()+" hasWindowFocus="+f.field.hasWindowFocus()+" terminal="+f.fence().terminal+" value="+f.field.getText()+" oldCloseCalls="+target.closeCalls);
    }}
    private static void blurredPair(boolean replacement){try(Fixture f=new Fixture(true)){
        InputConnection old=f.connect();BaseInputConnection oldTarget=f.target();Object oldEditable=f.field.getText();f.field.clearFocus();f.other.requestFocus();InputConnection healthy=f.other.onCreateInputConnection(new EditorInfo());check(healthy!=null&&oldTarget.closeCalls==1&&!old.beginBatchEdit()&&!f.fence().terminal,"A old close completes before focused B connection");BaseInputConnection target=(BaseInputConnection)f.other.lastConnection;
        check(!f.field.hasFocus()&&f.other.hasFocus()&&f.field.hasWindowFocus(),"source-faithful previously-focused A and focused B");int events=NativeBridge.prepareCalls;boolean returned=false;Throwable escaped=null;
        if(replacement){Bundle args=new Bundle();args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,"updated");NativeBridge.preparedPacket=pairPacket(2,"updated","other");try{returned=f.field.performAccessibilityAction(AccessibilityNodeInfo.ACTION_SET_TEXT,args);}catch(RuntimeException|Error failure){escaped=failure;}}
        else {check(healthy.setSelection(5,5),"ordinary B explicit cursor");NativeBridge.preparedPacket=pairPacket(2,"hello","otherz");try{returned=healthy.commitText("z",1);}catch(RuntimeException|Error failure){escaped=failure;}}
        System.out.println("REQUIRED_COMPATIBILITY_OBSERVATION route="+(replacement?"blurred-A-replacement":"focused-B-IME-compatible-echo")+" returned="+returned+" escaped="+escaped+" A.focusLost="+get(f.field,"focusLost")+" A.value="+f.field.getText()+" A.sameEditable="+(f.field.getText()==oldEditable)+" A.closeCalls="+oldTarget.closeCalls+" B.value="+f.other.getText()+" B.closeCalls="+target.closeCalls+" terminal="+f.fence().terminal+" eventPrepareDelta="+(NativeBridge.prepareCalls-events));
        check(returned&&escaped==null&&!f.fence().terminal,"required ordinary compatibility after completed A focus loss");
        check(oldTarget.closeCalls==1&&!old.beginBatchEdit()&&target.closeCalls==0&&healthy.setSelection(0,0),"old A stays revoked and B remains healthy");
        check(NativeBridge.prepareCalls==events+1,"exactly one ordinary synchronous event");
    }}
    public static void main(String[] args)throws Exception{descriptor=Files.readAllBytes(Path.of(args[1]));switch(args[0]){case "final-balance"->finalBalance();case "tuple-after-getter"->tupleAfterGetter();case "captured-target"->capturedTarget();case "focus-history-observation"->focusHistory();case "blurred-A-replacement"->blurredPair(true);case "focused-B-echo-after-A-blur"->blurredPair(false);default->throw new IllegalArgumentException(args[0]);}System.out.println("PASS independent reflected "+args[0]+" / "+checks+" assertions");}
}
