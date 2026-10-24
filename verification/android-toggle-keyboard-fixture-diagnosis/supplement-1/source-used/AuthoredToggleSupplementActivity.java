package dev.mixer.android;

import android.app.Activity;
import android.graphics.Rect;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowInsets;
import android.widget.FrameLayout;
import android.widget.ScrollView;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

/** Private observation-only component owner; the native superclass retains arbitration. */
@SuppressWarnings("deprecation")
public final class AuthoredToggleSupplementActivity extends Activity {
    FrameLayout root;ObservedScroll scroll;Parent content;boolean destroyed;
    final ScrollTraceBuffer trace=new ScrollTraceBuffer(2048);
    volatile boolean tracing;
    int traceCase;
    Supplier<Map<String,Object>> componentState=()->Json.map("available",false);
    private int observerFailures;
    void observe(String stage,MotionEvent event,Boolean returned){
        if(!tracing)return;
        try{
            Map<String,Object> row=Json.map("stage",stage,"case",traceCase,"uptime",SystemClock.uptimeMillis(),
                "thread",Thread.currentThread().getName(),"returned",returned,"state",android.os.Looper.myLooper()==getMainLooper()?componentState.get():null);
            if(event!=null)row.put("event",Json.map("action",event.getAction(),"masked",event.getActionMasked(),
                "downTime",event.getDownTime(),"eventTime",event.getEventTime(),"eventTimeLead",event.getEventTime()-SystemClock.uptimeMillis(),
                "pointerCount",event.getPointerCount(),"pointerId",event.getPointerId(0),"tool",event.getToolType(0),
                "source",event.getSource(),"deviceId",event.getDeviceId(),"x",event.getX(),"y",event.getY(),
                "rawX",event.getRawX(),"rawY",event.getRawY(),"historySize",event.getHistorySize()));
            trace.add(row);
        }catch(RuntimeException failure){observerFailures++;}
    }
    void watch(View view){view.setOnTouchListener((target,event)->{observe("toggle.OnTouchListener.before-return-false",event,false);return false;});}
    @Override public boolean dispatchTouchEvent(MotionEvent event){
        observe("activity.dispatch.before",event,null);boolean result=super.dispatchTouchEvent(event);
        observe("activity.dispatch.after",event,result);return result;
    }
    final class ObservedScroll extends ScrollView {
        ObservedScroll(){super(AuthoredToggleSupplementActivity.this);}
        @Override public boolean dispatchTouchEvent(MotionEvent event){observe("scroll.dispatch.before",event,null);boolean result=super.dispatchTouchEvent(event);observe("scroll.dispatch.after",event,result);return result;}
        @Override public boolean onInterceptTouchEvent(MotionEvent event){observe("scroll.intercept.before",event,null);boolean result=super.onInterceptTouchEvent(event);observe("scroll.intercept.after",event,result);return result;}
        @Override public boolean onTouchEvent(MotionEvent event){observe("scroll.touch.before",event,null);boolean result=super.onTouchEvent(event);observe("scroll.touch.after",event,result);return result;}
        @Override public void requestDisallowInterceptTouchEvent(boolean value){super.requestDisallowInterceptTouchEvent(value);observe("scroll.disallow."+value,null,null);}
        int nativeRange(){return computeVerticalScrollRange();}
        int nativeExtent(){return computeVerticalScrollExtent();}
        int nativeOffset(){return computeVerticalScrollOffset();}
    }
    final class Parent extends FrameLayout {
        int acquired,released,unownedRelease;boolean disallowed;
        Parent(){super(AuthoredToggleSupplementActivity.this);}
        @Override public void requestDisallowInterceptTouchEvent(boolean value){
            if(value){acquired++;disallowed=true;}else{released++;if(!disallowed)unownedRelease++;disallowed=false;}
            super.requestDisallowInterceptTouchEvent(value);observe("content.disallow."+value,null,null);
        }
        @Override public boolean dispatchTouchEvent(MotionEvent event){observe("content.dispatch.before",event,null);boolean result=super.dispatchTouchEvent(event);observe("content.dispatch.after",event,result);return result;}
    }
    @Override public void onCreate(Bundle state){
        super.onCreate(state);getWindow().setDecorFitsSystemWindows(false);root=new FrameLayout(this);setContentView(root);
        recreateScroll();
    }
    void recreateScroll(){
        if(scroll!=null)root.removeView(scroll);
        scroll=new ObservedScroll();content=new Parent();content.setMinimumHeight(6000);scroll.addView(content,new ScrollView.LayoutParams(-1,6000));root.addView(scroll,new FrameLayout.LayoutParams(-1,-1));
    }
    @Override public void onDestroy(){destroyed=true;super.onDestroy();}
    void place(View view,int top){FrameLayout.LayoutParams lp=new FrameLayout.LayoutParams(1000,132);lp.leftMargin=60;lp.topMargin=top;content.addView(view,lp);watch(view);}
    static Map<String,Object> viewState(View view){
        int[] screen=new int[2],window=new int[2];view.getLocationOnScreen(screen);view.getLocationInWindow(window);
        Rect visible=new Rect();boolean hasVisible=view.getGlobalVisibleRect(visible);
        return Json.map("frame",List.of(view.getLeft(),view.getTop(),view.getRight(),view.getBottom()),
            "size",List.of(view.getWidth(),view.getHeight()),"measured",List.of(view.getMeasuredWidth(),view.getMeasuredHeight()),
            "screen",List.of(screen[0],screen[1]),"window",List.of(window[0],window[1]),
            "globalVisible",hasVisible,"globalVisibleRect",List.of(visible.left,visible.top,visible.right,visible.bottom),
            "shown",view.isShown(),"attached",view.isAttachedToWindow(),"windowFocused",view.hasWindowFocus(),
            "focused",view.isFocused(),"enabled",view.isEnabled(),"layoutRequested",view.isLayoutRequested());
    }
    Map<String,Object> geometry(View toggle){
        View decor=getWindow().getDecorView();Rect frame=new Rect();decor.getWindowVisibleDisplayFrame(frame);
        WindowInsets insets=decor.getRootWindowInsets();android.graphics.Insets system=insets==null?null:insets.getInsets(WindowInsets.Type.systemBars());
        int viewport=scroll.getHeight()-scroll.getPaddingTop()-scroll.getPaddingBottom();
        return Json.map("decor",viewState(decor),"root",viewState(root),"scroll",viewState(scroll),"content",viewState(content),"toggle",viewState(toggle),
            "windowVisibleFrame",List.of(frame.left,frame.top,frame.right,frame.bottom),
            "systemBarInsets",system==null?null:List.of(system.left,system.top,system.right,system.bottom),
            "contentLayoutHeight",content.getLayoutParams().height,"viewportHeight",viewport,"contentHeight",content.getHeight(),
            "positiveContentExtent",content.getHeight()>viewport,"computedRange",scroll.nativeRange(),"computedExtent",scroll.nativeExtent(),"computedOffset",scroll.nativeOffset(),
            "canScrollUp",scroll.canScrollVertically(-1),"canScrollDown",scroll.canScrollVertically(1),"density",getResources().getDisplayMetrics().density);
    }
    Map<String,Object> ownedInputGeometry(View toggle,double x,double y,boolean diagonal){
        View decor=getWindow().getDecorView();Rect frame=new Rect();decor.getWindowVisibleDisplayFrame(frame);
        Rect rootVisible=new Rect(),toggleVisible=new Rect();boolean rootHasVisible=root.getLocalVisibleRect(rootVisible),toggleHasVisible=toggle.getLocalVisibleRect(toggleVisible);
        int[] rootScreen=new int[2],toggleScreen=new int[2],decorScreen=new int[2];root.getLocationOnScreen(rootScreen);toggle.getLocationOnScreen(toggleScreen);decor.getLocationOnScreen(decorScreen);
        rootVisible.offset(rootScreen[0],rootScreen[1]);toggleVisible.offset(toggleScreen[0],toggleScreen[1]);
        WindowInsets insets=decor.getRootWindowInsets();android.graphics.Insets bars=insets==null?null:insets.getInsets(WindowInsets.Type.systemBars());
        int[] visibleFrame={frame.left,frame.top,frame.right,frame.bottom},rootRect={rootVisible.left,rootVisible.top,rootVisible.right,rootVisible.bottom};
        int[] decorRect={decorScreen[0],decorScreen[1],decorScreen[0]+decor.getWidth(),decorScreen[1]+decor.getHeight()};
        int[] system=bars==null?new int[]{0,0,0,0}:new int[]{bars.left,bars.top,bars.right,bars.bottom};
        int[] owned=FixtureInputBounds.intersect(visibleFrame,rootRect,decorRect,system);double lastX=x+(diagonal?8*10:0),lastY=y-8*35;
        boolean firstOnToggle=toggleHasVisible&&FixtureInputBounds.contains(new int[]{toggleVisible.left,toggleVisible.top,toggleVisible.right,toggleVisible.bottom},x,y);
        boolean windowOwned=bars!=null&&rootHasVisible&&root.isAttachedToWindow()&&root.isShown()&&root.hasWindowFocus()&&decor.hasWindowFocus()&&toggle.isAttachedToWindow()&&toggle.isShown()&&toggle.hasWindowFocus();
        boolean admitted=windowOwned&&firstOnToggle&&FixtureInputBounds.contains(owned,x,y)&&FixtureInputBounds.contains(owned,lastX,lastY);
        return Json.map("admitted",admitted,"windowOwned",windowOwned,"firstOnVisibleToggle",firstOnToggle,"insetsAvailable",bars!=null,
            "windowVisibleFrame",List.of(frame.left,frame.top,frame.right,frame.bottom),"rootVisibleScreen",List.of(rootVisible.left,rootVisible.top,rootVisible.right,rootVisible.bottom),
            "toggleVisibleScreen",List.of(toggleVisible.left,toggleVisible.top,toggleVisible.right,toggleVisible.bottom),"decorScreen",List.of(decorRect[0],decorRect[1],decorRect[2],decorRect[3]),
            "systemBarInsets",List.of(system[0],system[1],system[2],system[3]),"ownedVisibleScreen",List.of(owned[0],owned[1],owned[2],owned[3]),"firstPoint",List.of(x,y),"lastPoint",List.of(lastX,lastY));
    }
    final ScrollTraceBuffer keyboardTrace=new ScrollTraceBuffer(64);
    boolean observingKeyboard;
    int keyboardCase,keyboardObserverFailures;
    @Override public boolean dispatchKeyEvent(android.view.KeyEvent event){
        observeKeyboardKey("activity.key.before",event,null);
        boolean returned=super.dispatchKeyEvent(event);
        observeKeyboardKey("activity.key.after",event,returned);
        return returned;
    }
    private void observeKeyboardKey(String stage,android.view.KeyEvent event,Boolean returned){
        if(!observingKeyboard)return;
        try{keyboardTrace.add(Json.map("stage",stage,"case",keyboardCase,"uptime",SystemClock.uptimeMillis(),"returned",returned,
            "action",event.getAction(),"keyCode",event.getKeyCode(),"source",event.getSource(),"repeat",event.getRepeatCount(),
            "canceled",event.isCanceled(),"downTime",event.getDownTime(),"eventTime",event.getEventTime(),"deviceId",event.getDeviceId()));}
        catch(RuntimeException failure){keyboardObserverFailures++;}
    }
    boolean deliveredKeyboardPair(int start,int which){
        List<Object> entries=keyboardTrace.snapshot();
        if(entries.size()!=start+4||keyboardTrace.dropped()!=0||keyboardObserverFailures!=0)return false;
        for(int i=0;i<4;i++){
            if(!(entries.get(start+i) instanceof Map<?,?> row))return false;
            if(!Integer.valueOf(which).equals(row.get("case"))||!(i%2==0?"activity.key.before":"activity.key.after").equals(row.get("stage"))||
                !Integer.valueOf(i/2).equals(row.get("action"))||!Integer.valueOf(android.view.KeyEvent.KEYCODE_DPAD_DOWN).equals(row.get("keyCode"))||
                !Integer.valueOf(android.view.InputDevice.SOURCE_KEYBOARD).equals(row.get("source"))||!Integer.valueOf(0).equals(row.get("repeat"))||!Boolean.FALSE.equals(row.get("canceled")))return false;
        }
        return true;
    }
    boolean ownedFocusVisible(View view){
        if(view==null||!view.isAttachedToWindow()||!view.isShown()||!view.hasWindowFocus()||!view.isEnabled()||view.getVisibility()!=View.VISIBLE||view.getWindowVisibility()!=View.VISIBLE)return false;
        Rect local=new Rect();if(!view.getLocalVisibleRect(local)||local.isEmpty()||view.getWidth()<=0||view.getHeight()<=0)return false;
        int[] screen=new int[2];view.getLocationOnScreen(screen);double x=screen[0]+local.exactCenterX(),y=screen[1]+local.exactCenterY();
        Map<String,Object> owned=ownedInputGeometry(view,x,y,false);
        return Boolean.TRUE.equals(owned.get("windowOwned"))&&Boolean.TRUE.equals(owned.get("firstOnVisibleToggle"))&&
            FixtureInputBounds.contains(((List<?>)owned.get("ownedVisibleScreen")).stream().mapToInt(v->((Number)v).intValue()).toArray(),x,y);
    }
    static Map<String,Object> focusView(View view){
        if(view==null)return null;
        Map<String,Object> value=viewState(view);
        value.putAll(Json.map("class",view.getClass().getName(),"identity",System.identityHashCode(view),"id",view.getId(),
            "focusable",view.isFocusable(),"focusableInTouchMode",view.isFocusableInTouchMode(),"inTouchMode",view.isInTouchMode(),
            "hasFocus",view.hasFocus(),"visibility",view.getVisibility(),"windowVisibility",view.getWindowVisibility()));
        if(view instanceof android.view.ViewGroup group)value.put("descendantFocusability",group.getDescendantFocusability());
        return value;
    }
    static boolean ancestorFocusBlocked(View view){
        android.view.ViewParent parent=view.getParent();int count=0;
        while(parent instanceof View ancestor){
            if(++count>16)return true;
            if(ancestor instanceof android.view.ViewGroup group&&group.getDescendantFocusability()==android.view.ViewGroup.FOCUS_BLOCK_DESCENDANTS)return true;
            parent=ancestor.getParent();
        }
        return false;
    }
    Map<String,Object> focusState(View toggle,View control){
        java.util.ArrayList<Object> ancestors=new java.util.ArrayList<>();android.view.ViewParent parent=toggle.getParent();int count=0;
        while(parent instanceof View ancestor&&count++<16){ancestors.add(focusView(ancestor));parent=ancestor.getParent();}
        View decor=getWindow().getDecorView(),owner=decor.findFocus(),activityOwner=getCurrentFocus();
        return Json.map("toggle",focusView(toggle),"control",focusView(control),"ancestors",ancestors,"ancestorChainComplete",!(parent instanceof View),
            "ancestorFocusBlocked",ancestorFocusBlocked(toggle),"toggleOwnedVisible",ownedFocusVisible(toggle),"controlOwnedVisible",ownedFocusVisible(control),
            "controlPresent",control!=null&&control.getParent()!=null,"decorFocusOwner",focusView(owner),"activityFocusOwner",focusView(activityOwner),
            "toggleIsFocusOwner",owner==toggle&&activityOwner==toggle,"controlIsFocusOwner",control!=null&&owner==control&&activityOwner==control,
            "geometry",geometry(toggle));
    }

    Map<String,Object> exportTrace(){return Json.map("schema",1,"mode","original-protocol","entries",trace.snapshot(),"dropped",trace.dropped(),
        "observerFailures",observerFailures,"entryLimit",2048,"byteLimit",524288,"listenerConsumes",false,
        "observerPerturbation","Public queries and Map allocation add time on dispatch; no sleep, coordinate or timestamp schedule changes");}
}
