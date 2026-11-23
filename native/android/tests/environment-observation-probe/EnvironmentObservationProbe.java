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
import android.util.Log;
import android.util.TypedValue;
import android.view.View;
import android.view.Window;
import android.view.WindowInsets;
import android.widget.FrameLayout;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.FutureTask;
import java.util.function.Predicate;
import java.util.function.Supplier;

import static dev.mixer.android.NativeEnvironmentPlatformV2.Status.*;

/** Exercises the production Compose observer against Activity-owned windows. */
@SuppressWarnings("deprecation")
public final class EnvironmentObservationProbe extends Instrumentation {
    private static final int SDK = Build.VERSION.SDK_INT;
    private static final long WINDOW_MS = 5000;
    private static final long INTERVAL_MS = 100;
    private static final int[] LISTENER_API = {28, 28, 28, 28, 30, 34, 36, 33};
    private static final String[] LISTENERS = {"component", "layout", "attachment", "focus", "insets",
        "contrast", "highText", "motion"};
    private final StringBuilder events = new StringBuilder();
    private final StringBuilder samples = new StringBuilder();
    private final StringBuilder settingsLog = new StringBuilder();
    private final StringBuilder restorations = new StringBuilder();
    private final StringBuilder outcomes = new StringBuilder();
    private final List<ProbeActivity> activities = new ArrayList<>();
    private int uiSequence;
    private int watchSequence;

    public static final class ProbeActivity extends Activity {
        FrameLayout root;
        EnvironmentObservationProbe probe;
        ProbeActivity predecessor;
        Object detachedToken;
        int number;
        int detaches;
        int configurations;
        String lastConfiguration = "none";
        boolean destroying;
        boolean configurationDestruction;
        boolean destroyReturned;

        @Override protected void onCreate(Bundle state) {
            super.onCreate(state);
            if (SDK >= 30) Api30.edgeToEdge(getWindow());
            root = new FrameLayout(this);
            setContentView(root);
        }

        @Override public void onConfigurationChanged(Configuration configuration) {
            configurations++;
            lastConfiguration = describeConfiguration(configuration);
            super.onConfigurationChanged(configuration);
            probe.event("lifecycle configuration " + rootIdentity(this) + " " + lastConfiguration);
        }
    }

