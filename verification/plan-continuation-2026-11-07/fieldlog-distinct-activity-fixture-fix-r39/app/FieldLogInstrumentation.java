package dev.mixer.android;
import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.accessibility.AccessibilityNodeInfo;
import android.widget.EditText;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.BooleanSupplier;

public final class FieldLogInstrumentation extends Instrumentation {
 @Override public void onCreate(Bundle arguments) {super.onCreate(arguments);start();}
 private void main(Runnable task) {
  AtomicReference<Throwable> failure=new AtomicReference<>();
  runOnMainSync(()->{try {task.run();}catch(Throwable error){failure.set(error);}});
  if(failure.get()!=null) throw new AssertionError(failure.get());
 }
 private void await(BooleanSupplier condition,FieldLogActivity activity) throws InterruptedException {
  for(int i=0;i<300;i++) {
   boolean[] result={false};main(()->result[0]=condition.getAsBoolean());
   if(result[0])return;Thread.sleep(50);
  }
  String[] diagnostic={""};main(()->diagnostic[0]=activity.diagnostic());
  throw new AssertionError("Timed out: "+diagnostic[0]);
 }
 private void input(EditText field,String value) {
  Bundle arguments=new Bundle();arguments.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,value);
  if(!field.performAccessibilityAction(AccessibilityNodeInfo.ACTION_SET_TEXT,arguments))throw new AssertionError("Native accessibility input rejected");
 }
 private static Object field(Object object,String name) throws ReflectiveOperationException {
  java.lang.reflect.Field member=object.getClass().getDeclaredField(name);member.setAccessible(true);return member.get(object);
 }
 private static void cleanupEqual(String slot,Object actual,Object expected) {
  if(!java.util.Objects.equals(actual,expected))throw new AssertionError("final cleanup "+slot+": expected "+expected+", actual "+actual);
 }
 private void finalCleanup(NativeOwnerV2 owner,OwnerLifecycleV2 core,NativeOwnerV2.Fence fence,
                           NativeCoordinatorV2 coordinator,NativeRenderer renderer,NativeEnvironmentV2.Observer observer) throws ReflectiveOperationException {
  OwnerLifecycleV2.Snapshot state=core.snapshot();
  cleanupEqual("core.phase",state.phase(),OwnerLifecycleV2.Phase.RETIRED);
  cleanupEqual("core.reason",state.terminalReason(),OwnerLifecycleV2.Reason.CLOSED);
  cleanupEqual("core.drain",state.pendingDrain(),null);cleanupEqual("core.operation",state.operation(),null);
  cleanupEqual("core.presentation",state.presentation(),null);cleanupEqual("core.resource",state.resource(),null);
  cleanupEqual("core.cancelPending",state.cancelPending(),false);cleanupEqual("core.unregisterPending",state.unregisterPending(),false);
  cleanupEqual("core.closePending",state.closePending(),false);cleanupEqual("core.primary",state.primaryFailure(),null);
  cleanupEqual("core.cancelFailure",state.cancelFailure(),null);cleanupEqual("core.unregisterFailure",state.unregisterFailure(),null);
  cleanupEqual("core.closeFailure",state.closeFailure(),null);
  cleanupEqual("fence.terminal",fence.terminal,true);cleanupEqual("fence.drawAllowed",fence.drawAllowed,false);
  cleanupEqual("fence.inputAllowed",fence.inputAllowed,false);cleanupEqual("fence.operation",fence.operation,null);
  cleanupEqual("fence.commitFinish",fence.commitFinish,false);cleanupEqual("fence.rendererReportActive",fence.rendererReportActive,false);
  for(String slot:new String[]{"queued","opening","activeOperation","pendingUnregister","pendingCloseToken","pendingCloseResource"})cleanupEqual("owner."+slot,field(owner,slot),null);
  cleanupEqual("owner.effectDepth",field(owner,"effectDepth"),0);cleanupEqual("owner.registering",field(owner,"registering"),false);
  cleanupEqual("owner.terminalProcessed",field(owner,"terminalProcessed"),true);cleanupEqual("owner.emergency",field(owner,"emergency"),false);
  NativeOwnerV2.CleanupLedger owned=owner.cleanupLedger();
  cleanupEqual("owner.cause",owned.cause(),NativeOwnerV2.Cause.OBSERVER_EXHAUSTED);
  // A live coordinator, observer and cancellation path were acquired before retirement.
  cleanupEqual("owner.handler",owned.handler(),NativeOwnerV2.Outcome.RETURNED);
  cleanupEqual("owner.input",owned.input(),NativeOwnerV2.Outcome.RETURNED);
  cleanupEqual("owner.unregister",owned.unregister(),NativeOwnerV2.Outcome.RETURNED);
  cleanupEqual("owner.coordinator",owned.coordinator(),NativeOwnerV2.Outcome.RETURNED);
  cleanupEqual("owner.unreportedCompletion",owned.coreCompletionUnreported(),false);
  cleanupEqual("owner.primary",owned.primary(),null);cleanupEqual("owner.fatal",owned.firstFatal(),null);
  cleanupEqual("owner.rendererCause",owned.rendererCause(),null);
  cleanupEqual("owner.handlerFailure",owned.handlerFailure(),null);cleanupEqual("owner.inputFailure",owned.inputFailure(),null);
  cleanupEqual("owner.unregisterFailure",owned.unregisterFailure(),null);cleanupEqual("owner.coordinatorFailure",owned.coordinatorFailure(),null);
  NativeCoordinatorV2.CleanupLedger coordinated=coordinator.cleanupLedger();
  cleanupEqual("coordinator.renderer",coordinated.renderer(),NativeCoordinatorV2.Outcome.RETURNED);
  // External frames never create an engine session or request successful-path recovery.
  cleanupEqual("coordinator.engine",coordinated.engine(),NativeCoordinatorV2.Outcome.NOT_REQUESTED);
  cleanupEqual("coordinator.abort",coordinated.abort(),NativeCoordinatorV2.Outcome.NOT_REQUESTED);
  cleanupEqual("coordinator.rollback",coordinated.rollback(),NativeCoordinatorV2.Outcome.NOT_REQUESTED);
  cleanupEqual("coordinator.discard",coordinated.discard(),NativeCoordinatorV2.Outcome.NOT_REQUESTED);
  cleanupEqual("coordinator.primary",coordinated.primary(),null);cleanupEqual("coordinator.fatal",coordinated.firstFatal(),null);
  cleanupEqual("coordinator.rendererFailure",coordinated.rendererFailure(),null);cleanupEqual("coordinator.engineFailure",coordinated.engineFailure(),null);
  cleanupEqual("coordinator.abortFailure",coordinated.abortFailure(),null);cleanupEqual("coordinator.rollbackFailure",coordinated.rollbackFailure(),null);
  cleanupEqual("coordinator.discardFailure",coordinated.discardFailure(),null);
  cleanupEqual("coordinator.retired",coordinator.isRetired(),true);cleanupEqual("coordinator.disposed",field(coordinator,"disposed"),true);
  cleanupEqual("coordinator.busy",coordinator.busyForOwnerDisposal(),false);cleanupEqual("coordinator.inputBusy",coordinator.inputCancellationInProgress(),false);
  cleanupEqual("coordinator.operation",field(coordinator,"operation"),null);cleanupEqual("coordinator.packet",field(coordinator,"committedPacket"),null);
  cleanupEqual("coordinator.session",field(coordinator,"session"),0L);
  NativeRenderer.CleanupLedger rendered=renderer.cleanupLedger();
  cleanupEqual("renderer.disposed",field(renderer,"v2Disposed"),true);cleanupEqual("renderer.retired",field(renderer,"v2Retired"),true);
  cleanupEqual("renderer.pending",field(renderer,"v2Pending"),null);cleanupEqual("renderer.inProgress",rendered.inProgress(),false);
  cleanupEqual("renderer.primary",rendered.primary(),null);cleanupEqual("renderer.fatal",rendered.firstFatal(),null);
  cleanupEqual("renderer.deferredCause",field(rendered,"deferredCause"),null);
  cleanupEqual("renderer.cancellationSerial",rendered.consumedSerial(),field(rendered,"requestedSerial"));
  NativeEnvironmentV2.Observer.CleanupLedger observed=observer.cleanupLedger();
  cleanupEqual("observer.primary",observed.primary(),null);cleanupEqual("observer.fatal",observed.firstFatal(),null);
  for(int i=0;i<8;i++)cleanupEqual("observer.failure["+i+"]",observed.failure(i),null);
 }
 private void terminalCleanup(FieldLogActivity app) {
  main(()->{
   try {
    java.lang.reflect.Field surfaceField=FieldLogActivity.class.getDeclaredField("nativeSurface");surfaceField.setAccessible(true);
    FieldLogNativeSurface surface=(FieldLogNativeSurface)surfaceField.get(app);
    NativeEnvironmentV2.Observer observer=surface.observer();
    NativeOwnerV2 owner=(NativeOwnerV2)field(surface,"nativeOwner");
    OwnerLifecycleV2 core=(OwnerLifecycleV2)field(owner,"core");NativeOwnerV2.Fence fence=(NativeOwnerV2.Fence)field(owner,"fence");
    NativeCoordinatorV2 coordinator=(NativeCoordinatorV2)field(owner,"coordinator");
    if(coordinator==null||core.snapshot().resource()!=coordinator||!coordinator.hasCommittedPresentation())throw new AssertionError("real committed coordinator not acquired");
    NativeRenderer renderer=(NativeRenderer)field(coordinator,"renderer");
    if(renderer==null||field(coordinator,"external")==null)throw new AssertionError("real external renderer not acquired");
    cleanupEqual("external engine never acquired",field(coordinator,"session"),0L);
    surface.terminalControl();
    for(int i=0;i<8;i++)if(observer.cleanupLedger().state(i)!=NativeEnvironmentV2.Observer.RETURNED)throw new AssertionError("terminal observer cleanup slot "+i+" state "+observer.cleanupLedger().state(i));
    app.terminalMeasureControl();
    surface.close();
    surface.close();
    for(int i=0;i<8;i++)if(observer.cleanupLedger().state(i)!=NativeEnvironmentV2.Observer.RETURNED)throw new AssertionError("repeat close changed cleanup slot "+i);
    finalCleanup(owner,core,fence,coordinator,renderer,observer);
   }catch(ReflectiveOperationException error){throw new AssertionError(error);}
  });
 }
 private long context(FieldLogActivity activity) {
  try {return (Long)field(activity,"context");}catch(ReflectiveOperationException error){throw new AssertionError(error);}
 }
 private boolean destroyed(FieldLogActivity activity) {
  try {return (Boolean)field(activity,"destroyed");}catch(ReflectiveOperationException error){throw new AssertionError(error);}
 }
 private String owner(FieldLogActivity activity) {
  try {FieldLogNativeSurface surface=(FieldLogNativeSurface)field(activity,"nativeSurface");return surface==null?"":surface.owner();}
  catch(ReflectiveOperationException error){throw new AssertionError(error);}
 }
 private void handoffRegression(Intent intent) throws InterruptedException {
  FieldLogActivity old=null,newer=null;
  try {
   Handler mainHandler=new Handler(Looper.getMainLooper());
   mainHandler.postDelayed(()->Log.i("FieldLogPremiseR36","MAIN_LOOP_RESPONSIVE"),5000);
   Log.i("FieldLogPremiseR36","BEFORE_FIRST_START_ACTIVITY_SYNC");
   old=(FieldLogActivity)startActivitySync(intent);
   Log.i("FieldLogPremiseR36","AFTER_FIRST_START_ACTIVITY_SYNC");
   FieldLogActivity previous=old;await(previous::ready,previous);
   Log.i("FieldLogPremiseR36","AFTER_FIRST_AWAIT_READY");
   Log.i("FieldLogPremiseR36","BEFORE_SECOND_START_ACTIVITY_SYNC");
   newer=(FieldLogActivity)startActivitySync(intent);
   Log.i("FieldLogPremiseR36","AFTER_SECOND_START_ACTIVITY_SYNC");
   FieldLogActivity next=newer;await(next::ready,next);
   long[] ids={0,0};String[] owners={"",""};String request=java.util.UUID.randomUUID().toString();
   main(()->{
    ids[0]=context(previous);ids[1]=context(next);owners[0]=owner(next);
    if(ids[0]==ids[1]||ids[0]<=0||ids[1]<=0)throw new AssertionError("Activity contexts alias");
    if(FieldLogBridge.submit(ids[1],Json.encode(Json.map("command","open","filesDir",next.getFilesDir().getPath(),"requestID",request)))!=0)throw new AssertionError("handoff open rejected");
   });
   // Only the old context pumps the new open; its poll must neither select the
   // activation receiver nor consume the new context's completed reply.
   await(()->{
    byte[] stolen=FieldLogBridge.poll(ids[0],request);
    if(stolen==null||stolen.length!=0)throw new AssertionError("old context stole new reply");
    return FieldLogBridge.hasReply(ids[1],request);
   },next);
   main(()->{
    owners[1]=owner(next);
    if(owners[1].isEmpty()||owners[1].equals(owners[0])||!owner(previous).isEmpty())throw new AssertionError("activation did not bind exact new Activity");
    android.util.Log.i("FieldLogContextR24","new-open reply-ready oldContext="+ids[0]+" newContext="+ids[1]+" request="+request+" oldOwner="+owners[0]+" newOwner="+owners[1]);
   });
   main(previous::finish);waitForIdleSync();await(()->destroyed(previous),previous);
   await(()->!FieldLogBridge.contextRetained(ids[0]),next);
   main(()->{
    byte[] oldPoll=FieldLogBridge.poll(ids[0],request);
    byte[] wrongRequest=FieldLogBridge.poll(ids[1],java.util.UUID.randomUUID().toString());
    if(oldPoll==null||oldPoll.length!=0||wrongRequest==null||wrongRequest.length!=0)throw new AssertionError("foreign poll consumed reply");
    if(!FieldLogBridge.hasReply(ids[1],request))throw new AssertionError("old destroy removed new reply");
    byte[] bytes=FieldLogBridge.poll(ids[1],request);if(bytes==null||bytes.length==0)throw new AssertionError("new reply missing");
    java.util.Map<String,Object> reply=Json.object(Json.parse(bytes));
    if(!Json.bool(reply.get("ok"))||!request.equals(Json.string(reply.get("requestID")))||!Long.toString(ids[1]).equals(Json.string(reply.get("contextID")))||!owners[1].equals(Json.string(reply.get("owner")))||!owners[1].equals(owner(next))||!next.ready())throw new AssertionError("old destroy revoked new owner/reply");
    if(FieldLogBridge.hasReply(ids[1],request))throw new AssertionError("reply delivered twice");
    if(FieldLogBridge.surfaceDiagnostic()!=0)throw new AssertionError("handoff JNI failure "+FieldLogBridge.surfaceDiagnostic());
    android.util.Log.i("FieldLogContextR24","old-destroy released="+!FieldLogBridge.contextRetained(ids[0])+" newContext="+ids[1]+" request="+request+" owner="+owner(next)+" reply=exact-once");
   });
   old=null;main(next::finish);waitForIdleSync();await(()->!FieldLogBridge.contextRetained(ids[1]),next);newer=null;
  } finally {
   if(old!=null){FieldLogActivity cleanup=old;main(cleanup::finish);}
   if(newer!=null){FieldLogActivity cleanup=newer;main(cleanup::finish);}
   waitForIdleSync();
  }
 }
 @Override public void onStart() {
  Bundle result=new Bundle();FieldLogActivity activity=null;
  try {
   Intent intent=new Intent(getTargetContext(),FieldLogActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_MULTIPLE_TASK);
   handoffRegression(intent);
   activity=(FieldLogActivity)startActivitySync(intent);FieldLogActivity app=activity;
   await(app::ready,app);
   String title="Inspect 雪 🌱\nEast stair — "+System.currentTimeMillis();String responsible="Zoë / evening crew";
   main(()->input(app.titleField(),title));await(()->app.ready()&&title.equals(app.stateTitle()),app);
   main(()->input(app.responsibleField(),responsible));await(()->app.ready()&&responsible.equals(app.stateResponsible()),app);
   main(()->{if(!app.addButton().performClick())throw new AssertionError("Add rejected");});
   await(()->app.ready()&&app.savedText().contains(title+"\n"+responsible+"\n"),app);
   String[] before={""};main(()->before[0]=app.savedText());
   main(()->app.reopenButton().performClick());
   await(()->app.ready()&&before[0].equals(app.savedText()),app);
   main(app::finish);waitForIdleSync();activity=null;
   // Fresh Activity requests a fresh repository, independent of retained Java UI.
   activity=(FieldLogActivity)startActivitySync(intent);FieldLogActivity fresh=activity;
   await(()->fresh.ready()&&before[0].equals(fresh.savedText()),fresh);
   main(fresh::nativeInvalidationControl);
   await(()->fresh.ready()&&before[0].equals(fresh.savedText()),fresh);
   terminalCleanup(fresh);
   result.putString("result","PASS: R24 context-scoped old-destroy-after-new-open + new-reply-not-stolen; R20 real NativeOwner/Coordinator external immutable packet synchronous JNI NativeRenderer -> exact Unicode save -> repository reopen -> freshActivity -> native-only refresh -> terminal cleanup 8 observers + retired remeasure + repeated close + full final owner/core/coordinator/renderer ledgers; owned releases RETURNED; engine/abort/rollback/discard NOT_REQUESTED; no pending/deferred/uncertain/unreported/failure");
   main(fresh::finish);waitForIdleSync();activity=null;finish(Activity.RESULT_OK,result);
  } catch(Throwable error) {
   result.putString("result","FAIL: "+error);
   if(activity!=null) {FieldLogActivity owned=activity;main(owned::finish);waitForIdleSync();}
   finish(Activity.RESULT_CANCELED,result);
  }
 }
}
