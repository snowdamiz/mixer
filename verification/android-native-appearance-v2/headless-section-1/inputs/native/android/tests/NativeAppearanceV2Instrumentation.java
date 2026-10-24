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
    private long revision=1;private byte[] lastPublishedBytes;private final Map<String,Long> generations=new java.util.LinkedHashMap<>();
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
    private void identities(Object raw,List<Object> result){Map<String,Object> n=Json.object(raw);result.add(Json.map("id",n.get("id"),"generation",num(generations.computeIfAbsent((String)n.get("id"),ignored->(long)generations.size()+1))));
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
        renderer.validateAttachedV2(c,j);renderer.finishV2(c,j);lastPublishedBytes=bytes.clone();}
    private void save(String name,Bitmap bitmap){try(FileOutputStream out=new FileOutputStream(new File(activity.getFilesDir(),name))){
        if(!bitmap.compress(Bitmap.CompressFormat.PNG,100,out))throw new AssertionError("bitmap encode");}catch(java.io.IOException failure){throw new AssertionError(failure);}}
    private void software(String name){Bitmap bitmap=Bitmap.createBitmap(activity.root.getWidth(),activity.root.getHeight(),Bitmap.Config.ARGB_8888);
        activity.root.draw(new Canvas(bitmap));save(name,bitmap);bitmap.recycle();}
    private static boolean ink(int pixel){int r=android.graphics.Color.red(pixel),g=android.graphics.Color.green(pixel),b=android.graphics.Color.blue(pixel);
        int high=Math.max(r,Math.max(g,b)),low=Math.min(r,Math.min(g,b));return high<128||high-low>64;}
    private static double inkAgreement(Bitmap software,Bitmap nativeImage,int x,int y,int safeTop,int safeBottom){long union=0,common=0;
        for(int row=safeTop;row<software.getHeight()-safeBottom;row+=2)for(int col=0;col<software.getWidth();col+=2){
            boolean a=ink(software.getPixel(col,row)),b=ink(nativeImage.getPixel(col+x,row+y));if(a||b)union++;if(a&&b)common++;}
        return union==0?0:common/(double)union;
    }
    private void await(java.util.concurrent.CountDownLatch latch,String message){try{check(latch.await(5,java.util.concurrent.TimeUnit.SECONDS),message);}catch(InterruptedException failure){throw new AssertionError(failure);}}
    private void hardware(String name){
        List<Object> attempts=new ArrayList<>();
        for(int attempt=0;attempt<3;attempt++){
            java.util.concurrent.CountDownLatch committed=new java.util.concurrent.CountDownLatch(1);
            ui(()->{publish(lastPublishedBytes.clone());check(activity.root.isHardwareAccelerated(),"actual native hardware accelerated window");
                activity.root.getViewTreeObserver().registerFrameCommitCallback(committed::countDown);activity.root.invalidate();});
            await(committed,"actual native frame submitted before capture");waitForIdleSync();
            boolean[] current={false};ui(()->current[0]=renderer.presentationCurrentV2());if(!current[0]){attempts.add(Json.map("attempt",n(attempt),"current",false));continue;}
            int[] windowOrigin=new int[2],screenOrigin=new int[2],safe=new int[2],size=new int[4];
            ui(()->{activity.root.getLocationInWindow(windowOrigin);activity.root.getLocationOnScreen(screenOrigin);
                var record=renderer.inspectV2().get(renderer.packet.root.id);var in=record.binding.plan().environment.safeArea64();
                safe[0]=NativeAppearanceViewsV2.px(in.top(),record.binding);safe[1]=NativeAppearanceViewsV2.px(in.bottom(),record.binding);
                size[0]=activity.root.getWidth();size[1]=activity.root.getHeight();size[2]=activity.getWindow().getDecorView().getWidth();size[3]=activity.getWindow().getDecorView().getHeight();});
            Bitmap nativeWindow=Bitmap.createBitmap(size[2],size[3],Bitmap.Config.ARGB_8888);int[] copyResult={-1};
            java.util.concurrent.CountDownLatch copied=new java.util.concurrent.CountDownLatch(1);
            ui(()->android.view.PixelCopy.request(activity.getWindow(),nativeWindow,code->{copyResult[0]=code;copied.countDown();},new android.os.Handler(android.os.Looper.getMainLooper())));
            await(copied,"actual native window PixelCopy completion");check(copyResult[0]==android.view.PixelCopy.SUCCESS,"actual native hardware window copy succeeded");
            Bitmap compositor=getUiAutomation().takeScreenshot();check(compositor!=null,"actual compositor screenshot");
            Bitmap software=Bitmap.createBitmap(size[0],size[1],Bitmap.Config.ARGB_8888);ui(()->activity.root.draw(new Canvas(software)));
            double windowMatch=inkAgreement(software,nativeWindow,windowOrigin[0],windowOrigin[1],safe[0],safe[1]);
            double screenMatch=inkAgreement(software,compositor,screenOrigin[0],screenOrigin[1],safe[0],safe[1]);
            save(name+"-hardware-attempt-"+attempt+".png",nativeWindow);save(name+"-compositor-attempt-"+attempt+".png",compositor);
            attempts.add(Json.map("attempt",n(attempt),"current",true,"windowOriginPx",List.of(n(windowOrigin[0]),n(windowOrigin[1])),"screenOriginPx",List.of(n(screenOrigin[0]),n(screenOrigin[1])),
                "rootSizePx",List.of(n(size[0]),n(size[1])),"windowSizePx",List.of(n(size[2]),n(size[3])),"safeTopPx",n(safe[0]),"safeBottomPx",n(safe[1]),
                "windowInkIntersectionOverUnion",new Json.Num(Double.toString(windowMatch)),"compositorInkIntersectionOverUnion",new Json.Num(Double.toString(screenMatch))));
            boolean matching=windowMatch>=.75&&screenMatch>=.75;
            if(matching){save(name+"-hardware.png",nativeWindow);save(name+"-compositor.png",compositor);save(name+"-software.png",software);ui(()->export(name+"-map.json"));}
            nativeWindow.recycle();compositor.recycle();software.recycle();
            saveBytes(name+"-capture.json",encode(Json.map("scope","Frame-committed public PixelCopy hardware window and UiAutomation compositor capture; structural ink correspondence to current native software render, not cross-platform pixel parity", "attempts",attempts)));
            if(matching){check(true,"committed native hardware/compositor ink corresponds to current native scene");return;}
        }throw new AssertionError("native hardware/compositor capture did not match committed scene: "+name);
    }
    private void saveBytes(String name,byte[] bytes){try(FileOutputStream out=new FileOutputStream(new File(activity.getFilesDir(),name))){out.write(bytes);}catch(java.io.IOException failure){throw new AssertionError(failure);}}
    private static Json.Num n(long value){return new Json.Num(Long.toString(value));}
    private void export(String name){
        NativeEnvironmentV2 env=renderer.captureEnvironmentV2(activity,activity.root);var e=env.value;
        List<Object> nodes=new ArrayList<>();for(var entry:renderer.inspectV2().entrySet()){
            var r=entry.getValue();View view=r.view;int[] origin=new int[2];view.getLocationInWindow(origin);var box=r.geometry.box;
            Map<String,Object> item=Json.map("id",r.id,"kind",r.kind,"generation",r.generation,"nativeClass",view.getClass().getName(),
                "pixels",Json.map("left",n(origin[0]),"top",n(origin[1]),"width",n(view.getWidth()),"height",n(view.getHeight())),
                "logical64",Json.map("x",n(box.x()),"y",n(box.y()),"width",n(box.width()),"height",n(box.height())),"semanticHeight64",n(r.geometry.semanticHeight));
            if(view instanceof TextView text){item.put("nativeText",text.getText().toString());item.put("fontPx",new Json.Num(Float.toString(text.getTextSize())));item.put("fontWeight",n(text.getTypeface().getWeight()));
                item.put("nativeTextColor",String.format(java.util.Locale.ROOT,"#%08X",text.getCurrentTextColor()));item.put("lineCount",n(text.getLineCount()));item.put("firstBaselinePx",n(text.getBaseline()));}
            if(r.header!=null&&r.geometry.header!=null){var frame=r.geometry.header;int[] headerOrigin=new int[2];r.header.getLocationInWindow(headerOrigin);
                item.put("header",Json.map("nativeText",r.header.getText().toString(),"logical64",Json.map("x",n(frame.x()),"y",n(frame.y()),"width",n(frame.width()),"height",n(frame.height())),
                    "pixels",Json.map("left",n(headerOrigin[0]),"top",n(headerOrigin[1]),"width",n(r.header.getWidth()),"height",n(r.header.getHeight())),
                    "lineCount",n(r.header.getLineCount()),"layoutHeightPx",n(r.header.getLayout().getHeight()),"fontPx",new Json.Num(Float.toString(r.header.getTextSize())),"fontWeight",n(r.header.getTypeface().getWeight())));}
            List<Object> groups=new ArrayList<>();for(var group:r.geometry.groups)groups.add(Json.map("width64",n(group.box.width()),"height64",n(group.box.height()),"nativePathEmpty",group.path.isEmpty(),"separators",group.separators.stream().map(NativeAppearanceV2Instrumentation::n).toList()));item.put("groups",groups);nodes.add(item);
        }
        saveBytes(name,encode(Json.map("scope","actual native API37 emulator; independent fixture; no engine/JNI join or parity claim", "descriptorSHA256",installed.sha256,
            "environment",Json.map("scheme",e.scheme().name(),"direction",e.direction().name(),"profile",e.profile().name(),"density1024",n(e.density1024()),"viewportWidth64",n(e.viewport().width64()),"viewportHeight64",n(e.viewport().height64()),"safeTop64",n(e.safeArea64().top()),"safeLeading64",n(e.safeArea64().leading()),"safeBottom64",n(e.safeArea64().bottom()),"safeTrailing64",n(e.safeArea64().trailing()),"locale",e.localeIdentifier(),"generation",e.generation()),"nodes",nodes)));
    }
    private void basic(){
        renderer=new NativeRenderer(activity,events::add);installed=renderer.captureInstalledV2();byte[] owned=installed.descriptorCopy();owned[0]='!';
        check(installed.descriptorCopy()[0]=='{',"captured descriptor defensive copy");
        NativeEnvironmentV2 env=renderer.captureEnvironmentV2(activity,activity.root);
        check(env.value.profile()==AppearanceDescriptorV2.Profile.l,"actual SP17/DIP1 profile l");
        byte[] bytes=scene(revision++,"native",false);saveBytes("all-ten-packet.json",bytes);saveBytes("appearance-descriptor.json",installed.descriptorCopy());NativeRenderer.Candidate candidate=renderer.prepareV2(bytes,installed,env);Arrays.fill(bytes,(byte)'!');
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
        check(events.isEmpty(),"prepare/attach/binding has zero events");
        Bitmap canvas=Bitmap.createBitmap(activity.root.getWidth(),activity.root.getHeight(),Bitmap.Config.ARGB_8888);activity.root.draw(new Canvas(canvas));
        check(canvas.getPixel(0,0)==NativeAppearanceViewsV2.color(installed.configuration.android.light().canvas()),"explicit captured canvas covers native safe-area region once");canvas.recycle();software("all-ten-software.png");export("all-ten-map.json");
        View stable=renderer.view("button");View scroll=renderer.view("list");View editor=renderer.view("field");
        publish(scene(revision++,"native",false));check(renderer.view("button")==stable&&renderer.view("list")==scroll&&renderer.view("field")==editor,"identity survives publication");
        check(events.isEmpty(),"repaint emits no guest event");
        Map<String,Object> disabled=Json.object(Json.parse(scene(revision++,"native",false)));
        Json.object(Json.object(Json.object(disabled.get("document")).get("root")).get("properties")).put("disabled",true);publish(encode(disabled));
        var paints=installed.configuration.android.light();
        check(!stable.isEnabled()&&((TextView)stable).getCurrentTextColor()==NativeAppearanceViewsV2.color(paints.button().normal().disabled().label()),"actual inherited-disabled native Button exact label paint");
        check(((EditText)editor).getHighlightColor()==0&&((EditText)editor).getCurrentTextColor()==NativeAppearanceViewsV2.color(paints.field().disabled().text()),"actual disabled native EditText text/selection paints");
        Switch disabledSwitch=(Switch)renderer.view("toggle");Bitmap switchBitmap=Bitmap.createBitmap(disabledSwitch.getWidth(),disabledSwitch.getHeight(),Bitmap.Config.ARGB_8888);disabledSwitch.draw(new Canvas(switchBitmap));
        int trackWidth=AppearanceGeometryV2.pixelEdge(installed.configuration.android.toggle().trackWidth64(),env.value.density1024());
        int sample=disabledSwitch.getWidth()-trackWidth+AppearanceGeometryV2.pixelEdge(5*64,env.value.density1024());
        check(switchBitmap.getPixel(sample,disabledSwitch.getHeight()/2)==NativeAppearanceViewsV2.color(paints.toggle().on().disabled().track()),"actual closed Switch disabled-on track raster");switchBitmap.recycle();
        check(((TextView)renderer.view("body")).getCurrentTextColor()==NativeAppearanceViewsV2.color(paints.text().body()),"inherited-disabled ordinary Text keeps exact role ink");software("disabled-software.png");
        publish(scene(revision++,"native",false));check(events.isEmpty(),"disabled binding/repaint emits no guest event");
        UiPacket acknowledged=renderer.packet;byte[] environmentOnly=lastPublishedBytes.clone();activity.root.setLayoutDirection(View.LAYOUT_DIRECTION_RTL);
        NativeRenderer.Candidate environmental=renderer.prepareV2(environmentOnly,installed,renderer.captureEnvironmentV2(activity,activity.root));Arrays.fill(environmentOnly,(byte)'!');
        NativeRenderer.AttachmentJournal environmentJournal=renderer.attachV2(environmental,activity.root);renderer.validateAttachedV2(environmental,environmentJournal);renderer.finishV2(environmental,environmentJournal);
        check(renderer.packet==acknowledged&&renderer.view("button")==stable&&stable.getLayoutDirection()==View.LAYOUT_DIRECTION_RTL,"exact-byte environment-only commit retains exact packet/revision/native identity");
        activity.root.setLayoutDirection(View.LAYOUT_DIRECTION_LTR);publish(lastPublishedBytes.clone());
        check(renderer.packet==acknowledged&&events.isEmpty(),"environment-only candidate bytes owned defensively and event silent");
        Map<String,Object> changed=Json.object(Json.parse(lastPublishedBytes));Json.object(Json.object(Json.object(changed.get("document")).get("root")).get("properties")).put("accessibilityHint","changed at same revision");
        reject(()->renderer.prepareV2(encode(changed),installed,renderer.captureEnvironmentV2(activity,activity.root)),"changed bytes at same revision");
        reject(()->renderer.prepareV2(scene(0,"native",false),installed,renderer.captureEnvironmentV2(activity,activity.root)),"older packet cannot become environment-only update");
        ((Button)stable).performClick();check(events.size()==1,"one actual Button activation");events.clear();
        ((Switch)renderer.view("toggle")).performClick();check(events.size()==1,"one actual Switch value change");
        check(!((Switch)renderer.view("toggle")).isChecked(),"native transient input can differ from acknowledged packet");
        UiPacket beforeTransientEnvironment=renderer.packet;publish(lastPublishedBytes.clone());
        check(!((Switch)renderer.view("toggle")).isChecked()&&renderer.packet==beforeTransientEnvironment&&events.size()==1,"byte-identical environment-only publication retains transient native Switch value");
        publish(scene(revision++,"native",false));
        check(((Switch)renderer.view("toggle")).isChecked()&&events.size()==1,"authoritative unchanged-value publication reasserts Switch without synthesizing input");events.clear();
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
        NativeRenderer.Candidate focus=renderer.prepareV2(scene(revision++,"native",false),installed,renderer.captureEnvironmentV2(activity,activity.root));
        check(renderer.view("toggle").requestFocusFromTouch(),"actual native focus transition while candidate pending");
        reject(()->renderer.attachV2(focus,activity.root),"native focus invalidates candidate epoch");renderer.discardV2(focus);button.requestFocusFromTouch();
        NativeRenderer.Candidate pressed=renderer.prepareV2(scene(revision++,"native",false),installed,renderer.captureEnvironmentV2(activity,activity.root));
        boolean wasPressed=button.isPressed();button.setPressed(!wasPressed);reject(()->renderer.attachV2(pressed,activity.root),"pressed-only native state invalidates exact snapshot");renderer.discardV2(pressed);button.setPressed(wasPressed);
        NativeEnvironmentV2 captured=renderer.captureEnvironmentV2(activity,activity.root);NativeRenderer.Candidate staleWindow=renderer.prepareV2(scene(revision++,"native",false),installed,captured);
        activity.root.setLayoutDirection(View.LAYOUT_DIRECTION_RTL);reject(()->renderer.attachV2(staleWindow,activity.root),"stale actual window direction");renderer.discardV2(staleWindow);activity.root.setLayoutDirection(View.LAYOUT_DIRECTION_LTR);
        NativeRenderer.Candidate staleBase=renderer.prepareV2(scene(revision++,"native",false),installed,renderer.captureEnvironmentV2(activity,activity.root));
        UiPacket original=renderer.packet;renderer.packet=UiPacket.decode(scene(revision++,"native",false));reject(()->renderer.attachV2(staleBase,activity.root),"exact base packet identity");renderer.packet=original;renderer.discardV2(staleBase);
        Object huge=node("huge","hStack",Json.map("spacing",num(256)),List.of(node("one","button",Json.map("label","one"),List.of()),node("two","button",Json.map("label","two"),List.of()),node("three","button",Json.map("label","three"),List.of())));
        reject(()->renderer.prepareV2(packet(huge,revision++),installed,renderer.captureEnvironmentV2(activity,activity.root)),"negative child width/invalid aggregate geometry");
        Object nested=node("nestedList","list",Map.of(),List.of(node("nestedStack","vStack",Map.of(),List.of(node("nestedButton","button",Json.map("label","nested"),List.of())))));
        reject(()->renderer.prepareV2(packet(nested,revision++),installed,renderer.captureEnvironmentV2(activity,activity.root)),"nested control row has no unproved hit routing");
        Object indirect=node("indirectNav","navigation",Json.map("title","Indirect"),List.of(node("navOverlay","zStack",Map.of(),List.of(node("indirectList","list",Map.of(),List.of(text("indirectText","row","body")))))));
        reject(()->renderer.prepareV2(packet(indirect,revision++),installed,renderer.captureEnvironmentV2(activity,activity.root)),"indirect navigation/container/List compact relayout is unqualified");
        check(renderer.packet.revision.equals(base)&&activity.root.getChildAt(0)==root&&renderer.view("button")==button,"indirect navigation rejection leaves live tuple unchanged");

        NativeEnvironmentV2 stale=renderer.captureEnvironmentV2(activity,activity.root);NativeRenderer.Candidate c=renderer.prepareV2(scene(revision++,"native",false),installed,stale);
        NativeRenderer.Candidate replaced=c;renderer.captureInstalledV2();reject(()->renderer.attachV2(replaced,activity.root),"replaced installed capture");renderer.discardV2(c);installed=renderer.captureInstalledV2();
        c=renderer.prepareV2(scene(revision++,"native",false),installed,renderer.captureEnvironmentV2(activity,activity.root));
        NativeRenderer.Candidate attached=c;NativeRenderer.AttachmentJournal j=renderer.attachV2(attached,activity.root);renderer.rollbackV2(attached,j);
        check(renderer.packet.revision.equals(base),"explicit post-attach rollback retains base");
        reject(()->renderer.attachV2(attached,activity.root),"aborted candidate reuse");
    }
    private void editing(){
        // Separate shallow scene makes native editor ancestry/frame unchanged across an accepted echo.
        renderer.disposeV2();renderer=new NativeRenderer(activity,events::add);activity.root.removeAllViews();installed=renderer.captureInstalledV2();revision=1000;
        Object field=node("editingField","textField",Json.map("label","Edit","value","hello"),List.of());
        publish(packet(node("editingRoot","vStack",Json.map("alignment","leading"),List.of(field)),revision++));
        EditText editor=(EditText)renderer.view("editingField");editor.requestFocus();editor.setSelection(1,4);Editable identity=editor.getText();
        InputConnection connection=editor.onCreateInputConnection(new EditorInfo());check(connection!=null,"native InputConnection");
        connection.setComposingRegion(1,4);int start=BaseInputConnection.getComposingSpanStart(identity),end=BaseInputConnection.getComposingSpanEnd(identity);
        check(start==1&&end==4,"actual native composing span");
        NativeRenderer.Candidate composingOnly=renderer.prepareV2(packet(node("editingRoot","vStack",Json.map("alignment","leading"),List.of(field)),revision++),installed,renderer.captureEnvironmentV2(activity,activity.root));
        connection.setComposingRegion(0,2);reject(()->renderer.attachV2(composingOnly,activity.root),"composing-only span mutation invalidates exact snapshot");renderer.discardV2(composingOnly);
        check(BaseInputConnection.getComposingSpanStart(identity)==0&&BaseInputConnection.getComposingSpanEnd(identity)==2,"stale-candidate rejection does not restore composing spans");connection.setComposingRegion(1,4);
        int selectionStart=editor.getSelectionStart(),selectionEnd=editor.getSelectionEnd();
        android.text.SpannableString styled=new android.text.SpannableString("red");styled.setSpan(new android.text.style.ForegroundColorSpan(0xffff0000),0,3,android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        check(!connection.setComposingText(styled,1),"native rich appearance span cannot override admitted paints/font");
        check(!connection.setComposingText("x".repeat(16385),1)&&!connection.setComposingText("\uD800",1),"oversized native IME proposal rejected before mutation");
        check(editor.getText()==identity&&editor.getText().toString().equals("hello")&&editor.getSelectionStart()==selectionStart&&editor.getSelectionEnd()==selectionEnd&&BaseInputConnection.getComposingSpanStart(identity)==start&&BaseInputConnection.getComposingSpanEnd(identity)==end,"rejected native IME proposal preserves exact buffer/selection/composition");
        publish(packet(node("editingRoot","vStack",Json.map("alignment","leading"),List.of(field)),revision++));
        check(renderer.view("editingField")==editor&&editor.getText()==identity&&editor.hasFocus(),"editor/Editable/focus identity retained");
        check(editor.getSelectionStart()==1&&editor.getSelectionEnd()==4&&BaseInputConnection.getComposingSpanStart(identity)==start&&BaseInputConnection.getComposingSpanEnd(identity)==end,"native selection/composition retained without restore");
        Object conflict=node("editingField","textField",Json.map("label","Edit","value","conflict"),List.of());
        reject(()->renderer.prepareV2(packet(node("editingRoot","vStack",Json.map("alignment","leading"),List.of(conflict)),revision++),installed,
            renderer.captureEnvironmentV2(activity,activity.root)),"conflicting composition before attachment");
        check(editor.getText()==identity&&editor.getText().toString().equals("hello")&&BaseInputConnection.getComposingSpanStart(identity)==1,"rejection leaves actual composing editor untouched");
        NativeRenderer.Candidate selection=renderer.prepareV2(packet(node("editingRoot","vStack",Json.map("alignment","leading"),List.of(field)),revision++),installed,renderer.captureEnvironmentV2(activity,activity.root));
        editor.setSelection(0);reject(()->renderer.attachV2(selection,activity.root),"native selection invalidates candidate epoch");renderer.discardV2(selection);editor.setSelection(1,4);
        events.clear();connection.setComposingText("abc",1);check(events.size()==1,"one native composing proposal event");
        String transientText=editor.getText().toString();int transientStart=BaseInputConnection.getComposingSpanStart(identity),transientEnd=BaseInputConnection.getComposingSpanEnd(identity);
        UiPacket acknowledged=renderer.packet;publish(lastPublishedBytes.clone());
        check(renderer.packet==acknowledged&&editor.getText()==identity&&editor.getText().toString().equals(transientText)&&BaseInputConnection.getComposingSpanStart(identity)==transientStart&&BaseInputConnection.getComposingSpanEnd(identity)==transientEnd&&events.size()==1,"byte-identical environment-only commit retains transient native Editable/composition without setter");
        String nativeValue=editor.getText().toString();Object echo=node("editingField","textField",Json.map("label","Edit","value",nativeValue),List.of());
        publish(packet(node("editingRoot","vStack",Json.map("alignment","leading"),List.of(echo)),revision++));
        check(editor.getText()==identity&&events.size()==1,"engine echo preserves native Editable and has no extra event");
        connection.finishComposingText();connection.performEditorAction(EditorInfo.IME_ACTION_DONE);check(events.size()==2,"native submit at most once");events.clear();
        software("editing-software.png");
        NativeRenderer.Candidate candidate=renderer.prepareV2(packet(node("editingRoot","vStack",Json.map("alignment","leading"),List.of(echo)),revision++),installed,renderer.captureEnvironmentV2(activity,activity.root));
        renderer.testFaultV2(0,true);try{renderer.attachV2(candidate,activity.root);throw new AssertionError("fault missing");}catch(IllegalStateException expected){checks++;}
        check(renderer.testRetiredV2(),"rollback failure retires gated presentation");reject(()->renderer.captureInstalledV2(),"retired owner");
    }
    private void environmentGates(){
        renderer.disposeV2();activity.root.removeAllViews();renderer=new NativeRenderer(activity,events::add);installed=renderer.captureInstalledV2();publish(scene(revision++,"native",false));
        Button button=(Button)renderer.view("button");int width=activity.root.getWidth(),height=activity.root.getHeight();
        activity.root.layout(0,0,width-3,height);button.performClick();
        check(events.isEmpty()&&!((NativeAppearanceViewsV2.Gate)activity.root.getChildAt(0)).open,"actual root layout invalidation immediately gates old native actions/presentation");
        activity.root.layout(0,0,width,height);renderer.captureEnvironmentV2(activity,activity.root);button.performClick();
        check(events.isEmpty(),"valid recapture alone cannot reopen committed gate");publish(lastPublishedBytes.clone());button.performClick();
        check(events.size()==1,"successful environment transaction reopens native input");events.clear();
        android.content.res.Configuration original=new android.content.res.Configuration(activity.getResources().getConfiguration());
        try{
            android.content.res.Configuration bold=new android.content.res.Configuration(original);bold.fontWeightAdjustment=50;
            activity.getResources().updateConfiguration(bold,activity.getResources().getDisplayMetrics());button.performClick();
            check(events.isEmpty()&&!((NativeAppearanceViewsV2.Gate)activity.root.getChildAt(0)).open,"synchronous committed native tuple check suppresses unsupported bold-context action before listener");
            reject(()->renderer.captureEnvironmentV2(activity,activity.root),"unsupported committed native environment recapture");
            check(renderer.testRetiredV2()&&activity.root.getChildAt(0).getVisibility()==View.INVISIBLE,"unsupported recapture retires gated old owner");button.performClick();check(events.isEmpty(),"retired unsupported environment cannot deliver old action");
        }finally{activity.getResources().updateConfiguration(original,activity.getResources().getDisplayMetrics());}
        renderer.disposeV2();activity.root.removeAllViews();renderer=new NativeRenderer(activity,events::add);installed=renderer.captureInstalledV2();publish(scene(revision++,"native",false));
        renderer.testExhaustInteractionV2();((Button)renderer.view("button")).performClick();
        check(renderer.testRetiredV2()&&events.isEmpty(),"checked interaction epoch overflow retires before action send");
    }
    private void buttonInsets(){
        renderer=new NativeRenderer(activity,events::add);installed=renderer.captureInstalledV2();
        Object shortButton=node("insetShort","button",Json.map("label","Short"),List.of());
        Object longButton=node("insetLong","button",Json.map("label","A long native button label with enough words to wrap under a finite width proposal and preserve every measured line"),List.of());
        publish(packet(node("insetRoot","vStack",Json.map("alignment","leading"),List.of(shortButton,longButton)),revision++));
        for(String id:List.of("insetShort","insetLong")){Button button=(Button)renderer.view(id);var record=renderer.inspectV2().get(id);var in=installed.configuration.android.button().labelInsets64();
            check(button.getPaddingLeft()==NativeAppearanceViewsV2.px(in.leading(),record.binding)&&button.getPaddingRight()==NativeAppearanceViewsV2.px(in.trailing(),record.binding),"authored horizontal Button insets enter actual native measurement");
            check(button.getHeight()>=button.getLayout().getHeight()+button.getPaddingTop()+button.getPaddingBottom(),"native Button measured Layout plus vertical insets fits actual view");
            check(record.geometry.semanticHeight==NativeAppearanceViewsV2.sum(NativeAppearanceViewsV2.logical(button.getLayout().getHeight(),record.binding),in.top(),in.bottom()),"Button semantic extent includes vertical authored insets");
        }
        Button shorter=(Button)renderer.view("insetShort"),longer=(Button)renderer.view("insetLong");
        check(shorter.getWidth()>=Math.ceil(shorter.getLayout().getLineWidth(0))+shorter.getPaddingLeft()+shorter.getPaddingRight()-1,"intrinsic native Button width includes both label insets");
        check(longer.getLineCount()>1&&longer.getWidth()<=activity.root.getWidth(),"nonzero-inset long native Button wraps under finite proposal");
    }
    private float scaleFor(double target){
        float low=.5f,high=6;
        for(int iteration=0;iteration<30;iteration++){float mid=(low+high)/2;android.content.res.Configuration c=new android.content.res.Configuration();c.fontScale=mid;
            var metrics=activity.createConfigurationContext(c).getResources().getDisplayMetrics();double body=android.util.TypedValue.applyDimension(android.util.TypedValue.COMPLEX_UNIT_SP,17,metrics)/(double)android.util.TypedValue.applyDimension(android.util.TypedValue.COMPLEX_UNIT_DIP,1,metrics);
            if(body<target)low=mid;else high=mid;
        }return (low+high)/2;
    }
    private void preferences(){
        double[] targets={14.05,15,16,17,19,21,23,28,33,40,47,52.95};List<Object> reports=new ArrayList<>();
        for(int index=0;index<targets.length;index++){
            float scale=scaleFor(targets[index]);int current=index;
            ui(()->{renderer.disposeV2();activity.finish();});
            android.content.res.Configuration config=new android.content.res.Configuration();config.fontScale=scale;
            boolean dark=index%2!=0,rtl=index%3==0;
            config.uiMode=dark?android.content.res.Configuration.UI_MODE_NIGHT_YES:android.content.res.Configuration.UI_MODE_NIGHT_NO;
            config.setLocale(java.util.Locale.forLanguageTag(rtl?"ar":"en-US"));config.setLayoutDirection(java.util.Locale.forLanguageTag(rtl?"ar":"en-US"));
            NativeAppearanceV2Activity.testConfiguration=config;
            activity=(NativeAppearanceV2Activity)startActivitySync(new Intent(getTargetContext(),NativeAppearanceV2Activity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));waitForIdleSync();
            ui(()->{renderer=new NativeRenderer(activity,events::add);installed=renderer.captureInstalledV2();NativeEnvironmentV2 env=renderer.captureEnvironmentV2(activity,activity.root);
                check(env.value.profile()==AppearanceDescriptorV2.Profile.values()[current],"actual nonlinear Activity preference profile "+current+" got "+env.value.profile());
                check((env.value.scheme()==AppearanceResolverV2.Scheme.dark)==dark,"actual Activity night configuration");
                check((env.value.direction()==AppearanceResolverV2.Direction.rightToLeft)==rtl,"actual Activity locale/direction configuration");
                publish(scene(revision++,"native",false));TextView body=(TextView)renderer.view("body");
                check(body.getLayout().getHeight()<=body.getHeight(),"native mixed-script text grows at profile "+env.value.profile());
                double expected=AppearanceGeometryV2.pixelCoordinate(Math.round(targets[current])*64,env.value.density1024());
                check(Math.abs(body.getTextSize()-expected)<.01,"explicit PX selected body metric, no second SP multiplier");
                check(body.getTypeface().getWeight()==400,"actual systemSans weight400");
                check(events.isEmpty(),"preference rebind is event silent");
                export("profile-"+env.value.profile()+"-map.json");software("profile-"+env.value.profile()+"-software.png");
                var metrics=activity.getResources().getDisplayMetrics();reports.add(Json.map("profile",env.value.profile().name(),"scheme",env.value.scheme().name(),"direction",env.value.direction().name(),"nativeFontScaleSetting",new Json.Num(Float.toString(scale)),"nativeSP17",new Json.Num(Float.toString(android.util.TypedValue.applyDimension(android.util.TypedValue.COMPLEX_UNIT_SP,17,metrics))),"nativeDIP1",new Json.Num(Float.toString(android.util.TypedValue.applyDimension(android.util.TypedValue.COMPLEX_UNIT_DIP,1,metrics)))));
            });
        }
        saveBytes("preference-corpus.json",encode(Json.map("scope","Synthetic actual Activity configuration contexts on API37; not physical preference setting or other API support", "profiles",reports)));
    }
    private void interactions(){
        View button=renderer.view("button"),toggle=renderer.view("toggle");
        events.clear();touch(button);waitForIdleSync();check(events.size()==1,"real native button touch exactly once");events.clear();
        cancel(button);waitForIdleSync();check(events.isEmpty(),"native button touch cancellation");
        touch(toggle);waitForIdleSync();check(events.size()==1,"real native switch touch exactly once");events.clear();
        cancel(toggle);waitForIdleSync();check(events.isEmpty(),"native switch touch cancellation");
        ui(()->{check(button.requestFocusFromTouch()&&button.hasFocus(),"native keyboard focus acquired");button.setPressed(true);software("pressed-focus-software.png");button.setPressed(false);});
        long now=SystemClock.uptimeMillis();check(getUiAutomation().injectInputEvent(new KeyEvent(now,now,KeyEvent.ACTION_DOWN,KeyEvent.KEYCODE_DPAD_CENTER,0),true),"native keyboard down");
        check(getUiAutomation().injectInputEvent(new KeyEvent(now,now+30,KeyEvent.ACTION_UP,KeyEvent.KEYCODE_DPAD_CENTER,0),true),"native keyboard up");waitForIdleSync();check(events.size()==1,"native Button keyboard action once");events.clear();
        ui(()->{ScrollView scroll=(ScrollView)renderer.view("list");var nav=renderer.inspectV2().get("navigation");long overflow=nav.geometry.overflow;
            scroll.scrollTo(0,NativeAppearanceViewsV2.px(overflow+64,nav.binding));
            check(nav.compact.getVisibility()==View.VISIBLE&&nav.header.getVisibility()==View.INVISIBLE,"actual scroll snaps compact navigation at captured overflow: y="+scroll.getScrollY()+" overflow="+overflow+" nativeHeight="+scroll.getHeight()+" content="+scroll.getChildAt(0).getHeight()+" parent="+scroll.getParent().getClass().getName()+" compact="+nav.compact.getVisibility()+" expanded="+nav.header.getVisibility());
            check(nav.geometry.children.get("list").y()==nav.geometry.compactBar,"actual compact bar geometry");
            software("compact-software.png");int offset=scroll.getScrollY();publish(scene(revision++,"native",false));
            check(renderer.view("list")==scroll&&scroll.getScrollY()==offset,"actual ScrollView identity/offset retained across update");
            scroll.scrollTo(0,0);check(nav.header.getVisibility()==View.VISIBLE,"native scroll restores measured expanded title");});
    }
    private void cancel(View view){int[] location=new int[2];view.getLocationOnScreen(location);float x=location[0]+view.getWidth()/2f,y=location[1]+view.getHeight()/2f;
        long now=SystemClock.uptimeMillis();MotionEvent down=MotionEvent.obtain(now,now,MotionEvent.ACTION_DOWN,x,y,0),cancel=MotionEvent.obtain(now,now+30,MotionEvent.ACTION_CANCEL,x,y,0);
        check(getUiAutomation().injectInputEvent(down,true)&&getUiAutomation().injectInputEvent(cancel,true),"injected native cancellation");down.recycle();cancel.recycle();}
    private void paired(){
        renderer.disposeV2();activity.root.removeAllViews();renderer=new NativeRenderer(activity,events::add);installed=renderer.captureInstalledV2();
        try(java.io.InputStream stream=activity.getAssets().open("NativeAppearanceV2/paired-packet.bin")){byte[] bytes=stream.readAllBytes();publish(bytes);saveBytes("paired-packet.bin",bytes);}
        catch(java.io.IOException failure){throw new AssertionError(failure);}
        check(((TextView)renderer.view("selectable")).isTextSelectable(),"shared actual Swift packet selectable native TextView");
        TextView longer=(TextView)renderer.view("long"),shorter=(TextView)renderer.view("short");
        check(longer.getLineCount()>1&&shorter.getWidth()<longer.getWidth(),"shared unequal HStack overflow uses bounded proposals without stretching short child");
        check(renderer.inspectV2().values().stream().map(r->r.kind).distinct().count()==10,"same canonical Swift packet consumes all ten kinds");
    }
    private void pairedSelectionFault(){
        TextView selectable=(TextView)renderer.view("selectable");check(selectable.getText() instanceof android.text.Spannable,"real selectable native Spannable");
        NativeRenderer.Candidate selected=renderer.prepareV2(lastPublishedBytes.clone(),installed,renderer.captureEnvironmentV2(activity,activity.root));
        android.text.Selection.setSelection((android.text.Spannable)selectable.getText(),0,5);
        reject(()->renderer.attachV2(selected,activity.root),"plain selectable TextView selection invalidates exact snapshot without listener");renderer.discardV2(selected);
        check(selectable.getSelectionStart()==0&&selectable.getSelectionEnd()==5,"stale selection remains native; no restore claimed");
    }
    private Object semanticSection(String id,String title,List<Object> children){return node(id,"section",Json.map("title",title),children);}
    private void sections(boolean rtl){
        renderer.disposeV2();activity.root.removeAllViews();activity.root.setLayoutDirection(rtl?View.LAYOUT_DIRECTION_RTL:View.LAYOUT_DIRECTION_LTR);
        renderer=new NativeRenderer(activity,events::add);installed=renderer.captureInstalledV2();
        Object z=node("sectionOverlay","zStack",Json.map("alignment","center"),List.of(semanticSection("sectionShort","Short",List.of(text("sectionX","x","body"))),text("sectionLonger","Longer label","body")));
        Object h=node("sectionHorizontal","hStack",Map.of(),List.of(semanticSection("sectionHShort","Short",List.of(text("sectionHX","x","body"))),text("sectionHLonger","Longer label","body")));
        Object only=semanticSection("sectionOnly","Header only",List.of());
        Object childWide=semanticSection("sectionChildWide","I",List.of(text("sectionWideText","Wider child content","body")));
        String wrapped="A deliberately lengthy native Section header that wraps under the bounded horizontal child proposal";
        Object wrappedOnly=node("sectionWrapOnlyH","hStack",Map.of(),List.of(semanticSection("sectionWrapOnly",wrapped,List.of()),text("sectionWrapOnlyPeer","Side","body")));
        Object wrappedChild=node("sectionWrapChildH","hStack",Map.of(),List.of(semanticSection("sectionWrapChild",wrapped,List.of(text("sectionWrapX","x","body"))),text("sectionWrapChildPeer","Tail","body")));
        Object row=node("sectionSemanticRow","zStack",Json.map("alignment","center"),List.of(semanticSection("sectionInRow","Short",List.of(text("sectionRowX","x","body"))),text("sectionRowLonger","Longer row label","body")));
        Object list=node("sectionSemanticList","list",Map.of(),List.of(row));
        byte[] bytes=packet(node("sectionsRoot","vStack",Json.map("alignment","leading","spacing",num(12)),List.of(z,h,only,childWide,wrappedOnly,wrappedChild,list)),revision++);
        publish(bytes);saveBytes("sections-"+(rtl?"rtl":"ltr")+"-packet.json",bytes);var records=renderer.inspectV2();
        for(String id:List.of("sectionShort","sectionHShort","sectionOnly","sectionChildWide","sectionWrapOnly","sectionWrapChild","sectionInRow")){
            var r=records.get(id);var g=r.geometry;long intrinsic=g.header.width(),height=g.header.height();var recipe=(AppearanceResolverV2.SectionRecipe)r.binding.node().recipe();
            for(String child:recipeChildIDs(r)){intrinsic=Math.max(intrinsic,records.get(child).geometry.box.width());height=NativeAppearanceViewsV2.sum(height,records.get(child).geometry.box.height());}
            long gaps=recipe.headerToContentGap64();for(int gap:recipe.contentGaps64())gaps=NativeAppearanceViewsV2.sum(gaps,gap);
            check(g.box.width()==intrinsic,"semantic Section width is max actual native header/child, "+id+" rtl="+rtl);
            check(g.semanticHeight==NativeAppearanceViewsV2.sum(height,gaps),"semantic Section native header/child heights and exact gaps, "+id);
            check(g.header.x()==(rtl?g.box.width()-g.header.width():0),"semantic Section header logical-leading position, "+id);
            check(r.header.getLayout().getHeight()<=r.header.getHeight(),"semantic Section actual native header Layout fits, "+id);
            for(String child:recipeChildIDs(r)){var cb=g.children.get(child);check(cb.x()==(rtl?g.box.width()-cb.width():0),"semantic Section child logical-leading position, "+id);
                check(cb.y()>=g.header.height()+recipe.headerToContentGap64(),"semantic Section native child starts after header gap, "+id);}
        }
        var overlay=records.get("sectionOverlay");var shortSection=records.get("sectionShort");var longer=records.get("sectionLonger");
        check(shortSection.geometry.box.width()<longer.geometry.box.width()&&overlay.geometry.box.width()==longer.geometry.box.width(),"center ZStack keeps narrower Section intrinsic width");
        check(shortSection.geometry.box.x()==(overlay.geometry.box.width()-shortSection.geometry.box.width())/2,"center ZStack positions short Section by intrinsic extent");
        check(Math.abs((shortSection.view.getLeft()+shortSection.view.getRight())-(longer.view.getLeft()+longer.view.getRight()))<=1,"actual native centered Section and wider Text centers agree");
        var horizontal=records.get("sectionHorizontal");var hs=records.get("sectionHShort");var hp=records.get("sectionHLonger");var hr=(AppearanceResolverV2.HStackRecipe)horizontal.binding.node().recipe();
        check(horizontal.geometry.box.width()==NativeAppearanceViewsV2.sum(hs.geometry.box.width(),hp.geometry.box.width(),hr.gaps64().get(0)),"HStack intrinsic probe does not fill Section proposal");
        check(hs.geometry.box.width()==shortSection.geometry.box.width()&&horizontal.geometry.box.width()<records.get("sectionsRoot").geometry.box.width(),"same short Section extent survives HStack without unnecessary equal split");
        check(hs.geometry.box.x()==(rtl?horizontal.geometry.box.width()-hs.geometry.box.width():0),"HStack Section source-order placement mirrors in RTL");
        check(records.get("sectionOnly").geometry.semanticHeight==records.get("sectionOnly").geometry.header.height(),"header-only semantic Section has no content gap");
        check(records.get("sectionChildWide").geometry.box.width()==records.get("sectionWideText").geometry.box.width(),"child-wider Section uses native child width and aligns narrower header");
        check(records.get("sectionWrapOnly").header.getLineCount()>1&&records.get("sectionWrapChild").header.getLineCount()>1,"native constrained semantic Section headers actually wrap");
        check(((AppearanceResolverV2.SectionRecipe)records.get("sectionInRow").binding.node().recipe()).context() instanceof AppearanceResolverV2.WithinListRow,"nested semantic Section exercises within-list-row context");
        check(events.isEmpty(),"semantic Section prepare/attachment/layout is event silent");
    }
    private static List<String> recipeChildIDs(NativeAppearanceViewsV2.Record record){return record.binding.node().childIDs();}
    private void touch(View view){int[] location=new int[2];view.getLocationOnScreen(location);float x=location[0]+view.getWidth()/2f,y=location[1]+view.getHeight()/2f;
        long now=SystemClock.uptimeMillis();MotionEvent down=MotionEvent.obtain(now,now,MotionEvent.ACTION_DOWN,x,y,0),up=MotionEvent.obtain(now,now+30,MotionEvent.ACTION_UP,x,y,0);
        check(getUiAutomation().injectInputEvent(down,true)&&getUiAutomation().injectInputEvent(up,true),"real native injected touch");down.recycle();up.recycle();}
    @Override public void onStart(){Bundle result=new Bundle();try{
        activity=(NativeAppearanceV2Activity)startActivitySync(new Intent(getTargetContext(),NativeAppearanceV2Activity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        waitForIdleSync();
        String expected=arguments==null?null:arguments.getString("captureRejection");
        if(expected!=null){ui(()->{NativeRenderer owner=new NativeRenderer(activity,ignored->{});
            try{owner.captureInstalledV2();throw new AssertionError("invalid installed capture accepted");}catch(AppearanceDescriptorV2.Failure failure){check(failure.code.name().equals(expected),"actual AssetManager complete-catalog rejection "+failure.code);}});
        }else if(arguments!=null&&"true".equals(arguments.getString("buttonInsets"))){
            ui(this::buttonInsets);hardware("inset");
        }else{
            ui(this::basic);waitForIdleSync();interactions();
            hardware("all-ten");
            // Touch actual visible Button after native ScrollView positions it.
            ui(()->((ScrollView)renderer.view("list")).smoothScrollTo(0,0));waitForIdleSync();
            ui(this::faults);ui(this::paired);hardware("paired");ui(this::pairedSelectionFault);
            ui(()->sections(false));hardware("sections-ltr");ui(()->sections(true));hardware("sections-rtl");ui(()->activity.root.setLayoutDirection(View.LAYOUT_DIRECTION_LTR));
            ui(this::editing);ui(this::environmentGates);preferences();
        }
        result.putString("status","passed");result.putInt("checks",checks);result.putString("scope","API37 emulator actual native renderer; ordinary engine/JNI join pending");finish(0,result);
    }catch(Throwable failure){result.putString("status","failed");result.putString("failure",android.util.Log.getStackTraceString(failure));finish(1,result);}}
}
