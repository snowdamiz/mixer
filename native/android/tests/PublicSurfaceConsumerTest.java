package example.customer;

import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import android.widget.FrameLayout;
import dev.mixer.android.AndroidUINativeSurface;
import dev.mixer.android.AndroidUIProfile;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.InvocationTargetException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

/** External-package client of the actual facade/owner/core/coordinator.
 * Existing closure-A platform and renderer leaves are explicit test doubles. */
public final class PublicSurfaceConsumerTest {
 private static int checks;
 private static byte[] descriptor;
 private static final byte[] OWNER="A34B0762-4A40-4FAA-A459-C4A16D2F0831".getBytes(StandardCharsets.UTF_8);
 private static final byte[] OTHER="090E5A7A-BB12-48E3-803D-0FE66CC74A77".getBytes(StandardCharsets.UTF_8);
 private static void check(boolean ok,String why){checks++;if(!ok)throw new AssertionError(why);}
 private static RuntimeException rejects(Runnable action){checks++;try{action.run();}catch(IllegalArgumentException|IllegalStateException expected){return expected;}throw new AssertionError("expected refusal");}
 private static Object field(Object value,String name){try{Field f=value.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(value);}catch(ReflectiveOperationException error){throw new AssertionError(error);}}
 private static Object call(Object value,String name,Class<?>[] types,Object... args){
  try{Method m=value.getClass().getDeclaredMethod(name,types);m.setAccessible(true);return m.invoke(value,args);}
  catch(InvocationTargetException error){if(error.getCause() instanceof RuntimeException failure)throw failure;if(error.getCause() instanceof Error failure)throw failure;throw new AssertionError(error);}
  catch(ReflectiveOperationException error){throw new AssertionError(error);}
 }
 private static void reset(){try{Class.forName("dev.mixer.android.OwnerHostProbe").getMethod("reset").invoke(null);Method reset=Class.forName("dev.mixer.android.NativeBridge").getDeclaredMethod("reset");reset.setAccessible(true);reset.invoke(null);}catch(ReflectiveOperationException error){throw new AssertionError(error);}}
 private static byte[] packet(int revision){return ("{\"schemaVersion\":1,\"document\":{\"schemaVersion\":1,\"revision\":"+revision+",\"root\":{\"id\":\"button\",\"kind\":\"button\",\"properties\":{\"label\":\"Unicode 雪 🌱\\nZoë\"},\"children\":[],\"actions\":[{\"id\":\"activate\",\"event\":\"activate\"}]}},\"identities\":[{\"id\":\"button\",\"generation\":1}]}").getBytes(StandardCharsets.UTF_8);}
 private static final class Fixture {
  final Activity activity=new Activity();final FrameLayout root=new FrameLayout(activity);
  final byte[][] delivered={null,null};int count;
  final AndroidUINativeSurface surface;
  Fixture(){reset();activity.assets.put("MixerAppearanceV2/descriptor.json",descriptor);root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);root.hostAttach(new Object());
   surface=new AndroidUINativeSurface(activity,root,AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,(owner,event)->{delivered[0]=owner;delivered[1]=event;count++;});
  }
  Object owner(){return field(surface,"nativeOwner");}
  Object renderer(){return field(field(owner(),"coordinator"),"renderer");}
  Handler queue(){return (Handler)field(owner(),"handler");}
  void emit(byte[] event){call(renderer(),"emit",new Class<?>[]{byte[].class},(Object)event);}
  void invalidate(){call(field(owner(),"observer"),"invalidate",new Class<?>[]{});}
  void install(int revision){surface.install(new AndroidUINativeSurface.Frame(OWNER,packet(revision),descriptor));}
 }
 private static void lifetimeAndBytes(){
  Fixture f=new Fixture();byte[] identity=OWNER.clone();f.surface.activate(identity);identity[0]=0;
  check(f.surface.profile()==AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,"profile changed");
  rejects(()->f.surface.activate(OTHER));
  byte[] p=packet(1),d=descriptor.clone(),o=OWNER.clone();byte[] expected=p.clone();
  AndroidUINativeSurface.Frame frame=new AndroidUINativeSurface.Frame(o,p,d);p[0]=0;d[0]=0;o[0]=0;
  f.surface.install(frame);
  check(f.surface.isCurrent(),"install returned without current attachment");
  check(f.queue().queued()==0,"synchronous install left pending work");
  check(Arrays.equals((byte[])field(f.renderer(),"preparedReference"),expected),"frame aliased or normalized packet");
  check(f.count==0,"install invoked app callback");
  byte[] event="{\"schemaVersion\":1,\"documentRevision\":18446744073709551615,\"generation\":9007199254740993,\"text\":\"雪 🌱\\nZoë\"}".getBytes(StandardCharsets.UTF_8);
  byte[] exact=event.clone();f.emit(event);event[0]=0;
  check(f.count==1&&Arrays.equals(f.delivered[0],OWNER)&&Arrays.equals(f.delivered[1],exact),"captured bytes/UInt64 changed");
  f.delivered[0][0]=0;f.emit(exact);check(Arrays.equals(f.delivered[0],OWNER),"callback owner aliases retained identity");
  rejects(()->f.surface.install(new AndroidUINativeSurface.Frame(OTHER,packet(2),descriptor)));
  f.emit(exact);check(f.count==2,"stale install left input open");
  f.install(2);f.emit(exact);check(f.count==3,"explicit valid install failed");
  f.surface.gateInput();f.emit(exact);check(f.count==3,"command gate admitted input");
  f.invalidate();Runnable stale=f.queue().snapshot().get(0);f.queue().drainAll(4);
  check(f.surface.isCurrent(),"native environment refresh lost current frame");
  f.emit(exact);check(f.count==3,"environment refresh reopened gated input");
  f.install(3);f.surface.onPause();f.emit(exact);check(f.count==3,"paused surface emitted input");
  f.surface.onResume();f.queue().drainAll(4);f.install(4);f.emit(exact);check(f.count==4,"resume did not delegate to real owner");
  f.surface.onStop();f.emit(exact);check(f.count==4,"stopped surface emitted input");
  f.surface.revoke(OWNER);f.surface.revoke(OWNER);f.surface.close();stale.run();f.emit(exact);
  check(!f.surface.isCurrent()&&f.count==4,"retired work/input revived lifetime");
  rejects(()->f.surface.install(frame));rejects(()->f.surface.activate(OWNER));rejects(()->f.surface.revoke(OTHER));
  Object retained=f.owner();
  AndroidUINativeSurface next=new AndroidUINativeSurface(f.activity,f.root,AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,(owner,envelope)->{throw new AssertionError("installation event");});
  next.activate(OTHER);next.install(new AndroidUINativeSurface.Frame(OTHER,packet(1),descriptor));f.surface.close();
  check(next.isCurrent()&&f.owner()==retained,"old close changed new lifetime or discarded old ownership");next.revoke(OTHER);next.close();
 }
 private static void refusalsAndFailureRetention(){
  AndroidUINativeSurface.Frame limits=new AndroidUINativeSurface.Frame(OWNER,new byte[1_048_576],new byte[65_536]);
  check(((byte[])field(limits,"packet")).length==1_048_576&&((byte[])field(limits,"appearance")).length==65_536,"exact byte caps refused");
  rejects(()->new AndroidUINativeSurface.Frame(OWNER,new byte[1_048_577],descriptor));
  rejects(()->new AndroidUINativeSurface.Frame(OWNER,packet(1),new byte[65_537]));
  rejects(()->new AndroidUINativeSurface.Frame(OWNER,new byte[0],descriptor));
  rejects(()->new AndroidUINativeSurface.Frame(OWNER,packet(1),new byte[0]));
  Fixture f=new Fixture();rejects(()->f.surface.install(new AndroidUINativeSurface.Frame(OWNER,packet(1),descriptor)));
  rejects(()->f.surface.activate(new byte[0]));rejects(()->f.surface.activate(new byte[65]));
  for(AndroidUIProfile profile:new AndroidUIProfile[]{AndroidUIProfile.LEGACY_HORIZONTAL,AndroidUIProfile.MEASURED_MULTILINE_V2})rejects(()->new AndroidUINativeSurface(f.activity,f.root,profile,(owner,event)->{}));
  rejects(()->new AndroidUINativeSurface(new Activity(),f.root,AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,(owner,event)->{}));
  Looper.hostSetMain(false);try{rejects(()->f.surface.activate(OWNER));rejects(f.surface::close);rejects(f.surface::isCurrent);}finally{Looper.hostReset();}
  f.surface.activate(OWNER);rejects(()->f.surface.install(new AndroidUINativeSurface.Frame(OWNER,new byte[]{0},descriptor)));
  check(!f.surface.isCurrent(),"malformed packet attached");
  RuntimeException failure=rejects(f.surface::close);check(rejects(f.surface::close)==failure,"repeated close erased original failure");
  Fixture cleanup=new Fixture();cleanup.surface.activate(OWNER);cleanup.install(1);cleanup.invalidate();
  Handler queue=cleanup.queue();queue.removeFailure=new IllegalStateException("controlled uncertain removal");
  RuntimeException uncertain=rejects(cleanup.surface::close);int removals=queue.removeCalls;Object owner=cleanup.owner();
  check(rejects(cleanup.surface::close)==uncertain&&queue.removeCalls==removals&&cleanup.owner()==owner,"uncertain cleanup was retried or discarded");
  check(!cleanup.surface.isCurrent(),"uncertain close admitted presentation");
  Fixture empty=new Fixture();empty.surface.close();empty.surface.close();rejects(()->empty.surface.activate(OWNER));
 }
 public static void main(String[] args)throws Exception{
  descriptor=Files.readAllBytes(Path.of(args[0]));lifetimeAndBytes();refusalsAndFailureRetention();
  System.out.println("PASS public external-package surface checks="+checks+"; real facade/owner/core/coordinator; existing controlled Android/JNI/renderer leaves; native runtime pending");
 }
}
