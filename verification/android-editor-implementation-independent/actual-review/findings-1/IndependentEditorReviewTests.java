package dev.mixer.android;

import android.app.Activity;
import android.os.Handler;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.HandwritingGesture;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.PreviewableHandwritingGesture;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;

/** Extra actual-source hostile controls. Android/JNI leaves are the sealed authored doubles. */
public final class IndependentEditorReviewTests {
    private IndependentEditorReviewTests() {}
    private static byte[] descriptor;
    private static void check(boolean yes,String message) { if(!yes)throw new AssertionError(message); }
    private static Object get(Object object,String name) {
        try {Field f=object.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(object);}
        catch(ReflectiveOperationException failure){throw new AssertionError(failure);}
    }
    private static void put(Object object,String name,Object value) {
        try {Field f=object.getClass().getDeclaredField(name);f.setAccessible(true);f.set(object,value);}
        catch(ReflectiveOperationException failure){throw new AssertionError(failure);}
    }
    private static byte[] packet() {
        return ("{\"schemaVersion\":1,\"document\":{\"schemaVersion\":1,\"revision\":1,"+
            "\"root\":{\"id\":\"field\",\"kind\":\"textField\",\"properties\":{\"label\":\"Entry\",\"value\":\"hello\"},"+
            "\"children\":[],\"actions\":[{\"id\":\"changed\",\"event\":\"textChange\"},{\"id\":\"done\",\"event\":\"submit\"}]}},"+
            "\"identities\":[{\"id\":\"field\",\"generation\":1}]}").getBytes(StandardCharsets.UTF_8);
    }
    private static final class Fixture implements AutoCloseable {
        final NativeOwnerV2 owner;
        final Handler queue;
        final NativeRenderer renderer;
        final NativeAppearanceViewsV2.NativeField edit;
        Fixture() {
            ConcreteHostProbe.reset();
            Activity activity=new Activity();FrameLayout root=new FrameLayout(activity);
            activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);
            root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);
            root.hostAttach(new Object());NativeBridge.reset();NativeBridge.preparedPacket=packet();
            owner=new NativeOwnerV2(activity,root);queue=(Handler)get(owner,"handler");
            owner.onResume();owner.start();queue.drainAll(6);
            check(owner.hasCommittedPresentation(),"independent fixture failed to publish");
            renderer=(NativeRenderer)get(get(owner,"coordinator"),"renderer");
            edit=(NativeAppearanceViewsV2.NativeField)renderer.view("field");edit.requestFocus();ConcreteHostProbe.reset();
        }
        NativeOwnerV2.Fence fence(){return (NativeOwnerV2.Fence)get(owner,"fence");}
        InputConnection connection(){InputConnection c=edit.onCreateInputConnection(new EditorInfo());check(c!=null,"connection");return c;}
        BaseInputConnection target(){return (BaseInputConnection)edit.lastConnection;}
        @Override public void close(){
            ConcreteHostProbe.hook=null;android.widget.EditText.creatorNull=false;
            try{owner.close();queue.drainAll(8);}catch(RuntimeException|Error expected){/* case checks actual disposition first */}
            ConcreteHostProbe.reset();
        }
    }
    private static final class RepopulatedInfo extends EditorInfo {
        @Override public void setSupportedHandwritingGesturePreviews(Set<Class<? extends PreviewableHandwritingGesture>> values) {
            super.setSupportedHandwritingGesturePreviews(values);
            // Both setters are public and non-final in the pinned official EditorInfo.
            super.setSupportedHandwritingGestures(List.of(HandwritingGesture.class));
            super.setSupportedHandwritingGesturePreviews(Set.of(PreviewableHandwritingGesture.class));
        }
    }
    private static final class RepopulatedFailedInfo extends EditorInfo {
        @Override public void setSupportedHandwritingGesturePreviews(Set<Class<? extends PreviewableHandwritingGesture>> values) {
            super.setSupportedHandwritingGesturePreviews(values);
            inputType=99;hintText="repopulated-output";initialSelStart=initialSelEnd=0;
            super.setInitialSurroundingText("private-surrounding-output");
        }
    }
    private static void metadataSuccess() {
        try(Fixture f=new Fixture()) {
            RepopulatedInfo info=new RepopulatedInfo();
            InputConnection c=f.edit.onCreateInputConnection(info);
            System.out.println("OBSERVED adapter="+(c!=null)+" gestures="+info.gestures.size()+" previews="+info.previews.size()+" terminal="+f.fence().terminal);
            check(c==null||info.gestures.isEmpty()&&info.previews.isEmpty(),
                "usable adapter advertises refused handwriting operations after setter reentry");
        }
    }
    private static void metadataFailure() {
        try(Fixture f=new Fixture()) {
            RepopulatedFailedInfo info=new RepopulatedFailedInfo();android.widget.EditText.creatorNull=true;
            InputConnection c=f.edit.onCreateInputConnection(info);
            System.out.println("OBSERVED adapter="+(c!=null)+" inputType="+info.inputType+" hint="+info.hintText+" privateSurrounding="+info.hostSurrounding()+" terminal="+f.fence().terminal);
            check(c==null,"native null returned adapter");
            check(info.inputType==0&&info.hintText==null&&info.hostSurrounding()==null,
                "failed creator silently retains repopulated public/private EditorInfo payload");
        }
    }
    private static void mutationGetterReentry() {
        try(Fixture f=new Fixture()) {
            InputConnection c=f.connection();boolean[] outer={false},inner={false},accepted={false};
            int[] saved={0};
            ConcreteHostProbe.hook=(method,phase)->{
                if(!outer[0]&&method.equals("BaseInputConnection.beginBatchEdit")&&phase.equals("entry")) {
                    outer[0]=true;f.owner.close();NativeAppearanceViewsV2.Mutation captured=f.edit.record.mutation();
                    saved[0]=(Integer)get(f.renderer,"v2RosterCount");
                    ConcreteHostProbe.hook=(nested,at)->{
                        if(!inner[0]&&nested.equals("TextView.getText")&&at.equals("beforeReturn")) {
                            inner[0]=true;put(f.renderer,"v2RosterCount",0);
                        }
                    };
                    try{captured.require();accepted[0]=true;}catch(IllegalStateException expected){accepted[0]=false;}
                    finally{put(f.renderer,"v2RosterCount",saved[0]);ConcreteHostProbe.hook=null;}
                }
            };
            c.beginBatchEdit();ConcreteHostProbe.hook=null;
            System.out.println("OBSERVED getterHook="+inner[0]+" capturedMutationAcceptedAfterRosterLoss="+accepted[0]+" targetClose="+f.target().closeCalls);
            check(outer[0]&&inner[0],"getter control missed actual captured Mutation use");
            check(!accepted[0],"exact Mutation use accepts roster loss introduced by its own native getter");
        }
    }
    private static boolean drainGetter(String method,String phase) {
        return method.equals("TextView.getText")&&phase.equals("beforeReturn")&&
            ConcreteHostProbe.lastEvent().productionFrames.stream().anyMatch(frame->frame.methodName().equals("drain"));
    }
    private static void closeRosterReentry() {
        try(Fixture f=new Fixture()) {
            InputConnection c=f.connection();BaseInputConnection old=f.target();boolean[] fired={false};
            int saved=(Integer)get(f.renderer,"v2RosterCount");
            ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&drainGetter(method,phase)) {fired[0]=true;put(f.renderer,"v2RosterCount",0);}};
            Throwable escaped=null;try{c.closeConnection();}catch(RuntimeException|Error failure){escaped=failure;}
            ConcreteHostProbe.hook=null;put(f.renderer,"v2RosterCount",saved);
            System.out.println("OBSERVED getterHook="+fired[0]+" nativeCloseAfterRosterLoss="+old.closeCalls+" escaped="+(escaped==null?"none":escaped.getClass().getSimpleName()));
            check(fired[0],"drain getter control not reached");
            check(old.closeCalls==0,"cleanup dispatch closes target after its getter removed retained roster authority");
        }
    }
    private static void closeTargetReentry() {
        try(Fixture f=new Fixture()) {
            InputConnection c=f.connection();BaseInputConnection old=f.target(),foreign=new BaseInputConnection(f.edit,true);
            Object attempt=get(f.edit,"attempt");boolean[] fired={false};
            ConcreteHostProbe.hook=(method,phase)->{if(!fired[0]&&drainGetter(method,phase)) {fired[0]=true;put(attempt,"target",foreign);}};
            Throwable escaped=null;try{c.closeConnection();}catch(RuntimeException|Error failure){escaped=failure;}
            ConcreteHostProbe.hook=null;
            System.out.println("OBSERVED getterHook="+fired[0]+" oldClose="+old.closeCalls+" foreignClose="+foreign.closeCalls+" escaped="+(escaped==null?"none":escaped.getClass().getSimpleName()));
            check(fired[0],"drain target control not reached");
            check(foreign.closeCalls==0,"cleanup dispatch follows mutable attempt.target instead of captured exact lease target");
        }
    }
    public static void main(String[] args) throws Exception {
        descriptor=Files.readAllBytes(Path.of(args[1]));
        switch(args[0]) {
            case "metadata-success" -> metadataSuccess();
            case "metadata-failure" -> metadataFailure();
            case "mutation-getter-reentry" -> mutationGetterReentry();
            case "close-roster-reentry" -> closeRosterReentry();
            case "close-target-reentry" -> closeTargetReentry();
            default -> throw new IllegalArgumentException(args[0]);
        }
        System.out.println("PASS independent actual-source control "+args[0]);
    }
}
