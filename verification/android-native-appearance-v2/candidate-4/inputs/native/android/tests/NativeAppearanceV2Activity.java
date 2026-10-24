package dev.mixer.android;

import android.app.Activity;
import android.os.Bundle;
import android.widget.FrameLayout;

/** Repository-only window for the actual private renderer. No engine/JNI integration. */
@SuppressWarnings("deprecation")
public final class NativeAppearanceV2Activity extends Activity {
    FrameLayout root;
    @Override public void onCreate(Bundle state){
        android.content.res.Configuration configuration=new android.content.res.Configuration();
        if(getIntent().hasExtra("fontScale"))configuration.fontScale=getIntent().getFloatExtra("fontScale",1);
        if(getIntent().getBooleanExtra("dark",false))configuration.uiMode=android.content.res.Configuration.UI_MODE_NIGHT_YES;
        if(getIntent().getBooleanExtra("rtl",false)){configuration.setLocale(java.util.Locale.forLanguageTag("ar"));configuration.setLayoutDirection(java.util.Locale.forLanguageTag("ar"));}
        applyOverrideConfiguration(configuration);super.onCreate(state);getWindow().setDecorFitsSystemWindows(false);
        root=new FrameLayout(this);setContentView(root);}
}
