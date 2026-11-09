package dev.mixer.android;
import android.app.Activity;
import dev.fieldlog.android.FieldLogActivity;
import dev.fieldlog.android.FieldLogBridge;
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
 private static android.view.View view(FieldLogActivity app,String id) {
  try{return ((NativeOwnerV2)field(field(app,"nativeSurface"),"nativeOwner")).externalView(id);}
  catch(ReflectiveOperationException error){throw new AssertionError(error);}
 }
 private static android.widget.Button reopenButton(FieldLogActivity app) {
  try{return (android.widget.Button)field(app,"reopen");}catch(ReflectiveOperationException error){throw new AssertionError(error);}
 }
 private static void nativeInvalidationControl(FieldLogActivity app) {
  try{NativeOwnerV2 owner=(NativeOwnerV2)field(field(app,"nativeSurface"),"nativeOwner");owner.changed(owner.externalObserver(),NativeEnvironmentV2.Change.INVALIDATED,null,null,null);}
  catch(ReflectiveOperationException error){throw new AssertionError(error);}
 }
 private static void terminalMeasureControl(FieldLogActivity app) {
  try{android.widget.FrameLayout root=(android.widget.FrameLayout)field(app,"root");
   for(int i=0;i<root.getChildCount();i++)root.getChildAt(i).forceLayout();root.forceLayout();
   root.measure(android.view.View.MeasureSpec.makeMeasureSpec(root.getWidth(),android.view.View.MeasureSpec.EXACTLY),android.view.View.MeasureSpec.makeMeasureSpec(root.getHeight(),android.view.View.MeasureSpec.EXACTLY));
  }catch(ReflectiveOperationException error){throw new AssertionError(error);}
 }
 private void terminalCleanup(FieldLogActivity app) {
  main(()->{
   try {
    java.lang.reflect.Field surfaceField=FieldLogActivity.class.getDeclaredField("nativeSurface");surfaceField.setAccessible(true);
    AndroidUINativeSurface surface=(AndroidUINativeSurface)surfaceField.get(app);
    NativeEnvironmentV2.Observer observer=(NativeEnvironmentV2.Observer)field(field(surface,"nativeOwner"),"observer");
    NativeOwnerV2 owner=(NativeOwnerV2)field(surface,"nativeOwner");
    OwnerLifecycleV2 core=(OwnerLifecycleV2)field(owner,"core");NativeOwnerV2.Fence fence=(NativeOwnerV2.Fence)field(owner,"fence");
    NativeCoordinatorV2 coordinator=(NativeCoordinatorV2)field(owner,"coordinator");
    if(coordinator==null||core.snapshot().resource()!=coordinator||!coordinator.hasCommittedPresentation())throw new AssertionError("real committed coordinator not acquired");
    NativeRenderer renderer=(NativeRenderer)field(coordinator,"renderer");
    if(renderer==null||field(coordinator,"external")==null)throw new AssertionError("real external renderer not acquired");
    cleanupEqual("external engine never acquired",field(coordinator,"session"),0L);
    owner.changed(observer,NativeEnvironmentV2.Change.EPOCH_EXHAUSTED,null,null,null);
    for(int i=0;i<8;i++)if(observer.cleanupLedger().state(i)!=NativeEnvironmentV2.Observer.RETURNED)throw new AssertionError("terminal observer cleanup slot "+i+" state "+observer.cleanupLedger().state(i));
    terminalMeasureControl(app);
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
  try {AndroidUINativeSurface surface=(AndroidUINativeSurface)field(activity,"nativeSurface");return surface==null?"":new String((byte[])field(activity,"activeOwner"),java.nio.charset.StandardCharsets.UTF_8);}
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
 private String r53Stage="not-started";
 private static void compositionEqual(String stage,Object actual,Object expected) {
  if(!java.util.Objects.equals(actual,expected))throw new AssertionError("R53 InputConnection "+stage+": expected "+expected+", observed "+actual);
 }
 private static void compositionTrue(String stage,boolean actual) {compositionEqual(stage,actual,true);}
 private android.view.inputmethod.InputConnection currentConnection(FieldLogActivity app,EditText edit,String stage) {
  compositionEqual(stage+".thread",Looper.myLooper(),Looper.getMainLooper());
  compositionTrue(stage+".ready",app.ready());compositionTrue(stage+".owner-widget",view(app,"task.title")==edit);
  compositionTrue(stage+".attached",edit.isAttachedToWindow());compositionTrue(stage+".shown",edit.isShown());
  compositionTrue(stage+".window-focus",edit.hasWindowFocus());compositionTrue(stage+".focused",edit.hasFocus());
  compositionEqual(stage+".api",android.os.Build.VERSION.SDK_INT,37);
  android.view.inputmethod.EditorInfo info=new android.view.inputmethod.EditorInfo();
  android.view.inputmethod.InputConnection connection=edit.onCreateInputConnection(info);
  if(connection==null)throw new AssertionError("R53 InputConnection "+stage+".create: expected non-null current focused NativeField connection, observed null; inputType="+info.inputType+" imeOptions="+info.imeOptions+" initialSelection="+info.initialSelStart+","+info.initialSelEnd+"; "+app.diagnostic());
  int authored=android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES|android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE;
  compositionEqual(stage+".widget-input-type",edit.getInputType(),authored);
  compositionTrue(stage+".API37-negotiated-input-type",info.inputType==authored||info.inputType==(authored|0x00200000));
  compositionEqual(stage+".ime-action",info.imeOptions&(android.view.inputmethod.EditorInfo.IME_MASK_ACTION|android.view.inputmethod.EditorInfo.IME_FLAG_NO_ENTER_ACTION),android.view.inputmethod.EditorInfo.IME_ACTION_NONE|android.view.inputmethod.EditorInfo.IME_FLAG_NO_ENTER_ACTION);
  int restricted=android.view.inputmethod.EditorInfo.IME_FLAG_NO_EXTRACT_UI|android.view.inputmethod.EditorInfo.IME_FLAG_NO_FULLSCREEN;
  compositionEqual(stage+".ime-restrictions",info.imeOptions&restricted,restricted);
  compositionEqual(stage+".ime-navigation",info.imeOptions&(android.view.inputmethod.EditorInfo.IME_FLAG_NAVIGATE_NEXT|android.view.inputmethod.EditorInfo.IME_FLAG_NAVIGATE_PREVIOUS),0);
  compositionEqual(stage+".initial-start",info.initialSelStart,edit.getSelectionStart());
  compositionEqual(stage+".initial-end",info.initialSelEnd,edit.getSelectionEnd());
  compositionTrue(stage+".handwriting-gestures",info.getSupportedHandwritingGestures().isEmpty());
  compositionTrue(stage+".handwriting-previews",info.getSupportedHandwritingGesturePreviews().isEmpty());
  Log.i("FieldLogCompositionR53",stage+" EditorInfo api=37 widget="+edit.getInputType()+" output="+info.inputType+" imeOptions="+info.imeOptions+" owner="+owner(app));
  return connection;
 }
 private void capturedCompositionEvent(FieldLogActivity app,String expected,String stage) {
  try {
   Object surface=field(app,"nativeSurface");
   java.util.ArrayDeque<?> events=(java.util.ArrayDeque<?>)field(app,"events");
   compositionEqual(stage+".event-count",events.size(),1);Object captured=events.peekFirst();
   compositionTrue(stage+".event-surface",field(captured,"surface")==surface);
   compositionTrue(stage+".event-owner",java.util.Arrays.equals((byte[])field(captured,"owner"),(byte[])field(app,"activeOwner")));
   byte[] bytes=(byte[])field(captured,"envelope");java.util.Map<String,Object> envelope=Json.object(Json.parse(bytes));
   Json.keys(envelope,"revision","identity","event","value");
   compositionEqual(stage+".event-name",Json.string(envelope.get("event")),"textChange");
   compositionEqual(stage+".event-value",Json.string(envelope.get("value")),expected);
   java.util.Map<String,Object> identity=Json.object(envelope.get("identity"));
   compositionEqual(stage+".event-id",Json.string(identity.get("id")),"task.title");
   Object coordinator=field(field(surface,"nativeOwner"),"coordinator");
   java.util.Map<String,Object> packet=Json.object(Json.parse((byte[])field(coordinator,"committedPacket")));
   compositionEqual(stage+".event-revision",Json.uint(envelope.get("revision")),Json.uint(Json.object(packet.get("document")).get("revision")));
   String generation=null;
   for(Object raw:Json.array(packet.get("identities"))) {
    java.util.Map<String,Object> node=Json.object(raw);
    if("task.title".equals(Json.string(node.get("id"))))generation=Json.uint(node.get("generation"));
   }
   if(generation==null)throw new AssertionError("R53 InputConnection "+stage+": title identity absent from current owner packet");
   compositionEqual(stage+".event-generation",Json.uint(identity.get("generation")),generation);
   Log.i("FieldLogCompositionR53",stage+" current-owner exact event="+new String(bytes,java.nio.charset.StandardCharsets.UTF_8));
  }catch(ReflectiveOperationException error){throw new AssertionError("R53 InputConnection "+stage+" read-only event observation",error);}
 }
 private void compositionRegression(Intent intent) throws InterruptedException {
  FieldLogActivity activity=null;
  try {
   r53Stage="open";activity=(FieldLogActivity)startActivitySync(intent);FieldLogActivity app=activity;await(app::ready,app);
   String nonce=Long.toString(System.currentTimeMillis());String composing="Inspect 雪 🌱\nEast stair — R53 "+nonce;
   String committed="Inspect 雪 🌱\nWest 🌿 stair — R53 "+nonce;String responsible="R53 Zoë / evening crew";
   String[] priorSaved={""};main(()->priorSaved[0]=app.savedText());
   main(()->input((EditText)view(app,"task.responsible"),responsible));
   await(()->app.ready()&&responsible.equals(app.stateResponsible()),app);
   r53Stage="compose-focus";main(()->compositionTrue(r53Stage+".request",view(app,"task.title").requestFocus()));
   await(()->app.ready()&&view(app,"task.title").hasFocus()&&view(app,"task.title").hasWindowFocus(),app);
   r53Stage="compose-and-finish";
   main(()->{
    EditText edit=(EditText)view(app,"task.title");String currentOwner=owner(app);
    android.view.inputmethod.InputConnection connection=currentConnection(app,edit,"compose");
    compositionTrue("compose.select-all",connection.setSelection(0,edit.getText().length()));
    compositionTrue("compose.setComposingText",connection.setComposingText(composing,1));
    compositionEqual("compose.widget-value",edit.getText().toString(),composing);
    compositionEqual("compose.span-start",android.view.inputmethod.BaseInputConnection.getComposingSpanStart(edit.getText()),0);
    compositionEqual("compose.span-end",android.view.inputmethod.BaseInputConnection.getComposingSpanEnd(edit.getText()),composing.length());
    compositionEqual("compose.cursor-start",edit.getSelectionStart(),composing.length());
    compositionEqual("compose.cursor-end",edit.getSelectionEnd(),composing.length());
    capturedCompositionEvent(app,composing,"compose");
    compositionTrue("compose.finishComposingText",connection.finishComposingText());
    compositionEqual("finish.widget-value",edit.getText().toString(),composing);
    compositionEqual("finish.span-start",android.view.inputmethod.BaseInputConnection.getComposingSpanStart(edit.getText()),-1);
    compositionEqual("finish.span-end",android.view.inputmethod.BaseInputConnection.getComposingSpanEnd(edit.getText()),-1);
    capturedCompositionEvent(app,composing,"finish-no-extra-event");compositionEqual("finish.owner",owner(app),currentOwner);
   });
   r53Stage="compose-model";await(()->app.ready()&&composing.equals(app.stateTitle())&&responsible.equals(app.stateResponsible()),app);
   main(()->compositionEqual("compose.model-widget",((EditText)view(app,"task.title")).getText().toString(),composing));
   r53Stage="commit-focus";main(()->compositionTrue(r53Stage+".request",view(app,"task.title").requestFocus()));
   await(()->app.ready()&&view(app,"task.title").hasFocus()&&view(app,"task.title").hasWindowFocus(),app);
   r53Stage="selection-replacement-commit";
   main(()->{
    EditText edit=(EditText)view(app,"task.title");String currentOwner=owner(app);
    android.view.inputmethod.InputConnection connection=currentConnection(app,edit,"commit");int start=composing.indexOf("East");
    compositionTrue("commit.setSelection",connection.setSelection(start,start+4));
    compositionEqual("commit.selection-start",edit.getSelectionStart(),start);compositionEqual("commit.selection-end",edit.getSelectionEnd(),start+4);
    CharSequence selected=connection.getSelectedText(0);compositionEqual("commit.selected-text",selected==null?null:selected.toString(),"East");
    compositionTrue("commit.commitText",connection.commitText("West 🌿",1));
    compositionEqual("commit.widget-value",edit.getText().toString(),committed);
    compositionEqual("commit.cursor-start",edit.getSelectionStart(),start+"West 🌿".length());
    compositionEqual("commit.cursor-end",edit.getSelectionEnd(),start+"West 🌿".length());
    compositionEqual("commit.span-start",android.view.inputmethod.BaseInputConnection.getComposingSpanStart(edit.getText()),-1);
    compositionEqual("commit.span-end",android.view.inputmethod.BaseInputConnection.getComposingSpanEnd(edit.getText()),-1);
    capturedCompositionEvent(app,committed,"commit");compositionEqual("commit.owner",owner(app),currentOwner);
   });
   r53Stage="commit-model";await(()->app.ready()&&committed.equals(app.stateTitle())&&responsible.equals(app.stateResponsible()),app);
   main(()->compositionEqual("commit.model-widget",((EditText)view(app,"task.title")).getText().toString(),committed));
   r53Stage="save";main(()->compositionTrue("save.click",view(app,"task.save").performClick()));
   String exactSaved=priorSaved[0]+committed+"\n"+responsible+"\n";
   await(()->app.ready()&&exactSaved.equals(app.savedText()),app);
   r53Stage="repository-reopen";main(()->compositionTrue("reopen.click",reopenButton(app).performClick()));
   await(()->app.ready()&&exactSaved.equals(app.savedText()),app);
   long[] oldContext={0};main(()->{oldContext[0]=context(app);app.finish();});waitForIdleSync();
   await(()->!FieldLogBridge.contextRetained(oldContext[0]),app);activity=null;
   r53Stage="fresh-activity";activity=(FieldLogActivity)startActivitySync(intent);FieldLogActivity fresh=activity;
   await(()->fresh.ready()&&exactSaved.equals(fresh.savedText()),fresh);
   r53Stage="native-refresh";main(()->nativeInvalidationControl(fresh));await(()->fresh.ready()&&exactSaved.equals(fresh.savedText()),fresh);
   r53Stage="final-ledgers";terminalCleanup(fresh);
   main(()->{oldContext[0]=context(fresh);fresh.finish();});waitForIdleSync();
   await(()->!FieldLogBridge.contextRetained(oldContext[0]),fresh);activity=null;
   r53Stage="complete";Log.i("FieldLogCompositionR53","PASS exact composition/commit/model/save/reopen/freshActivity/native-refresh/final-ledgers");
  }catch(RuntimeException|java.lang.Error error){throw new AssertionError("R53 InputConnection stage="+r53Stage+" expected public native composition/commit accepted with exact state; observed "+error,error);}
  finally {if(activity!=null){FieldLogActivity owned=activity;main(owned::finish);waitForIdleSync();}}
 }
 @Override public void onStart() {
  Bundle result=new Bundle();FieldLogActivity activity=null;
  try {
   Intent intent=new Intent(getTargetContext(),FieldLogActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_MULTIPLE_TASK);
   handoffRegression(intent);
   compositionRegression(intent);
   activity=(FieldLogActivity)startActivitySync(intent);FieldLogActivity app=activity;
   await(app::ready,app);
   String title="Inspect 雪 🌱\nEast stair — "+System.currentTimeMillis();String responsible="Zoë / evening crew";
   main(()->input((EditText)view(app,"task.title"),title));await(()->app.ready()&&title.equals(app.stateTitle()),app);
   main(()->input((EditText)view(app,"task.responsible"),responsible));await(()->app.ready()&&responsible.equals(app.stateResponsible()),app);
   main(()->{if(!((android.widget.Button)view(app,"task.save")).performClick())throw new AssertionError("Add rejected");});
   await(()->app.ready()&&app.savedText().contains(title+"\n"+responsible+"\n"),app);
   String[] before={""};main(()->before[0]=app.savedText());
   main(()->reopenButton(app).performClick());
   await(()->app.ready()&&before[0].equals(app.savedText()),app);
   main(app::finish);waitForIdleSync();activity=null;
   // Fresh Activity requests a fresh repository, independent of retained Java UI.
   activity=(FieldLogActivity)startActivitySync(intent);FieldLogActivity fresh=activity;
   await(()->fresh.ready()&&before[0].equals(fresh.savedText()),fresh);
   main(()->nativeInvalidationControl(fresh));
   await(()->fresh.ready()&&before[0].equals(fresh.savedText()),fresh);
   terminalCleanup(fresh);
   result.putString("result","PASS: R24 context-scoped old-destroy-after-new-open + new-reply-not-stolen; R20 real NativeOwner/Coordinator external immutable packet synchronous JNI NativeRenderer -> exact Unicode save -> repository reopen -> freshActivity -> native-only refresh -> terminal cleanup 8 observers + retired remeasure + repeated close + full final owner/core/coordinator/renderer ledgers; owned releases RETURNED; engine/abort/rollback/discard NOT_REQUESTED; no pending/deferred/uncertain/unreported/failure");
   result.putString("result",result.getString("result")+"; R53 API37 real focused NativeField public InputConnection: negotiated EditorInfo + Unicode/newline composing spans + finishComposingText + current-owner exact textChange/model + selection replacement commitText + exact save/reopen/freshActivity/native-refresh/full final ledgers");
   main(fresh::finish);waitForIdleSync();activity=null;finish(Activity.RESULT_OK,result);
  } catch(Throwable error) {
   result.putString("result","FAIL: "+error);
   if(activity!=null) {FieldLogActivity owned=activity;main(owned::finish);waitForIdleSync();}
   finish(Activity.RESULT_CANCELED,result);
  }
 }
}
