package dev.mixer.android;

import android.app.Instrumentation;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.os.Bundle;
import android.os.SystemClock;
import android.text.Editable;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;
import java.io.File;
import java.io.FileOutputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

/** Native Views, real Activity/window/AssetManager, software and compositor captures. */
@SuppressWarnings("deprecation")
public final class NativeAppearanceV2Instrumentation extends Instrumentation {
    private NativeAppearanceV2Activity activity;
    private NativeRenderer renderer;
    private InstalledAppearanceV2 installed;
    private final List<byte[]> events=new ArrayList<>();
    private int checks;
    private Bundle arguments;
    private long revision=1;
    @Override public void onCreate(Bundle args){super.onCreate(args);arguments=args;start();}
    private void check(boolean value,String message){if(!value)throw new AssertionError(message);checks++;}
    private void reject(Runnable action,String message){try{action.run();throw new AssertionError("accepted "+message);}catch(IllegalArgumentException expected){checks++;}}
    private static Json.Num num(long value){return new Json.Num(Long.toString(value));}
    private static Map<String,Object> node(String id,String kind,Map<String,Object> props,List<Object> children){
        List<Object> actions=switch(kind){case "button"->List.of(Json.map("id",id+"-action","event","activate"));
            case "toggle"->List.of(Json.map("id",id+"-action","event","valueChange"));
            case "textField"->List.of(Json.map("id",id+"-change","event","textChange"),Json.map("id",id+"-submit","event","submit"));default->List.of();};
        return Json.map("id",id,"kind",kind,"properties",props,"children",children,"actions",actions);
    }
    private byte[] packet(Object root,long version){List<Object> identities=new ArrayList<>();identities(root,identities);
        return encode(Json.map("schemaVersion",num(1),"document",Json.map("schemaVersion",num(1),"revision",num(version),"root",root),"identities",identities));}
    private static byte[] encode(Object value){StringBuilder out=new StringBuilder();write(out,value);return out.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8);}
    private static void write(StringBuilder out,Object value){
        if(value instanceof List<?> list){out.append('[');for(int i=0;i<list.size();i++){if(i>0)out.append(',');write(out,list.get(i));}out.append(']');}
        else if(value instanceof Map<?,?> map){out.append('{');boolean comma=false;for(var entry:map.entrySet()){if(comma)out.append(',');comma=true;Json.write(out,entry.getKey());out.append(':');write(out,entry.getValue());}out.append('}');}
        else Json.write(out,value);
    }
    private void ui(Runnable work){Throwable[] failure=new Throwable[1];super.runOnMainSync(()->{try{work.run();}catch(Throwable e){failure[0]=e;}});if(failure[0]!=null)throw new AssertionError("UI assertion",failure[0]);}
    private void identities(Object raw,List<Object> result){Map<String,Object> n=Json.object(raw);result.add(Json.map("id",n.get("id"),"generation",num(result.size()+1)));
        for(Object child:Json.array(n.get("children")))identities(child,result);}
    private Object text(String id,String value,String style){return node(id,"text",Json.map("text",value,"style",style),List.of());}
    private byte[] scene(long version,String value,boolean off){
        Object stack=node("v","vStack",Json.map("alignment","leading"),List.of(text("body","Body combining e\u0301 العربية 漢字 👩🏽‍🚀","body"),text("caption","Caption","caption")));
        Object horizontal=node("h","hStack",Map.of(),List.of(text("short","Short","body"),text("long","A longer native shaped label","body")));
        Object overlay=node("z","zStack",Json.map("alignment","bottomTrailing"),List.of(text("back","Overlay background","headline"),text("front","front","caption")));
        Object button=node("button","button",Json.map("label","Activate"),List.of());
        Object field=node("field","textField",Json.map("label","Native field","value",value),List.of());
        Object toggle=node("toggle","toggle",Json.map("label","Native switch","value",!off),List.of());
        Object section=node("section","section",Json.map("title","A native group"),List.of(stack,horizontal,overlay,button,field,toggle));
        Object empty=node("empty","section",Map.of(),List.of());Object header=node("headerOnly","section",Json.map("title","Header only"),List.of());
        List<Object> children=new ArrayList<>(List.of(section,empty,header,text("direct","Direct row","body")));
        for(int i=0;i<15;i++)children.add(text("tail"+i,"Native scrolling row "+i,"body"));
        return packet(node("navigation","navigation",Json.map("title","Shared appearance V2"),List.of(node("list","list",Map.of(),children))),version);
    }
    private void publish(byte[] bytes){NativeEnvironmentV2 env=renderer.captureEnvironmentV2(activity,activity.root);
        NativeRenderer.Candidate c=renderer.prepareV2(bytes,installed,env);NativeRenderer.AttachmentJournal j=renderer.attachV2(c,activity.root);
        renderer.validateAttachedV2(c,j);renderer.finishV2(c,j);}
    private void save(String name,Bitmap bitmap){try(FileOutputStream out=new FileOutputStream(new File(activity.getFilesDir(),name))){
        if(!bitmap.compress(Bitmap.CompressFormat.PNG,100,out))throw new AssertionError("bitmap encode");}catch(java.io.IOException failure){throw new AssertionError(failure);}}
    private void software(String name){Bitmap bitmap=Bitmap.createBitmap(activity.root.getWidth(),activity.root.getHeight(),Bitmap.Config.ARGB_8888);
        activity.root.draw(new Canvas(bitmap));save(name,bitmap);bitmap.recycle();}
    private void basic(){
        renderer=new NativeRenderer(activity,events::add);installed=renderer.captureInstalledV2();byte[] owned=installed.descriptorCopy();owned[0]='!';
        check(installed.descriptorCopy()[0]=='{',"captured descriptor defensive copy");
        NativeEnvironmentV2 env=renderer.captureEnvironmentV2(activity,activity.root);
        check(env.value.profile()==AppearanceDescriptorV2.Profile.l,"actual SP17/DIP1 profile l");
        byte[] bytes=scene(revision++,"native",false);NativeRenderer.Candidate candidate=renderer.prepareV2(bytes,installed,env);Arrays.fill(bytes,(byte)'!');
        check(activity.root.getChildCount()==0,"prepare leaves live root untouched");
        reject(()->renderer.prepareV2(scene(99,"native",false),installed,env),"second pending candidate");
        NativeRenderer foreign=new NativeRenderer(activity,ignored->{});reject(()->foreign.attachV2(candidate,activity.root),"foreign candidate");
        NativeRenderer.AttachmentJournal journal=renderer.attachV2(candidate,activity.root);check(renderer.packet==null,"native attach does not commit packet");
        renderer.validateAttachedV2(candidate,journal);renderer.finishV2(candidate,journal);
        reject(()->renderer.finishV2(candidate,journal),"replayed candidate");
        check(renderer.view("button") instanceof Button&&renderer.view("field") instanceof EditText&&renderer.view("toggle") instanceof Switch&&renderer.view("list") instanceof ScrollView,"real native input/list objects");
        TextView body=(TextView)renderer.view("body");check(body.getLayout()!=null&&body.getLayout().getHeight()<=body.getHeight(),"actual native layout fits grown text");
        check(!body.getIncludeFontPadding(),"no native font padding");
        check(((Button)renderer.view("button")).getStateListAnimator()==null&&renderer.view("button").getElevation()==0,"no native elevation/state animation");
        check(renderer.view("button").getBackground().getClass().getName().contains("ControlDrawable"),"owned button background replaces ripple");
        check(events.isEmpty(),"prepare/attach/binding has zero events");software("all-ten-software.png");
        View stable=renderer.view("button");View scroll=renderer.view("list");View editor=renderer.view("field");
        publish(scene(revision++,"native",false));check(renderer.view("button")==stable&&renderer.view("list")==scroll&&renderer.view("field")==editor,"identity survives publication");
        check(events.isEmpty(),"repaint emits no guest event");
        ((Button)stable).performClick();check(events.size()==1,"one actual Button activation");events.clear();
        ((Switch)renderer.view("toggle")).performClick();check(events.size()==1,"one actual Switch value change");events.clear();
    }
    private void faults(){
        String base=renderer.packet.revision;View root=activity.root.getChildAt(0);View button=renderer.view("button");
        // Every concrete node-bind/parent step plus root and layout attachment is faulted.
        int nodes=renderer.packet.nodes.size();
        for(int step=0;step<2*nodes+2;step++){
            renderer.testFaultV2(step,false);NativeRenderer.Candidate c=renderer.prepareV2(scene(revision++,"changed",true),installed,renderer.captureEnvironmentV2(activity,activity.root));
            boolean failed=false;try{renderer.attachV2(c,activity.root);}catch(IllegalStateException expected){failed=true;}
            check(failed,"injected attachment step "+step);check(renderer.packet.revision.equals(base),"rollback retains exact packet revision");
            check(activity.root.getChildAt(0)==root&&renderer.view("button")==button,"rollback retains native hierarchy identity");
            check(((EditText)renderer.view("field")).getText().toString().equals("native"),"rollback restores inactive native editor value");
        }
        renderer.testFaultV2(-1,false);((Button)button).performClick();check(events.size()==1,"old tree callback after every rollback");events.clear();
        NativeEnvironmentV2 stale=renderer.captureEnvironmentV2(activity,activity.root);NativeRenderer.Candidate c=renderer.prepareV2(scene(revision++,"native",false),installed,stale);
        NativeRenderer.Candidate replaced=c;renderer.captureInstalledV2();reject(()->renderer.attachV2(replaced,activity.root),"replaced installed capture");renderer.discardV2(c);installed=renderer.captureInstalledV2();
        c=renderer.prepareV2(scene(revision++,"native",false),installed,renderer.captureEnvironmentV2(activity,activity.root));
        NativeRenderer.Candidate attached=c;NativeRenderer.AttachmentJournal j=renderer.attachV2(attached,activity.root);renderer.rollbackV2(attached,j);
        check(renderer.packet.revision.equals(base),"explicit post-attach rollback retains base");
        reject(()->renderer.attachV2(attached,activity.root),"aborted candidate reuse");
    }
    private void editing(){
        // Separate shallow scene makes native editor ancestry/frame unchanged across an accepted echo.
        renderer=new NativeRenderer(activity,events::add);activity.root.removeAllViews();installed=renderer.captureInstalledV2();revision=1000;
        Object field=node("editingField","textField",Json.map("label","Edit","value","hello"),List.of());
        publish(packet(node("editingRoot","vStack",Json.map("alignment","leading"),List.of(field)),revision++));
        EditText editor=(EditText)renderer.view("editingField");editor.requestFocus();editor.setSelection(1,4);Editable identity=editor.getText();
        InputConnection connection=editor.onCreateInputConnection(new EditorInfo());check(connection!=null,"native InputConnection");
        connection.setComposingRegion(1,4);int start=BaseInputConnection.getComposingSpanStart(identity),end=BaseInputConnection.getComposingSpanEnd(identity);
        check(start==1&&end==4,"actual native composing span");
        publish(packet(node("editingRoot","vStack",Json.map("alignment","leading"),List.of(field)),revision++));
        check(renderer.view("editingField")==editor&&editor.getText()==identity&&editor.hasFocus(),"editor/Editable/focus identity retained");
        check(editor.getSelectionStart()==1&&editor.getSelectionEnd()==4&&BaseInputConnection.getComposingSpanStart(identity)==start&&BaseInputConnection.getComposingSpanEnd(identity)==end,"native selection/composition retained without restore");
        Object conflict=node("editingField","textField",Json.map("label","Edit","value","conflict"),List.of());
        reject(()->renderer.prepareV2(packet(node("editingRoot","vStack",Json.map("alignment","leading"),List.of(conflict)),revision++),installed,
            renderer.captureEnvironmentV2(activity,activity.root)),"conflicting composition before attachment");
        check(editor.getText()==identity&&editor.getText().toString().equals("hello")&&BaseInputConnection.getComposingSpanStart(identity)==1,"rejection leaves actual composing editor untouched");
        events.clear();connection.setComposingText("abc",1);check(events.size()==1,"one native composing proposal event");
        String nativeValue=editor.getText().toString();Object echo=node("editingField","textField",Json.map("label","Edit","value",nativeValue),List.of());
        publish(packet(node("editingRoot","vStack",Json.map("alignment","leading"),List.of(echo)),revision++));
        check(editor.getText()==identity&&events.size()==1,"engine echo preserves native Editable and has no extra event");
        connection.finishComposingText();connection.performEditorAction(EditorInfo.IME_ACTION_DONE);check(events.size()==2,"native submit at most once");events.clear();
        software("editing-software.png");
        NativeRenderer.Candidate candidate=renderer.prepareV2(packet(node("editingRoot","vStack",Json.map("alignment","leading"),List.of(echo)),revision++),installed,renderer.captureEnvironmentV2(activity,activity.root));
        renderer.testFaultV2(0,true);try{renderer.attachV2(candidate,activity.root);throw new AssertionError("fault missing");}catch(IllegalStateException expected){checks++;}
        check(renderer.testRetiredV2(),"rollback failure retires gated presentation");reject(()->renderer.captureInstalledV2(),"retired owner");
    }
    private void touch(View view){int[] location=new int[2];view.getLocationOnScreen(location);float x=location[0]+view.getWidth()/2f,y=location[1]+view.getHeight()/2f;
        long now=SystemClock.uptimeMillis();MotionEvent down=MotionEvent.obtain(now,now,MotionEvent.ACTION_DOWN,x,y,0),up=MotionEvent.obtain(now,now+30,MotionEvent.ACTION_UP,x,y,0);
        check(getUiAutomation().injectInputEvent(down,true)&&getUiAutomation().injectInputEvent(up,true),"real native injected touch");down.recycle();up.recycle();}
    @Override public void onStart(){Bundle result=new Bundle();try{
        activity=(NativeAppearanceV2Activity)startActivitySync(new Intent(getTargetContext(),NativeAppearanceV2Activity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        waitForIdleSync();
        String expected=arguments==null?null:arguments.getString("captureRejection");
        if(expected!=null){ui(()->{NativeRenderer owner=new NativeRenderer(activity,ignored->{});
            try{owner.captureInstalledV2();throw new AssertionError("invalid installed capture accepted");}catch(AppearanceDescriptorV2.Failure failure){check(failure.code.name().equals(expected),"actual AssetManager complete-catalog rejection "+failure.code);}});
        }else{
            ui(this::basic);waitForIdleSync();
            Bitmap screenshot=getUiAutomation().takeScreenshot();check(screenshot!=null,"compositor screenshot");save("all-ten-compositor.png",screenshot);screenshot.recycle();
            // Touch actual visible Button after native ScrollView positions it.
            ui(()->((ScrollView)renderer.view("list")).smoothScrollTo(0,0));waitForIdleSync();
            ui(this::faults);ui(this::editing);
        }
        result.putString("status","passed");result.putInt("checks",checks);result.putString("scope","API37 emulator actual native renderer; ordinary engine/JNI join pending");finish(0,result);
    }catch(Throwable failure){result.putString("status","failed");result.putString("failure",android.util.Log.getStackTraceString(failure));finish(1,result);}}
}
