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
        scroll=new ObservedScroll();content=new Parent();scroll.addView(content,new ScrollView.LayoutParams(-1,6000));root.addView(scroll,new FrameLayout.LayoutParams(-1,-1));
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
    Map<String,Object> exportTrace(){return Json.map("schema",1,"mode","original-protocol","entries",trace.snapshot(),"dropped",trace.dropped(),
        "observerFailures",observerFailures,"entryLimit",2048,"byteLimit",524288,"listenerConsumes",false,
        "observerPerturbation","Public queries and Map allocation add time on dispatch; no sleep, coordinate or timestamp schedule changes");}
}
