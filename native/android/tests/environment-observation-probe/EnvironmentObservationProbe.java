package dev.mixer.android;

import android.app.Activity;
import android.app.Instrumentation;
import android.app.UiAutomation;
import android.content.Intent;
import android.content.res.Configuration;
import android.os.Build;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.os.SystemClock;
import android.view.Window;
import android.widget.FrameLayout;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.FutureTask;
import java.util.function.Predicate;
import java.util.function.Supplier;
import static dev.mixer.android.NativeEnvironmentPlatformV2.Status.*;

/** Observation-only test Activity and instrumentation for disposable emulators. */
@SuppressWarnings("deprecation")
public final class EnvironmentObservationProbe extends Instrumentation {
    private static final int SDK = Build.VERSION.SDK_INT;
    private static final long WAIT_MS = 5000;
    private final StringBuilder checks = new StringBuilder();
    private final StringBuilder transitions = new StringBuilder();
    private final StringBuilder restorations = new StringBuilder();

    public static final class ProbeActivity extends Activity {
        FrameLayout root;
        int configurationCallbacks;
        String lastConfigurationCallback = "none";

        @Override protected void onCreate(Bundle state) {
            super.onCreate(state);
            if (SDK >= 30) Api30.edgeToEdge(getWindow());
            root = new FrameLayout(this);
            setContentView(root);
        }

        @Override public void onConfigurationChanged(Configuration configuration) {
            configurationCallbacks++;
            lastConfigurationCallback = describeConfiguration(configuration);
            super.onConfigurationChanged(configuration);
        }
    }

    private static final class Api30 {
        static void edgeToEdge(Window window) {
            window.setDecorFitsSystemWindows(false);
        }
    }

    private static final class Api31 {
        static int fontWeightAdjustment(Configuration configuration) {
            return configuration.fontWeightAdjustment;
        }
    }

    private static String describeConfiguration(Configuration configuration) {
        return "fontScale=" + configuration.fontScale + ", fontWeightAdjustment="
            + (SDK >= 31 ? Integer.toString(Api31.fontWeightAdjustment(configuration)) : "unavailable");
    }

