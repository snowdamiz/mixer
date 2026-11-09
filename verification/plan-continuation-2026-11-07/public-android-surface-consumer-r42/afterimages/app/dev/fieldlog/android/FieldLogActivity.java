package dev.fieldlog.android;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Base64;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import dev.mixer.android.AndroidUINativeSurface;
import dev.mixer.android.AndroidUIProfile;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

public final class FieldLogActivity extends Activity {
 private final Handler handler=new Handler(Looper.getMainLooper());
 private FrameLayout root;private Button reopen;private TextView status,records;
 private AndroidUINativeSurface nativeSurface;
 private byte[] activeOwner;
 private int installs;
 private long context;
 private String requestID;private boolean pending,destroyed,refresh;private int polls;
 private JSONObject last;
 private record CapturedEvent(AndroidUINativeSurface surface,byte[] owner,byte[] envelope) {}
 private final java.util.ArrayDeque<CapturedEvent> events=new java.util.ArrayDeque<>();
 private boolean eventPosted;
 private void drainEvent(){
  eventPosted=false;if(destroyed||pending||events.isEmpty())return;
  CapturedEvent event=events.removeFirst();
  if(event.surface()!=nativeSurface||!Arrays.equals(event.owner(),activeOwner)){fail("captured event owner retired");return;}
  // The original envelope never passes through a JSON number implementation.
  request(command("event","owner",utf8(event.owner()),"eventPayload",Base64.encodeToString(event.envelope(),Base64.NO_WRAP)));
 }
 private void queueEvent(){if(!eventPosted&&!destroyed&&!pending&&!events.isEmpty()){eventPosted=true;if(!handler.post(this::drainEvent))throw new IllegalStateException("app event queue rejected");}}

