package dev.mixer.android;
import android.app.Activity;
import android.widget.FrameLayout;
import android.os.Handler;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
/** Same actual-owner witness runs against immutable candidate2 and repaired exact classes. */
public final class LedgerStateWitness {
 private static Object field(Object value,String name)throws ReflectiveOperationException{Field f=value.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(value);}
 public static void main(String[] args)throws Exception{
  Activity activity=new Activity();FrameLayout root=new FrameLayout(activity);activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,Files.readAllBytes(Path.of(args[0])));root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);root.hostAttach(new Object());
  OwnerHostProbe.reset();NativeBridge.reset();NativeBridge.preparedPacket=("{\"schemaVersion\":1,\"document\":{\"schemaVersion\":1,\"revision\":1,\"root\":{\"id\":\"button\",\"kind\":\"button\",\"properties\":{\"label\":\"Ledger witness\"},\"children\":[],\"actions\":[{\"id\":\"activate\",\"event\":\"activate\"}]}},\"identities\":[{\"id\":\"button\",\"generation\":1}]}").getBytes(StandardCharsets.UTF_8);
  NativeOwnerV2 owner=new NativeOwnerV2(activity,root);Handler queue=(Handler)field(owner,"handler");NativeOwnerV2.Outcome[] reached={null};
  owner.onResume();owner.start();
  try{
   if(args[1].equals("active")){OwnerHostProbe.hook=(method,phase)->{if(reached[0]==null&&method.equals("Renderer.attach")&&phase.equals("entry")){OwnerHostProbe.hook=null;owner.onPause();reached[0]=owner.cleanupLedger().input();}};queue.drainAll(4);}
   else{queue.drainAll(4);NativeCoordinatorV2 coordinator=(NativeCoordinatorV2)field(owner,"coordinator");NativeRenderer renderer=(NativeRenderer)field(coordinator,"renderer");renderer.terminal(NativeEnvironmentV2.RendererCause.TERMINAL_VALIDATION_FAILED,null,null);reached[0]=owner.cleanupLedger().input();if(owner.cleanupLedger().coordinator()!=NativeOwnerV2.Outcome.DEFERRED||NativeBridge.destroyCalls!=0)throw new AssertionError("report disposal was not independently deferred");}
  }finally{OwnerHostProbe.hook=null;owner.close();queue.drainAll(4);}
  System.out.println("OBSERVED "+args[1]+" cancellation="+reached[0]+" destroy="+NativeBridge.destroyCalls);
  if(reached[0]!=NativeOwnerV2.Outcome.RETURNED)throw new AssertionError("completed cancellation mislabeled "+args[1]+": "+reached[0]);
  System.out.println("PASS actual-owner cancellation-only ledger "+args[1]);
 }
}
