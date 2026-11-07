package dev.mixer.android;
import android.app.Activity;
import android.os.Handler;
import android.widget.FrameLayout;
import android.widget.EditText;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
/** Identical actual fourteen-subject witness against frozen candidate 2 and repaired class bytes. */
public final class FocusStateWitness {
 private static Object field(Object value,String name){try{Field f=value.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(value);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
 private static boolean closed(NativeOwnerV2 owner){NativeOwnerV2.Fence fence=(NativeOwnerV2.Fence)field(owner,"fence");Object coordinator=field(owner,"coordinator");NativeRenderer renderer=(NativeRenderer)field(coordinator,"renderer");return !fence.drawAllowed&&!fence.inputAllowed&&!(Boolean)field(field(renderer,"v2Gate"),"open");}
 public static void main(String[] args)throws Exception{
  Activity activity=new Activity();FrameLayout root=new FrameLayout(activity);activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,Files.readAllBytes(Path.of(args[0])));root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);root.hostAttach(new Object());
  ConcreteHostProbe.reset();NativeBridge.reset();NativeBridge.preparedPacket=("{\"schemaVersion\":1,\"document\":{\"schemaVersion\":1,\"revision\":1,\"root\":{\"id\":\"field\",\"kind\":\"textField\",\"properties\":{\"label\":\"Focus witness\",\"value\":\"hello\"},\"children\":[],\"actions\":[{\"id\":\"change\",\"event\":\"textChange\"},{\"id\":\"submit\",\"event\":\"submit\"}]}},\"identities\":[{\"id\":\"field\",\"generation\":1}]}").getBytes(StandardCharsets.UTF_8);
  NativeOwnerV2 owner=new NativeOwnerV2(activity,root);Handler queue=(Handler)field(owner,"handler");OwnerLifecycleV2 core=(OwnerLifecycleV2)field(owner,"core");boolean[] reached={false,false},closed={false,false};int[] captured={0};String[] trace={"",""};boolean dirty;boolean focused;long beforeSerial;
  owner.onResume();owner.start();queue.drainAll(4);NativeCoordinatorV2 coordinator=(NativeCoordinatorV2)field(owner,"coordinator");NativeRenderer renderer=(NativeRenderer)field(coordinator,"renderer");beforeSerial=((NativeOwnerV2.Fence)field(owner,"fence")).sealSerial;
  try{
   EditText editor=(EditText)renderer.view("field");editor.requestFocus();InputConnection connection=editor.onCreateInputConnection(new EditorInfo());
   ConcreteHostProbe.hook=(method,phase)->{
    var event=ConcreteHostProbe.lastEvent();boolean fresh=event.productionFrames.stream().anyMatch(frame->frame.className().equals("dev.mixer.android.NativeOwnerV2")&&frame.methodName().equals("seedFocus"));
    if(!fresh&&method.equals("View.hasWindowFocus")&&phase.equals("beforeReturn")&&event.receiver==root&&event.productionFrames.stream().anyMatch(frame->frame.className().equals("dev.mixer.android.NativeRenderer$2")&&frame.methodName().equals("event"))&&++captured[0]==2)root.windowFocus=false;
    if(fresh&&method.equals("View.hasWindowFocus")&&phase.equals("entry")&&event.receiver==root){reached[0]=true;closed[0]=closed(owner);trace[0]=event.productionFrames.toString();}
    if(method.equals("Handler.post")&&phase.equals("entry")){reached[1]=true;closed[1]=closed(owner);trace[1]=event.productionFrames.toString();}
   };
   if(args[1].equals("input"))connection.commitText("z",1);
   else {List<OwnerLifecycleV2.Decision> decisions=core.focusChanged(core.lifetime(),false);var process=NativeOwnerV2.class.getDeclaredMethod("process",List.class,byte[].class);process.setAccessible(true);process.invoke(owner,decisions,null);if(((NativeOwnerV2.Fence)field(owner,"fence")).sealSerial!=beforeSerial)throw new AssertionError("effect advanced serial");}
   dirty=core.snapshot().dirty();focused=core.snapshot().focused();
  }finally{ConcreteHostProbe.hook=null;owner.close();queue.drainAll(4);}
  System.out.println("OBSERVED "+args[1]+" captured="+captured[0]+" fresh="+reached[0]+" freshClosed="+closed[0]+" post="+reached[1]+" postClosed="+closed[1]+" dirty="+dirty+" focused="+focused+" prepare="+NativeBridge.prepareCalls+" commit="+NativeBridge.commitCalls+" destroy="+NativeBridge.destroyCalls);System.out.println("FRESH "+trace[0]);System.out.println("POST "+trace[1]);
  if(!reached[1]||!closed[1]||!dirty||focused||NativeBridge.prepareCalls!=1||NativeBridge.commitCalls!=1)throw new AssertionError("nonterminal focus change left gates open at actual post");
  if(args[1].equals("input")&&(captured[0]!=2||!reached[0]||!closed[0]))throw new AssertionError("native input fresh probe preceded scalar seal");
  System.out.println("PASS actual-owner scalar focus sealing "+args[1]);
 }
}
