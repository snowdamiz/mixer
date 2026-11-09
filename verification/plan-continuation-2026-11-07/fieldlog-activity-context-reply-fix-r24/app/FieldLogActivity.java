package dev.mixer.android;
import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.nio.charset.StandardCharsets;
import java.util.Map;

public final class FieldLogActivity extends Activity {
 private final Handler handler=new Handler(Looper.getMainLooper());
 private FrameLayout root;private Button reopen;private TextView status,records;
 private FieldLogNativeSurface nativeSurface;
 private long context;
 private String requestID;private boolean pending,destroyed,refresh;private int polls;
 private Map<String,Object> last;
 private record CapturedEvent(FieldLogNativeSurface surface,String owner,byte[] envelope) {}
 private final java.util.ArrayDeque<CapturedEvent> events=new java.util.ArrayDeque<>();
 private boolean eventPosted;
 private void drainEvent(){
  eventPosted=false;if(destroyed||pending||events.isEmpty())return;
  CapturedEvent event=events.removeFirst();
  if(event.surface()!=nativeSurface||!event.owner().equals(nativeSurface.owner())){fail("captured event owner retired");return;}
  request(Json.map("command","event","owner",event.owner(),"event",Json.parse(event.envelope())));
 }
 private void queueEvent(){if(!eventPosted&&!destroyed&&!pending&&!events.isEmpty()){eventPosted=true;if(!handler.post(this::drainEvent))throw new IllegalStateException("app event queue rejected");}}

