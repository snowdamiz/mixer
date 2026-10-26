package dev.mixer.android;

import android.app.Activity;
import android.os.Handler;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.EditText;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.ArrayList;

/** Independent actual-subject focus race control. No product source overlays or minted authority. */
public final class IndependentOwnerFocusReview {
    private IndependentOwnerFocusReview() {}
    private static Object field(Object owner,String name) {
        try { Field f=owner.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(owner); }
        catch(ReflectiveOperationException error){throw new AssertionError(error);}
    }
    private static void check(boolean value,String description) { if(!value)throw new AssertionError(description); }
    private static java.lang.reflect.Method method(Class<?> type,String name,Class<?>...parameters)throws Exception{
        var result=type.getDeclaredMethod(name,parameters);result.setAccessible(true);return result;
    }
    private static void refuses(String name,java.lang.reflect.Executable executable,Object receiver,Object...arguments)throws Exception{
        int before=ConcreteHostProbe.events().size();Throwable original=null;
        try{if(executable instanceof java.lang.reflect.Method method)method.invoke(receiver,arguments);else ((java.lang.reflect.Constructor<?>)executable).newInstance(arguments);}
        catch(java.lang.reflect.InvocationTargetException failure){original=failure.getCause();}
        check(original instanceof IllegalStateException,name+" refuses mode/stale scope itself");
        check(ConcreteHostProbe.events().size()==before,name+" refuses before any native leaf");
    }
    private static String frames(List<ConcreteHostProbe.Site> sites) {
        StringBuilder out=new StringBuilder("[");
        for(var site:sites){if(out.length()>1)out.append(',');out.append('"').append(site.className()).append('.').append(site.methodName()).append(site.descriptor()).append('@').append(site.bytecodeIndex()).append(':').append(site.line()).append('"');}
        return out.append(']').toString();
    }
    public static void main(String[] args)throws Exception {
        Path inputs=Path.of(args[0]);String mode=args[1];
        ConcreteHostProbe.reset();NativeBridge.reset();
        Activity activity=new Activity();FrameLayout root=new FrameLayout(activity);
        root.layout(0,0,320,480);root.hostAttach(new Object());
        activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,Files.readAllBytes(inputs.resolve("independent-descriptor.json")));
        NativeBridge.preparedPacket=Files.readAllBytes(inputs.resolve("independent-packet-1.json"));
        if(mode.equals("helper-negative"))NativeBridge.preparedPacket=Files.readAllBytes(inputs.resolve("independent-helper-packet.json"));
        NativeOwnerV2 owner=new NativeOwnerV2(activity,root);
        try {
            if(mode.startsWith("post-reentry-")){
                Handler ownedHandler=(Handler)field(owner,"handler");
                OwnerLifecycleV2 actualCore=(OwnerLifecycleV2)field(owner,"core");
                String phase=mode.endsWith("entry")&&!mode.endsWith("return-entry")?"entry":"beforeReturn";
                boolean removeFails=mode.contains("remove-fatal");
                Error removalFatal=new AssertionError("independent actual removal fatal");
                boolean[] reentered={false},pendingAtCallback={false},deferredAtCallback={false};String[] callbackTrace={"[]"};
                ConcreteHostProbe.hook=(method,point)->{
                    var event=ConcreteHostProbe.lastEvent();
                    if(method.equals("Handler.post")&&point.equals(phase)&&event.receiver==ownedHandler&&!reentered[0]){
                        reentered[0]=true;callbackTrace[0]=frames(event.productionFrames);
                        if(removeFails)ownedHandler.removeFailure=removalFatal;
                        owner.close();
                        pendingAtCallback[0]=actualCore.snapshot().cancelPending();
                        deferredAtCallback[0]=owner.cleanupLedger().handler()==NativeOwnerV2.Outcome.DEFERRED;
                    }
                };
                Error escaped=null;try{owner.start();}catch(Error error){escaped=error;}
                ConcreteHostProbe.hook=null;ownedHandler.removeFailure=null;
                int retained=ownedHandler.queued();
                System.out.println("{\"mode\":\""+mode+"\",\"phase\":\""+phase+"\",\"actualReentry\":"+reentered[0]+",\"actualCancelPendingInsidePost\":"+pendingAtCallback[0]+",\"handlerDeferredInsidePost\":"+deferredAtCallback[0]+",\"actualCancelPendingAfterPost\":"+actualCore.snapshot().cancelPending()+",\"actualQueuedAfterPost\":"+retained+",\"actualRemoveCalls\":"+ownedHandler.removeCalls+",\"handlerLedger\":\""+owner.cleanupLedger().handler()+"\",\"sameFatalEscaped\":"+(escaped==removalFatal)+",\"JNIcreateCalls\":"+NativeBridge.createCalls+",\"actualPostFrames\":"+callbackTrace[0]+"}");
                check(reentered[0]&&pendingAtCallback[0]&&deferredAtCallback[0],"actual post reentry retains exact uncompleted cleanup token until acquisition unwinds");
                check(!actualCore.snapshot().cancelPending()&&ownedHandler.removeCalls==1,"deferred exact cleanup token completes after one removal attempt");
                check(actualCore.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED&&NativeBridge.createCalls==0,"post cancellation cannot start operation");
                if(removeFails){check(escaped==removalFatal&&owner.cleanupLedger().handler()==NativeOwnerV2.Outcome.FAILED_UNCERTAIN&&owner.cleanupLedger().handlerFailure()==removalFatal&&retained==1,"uncertain removal preserves original fatal and retained stale work");}
                else check(escaped==null&&owner.cleanupLedger().handler()==NativeOwnerV2.Outcome.RETURNED&&retained==0,"returned removal leaves no owned queued work");
                ownedHandler.drainAll(1);check(NativeBridge.createCalls==0,"uncertain retained stale delivery is inert");
                return;
            }
            if(mode.equals("registration-failure")){
                RuntimeException primary=new IllegalStateException("independent uncertain final registration");
                Error fatal=new AssertionError("independent cleanup fatal");
                String[] removals={"Context.unregisterComponentCallbacks","View.removeOnLayoutChangeListener","View.removeOnAttachStateChangeListener","ViewTreeObserver.removeOnWindowFocusChangeListener","View.setOnApplyWindowInsetsListener","UiModeManager.removeContrastChangeListener","AccessibilityManager.removeHighContrastTextStateChangeListener","ContentResolver.unregisterContentObserver"};
                boolean[] addThrew={false},removeThrew={false};int[] attempts=new int[8];String[] addTrace={"[]"},removeTrace={"[]"};
                ConcreteHostProbe.hook=(method,phase)->{
                    var event=ConcreteHostProbe.lastEvent();
                    if(method.equals("ContentResolver.registerContentObserver")&&phase.equals("beforeReturn")&&!addThrew[0]){addThrew[0]=true;addTrace[0]=frames(event.productionFrames);throw primary;}
                    if(phase.equals("entry")&&event.productionFrames.stream().anyMatch(site->site.className().equals("dev.mixer.android.NativeEnvironmentV2$Observer")&&site.methodName().equals("cleanupAll"))){
                        for(int i=0;i<removals.length;i++)if(method.equals(removals[i]))attempts[i]++;
                        if(method.equals(removals[1])&&!removeThrew[0]){removeThrew[0]=true;removeTrace[0]=frames(event.productionFrames);throw fatal;}
                    }
                };
                Error escaped=null;try{owner.start();}catch(Error error){escaped=error;}
                ConcreteHostProbe.hook=null;
                NativeEnvironmentV2.Observer actualObserver=(NativeEnvironmentV2.Observer)field(owner,"observer");
                OwnerLifecycleV2 actualCore=(OwnerLifecycleV2)field(owner,"core");
                int[] states=new int[8];for(int i=0;i<8;i++)states[i]=actualObserver.cleanupLedger().state(i);
                System.out.println("{\"mode\":\"registration-failure\",\"allEightActualRemovalAttempts\":\""+java.util.Arrays.toString(attempts)+"\",\"actualObserverSlots\":\""+java.util.Arrays.toString(states)+"\",\"sameOwnerPrimary\":"+(owner.cleanupLedger().primary()==primary)+",\"sameOwnerFirstFatal\":"+(owner.cleanupLedger().firstFatal()==fatal)+",\"sameEscapedFatal\":"+(escaped==fatal)+",\"sameObserverPrimary\":"+(actualObserver.cleanupLedger().primary()==primary)+",\"sameObserverFirstFatal\":"+(actualObserver.cleanupLedger().firstFatal()==fatal)+",\"actualCorePhase\":\""+actualCore.snapshot().phase()+"\",\"JNIcreateCalls\":"+NativeBridge.createCalls+",\"uncertainAddFrames\":"+addTrace[0]+",\"failedRemovalFrames\":"+removeTrace[0]+"}");
                check(addThrew[0]&&removeThrew[0],"actual uncertain acquisition and fatal cleanup callbacks reached");
                check(escaped==fatal&&owner.cleanupLedger().primary()==primary&&owner.cleanupLedger().firstFatal()==fatal,"owner keeps independent first primary and fatal identities");
                check(actualObserver.cleanupLedger().primary()==primary&&actualObserver.cleanupLedger().firstFatal()==fatal,"observer keeps primary and fatal separately");
                for(int i=0;i<8;i++){check(attempts[i]==1,"each exact observer removal attempted once including uncertain acquisition");check(states[i]==(i==1?NativeEnvironmentV2.Observer.FAILED_UNCERTAIN:NativeEnvironmentV2.Observer.RETURNED),"actual fixed observer slot records own removal disposition");}
                check(actualCore.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED&&NativeBridge.createCalls==0,"registration failure never opens engine");
                return;
            }
            if(mode.equals("post-failure")){
                Handler ownedHandler=(Handler)field(owner,"handler");RuntimeException failure=new IllegalStateException("independent post-after-enqueue failure");boolean[] threw={false};
                ConcreteHostProbe.hook=(method,phase)->{
                    if(method.equals("Handler.post")&&phase.equals("beforeReturn")&&ConcreteHostProbe.lastEvent().receiver==ownedHandler&&!threw[0]){threw[0]=true;throw failure;}
                };
                owner.start();ConcreteHostProbe.hook=null;
                OwnerLifecycleV2 actualCore=(OwnerLifecycleV2)field(owner,"core");
                int queuedBeforeDelivery=ownedHandler.queued();int removes=ownedHandler.removeCalls;
                System.out.println("{\"mode\":\"post-failure\",\"threwAfterActualEnqueue\":"+threw[0]+",\"actualQueuedWorkAfterRetirement\":"+queuedBeforeDelivery+",\"actualRemoveCalls\":"+removes+",\"handlerLedger\":\""+owner.cleanupLedger().handler()+"\",\"samePrimaryFailure\":"+(owner.cleanupLedger().primary()==failure)+",\"actualCorePhase\":\""+actualCore.snapshot().phase()+"\",\"JNIcreateCalls\":"+NativeBridge.createCalls+"}");
                check(threw[0]&&actualCore.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED,"actual post failure terminally processed");
                check(owner.cleanupLedger().primary()==failure,"post failure retained by identity");
                ownedHandler.drainAll(1);check(NativeBridge.createCalls==0,"retained stale delivery cannot create session");
                check(removes==1,"possibly-enqueued owned work requires one real cancellation attempt before RETURNED");
                return;
            }
            owner.start();owner.onResume();Handler handler=(Handler)field(owner,"handler");
            check(handler.drainOne(),"one actual initial drain");
            if(!owner.hasCommittedPresentation()&&owner.cleanupLedger().primary()!=null){System.out.println("Initial fixture failure cause="+owner.cleanupLedger().cause());owner.cleanupLedger().primary().printStackTrace(System.out);}
            check(owner.hasCommittedPresentation(),"actual initial renderer finish/core publication");
            NativeCoordinatorV2 coordinator=(NativeCoordinatorV2)field(owner,"coordinator");
            NativeRenderer renderer=(NativeRenderer)field(coordinator,"renderer");
            NativeOwnerV2.Fence fence=(NativeOwnerV2.Fence)field(owner,"fence");
            OwnerLifecycleV2 core=(OwnerLifecycleV2)field(owner,"core");
            if(mode.equals("helper-negative")){
                var records=renderer.inspectV2();var record=records.get("field");var container=records.get("container");var list=records.get("list");
                var live=NativeAppearanceViewsV2.Mutation.live(fence);owner.onPause();
                var cleanup=NativeAppearanceViewsV2.Mutation.cleanup(fence);
                Class<?> views=NativeAppearanceViewsV2.class,recordType=NativeAppearanceViewsV2.Record.class,scope=NativeAppearanceViewsV2.Mutation.class;
                Class<?> binding=NativeAppearanceViewsV2.Binding.class,geometry=NativeAppearanceViewsV2.Geometry.class,textType=AppearanceResolverV2.Text.class;
                var text=((AppearanceResolverV2.FieldRecipe)record.binding.node().recipe()).text();
                var insets=((AppearanceResolverV2.FieldRecipe)record.binding.node().recipe()).metrics().insets64();
                var constructor=recordType.getDeclaredConstructor(android.content.Context.class,UiPacket.Node.class,NativeAppearanceViewsV2.Input.class,scope);constructor.setAccessible(true);
                int refused=0;ConcreteHostProbe.reset();
                for(var captured:new NativeAppearanceViewsV2.Mutation[]{live,cleanup}){
                    refuses("Record",constructor,null,activity,record.binding.source(),record.input,captured);refused++;
                    refuses("bind",method(recordType,"bind",binding,geometry,boolean.class,scope),record,record.binding,record.geometry,false,captured);refused++;
                    refuses("defaults",method(views,"defaults",android.widget.TextView.class,scope),null,record.view,captured);refused++;
                    refuses("text",method(views,"text",android.widget.TextView.class,textType,binding,scope),null,record.view,text,record.binding,captured);refused++;
                    refuses("bindTitle",method(views,"bindTitle",android.widget.TextView.class,textType,binding,AppearanceDescriptorV2.Color.class,scope),null,record.view,text,record.binding,record.binding.palette().field().enabled().text(),captured);refused++;
                    refuses("installChildren",method(views,"installChildren",recordType,java.util.Map.class,scope),null,container,records,captured);refused++;
                    refuses("measure",method(views,"measure",recordType,java.util.Map.class,long.class,long.class,scope),null,container,records,20480L,30720L,captured);refused++;
                    refuses("title",method(views,"title",android.widget.TextView.class,textType,long.class,AppearanceDescriptorV2.Insets.class,binding,scope),null,record.view,text,20480L,insets,record.binding,captured);refused++;
                    refuses("measureList",method(views,"measureList",recordType,java.util.Map.class,AppearanceResolverV2.ListRecipe.class,long.class,long.class,scope),null,list,records,list.binding.node().recipe(),20480L,30720L,captured);refused++;
                    refuses("layoutRoot",method(views,"layoutRoot",recordType,int.class,int.class,AppearanceResolverV2.SafeArea.class,scope),null,container,320,480,container.binding.plan().environment.safeArea64(),captured);refused++;
                    refuses("layout",method(views,"layout",recordType,long.class,long.class,long.class,long.class,scope),null,container,0L,0L,0L,0L,captured);refused++;
                    refuses("Group.onLayout",method(NativeAppearanceViewsV2.Group.class,"onLayout",boolean.class,int.class,int.class,int.class,int.class,scope),container.group,true,0,0,320,480,captured);refused++;
                    refuses("Group.titleLayout",method(NativeAppearanceViewsV2.Group.class,"titleLayout",android.widget.TextView.class,NativeAppearanceViewsV2.Box.class,binding,scope),container.group,record.view,record.geometry.box,record.binding,captured);refused++;
                }
                System.out.println("{\"mode\":\"helper-negative\",\"actualHelpers\":13,\"staleAndCleanupRefusals\":"+refused+",\"nativeLeavesReached\":"+ConcreteHostProbe.events().size()+",\"actualCorePhase\":\""+core.snapshot().phase()+"\",\"noOperationMinted\":"+(fence.operation==null)+"}");
                check(refused==26&&ConcreteHostProbe.events().isEmpty()&&fence.operation==null,"all13 actual helpers reject stale/cleanup before native work");return;
            }
            EditText edit=(EditText)renderer.view("field");edit.requestFocus();
            InputConnection connection=edit.onCreateInputConnection(new EditorInfo());check(connection!=null,"actual retained input connection");
            edit.setSelection(0,edit.getText().length());
            NativeBridge.preparedPacket=Files.readAllBytes(inputs.resolve("independent-packet-2.json"));
            OwnerLifecycleV2.Token originalPresentation=fence.presentation;
            int[] eventFocusReads={0};boolean[] flipped={false},observed={false};boolean[] state=new boolean[5];
            String[] trace={"[]"};
            List<String> postTerminalProbes=new ArrayList<>();String[] terminalTrace={"[]"};
            ConcreteHostProbe.hook=(method,phase)->{
                var event=ConcreteHostProbe.lastEvent();
                if(mode.equals("terminal")&&method.equals("View.invalidate")&&phase.equals("entry")&&event.receiver==field(renderer,"v2Gate")&&!flipped[0]){
                    flipped[0]=true;terminalTrace[0]=frames(event.productionFrames);owner.close();
                }
                if(mode.equals("terminal")&&flipped[0]&&fence.terminal&&phase.equals("entry")&&
                    event.productionFrames.stream().anyMatch(site->site.className().equals("dev.mixer.android.NativeOwnerV2")&&(site.methodName().equals("seedFocus")||site.methodName().equals("probeWindow")))){
                    if(postTerminalProbes.size()<24)postTerminalProbes.add(method);
                }
                if(mode.equals("fresh-input")&&method.equals("View.hasWindowFocus")&&phase.equals("beforeReturn")&&event.receiver==root&&
                    event.productionFrames.stream().anyMatch(site->site.className().startsWith("dev.mixer.android.NativeRenderer$")&&site.methodName().equals("event"))) {
                    if(++eventFocusReads[0]==2){root.windowFocus=false;flipped[0]=true;}
                }
                if(method.equals("Handler.post")&&phase.equals("entry")&&event.receiver==handler&&!observed[0]){
                    observed[0]=true;state[0]=fence.drawAllowed;state[1]=fence.inputAllowed;
                    Object gate=field(renderer,"v2Gate");state[2]=gate!=null&&((NativeAppearanceViewsV2.Gate)gate).open;
                    state[3]=core.snapshot().dirty();state[4]=core.snapshot().focused();trace[0]=frames(event.productionFrames);
                }
            };
            boolean completedResult=false;
            if(mode.equals("fresh-input")||mode.equals("accepted-input"))completedResult=connection.commitText("beta",1);
            else if(mode.equals("lifecycle")){root.windowFocus=false;owner.onResume();}
            else if(mode.equals("terminal"))owner.onResume();
            else throw new IllegalArgumentException("unknown control");
            ConcreteHostProbe.hook=null;
            if(mode.equals("accepted-input")){
                System.out.println("{\"mode\":\"accepted-input\",\"delegateResult\":"+completedResult+",\"actualPresentationChanged\":"+(fence.presentation!=originalPresentation)+",\"actualCorePhase\":\""+core.snapshot().phase()+"\",\"drawAllowed\":"+fence.drawAllowed+",\"inputAllowed\":"+fence.inputAllowed+",\"JNIprepareCalls\":"+NativeBridge.prepareCalls+",\"JNIcommitCalls\":"+NativeBridge.commitCalls+",\"operationCleared\":"+(fence.operation==null)+",\"actualPacketRevision\":\""+renderer.packet.revision+"\"}");
                check(completedResult&&fence.presentation!=originalPresentation,"actual completed delegate returns across synchronous successor publication");
                check(core.snapshot().phase()==OwnerLifecycleV2.Phase.LIVE&&fence.drawAllowed&&fence.inputAllowed&&fence.operation==null,"clean successor published after actual completion");
                check(NativeBridge.prepareCalls==2&&NativeBridge.commitCalls==2&&renderer.packet.revision.equals("2"),"real independently decoded input transaction completed once");
                return;
            }
            if(mode.equals("terminal")){
                System.out.println("{\"mode\":\"terminal\",\"actualCancellationReentry\":"+flipped[0]+",\"ordinaryProbesAfterTerminal\":\""+postTerminalProbes+"\",\"actualCorePhase\":\""+core.snapshot().phase()+"\",\"JNIprepareCalls\":"+NativeBridge.prepareCalls+",\"JNIdestroyCalls\":"+NativeBridge.destroyCalls+",\"drawAllowed\":"+fence.drawAllowed+",\"inputAllowed\":"+fence.inputAllowed+",\"actualCancellationFrames\":"+terminalTrace[0]+"}");
                check(flipped[0],"actual cancellation leaf boundary reached");
                check(core.snapshot().phase()==OwnerLifecycleV2.Phase.RETIRED&&!fence.drawAllowed&&!fence.inputAllowed,"terminal authority remains sealed");
                check(NativeBridge.prepareCalls==1&&NativeBridge.destroyCalls==1,"no new engine operation and one disposal");
                check(postTerminalProbes.isEmpty(),"ordinary readiness probes must stop after terminal cancellation reentry");
                return;
            }
            System.out.println("{\"mode\":\""+mode+"\",\"focusFlippedAtNativeReturn\":"+flipped[0]+",\"queuedCallbackObserved\":"+observed[0]+",\"drawAllowedAtPost\":"+state[0]+",\"inputAllowedAtPost\":"+state[1]+",\"actualCurrentGateOpenAtPost\":"+state[2]+",\"actualCoreDirtyAtPost\":"+state[3]+",\"actualCoreFocusedAtPost\":"+state[4]+",\"JNIprepareCalls\":"+NativeBridge.prepareCalls+",\"frames\":"+trace[0]+"}");
            check(observed[0],"exact queued callback must be observed");
            if(mode.equals("fresh-input"))check(flipped[0],"focus changed at actual event's final captured native focus return");
            check(state[3],"real core is dirty");
            check(!state[0]&&!state[1]&&!state[2],"fresh focus invalidation must scalar-seal actual gates before Handler.post callback");
        } finally {ConcreteHostProbe.hook=null;try{owner.close();}catch(Error retained){if(!mode.equals("registration-failure")&&!mode.contains("remove-fatal"))throw retained;}ConcreteHostProbe.reset();NativeBridge.reset();}
    }
}
