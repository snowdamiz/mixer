package dev.mixer.android;
import android.app.Activity;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.view.WindowInsetsController;
import android.widget.FrameLayout;
import android.widget.Toast;
/** Activity owns native lifecycle only. Swift owns the example model and UI tree. */
public final class MixerActivity extends Activity {
    long session;NativeRenderer renderer;private FrameLayout root;
    @SuppressWarnings("deprecation")
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        root = new FrameLayout(this);
        root.setBackgroundColor(0xfffafafa);
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                    insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets;
        });
        setContentView(root);

        // Installing content creates the decor required by PhoneWindow's controller.
        if (Build.VERSION.SDK_INT >= 30) {
            int lightBars = WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                    | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS;
            getWindow().getInsetsController().setSystemBarsAppearance(lightBars, lightBars);
        } else {
            getWindow().getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        }

        session = NativeBridge.create();
        renderer = new NativeRenderer(this, this::event);
        render(NativeBridge.exchange(session, 0, null));
    }
    private void render(byte[] bytes){UiPacket next=UiPacket.decode(bytes);View content=renderer.apply(next);if(content.getParent()!=root){root.removeAllViews();root.addView(content,new FrameLayout.LayoutParams(-1,-1));}}
    private void event(byte[] envelope){try{render(NativeBridge.exchange(session,1,envelope));}catch(RuntimeException error){Log.e("MixerAndroid","Input rejected",error);Toast.makeText(this,"Couldn't apply that edit",Toast.LENGTH_SHORT).show();}}
    @Override public void onDestroy(){if(session!=0){NativeBridge.destroy(session);session=0;}super.onDestroy();}
}