 @Override public void onCreate(Bundle state){
  super.onCreate(state);context=FieldLogBridge.createContext(this);if(context<=0)throw new IllegalStateException("JNI context creation failed");LinearLayout page=new LinearLayout(this);page.setOrientation(LinearLayout.VERTICAL);
  root=new FrameLayout(this);status=new TextView(this);records=new TextView(this);reopen=new Button(this);reopen.setText("Close and reopen workspace");
  page.addView(root,new LinearLayout.LayoutParams(-1,0,1));page.addView(status,new LinearLayout.LayoutParams(-1,96));page.addView(records,new LinearLayout.LayoutParams(-1,144));page.addView(reopen,new LinearLayout.LayoutParams(-1,64));setContentView(page);
  reopen.setOnClickListener(v->open());root.post(this::openWhenReady);
 }
 private void openWhenReady(){if(destroyed)return;if(root.getWidth()<=0||root.getHeight()<=0||root.getRootWindowInsets()==null||!root.hasWindowFocus()){handler.postDelayed(this::openWhenReady,16);return;}open();}
 private void open(){request(Json.map("command","open","filesDir",getFilesDir().getPath()));}
 private void nativeEvent(String capturedOwner,byte[] envelope){
  if(destroyed||pending||nativeSurface==null||events.size()>=32)throw new IllegalStateException("native event queue unavailable");
  events.addLast(new CapturedEvent(nativeSurface,capturedOwner,envelope.clone()));queueEvent();
 }
 private void refresh(){refresh=true;if(!pending&&!destroyed)request(Json.map("command","refresh"));}
 int surface(int operation,byte[] identity,byte[] packet,byte[] descriptor){
  NativeEnvironmentV2.requireMain();String owner=new String(identity,StandardCharsets.UTF_8);
  try{
   switch(operation){
    case 0:if(nativeSurface!=null)throw new IllegalStateException("native owner already active");nativeSurface=new FieldLogNativeSurface(this,root,owner,event->nativeEvent(owner,event),this::refresh,this::fail);break;
    case 1:if(nativeSurface==null)throw new IllegalStateException("no native owner");nativeSurface.install(owner,packet,descriptor);break;
    case 2:if(nativeSurface==null||!nativeSurface.owner().equals(owner))throw new IllegalStateException("foreign revocation");nativeSurface.close();nativeSurface=null;break;
    default:throw new IllegalArgumentException("unknown native operation");
   }
   return 0;
  }catch(RuntimeException error){android.util.Log.e("FieldLogHostR12","surface operation="+operation+" root="+root.getWidth()+"x"+root.getHeight()+" owner="+(nativeSurface==null?"none":nativeSurface.diagnostic()),error);fail(error.toString());return 1;}
 }
 private void request(Map<String,Object> command){
  if(pending||destroyed)return;requestID=java.util.UUID.randomUUID().toString();command.put("requestID",requestID);pending=true;polls=0;
  if(nativeSurface!=null)nativeSurface.gateInput();reopen.setEnabled(false);status.setText("Working…");
  if(FieldLogBridge.submit(context,Json.encode(command))!=0){fail("JNI rejected command");return;}handler.post(this::poll);
 }
 private void poll(){
  if(destroyed)return;byte[] bytes=FieldLogBridge.poll(context,requestID);if(bytes==null){fail("JNI reply unavailable");return;}
  if(bytes.length==0){if(++polls>625){fail("Swift MainActor timeout");return;}handler.postDelayed(this::poll,16);return;}
  try{
   Map<String,Object> reply=Json.object(Json.parse(bytes));if(!Long.toString(context).equals(Json.string(reply.get("contextID")))||!requestID.equals(Json.string(reply.get("requestID"))))throw new IllegalStateException("Foreign context/request reply");
   if(!Json.bool(reply.get("ok"))){fail(Json.string(reply.get("error")));return;}
   last=reply;StringBuilder saved=new StringBuilder();for(Object raw:Json.array(reply.get("tasks"))){Map<String,Object> task=Json.object(raw);saved.append(Json.string(task.get("title"))).append("\n").append(Json.string(task.get("responsible"))).append("\n");}
   records.setText(saved.toString());status.setText("FieldLog public host ready");pending=false;reopen.setEnabled(true);queueEvent();
   if(refresh){refresh=false;handler.post(()->request(Json.map("command","refresh")));}
  }catch(RuntimeException error){fail(error.toString());}
 }
 private void fail(String error){pending=false;if(!status.getText().toString().startsWith("FAILED:"))status.setText("FAILED: "+error+"; JNI boundary="+FieldLogBridge.surfaceDiagnostic());reopen.setEnabled(false);if(nativeSurface!=null)nativeSurface.gateInput();}
 @Override public void onResume(){super.onResume();if(nativeSurface!=null)nativeSurface.resume();}
 @Override public void onPause(){if(nativeSurface!=null)nativeSurface.pause();super.onPause();}
 @Override public void onStop(){if(nativeSurface!=null)nativeSurface.stop();super.onStop();}
 @Override public void onDestroy(){
  destroyed=true;events.clear();handler.removeCallbacksAndMessages(null);
  // Invalidate this lifetime immediately; JNI retains its receiver until the
  // serialized SDK revocation and repository close have actually returned.
  FieldLogBridge.closeContext(context);super.onDestroy();
 }
 boolean ready(){return !pending&&!eventPosted&&events.isEmpty()&&!destroyed&&nativeSurface!=null&&nativeSurface.installs()>0&&nativeSurface.current()&&!status.getText().toString().startsWith("FAILED:");}
 EditText titleField(){return (EditText)nativeSurface.view("task.title");}
 EditText responsibleField(){return (EditText)nativeSurface.view("task.responsible");}
 Button addButton(){return (Button)nativeSurface.view("task.save");}
 Button reopenButton(){return reopen;}
 String savedText(){return records.getText().toString();}
 String stateTitle(){return last==null?"":Json.string(last.get("title"));}
 String stateResponsible(){return last==null?"":Json.string(last.get("responsible"));}
 String diagnostic(){return status.getText().toString()+"; owner="+(nativeSurface==null?"none":nativeSurface.diagnostic());}
 void nativeInvalidationControl(){nativeSurface.invalidationControl();}
 void terminalMeasureControl(){
  for(int i=0;i<root.getChildCount();i++)root.getChildAt(i).forceLayout();
  root.forceLayout();
  root.measure(android.view.View.MeasureSpec.makeMeasureSpec(root.getWidth(),android.view.View.MeasureSpec.EXACTLY),android.view.View.MeasureSpec.makeMeasureSpec(root.getHeight(),android.view.View.MeasureSpec.EXACTLY));
 }
}