 @Override public void onCreate(Bundle state){
  super.onCreate(state);context=FieldLogBridge.createContext(this);if(context<=0)throw new IllegalStateException("JNI context creation failed");LinearLayout page=new LinearLayout(this);page.setOrientation(LinearLayout.VERTICAL);
  root=new FrameLayout(this);status=new TextView(this);records=new TextView(this);reopen=new Button(this);reopen.setText("Close and reopen workspace");
  page.addView(root,new LinearLayout.LayoutParams(-1,0,1));page.addView(status,new LinearLayout.LayoutParams(-1,96));page.addView(records,new LinearLayout.LayoutParams(-1,144));page.addView(reopen,new LinearLayout.LayoutParams(-1,64));setContentView(page);
  reopen.setOnClickListener(v->open());root.post(this::openWhenReady);
 }
 private void openWhenReady(){if(destroyed)return;if(root.getWidth()<=0||root.getHeight()<=0||root.getRootWindowInsets()==null||!root.hasWindowFocus()){handler.postDelayed(this::openWhenReady,16);return;}open();}
 private void open(){request(command("open","filesDir",getFilesDir().getPath()));}
 private void nativeEvent(byte[] capturedOwner,byte[] envelope){
  if(destroyed||pending||nativeSurface==null||events.size()>=32)throw new IllegalStateException("native event queue unavailable");
  events.addLast(new CapturedEvent(nativeSurface,capturedOwner.clone(),envelope.clone()));queueEvent();
 }
 private void refresh(){refresh=true;if(!pending&&!destroyed)request(command("refresh"));}
 int surface(int operation,byte[] identity,byte[] packet,byte[] descriptor){
  requireMain();
  try{
   switch(operation){
    case 0:
     if(nativeSurface!=null)throw new IllegalStateException("native owner already active");
     AndroidUINativeSurface candidate=new AndroidUINativeSurface(this,root,AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,this::nativeEvent);
     candidate.activate(identity);nativeSurface=candidate;activeOwner=identity.clone();installs=0;break;
    case 1:
     if(nativeSurface==null)throw new IllegalStateException("no native owner");
     nativeSurface.install(new AndroidUINativeSurface.Frame(identity,packet,descriptor));installs++;break;
    case 2:
     if(nativeSurface==null)throw new IllegalStateException("no owner to revoke");
     nativeSurface.revoke(identity);nativeSurface=null;activeOwner=null;break;
    default:throw new IllegalArgumentException("unknown native operation");
   }
   return 0;
  }catch(RuntimeException error){android.util.Log.e("FieldLogPublicR42","surface operation="+operation+" root="+root.getWidth()+"x"+root.getHeight(),error);fail(error.toString());return 1;}
 }
 private void request(JSONObject command){
  if(pending||destroyed)return;requestID=java.util.UUID.randomUUID().toString();
  try{command.put("requestID",requestID);}catch(JSONException error){throw new IllegalArgumentException(error);}
  pending=true;polls=0;
  if(nativeSurface!=null)nativeSurface.gateInput();reopen.setEnabled(false);status.setText("Working…");
  if(FieldLogBridge.submit(context,command.toString().getBytes(StandardCharsets.UTF_8))!=0){fail("JNI rejected command");return;}handler.post(this::poll);
 }
 private void poll(){
  if(destroyed)return;byte[] bytes=FieldLogBridge.poll(context,requestID);if(bytes==null){fail("JNI reply unavailable");return;}
  if(bytes.length==0){if(++polls>625){fail("Swift MainActor timeout");return;}handler.postDelayed(this::poll,16);return;}
  try{
   JSONObject reply=new JSONObject(utf8(bytes));
   if(!Long.toString(context).equals(string(reply,"contextID"))||!requestID.equals(string(reply,"requestID")))throw new IllegalStateException("Foreign context/request reply");
   Object ok=reply.get("ok");if(!(ok instanceof Boolean))throw new IllegalArgumentException("ok must be boolean");
   if(!((Boolean)ok)){fail(string(reply,"error"));return;}
   Object rawTasks=reply.get("tasks");if(!(rawTasks instanceof JSONArray tasks))throw new IllegalArgumentException("tasks must be array");
   StringBuilder saved=new StringBuilder();for(int i=0;i<tasks.length();i++){Object raw=tasks.get(i);if(!(raw instanceof JSONObject task))throw new IllegalArgumentException("task must be object");saved.append(string(task,"title")).append("\n").append(string(task,"responsible")).append("\n");}
   last=reply;records.setText(saved.toString());status.setText("FieldLog public host ready");pending=false;reopen.setEnabled(true);queueEvent();
   if(refresh){refresh=false;handler.post(()->request(command("refresh")));}
  }catch(JSONException|RuntimeException error){fail(error.toString());}
 }
 private void fail(String error){pending=false;if(!status.getText().toString().startsWith("FAILED:"))status.setText("FAILED: "+error+"; JNI boundary="+FieldLogBridge.surfaceDiagnostic());reopen.setEnabled(false);if(nativeSurface!=null)nativeSurface.gateInput();}
 @Override public void onResume(){super.onResume();if(nativeSurface!=null)nativeSurface.onResume();}
 @Override public void onPause(){if(nativeSurface!=null)nativeSurface.onPause();super.onPause();}
 @Override public void onStop(){if(nativeSurface!=null)nativeSurface.onStop();super.onStop();}
 @Override public void onDestroy(){
  destroyed=true;events.clear();handler.removeCallbacksAndMessages(null);
  // JNI retains this receiver until serialized SDK revocation and repository close return.
  FieldLogBridge.closeContext(context);super.onDestroy();
 }
 public boolean ready(){return !pending&&!eventPosted&&events.isEmpty()&&!destroyed&&nativeSurface!=null&&installs>0&&nativeSurface.isCurrent()&&!status.getText().toString().startsWith("FAILED:");}
 public String savedText(){return records.getText().toString();}
 public String stateTitle(){return last==null?"":string(last,"title");}
 public String stateResponsible(){return last==null?"":string(last,"responsible");}
 public String diagnostic(){return status.getText().toString()+"; current="+(nativeSurface!=null&&nativeSurface.isCurrent());}
 private static JSONObject command(String name,String... fields){
  if((fields.length&1)!=0)throw new IllegalArgumentException("unpaired app command fields");
  JSONObject result=new JSONObject();try{result.put("command",name);for(int i=0;i<fields.length;i+=2)result.put(fields[i],fields[i+1]);}catch(JSONException error){throw new IllegalArgumentException(error);}return result;
 }
 private static String string(JSONObject object,String key){
  try{Object value=object.get(key);if(value instanceof String text)return text;throw new IllegalArgumentException(key+" must be string");}catch(JSONException error){throw new IllegalArgumentException(error);}
 }
 private static String utf8(byte[] bytes){
  try{return StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();}catch(CharacterCodingException error){throw new IllegalArgumentException("invalid UTF-8",error);}
 }
 private static void requireMain(){if(Looper.myLooper()!=Looper.getMainLooper())throw new IllegalStateException("Android main thread required");}
}
