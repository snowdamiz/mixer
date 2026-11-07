package dev.mixer.android;
import android.app.Activity;
import android.os.Handler;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
/** Identical real fourteen-subject witness against immutable candidate3 and the repaired bytes. */
public final class PublicationStateWitness {
 private static Object field(Object value,String name){try{Field f=value.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(value);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
 private static NativeRenderer renderer(NativeOwnerV2 owner){Object joined=field(owner,"opening");if(joined==null)joined=field(owner,"coordinator");return (NativeRenderer)field(joined,"renderer");}
 private static boolean closed(NativeOwnerV2 owner){NativeOwnerV2.Fence fence=(NativeOwnerV2.Fence)field(owner,"fence");NativeRenderer renderer=renderer(owner);return !fence.drawAllowed&&!fence.inputAllowed&&!(Boolean)field(renderer,"v2Open")&&!(Boolean)field(field(renderer,"v2Gate"),"open");}
 private static byte[] packet(int revision){return ("{\"schemaVersion\":1,\"document\":{\"schemaVersion\":1,\"revision\":"+revision+",\"root\":{\"id\":\"button\",\"kind\":\"button\",\"properties\":{\"label\":\"Completion witness\"},\"children\":[],\"actions\":[{\"id\":\"activate\",\"event\":\"activate\"}]}},\"identities\":[{\"id\":\"button\",\"generation\":1}]}").getBytes(StandardCharsets.UTF_8);}
 public static void main(String[] args)throws Exception{
  Activity activity=new Activity();FrameLayout root=new FrameLayout(activity);activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,Files.readAllBytes(Path.of(args[0])));root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);root.hostAttach(new Object());ConcreteHostProbe.reset();NativeBridge.reset();NativeBridge.preparedPacket=packet(1);
  NativeOwnerV2[] selected={null};int[] hooks={0},posts={0};boolean[] atHook={true},atPost={true},preparedDirty={false};String[] trace={""};
  Runnable completion=()->{NativeOwnerV2 owner=selected[0];hooks[0]++;atHook[0]&=closed(owner);if(args[1].equals("hook-dirty")&&hooks[0]==1)owner.onPause();};
  NativeOwnerV2 owner=new NativeOwnerV2(activity,root,completion);selected[0]=owner;Handler queue=(Handler)field(owner,"handler");OwnerLifecycleV2 core=(OwnerLifecycleV2)field(owner,"core");boolean successful,dirty,openAfter;int queued;
  owner.onResume();owner.start();ConcreteHostProbe.hook=(method,phase)->{
   var event=ConcreteHostProbe.lastEvent();if(args[1].equals("prepare-dirty")&&!preparedDirty[0]&&method.equals("NativeBridge.prepareV2")&&phase.equals("entry")){preparedDirty[0]=true;owner.onPause();}
   if(method.equals("Handler.post")&&phase.equals("entry")&&core.snapshot().phase()==OwnerLifecycleV2.Phase.LIVE&&core.snapshot().dirty()){posts[0]++;atPost[0]&=closed(owner);trace[0]=event.productionFrames.toString();}
  };
  try{
   queue.drainOne();successful=core.snapshot().phase()==OwnerLifecycleV2.Phase.LIVE&&core.snapshot().presentation()!=null&&field(field(owner,"coordinator"),"committedPacket")!=null;dirty=core.snapshot().dirty();queued=queue.queued();openAfter=(Boolean)field(field(renderer(owner),"v2Gate"),"open");
   if(args[1].equals("clean")){NativeBridge.preparedPacket=packet(2);renderer(owner).view("button").performClick();if(!owner.hasCommittedPresentation()||!(Boolean)field(field(renderer(owner),"v2Gate"),"open")||NativeBridge.commitCalls!=2)throw new AssertionError("clean native successor blocked");}
  }finally{ConcreteHostProbe.hook=null;owner.close();queue.drainAll(4);}
  System.out.println("OBSERVED "+args[1]+" completionHooks="+hooks[0]+" hookClosed="+atHook[0]+" dirtyPosts="+posts[0]+" postClosed="+atPost[0]+" committed="+successful+" dirty="+dirty+" queued="+queued+" concreteOpenAfter="+openAfter+" prepares="+NativeBridge.prepareCalls+" commits="+NativeBridge.commitCalls);System.out.println("POST "+trace[0]);
  if(!successful||!atHook[0])throw new AssertionError("successful finish opened before actual core completion hook");
  if(!args[1].equals("clean")&&(!dirty||queued!=1||posts[0]!=1||!atPost[0]||openAfter||NativeBridge.prepareCalls!=1||NativeBridge.commitCalls!=1))throw new AssertionError("dirty successful completion reopened concrete gate before queued drain");
  if(args[1].equals("clean")&&(dirty||queued!=0||!openAfter))throw new AssertionError("clean completion failed to publish");
  System.out.println("PASS real owner closed finish and clean core publication "+args[1]);
 }
}
