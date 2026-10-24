package dev.mixer.android;

import android.app.Instrumentation;
import android.content.Intent;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.view.accessibility.AccessibilityNodeInfo;
import android.widget.Button;
import android.widget.Switch;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

/** Finite actual-View component supplement. Fixture Input acknowledgements are not engine commits. */
@SuppressWarnings("deprecation")
public final class AuthoredToggleSupplementInstrumentation extends Instrumentation {
    private AuthoredToggleSupplementActivity window;
    private NativeAppearanceViewsV2.Record record;
    private NativeAppearanceViewsV2.Binding binding;
    private NativeAppearanceViewsV2.Geometry measured;
    private byte[] descriptor;
    private Switch toggle;
    private boolean permit,rtl,dark;
    private int proposals,fixtureAcks,epochs,checks,events,cases;
    private int setupChecks,keyboardSetupChecks,keyboardSetupEvents;
    private final List<Object> keyboardSetupObservations=new ArrayList<>(),keyboardSetupRequests=new ArrayList<>();
    private int mode,overflowAt=-1; // 0 fixture accepts, 1 fixture rejects, 2 closes, 3 newer bind, 4 replacement.
    private long down,started,lastDeliveredTime;
    private final List<Object> results=new ArrayList<>();
    private final List<Object> observations=new ArrayList<>();
    private Bundle arguments;
    private final NativeAppearanceViewsV2.Input input=new NativeAppearanceViewsV2.Input(){
        public boolean open(NativeAppearanceViewsV2.Record candidate){return permit&&candidate==record&&candidate.view.isEnabled()&&candidate.view.isAttachedToWindow()&&candidate.view.isShown()&&candidate.view.hasWindowFocus();}
        public void interaction(){if(++epochs==overflowAt){permit=false;record.cancelToggleInput();}}
        public void event(NativeAppearanceViewsV2.Record candidate,String event,Object value){
            require(open(candidate)&&event.equals("valueChange")&&value instanceof Boolean,"ordinary component Input boundary");proposals++;
            if(mode==0){bind((Boolean)value);fixtureAcks++;}
            else if(mode==2){permit=false;record.cancelToggleInput();}
            else if(mode==3){bind(true);fixtureAcks++;}
            else if(mode==4){var old=record;old.cancelToggleInput();window.content.removeView(old.view);record=null;install(true);}
        }
    };
    @Override public void onCreate(Bundle args){super.onCreate(args);arguments=args;start();}
    private void require(boolean value,String label){if(++checks>512)throw new AssertionError("512 assertions");if(!value)throw new AssertionError(label);}
    private void setupRequire(boolean value,String label){setupChecks++;require(value,label);}
    private void main(Runnable action){FixtureFailures.main(this::runOnMainSync,action);}
    private void idle(){waitForIdleSync();if(SystemClock.uptimeMillis()-started>120000)throw new AssertionError("120 second supplement budget");}
    private static String sha(byte[] bytes){try{StringBuilder b=new StringBuilder();for(byte value:MessageDigest.getInstance("SHA-256").digest(bytes))b.append(String.format(java.util.Locale.ROOT,"%02x",value&255));return b.toString();}catch(java.security.NoSuchAlgorithmException e){throw new AssertionError(e);}}
    private byte[] packet(boolean checked){return new org.json.JSONObject(Json.map("schemaVersion",1,"document",Json.map("schemaVersion",1,"revision",1,"root",Json.map("id","toggle","kind","toggle","properties",Json.map("label","Authored toggle","value",checked,"accessibilityLabel","Supplement toggle","accessibilityHint","Native activation"),"children",List.of(),"actions",List.of(Json.map("id","change","event","valueChange")))),"identities",List.of(Json.map("id","toggle","generation",1)))).toString().getBytes(java.nio.charset.StandardCharsets.UTF_8);}
    private NativeAppearanceViewsV2.Binding binding(boolean checked){
        var env=new AppearanceResolverV2.Environment(dark?AppearanceResolverV2.Scheme.dark:AppearanceResolverV2.Scheme.light,rtl?AppearanceResolverV2.Direction.rightToLeft:AppearanceResolverV2.Direction.leftToRight,AppearanceDescriptorV2.Profile.l,3072,new AppearanceResolverV2.Viewport(25728,55936),new AppearanceResolverV2.SafeArea(0,0,0,0),"en-US",new AppearanceResolverV2.Accessibility(false,false,false),"1");
        byte[] bytes=packet(checked);var plan=AppearanceResolverV2.prepare(bytes,descriptor,env,AppearanceResolverV2.Platform.android);var source=UiPacket.decode(bytes).root;
        return new NativeAppearanceViewsV2.Binding(plan,plan.node("toggle"),source,AppearanceDescriptorV2.decode(descriptor).android);
    }
    private void install(boolean checked){
        binding=binding(checked);record=new NativeAppearanceViewsV2.Record(window,binding.source(),input);measured=new NativeAppearanceViewsV2.Geometry();measured.box=new NativeAppearanceViewsV2.Box(0,0,21334,2816);record.bind(binding,measured,false);toggle=(Switch)record.view;window.place(toggle,400);
    }
    private void bind(boolean checked){binding=binding(checked);record.bind(binding,measured,false);}
    private void reset(boolean checked,boolean direction,boolean scheme){
        main(()->{if(record!=null){record.cancelToggleInput();if(record.view.getParent() instanceof android.view.ViewGroup parent)parent.removeView(record.view);}window.content.removeAllViews();window.recreateScroll();rtl=direction;dark=scheme;permit=true;mode=0;overflowAt=-1;proposals=0;fixtureAcks=0;epochs=0;install(checked);});idle();
        main(()->{require(toggle.getWidth()==1000&&toggle.getHeight()==132,"exact component carrier frame");require(input.open(record),"fixture Input gate open and actual window focused");window.content.acquired=window.content.released=window.content.unownedRelease=0;});down=SystemClock.uptimeMillis();lastDeliveredTime=down;
    }
    private AuthoredToggleInputV2.Geometry geometry(){var m=((AppearanceResolverV2.ToggleRecipe)binding.node().recipe()).metrics();return AuthoredToggleInputV2.geometry(toggle.getWidth(),toggle.getHeight(),binding.density(),binding.rtl(),m.trackWidth64(),m.trackHeight64(),m.thumbWidth64(),m.thumbHeight64());}
    private double thumbStart(){return toggle.isChecked()?geometry().onCenter():geometry().offCenter();}
    private double end(){return toggle.isChecked()?geometry().offCenter():geometry().onCenter();}
    private MotionEvent event(int action,double x,double y,int contacts,int id,long time){
        MotionEvent.PointerProperties[] properties=new MotionEvent.PointerProperties[contacts];MotionEvent.PointerCoords[] points=new MotionEvent.PointerCoords[contacts];
        for(int i=0;i<contacts;i++){var p=new MotionEvent.PointerProperties();p.id=id+i;p.toolType=MotionEvent.TOOL_TYPE_FINGER;properties[i]=p;var c=new MotionEvent.PointerCoords();c.x=(float)x+i;c.y=(float)y;c.pressure=action==MotionEvent.ACTION_UP||action==MotionEvent.ACTION_CANCEL?0:1;c.size=1;points[i]=c;}
        return MotionEvent.obtain(down,time,action,contacts,properties,points,0,0,1,1,0,0,InputDevice.SOURCE_TOUCHSCREEN,0);
    }
    private void touch(int action,double x,double y){touch(action,x,y,1,7);}
    private void touch(int action,double x,double y,int contacts,int id){
        if(++events>512)throw new AssertionError("512 MotionEvents");long time=Math.max(lastDeliveredTime+1,SystemClock.uptimeMillis());lastDeliveredTime=time;
        main(()->{MotionEvent e=event(action,x,y,contacts,id,time);try{boolean returned=toggle.onTouchEvent(e);observations.add(Json.map("case",cases,"route","actual View.onTouchEvent component","action",action,"pointerCount",contacts,"pointerId",id,"x",x,"y",y,"eventTime",time,"returned",returned,"nativeChecked",toggle.isChecked(),"boundChecked",record.binding.nativeToggleValue(),"proposals",proposals,"fixtureAcknowledgements",fixtureAcks,"pressed",toggle.isPressed()));}finally{e.recycle();}});
    }
    private void drag(double x,double y){touch(MotionEvent.ACTION_DOWN,thumbStart(),66);touch(MotionEvent.ACTION_MOVE,x,y);}
    private void balanced(){main(()->require(window.content.acquired==window.content.released&&window.content.unownedRelease==0&&!window.content.disallowed,"acquired parent release exactly once"));}
    private void caseRun(String name,Runnable body){if(++cases>64)throw new AssertionError("64 cases");body.run();balanced();main(()->{results.add(Json.map("id",cases,"name",name,"status","passed-component-native","proposals",proposals,"fixtureAcknowledgements",fixtureAcks,"authoritativeCommits",null,"rawCheckedListenerCallbacks",null));});}
    private void snapshot(String name){
        idle();AtomicReference<Map<String,Object>> state=new AtomicReference<>();main(()->{require(!toggle.isChecked()&&!record.binding.nativeToggleValue()&&proposals==0,"preview retains committed component state");state.set(Json.map("name",name,"checked",toggle.isChecked(),"boundChecked",record.binding.nativeToggleValue(),"proposals",proposals,"geometry",Json.map("offCenter",geometry().offCenter(),"onCenter",geometry().onCenter(),"trackX",geometry().trackX()),"route","UiAutomation.takeScreenshot after native idle"));});
        Bitmap image=getUiAutomation().takeScreenshot();if(image==null)throw new AssertionError("screenshot unavailable");try(var stream=Files.newOutputStream(getTargetContext().getFilesDir().toPath().resolve(name+".png"),StandardOpenOption.CREATE_NEW)){if(!image.compress(Bitmap.CompressFormat.PNG,100,stream))throw new AssertionError("PNG");}catch(java.io.IOException e){throw new AssertionError(e);}finally{image.recycle();}observations.add(state.get());
    }
    private void key(int action,int repeat,boolean cancelled){main(()->{var e=new KeyEvent(down,SystemClock.uptimeMillis(),action,KeyEvent.KEYCODE_DPAD_CENTER,repeat,0,android.view.KeyCharacterMap.VIRTUAL_KEYBOARD,0,cancelled?KeyEvent.FLAG_CANCELED:0,InputDevice.SOURCE_KEYBOARD);toggle.dispatchKeyEvent(e);});}
    private record FocusBaseline(android.view.ViewParent parent,List<Integer> frame,List<Integer> screen,boolean focusable,boolean touchFocusable,boolean enabled,boolean checked,boolean boundChecked,boolean inTouchMode) {}
    private static List<Integer> focusFrame(View view){return List.of(view.getLeft(),view.getTop(),view.getRight(),view.getBottom(),view.getWidth(),view.getHeight(),view.getMeasuredWidth(),view.getMeasuredHeight());}
    private static List<Integer> focusScreen(View view){int[] point=new int[2];view.getLocationOnScreen(point);return List.of(point[0],point[1]);}
    private FocusBaseline focusBaseline(){return new FocusBaseline(toggle.getParent(),focusFrame(toggle),focusScreen(toggle),toggle.isFocusable(),toggle.isFocusableInTouchMode(),toggle.isEnabled(),toggle.isChecked(),record.binding.nativeToggleValue(),toggle.isInTouchMode());}
    private boolean stableFocusPolicy(FocusBaseline before){return toggle.getParent()==before.parent()&&focusFrame(toggle).equals(before.frame())&&focusScreen(toggle).equals(before.screen())&&toggle.isFocusable()==before.focusable()&&toggle.isFocusableInTouchMode()==before.touchFocusable()&&toggle.isEnabled()==before.enabled();}
    private boolean keyboardQuiet(FocusBaseline before){return proposals==0&&fixtureAcks==0&&!toggle.isPressed()&&toggle.isChecked()==before.checked()&&record.binding.nativeToggleValue()==before.boundChecked();}
    private void keyboardRequire(boolean value,String label){keyboardSetupChecks++;setupRequire(value,label);}
    private void keyboardObserve(String stage,Button control,FocusBaseline before,Boolean admitted){
        if(keyboardSetupObservations.size()>=32)throw new AssertionError("32 keyboard setup observations");
        keyboardSetupObservations.add(Json.map("case",cases,"stage",stage,"uptime",SystemClock.uptimeMillis(),"requestReturned",admitted,
            "state",window.focusState(toggle,control),"inputOpen",input.open(record),"permit",permit,"proposals",proposals,"fixtureAcknowledgements",fixtureAcks,
            "nativeChecked",toggle.isChecked(),"boundChecked",record.binding.nativeToggleValue(),"pressed",toggle.isPressed(),
            "stableToggle",before!=null&&stableFocusPolicy(before),"quiet",before!=null&&keyboardQuiet(before),
            "addedKeyboardSetupAssertionsBefore",keyboardSetupChecks,"addedSetupAssertionsBefore",setupChecks));
    }
    private void focus(){
        AtomicReference<Button> ownedControl=new AtomicReference<>();AtomicReference<FocusBaseline> baseline=new AtomicReference<>();
        int traceStart=window.keyboardTrace.snapshot().size(),modeStart=window.keyboardModeTrace.snapshot().size();Throwable failure=null;
        try{
            main(()->{baseline.set(focusBaseline());keyboardObserve("keyboard.control.install.before",null,baseline.get(),null);Button control=new Button(window);ownedControl.set(control);control.setText("Keyboard focus control");window.place(control,600);});idle();
            main(()->{
                Button control=ownedControl.get();window.keyboardCase=cases;window.observingKeyboard=true;
                keyboardObserve("keyboard.before",control,baseline.get(),null);
                keyboardRequire(window.ownedFocusVisible(toggle)&&window.ownedFocusVisible(control)&&toggle.isFocusable()&&control.isFocusable()&&
                    control.getClass()==Button.class&&stableFocusPolicy(baseline.get())&&!AuthoredToggleSupplementActivity.ancestorFocusBlocked(toggle)&&!AuthoredToggleSupplementActivity.ancestorFocusBlocked(control)&&input.open(record)&&keyboardQuiet(baseline.get()),"fixture keyboard owned visible focusable window and native control before navigation");
            });
            long time=SystemClock.uptimeMillis();
            for(int action=0;action<=1;action++){
                long eventTime=Math.max(time,SystemClock.uptimeMillis());
                Map<String,Object> request=Json.map("case",cases,"action",action,"keyCode",KeyEvent.KEYCODE_DPAD_DOWN,"source",InputDevice.SOURCE_KEYBOARD,"repeat",0,"downTime",time,"eventTime",eventTime,"dispatched",false);
                keyboardSetupRequests.add(request);
                sendKeySync(new KeyEvent(time,eventTime,action,KeyEvent.KEYCODE_DPAD_DOWN,0,0,android.view.KeyCharacterMap.VIRTUAL_KEYBOARD,0,0,InputDevice.SOURCE_KEYBOARD));
                keyboardSetupEvents++;request.put("dispatched",true);
            }
            idle();
            main(()->{
                Button control=ownedControl.get();keyboardObserve("keyboard.navigation.after",control,baseline.get(),null);
                keyboardRequire(!toggle.isInTouchMode()&&!control.isInTouchMode()&&window.deliveredKeyboardPair(traceStart,modeStart,cases,baseline.get().inTouchMode())&&
                    window.ownedFocusVisible(toggle)&&window.ownedFocusVisible(control)&&input.open(record)&&stableFocusPolicy(baseline.get())&&keyboardQuiet(baseline.get()),"fixture actual keyboard navigation leaves touch mode without activation or policy change");
                boolean admitted=control.requestFocus();keyboardObserve("keyboard.control.focus.after",control,baseline.get(),admitted);
                keyboardRequire(admitted&&control.isFocused()&&window.getWindow().getDecorView().findFocus()==control&&window.getCurrentFocus()==control&&
                    !control.isInTouchMode()&&stableFocusPolicy(baseline.get())&&keyboardQuiet(baseline.get()),"fixture unmodified native Button focus positive control");
                if(control.getParent() instanceof android.view.ViewGroup parent)parent.removeView(control);
            });idle();
            main(()->{
                Button control=ownedControl.get();keyboardObserve("keyboard.control.removed",control,baseline.get(),null);
                keyboardRequire(control.getParent()==null&&!control.isAttachedToWindow()&&stableFocusPolicy(baseline.get())&&!toggle.isInTouchMode()&&
                    window.ownedFocusVisible(toggle)&&input.open(record)&&keyboardQuiet(baseline.get()),"fixture native focus control removed and original toggle policy geometry retained");
                boolean admitted=toggle.requestFocus();keyboardObserve("keyboard.toggle.focus.after",control,baseline.get(),admitted);
                require(admitted,"native focus admitted");
            });idle();
            main(()->{
                keyboardObserve("keyboard.toggle.focus.settled",ownedControl.get(),baseline.get(),null);
                keyboardRequire(toggle.isFocused()&&window.getWindow().getDecorView().findFocus()==toggle&&window.getCurrentFocus()==toggle&&!toggle.isInTouchMode()&&
                    window.ownedFocusVisible(toggle)&&input.open(record)&&stableFocusPolicy(baseline.get())&&keyboardQuiet(baseline.get()),"fixture original native toggle owns settled keyboard focus without activation");
            });
        }catch(Throwable caught){failure=caught;}
        finally{
            failure=FixtureFailures.attempt(failure,()->main(()->{
                Button control=ownedControl.get();if(control!=null&&control.getParent() instanceof android.view.ViewGroup parent)parent.removeView(control);
                window.observingKeyboard=false;keyboardObserve("keyboard.cleanup",control,baseline.get(),null);
            }));
        }
        if(failure instanceof Error error)throw error;
        if(failure instanceof RuntimeException exception)throw exception;
        if(failure!=null)throw new AssertionError(failure);
    }
    private void cancelCase(String name,Runnable mutation){caseRun(name,()->{reset(false,false,false);double x=end();drag(x,66);main(mutation);touch(MotionEvent.ACTION_UP,x,66);main(()->require(proposals==0&&!toggle.isPressed(),"cancellation emits no proposal or resurrected pressed"));});}
    private Map<String,Object> scrollState(){
        int viewport=window.scroll.getHeight()-window.scroll.getPaddingTop()-window.scroll.getPaddingBottom();
        return Json.map("scrollY",window.scroll.getScrollY(),"proposals",proposals,"pressed",toggle.isPressed(),
            "scrollPositive",window.scroll.getScrollY()>0,"zeroProposals",proposals==0,"notPressed",!toggle.isPressed(),
            "positiveContentExtent",window.content.getHeight()>viewport,"contentHeight",window.content.getHeight(),"viewportHeight",viewport,
            "nativeChecked",toggle.isChecked(),"boundChecked",record.binding.nativeToggleValue(),"fixtureAcknowledgements",fixtureAcks,
            "inputOpen",input.open(record),"parentAcquired",window.content.acquired,"parentReleased",window.content.released,
            "unownedRelease",window.content.unownedRelease,"disallowed",window.content.disallowed);
    }
    private void dispatchScroll(boolean diagonal){
        main(()->{window.componentState=this::scrollState;window.traceCase=cases;window.tracing=true;
            window.trace.add(Json.map("stage","scroll.geometry.before","case",cases,"uptime",SystemClock.uptimeMillis(),"diagonal",diagonal,"geometry",window.geometry(toggle),"state",scrollState()));
        });
        int[] xy=new int[2];main(()->toggle.getLocationOnScreen(xy));double x=xy[0]+geometry().offCenter(),y=xy[1]+66;
        main(()->{
            Map<String,Object> ownedInput=window.ownedInputGeometry(toggle,x,y,diagonal);
            window.trace.add(Json.map("stage","scroll.input.preconditions","case",cases,"uptime",SystemClock.uptimeMillis(),"geometry",window.geometry(toggle),"state",scrollState(),"ownedInput",ownedInput,"addedSetupAssertionsBefore",setupChecks));
            int viewport=window.scroll.getHeight()-window.scroll.getPaddingTop()-window.scroll.getPaddingBottom();
            setupRequire(viewport>0&&window.content.getMeasuredHeight()>viewport&&window.content.getHeight()>viewport&&window.scroll.canScrollVertically(1),"fixture positive measured content extent and canScrollDown before injection");
            setupRequire(window.scroll.getScrollX()==0&&window.scroll.getScrollY()==0,"fixture fresh scroll zero offset before injection");
            setupRequire(Boolean.TRUE.equals(ownedInput.get("admitted")),"fixture original first and last points within owned visible app input area");
        });
        long base=SystemClock.uptimeMillis();down=base;
        for(int i=0;i<=8;i++){int action=i==0?0:i==8?1:2;double dx=diagonal?i*10:0;MotionEvent e=event(action,x+dx,y-i*35,1,7,base+i*25);try{window.observe("worker.injection.before",e,null);sendPointerSync(e);events++;window.observe("worker.injection.after",e,null);}finally{e.recycle();}}
        idle();main(()->{window.trace.add(Json.map("stage","scroll.geometry.after","case",cases,"uptime",SystemClock.uptimeMillis(),"diagonal",diagonal,"geometry",window.geometry(toggle),"state",scrollState()));window.tracing=false;});
        main(()->require(window.scroll.getScrollY()>0&&proposals==0&&!toggle.isPressed(),"actual native ScrollView interception and CANCEL"));
    }
    @Override public void onStart(){
        started=SystemClock.uptimeMillis();Throwable failure=null;
        try{
            if(arguments==null||arguments.getString("apkSHA256")==null||arguments.getString("sourceClosureSHA256")==null)throw new AssertionError("root-bound executable/source identities required");
            try(InputStream s=getTargetContext().getAssets().open("MixerAppearanceV2/descriptor.json")){descriptor=s.readNBytes(65537);}catch(java.io.IOException e){throw new AssertionError(e);}
            window=(AuthoredToggleSupplementActivity)startActivitySync(new Intent(getTargetContext(),AuthoredToggleSupplementActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));idle();
            main(()->require(android.os.Build.VERSION.SDK_INT==37&&window.getResources().getDisplayMetrics().density==3f,"API37 density3 component tuple"));
            for(boolean direction:new boolean[]{false,true})for(boolean initial:new boolean[]{false,true})caseRun("endpoint direction="+direction+" initial="+initial,()->{reset(initial,direction,false);double x=end();drag(x,66);touch(1,x,66);main(()->require(toggle.isChecked()!=initial&&proposals==1&&fixtureAcks==1,"one ordinary proposal and fixture acknowledgement"));});
            for(boolean direction:new boolean[]{false,true})for(boolean scheme:new boolean[]{false,true})caseRun("continuous preview direction="+direction+" dark="+scheme,()->{reset(false,direction,scheme);double a=geometry().offCenter(),b=geometry().onCenter();drag(a+(b-a)*.375,66);snapshot("preview-"+direction+"-"+scheme);touch(3,a,66);main(()->require(!toggle.isChecked()&&proposals==0&&!toggle.isPressed(),"cancel preview"));});
            caseRun("crossing displacement and return side",()->{reset(false,false,false);var g=geometry();drag(g.offCenter()+24.75,66);touch(2,g.offCenter()+16.5,66);touch(1,g.offCenter()+16.5,66);main(()->require(proposals==0&&!toggle.isChecked(),"full crossing retained and return unchanged"));});
            caseRun("exact midpoint tie",()->{reset(false,false,false);double x=(geometry().offCenter()+geometry().onCenter())/2;drag(x,66);touch(1,x,66);main(()->require(proposals==0&&!toggle.isChecked(),"tie initial"));});
            caseRun("horizontal side release outside row",()->{reset(false,false,false);drag(1500,66);touch(1,1500,66);main(()->require(proposals==1&&toggle.isChecked(),"clamped side release"));});
            for(double y:new double[]{-66,198,-66.01,198.01})caseRun("corridor boundary y="+y,()->{reset(false,false,false);double x=end();drag(x,66);touch(2,x,y);touch(1,x,y);main(()->require(proposals==(y>=-66&&y<=198?1:0),"inclusive corridor"));});
            caseRun("label held tap no long press commit",()->{reset(false,false,false);touch(0,30,66);SystemClock.sleep(ViewConfiguration.getLongPressTimeout()+50);main(()->require(proposals==0,"no long press activation"));touch(1,30,66);main(()->require(proposals==1,"held UP once"));});
            caseRun("label horizontal drift cancels",()->{reset(false,false,false);touch(0,30,66);touch(2,90,66);touch(1,90,66);main(()->require(proposals==0,"label drift"));});
            caseRun("native parent vertical scroll",()->{reset(false,false,false);dispatchScroll(false);});
            caseRun("native parent diagonal vertical dominance",()->{reset(false,false,false);dispatchScroll(true);});
            caseRun("history crossing and return",()->{reset(false,false,false);double a=thumbStart();touch(0,a,66);main(()->{long t=Math.max(lastDeliveredTime+1,SystemClock.uptimeMillis());lastDeliveredTime=t+1;MotionEvent e=event(2,a+24.75,66,1,7,t);try{e.addBatch(t+1,(float)(a+16.5),66,1,1,0);require(e.getHistorySize()==1,"one actual MotionEvent historical sample");require(toggle.onTouchEvent(e)&&toggle.isPressed()&&proposals==0,"actual history retained active native preview");}finally{e.recycle();}});touch(1,a+16.5,66);main(()->require(proposals==0,"history unchanged"));});
            caseRun("extra pointer cancels no transfer",()->{reset(false,false,false);double x=end();drag(x,66);touch(MotionEvent.ACTION_POINTER_DOWN|(1<<MotionEvent.ACTION_POINTER_INDEX_SHIFT),x,66,2,7);touch(1,x,66);main(()->require(proposals==0,"extra pointer"));});
            caseRun("active pointer lost",()->{reset(false,false,false);double x=end();drag(x,66);touch(2,x,66,1,8);touch(1,x,66,1,8);main(()->require(proposals==0,"pointer loss"));});
            caseRun("ACTION_OUTSIDE cancellation",()->{reset(false,false,false);double x=end();drag(x,66);touch(4,x,66);touch(1,x,66);main(()->require(proposals==0,"outside event"));});
            cancelCase("disabled mid drag",()->toggle.setEnabled(false));
            cancelCase("equal binding replacement",()->record.bind(record.binding,measured,false));
            cancelCase("frame change mid drag",()->toggle.layout(toggle.getLeft(),toggle.getTop()+1,toggle.getRight(),toggle.getBottom()+1));
            cancelCase("parent rebinding mid drag",()->{window.content.removeView(toggle);window.root.addView(toggle);});
            cancelCase("detach mid drag",()->window.content.removeView(toggle));
            cancelCase("visibility loss",()->toggle.setVisibility(View.INVISIBLE));
            cancelCase("window focus loss callback",()->toggle.onWindowFocusChanged(false));
            cancelCase("fixture environment gate closes synchronously",()->{permit=false;record.cancelToggleInput();});
            caseRun("local interaction closes before preview",()->{reset(false,false,false);touch(0,thumbStart(),66);main(()->overflowAt=epochs+1);touch(2,end(),66);touch(1,end(),66);main(()->require(proposals==0&&!toggle.isPressed(),"epoch cancellation fence"));});
            caseRun("engine-style rejected fixture proposal restores latest",()->{reset(false,false,false);main(()->mode=1);main(()->toggle.performClick());main(()->require(proposals==1&&fixtureAcks==0&&!toggle.isChecked(),"one proposal zero fixture acknowledgement"));});
            caseRun("synchronous newer binding wins",()->{reset(true,false,false);main(()->mode=3);main(()->toggle.performClick());main(()->require(proposals==1&&toggle.isChecked()&&record.binding.nativeToggleValue(),"latest true binding"));});
            caseRun("synchronous retirement restores old view",()->{reset(false,false,false);main(()->mode=2);main(()->toggle.performClick());main(()->require(proposals==1&&!permit&&!toggle.isChecked(),"closed fixture owner restoration"));});
            caseRun("synchronous record replacement unaffected by old restoration",()->{reset(false,false,false);Switch old=toggle;main(()->mode=4);main(()->old.performClick());idle();main(()->require(proposals==1&&toggle!=old&&toggle.isChecked()&&!old.isChecked(),"replacement isolation"));});
            caseRun("native accessibility role checked and click",()->{reset(false,false,false);main(()->{AccessibilityNodeInfo n=toggle.createAccessibilityNodeInfo();try{require(n.isCheckable()&&!n.isChecked()&&n.getClassName().toString().equals("android.widget.Switch"),"native Switch role checked metadata");require(toggle.performAccessibilityAction(AccessibilityNodeInfo.ACTION_CLICK,new Bundle()),"native AX click accepted");require(proposals==1&&toggle.isChecked(),"AX ordinary proposal");}finally{n.recycle();}});});
            caseRun("disabled accessibility rejection",()->{reset(false,false,false);main(()->{toggle.setEnabled(false);require(!toggle.performAccessibilityAction(AccessibilityNodeInfo.ACTION_CLICK,new Bundle())&&proposals==0,"disabled AX");});});
            caseRun("stale accessibility and keyboard rejection",()->{reset(false,false,false);main(()->permit=false);main(()->require(!toggle.performAccessibilityAction(AccessibilityNodeInfo.ACTION_CLICK,new Bundle()),"stale AX"));key(0,0,false);key(1,0,false);main(()->require(proposals==0,"stale key"));});
            caseRun("native keyboard activation",()->{reset(false,false,false);focus();key(0,0,false);key(1,0,false);main(()->require(proposals==1&&toggle.isChecked(),"native key one proposal"));});
            caseRun("native key repeat does not multiply",()->{reset(false,false,false);focus();key(0,0,false);key(0,1,false);key(0,2,false);main(()->require(proposals==0,"repeat no early proposal"));key(1,0,false);main(()->require(proposals==1,"repeat UP once"));});
            caseRun("cancelled native key no activation",()->{reset(false,false,false);focus();key(0,0,false);key(1,0,true);main(()->require(proposals==0,"cancelled key"));});
            caseRun("keyboard during held touch then old UP",()->{reset(false,false,false);focus();double x=thumbStart();touch(0,x,66);key(0,0,false);key(1,0,false);touch(1,x,66);main(()->require(proposals==1,"held key cancels touch"));});
            caseRun("accessibility during held touch then old UP",()->{reset(false,false,false);double x=thumbStart();touch(0,x,66);main(()->toggle.performAccessibilityAction(AccessibilityNodeInfo.ACTION_CLICK,new Bundle()));touch(1,x,66);main(()->require(proposals==1,"held AX cancels touch"));});
            caseRun("native focus order retained",()->{reset(false,false,false);main(()->{Button next=new Button(window);next.setText("Next");window.place(next,600);toggle.setNextFocusForwardId(View.generateViewId());next.setId(toggle.getNextFocusForwardId());require(toggle.focusSearch(View.FOCUS_FORWARD)==next,"native focusSearch");});});
        }catch(Throwable caught){failure=caught;}
        finally{
            failure=FixtureFailures.attempt(failure,()->{
                if(window!=null)main(()->{if(record!=null)record.cancelToggleInput();observations.add(Json.map("finally",true,"pressed",toggle!=null&&toggle.isPressed(),"parentAcquired",window.content.acquired,"parentReleased",window.content.released));window.finish();});
            });
            final Throwable retained=failure;
            Bundle bundle=new Bundle();
            failure=FixtureFailures.attempt(failure,()->{
                Map<String,Object> export=Json.map("schema",1,"scope","actual native View component fixture; fixture Input acknowledgements are not authoritative engine commits","status",retained==null?"passed-component-only":"failed-retained","failure",retained==null?null:retained.toString(),"apkSHA256",arguments==null?null:arguments.getString("apkSHA256"),"sourceClosureSHA256",arguments==null?null:arguments.getString("sourceClosureSHA256"),"cases",results,"observations",observations,"assertions",checks,"addedSetupAssertions",setupChecks,"originalAssertionCounter",checks-setupChecks,"addedScrollSetupAssertions",setupChecks-keyboardSetupChecks,"addedKeyboardSetupAssertions",keyboardSetupChecks,"keyboardSetupEvents",keyboardSetupEvents,"keyboardSetup",Json.map("schema",1,"requests",keyboardSetupRequests,"observations",keyboardSetupObservations,"nativeKeyTrace",window==null?List.of():window.keyboardTrace.snapshot(),"nativeModeTrace",window==null?List.of():window.keyboardModeTrace.snapshot(),"modeDropped",window==null?0:window.keyboardModeTrace.dropped(),"dropped",window==null?0:window.keyboardTrace.dropped(),"observerFailures",window==null?0:window.keyboardObserverFailures),"events",events,"durationMilliseconds",SystemClock.uptimeMillis()-started,"rawCheckedListenerCallbacks",null,"authoritativeCommits",null,"physicalPhones","deferred disconnected","TalkBackServiceWorkflow","NOT RUN");
                try{byte[] bytes=new org.json.JSONObject(export).toString().getBytes(java.nio.charset.StandardCharsets.UTF_8);if(bytes.length>8388608)throw new AssertionError("8MiB export");Files.write(getTargetContext().getFilesDir().toPath().resolve("toggle-supplement-results.json"),bytes,StandardOpenOption.CREATE_NEW);bundle.putString("exportSHA256",sha(bytes));}catch(java.io.IOException e){throw new AssertionError(e);}
            });
            failure=FixtureFailures.attempt(failure,()->{
                if(window==null)throw new AssertionError("scroll diagnostic window unavailable");
                byte[] bytes=new org.json.JSONObject(window.exportTrace()).toString().getBytes(java.nio.charset.StandardCharsets.UTF_8);
                if(bytes.length>524288)throw new AssertionError("512KiB scroll trace");
                try{Files.write(getTargetContext().getFilesDir().toPath().resolve("toggle-scroll-trace.json"),bytes,StandardOpenOption.CREATE_NEW);bundle.putString("scrollTraceSHA256",sha(bytes));}catch(java.io.IOException e){throw new AssertionError(e);}
            });
            final Throwable beforeDiagnostics=failure;
            failure=FixtureFailures.attempt(failure,()->{
                try{byte[] bytes=FixtureFailures.diagnostic(beforeDiagnostics).getBytes(java.nio.charset.StandardCharsets.UTF_8);if(bytes.length>131072)throw new AssertionError("128KiB diagnostics");Files.write(getTargetContext().getFilesDir().toPath().resolve("toggle-supplement-diagnostics.txt"),bytes,StandardOpenOption.CREATE_NEW);bundle.putString("diagnosticSHA256",sha(bytes));}catch(java.io.IOException e){throw new AssertionError(e);}
            });
            bundle.putString("status",failure==null?"passed-component-only":"failed-retained");
            if(failure!=null)bundle.putString("failure",failure.toString());
            finish(failure==null?-1:0,bundle);
        }
    }
}
