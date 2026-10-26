package dev.mixer.android;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.*;
import java.nio.charset.StandardCharsets;
/** Debug-only physical native-view integration tests; no production test backend. */
public final class AdapterInstrumentation extends Instrumentation {
    @Override public void onCreate(Bundle arguments){super.onCreate(arguments);start();}
    private static void check(boolean value,String message){if(!value)throw new AssertionError(message);}
    @Override public void onStart(){Bundle result=new Bundle();MixerActivity activity=null;try{
        Intent intent=new Intent(getTargetContext(),MixerActivity.class);intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);activity=(MixerActivity)startActivitySync(intent);final MixerActivity app=activity;
        runOnMainSync(()->{
            check(app.renderer.packet.nodes.size()==12,"initial node count");
            EditText title=(EditText)app.renderer.view("title");View first=app.renderer.view("task.1");String firstGeneration=app.renderer.packet.nodes.get("task.1").generation;
            check("mixer.title".equals(title.getTag()),"native accessibility identifier tag");UiPacket old=app.renderer.packet;
            title.setText("Device release");check(app.renderer.view("title")==title,"text field native identity");check(((TextView)app.renderer.view("heading")).getText().toString().equals("Device release"),"Swift title update");
            EditText draft=(EditText)app.renderer.view("draft");draft.setText("Ship physical build");check(((Button)app.renderer.view("add")).isEnabled(),"Swift add enable");((Button)app.renderer.view("add")).performClick();check(draft.getText().length()==0,"Swift clears draft");check(app.renderer.packet.nodes.containsKey("task.3"),"Swift inserted stable task");
            ((CompoundButton)app.renderer.view("task.1")).performClick();check(((TextView)app.renderer.view("summary")).getText().toString().equals("1 of 3 complete"),"Swift toggle model");
            ((Button)app.renderer.view("reverse")).performClick();check(app.renderer.view("task.1")==first,"native view survives list reorder");check(app.renderer.packet.nodes.get("task.1").generation.equals(firstGeneration),"logical identity survives reorder");check(app.renderer.packet.nodes.get("tasks").children.get(0).id.equals("task.3"),"Swift order reversed");
            draft.setText("Café 東京 🧪");((Button)app.renderer.view("add")).performClick();check(((CompoundButton)app.renderer.view("task.4")).getText().toString().equals("Café 東京 🧪"),"UTF8 JNI roundtrip");
            byte[] stale=old.event("title",old.nodes.get("title").generation,"textChange","stale title");boolean rejected=false;try{NativeBridge.exchange(app.session,1,stale);}catch(IllegalStateException expected){rejected=true;}check(rejected,"Swift rejects stale revision");
            rejected=false;try{app.renderer.packet.event("task.1",firstGeneration,"valueChange","wrong");}catch(IllegalArgumentException expected){rejected=true;}check(rejected,"Java rejects event type mismatch");
            byte[] unchanged=NativeBridge.exchange(app.session,0,null);check(UiPacket.decode(unchanged).nodes.get("title").text("value","").equals("Device release"),"rejected events preserve Swift state");
            long closed=NativeBridge.create();NativeBridge.destroy(closed);rejected=false;try{NativeBridge.exchange(closed,0,null);}catch(IllegalStateException expected){rejected=true;}check(rejected,"JNI closed handle rejected");
            rejected=false;try{NativeBridge.exchange(app.session,1,new byte[131073]);}catch(IllegalStateException expected){rejected=true;}check(rejected,"JNI input bound");
            result.putString("checks","native input, button, toggle, list insertion/reorder identity, UTF8, stale revision, event mismatch, closed handle, JNI bounds");result.putString("revision",app.renderer.packet.revision);result.putString("status","passed");
        });
        finish(0,result);
    }catch(Throwable error){result.putString("status","failed");result.putString("failure",android.util.Log.getStackTraceString(error));finish(1,result);}}
}
