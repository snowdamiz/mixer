package dev.mixer.android;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.widget.Switch;
import java.lang.reflect.Field;
import java.math.BigInteger;
import java.util.Arrays;
import java.util.concurrent.atomic.AtomicReference;

/**
 * FUTURE NATIVE TEST ONLY, compiled but NOT RUN during the computer-use/native-runtime pause.
 * Requires a separate private APK with the real JNI/Swift registry, native classes and descriptor
 * asset. No substitute renderer, engine, installed capture or environment is accepted here.
 * This is a narrow smoke test, not native rollback/IME/lifecycle/physical-device acceptance.
 */
@SuppressWarnings("deprecation")
public final class NativeCoordinatorV2IntegrationInstrumentation extends Instrumentation {
    private int checks;

    @Override public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        start();
    }

    private void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
        checks++;
    }

    private static NativeCoordinatorV2 coordinator(NativeOwnerV2 owner) {
        try {Field field=NativeOwnerV2.class.getDeclaredField("coordinator");field.setAccessible(true);return (NativeCoordinatorV2)field.get(owner);}
        catch(ReflectiveOperationException failure){throw new AssertionError(failure);}
    }
    private void awaitPresentation(NativeOwnerV2 owner) {
        for(int attempt=0;attempt<100;attempt++){
            boolean[] ready={false};onMain(()->ready[0]=owner.hasCommittedPresentation());if(ready[0])return;
            try{Thread.sleep(20);}catch(InterruptedException failure){Thread.currentThread().interrupt();throw new AssertionError(failure);}
            waitForIdleSync();
        }
        throw new AssertionError("actual owner readiness did not publish");
    }
    private static byte[] retained(NativeCoordinatorV2 coordinator) {
        try {
            Field field = NativeCoordinatorV2.class.getDeclaredField("committedPacket");
            field.setAccessible(true);
            return (byte[]) field.get(coordinator);
        } catch (ReflectiveOperationException failure) {
            throw new AssertionError("test-only observation of exact retained packet", failure);
        }
    }

    private void onMain(Runnable operation) {
        AtomicReference<Throwable> failure = new AtomicReference<>();
        runOnMainSync(() -> {
            try { operation.run(); }
            catch (RuntimeException | Error rejected) { failure.set(rejected); }
        });
        if (failure.get() instanceof RuntimeException rejected) throw rejected;
        if (failure.get() instanceof Error rejected) throw rejected;
    }

    @Override public void onStart() {
        Bundle result = new Bundle();
        NativeCoordinatorV2IntegrationActivity activity = null;
        int resultCode = Activity.RESULT_CANCELED;
        try {
            check(Build.VERSION.SDK_INT >= 36, "private V2 runtime floor is API36");
            Intent intent = new Intent(getTargetContext(), NativeCoordinatorV2IntegrationActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            activity = (NativeCoordinatorV2IntegrationActivity) startActivitySync(intent);
            waitForIdleSync();
            NativeCoordinatorV2IntegrationActivity window = activity;
            awaitPresentation(window.owner);
            byte[][] initialHolder=new byte[2][];
            onMain(() -> {
                check(window.root.isAttachedToWindow() && window.root.getWidth() > 0
                    && window.root.getHeight() > 0 && window.root.hasWindowFocus(), "actual attached focused window");
                NativeCoordinatorV2 joined=coordinator(window.owner);
                check(window.owner.hasCommittedPresentation(), "ordinary JNI/Swift/native initial commit");
                byte[] initial = retained(joined);initialHolder[0]=initial;initialHolder[1]=initial.clone();
                UiPacket initialPacket = UiPacket.decode(initial);
                check(initialPacket.nodes.containsKey("task.1"), "actual ordinary Swift checklist packet");
                // Refresh is driven through the owner and its real queued drain below.
                window.owner.onPause();
            });
            waitForIdleSync();awaitPresentation(window.owner);
            onMain(() -> {
                NativeCoordinatorV2 joined=coordinator(window.owner);
                window.owner.onResume();
            });
            waitForIdleSync();awaitPresentation(window.owner);
            onMain(() -> {
                NativeCoordinatorV2 joined=coordinator(window.owner);
                byte[] initial=initialHolder[0];UiPacket initialPacket=UiPacket.decode(initial);
                check(retained(joined) == initial, "environment-only retains exact packet reference");
                check(Arrays.equals(retained(joined), initialHolder[1]), "environment-only exact bytes");
                Switch toggle = window.root.findViewWithTag("mixer.task.1");
                check(toggle != null && toggle.isAttachedToWindow() && toggle.isShown()
                    && toggle.isEnabled() && toggle.hasWindowFocus(), "actual native Switch is eligible for input");
                boolean previous = toggle.isChecked();
                check(toggle.performClick(), "actual native click accepted");
                UiPacket next = UiPacket.decode(retained(joined));
                check(new BigInteger(next.revision).compareTo(new BigInteger(initialPacket.revision)) > 0,
                    "native input advances the ordinary Swift document revision");
                check(next.nodes.get("task.1").flag("value", previous) != previous,
                    "Swift committed the toggle input");
                check(toggle.isChecked() != previous && window.owner.hasCommittedPresentation(),
                    "actual native toggle agrees with committed Swift packet");
                window.owner.onPause();
                check(!window.owner.cleanupLedger().coreCompletionUnreported(),"owner retained exact core completion");
            });
            result.putString("scope", "actual JNI/Swift/native smoke test only; no complete native/IME/physical/GA acceptance");
            result.putInt("checks", checks);
            resultCode = Activity.RESULT_OK;
        } catch (RuntimeException | Error failure) {
            result.putString("failure", failure.toString());
        } finally {
            if (activity != null) {
                NativeCoordinatorV2IntegrationActivity window = activity;
                try {
                    onMain(() -> {
                        try {
                            if (window.owner != null) window.owner.close();
                        } finally {
                            window.finish();
                        }
                    });
                } catch (RuntimeException | Error failure) {
                    result.putString("cleanupFailure", failure.toString());
                    resultCode = Activity.RESULT_CANCELED;
                }
            }
            finish(resultCode, result);
        }
    }
}
