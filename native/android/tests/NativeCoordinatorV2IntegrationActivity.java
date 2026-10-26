package dev.mixer.android;

import android.app.Activity;
import android.os.Bundle;
import android.widget.FrameLayout;

/** FUTURE NATIVE TEST ONLY. Not launched while native runtime is paused. */
@SuppressWarnings("deprecation")
public final class NativeCoordinatorV2IntegrationActivity extends Activity {
    FrameLayout root;
    NativeOwnerV2 owner;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setDecorFitsSystemWindows(false);
        root=new FrameLayout(this);setContentView(root);
        owner=new NativeOwnerV2(this,root);owner.start();
    }
    @Override public void onResume(){super.onResume();if(owner!=null)owner.onResume();}
    @Override public void onPause(){try{if(owner!=null)owner.onPause();}finally{super.onPause();}}
    @Override public void onStop(){try{if(owner!=null)owner.onStop();}finally{super.onStop();}}
    @Override public void onDestroy(){try{if(owner!=null)owner.close();}finally{super.onDestroy();}}
}
