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
        NativeOwnerV2 owner=new NativeOwnerV2(activity,root);
        try {
            owner.start();owner.onResume();Handler handler=(Handler)field(owner,"handler");
            check(handler.drainOne(),"one actual initial drain");
            check(owner.hasCommittedPresentation(),"actual initial renderer finish/core publication");
            NativeCoordinatorV2 coordinator=(NativeCoordinatorV2)field(owner,"coordinator");
            NativeRenderer renderer=(NativeRenderer)field(coordinator,"renderer");
            NativeOwnerV2.Fence fence=(NativeOwnerV2.Fence)field(owner,"fence");
            OwnerLifecycleV2 core=(OwnerLifecycleV2)field(owner,"core");
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
        } finally {ConcreteHostProbe.hook=null;owner.close();ConcreteHostProbe.reset();NativeBridge.reset();}
    }
}
