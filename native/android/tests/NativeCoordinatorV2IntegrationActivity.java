package dev.mixer.android;

import android.app.Activity;
import android.os.Bundle;
import android.widget.FrameLayout;
import android.util.Log;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.lang.reflect.Field;

/** Private native smoke activity; diagnostics observe failures before test cleanup. */
@SuppressWarnings("deprecation")
public final class NativeCoordinatorV2IntegrationActivity extends Activity {
    FrameLayout root;
    NativeOwnerV2 owner;
    String lifecycleStage = "constructed";
    @Override public void onCreate(Bundle state) {
        lifecycleStage = "onCreate";
        try {
        super.onCreate(state);
        getWindow().setDecorFitsSystemWindows(false);
        root=new FrameLayout(this);setContentView(root);
        owner=new NativeOwnerV2(this,root);owner.start();
        lifecycleStage = "onCreate.returned";
        } catch (RuntimeException | Error failure) {
            Log.e("MixerReadinessDiagnostic", "activity stage=" + lifecycleStage, failure);
            throw failure;
        }
    }
    @Override public void onResume(){lifecycleStage="onResume";super.onResume();if(owner!=null)owner.onResume();lifecycleStage="onResume.returned";}
    @Override public void onPause(){try{if(owner!=null)owner.onPause();}finally{super.onPause();}}
    @Override public void onStop(){try{if(owner!=null)owner.onStop();}finally{super.onStop();}}
    @Override public void onDestroy(){try{if(owner!=null)owner.close();}finally{super.onDestroy();}}

    private static Object read(Object object, String name) throws ReflectiveOperationException {
        Field field = object.getClass().getDeclaredField(name);
        field.setAccessible(true);
        return field.get(object);
    }

    private static void fields(StringBuilder out, String label, Object object, String... names)
            throws ReflectiveOperationException {
        out.append(label).append('=').append(object).append('\n');
        if (object == null) return;
        for (String name : names) {
            Object value = read(object, name);
            out.append(label).append('.').append(name).append('=').append(value).append('\n');
            if (value instanceof Throwable failure) out.append(trace(failure));
        }
    }

    static String trace(Throwable failure) {
        StringWriter text = new StringWriter();
        failure.printStackTrace(new PrintWriter(text));
        return text.toString();
    }

    String failureDiagnostics() {
        StringBuilder out = new StringBuilder("lifecycleStage=").append(lifecycleStage).append('\n');
        try {
            out.append("activity.destroyed=").append(isDestroyed()).append(" finishing=").append(isFinishing())
                .append(" window=").append(getWindow()).append('\n');
            if (root != null) out.append("root.attached=").append(root.isAttachedToWindow())
                .append(" width=").append(root.getWidth()).append(" height=").append(root.getHeight())
                .append(" focused=").append(root.hasWindowFocus()).append(" shown=").append(root.isShown())
                .append(" token=").append(root.getWindowToken()).append(" insets=").append(root.getRootWindowInsets()).append('\n');
            fields(out,"owner",owner,"started","registering","terminalProcessed","focusKnown","lastFocus",
                "emergency","effectDepth","window","queued","activeOperation","pendingCloseResource","pendingCloseToken");
            if (owner != null) {
                out.append("owner.hasCommittedPresentation=").append(owner.hasCommittedPresentation()).append('\n');
                OwnerLifecycleV2 core = (OwnerLifecycleV2) read(owner,"core");
                out.append("core.snapshot=").append(core.snapshot()).append('\n');
                fields(out,"core",core,"facts","primaryFailure","cancelFailure","unregisterFailure","closeFailure");
                fields(out,"fence",read(owner,"fence"),"terminal","drawAllowed","inputAllowed","commitFinish",
                    "rendererReportActive","sealSerial","operation","presentation");
                fields(out,"observer",read(owner,"observer"),"initialized","retired");
                fields(out,"owner.cleanupLedger",owner.cleanupLedger(),"cause","rendererCause","primary","firstFatal",
                    "handler","input","unregister","coordinator","coreCompletionUnreported",
                    "handlerFailure","inputFailure","unregisterFailure","coordinatorFailure");
                for (String name : new String[]{"opening","coordinator","pendingCloseResource"}) {
                    Object joined = read(owner,name);
                    fields(out,name,joined,"session","active","retired","disposed","cancellation","operation","committedPacket");
                    if (joined != null) fields(out,name+".cleanupLedger",((NativeCoordinatorV2)joined).cleanupLedger(),
                        "primary","firstFatal","renderer","engine","abort","rollback","discard",
                        "rendererFailure","engineFailure","abortFailure","rollbackFailure","discardFailure");
                }
            }
        } catch (ReflectiveOperationException | RuntimeException | Error failure) {
            out.append("diagnosticObservationFailure=").append(trace(failure));
        }
        return out.toString();
    }
}
