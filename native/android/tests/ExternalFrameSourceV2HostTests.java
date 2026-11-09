package dev.mixer.android;
import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

/** Actual external source and owner/core/coordinator; renderer is closure A's explicit leaf. */
public final class ExternalFrameSourceV2HostTests {
    private static int checks;
    private static byte[] descriptor;
    static void check(boolean ok,String message){checks++;if(!ok)throw new AssertionError(message);}
    static Object field(Object value,String name){try{Field f=value.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(value);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
    static void rejects(Runnable action){try{action.run();}catch(IllegalArgumentException|IllegalStateException expected){return;}throw new AssertionError("expected refusal");}
    static byte[] packet(int revision){return ("{\"schemaVersion\":1,\"document\":{\"schemaVersion\":1,\"revision\":"+revision+",\"root\":{\"id\":\"button\",\"kind\":\"button\",\"properties\":{\"label\":\"Unicode 雪 🦊\"},\"children\":[],\"actions\":[{\"id\":\"activate\",\"event\":\"activate\"}]}},\"identities\":[{\"id\":\"button\",\"generation\":1}]}").getBytes(StandardCharsets.UTF_8);}
    private static final class Fixture implements AutoCloseable {
        final Activity activity=new Activity();final FrameLayout root=new FrameLayout(activity);
        final byte[][] delivered={null};final int[] deliveries={0};
        final ExternalFrameSourceV2 source=new ExternalFrameSourceV2(bytes->{delivered[0]=bytes;deliveries[0]++;});
        final NativeOwnerV2 owner;final Handler queue;
        Fixture(){OwnerHostProbe.reset();NativeBridge.reset();activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);root.hostAttach(new Object());owner=NativeOwnerV2.external(activity,root,source);queue=(Handler)field(owner,"handler");}
        NativeCoordinatorV2 coordinator(){return (NativeCoordinatorV2)field(owner,"coordinator");}
        NativeRenderer renderer(){return (NativeRenderer)field(coordinator(),"renderer");}
        NativeOwnerV2.Fence fence(){return (NativeOwnerV2.Fence)field(owner,"fence");}
        @Override public void close(){OwnerHostProbe.hook=null;owner.close();queue.drainAll(4);}
    }
    private static void immutableAndDescriptor(){
        byte[][] delivery={null};ExternalFrameSourceV2 source=new ExternalFrameSourceV2(b->delivery[0]=b);
        rejects(source::current);check(!source.inputEnabled(),"input starts open");
        byte[] p=packet(1),d=descriptor.clone();byte[] expected=p.clone();source.offer(p,d);p[0]=0;d[0]^=1;
        check(Arrays.equals(source.current().packet,expected)&&Arrays.equals(source.current().descriptor,descriptor),"caller can mutate retained frame");
        ExternalFrameSourceV2.Frame prior=source.current();rejects(()->source.offer(packet(2),d));check(source.current()==prior,"rejected offer replaced frame");
        byte[] envelope={1,2,3};source.input(envelope);envelope[0]=9;check(delivery[0][0]==1&&delivery[0]!=envelope,"input envelope aliased");
        source.openInput();check(source.inputEnabled(),"open failed");source.gateInput();check(!source.inputEnabled(),"gate failed");
        Looper.hostSetMain(false);try{rejects(source::current);rejects(()->source.offer(packet(2),descriptor));}finally{Looper.hostReset();}
    }
    private static void ownerAndStale(){
        try(Fixture f=new Fixture()){
            byte[] p=packet(1);f.owner.installExternal(p,descriptor);check(f.owner.externalCurrent(),"synchronous install not current");
            check(NativeBridge.createCalls==0&&NativeBridge.prepareCalls==0&&NativeBridge.commitCalls==0,"external install entered engine");
            check(f.queue.queued()==0,"exact queued work not consumed");
            byte[] event=UiPacket.decode(p).event("button","1","activate",null);f.renderer().emit(event);check(f.deliveries[0]==1&&f.delivered[0]!=event,"external input not copied/delivered");
            f.owner.gateExternalInput();f.renderer().emit(event);check(f.deliveries[0]==1,"gated external input admitted");
            f.owner.externalObserver().invalidate();Runnable stale=f.queue.snapshot().get(0);check(!f.owner.externalCurrent(),"dirty owner claims current");f.queue.drainAll(4);
            check(f.owner.externalCurrent()&&!f.fence().inputAllowed,"environment-only refresh reopened app gate");
            check(f.renderer().preparedReference==f.source.current().packet&&NativeBridge.prepareCalls==0,"refresh changed packet or touched engine");
            f.owner.installExternal(packet(2),descriptor);check(f.fence().inputAllowed,"new app presentation did not reopen input");
            f.owner.onPause();f.renderer().emit(event);check(f.deliveries[0]==1,"paused input admitted");f.queue.drainAll(4);
            f.owner.close();stale.run();check(!f.owner.externalCurrent()&&f.fence().terminal,"retired stale work reopened presentation");
            check(f.owner.cleanupLedger().coordinator()==NativeOwnerV2.Outcome.RETURNED,"owner release not returned");
            check(f.coordinator().cleanupLedger().renderer()==NativeCoordinatorV2.Outcome.RETURNED&&f.coordinator().cleanupLedger().engine()==NativeCoordinatorV2.Outcome.NOT_REQUESTED,"external cleanup acquired engine or lost renderer");
        }
    }
    private static void failures(){
        try(Fixture f=new Fixture()){
            byte[] wrong=descriptor.clone();wrong[0]^=1;rejects(()->f.owner.installExternal(packet(1),wrong));
            check(f.fence().terminal&&!f.owner.hasCommittedPresentation()&&NativeBridge.createCalls==0,"descriptor mismatch published or used engine");
            check(f.coordinator().cleanupLedger().renderer()==NativeCoordinatorV2.Outcome.RETURNED,"descriptor failure renderer release missing");
        }
        try(Fixture f=new Fixture()){
            rejects(()->f.owner.installExternal(new byte[]{0},descriptor));check(f.fence().terminal&&!f.owner.externalCurrent(),"malformed packet published");
            check(NativeBridge.prepareCalls==0&&NativeBridge.destroyCalls==0,"malformed external packet entered engine");
        }
        try(Fixture f=new Fixture()){
            f.owner.installExternal(packet(1),descriptor);f.owner.close();rejects(()->f.owner.installExternal(packet(2),descriptor));
            check(f.fence().terminal,"closed installation revived owner");
        }
    }
    public static void main(String[] args)throws Exception{descriptor=Files.readAllBytes(Path.of(args[0]));immutableAndDescriptor();ownerAndStale();failures();System.out.println("PASS external-source owner lifecycle checks="+checks+"; controlled framework/JNI leaves only");}
}