    @Override public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        start();
    }

    @Override public void onStart() {
        Bundle report = new Bundle();
        report.putString("api", Integer.toString(SDK));
        Throwable failure = null;
        ProbeActivity activity = null;
        try {
            require(SDK == 28 || SDK == 35 || SDK == 36 || SDK == 37, "unexpected probe API " + SDK);
            activity = (ProbeActivity) startActivitySync(new Intent(getTargetContext(), ProbeActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            exercise(activity);
        } catch (Throwable error) {
            failure = error;
        } finally {
            if (activity != null) {
                try {
                    ProbeActivity ownedActivity = activity;
                    onMain(() -> { ownedActivity.finish(); return null; });
                } catch (Throwable cleanup) {
                    if (failure == null) failure = cleanup;
                    else if (cleanup != failure) failure.addSuppressed(cleanup);
                }
            }
        }
        report.putString("checks", checks.toString());
        report.putString("transition_observations", transitions.toString());
        report.putString("settings_restore", restorations.toString());
        report.putString("status", failure == null ? "passed" : "failed");
        if (failure != null) report.putString("failure", android.util.Log.getStackTraceString(failure));
        finish(failure == null ? Activity.RESULT_OK : Activity.RESULT_CANCELED, report);
    }

    private void exercise(ProbeActivity activity) throws Exception {
        await("attached, laid-out root", () -> activity.root.isAttachedToWindow()
            && activity.root.getWidth() > 0 && activity.root.getHeight() > 0
            && (SDK < 30 || activity.root.getRootWindowInsets() != null));
        UiAutomation shell = getUiAutomation(UiAutomation.FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES);
        String settings = settingsCommand(shell);
        try (Setting font = new Setting(shell, settings, "system", "font_scale");
             Setting weight = SDK < 31 ? null : new Setting(shell, settings, "secure", "font_weight_adjustment");
             Setting motion = SDK < 33 ? null : new Setting(shell, settings, "global", "animator_duration_scale");
             Setting contrast = SDK < 34 ? null : new Setting(shell, settings, "secure", "contrast_level");
             Setting highText = SDK < 36 ? null : new Setting(shell, settings, "secure", "high_text_contrast_enabled")) {
            Watch watch = new Watch(activity);
            int profile;
            try (watch) {
                await("startup policy", () -> {
                    var snapshot = NativeEnvironmentPlatformV2.snapshotForCompose(activity, activity.root);
                    var value = watch.observer.readForCompose();
                    require(snapshot.insets.status == (SDK < 30 ? UNAVAILABLE_SEMANTICS : KNOWN), "inset observation");
                    require(weight == null ? snapshot.fontAdjustment.status == UNAVAILABLE_API
                        : snapshot.fontAdjustment.status == KNOWN || snapshot.fontAdjustment.status == UNSET_PREFERENCE,
                        "weight observation");
                    require(snapshot.animator.status == (motion == null ? UNAVAILABLE_API : KNOWN), "motion observation");
                    require(snapshot.contrast.status == (contrast == null ? UNAVAILABLE_API : KNOWN), "contrast observation");
                    require(snapshot.highContrast.status == (highText == null ? UNAVAILABLE_API : KNOWN), "high-text observation");
                    require(value.frameworkFitsInsets() == (SDK < 30), "inset policy");
                    return true;
                });

                font.write("1.0");
                if (weight != null) weight.write("0");
                if (motion != null) motion.write("1");
                if (contrast != null) contrast.write("0");
                if (highText != null) highText.write("0");
                await("baseline settings observed", () -> {
                    var value = watch.observer.readForCompose();
                    return activity.getResources().getConfiguration().fontScale == 1.0f
                        && value.weightDelta() == 0 && !value.value().accessibility().increasedContrast()
                        && value.value().accessibility().reduceMotion() == (motion == null);
                });
                profile = onMain(() -> watch.observer.readForCompose().value().profile().ordinal());
                transition(watch, font, "1.3", v -> v.value().profile().ordinal() > profile);
                if (weight != null) {
                    transition(watch, weight, "300", v -> v.weightDelta() == 300 && v.value().accessibility().boldText());
                }
                if (motion != null) {
                    transition(watch, motion, "0", v -> v.value().accessibility().reduceMotion());
                }
                if (contrast != null) {
                    transition(watch, contrast, "1", v -> v.value().accessibility().increasedContrast());
                    transition(watch, contrast, "0", v -> !v.value().accessibility().increasedContrast());
                }
                if (highText != null) {
                    transition(watch, highText, "1", v -> v.value().accessibility().increasedContrast());
                }
            }
            int retiredCount = onMain(() -> watch.invalidations);
            try (Watch replacement = new Watch(activity)) {
                transition(replacement, font, "1.0", v -> v.value().profile().ordinal() == profile);
                if (weight != null) {
                    transition(replacement, weight, "0", v -> v.weightDelta() == 0 && !v.value().accessibility().boldText());
                }
                if (motion != null) {
                    transition(replacement, motion, "1", v -> !v.value().accessibility().reduceMotion());
                }
                if (highText != null) {
                    transition(replacement, highText, "0", v -> !v.value().accessibility().increasedContrast());
                }
                if (contrast != null) {
                    transition(replacement, contrast, "1", v -> v.value().accessibility().increasedContrast());
                }
            }
            require(onMain(() -> watch.invalidations) == retiredCount, "retired observer reported a change");
            checks.append("cleanup and replacement; ");
        }
        checks.append("settings restored");
    }

    private final class Watch implements AutoCloseable {
        final ProbeActivity activity;
        final NativeEnvironmentV2.Observer observer;
        int invalidations;
        int configurationInvalidations;
        String lastInvalidationSource = "none";
        private boolean closed;

        Watch(ProbeActivity activity) {
            this.activity = activity;
            observer = onMain(() -> {
                var source = NativeEnvironmentV2.Observer.forCompose(activity, activity.root,
                    (from, change, cause, primary, fatal) -> {
                        if (change == NativeEnvironmentV2.Change.INVALIDATED) recordInvalidation();
                    });
                source.register();
                try {
                    checkLedger(source, NativeEnvironmentV2.Observer.POSSIBLY_OWNED);
                } catch (AssertionError failure) {
                    try {
                        source.close();
                    } catch (RuntimeException | Error cleanup) {
                        if (failure != cleanup) failure.addSuppressed(cleanup);
                    }
                    throw failure;
                }
                return source;
            });
        }

        private void recordInvalidation() {
            invalidations++;
            lastInvalidationSource = "other observer listener";
            // Observe the existing callback path without wrapping or replacing its registration.
            for (StackTraceElement frame : Thread.currentThread().getStackTrace()) {
                if (frame.getClassName().equals(NativeEnvironmentV2.Observer.class.getName())
                    && frame.getMethodName().equals("onConfigurationChanged")) {
                    configurationInvalidations++;
                    lastInvalidationSource = "Observer.onConfigurationChanged";
                    break;
                }
            }
        }

        private TransitionState transitionState() {
            return new TransitionState(invalidations,
                "activityResources={" + describeConfiguration(activity.getResources().getConfiguration()) + "}"
                    + ", activityConfigurationCallbacks=" + activity.configurationCallbacks
                    + ", lastActivityConfiguration={" + activity.lastConfigurationCallback + "}"
                    + ", observerInvalidations=" + invalidations
                    + ", observerConfigurationInvalidations=" + configurationInvalidations
                    + ", lastObserverInvalidationSource=" + lastInvalidationSource);
        }

        @Override public void close() {
            if (closed) return;
            closed = true;
            onMain(() -> {
                observer.close();
                checkLedger(observer, NativeEnvironmentV2.Observer.RETURNED);
                return null;
            });
        }

        private void checkLedger(NativeEnvironmentV2.Observer source, int expected) {
            int[] since = {28, 28, 28, 28, 30, 34, 36, 33};
            for (int slot = 0; slot < since.length; slot++) {
                int state = SDK >= since[slot] ? expected : NativeEnvironmentV2.Observer.UNATTEMPTED;
                require(source.cleanupLedger().state(slot) == state, "listener slot " + slot + " state");
            }
        }
    }

    private record TransitionState(int invalidations, String details) {}

    private void transition(Watch watch, Setting setting, String next,
                            Predicate<NativeEnvironmentV2.ComposeEnvironment> predicate) throws Exception {
        String label = setting.key + "=" + next;
        String beforeSetting = setting.read();
        TransitionState before = onMain(watch::transitionState);
        String beforeDetails = "settingsBefore=[" + beforeSetting + "], before={" + before.details() + "}";
        require(!beforeSetting.equals(next), "setting already equals target for " + label + ", " + beforeDetails);
        setting.write(next);
        boolean observed = poll(() -> watch.invalidations > before.invalidations()
            && predicate.test(watch.observer.readForCompose()));
        String afterDetails = onMain(() -> {
            String state = "after={" + watch.transitionState().details() + "}";
            return observed ? state : state + ", " + describeTimeoutEnvironment(watch, predicate);
        });
        String details = label + ", " + beforeDetails + ", " + afterDetails;
        if (!observed) {
            AssertionError timeout;
            try {
                timeout = new AssertionError("timed out observing " + details
                    + ", settingsAtTimeout=[" + setting.read() + "]");
            } catch (IOException | AssertionError readFailure) {
                timeout = new AssertionError("timed out observing " + details + ", settingsAtTimeout=read failed");
                timeout.addSuppressed(readFailure);
            }
            throw timeout;
        }
        transitions.append(details).append('\n');
        checks.append(label).append("; ");
    }

    private static String describeTimeoutEnvironment(Watch watch,
            Predicate<NativeEnvironmentV2.ComposeEnvironment> predicate) {
        try {
            var value = watch.observer.readForCompose();
            return "composeAtTimeout={profile=" + value.value().profile()
                + ", weightDelta=" + value.weightDelta() + ", accessibility=" + value.value().accessibility()
                + ", predicateMatches=" + predicate.test(value) + "}";
        } catch (RuntimeException | AssertionError failure) {
            return "composeAtTimeout=read failed [" + failure + "]";
        }
    }

    private void await(String label, Supplier<Boolean> condition) {
        require(poll(condition), "timed out observing " + label);
        checks.append(label).append("; ");
    }

    private boolean poll(Supplier<Boolean> condition) {
        long deadline = SystemClock.uptimeMillis() + WAIT_MS;
        do {
            if (onMain(condition)) return true;
            SystemClock.sleep(50);
        } while (SystemClock.uptimeMillis() < deadline);
        return false;
    }

    private <T> T onMain(Supplier<T> action) {
        FutureTask<T> job = new FutureTask<>(action::get);
        runOnMainSync(job);
        try {
            return job.get();
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("main-thread observation interrupted", interrupted);
        } catch (ExecutionException failed) {
            Throwable cause = failed.getCause();
            if (cause instanceof Error error) throw error;
            throw (RuntimeException) cause;
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static String settingsCommand(UiAutomation shell) throws IOException {
        if (SDK != 28) return "settings --user current";
        // Android 9 rejects --user on delete. Unqualified commands target the system user.
        String user = shellOutput(shell, "cmd activity get-current-user");
        require(user.equals("0"), "API 28 probe requires foreground user 0, got [" + user + "]");
        return "settings";
    }

    private final class Setting implements AutoCloseable {
        private final UiAutomation shell;
        private final String settings, namespace, key, original;
        private boolean changed;

        Setting(UiAutomation shell, String settings, String namespace, String key) throws IOException {
            this.shell = shell;
            this.settings = settings;
            this.namespace = namespace;
            this.key = key;
            original = read();
            require(original.equals("null") || original.matches("[-+0-9.Ee]+"),
                command("get") + " returned unexpected value [" + original + "]");
        }

        void write(String value) throws IOException {
            changed = true;
            mutate(value, false);
        }

        @Override public void close() throws IOException {
            if (changed) mutate(original, true);
        }

        private void mutate(String expected, boolean restoring) throws IOException {
            boolean delete = expected.equals("null");
            String mutation = delete ? command("delete") : command("put") + " " + expected;
            String stdout = shellOutput(shell, mutation);
            String actual = read();
            String result = mutation + " stdout=[" + stdout + "], expected=[" + expected + "], readback=[" + actual + "]";
            boolean acknowledged = delete ? stdout.equals("Deleted 1 rows") || stdout.equals("Deleted 0 rows")
                : stdout.isEmpty();
            require(acknowledged && actual.equals(expected), (restoring ? "restore " : "write ") + result);
            if (restoring) restorations.append(result).append("; ");
        }

        private String read() throws IOException {
            return shellOutput(shell, command("get"));
        }

        private String command(String verb) {
            return settings + " " + verb + " " + namespace + " " + key;
        }
    }

    private static String shellOutput(UiAutomation shell, String command) throws IOException {
        ParcelFileDescriptor descriptor = shell.executeShellCommand(command);
        try (InputStream in = new ParcelFileDescriptor.AutoCloseInputStream(descriptor)) {
            byte[] result = new byte[1024];
            int length = 0;
            int received;
            while (length < result.length && (received = in.read(result, length, result.length - length)) >= 0) {
                length += received;
            }
            require(length < result.length, "oversized stdout from " + command);
            String stdout = new String(result, 0, length, StandardCharsets.UTF_8);
            return stdout.endsWith("\n") ? stdout.substring(0, stdout.length() - 1) : stdout;
        } catch (IOException error) {
            throw new IOException("reading stdout from " + command, error);
        }
    }
}
