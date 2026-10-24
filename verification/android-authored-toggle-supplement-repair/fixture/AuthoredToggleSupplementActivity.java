package dev.mixer.android;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.ScrollView;

/** Private component owner; native ScrollView owns parent arbitration. */
@SuppressWarnings("deprecation")
public final class AuthoredToggleSupplementActivity extends Activity {
    FrameLayout root;ScrollView scroll;Parent content;boolean destroyed;
    static final class Parent extends FrameLayout {
        int acquired,released,unownedRelease;boolean disallowed;
        Parent(android.content.Context context){super(context);}
        @Override public void requestDisallowInterceptTouchEvent(boolean value){
            if(value){acquired++;disallowed=true;}else{released++;if(!disallowed)unownedRelease++;disallowed=false;}
            super.requestDisallowInterceptTouchEvent(value);
        }
    }
    @Override public void onCreate(Bundle state){
        super.onCreate(state);getWindow().setDecorFitsSystemWindows(false);root=new FrameLayout(this);setContentView(root);
        scroll=new ScrollView(this);content=new Parent(this);scroll.addView(content,new ScrollView.LayoutParams(-1,6000));root.addView(scroll,new FrameLayout.LayoutParams(-1,-1));
    }
    @Override public void onDestroy(){destroyed=true;super.onDestroy();}
    void place(View view,int top){FrameLayout.LayoutParams lp=new FrameLayout.LayoutParams(1000,132);lp.leftMargin=60;lp.topMargin=top;content.addView(view,lp);}
}
