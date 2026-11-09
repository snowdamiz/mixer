package dev.mixer.android;
import android.app.Activity;
import android.os.Handler;
import android.view.View;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/** Real renderer/Gate measurement on controlled platform leaves; no full callback-matrix claim. */
public final class ExternalFrameGateV2HostTests {
    private static int checks;
    private static void check(boolean ok,String message){checks++;if(!ok)throw new AssertionError(message);}
    private static Object field(Object value,String name){try{Field f=value.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(value);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    private static final class Sentinel extends View {
        int measures;
        Sentinel(Activity activity){super(activity);}
        @Override protected void onMeasure(int w,int h){measures++;throw new AssertionError("framework traversed authored child");}
    }
    private static byte[] packet(){return "{\"schemaVersion\":1,\"document\":{\"schemaVersion\":1,\"revision\":1,\"root\":{\"id\":\"label\",\"kind\":\"text\",\"properties\":{\"text\":\"雪 🦊\"},\"children\":[],\"actions\":[]}},\"identities\":[{\"id\":\"label\",\"generation\":1}]}".getBytes(StandardCharsets.UTF_8);}
    public static void main(String[] args)throws Exception{
        ConcreteHostProbe.reset();NativeBridge.reset();Activity activity=new Activity();FrameLayout root=new FrameLayout(activity);
        byte[] descriptor=Files.readAllBytes(Path.of(args[0]));activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);
        root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);root.hostAttach(new Object());
        ExternalFrameSourceV2 source=new ExternalFrameSourceV2(bytes->{throw new AssertionError("installation emitted app input");});
        NativeOwnerV2 owner=NativeOwnerV2.external(activity,root,source);Handler queue=(Handler)field(owner,"handler");
        try {
            owner.installExternal(packet(),descriptor);check(owner.externalCurrent(),"external real renderer not current");
            NativeCoordinatorV2 coordinator=(NativeCoordinatorV2)field(owner,"coordinator");NativeRenderer renderer=(NativeRenderer)field(coordinator,"renderer");
            NativeAppearanceViewsV2.Gate gate=(NativeAppearanceViewsV2.Gate)field(renderer,"v2Gate");Sentinel sentinel=new Sentinel(activity);gate.addView(sentinel);
            int w=View.MeasureSpec.makeMeasureSpec(777,View.MeasureSpec.EXACTLY),h=View.MeasureSpec.makeMeasureSpec(999,View.MeasureSpec.EXACTLY);
            gate.measure(w,h);check(gate.getMeasuredWidth()==777&&gate.getMeasuredHeight()==999&&sentinel.measures==0,"passive viewport measure incorrect");
            gate.removeView(sentinel);owner.gateExternalInput();owner.externalObserver().invalidate();queue.drainAll(4);
            check(owner.externalCurrent()&&!((NativeOwnerV2.Fence)field(owner,"fence")).inputAllowed,"refresh reopened input");
            owner.close();queue.drainAll(4);gate.addView(sentinel);gate.measure(w,h);check(sentinel.measures==0,"retired gate traversed child");
            check(!owner.externalCurrent()&&coordinator.cleanupLedger().renderer()==NativeCoordinatorV2.Outcome.RETURNED,"retired renderer not released");
            check(coordinator.cleanupLedger().engine()==NativeCoordinatorV2.Outcome.NOT_REQUESTED&&NativeBridge.createCalls==0&&NativeBridge.prepareCalls==0&&NativeBridge.destroyCalls==0,"external branch acquired engine");
        } finally {owner.close();queue.drainAll(4);}
        System.out.println("PASS external-gate real renderer checks="+checks+"; controlled platform leaves; 189-case matrix unrun");
    }
}
