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
 private static byte[] descriptor;private static int checks,cases;private static final java.util.ArrayList<String> migrated=new java.util.ArrayList<>();
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
 private static void registrationTerminalCallback(){
  for(String phase:List.of("entry","beforeReturn"))try(Fixture f=new Fixture(true)){
   boolean[] reached={false};OwnerHostProbe.hook=(method,at)->{if(!reached[0]&&method.equals("Context.registerComponentCallbacks")&&at.equals(phase)){reached[0]=true;OwnerHostProbe.hook=null;check(f.observer()!=null,"observer not prepublished");f.owner.close();check(f.owner.cleanupLedger().unregister()==NativeOwnerV2.Outcome.DEFERRED,"inflight add disposition not deferred");}};
   f.start();check(reached[0]&&f.fence().terminal&&NativeBridge.createCalls==0,"registration callback opened engine");
   check(OwnerHostProbe.count("View.addOnLayoutChangeListener","entry")==0&&OwnerHostProbe.count("View.addOnAttachStateChangeListener","entry")==0,"registration acquired after terminal callback");
   check(OwnerHostProbe.count("Context.unregisterComponentCallbacks","entry")==1,"late inflight add not removed once");
  }cases++;
 }
 private static void registrationCoreFault(){
  for(String selectedPhase:List.of("entry","beforeReturn")){
   Fatal fatal=new Fatal("registration exact-core boundary");boolean[] reached={false};int[] coreFailures={0};
   try(Fixture f=new Fixture(true)){
    OwnerHostProbe.hook=(method,phase)->{if(!reached[0]&&method.equals("Context.registerComponentCallbacks")&&phase.equals(selectedPhase)){
     reached[0]=true;OwnerHostProbe.hook=null;Looper.beforeRead=()->{boolean actualCore=StackWalker.getInstance().walk(frames->frames.anyMatch(frame->frame.getClassName().equals("dev.mixer.android.OwnerLifecycleV2")&&(frame.getMethodName().equals("pause")||frame.getMethodName().equals("close"))));if(actualCore){coreFailures[0]++;throw fatal;}};
     try{check(caught(f.owner::onPause)==fatal,"exact core fault demoted during registration");}finally{Looper.beforeRead=null;}
     check(f.owner.cleanupLedger().coreCompletionUnreported()&&f.owner.cleanupLedger().unregister()==NativeOwnerV2.Outcome.DEFERRED,"registration emergency invented cleanup token or lost deferral");
    }};
    check(caught(f::start)==fatal,"registration core fatal lost at outer return");
    check(reached[0]&&coreFailures[0]==2&&f.fence().terminal,"real core pause and close not reached");
    check(OwnerHostProbe.count("View.addOnLayoutChangeListener","entry")==0&&OwnerHostProbe.count("Context.unregisterComponentCallbacks","entry")==1,"registration fallback acquired later slot or repeated late removal");
    check(NativeBridge.createCalls==0&&f.core().snapshot().operation()==null,"registration fallback fabricated operation/resource");
   }catch(Fatal expected){check(expected==fatal,"wrong registration fatal");}finally{Looper.hostReset();}cases++;
  }
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
    f.start();final boolean[] hit={false};OwnerHostProbe.hook=(m,p)->{if(!hit[0]&&m.equals(method)&&p.equals(phase)){hit[0]=true;OwnerHostProbe.hook=null;f.owner.close();check(!f.fence().drawAllowed&&!f.fence().inputAllowed,"terminal gates open at callback");check(NativeBridge.destroyCalls==0,"active resource destroyed before return");check(f.core().snapshot().operation()!=null&&!f.core().snapshot().closePending(),"unfinished operation fabricated close completion");}};
    f.queue.drainAll(4);check(hit[0],"reentry missed "+method);check(f.fence().terminal&&!f.owner.hasCommittedPresentation(),"terminal operation published");check(NativeBridge.commitCalls==0&&NativeBridge.destroyCalls==1,"late session not disposed once");
   }cases++;
  }
  try(Fixture f=new Fixture(true)){
   f.start();final boolean[] hit={false};OwnerHostProbe.hook=(m,p)->{if(!hit[0]&&m.equals("Renderer.attach")&&p.equals("entry")){hit[0]=true;OwnerHostProbe.hook=null;f.owner.onPause();check(!f.fence().terminal,"lifecycle dirty invented retirement");}};
   f.queue.drainAll(4);check(hit[0]&&f.owner.hasCommittedPresentation()&&NativeBridge.prepareCalls==1,"lifecycle dirty did not finish/coalesce refresh");check(f.queue.postCalls==2,"dirty operation did not post one later drain");
  }cases++;
 }
 private static void focusAdmission(){
  for(String state:List.of("focusLoss","dirty","terminal","fatal")){
   Fatal fatal=new Fatal("fresh focus fatal");
   try(Fixture f=new Fixture(true)){
    f.ready();byte[] event=UiPacket.decode((byte[])field(f.coordinator(),"committedPacket")).event("button","1","activate",null);int calls=NativeBridge.prepareCalls;boolean[] reached={false,false};
    f.root.windowFocus=false;OwnerHostProbe.hook=(method,phase)->{
     var trace=OwnerHostProbe.lastEvent();boolean fresh=trace.productionFrames.stream().anyMatch(site->site.className().equals("dev.mixer.android.NativeOwnerV2")&&site.methodName().equals("seedFocus"));
     if(!reached[0]&&fresh&&method.equals("View.hasWindowFocus")&&phase.equals("entry")){
      reached[0]=true;check(!f.fence().drawAllowed&&!f.fence().inputAllowed&&!f.renderer().currentOpen&&!f.renderer().pendingOpen,"fresh focus callback entered with open gates");
      f.renderer().emit(event);check(NativeBridge.prepareCalls==calls,"fresh focus callback reentered input");
      if(state.equals("terminal"))f.owner.close();else if(!state.equals("focusLoss"))f.owner.onPause();if(state.equals("fatal"))throw fatal;
     }
     if(fresh&&method.equals("Handler.post")&&phase.equals("entry")){
      reached[1]=true;check(!f.fence().drawAllowed&&!f.fence().inputAllowed&&!f.renderer().currentOpen&&!f.renderer().pendingOpen,"focus drain posted before sealing");
     }
    };
    Throwable escaped=caught(()->f.renderer().emit(event));OwnerHostProbe.hook=null;check(reached[0]&&NativeBridge.prepareCalls==calls,"fresh focus input changed engine or missed hook");
    if(state.equals("fatal")){check(escaped==fatal&&f.fence().terminal,"fresh focus fatal swallowed");}
    else if(state.equals("terminal"))check(escaped==null&&f.fence().terminal,"terminal focus callback reopened owner");
    else {check(escaped==null&&reached[1]&&f.core().snapshot().dirty()&&!f.core().snapshot().focused()&&f.queue.queued()==1,"focus loss did not coalesce exact dirty core");f.queue.drainAll(4);check(NativeBridge.prepareCalls==calls&&!f.fence().inputAllowed&&f.fence().drawAllowed,"focus refresh advanced engine or opened input");}
   }catch(Fatal expected){check(expected==fatal,"wrong focus fatal");}cases++;
  }
  try(Fixture f=new Fixture(true)){
   f.ready();long serial=f.fence().sealSerial;int cancellations=f.renderer().cancellations;boolean[] posted={false};
   List<OwnerLifecycleV2.Decision> decisions=f.core().focusChanged(f.core().lifetime(),false);
   OwnerHostProbe.hook=(method,phase)->{if(method.equals("Handler.post")&&phase.equals("entry")){posted[0]=true;check(!f.fence().drawAllowed&&!f.fence().inputAllowed&&!f.renderer().currentOpen&&!f.renderer().pendingOpen,"actual nonterminal SEAL effect did not close gates before post");}};
   try{var process=NativeOwnerV2.class.getDeclaredMethod("process",List.class,byte[].class);process.setAccessible(true);process.invoke(f.owner,decisions,null);}catch(ReflectiveOperationException failure){throw new AssertionError(failure);}finally{OwnerHostProbe.hook=null;}
   check(posted[0]&&f.fence().sealSerial==serial&&f.renderer().cancellations==cancellations,"SEAL effect redundantly cancelled or advanced serial");f.queue.drainAll(4);check(f.owner.hasCommittedPresentation()&&!f.fence().inputAllowed,"nonterminal SEAL effect changed presentation lifecycle");
  }cases++;
 }
 private static void completionPublication(){
  for(boolean dirty:new boolean[]{false,true}){
   Fixture[] selected={null};boolean[] reached={false};
   try(Fixture f=new Fixture(true,()->{Fixture current=selected[0];if(!reached[0]){reached[0]=true;check(!current.renderer().currentOpen&&!current.renderer().pendingOpen&&!current.fence().drawAllowed&&!current.fence().inputAllowed,"finish opened before real core completion");if(dirty)current.owner.onPause();}})){
    selected[0]=f;f.start();f.queue.drainOne();check(reached[0]&&NativeBridge.commitCalls==1&&f.core().snapshot().phase()==OwnerLifecycleV2.Phase.LIVE&&field(f.coordinator(),"committedPacket")!=null,"completion hook lost successful finish");
    if(dirty){check(!f.renderer().currentOpen&&f.core().snapshot().dirty()&&f.queue.queued()==1,"dirty completion opened concrete gate before follow-up");f.queue.drainAll(4);}
    check(f.renderer().currentOpen&&f.fence().drawAllowed&&!f.core().snapshot().dirty(),"clean core completion did not publish concrete gate");check(NativeBridge.prepareCalls==1&&NativeBridge.commitCalls==1,"dirty completion reissued engine operation");
   }cases++;
  }
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
 private static void latePostCleanup(){
  for(String phase:List.of("entry","beforeReturn"))for(boolean fatalKind:new boolean[]{false,true}){
   Throwable failure=fatalKind?new Fatal("post "+phase):new IllegalStateException("post "+phase);
   try(Fixture f=new Fixture(true)){
    OwnerHostProbe.hook=(method,at)->{if(method.equals("Handler.post")&&at.equals(phase)){OwnerHostProbe.hook=null;OwnerHostProbe.fail(failure);}};
    Throwable escaped=caught(f::start);check((!fatalKind&&escaped==null)||(fatalKind&&escaped==failure),"post throwable identity lost");check(f.owner.cleanupLedger().primary()==failure&&f.owner.cleanupLedger().firstFatal()==(fatalKind?failure:null),"post primary/fatal slots lost");
    check(f.fence().terminal&&NativeBridge.createCalls==0&&f.queue.queued()==0&&f.queue.removeCalls==1&&f.owner.cleanupLedger().handler()==NativeOwnerV2.Outcome.RETURNED,"possibly enqueued failed post was not removed");
   }catch(Fatal expected){check(expected==failure,"wrong post fatal");}cases++;
  }
  for(String phase:List.of("entry","beforeReturn"))try(Fixture f=new Fixture(true)){
   boolean[] reached={false};OwnerHostProbe.hook=(method,at)->{if(!reached[0]&&method.equals("Handler.post")&&at.equals(phase)){reached[0]=true;f.owner.close();check(f.owner.cleanupLedger().handler()==NativeOwnerV2.Outcome.DEFERRED&&f.queue.removeCalls==0,"inflight post cleanup claimed early return");}};
   f.start();OwnerHostProbe.hook=null;check(reached[0]&&f.queue.queued()==0&&f.queue.removeCalls==1&&f.owner.cleanupLedger().handler()==NativeOwnerV2.Outcome.RETURNED&&NativeBridge.createCalls==0,"late terminal post cleanup missing");
  }cases++;
  for(boolean fatalKind:new boolean[]{false,true}){
   RuntimeException primary=new IllegalStateException("enqueue then throw");Throwable removal=fatalKind?new Fatal("remove fatal"):new IllegalStateException("remove ordinary");
   try(Fixture f=new Fixture(true)){
    f.queue.removeFailure=removal;OwnerHostProbe.hook=(method,phase)->{if(method.equals("Handler.post")&&phase.equals("beforeReturn")){OwnerHostProbe.hook=null;throw primary;}};Throwable escaped=caught(f::start);
    check(f.owner.cleanupLedger().primary()==primary&&f.owner.cleanupLedger().handlerFailure()==removal&&f.owner.cleanupLedger().firstFatal()==(fatalKind?removal:null),"failed removal primary/fatal identities lost");check(f.owner.cleanupLedger().handler()==NativeOwnerV2.Outcome.FAILED_UNCERTAIN&&f.queue.removeCalls==1&&f.queue.queued()==1&&NativeBridge.createCalls==0,"failed removal claimed success");
    check((fatalKind&&escaped==removal)||(!fatalKind&&escaped==null),"failed removal fatal swallowed");f.queue.removeFailure=null;f.queue.drainAll(4);check(NativeBridge.createCalls==0,"failed removal stale work acquired engine");
   }catch(Fatal expected){check(expected==removal,"wrong remove fatal");}cases++;
  }
  try(Fixture f=new Fixture(true)){
   Runnable[] newer={null};boolean[] reached={false};OwnerHostProbe.hook=(method,phase)->{if(!reached[0]&&method.equals("Handler.post")&&phase.equals("entry")){reached[0]=true;OwnerHostProbe.hook=null;((Runnable)field(f.owner,"queued")).run();check(f.owner.hasCommittedPresentation(),"controlled explicit delivery did not open");f.owner.onPause();newer[0]=(Runnable)field(f.owner,"queued");}};
   f.start();check(reached[0]&&newer[0]!=null&&f.queue.queued()==1&&f.queue.snapshot().get(0)==newer[0]&&field(f.owner,"queued")==newer[0],"old post cleanup removed newer identity");check(f.queue.removeCalls==1&&f.owner.cleanupLedger().handler()==NativeOwnerV2.Outcome.RETURNED,"old late post cleanup did not run");f.queue.drainAll(4);check(NativeBridge.prepareCalls==1&&f.owner.hasCommittedPresentation(),"newer refresh lost or advanced engine");
  }cases++;
  try(Fixture f=new Fixture(true)){
   RuntimeException primary=new IllegalStateException("post primary");boolean[] reentered={false};OwnerHostProbe.hook=(method,phase)->{if(method.equals("Handler.post")&&phase.equals("beforeReturn"))throw primary;if(!reentered[0]&&method.equals("Handler.removeCallbacks")&&phase.equals("entry")){reentered[0]=true;f.owner.close();}};
   f.start();OwnerHostProbe.hook=null;check(reentered[0]&&f.queue.removeCalls==1&&f.queue.queued()==0&&f.owner.cleanupLedger().handler()==NativeOwnerV2.Outcome.RETURNED&&f.owner.cleanupLedger().primary()==primary,"cleanup reentry repeated or lost post failure");
  }cases++;
 }
 private record Stage(String old,String method,String phase) {}
 private static final List<Stage> stages=List.of(
  new Stage("capture.installed","Renderer.captureInstalled","entry"),new Stage("capture.environment","Renderer.captureEnvironment","entry"),
  new Stage("engine.prepare.before","NativeBridge.prepareV2","entry"),new Stage("engine.prepare.delivery","NativeBridge.prepareV2","beforeReturn"),
  new Stage("engine.token","NativeBridge.Candidate.token","entry"),new Stage("engine.packet.copy","NativeBridge.Candidate.packet","entry"),
  new Stage("renderer.prepare","Renderer.prepare","entry"),new Stage("environment.current","View.getWidth","entry"),
  new Stage("renderer.attach.preflight","Renderer.attach","entry"),new Stage("renderer.attach.mutation","Renderer.attach","beforeReturn"),
  new Stage("renderer.attach.return","Renderer.attach","beforeReturn"),new Stage("renderer.validate","Renderer.validate","entry"),new Stage("engine.commit.before","NativeBridge.commitV2","entry"));
 private static Throwable caught(Runnable call){try{call.run();return null;}catch(RuntimeException|Error failure){return failure;}}
 private static boolean selected(Stage stage,String method,String phase){return stage.method().equals(method)&&stage.phase().equals(phase)&&(!stage.old().equals("environment.current")||OwnerHostProbe.lastEvent().productionFrames.stream().anyMatch(frame->frame.methodName().equals("current")&&frame.className().equals("dev.mixer.android.NativeEnvironmentV2")));}
 private static void migratedFaults(){
  for(String mode:List.of("initial","input","refresh"))for(Stage stage:stages){
   if(mode.equals("refresh")&&stage.old().startsWith("engine."))continue;
   for(boolean error:new boolean[]{false,true}){
    String id="migrated."+mode+"."+stage.old()+"."+(error?"fatal":"ordinary");Fatal fatal=new Fatal(id);RuntimeException ordinary=new IllegalStateException(id);Throwable fault=error?fatal:ordinary;
    try(Fixture f=new Fixture(true)){
     if(!mode.equals("initial"))f.ready();int prepared=NativeBridge.prepareCalls,committed=NativeBridge.commitCalls;boolean[] reached={false};
     OwnerHostProbe.hook=(method,phase)->{if(!reached[0]&&selected(stage,method,phase)){reached[0]=true;OwnerHostProbe.hook=null;OwnerHostProbe.fail(fault);}};
     if(mode.equals("initial"))f.start();else if(mode.equals("refresh"))f.owner.onPause();else{NativeBridge.preparedPacket=packet(2);caught(()->f.renderer().emit(new byte[]{7}));}
     Throwable escaped=caught(()->f.queue.drainAll(4));OwnerHostProbe.hook=null;
     check(reached[0],"old vector missed "+id);check(f.fence().terminal&&!f.owner.hasCommittedPresentation(),"old failed completion revived "+id);
     check(stage.old().equals("environment.current")&&!error?f.owner.cleanupLedger().primary()!=null:f.owner.cleanupLedger().primary()==fault,"old vector primary identity "+id);if(error)check(escaped==fatal||f.owner.cleanupLedger().firstFatal()==fatal,"old vector fatal demoted "+id);
     check(NativeBridge.commitCalls==committed,"old vector committed after precommit failure "+id);check(NativeBridge.destroyCalls==1&&f.renderer().disposals==1,"old vector independent disposition "+id);
     if(mode.equals("refresh"))check(NativeBridge.prepareCalls==prepared&&NativeBridge.abortCalls==0,"refresh old vector engine work "+id);
     migrated.add(id);
    }catch(Fatal expected){check(expected==fatal,"wrong retained fatal "+id);}cases++;
   }
  }
 }
 private static void migratedCommitAndCleanup(){
  try(Fixture f=new Fixture(true)){NativeBridge.preparedToken=Long.MIN_VALUE+23;byte[] original=NativeBridge.preparedPacket;f.ready();check(NativeBridge.lastToken==Long.MIN_VALUE+23,"opaque sign-bit token changed");check(f.renderer().preparedReference!=original&&Arrays.equals(f.renderer().preparedReference,original),"defensive candidate packet copy lost");migrated.add("migrated.success.sign-bit-token-copy");}cases++;
  for(String mode:List.of("initial","input"))for(int code:new int[]{1,2,3,4,5,6,7,-1,8,Integer.MAX_VALUE})try(Fixture f=new Fixture(true)){
   if(mode.equals("input"))f.ready();int effects=NativeBridge.effects;NativeBridge.commitStatus=code;
   if(mode.equals("initial")){f.start();f.queue.drainAll(4);}else{NativeBridge.preparedPacket=packet(2);f.renderer().emit(new byte[]{7});}
   check(f.fence().terminal&&NativeBridge.effects==effects,"commit rejection failed closed "+code);check(NativeBridge.abortCalls==(code>=1&&code<=7?1:0),"known vs unknown commit abort "+code);
   if(code==2)check(f.coordinator().cleanupLedger().rollback()==NativeCoordinatorV2.Outcome.NOT_REQUESTED,"status2 rolled back unusable candidate");
   check(NativeBridge.destroyCalls==1&&f.renderer().disposals==1,"commit rejection leaked disposition");migrated.add("migrated."+mode+".commit-status."+code);cases++;
  }
  for(String phase:List.of("entry","beforeReturn"))for(boolean error:new boolean[]{false,true}){
   Fatal fatal=new Fatal("unknown commit");Throwable fault=error?fatal:new IllegalStateException("unknown commit");
   try(Fixture f=new Fixture(true)){
    OwnerHostProbe.hook=(method,at)->{if(method.equals("NativeBridge.commitV2")&&at.equals(phase)){OwnerHostProbe.hook=null;OwnerHostProbe.fail(fault);}};f.start();caught(()->f.queue.drainAll(4));OwnerHostProbe.hook=null;
    check(f.fence().terminal&&NativeBridge.abortCalls==0,"ambiguous commit aborted or revived");check(NativeBridge.effects==(phase.equals("beforeReturn")?1:0),"before/after unknown effect not distinguished");migrated.add("migrated.unknown-commit."+phase+"."+error);
   }catch(Fatal expected){check(expected==fatal,"unknown commit fatal lost");}cases++;
  }
  for(int status:new int[]{0,1,2,3,4,5,6,7,99})try(Fixture f=new Fixture(true)){
   NativeBridge.abortStatus=status;OwnerHostProbe.hook=(method,phase)->{if(method.equals("Renderer.validate")&&phase.equals("entry")){OwnerHostProbe.hook=null;throw new IllegalStateException("validation");}};f.start();f.queue.drainAll(4);OwnerHostProbe.hook=null;
   check(f.fence().terminal&&NativeBridge.abortCalls==1,"abort disposition retry");check(f.coordinator().cleanupLedger().abort()==(status==0?NativeCoordinatorV2.Outcome.RETURNED:NativeCoordinatorV2.Outcome.FAILED_UNCERTAIN),"abort status ledger");
   check(NativeBridge.destroyCalls==1,"abort status leaked session");migrated.add("migrated.abort-status."+status);cases++;
  }
  for(String cleanup:List.of("NativeBridge.abortV2","Renderer.rollback","Renderer.discard"))for(String phase:List.of("entry","beforeReturn"))for(boolean error:new boolean[]{false,true}){
   Fatal fatal=new Fatal("cleanup fatal");Throwable fault=error?fatal:new IllegalStateException("cleanup ordinary");RuntimeException primary=new IllegalStateException("validation primary");
   try(Fixture f=new Fixture(true)){
    boolean discard=cleanup.equals("Renderer.discard");boolean[] failed={false};
    OwnerHostProbe.hook=(method,at)->{
     if(!failed[0]&&method.equals(discard?"Renderer.prepare":"Renderer.validate")&&at.equals(discard?"beforeReturn":"entry")){failed[0]=true;if(discard)f.activity.getResources().configuration.uiMode=android.content.res.Configuration.UI_MODE_NIGHT_YES;else throw primary;}
     if(method.equals(cleanup)&&at.equals(phase))OwnerHostProbe.fail(fault);
    };f.start();caught(()->f.queue.drainAll(4));OwnerHostProbe.hook=null;
    NativeCoordinatorV2.CleanupLedger ledger=f.coordinator().cleanupLedger();Throwable retained=cleanup.equals("NativeBridge.abortV2")?ledger.abortFailure():cleanup.equals("Renderer.rollback")?ledger.rollbackFailure():ledger.discardFailure();
    check(retained==fault,"cleanup secondary diagnostic lost "+cleanup);check(discard?f.owner.cleanupLedger().primary()==ledger.primary():f.owner.cleanupLedger().primary()==primary,"cleanup replaced primary");
    if(error)check(f.owner.cleanupLedger().firstFatal()==fatal,"cleanup fatal demoted");check(NativeBridge.destroyCalls==1,"cleanup vector leaked engine");migrated.add("migrated.cleanup."+cleanup+"."+phase+"."+error);
   }catch(Fatal expected){check(expected==fatal,"cleanup fatal identity");}cases++;
  }
  for(String nativePhase:List.of("entry","beforeReturn"))for(String enginePhase:List.of("entry","beforeReturn")){
   Fatal fatal=new Fatal("destroy fatal");RuntimeException primary=new IllegalStateException("dispose ordinary");
   try(Fixture f=new Fixture(true)){
    f.ready();OwnerHostProbe.hook=(method,phase)->{if(method.equals("Renderer.dispose")&&phase.equals(nativePhase))throw primary;if(method.equals("NativeBridge.destroy")&&phase.equals(enginePhase))throw fatal;};caught(f.owner::close);OwnerHostProbe.hook=null;
    check(f.renderer().disposals==1&&OwnerHostProbe.count("NativeBridge.destroy","entry")==1,"combined cleanup owners not attempted");check(f.coordinator().cleanupLedger().rendererFailure()==primary&&f.coordinator().cleanupLedger().engineFailure()==fatal,"combined cleanup diagnostics");caught(f.owner::close);check(OwnerHostProbe.count("NativeBridge.destroy","entry")==1,"combined cleanup repeated");migrated.add("migrated.independent-disposal."+nativePhase+"."+enginePhase);
   }catch(Fatal expected){check(expected==fatal,"combined cleanup fatal identity");}cases++;
  }
  for(boolean nullCandidate:new boolean[]{false,true})try(Fixture f=new Fixture(true)){
   NativeBridge.nullCandidate=nullCandidate;if(!nullCandidate)NativeBridge.preparedToken=0;f.start();f.queue.drainAll(4);
   check(f.fence().terminal&&NativeBridge.abortCalls==0&&NativeBridge.destroyCalls==1,"null/zero delivery invented token");migrated.add("migrated.invalid-candidate."+nullCandidate);cases++;
  }
 }
 private static void migratedCombinedVectors(){
  for(String mode:List.of("initial","input","refresh"))for(String cleanup:List.of("NativeBridge.abortV2","Renderer.rollback","Renderer.discard","Renderer.dispose","NativeBridge.destroy")){
   if(mode.equals("refresh")&&cleanup.equals("NativeBridge.abortV2"))continue;
   Fatal fatal=new Fatal("combined "+mode+" / "+cleanup);RuntimeException primary=new IllegalStateException("operation validation");
   try(Fixture f=new Fixture(true)){
    if(!mode.equals("initial"))f.ready();boolean stale=cleanup.equals("Renderer.discard");boolean[] injected={false};
    OwnerHostProbe.hook=(method,phase)->{
     if(!injected[0]&&method.equals(stale?"Renderer.prepare":"Renderer.validate")&&phase.equals(stale?"beforeReturn":"entry")){injected[0]=true;if(stale)f.activity.getResources().configuration.uiMode=android.content.res.Configuration.UI_MODE_NIGHT_YES;else throw primary;}
     if(method.equals(cleanup)&&phase.equals("entry"))throw fatal;
    };
    if(mode.equals("initial"))f.start();else if(mode.equals("input")){NativeBridge.preparedPacket=packet(2);caught(()->f.renderer().emit(new byte[]{7}));}else f.owner.onPause();
    caught(()->f.queue.drainAll(4));OwnerHostProbe.hook=null;
    check(injected[0]&&f.fence().terminal&&f.owner.cleanupLedger().firstFatal()==fatal,"combined callback cleanup fatal lost "+mode+" / "+cleanup);
    check(stale?f.owner.cleanupLedger().primary()==f.coordinator().cleanupLedger().primary():f.owner.cleanupLedger().primary()==primary,"combined callback cleanup replaced ordinary primary");
    check(f.renderer().disposals==1&&OwnerHostProbe.count("NativeBridge.destroy","entry")==1,"combined transaction cleanup skipped owner");
    migrated.add("migrated.combined."+mode+"."+cleanup);
   }catch(Fatal expected){check(expected==fatal,"combined callback fatal identity");}cases++;
  }
  for(String phase:List.of("entry","beforeReturn"))try(Fixture f=new Fixture(true)){
   RuntimeException primary=new IllegalStateException("attach failure"),abort=new IllegalStateException("abort failure");
   OwnerHostProbe.hook=(method,at)->{if(method.equals("Renderer.attach")&&at.equals(phase))throw primary;if(method.equals("NativeBridge.abortV2")&&at.equals("entry"))throw abort;};
   f.start();f.queue.drainAll(4);OwnerHostProbe.hook=null;check(f.fence().terminal&&f.owner.cleanupLedger().primary()==primary&&f.coordinator().cleanupLedger().abortFailure()==abort,"attach+abort diagnostics lost");
   check(f.coordinator().cleanupLedger().discard()==NativeCoordinatorV2.Outcome.NOT_REQUESTED&&f.coordinator().cleanupLedger().rollback()==NativeCoordinatorV2.Outcome.NOT_REQUESTED,"throwing attachment disposition repeated");migrated.add("migrated.attach-abort."+phase);cases++;
  }
  Fatal fatal=new Fatal("unknown commit destroy");RuntimeException operation=new IllegalStateException("unknown commit"),dispose=new IllegalStateException("dispose");
  try(Fixture f=new Fixture(true)){
   OwnerHostProbe.hook=(method,phase)->{if(method.equals("NativeBridge.commitV2")&&phase.equals("beforeReturn"))throw operation;if(method.equals("Renderer.dispose")&&phase.equals("entry"))throw dispose;if(method.equals("NativeBridge.destroy")&&phase.equals("entry"))throw fatal;};
   f.start();caught(()->f.queue.drainAll(4));OwnerHostProbe.hook=null;var ledger=f.coordinator().cleanupLedger();check(NativeBridge.effects==1&&NativeBridge.abortCalls==0&&ledger.primary()==operation&&ledger.rendererFailure()==dispose&&ledger.engineFailure()==fatal,"ambiguous commit combined disposition diagnostics");check(f.owner.cleanupLedger().primary()==operation&&f.owner.cleanupLedger().firstFatal()==fatal,"ambiguous commit combined owner diagnostics");migrated.add("migrated.unknown-commit.independent-disposal");
  }catch(Fatal expected){check(expected==fatal,"unknown commit cleanup fatal identity");}cases++;
 }
 private static void migratedHiddenOutcomesAndInputFatal(){
  for(int status:new int[]{-1,8,Integer.MAX_VALUE})for(boolean effect:new boolean[]{false,true})try(Fixture f=new Fixture(true)){
   NativeBridge.commitStatus=status;OwnerHostProbe.hook=(method,phase)->{if(method.equals("NativeBridge.commitV2")&&phase.equals("beforeReturn")){OwnerHostProbe.hook=null;if(effect)NativeBridge.effects++;}};
   f.start();f.queue.drainAll(4);check(f.fence().terminal&&NativeBridge.effects==(effect?1:0)&&NativeBridge.abortCalls==0&&NativeBridge.destroyCalls==1,"hidden unexpected status outcome was reused");migrated.add("migrated.hidden-status."+status+"."+effect);cases++;
  }
  for(String point:List.of("packet-copy","commit-after")){
   Fatal fatal=new Fatal("input "+point);try(Fixture f=new Fixture(true)){
    f.ready();NativeBridge.preparedPacket=packet(2);OwnerHostProbe.hook=(method,phase)->{if(method.equals(point.equals("packet-copy")?"NativeBridge.Candidate.packet":"NativeBridge.commitV2")&&phase.equals(point.equals("packet-copy")?"entry":"beforeReturn")){OwnerHostProbe.hook=null;throw fatal;}};
    check(caught(()->f.renderer().emit(new byte[]{7}))==fatal,"native callback fatal swallowed "+point);check(f.fence().terminal&&f.owner.cleanupLedger().firstFatal()==fatal&&NativeBridge.destroyCalls==1,"native fatal disposition "+point);migrated.add("migrated.input.fatal."+point);
   }catch(Fatal expected){check(expected==fatal,"native callback fatal identity");}cases++;
  }
 }
 private static void migratedLifecycle(){
  for(String action:List.of("initial","input","environment","close","nativeInput"))for(String stage:List.of("Renderer.captureInstalled","Renderer.prepare","Renderer.validate","NativeBridge.commitV2"))try(Fixture f=new Fixture(true)){
   boolean[] reached={false};OwnerHostProbe.hook=(method,phase)->{if(!reached[0]&&method.equals(stage)&&phase.equals("entry")){reached[0]=true;OwnerHostProbe.hook=null;int engine=NativeBridge.prepareCalls;
    if(action.equals("nativeInput"))f.renderer().emit(new byte[]{1});else check(caught(switch(action){case "initial"->f.coordinator()::renderInitial;case "input"->()->f.coordinator().dispatchInput(new byte[]{1});case "environment"->f.coordinator()::refreshEnvironment;default->f.coordinator()::closeFromOwner;}) instanceof IllegalStateException,"reentrant operation admitted");
    check(NativeBridge.prepareCalls==engine,"reentrant callback performed engine work");}};
   f.start();f.queue.drainAll(4);check(reached[0]&&f.owner.hasCommittedPresentation(),"reentry changed outer accepted operation");migrated.add("migrated.reentry."+action+"."+stage);cases++;
  }
  for(String phase:List.of("entry","beforeReturn"))for(boolean error:new boolean[]{false,true}){
   Fatal fatal=new Fatal("create fatal");Throwable fault=error?fatal:new IllegalStateException("create ordinary");
   try(Fixture f=new Fixture(true)){OwnerHostProbe.hook=(method,at)->{if(method.equals("NativeBridge.create")&&at.equals(phase)){OwnerHostProbe.hook=null;OwnerHostProbe.fail(fault);}};f.start();caught(()->f.queue.drainAll(4));check(f.fence().terminal&&f.renderer().disposals==1&&NativeBridge.destroyCalls==0,"create failure disposition");migrated.add("migrated.create."+phase+"."+error);}catch(Fatal expected){check(expected==fatal,"create fatal identity");}cases++;
  }
  try(Fixture f=new Fixture(true)){NativeBridge.createResult=0;f.start();f.queue.drainAll(4);check(f.fence().terminal&&NativeBridge.destroyCalls==0&&f.renderer().disposals==1,"zero handle disposed nonexistent engine");migrated.add("migrated.create.zero");}cases++;
 }
 private static void cancellationLedger(){
  try(Fixture f=new Fixture(true)){
   boolean[] reached={false};f.start();OwnerHostProbe.hook=(method,phase)->{if(!reached[0]&&method.equals("Renderer.attach")&&phase.equals("entry")){
    reached[0]=true;OwnerHostProbe.hook=null;f.owner.onPause();
    check(f.owner.cleanupLedger().input()==NativeOwnerV2.Outcome.RETURNED&&!f.coordinator().inputCancellationInProgress(),"completed active cancellation mislabeled in progress");
    check(f.coordinator().busyForOwnerDisposal()&&f.fence().operation!=null&&NativeBridge.destroyCalls==0,"active disposal distinction lost");
   }};f.queue.drainAll(4);check(reached[0]&&f.owner.hasCommittedPresentation()&&f.owner.cleanupLedger().input()==NativeOwnerV2.Outcome.RETURNED,"active cancellation final outer result lost");
  }cases++;
  try(Fixture f=new Fixture(true)){
   f.ready();boolean[] reached={false};int before=f.renderer().cancellations;OwnerHostProbe.hook=(method,phase)->{if(!reached[0]&&method.equals("Renderer.cancelInput")&&phase.equals("entry")){
    reached[0]=true;OwnerHostProbe.hook=null;f.owner.onPause();check(f.owner.cleanupLedger().input()==NativeOwnerV2.Outcome.IN_PROGRESS&&f.coordinator().inputCancellationInProgress(),"recursive cancellation did not report actual in progress");check(f.renderer().cancellations==before+1,"recursive bridge restarted renderer pass");
   }};f.owner.onPause();check(reached[0]&&f.owner.cleanupLedger().input()==NativeOwnerV2.Outcome.RETURNED&&!f.coordinator().inputCancellationInProgress(),"outer cancellation failed to replace recursive status");check(!f.coordinator().busyForOwnerDisposal()&&NativeBridge.destroyCalls==0,"returned cancellation invented disposal");
  }cases++;
  try(Fixture f=new Fixture(true)){
   f.ready();boolean[] reached={false};OwnerHostProbe.hook=(method,phase)->{if(method.equals("Renderer.terminal.beforeUnwind")){
    reached[0]=true;OwnerHostProbe.hook=null;check(f.fence().rendererReportActive&&f.owner.cleanupLedger().input()==NativeOwnerV2.Outcome.RETURNED&&!f.coordinator().inputCancellationInProgress(),"completed report-frame cancellation mislabeled");check(f.coordinator().busyForOwnerDisposal()&&f.owner.cleanupLedger().coordinator()==NativeOwnerV2.Outcome.DEFERRED&&NativeBridge.destroyCalls==0,"report disposition not independently deferred");
   }};f.renderer().terminal(NativeEnvironmentV2.RendererCause.TERMINAL_VALIDATION_FAILED,null,null);check(reached[0]&&f.owner.cleanupLedger().input()==NativeOwnerV2.Outcome.RETURNED&&f.queue.queued()==1,"report cancellation outer result");f.queue.drainAll(4);check(f.owner.cleanupLedger().coordinator()==NativeOwnerV2.Outcome.RETURNED&&f.owner.cleanupLedger().input()==NativeOwnerV2.Outcome.RETURNED&&NativeBridge.destroyCalls==1,"report tail conflated cancellation and disposal");
   Looper.hostSetMain(false);try{check(caught(f.coordinator()::inputCancellationInProgress) instanceof IllegalStateException,"stale cancellation status skipped main first");}finally{Looper.hostReset();}
  }cases++;
 }
 private static void successfulDispositionAfterFailure(){
  try(Fixture f=new Fixture(true)){
   RuntimeException primary=new IllegalStateException("prepare operation primary");NativeBridge.prepareFailure=primary;
   f.start();f.queue.drainAll(4);NativeCoordinatorV2.CleanupLedger disposition=f.coordinator().cleanupLedger();
   check(f.fence().terminal&&disposition.primary()==primary&&f.owner.cleanupLedger().primary()==primary,"operation primary identity lost");
   check(disposition.renderer()==NativeCoordinatorV2.Outcome.RETURNED&&disposition.engine()==NativeCoordinatorV2.Outcome.RETURNED,"successful release slot mislabeled");
   check(f.owner.cleanupLedger().coordinator()==NativeOwnerV2.Outcome.RETURNED&&f.owner.cleanupLedger().coordinatorFailure()==null,"operation failure mislabeled as disposal failure");
   check(NativeBridge.destroyCalls==1&&f.renderer().disposals==1,"disposition repeated release");
  }cases++;
 }
 private static void unreportedCompletion(){
  for(String mode:List.of("initial","input","refresh")){
   Fatal fatal=new Fatal("completion bookkeeping "+mode);boolean[] armed={false};
   try(Fixture f=new Fixture(true,()->{if(armed[0])throw fatal;})){
    NativeRenderer[] observed={null};OwnerHostProbe.hook=(method,phase)->{if(method.equals("Renderer.prepare")&&phase.equals("entry"))observed[0]=f.renderer();};
    if(!mode.equals("initial"))f.ready();armed[0]=true;Throwable escaped;
    if(mode.equals("initial")){f.start();escaped=caught(()->f.queue.drainAll(4));}else if(mode.equals("input")){NativeBridge.preparedPacket=packet(2);escaped=caught(()->f.renderer().emit(new byte[]{7}));}else{f.owner.onPause();escaped=caught(()->f.queue.drainAll(4));}
    check(escaped==fatal,"completion fatal demoted");check(f.owner.cleanupLedger().coreCompletionUnreported(),"missing unreported core completion diagnostic");
    OwnerLifecycleV2.Phase expected=mode.equals("initial")?OwnerLifecycleV2.Phase.OPENING:mode.equals("input")?OwnerLifecycleV2.Phase.INPUTTING:OwnerLifecycleV2.Phase.REFRESHING;
    check(f.core().snapshot().operation()!=null&&f.core().snapshot().phase()==expected,"fallback fabricated core completion");
    check(f.fence().terminal&&NativeBridge.destroyCalls==1&&observed[0]!=null&&observed[0].disposals==1,"fallback independent resource cleanup missed");
    check(thrown(f.owner::close)==fatal,"fallback revived or forgot fatal");migrated.add("migrated.completion-bookkeeping."+mode);
   }catch(Fatal expected){check(expected==fatal,"completion fatal identity");}cases++;
  }
 }
 private static void exhaustionAndThreads(){
  try(Fixture f=new Fixture(true)){f.ready();f.fence().sealSerial=Long.MAX_VALUE;f.owner.onPause();check(f.fence().terminal&&f.fence().sealSerial==Long.MAX_VALUE,"serial wrapped");check(f.owner.cleanupLedger().cause()==NativeOwnerV2.Cause.SEAL_SERIAL_EXHAUSTED,"serial cause lost");}
  try(Fixture f=new Fixture(true)){f.ready();NativeCoordinatorV2 coordinator=f.coordinator();check(caught(coordinator::renderInitial) instanceof IllegalStateException,"ownerless duplicate initial admitted");check(caught(()->coordinator.dispatchInput(new byte[]{1})) instanceof IllegalStateException,"programmatic input bypass admitted");check(caught(coordinator::refreshEnvironment) instanceof IllegalStateException,"programmatic refresh bypass admitted");f.owner.close();Looper.hostSetMain(false);try{for(Runnable call:List.<Runnable>of(coordinator::renderInitial,()->coordinator.dispatchInput(new byte[]{1}),coordinator::refreshEnvironment,coordinator::closeFromOwner,coordinator::isRetired,coordinator::hasCommittedPresentation,coordinator::cleanupLedger,f.owner::onResume,f.owner::onPause,f.owner::onStop,f.owner::close,f.owner::hasCommittedPresentation,f.owner::cleanupLedger,()->f.observer().invalidate()))check(thrown(call) instanceof IllegalStateException,"stale entry skipped real thread check");}finally{Looper.hostReset();}}cases++;
 }
 public static void main(String[] args)throws Exception{descriptor=Files.readAllBytes(Path.of(args[0]));inertAndReadiness();registrationTerminalCallback();registrationCoreFault();staleAndWindow();inputAndRefresh();reentry();focusAdmission();completionPublication();observerDuringOperation();terminalReports();schedulingAndCleanup();latePostCleanup();migratedFaults();migratedCommitAndCleanup();migratedCombinedVectors();migratedHiddenOutcomesAndInputFatal();migratedLifecycle();cancellationLedger();successfulDispositionAfterFailure();unreportedCompletion();exhaustionAndThreads();if(args.length>1)Files.writeString(Path.of(args[1]),String.join("\n",migrated)+"\n");System.out.println("PASS actual owner/core/coordinator/observer closure A cases="+cases+" assertions="+checks+"; renderer leaf only, native runtime pending");}
}
