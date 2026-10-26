package dev.mixer.android;

import android.os.Bundle;
import android.text.Annotation;
import android.text.Editable;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/** Prepared before correction access. Compile only until root releases its exact seal. */
public final class FocusHistoryControls {
    private FocusHistoryControls() {}
    private static int assertions;
    private static final class Fatal extends Error {private static final long serialVersionUID=1L;Fatal(String text){super(text);}}
    private static final List<String> trace=new ArrayList<>();
    private static void check(boolean value,String message){assertions++;if(!value)throw new AssertionError(message+" trace="+trace);}
    private static void note(String text){if(trace.size()<128)trace.add(text);}
    private static Object get(Object target,String name){try{Field field=target.getClass().getDeclaredField(name);field.setAccessible(true);return field.get(target);}catch(ReflectiveOperationException failure){throw new AssertionError("future hook binding "+name,failure);}}
    private static void put(Object target,String name,Object value){try{Field field=target.getClass().getDeclaredField(name);field.setAccessible(true);field.set(target,value);}catch(ReflectiveOperationException failure){throw new AssertionError("future hook binding "+name,failure);}}
    private static Object invoke(Object target,Method method,Object... arguments){try{method.setAccessible(true);return method.invoke(target,arguments);}catch(InvocationTargetException failure){if(failure.getCause() instanceof Error fatal)throw fatal;if(failure.getCause() instanceof RuntimeException ordinary)throw ordinary;throw new AssertionError(failure.getCause());}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static Object input(NativeAppearanceViewsV2.Record record,String name,Object... args){for(Method method:record.input.getClass().getDeclaredMethods())if(method.getName().equals(name)&&method.getParameterCount()==args.length)return invoke(record.input,method,args);throw new AssertionError("selected future Input method not found: "+name);}
    private static Object preservation(NativeAppearanceViewsV2.Record record){Object selected=null;for(Field field:record.getClass().getDeclaredFields())if(field.getType().getSimpleName().equals("FieldPreservation")){try{field.setAccessible(true);Object value=field.get(record);if(value!=null){check(selected==null,"unique exact preservation binding");selected=value;}}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}return selected;}
    private static void callback(NativeAppearanceViewsV2.NativeField field,String name,Class<?>[] signature,Object... args){try{invoke(field,field.getClass().getDeclaredMethod(name,signature),args);}catch(NoSuchMethodException failure){throw new AssertionError(failure);}}
    private static void focusLoss(NativeAppearanceViewsV2.NativeField field,boolean gain){callback(field,"onFocusChanged",new Class<?>[]{boolean.class,int.class,android.graphics.Rect.class},false,0,null);if(gain)callback(field,"onFocusChanged",new Class<?>[]{boolean.class,int.class,android.graphics.Rect.class},true,0,null);}
    private static long loss(NativeAppearanceViewsV2.Record record){return (Long)input(record,"editorLossObservation");}
    private static Field namedField(Object target,Class<?> type,String fragment){Field selected=null;for(Field field:target.getClass().getDeclaredFields())if(field.getType()==type&&field.getName().toLowerCase(java.util.Locale.ROOT).contains(fragment)){check(selected==null,"unique future invariant hook "+fragment);selected=field;}check(selected!=null,"future private hook needs frozen-source binding: "+fragment);selected.setAccessible(true);return selected;}
    private static void fieldSet(Object target,Field field,Object value){try{field.set(target,value);}catch(IllegalAccessException failure){throw new AssertionError(failure);}}
    private static byte[] packet(long revision,String a,String b){try{Method method=AdditionalReplacementControls.class.getDeclaredMethod("pairPacket",long.class,String.class,String.class);return (byte[])invoke(null,method,revision,a,b);}catch(NoSuchMethodException failure){throw new AssertionError(failure);}}
    private static Bundle payload(CharSequence text){Bundle result=new Bundle();result.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,text);return result;}
    private static final class Fixture implements AutoCloseable {
        final AutoCloseable base;
        final NativeOwnerV2 owner;final NativeRenderer renderer;
        final NativeAppearanceViewsV2.NativeField a,b;
        InputConnection oldA,liveB;BaseInputConnection targetA,targetB;
        Fixture(){try{Class<?> type=Class.forName("dev.mixer.android.AdditionalReplacementControls$Fixture");Constructor<?> constructor=type.getDeclaredConstructor(boolean.class);constructor.setAccessible(true);base=(AutoCloseable)constructor.newInstance(true);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}owner=(NativeOwnerV2)get(base,"owner");renderer=(NativeRenderer)get(base,"renderer");a=(NativeAppearanceViewsV2.NativeField)get(base,"field");b=(NativeAppearanceViewsV2.NativeField)get(base,"other");}
        void connectA(){oldA=a.onCreateInputConnection(new EditorInfo());check(oldA!=null,"A native connection");targetA=(BaseInputConnection)a.lastConnection;}
        void settleA(){connectA();a.clearFocus();b.requestFocus();liveB=b.onCreateInputConnection(new EditorInfo());check(liveB!=null&&targetA.closeCalls==1&&!oldA.beginBatchEdit(),"settled retired A and healthy B");targetB=(BaseInputConnection)b.lastConnection;}
        NativeOwnerV2.Fence fence(){return (NativeOwnerV2.Fence)get(owner,"fence");}
        boolean replace(CharSequence value){NativeBridge.preparedPacket=packet(2,value.toString(),"other");return a.performAccessibilityAction(AccessibilityNodeInfo.ACTION_SET_TEXT,payload(value));}
        @Override public void close(){ConcreteHostProbe.hook=null;try{base.close();}catch(RuntimeException|Error expected){/* actual disposition checked before fixture retirement */}catch(Exception unexpected){throw new AssertionError(unexpected);}}
    }
    private static void priorFocusValues(){for(String text:new String[]{"updated","hello",""})try(Fixture fixture=new Fixture()){
        fixture.settleA();Object original=fixture.a.getText();int events=NativeBridge.prepareCalls;
        Editable proposal=new Editable(text);Annotation annotation=null;if(!text.isEmpty()){annotation=new Annotation("independent","kept");proposal.setSpan(annotation,0,text.length(),18);}
        check(fixture.replace(proposal),"ordinary previously-focused replacement including same/empty");check(fixture.a.getText()!=original&&fixture.a.getText().toString().equals(text),"one native Enew and captured value");
        check(fixture.a.getSelectionStart()==text.length()&&fixture.a.getSelectionEnd()==text.length(),"native final selection");check(NativeBridge.prepareCalls==events+1&&!fixture.fence().terminal,"one ordinary successful event");
        check((Boolean)get(fixture.a,"focusLost")&&!fixture.a.hasFocus()&&!fixture.oldA.setSelection(0,0)&&fixture.a.onCreateInputConnection(new EditorInfo())==null,"focus history and old revocation retained; new IME refused");
        check(fixture.targetA.closeCalls==1&&fixture.targetB.closeCalls==0&&fixture.liveB.setSelection(0,0),"B healthy after completed replacement");if(annotation!=null){Annotation[] kept=fixture.a.getText().getSpans(0,text.length(),Annotation.class);check(kept.length==1&&kept[0].getKey().equals("independent")&&kept[0].getValue().equals("kept")&&fixture.a.getText().getSpanStart(kept[0])==0&&fixture.a.getText().getSpanEnd(kept[0])==text.length()&&fixture.a.getText().getSpanFlags(kept[0])==18,"Annotation semantics preserved without extra identity requirement");}
    }}
    private static void coexistence(){try(Fixture fixture=new Fixture()){
        fixture.settleA();Object editable=fixture.a.getText();boolean[] scopeSeen={false},callbackSeen={false};Object[] scope={null};
        ConcreteHostProbe.hook=(method,phase)->{var hit=ConcreteHostProbe.lastEvent();Object active=preservation(fixture.a.record);
            if(!scopeSeen[0]&&active!=null&&hit.receiver==fixture.a&&method.equals("View.invalidate")&&phase.equals("entry")){
                scopeSeen[0]=true;scope[0]=active;note("A preservation while B editor active count="+get(fixture.renderer,"outstandingEditorNativeCalls"));
                check(fixture.b.record.editorCallbackLease!=null&&fixture.a.record.editorCallbackLease==null,"distinct B editor and A field routes");check((Integer)get(fixture.renderer,"outstandingEditorNativeCalls")>=2,"A count coexists with B lease");
                for(Field field:active.getClass().getDeclaredFields())check(!InputConnection.class.isAssignableFrom(field.getType())&&!NativeAppearanceViewsV2.EditorLease.class.isAssignableFrom(field.getType()),"field scope has no target/editor lease");
                callback(fixture.a,"drawableStateChanged",new Class<?>[]{});
            }
            if(scopeSeen[0]&&!callbackSeen[0]&&hit.receiver==fixture.a&&method.equals("View.drawableStateChanged")&&phase.equals("entry")){
                callbackSeen[0]=true;check(preservation(fixture.a.record)==scope[0],"exact scope in callback");NativeAppearanceViewsV2.Mutation mutation=fixture.a.record.mutation();mutation.require();
                boolean refused=false;try{mutation.requireMutation();}catch(IllegalStateException expected){refused=true;}check(refused,"field callback cannot authorize bind/layout");int before=ConcreteHostProbe.events().size();check(!fixture.oldA.beginBatchEdit()&&fixture.a.onCreateInputConnection(new EditorInfo())==null,"field scope never revives target/creator");check(ConcreteHostProbe.events().size()==before,"retired target refusal before native work");
            }
        };
        check(fixture.liveB.setSelection(5,5),"B explicit cursor");NativeBridge.preparedPacket=packet(2,"hello","otherz");check(fixture.liveB.commitText("z",1),"B compatible ordinary echo with preservation");ConcreteHostProbe.hook=null;
        check(scopeSeen[0]&&callbackSeen[0]&&fixture.a.getText()==editable,"inactive A exact buffer preserved through callback/layout");check(preservation(fixture.a.record)==null&&(Integer)get(fixture.renderer,"outstandingEditorNativeCalls")==0&&!fixture.renderer.editorDisposalBusyV2(),"both exact counts balanced");
    }}
    private static void restore(boolean invalidate,boolean foreignToken){try(Fixture fixture=new Fixture()){
        fixture.settleA();Object editable=fixture.a.getText();int start=fixture.a.getSelectionStart(),end=fixture.a.getSelectionEnd();boolean[] forward={false},restoring={false};Object[] scope={null};int[] aSetters={0};
        ConcreteHostProbe.hook=(method,phase)->{var hit=ConcreteHostProbe.lastEvent();if(hit.receiver==fixture.a&&method.equals("TextView.setText")&&phase.equals("entry"))aSetters[0]++;
            Object active=preservation(fixture.a.record);if(active!=null&&hit.receiver==fixture.a){boolean rollback=hit.productionFrames.stream().anyMatch(frame->frame.methodName().equals("restoreV2"));if(rollback){restoring[0]=true;check(active==scope[0],"restore cannot mint a fresh scope");}else if(!forward[0]&&method.equals("View.invalidate")&&phase.equals("entry")){forward[0]=true;scope[0]=active;if(invalidate)fixture.fence().operation=foreignToken?fixture.fence().presentation:null;}}
        };
        if(!invalidate)fixture.renderer.testFaultV2(2,false);check(fixture.liveB.setSelection(5,5),"B explicit cursor");NativeBridge.preparedPacket=packet(2,"hello","otherz");boolean result=false;try{result=fixture.liveB.commitText("z",1);}catch(RuntimeException|Error expected){note("restore path escaped "+expected.getClass().getSimpleName());}ConcreteHostProbe.hook=null;
        check(forward[0]&&!result,"controlled failed transaction reached A forward preservation");check(fixture.a.getText()==editable&&fixture.a.getText().toString().equals("hello")&&fixture.a.getSelectionStart()==start&&fixture.a.getSelectionEnd()==end&&aSetters[0]==0,"inactive A restoration never rebuilds its buffer");
        if(invalidate)check(!restoring[0]&&fixture.fence().terminal,"lost original refuses native restoration honestly");else check(restoring[0],"eligible restore exercised under captured scope");
    }}
    private static void lossPhases(boolean settled){for(String stage:new String[]{"ADMISSION","SNAPSHOTTING","CLOSING","NATIVE","FINAL"})for(boolean foreign:new boolean[]{false,true})for(boolean gain:new boolean[]{false,true})try(Fixture fixture=new Fixture()){
        if(settled)fixture.settleA();else fixture.connectA();NativeAppearanceViewsV2.NativeField losing=foreign?fixture.b:fixture.a;long before=loss(fixture.a.record);int events=NativeBridge.prepareCalls;boolean[] fired={false};
        Runnable lose=()->{if(fired[0])return;fired[0]=true;note(stage+" foreign="+foreign+" gain="+gain);focusLoss(losing,gain);if(gain)focusLoss(losing,false);};
        ConcreteHostProbe.hook=(method,phase)->{if(fired[0])return;var hit=ConcreteHostProbe.lastEvent();Object operation=get(fixture.a,"replacement");boolean selected=switch(stage){case "ADMISSION"->hit.receiver==fixture.a&&method.equals("View.isAttachedToWindow")&&phase.equals("beforeReturn")&&operation==null;case "CLOSING"->hit.receiver==fixture.targetA&&method.equals("BaseInputConnection.closeConnection")&&phase.equals("entry")||hit.receiver==fixture.a&&method.equals("TextView.getEditableText")&&phase.equals("beforeReturn")&&operation!=null&&get(operation,"stage").toString().equals("CLOSING");case "NATIVE"->hit.receiver==fixture.a&&method.equals("TextView.setText")&&phase.equals("entry");case "FINAL"->hit.receiver==fixture.a&&method.equals("TextView.getEditableText")&&phase.equals("beforeReturn")&&operation!=null&&!(Boolean)get(operation,"nativeExecuting")&&get(operation,"stage").toString().equals("NATIVE");default->false;};if(selected)lose.run();};
        CharSequence value=stage.equals("SNAPSHOTTING")?new CharSequence(){public int length(){return 7;}public char charAt(int at){return "updated".charAt(at);}public CharSequence subSequence(int a,int b){return "updated".substring(a,b);}@Override public String toString(){lose.run();return "updated";}}:"updated";
        NativeBridge.preparedPacket=packet(2,"updated","other");boolean result=false;try{result=fixture.a.performAccessibilityAction(AccessibilityNodeInfo.ACTION_SET_TEXT,payload(value));}catch(RuntimeException|Error expected){note("loss escaped "+expected.getClass().getSimpleName());}ConcreteHostProbe.hook=null;
        check(fired[0]&&!result&&NativeBridge.prepareCalls==events,"new own/foreign loss cannot produce successful replacement/event");check(loss(fixture.a.record)>before,"actual loss observation increases, gain cannot erase");
    }}
    private static void observedHooks(){for(String hook:new String[]{"focus","windowFocus","windowVisibility","visibility","aggregate","detach"})for(boolean foreign:new boolean[]{false,true})try(Fixture fixture=new Fixture()){
        NativeAppearanceViewsV2.NativeField field=foreign?fixture.b:fixture.a;long before=loss(field.record);Runnable lose=switch(hook){case "focus"->()->focusLoss(field,false);case "windowFocus"->()->field.onWindowFocusChanged(false);case "windowVisibility"->()->callback(field,"onWindowVisibilityChanged",new Class<?>[]{int.class},android.view.View.INVISIBLE);case "visibility"->()->callback(field,"onVisibilityChanged",new Class<?>[]{android.view.View.class,int.class},field,android.view.View.INVISIBLE);case "aggregate"->()->field.onVisibilityAggregated(false);default->()->callback(field,"onDetachedFromWindow",new Class<?>[]{});};
        lose.run();long once=loss(field.record);lose.run();long twice=loss(field.record);check(once>before&&twice>once,"every actual own/foreign repeated lifecycle hook increments even already latched: "+hook);
    }}
    private static void eventReentry(){try(Fixture fixture=new Fixture()){
        fixture.settleA();Object[] completed={null};boolean[] reentered={false},sent={false};int[] afterSend={0};int events=NativeBridge.prepareCalls;
        ConcreteHostProbe.hook=(method,phase)->{var hit=ConcreteHostProbe.lastEvent();Object operation=get(fixture.a,"replacement");if(operation!=null)completed[0]=operation;
            if(!reentered[0]&&hit.receiver==fixture.a&&method.equals("View.hasWindowFocus")&&phase.equals("beforeReturn")&&hit.productionFrames.stream().anyMatch(frame->frame.methodName().equals("replacementEvent"))){reentered[0]=true;int count=ConcreteHostProbe.events().size();try{input(fixture.a.record,"replacementEvent",fixture.a.record,completed[0]);}catch(RuntimeException expected){note("nested event refused");}check(ConcreteHostProbe.events().size()==count,"completed event reentry refused before native observations");}
            if(method.equals("NativeBridge.prepareV2")&&phase.equals("entry"))sent[0]=true;
            if(sent[0]&&hit.receiver==fixture.a&&!hit.productionFrames.stream().anyMatch(frame->frame.className().equals("dev.mixer.android.NativeOwnerV2")&&frame.methodName().equals("nativeInput")))afterSend[0]++;
        };
        check(fixture.replace("updated"),"outer completed replacement survives reentry");ConcreteHostProbe.hook=null;check(reentered[0]&&NativeBridge.prepareCalls==events+1&&afterSend[0]==0&&!fixture.fence().terminal,"one event and scalar-only native suffix return");int before=ConcreteHostProbe.events().size();try{input(fixture.a.record,"replacementEvent",fixture.a.record,completed[0]);}catch(RuntimeException expected){note("second event refused");}check(ConcreteHostProbe.events().size()==before&&NativeBridge.prepareCalls==events+1,"one-shot event cannot replay");
    }}
    private static void eventPostgetter(){for(String mode:new String[]{"loss","roster","original"})try(Fixture fixture=new Fixture()){
        fixture.settleA();boolean[] fired={false};int events=NativeBridge.prepareCalls;int roster=(Integer)get(fixture.renderer,"v2RosterCount");
        ConcreteHostProbe.hook=(method,phase)->{var hit=ConcreteHostProbe.lastEvent();if(!fired[0]&&hit.receiver==fixture.a&&method.equals("View.hasWindowFocus")&&phase.equals("beforeReturn")&&hit.productionFrames.stream().anyMatch(frame->frame.methodName().equals("replacementEvent"))){fired[0]=true;note("post-open invalidation "+mode);switch(mode){case "loss"->focusLoss(fixture.a,false);case "roster"->put(fixture.renderer,"v2RosterCount",0);default->fixture.fence().presentation=null;}}};
        boolean result=false;try{result=fixture.replace("updated");}catch(RuntimeException|Error expected){note("postgetter uncertainty "+expected.getClass().getSimpleName());}ConcreteHostProbe.hook=null;put(fixture.renderer,"v2RosterCount",roster);
        check(fired[0]&&!result&&fixture.fence().terminal&&NativeBridge.prepareCalls==events,"completed mutation with post-getter authority loss is honest uncertainty/no event");check(fixture.targetA.closeCalls==1,"old target never reclosed against Enew");
    }}
    private static void scopeImbalance(){for(boolean fatal:new boolean[]{false,true})try(Fixture fixture=new Fixture()){
        fixture.settleA();Fatal first=new Fatal("independent preservation native first fatal");boolean[] entered={false},corrupt={false};Object[] captured={null};
        ConcreteHostProbe.hook=(method,phase)->{var hit=ConcreteHostProbe.lastEvent();Object active=preservation(fixture.a.record);
            if(!entered[0]&&active!=null&&hit.receiver==fixture.a&&method.equals("View.invalidate")&&phase.equals("entry")){entered[0]=true;captured[0]=active;callback(fixture.a,"drawableStateChanged",new Class<?>[]{});}
            if(entered[0]&&!corrupt[0]&&hit.receiver==fixture.a&&method.equals("View.drawableStateChanged")&&phase.equals("entry")){corrupt[0]=true;Field callbacks=namedField(captured[0],int.class,"callback");try{callbacks.setInt(captured[0],callbacks.getInt(captured[0])+1);}catch(IllegalAccessException failure){throw new AssertionError(failure);}if(fatal)throw first;}
        };
        fixture.liveB.setSelection(5,5);NativeBridge.preparedPacket=packet(2,"hello","otherz");Throwable escaped=null;try{fixture.liveB.commitText("z",1);}catch(RuntimeException|Error expected){escaped=expected;}ConcreteHostProbe.hook=null;
        check(entered[0]&&corrupt[0]&&fixture.fence().terminal,"actual field suffix imbalance recorded");if(fatal)check(escaped==first,"first native fatal survives later end imbalance");check(fixture.renderer.editorDisposalBusyV2()&&(Integer)get(fixture.renderer,"outstandingEditorNativeCalls")>0&&NativeBridge.destroyCalls==0,"unbalanced exact scope retains counted terminal custody");check(preservation(fixture.a.record)==null,"failed scope retains custody without callback authority");
    }}
    private static void exhaustion(){for(boolean nativeStage:new boolean[]{false,true})for(boolean fatal:new boolean[]{false,true})try(Fixture fixture=new Fixture()){
        fixture.connectA();Field counter=namedField(fixture.renderer,long.class,"loss");fieldSet(fixture.renderer,counter,Long.MAX_VALUE);check(loss(fixture.a.record)==Long.MAX_VALUE,"host invariant set at exact exhaustion boundary");boolean[] fired={false},superSeen={false};Fatal first=new Fatal("independent exhausted-marker native superclass fatal");int events=NativeBridge.prepareCalls;
        Runnable lose=()->{if(!fired[0]){fired[0]=true;focusLoss(fixture.a,false);}};
        ConcreteHostProbe.hook=(method,phase)->{var hit=ConcreteHostProbe.lastEvent();if(nativeStage&&!fired[0]&&hit.receiver==fixture.a&&method.equals("TextView.setText")&&phase.equals("entry"))lose.run();if(fired[0]&&hit.receiver==fixture.a&&method.equals("View.onFocusChanged")&&phase.equals("entry")){superSeen[0]=true;if(fatal)throw first;}};
        CharSequence proposal=nativeStage?"updated":new CharSequence(){public int length(){return 7;}public char charAt(int at){return "updated".charAt(at);}public CharSequence subSequence(int a,int b){return "updated".substring(a,b);}@Override public String toString(){lose.run();return "updated";}};
        NativeBridge.preparedPacket=packet(2,"updated","other");boolean result=false;Throwable escaped=null;try{result=fixture.a.performAccessibilityAction(AccessibilityNodeInfo.ACTION_SET_TEXT,payload(proposal));}catch(RuntimeException|Error expected){escaped=expected;}ConcreteHostProbe.hook=null;
        check(fired[0]&&superSeen[0]&&!result&&fixture.fence().terminal&&NativeBridge.prepareCalls==events,"exhaustion preserves exact superclass suffix and forbids success/event");check(loss(fixture.a.record)==Long.MAX_VALUE&&(Boolean)get(fixture.a,"focusLost"),"no wrap, actual denial retained despite exhaustion");if(fatal)check(escaped==first,"native superclass fatal retains fatal precedence over scalar exhaustion");
    }}
    public static void main(String[] args)throws Exception{Field descriptor=AdditionalReplacementControls.class.getDeclaredField("descriptor");descriptor.setAccessible(true);descriptor.set(null,Files.readAllBytes(Path.of(args[1])));switch(args[0]){case "prior-focus-values"->priorFocusValues();case "coexistence"->coexistence();case "eligible-restore"->restore(false,false);case "lost-original-restore"->restore(true,false);case "foreign-token-restore"->restore(true,true);case "loss-phases"->lossPhases(false);case "settled-loss-phases"->lossPhases(true);case "observed-hooks"->observedHooks();case "event-reentry"->eventReentry();case "event-postgetter"->eventPostgetter();case "scope-imbalance"->scopeImbalance();case "exhaustion"->exhaustion();default->throw new IllegalArgumentException(args[0]);}System.out.println("PASS focus-history actual-source control "+args[0]+" / "+assertions+" assertions; trace="+trace);}
}
