package dev.mixer.android;

import android.Manifest;
import android.animation.ValueAnimator;
import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.Looper;
import android.provider.Settings;
import android.util.Log;
import android.widget.Switch;
import java.lang.reflect.Field;
import java.math.BigInteger;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Objects;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Private native smoke with failure-only readiness diagnostics.
 * Requires a separate private APK with the real JNI/Swift registry, native classes and descriptor
 * asset. No substitute renderer, engine, installed capture or environment is accepted here.
 * This is a narrow smoke test, not native rollback/IME/lifecycle/physical-device acceptance.
 */
@SuppressWarnings("deprecation")
public final class NativeCoordinatorV2IntegrationInstrumentation extends Instrumentation {
    private int checks;
    private String stage = "api-floor";

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
    private void awaitPresentation(String readinessStage, NativeOwnerV2 owner) {
        stage = readinessStage;
        for(int attempt=0;attempt<100;attempt++){
            boolean[] ready={false};onMain(()->ready[0]=owner.hasCommittedPresentation());if(ready[0])return;
            try{Thread.sleep(20);}catch(InterruptedException failure){Thread.currentThread().interrupt();throw new AssertionError(failure);}
            waitForIdleSync();
        }
        throw new AssertionError("actual owner readiness did not publish; stage=" + stage);
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

    private static Object observedField(Object source, String name) {
        try {
            Field field = source.getClass().getDeclaredField(name);
            field.setAccessible(true);
            return field.get(source);
        } catch (ReflectiveOperationException failure) {
            throw new AssertionError("read-only motion observation: " + name, failure);
        }
    }

    private static OwnerLifecycleV2.Snapshot ownerState(NativeOwnerV2 owner) {
        return ((OwnerLifecycleV2) observedField(owner, "core")).snapshot();
    }

    private static long observerGeneration(NativeOwnerV2 owner) {
        return (Long) observedField(observedField(owner, "observer"), "generation");
    }

    private record MotionEvent(boolean main, float scale, long generation,
                               OwnerLifecycleV2.Snapshot owner) {}
    private static final class MotionProbe {
        final ArrayList<MotionEvent> events = new ArrayList<>();
        final NativeEnvironmentPlatformV2.Listener listener;
        boolean added;
        MotionProbe(NativeOwnerV2 owner) {
            listener = NativeEnvironmentPlatformV2.motionListener(() -> {
                // Observation only. Weak listener slots and independent main posts permit
                // this probe to run before invalidation or after the ordinary owner drain.
                if (events.size() >= 16) throw new AssertionError("motion callback bound exceeded");
                events.add(new MotionEvent(Looper.myLooper() == Looper.getMainLooper(),
                    ValueAnimator.getDurationScale(), observerGeneration(owner), ownerState(owner)));
            });
        }
        void add() { added = true; listener.add(); }
        void remove() { if (added) { added = false; listener.remove(); } }
    }

    private void motionWait(String label, java.util.function.BooleanSupplier ready) {
        stage = label;
        for (int attempt = 0; attempt < 300; attempt++) {
            boolean[] value = {false};
            onMain(() -> value[0] = ready.getAsBoolean());
            if (value[0]) return;
            try { Thread.sleep(20); }
            catch (InterruptedException failure) { Thread.currentThread().interrupt(); throw new AssertionError(failure); }
            waitForIdleSync();
        }
        throw new AssertionError("motion condition did not arrive within 300 x 20ms: " + label);
    }

    private void putMotionSetting(NativeCoordinatorV2IntegrationActivity window, String raw) {
        check(Settings.Global.putString(window.getContentResolver(), Settings.Global.ANIMATOR_DURATION_SCALE, raw),
            "owned emulator animator setting write/delete returned true");
    }

    private void verifyMotionDelivery(NativeCoordinatorV2IntegrationActivity window, MotionProbe probe,
                                      float expected, OwnerLifecycleV2.Snapshot before, long generation,
                                      byte[] packet, byte[] bytes, Bundle result, String label) {
        motionWait(label + "-callback-and-drain", () -> !probe.events.isEmpty()
            && Float.compare(ValueAnimator.getDurationScale(), expected) == 0
            && observerGeneration(window.owner) > generation
            && ownerState(window.owner).epoch() > before.epoch()
            && ownerState(window.owner).presentation() != before.presentation()
            && window.owner.hasCommittedPresentation() && !ownerState(window.owner).dirty()
            && ownerState(window.owner).pendingDrain() == null && ownerState(window.owner).operation() == null);
        onMain(() -> {
            MotionEvent delivered = probe.events.get(0);
            check(delivered.main(), "real platform duration-scale callback delivered on main");
            check(Float.compare(delivered.scale(), expected) == 0,
                "real effective getter observed changed/restored animator scale in callback");
            OwnerLifecycleV2.Snapshot after = ownerState(window.owner);
            check(observerGeneration(window.owner) > generation && after.epoch() > before.epoch(),
                "actual Observer generation and owner epoch advanced after Settings mutation");
            check(after.phase() == OwnerLifecycleV2.Phase.LIVE && !after.dirty()
                && after.presentation() != null && after.presentation() != before.presentation()
                && after.pendingDrain() == null && after.operation() == null,
                "real owner drain completed and published a new presentation");
            NativeCoordinatorV2 joined = coordinator(window.owner);
            check(retained(joined) == packet && Arrays.equals(retained(joined), bytes),
                "motion callback refresh retained exact document packet identity and bytes");
            NativeRenderer renderer = (NativeRenderer) observedField(joined, "renderer");
            NativeEnvironmentV2 committed = (NativeEnvironmentV2) observedField(renderer, "v2CommittedEnvironment");
            check(committed.value.accessibility().reduceMotion() == (expected == 0)
                && committed.value.generation().equals(Long.toString(observerGeneration(window.owner))),
                "real committed environment reflects motion and current Observer generation");
            result.putString(label, "callback=" + delivered + "; completed=" + after
                + "; committedGeneration=" + committed.value.generation()
                + "; reduceMotion=" + committed.value.accessibility().reduceMotion()
                + "; exactPacketIdentityAndBytes=true");
        });
    }

    private void exerciseMotionCallback(NativeCoordinatorV2IntegrationActivity window, Bundle result) {
        stage = "motion-original-observation";
        String original = Settings.Global.getString(window.getContentResolver(), Settings.Global.ANIMATOR_DURATION_SCALE);
        float[] scale = {Float.NaN};
        MotionProbe[] first = {null}, restoration = {null};
        OwnerLifecycleV2.Snapshot[] before = {null}, beforeRestore = {null};
        long[] generation = {0}, restoreGeneration = {0};
        byte[][] packet = new byte[2][];
        int[] removedCount = {-1};
        boolean mutated = false;
        boolean adopted = false;
        try {
            onMain(() -> {
                scale[0] = ValueAnimator.getDurationScale();
                check(Float.isFinite(scale[0]) && scale[0] >= 0, "original effective scale is valid");
                NativeEnvironmentPlatformV2.Observed<Float> observed = NativeEnvironmentPlatformV2.snapshot(window, window.root).animator;
                check(observed.status == NativeEnvironmentPlatformV2.Status.KNOWN
                    && Float.compare(observed.value, scale[0]) == 0, "real pair9 snapshot agrees with effective getter");
                first[0] = new MotionProbe(window.owner); first[0].add();
                before[0] = ownerState(window.owner); generation[0] = observerGeneration(window.owner);
                packet[0] = retained(coordinator(window.owner)); packet[1] = packet[0].clone();
            });
            result.putBoolean("motionOriginalRawPresent", original != null);
            result.putString("motionOriginalRaw", original == null ? "<absent>" : original);
            result.putFloat("motionOriginalEffective", scale[0]);
            float changed = scale[0] == 0 ? 1 : 0;
            result.putFloat("motionChangedEffectiveTarget", changed);
            getUiAutomation().adoptShellPermissionIdentity(Manifest.permission.WRITE_SECURE_SETTINGS);
            adopted = true;
            mutated = true; // restore even if the write partially succeeds or verification fails
            putMotionSetting(window, Float.toString(changed));
            verifyMotionDelivery(window, first[0], changed, before[0], generation[0], packet[0], packet[1], result, "motionChanged");
            onMain(() -> first[0].remove());
            result.putBoolean("motionTestListenerRemoved", true);
        } catch (RuntimeException | Error failure) {
            result.putString("motionPrimaryFailureStage", stage);
            result.putString("motionPrimaryFailure", failure.toString());
            throw failure;
        } finally {
            try {
                if (mutated) {
                    try {
                        try {
                            onMain(() -> {
                                if (first[0] != null) {
                                    first[0].remove();
                                    removedCount[0] = first[0].events.size();
                                }
                                restoration[0] = new MotionProbe(window.owner); restoration[0].add();
                                beforeRestore[0] = ownerState(window.owner); restoreGeneration[0] = observerGeneration(window.owner);
                            });
                        } finally {
                            // An absent row may preserve WMS's current effective scale. Restore the
                            // captured effective value before restoring exact raw presence/value.
                            putMotionSetting(window, Float.toString(scale[0]));
                            motionWait("motion-effective-restoration", () -> Float.compare(ValueAnimator.getDurationScale(), scale[0]) == 0);
                            result.putBoolean("motionEffectiveRestoredBeforeRaw", true);
                        }
                        verifyMotionDelivery(window, restoration[0], scale[0], beforeRestore[0], restoreGeneration[0],
                            packet[0], packet[1], result, "motionRestored");
                    } finally {
                        // Always restore the raw row, including after callback/owner verification fails.
                        putMotionSetting(window, original);
                        check(Objects.equals(original, Settings.Global.getString(window.getContentResolver(),
                            Settings.Global.ANIMATOR_DURATION_SCALE)), "exact original raw setting presence/value restored");
                        result.putBoolean("motionRawRestored", true);
                        motionWait("motion-effective-after-raw-restoration", () -> Float.compare(ValueAnimator.getDurationScale(), scale[0]) == 0);
                        result.putBoolean("motionEffectiveRestored", true);
                    }
                    for (int flush = 0; flush < 25; flush++) {
                        try { Thread.sleep(20); }
                        catch (InterruptedException failure) { Thread.currentThread().interrupt(); throw new AssertionError(failure); }
                        waitForIdleSync();
                        onMain(() -> {
                            check(first[0].events.size() == removedCount[0],
                                "removed real listener stays silent through restoration delivery and main queue flush");
                            check(Float.compare(ValueAnimator.getDurationScale(), scale[0]) == 0,
                                "effective restoration stays exact after raw restoration");
                            check(Objects.equals(original, Settings.Global.getString(window.getContentResolver(),
                                Settings.Global.ANIMATOR_DURATION_SCALE)), "raw restoration stays exact");
                        });
                    }
                    result.putBoolean("motionNoCallbackAfterRemove", true);
                    result.putInt("motionRemovalQuietFlushes", 25);
                    result.putInt("motionRemovedListenerCallbackCount", removedCount[0]);
                }
            } finally {
                try {
                    onMain(() -> {
                        try { if (first[0] != null) first[0].remove(); }
                        finally { if (restoration[0] != null) restoration[0].remove(); }
                    });
                    result.putBoolean("motionAllTestHandlesClosed", true);
                } finally {
                    if (adopted) getUiAutomation().dropShellPermissionIdentity();
                }
            }
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
            stage = "activity-startup";
            Intent intent = new Intent(getTargetContext(), NativeCoordinatorV2IntegrationActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            activity = (NativeCoordinatorV2IntegrationActivity) startActivitySync(intent);
            waitForIdleSync();
            NativeCoordinatorV2IntegrationActivity window = activity;
            awaitPresentation("initial-presentation", window.owner);
            stage = "initial-packet-and-pause";
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
            waitForIdleSync();awaitPresentation("post-pause-presentation", window.owner);
            stage = "owner-resume";
            onMain(() -> {
                NativeCoordinatorV2 joined=coordinator(window.owner);
                window.owner.onResume();
            });
            waitForIdleSync();awaitPresentation("post-resume-presentation", window.owner);
            int checksBeforeMotion = checks;
            exerciseMotionCallback(window, result);
            int motionChecks = checks - checksBeforeMotion;
            result.putInt("motionChecks", motionChecks);
            stage = "runtime-toggle-oracle";
            onMain(() -> {
                NativeCoordinatorV2 joined=coordinator(window.owner);
                byte[] initial=initialHolder[0];UiPacket initialPacket=UiPacket.decode(initial);
                check(retained(joined) == initial, "environment-only retains exact packet reference");
                check(Arrays.equals(retained(joined), initialHolder[1]), "environment-only exact bytes");
                Switch toggle = window.root.findViewWithTag("mixer.task.1");
                check(toggle != null && toggle.isAttachedToWindow() && toggle.isShown()
                    && toggle.isEnabled() && toggle.hasWindowFocus(), "actual native Switch is eligible for input");
                boolean previous = toggle.isChecked();
                result.putBoolean("togglePerformClickReturn", toggle.performClick());
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
            result.putInt("originalSmokeChecks", checks - motionChecks);
            result.putString("scope", "PAIR9-MOTION-CALLBACK-NATIVE API37 arm64 plus actual JNI/Swift/native smoke; no API28/32/33 or GA acceptance");
            result.putInt("checks", checks);
            resultCode = Activity.RESULT_OK;
        } catch (RuntimeException | Error failure) {
            result.putString("failure", failure.toString());
            result.putString("failureStage", stage);
            result.putString("failureTrace", NativeCoordinatorV2IntegrationActivity.trace(failure));
            Log.e("MixerReadinessDiagnostic", "instrumentation stage=" + stage, failure);
            if (activity != null) {
                NativeCoordinatorV2IntegrationActivity window = activity;
                try {
                    onMain(() -> result.putString("failureDiagnostics", window.failureDiagnostics()));
                    Log.e("MixerReadinessDiagnostic", result.getString("failureDiagnostics"));
                } catch (RuntimeException | Error observationFailure) {
                    result.putString("diagnosticFailureTrace", NativeCoordinatorV2IntegrationActivity.trace(observationFailure));
                    Log.e("MixerReadinessDiagnostic", "failure observation", observationFailure);
                }
            }
        } finally {
            if (activity != null) {
                NativeCoordinatorV2IntegrationActivity window = activity;
                try {
                    onMain(() -> {
                        try {
                            if (window.owner != null) {
                                NativeEnvironmentV2.Observer observer = (NativeEnvironmentV2.Observer) observedField(window.owner, "observer");
                                window.owner.close();
                                if (observer != null) {
                                    boolean returned = observer.cleanupLedger().state(7) == NativeEnvironmentV2.Observer.RETURNED
                                        && observer.cleanupLedger().failure(7) == null;
                                    result.putBoolean("motionOwnerListenerRemoved", returned);
                                    check(returned, "actual owner motion listener removal returned without failure");
                                }
                            }
                        } finally {
                            window.finish();
                        }
                    });
                } catch (RuntimeException | Error failure) {
                    result.putString("cleanupFailure", failure.toString());
                    result.putString("cleanupFailureTrace", NativeCoordinatorV2IntegrationActivity.trace(failure));
                    Log.e("MixerReadinessDiagnostic", "test cleanup", failure);
                    resultCode = Activity.RESULT_CANCELED;
                }
            }
            finish(resultCode, result);
        }
    }
}
