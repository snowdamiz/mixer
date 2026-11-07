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
import java.util.List;

/** Closure A executes actual owner/core/coordinator/observer; renderer is an explicit orchestration leaf. */
public final class NativeOwnerV2HostTests {
 private static byte[] descriptor;private static int checks,cases;
 private static final class Fatal extends Error {private static final long serialVersionUID=1L;Fatal(String message){super(message);}}
 private static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
 private static Object field(Object value,String name){try{Field field=value.getClass().getDeclaredField(name);field.setAccessible(true);return field.get(value);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}}
 private static byte[] packet(int revision){return ("{\"schemaVersion\":1,\"document\":{\"schemaVersion\":1,\"revision\":"+revision+",\"root\":{\"id\":\"button\",\"kind\":\"button\",\"properties\":{\"label\":\"Independent owner host\"},\"children\":[],\"actions\":[{\"id\":\"activate\",\"event\":\"activate\"}]}},\"identities\":[{\"id\":\"button\",\"generation\":1}]}").getBytes(StandardCharsets.UTF_8);}
 private static Throwable thrown(Runnable action){try{action.run();}catch(RuntimeException|Error failure){return failure;}throw new AssertionError("expected throw");}
 private static final class Fixture implements AutoCloseable {
  final Activity activity=new Activity();final FrameLayout root=new FrameLayout(activity);final NativeOwnerV2 owner;final Handler queue;
  Fixture(boolean ready){this(ready,null);}
  Fixture(boolean ready,Runnable completionFault){OwnerHostProbe.reset();NativeBridge.reset();NativeBridge.preparedPacket=packet(1);activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);root.layout(0,0,1000,1500);activity.window.getDecorView().layout(0,0,1000,1500);if(ready)root.hostAttach(new Object());owner=new NativeOwnerV2(activity,root,completionFault);queue=(Handler)field(owner,"handler");}
  NativeOwnerV2.Fence fence(){return (NativeOwnerV2.Fence)field(owner,"fence");}
  NativeEnvironmentV2.Observer observer(){return (NativeEnvironmentV2.Observer)field(owner,"observer");}
  NativeCoordinatorV2 coordinator(){Object value=field(owner,"coordinator");if(value==null)value=field(owner,"opening");return (NativeCoordinatorV2)value;}
  NativeRenderer renderer(){return (NativeRenderer)field(coordinator(),"renderer");}
  OwnerLifecycleV2 core(){return (OwnerLifecycleV2)field(owner,"core");}
  void start(){owner.onResume();owner.start();}
  void ready(){start();queue.drainAll(4);check(owner.hasCommittedPresentation(),"not ready: "+owner.cleanupLedger().primary());}
  @Override public void close(){OwnerHostProbe.hook=null;owner.close();queue.drainAll(4);}
 }
 private static void inertAndReadiness(){
  try(Fixture f=new Fixture(false)){
   check(NativeBridge.createCalls==0&&OwnerHostProbe.count("Context.registerComponentCallbacks","entry")==0,"constructor acquired resource");f.start();check(f.queue.queued()==0&&NativeBridge.createCalls==0,"unattached root opened");
   f.root.rootInsets=null;f.root.layout(0,0,0,0);f.root.hostAttach(new Object());check(f.queue.queued()==0,"zero root opened");
   f.root.layout(0,0,1000,1500);check(f.queue.queued()==0,"no-insets root opened");f.root.hostInsets(new android.view.WindowInsets());check(f.queue.queued()==1,"ready root did not queue once");
   for(int i=0;i<20;i++)f.observer().invalidate();check(f.queue.queued()==1,"dirty burst owned multiple drains");f.queue.drainAll(4);check(f.owner.hasCommittedPresentation(),"ready drain did not open");
   check(f.core().snapshot().operation()==null&&f.fence().operation==null,"operation leaked after completion");
  }cases++;
 }
 private static void staleAndWindow(){
  try(Fixture f=new Fixture(true)){f.start();Runnable stale=f.queue.snapshot().get(0);f.owner.close();stale.run();check(NativeBridge.createCalls==0,"stale delivered effect");}
  try(Fixture f=new Fixture(true)){f.ready();f.activity.window=new android.view.Window(f.activity);f.observer().invalidate();check(f.fence().terminal,"changed Window was not terminal");check(f.core().snapshot().terminalReason()==OwnerLifecycleV2.Reason.WINDOW_LOST,"Window identity changed reason");}cases++;
 }
 private static void inputAndRefresh(){
  try(Fixture f=new Fixture(true)){
   f.ready();byte[] retained=(byte[])field(f.coordinator(),"committedPacket");byte[] bytes=retained.clone();int calls=NativeBridge.prepareCalls;
   f.observer().invalidate();check(!f.fence().inputAllowed&&!f.fence().drawAllowed,"observer did not seal");f.queue.drainAll(4);
   check(field(f.coordinator(),"committedPacket")==retained&&Arrays.equals(retained,bytes)&&f.renderer().preparedReference==retained,"refresh changed retained packet/reference");
   check(NativeBridge.prepareCalls==calls&&NativeBridge.commitCalls==1&&NativeBridge.abortCalls==0&&NativeBridge.exchangeCalls==0,"refresh touched engine");
   byte[] event=UiPacket.decode(retained).event("button","1","activate",null);NativeBridge.preparedPacket=packet(2);f.renderer().emit(event);
   check(NativeBridge.lastInput==event&&NativeBridge.lastOperation==1&&NativeBridge.prepareCalls==calls+1,"input was not synchronous/exact operation1");
   for(Field member:NativeOwnerV2.class.getDeclaredFields())check(member.getType()!=byte[].class,"owner retains bytes");
   calls=NativeBridge.prepareCalls;f.owner.onPause();f.renderer().emit(event);check(NativeBridge.prepareCalls==calls,"background input admitted");f.queue.drainAll(4);f.owner.onResume();f.queue.drainAll(4);
   f.root.hostWindowFocus(false);f.renderer().emit(event);check(NativeBridge.prepareCalls==calls,"unfocused input admitted");f.queue.drainAll(4);check(!f.fence().inputAllowed,"core focus not applied");
  }cases++;
 }
 private static void reentry(){
  for(String method:List.of("NativeBridge.create","Renderer.captureInstalled","Renderer.captureEnvironment","Renderer.prepare","Renderer.attach","Renderer.validate"))for(String phase:List.of("entry","beforeReturn")){
   try(Fixture f=new Fixture(true)){
    f.start();final boolean[] hit={false};OwnerHostProbe.hook=(m,p)->{if(!hit[0]&&m.equals(method)&&p.equals(phase)){hit[0]=true;OwnerHostProbe.hook=null;f.owner.close();check(!f.fence().drawAllowed&&!f.fence().inputAllowed,"terminal gates open at callback");check(NativeBridge.destroyCalls==0,"active resource destroyed before return");}};
    f.queue.drainAll(4);check(hit[0],"reentry missed "+method);check(f.fence().terminal&&!f.owner.hasCommittedPresentation(),"terminal operation published");check(NativeBridge.commitCalls==0&&NativeBridge.destroyCalls==1,"late session not disposed once");
   }cases++;
  }
  try(Fixture f=new Fixture(true)){
   f.start();final boolean[] hit={false};OwnerHostProbe.hook=(m,p)->{if(!hit[0]&&m.equals("Renderer.attach")&&p.equals("entry")){hit[0]=true;OwnerHostProbe.hook=null;f.owner.onPause();check(!f.fence().terminal,"lifecycle dirty invented retirement");}};
   f.queue.drainAll(4);check(hit[0]&&f.owner.hasCommittedPresentation()&&NativeBridge.prepareCalls==1,"lifecycle dirty did not finish/coalesce refresh");check(f.queue.postCalls==2,"dirty operation did not post one later drain");
  }cases++;
 }
 private static void observerDuringOperation(){
  for(String method:List.of("Renderer.captureEnvironment","Renderer.prepare","Renderer.attach","Renderer.validate"))try(Fixture f=new Fixture(true)){
   f.start();final boolean[] hit={false};OwnerHostProbe.hook=(m,p)->{if(!hit[0]&&m.equals(method)&&p.equals("beforeReturn")){hit[0]=true;OwnerHostProbe.hook=null;f.observer().invalidate();}};
   f.queue.drainAll(4);check(hit[0],"observer hook missed "+method);
   if(method.equals("Renderer.validate")){check(!f.fence().terminal&&f.owner.hasCommittedPresentation(),"post-validation dirty did not complete/coalesce");check(f.queue.postCalls==2&&NativeBridge.commitCalls==1,"post-validation dirtiness repeated engine operation");}
   else{check(f.fence().terminal&&!f.owner.hasCommittedPresentation(),"stale concrete generation did not fail closed "+method);check(NativeBridge.destroyCalls==1,"stale operation session cleanup");}
  }cases++;
 }
 private static void terminalReports(){
  try(Fixture f=new Fixture(true)){
   f.ready();Throwable primary=new IllegalStateException("renderer primary");f.renderer().terminal(NativeEnvironmentV2.RendererCause.CAPTURE_FAILED,primary,null);
   check(f.owner.cleanupLedger().primary()==primary&&f.owner.cleanupLedger().rendererCause()==NativeEnvironmentV2.RendererCause.CAPTURE_FAILED,"typed cause lost");
   check(f.queue.queued()==1&&NativeBridge.destroyCalls==0,"report did not defer disposal tail");f.queue.drainAll(4);check(NativeBridge.destroyCalls==1&&f.renderer().disposals==1,"tail disposition repeated/missed");
   f.observer().rendererTerminal(null,null,new IllegalStateException("stale"),new Fatal("stale"));check(NativeBridge.destroyCalls==1,"stale report repeated disposition");
  }
  try(Fixture f=new Fixture(true)){
   f.ready();Throwable primary=new IllegalStateException("ordinary");Fatal fatal=new Fatal("fatal");check(thrown(()->f.renderer().terminal(NativeEnvironmentV2.RendererCause.CANCELLATION_FAILED,primary,fatal))==fatal,"reported fatal demoted");
   check(f.owner.cleanupLedger().primary()==primary&&f.owner.cleanupLedger().firstFatal()==fatal,"explicit primary/fatal lost");OwnerHostProbe.hook=null;check(thrown(()->f.queue.drainAll(4))==fatal,"tail fatal did not escape");
   check(NativeBridge.destroyCalls==1,"fatal report skipped engine cleanup");
   // Repeated close rethrows the retained fatal without repeating resources.
   check(thrown(f.owner::close)==fatal,"retained fatal lost");
  }catch(Fatal expected){/* AutoCloseable repeats the retained fatal; resources remain consumed. */}cases++;
 }
 private static void schedulingAndCleanup(){
  for(boolean throwing:new boolean[]{false,true})try(Fixture f=new Fixture(true)){
   if(throwing)f.queue.postFailure=new IllegalStateException("post");else f.queue.postResult=false;f.start();check(f.fence().terminal&&NativeBridge.createCalls==0,"failed post retried/opened");check(f.owner.cleanupLedger().cause()==NativeOwnerV2.Cause.SCHEDULING_FAILED,"failed post cause lost");
  }
  try(Fixture f=new Fixture(true)){
   f.ready();RuntimeException ordinary=new IllegalStateException("renderer dispose");Fatal fatal=new Fatal("destroy fatal");NativeBridge.destroyFailure=fatal;
   OwnerHostProbe.hook=(m,p)->{if(m.equals("Renderer.dispose")&&p.equals("entry")){OwnerHostProbe.hook=null;throw ordinary;}};
   check(thrown(f.owner::close)==fatal,"later cleanup fatal demoted");check(f.renderer().disposals==1&&NativeBridge.destroyCalls==1,"independent cleanup skipped");
   check(f.coordinator().cleanupLedger().rendererFailure()==ordinary&&f.coordinator().cleanupLedger().firstFatal()==fatal,"coordinator fixed diagnostics lost");
  }catch(Fatal expected){}cases++;
 }
 private static void unreportedCompletion(){
  Fatal fatal=new Fatal("completion bookkeeping");
  try(Fixture f=new Fixture(true,()->{throw fatal;})){
   f.start();check(thrown(()->f.queue.drainAll(4))==fatal,"completion fatal demoted");
   check(f.owner.cleanupLedger().coreCompletionUnreported(),"missing unreported core completion diagnostic");
   check(f.core().snapshot().operation()!=null&&f.core().snapshot().phase()==OwnerLifecycleV2.Phase.OPENING,"fallback fabricated core completion");
   check(f.fence().terminal&&NativeBridge.destroyCalls==1&&f.renderer().disposals==1,"fallback independent resource cleanup missed");
   check(thrown(f.owner::close)==fatal,"fallback revived or forgot fatal");
  }catch(Fatal expected){}cases++;
 }
 private static void exhaustionAndThreads(){
  try(Fixture f=new Fixture(true)){f.ready();f.fence().sealSerial=Long.MAX_VALUE;f.owner.onPause();check(f.fence().terminal&&f.fence().sealSerial==Long.MAX_VALUE,"serial wrapped");check(f.owner.cleanupLedger().cause()==NativeOwnerV2.Cause.SEAL_SERIAL_EXHAUSTED,"serial cause lost");}
  try(Fixture f=new Fixture(true)){f.ready();f.owner.close();Looper.hostSetMain(false);try{for(Runnable call:List.<Runnable>of(f.owner::onResume,f.owner::onPause,f.owner::onStop,f.owner::close,f.owner::hasCommittedPresentation,f.owner::cleanupLedger,()->f.observer().invalidate()))check(thrown(call) instanceof IllegalStateException,"stale entry skipped real thread check");}finally{Looper.hostReset();}}cases++;
 }
 public static void main(String[] args)throws Exception{descriptor=Files.readAllBytes(Path.of(args[0]));inertAndReadiness();staleAndWindow();inputAndRefresh();reentry();observerDuringOperation();terminalReports();schedulingAndCleanup();unreportedCompletion();exhaustionAndThreads();System.out.println("PASS actual owner/core/coordinator/observer closure A cases="+cases+" assertions="+checks+"; renderer leaf only, native runtime pending");}
}