    private static final class Api30 {
        static void edgeToEdge(Window window) { window.setDecorFitsSystemWindows(false); }
        static String insets(WindowInsets insets) {
            return insets == null ? "null"
                : insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout()).toString();
        }
    }

    private static final class Api31 {
        static int weight(Configuration configuration) { return configuration.fontWeightAdjustment; }
    }

    @Override public void callActivityOnCreate(Activity activity, Bundle state) {
        ProbeActivity owned = (ProbeActivity) activity;
        owned.predecessor = latest();
        owned.probe = this;
        owned.number = activities.size() + 1;
        activities.add(owned);
        super.callActivityOnCreate(activity, state);
        event("lifecycle create " + rootIdentity(owned) + " predecessor="
            + (owned.predecessor == null ? "none" : owned.predecessor.number) + " savedState=" + (state != null));
        owned.root.addOnAttachStateChangeListener(new View.OnAttachStateChangeListener() {
            @Override public void onViewAttachedToWindow(View view) {
                event("lifecycle attach " + rootIdentity(owned));
            }

            @Override public void onViewDetachedFromWindow(View view) {
                owned.detachedToken = view.getWindowToken();
                owned.detaches++;
                event("lifecycle detach " + rootIdentity(owned) + " detaches=" + owned.detaches);
            }
        });
    }

    @Override public void callActivityOnDestroy(Activity activity) {
        ProbeActivity owned = (ProbeActivity) activity;
        owned.destroying = true;
        owned.configurationDestruction = activity.isChangingConfigurations() && !activity.isFinishing();
        event("lifecycle destroy " + rootIdentity(owned) + " changingConfigurations="
            + activity.isChangingConfigurations() + " finishing=" + activity.isFinishing());
        super.callActivityOnDestroy(activity);
        owned.destroyReturned = true;
    }

    private ProbeActivity latest() {
        return activities.isEmpty() ? null : activities.get(activities.size() - 1);
    }

    private record Authority(ProbeActivity activity, FrameLayout root, Object token, int detaches) {
        boolean isCurrent(ProbeActivity latest) {
            return activity == latest && activity.root == root && root.getContext() == activity
                && !activity.destroying && !activity.isDestroyed() && !activity.isFinishing()
                && root.isAttachedToWindow() && root.getWindowToken() == token && activity.detaches == detaches;
        }

        String description() {
            return rootIdentity(activity) + " acquiredToken=" + identity(token)
                + " detaches=" + activity.detaches + "/" + detaches;
        }
    }

    @Override public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        start();
    }

    @Override public void onStart() {
        Throwable failure = null;
        try {
            check(SDK == 28 || SDK == 35 || SDK == 36 || SDK == 37, "unexpected probe API " + SDK);
            UiAutomation shell = getUiAutomation(UiAutomation.FLAG_DONT_SUPPRESS_ACCESSIBILITY_SERVICES);
            String user = command(shell, "cmd activity get-current-user");
            settingsLog.append("foreground-user=").append(user).append('\n');
            check(SDK != 28 || "0".equals(user), "API 28 probe requires foreground user 0");
            Journey completed = exercise(shell);
            main(() -> {
                completed.verifyRetired("after Settings restoration");
                return null;
            });
        } catch (Exception | AssertionError | LinkageError error) {
            failure = error;
        } finally {
            try {
                main(() -> {
                    for (ProbeActivity owned : activities) {
                        if (!owned.destroying && !owned.isFinishing()) {
                            event("fixture finish " + rootIdentity(owned));
                            owned.finish();
                        }
                    }
                    return null;
                });
            } catch (RuntimeException | AssertionError cleanup) {
                if (failure == null) failure = cleanup;
                else if (failure != cleanup) failure.addSuppressed(cleanup);
            }
        }
        flush("end");
        Bundle result = new Bundle();
        result.putInt("api", SDK);
        result.putString("fingerprint", Build.FINGERPRINT);
        result.putString("status", failure == null ? "passed" : "failed");
        result.putString("checks", outcomes.toString());
        result.putString("settings_restore", restorations.toString());
        if (failure == null) result.putString("cleanup", "settings restored");
        else result.putString("failure", Log.getStackTraceString(failure));
        finish(failure == null ? Activity.RESULT_OK : Activity.RESULT_CANCELED, result);
    }

    private Authority acquireActivity() {
        ProbeActivity launched = (ProbeActivity) startActivitySync(new Intent(getTargetContext(), ProbeActivity.class)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        main(() -> {
            check(launched.number != 0 && latest() != null, "launch returned without fixture lifecycle");
            event("fixture launch returned " + rootIdentity(launched));
            return null;
        });
        long deadline = now() + WINDOW_MS;
        while (now() < deadline) {
            Authority authority = main(() -> {
                Authority live = liveAuthority();
                if (live == null) return null;
                for (ProbeActivity old : activities) {
                    if (old != live.activity()) rejectRetiredRoot(old);
                }
                event("fixture acquired " + live.description());
                return live;
            });
            if (authority != null) return authority;
            sleepUntilNextSample(deadline);
        }
        throw new AssertionError("fixture Activity acquisition timed out"
            + main(() -> latest() == null ? "" : " latest=" + rootIdentity(latest())));
    }

    private Authority liveAuthority() {
        ProbeActivity candidate = latest();
        if (candidate == null || candidate.root == null) return null;
        FrameLayout root = candidate.root;
        Object token = root.getWindowToken();
        Authority binding = new Authority(candidate, root, token, candidate.detaches);
        if (token == null || !binding.isCurrent(candidate) || root.getWidth() <= 0 || root.getHeight() <= 0
                || (SDK >= 30 && root.getRootWindowInsets() == null)) return null;
        return binding;
    }

    private Journey exercise(UiAutomation shell) throws IOException {
        try (Setting font = new Setting(shell, "system", "font_scale");
             Setting weight = SDK < 31 ? null : new Setting(shell, "secure", "font_weight_adjustment");
             Setting motion = SDK < 33 ? null : new Setting(shell, "global", "animator_duration_scale");
             Setting contrast = SDK < 34 ? null : new Setting(shell, "secure", "contrast_level");
             Setting high = SDK < 36 ? null : new Setting(shell, "secure", "high_text_contrast_enabled")) {
            font.normalize("1.0");
            if (weight != null) weight.normalize("0");
            if (motion != null) motion.normalize("1");
            if (contrast != null) contrast.normalize("0");
            if (high != null) high.normalize("0");
            try (Journey journey = new Journey(acquireActivity())) {
                int profile = journey.baseline();
                journey.edge("font scale on", font, "1.0", "1.3", Source.CONFIGURATION,
                    s -> s.fontScale() == 1.3f && s.profile() > profile);
                if (weight != null) {
                    journey.edge("bold text on", weight, "0", "300", Source.CONFIGURATION,
                        s -> Integer.valueOf(300).equals(s.weight()) && s.compose().weightDelta() == 300);
                }
                if (motion != null) {
                    journey.edge("reduce motion on", motion, "1", "0", Source.MOTION,
                        s -> Float.valueOf(0f).equals(s.animator()) && s.reduced());
                }
                if (contrast != null) {
                    journey.edge("early contrast on", contrast, "0", "1", Source.CONTRAST,
                        s -> s.highOff() && Float.valueOf(1f).equals(s.contrast()) && s.increased());
                    journey.edge("early contrast off", contrast, "1", "0", Source.CONTRAST,
                        s -> s.highOff() && Float.valueOf(0f).equals(s.contrast()) && !s.increased());
                }
                if (high != null) {
                    journey.edge("high-text on", high, "0", "1", Source.HIGH_TEXT,
                        s -> Boolean.TRUE.equals(s.high()) && Float.valueOf(0f).equals(s.contrast()) && s.increased());
                }
                journey.replaceOnSameRoot();
                journey.edge("replacement font scale off", font, "1.3", "1.0", Source.CONFIGURATION,
                    s -> s.fontScale() == 1f && s.profile() == profile);
                if (weight != null) {
                    journey.edge("replacement bold text off", weight, "300", "0", Source.CONFIGURATION,
                        s -> s.weightNeutral() && s.compose().weightDelta() == 0);
                }
                if (motion != null) {
                    journey.edge("replacement reduce motion off", motion, "0", "1", Source.MOTION,
                        s -> Float.valueOf(1f).equals(s.animator()) && !s.reduced());
                }
                if (high != null) {
                    journey.edge("replacement high-text off", high, "1", "0", Source.HIGH_TEXT,
                        s -> s.highOff() && Float.valueOf(0f).equals(s.contrast()) && !s.increased());
                }
                if (contrast != null) {
                    journey.edge("replacement late contrast on", contrast, "0", "1", Source.CONTRAST,
                        s -> s.highOff() && Float.valueOf(1f).equals(s.contrast()) && s.increased());
                }
                return journey;
            }
        }
    }

    private enum Source {
        CONFIGURATION("NativeEnvironmentV2$Observer.onConfigurationChanged"),
        MOTION("NativeEnvironmentPlatformV2$Api33"),
        CONTRAST("NativeEnvironmentPlatformV2$Api34"),
        HIGH_TEXT("NativeEnvironmentPlatformV2$Api36");

        private final String frame;
        Source(String frame) { this.frame = frame; }
    }

    private final class Journey implements AutoCloseable {
        private final List<Watch> retired = new ArrayList<>();
        private Watch active;

        Journey(Authority authority) {
            main(() -> {
                active = new Watch(authority);
                return null;
            });
        }

        int baseline() {
            long deadline = now() + WINDOW_MS;
            do {
                Sample sample = main(() -> snapshot(active));
                logSample("baseline", sample);
                if (sample.valid() && sample.fontScale() == 1f && sample.weightNeutral()
                        && (SDK < 33 || Float.valueOf(1f).equals(sample.animator()))
                        && (SDK < 34 || Float.valueOf(0f).equals(sample.contrast())) && sample.highOff()) {
                    flush("baseline");
                    return sample.profile();
                }
                sleepUntilNextSample(deadline);
            } while (now() < deadline);
            throw new AssertionError("baseline did not settle");
        }

        void replaceOnSameRoot() {
            main(() -> {
                Watch first = active;
                check(snapshot(first).valid(), "same-root replacement requires a valid live observation");
                retire(first, false);
                active = new Watch(first.authority);
                check(active.observer != first.observer && snapshot(active).valid(), "same-root replacement read");
                assertQuietRetired("same-root replacement");
                event("same-root replacement old=" + first.label + " new=" + active.label + " "
                    + first.authority.description());
                return null;
            });
            outcomes.append("same-root observer replacement\n");
            flush("same-root replacement");
        }

        void edge(String label, Setting setting, String from, String to, Source source, Predicate<Sample> expected)
                throws IOException {
            String stored = setting.read();
            settingsLog.append(now()).append(" before ").append(setting.key).append('=').append(stored).append('\n');
            check(from.equals(stored), "unexpected prior Settings value for " + label + ": " + stored);
            Before before = main(() -> {
                assertQuietRetired("before " + label);
                Sample live = snapshot(active);
                return new Before(active, live, active.sourceCounts[source.ordinal()]);
            });
            logSample("before " + label, before.sample());
            check(before.sample().valid() && !expected.test(before.sample()), "invalid starting observation for " + label);
            long writeStarted = now();
            setting.set(to, false);
            long deadline = now() + WINDOW_MS;
            settingsLog.append("window ").append(label).append(" start=").append(deadline - WINDOW_MS)
                .append(" deadline=").append(deadline).append('\n');

            Sample last = null;
            Watch witnessed = null;
            long witnessedAt = 0;
            String previous = "";
            while (now() < deadline) {
                Sample sample = main(() -> {
                    if (now() >= deadline || !followRecreation(label)) return null;
                    return snapshot(active);
                });
                if (sample != null) {
                    last = sample;
                    String proof = proof(sample, before, source, writeStarted, expected);
                    String current = sample.details() + " proof=" + proof;
                    if (!current.equals(previous)) {
                        logSample(label + " proof=" + proof, sample);
                        previous = current;
                    }
                    if (sample.uptime() < deadline) {
                        witnessed = proof == null ? null : sample.watch();
                        witnessedAt = sample.uptime();
                    }
                }
                sleepUntilNextSample(deadline);
            }

            // The boundary check can disqualify an in-window witness. It cannot bind a successor
            // or give credit for a first valid observation outside the five-second window.
            Sample boundary = main(() -> {
                assertQuietRetired("deadline " + label);
                if (active.closed || !active.authority.isCurrent(latest())) {
                    event("deadline has no current bound root for " + label + " " + active.authority.description());
                    return null;
                }
                return snapshot(active);
            });
            if (last != null) logSample("last in-window " + label, last);
            if (boundary != null) logSample("deadline " + label, boundary);
            String actual = setting.read();
            settingsLog.append(now()).append(" after ").append(setting.key).append('=').append(actual).append('\n');
            String proof = boundary == null ? null : proof(boundary, before, source, writeStarted, expected);
            boolean accepted = to.equals(actual) && proof != null && witnessed == boundary.watch();
            if (accepted) {
                String outcome = label + " proof=" + proof + " source=" + source
                    + " initial=" + before.watch().label + " final=" + witnessed.label
                    + " witnessUptime=" + witnessedAt + " deadline=" + deadline;
                outcomes.append(outcome).append('\n');
                samples.append(outcome).append('\n');
            }
            flush(label);
            check(accepted, label + " did not settle on the authoritative root within " + WINDOW_MS
                + "ms, readback=" + actual + " active=" + (boundary == null ? "none" : boundary.watch().label)
                + " inWindowWitness=" + (witnessed == null ? "none" : witnessed.label));
        }

        private boolean followRecreation(String label) {
            assertQuietRetired(label);
            Authority old = active.authority;
            if (!active.closed && old.isCurrent(latest())) return true;
            ProbeActivity predecessor = old.activity();
            check(!predecessor.isFinishing(), "fixture Activity finished during " + label);
            check(!predecessor.destroying || predecessor.configurationDestruction,
                "non-configuration Activity destruction during " + label);
            if (!predecessor.configurationDestruction || !predecessor.destroyReturned
                    || predecessor.root.isAttachedToWindow()) return false;
            check(predecessor.detaches == old.detaches() + 1 && predecessor.detachedToken == old.token(),
                "missing exact binding detach during " + label);

            if (!active.closed) {
                rejectRetiredRoot(predecessor);
                event("retired root construction=REFUSED " + rootIdentity(predecessor));
                retire(active, true);
            }
            Authority next = liveAuthority();
            if (next == null) return false;
            check(next.activity() != predecessor && next.root() != old.root(), "recreation reused the retired root");
            for (ProbeActivity intermediate = next.activity().predecessor; intermediate != predecessor;
                    intermediate = intermediate.predecessor) {
                check(intermediate != null, "configuration successor did not descend from the bound Activity");
                rejectRetiredRoot(intermediate);
                event("unbound intermediate root construction=REFUSED " + rootIdentity(intermediate));
            }
            Watch previous = active;
            active = new Watch(next);
            assertQuietRetired("rebound " + label);
            event("configuration rebind " + label + " old=" + previous.label + " new=" + active.label + " "
                + old.description() + " -> " + next.description());
            return true;
        }

        private void retire(Watch watch, boolean detached) {
            if (detached) {
                check(watch.detached == 1 && !watch.observer.ready(), "missing exact observer DETACHED terminal");
                rejectComposeRead(watch);
            } else {
                check(watch.detached == 0, "unexpected terminal before ordered close of " + watch.label);
            }
            watch.close();
            check(!watch.observer.ready(), "closed observer still ready " + watch.label);
            rejectComposeRead(watch);
            rejectRoute(watch);
            retired.add(watch);
            event(watch.label + " retired read=REFUSED route=REFUSED callbacks=" + watch.callbacks
                + " " + watch.authority.description());
        }

        private void assertQuietRetired(String stage) {
            for (Watch watch : retired) {
                check(watch.callbacks == watch.callbacksAtClose && !watch.observer.ready(),
                    "retired observer was active during " + stage + " " + watch.label);
            }
        }

        private void verifyRetired(String stage) {
            assertQuietRetired(stage);
            for (Watch watch : retired) {
                rejectRoute(watch);
                rejectComposeRead(watch);
                event("quiet retired " + watch.label + " callbacks=" + watch.callbacks + " " + stage + " "
                    + watch.authority.description());
            }
        }

        @Override public void close() {
            main(() -> {
                if (!active.closed) {
                    if (active.authority.isCurrent(latest())) {
                        retire(active, false);
                    } else {
                        // Preserve the journey's primary assertion and still attempt cleanup.
                        active.close();
                    }
                }
                verifyRetired("journey close");
                return null;
            });
        }
    }

    private record Before(Watch watch, Sample sample, int sourceCount) {}

    private static String proof(Sample sample, Before before, Source source, long writeStarted,
            Predicate<Sample> expected) {
        if (!sample.valid() || !expected.test(sample)) return null;
        if (sample.watch() != before.watch()) return "FRESH_LIVE_TYPED_READ";
        int slot = source.ordinal();
        return sample.sourceCounts()[slot] > before.sourceCount() && sample.sourceUptimes()[slot] >= writeStarted
            ? "SAME_ROOT_CALLBACK" : null;
    }

    private static void rejectRetiredRoot(ProbeActivity old) {
        check(old.destroyReturned && old.configurationDestruction && !old.isFinishing() && old.detaches > 0
                && !old.root.isAttachedToWindow(),
            "missing configuration destruction/detach for " + rootIdentity(old));
        expectUnsupported(() -> NativeEnvironmentV2.Observer.forCompose(old, old.root,
            (from, change, cause, primary, fatal) -> {}), "observer construction for " + rootIdentity(old));
    }

    private void rejectComposeRead(Watch watch) {
        expectUnsupported(watch.observer::readForCompose, "retired read " + watch.label);
    }

    private void rejectRoute(Watch watch) {
        expectUnsupported(() -> routedRead(watch), "retired route " + watch.label);
    }

    private static void expectUnsupported(Runnable read, String operation) {
        try {
            read.run();
        } catch (AppearanceDescriptorV2.Failure refusal) {
            check(refusal.code == AppearanceDescriptorV2.Error.unsupportedNativeOperation,
                "wrong rejection for " + operation + ": " + refusal.code);
            return;
        }
        throw new AssertionError("unexpected success: " + operation);
    }

    private NativeEnvironmentV2.ComposeEnvironment routedRead(Watch watch) {
        if (watch.closed || !watch.authority.isCurrent(latest())) NativeEnvironmentV2.unsupported();
        return watch.observer.readForCompose();
    }

    private final class Watch {
        private final String label = "observer#" + (++watchSequence);
        private final Authority authority;
        private final NativeEnvironmentV2.Observer observer;
        private final int[] sourceCounts = new int[Source.values().length];
        private final long[] sourceUptimes = new long[Source.values().length];
        private int callbacks;
        private int detached;
        private int callbacksAtClose;
        private boolean closed;

        Watch(Authority authority) {
            this.authority = authority;
            check(authority.isCurrent(latest()), "registration without root authority");
            observer = NativeEnvironmentV2.Observer.forCompose(authority.activity(), authority.root(), this::changed);
            observer.register();
            try {
                ledger(NativeEnvironmentV2.Observer.POSSIBLY_OWNED);
            } catch (AssertionError failure) {
                try { observer.close(); }
                catch (RuntimeException | Error cleanup) { failure.addSuppressed(cleanup); }
                throw failure;
            }
        }

        private void changed(NativeEnvironmentV2.Observer from, NativeEnvironmentV2.Change change,
                NativeEnvironmentV2.RendererCause cause, Throwable primary, Error fatal) {
            check(from == observer && from.activity == authority.activity() && from.root == authority.root(),
                "foreign observer callback " + label);
            callbacks++;
            String origin = caller();
            if (change == NativeEnvironmentV2.Change.INVALIDATED) {
                // Once a binding loses authority, its callbacks cannot validate the edge.
                if (authority.isCurrent(latest())) {
                    for (Source source : Source.values()) {
                        if (origin.contains(source.frame)) {
                            sourceCounts[source.ordinal()]++;
                            sourceUptimes[source.ordinal()] = now();
                        }
                    }
                }
            } else if (change == NativeEnvironmentV2.Change.DETACHED) {
                detached++;
                check(!from.ready() && !authority.isCurrent(latest()), "DETACHED failed to fence the observer");
                rejectComposeRead(this);
                rejectRoute(this);
            } else {
                throw new AssertionError("unexpected observer terminal " + label + " " + change, primary);
            }
            event(label + " change=" + change + " " + authority.description() + " origin=" + origin);
        }

        void close() {
            if (closed) return;
            callbacksAtClose = callbacks;
            closed = true;
            observer.close();
            ledger(NativeEnvironmentV2.Observer.RETURNED);
            check(callbacks == callbacksAtClose, "callback during observer removal " + label);
        }

        private void ledger(int expected) {
            StringBuilder slots = new StringBuilder();
            int acquired = 0;
            for (int slot = 0; slot < LISTENER_API.length; slot++) {
                boolean applicable = SDK >= LISTENER_API[slot];
                int state = applicable ? expected : NativeEnvironmentV2.Observer.UNATTEMPTED;
                var ledger = observer.cleanupLedger();
                check(ledger.state(slot) == state && ledger.failure(slot) == null,
                    label + " unexpected listener disposition " + LISTENERS[slot] + "=" + ledger.state(slot));
                if (applicable) acquired++;
                slots.append(LISTENERS[slot]).append('=').append(!applicable ? "UNATTEMPTED"
                    : expected == NativeEnvironmentV2.Observer.RETURNED ? "RETURNED" : "POSSIBLY_OWNED").append(' ');
            }
            event(label + " observer=" + identity(observer) + " slots=" + acquired + "/8 " + slots
                + authority.description());
        }
    }

    private record Sample(Watch watch, long uptime, int sequence, float fontScale,
            NativeEnvironmentPlatformV2.Snapshot typed, NativeEnvironmentV2.ComposeEnvironment compose,
            int[] sourceCounts, long[] sourceUptimes, String details) {
        Integer weight() { return typed.fontAdjustment.value; }
        Boolean high() { return typed.highContrast.value; }
        Float contrast() { return typed.contrast.value; }
        Float animator() { return typed.animator.value; }
        int profile() { return compose.value().profile().ordinal(); }
        boolean reduced() { return compose.value().accessibility().reduceMotion(); }
        boolean increased() { return compose.value().accessibility().increasedContrast(); }
        boolean highOff() { return SDK < 36 || Boolean.FALSE.equals(high()); }
        boolean weightNeutral() {
            return SDK < 31 || typed.fontAdjustment.status == UNSET_PREFERENCE || Integer.valueOf(0).equals(weight());
        }

        boolean valid() {
            if (typed == null || compose == null || typed.frame.status != KNOWN || typed.frame.value.token != watch.authority.token()
                    || typed.dark.status != KNOWN || typed.rtl.status != KNOWN || typed.locale.status != KNOWN
                    || typed.density1024.status != KNOWN || typed.bodyProfile.status != KNOWN
                    || typed.bodyProfile.value != profile() || typed.insets.status != (SDK < 30 ? UNAVAILABLE_SEMANTICS : KNOWN)
                    || compose.frameworkFitsInsets() != (SDK < 30)
                    || !(SDK < 31 ? typed.fontAdjustment.status == UNAVAILABLE_API
                        : typed.fontAdjustment.status == KNOWN || typed.fontAdjustment.status == UNSET_PREFERENCE)
                    || typed.animator.status != (SDK < 33 ? UNAVAILABLE_API : KNOWN)
                    || typed.contrast.status != (SDK < 34 ? UNAVAILABLE_API : KNOWN)
                    || typed.highContrast.status != (SDK < 36 ? UNAVAILABLE_API : KNOWN)) return false;
            int adjustment = weight() == null ? 0 : weight();
            return compose.weightDelta() == adjustment && compose.value().accessibility().boldText() == (adjustment > 0)
                && increased() == (Boolean.TRUE.equals(high()) || (contrast() != null && contrast() > 0))
                && reduced() == (animator() == null || animator() == 0f);
        }
    }

    private Sample snapshot(Watch watch) {
        Authority authority = watch.authority;
        NativeEnvironmentPlatformV2.Snapshot typed = null;
        String fields;
        try {
            typed = NativeEnvironmentPlatformV2.snapshotForCompose(authority.activity(), authority.root());
            fields = "typed{frame=" + observed(typed.frame) + ", dark=" + observed(typed.dark)
                + ", rtl=" + observed(typed.rtl) + ", locale=" + observed(typed.locale)
                + ", density1024=" + observed(typed.density1024) + ", bodyProfile=" + observed(typed.bodyProfile)
                + ", insets=" + observed(typed.insets) + ", fontAdjustment=" + observed(typed.fontAdjustment)
                + ", contrast=" + observed(typed.contrast) + ", highContrast=" + observed(typed.highContrast)
                + ", animator=" + observed(typed.animator) + "}";
        } catch (RuntimeException | LinkageError failure) {
            fields = "snapshotFailure=" + stack(failure);
        }
        NativeEnvironmentV2.ComposeEnvironment compose = null;
        String result;
        try {
            compose = routedRead(watch);
            result = "compose=" + compose;
        } catch (RuntimeException | LinkageError failure) {
            result = "composeFailure=" + stack(failure);
        }
        Configuration config = authority.activity().getResources().getConfiguration();
        String details = watch.label + " " + authority.description() + " current="
            + authority.isCurrent(latest()) + " ready=" + watch.observer.ready()
            + "\n  " + describeConfiguration(config) + " configurationCallbacks=" + authority.activity().configurations
            + " lastConfiguration={" + authority.activity().lastConfiguration + "}"
            + " sp17=" + TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, 17,
                authority.activity().getResources().getDisplayMetrics())
            + " typedInsets=" + (SDK < 30 ? "unavailable" : Api30.insets(authority.root().getRootWindowInsets()))
            + "\n  " + fields + "\n  " + result + "\n  notifications=" + watch.callbacks
            + " configuration=" + watch.sourceCounts[Source.CONFIGURATION.ordinal()]
            + " motion=" + watch.sourceCounts[Source.MOTION.ordinal()]
            + " contrast=" + watch.sourceCounts[Source.CONTRAST.ordinal()]
            + " highText=" + watch.sourceCounts[Source.HIGH_TEXT.ordinal()];
        return new Sample(watch, now(), ++uiSequence, config.fontScale, typed, compose,
            watch.sourceCounts.clone(), watch.sourceUptimes.clone(), details);
    }

    private static String observed(NativeEnvironmentPlatformV2.Observed<?> observation) {
        Object value = observation.value;
        if (value instanceof NativeEnvironmentPlatformV2.Frame frame) {
            value = identity(frame.token) + "/" + frame.width + "x" + frame.height + "@" + frame.x + "," + frame.y
                + " in " + frame.windowWidth + "x" + frame.windowHeight;
        } else if (value instanceof NativeEnvironmentPlatformV2.Insets4 insets) {
            value = "top=" + insets.top + ",left=" + insets.left + ",bottom=" + insets.bottom + ",right=" + insets.right;
        }
        return observation.status + "(" + value + "; " + observation.reason
            + (observation.failure == null ? "" : "; " + stack(observation.failure)) + ")";
    }

    private static String describeConfiguration(Configuration config) {
        return "fontScale=" + config.fontScale + " fontWeightAdjustment="
            + (SDK < 31 ? "unavailable" : Integer.toString(Api31.weight(config)));
    }

    private static String rootIdentity(ProbeActivity activity) {
        FrameLayout root = activity.root;
        return "activity#" + activity.number + "=" + identity(activity) + " root=" + identity(root)
            + " token=" + identity(root == null ? null : root.getWindowToken());
    }

    private static String identity(Object value) {
        return value == null ? "null" : Integer.toHexString(System.identityHashCode(value));
    }

    private static String stack(Throwable failure) {
        return Log.getStackTraceString(failure).trim().replace("\n", " <- ");
    }

    private static String caller() {
        StringBuilder frames = new StringBuilder();
        for (StackTraceElement frame : Thread.currentThread().getStackTrace()) {
            if (frame.getClassName().startsWith("dev.mixer.android.NativeEnvironment")) {
                frames.append(frame).append(" <- ");
            }
        }
        return frames.toString();
    }

    private void logSample(String label, Sample sample) {
        samples.append(sample.uptime()).append(" ui#").append(sample.sequence()).append(' ').append(label).append(' ')
            .append(sample.details()).append(" valid=").append(sample.valid()).append('\n');
    }

    private void flush(String stage) {
        Bundle report = new Bundle();
        report.putString("stage", stage);
        report.putString("samples", samples.toString());
        report.putString("settings", settingsLog.toString());
        report.putString("callbacks", main(() -> {
            String batch = events.toString();
            events.setLength(0);
            return batch;
        }));
        samples.setLength(0);
        settingsLog.setLength(0);
        sendStatus(0, report);
    }

    private void event(String what) {
        events.append(now()).append(" ui#").append(++uiSequence).append(' ').append(what).append('\n');
    }

    private static long now() { return SystemClock.uptimeMillis(); }

    private static void sleepUntilNextSample(long deadline) {
        long remaining = deadline - now();
        if (remaining > 0) SystemClock.sleep(Math.min(remaining, INTERVAL_MS));
    }

    private <T> T main(Supplier<T> action) {
        FutureTask<T> task = new FutureTask<>(action::get);
        runOnMainSync(task);
        try {
            return task.get();
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(interrupted);
        } catch (ExecutionException failed) {
            if (failed.getCause() instanceof Error error) throw error;
            throw (RuntimeException) failed.getCause();
        }
    }

    private final class Setting implements AutoCloseable {
        private final UiAutomation shell;
        private final String namespace, key, original;
        private boolean dirty;

        Setting(UiAutomation shell, String namespace, String key) throws IOException {
            this.shell = shell;
            this.namespace = namespace;
            this.key = key;
            original = read();
            settingsLog.append("saved ").append(namespace).append(' ').append(key).append('=').append(original).append('\n');
            check("null".equals(original) || original.matches("[-+0-9.Ee]+"), "unexpected saved value for " + key);
        }

        String read() throws IOException { return command(shell, prefix("get")); }

        void normalize(String expected) throws IOException {
            if (!expected.equals(original)) set(expected, false);
        }

        void set(String expected, boolean restoring) throws IOException {
            boolean delete = "null".equals(expected);
            String operation = delete ? prefix("delete") : prefix("put") + " " + expected;
            dirty = true;
            settingsLog.append(now()).append(restoring ? " restore " : " write ").append(operation).append('\n');
            String stdout = command(shell, operation);
            String actual = read();
            String result = operation + " ack=[" + stdout + "] expected=[" + expected + "] readback=[" + actual + "]";
            settingsLog.append(now()).append(' ').append(result).append('\n');
            if (restoring) restorations.append(result).append('\n');
            boolean acknowledged = delete ? "Deleted 1 rows".equals(stdout) || "Deleted 0 rows".equals(stdout)
                : stdout.isEmpty();
            check(acknowledged && expected.equals(actual), "Settings mutation/readback failed: " + result);
        }

        @Override public void close() throws IOException {
            if (dirty) set(original, true);
        }

        private String prefix(String verb) {
            return (SDK == 28 ? "settings " : "settings --user current ") + verb + " " + namespace + " " + key;
        }
    }

    private static String command(UiAutomation shell, String command) throws IOException {
        try (InputStream in = new ParcelFileDescriptor.AutoCloseInputStream(shell.executeShellCommand(command))) {
            byte[] bytes = new byte[1024];
            int length = 0;
            int received;
            while (length < bytes.length && (received = in.read(bytes, length, bytes.length - length)) >= 0) {
                length += received;
            }
            check(length < bytes.length, "oversized stdout from " + command);
            String stdout = new String(bytes, 0, length, StandardCharsets.UTF_8);
            return stdout.endsWith("\n") ? stdout.substring(0, stdout.length() - 1) : stdout;
        }
    }

    private static void check(boolean result, String label) {
        if (!result) throw new AssertionError(label);
    }
}
