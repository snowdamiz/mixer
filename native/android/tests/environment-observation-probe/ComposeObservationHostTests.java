package dev.mixer.android;

import android.app.Activity;
import android.os.Build;
import android.view.View;
import android.widget.FrameLayout;
import java.util.List;

/** The actual observation policy with the existing faulting Android leaves. */
public final class ComposeObservationHostTests {
    private static final int[] LISTENER_API = {28, 28, 28, 28, 30, 34, 36, 33};

    private static void require(boolean condition, String label) {
        if (!condition) throw new AssertionError(label);
    }

    private static Throwable thrown(Runnable operation) {
        try {
            operation.run();
        } catch (RuntimeException | Error error) {
            return error;
        }
        throw new AssertionError("expected observer to reject");
    }

    private static final class Fixture implements AutoCloseable {
        final Activity activity = new Activity();
        final FrameLayout root = new FrameLayout(activity);
        final NativeEnvironmentV2.Observer observer;
        int changes;

        Fixture(int sdk) {
            ObserverHostProbe.reset();
            Build.VERSION.SDK_INT = sdk;
            observer = NativeEnvironmentV2.Observer.forCompose(activity, root,
                (from, change, cause, primary, fatal) -> changes++);
            observer.register();
        }

        @Override public void close() {
            observer.close();
        }
    }

    private static void sdkMatrix() {
        for (int sdk = 28; sdk <= 37; sdk++) {
            try (Fixture f = new Fixture(sdk)) {
                for (int slot = 0; slot < LISTENER_API.length; slot++) {
                    require((ObserverHostProbe.live[slot] != null) == (sdk >= LISTENER_API[slot]),
                        "listener add API " + sdk + " slot " + slot);
                }
                var environment = f.observer.readForCompose();
                require(environment.frameworkFitsInsets() == (sdk < 30), "system fitting");
                require(environment.value().accessibility().reduceMotion() == (sdk < 33), "motion fallback");
                require(!environment.value().accessibility().boldText() && environment.weightDelta() == 0,
                    "base weight");
                require(!environment.value().accessibility().increasedContrast(), "base contrast");
                require(thrown(f.observer::capture) instanceof AppearanceDescriptorV2.Failure,
                    "observation granted legacy capture");
                require(thrown(() -> f.observer.bindRenderer(new NativeRenderer())) instanceof IllegalStateException,
                    "observation bound legacy renderer");
                View.OnLayoutChangeListener old = (View.OnLayoutChangeListener) ObserverHostProbe.live[1];
                f.observer.close();
                for (int slot = 0; slot < LISTENER_API.length; slot++) {
                    int state = sdk >= LISTENER_API[slot]
                        ? NativeEnvironmentV2.Observer.RETURNED : NativeEnvironmentV2.Observer.UNATTEMPTED;
                    require(ObserverHostProbe.live[slot] == null && f.observer.cleanupLedger().state(slot) == state,
                        "listener cleanup API " + sdk + " slot " + slot);
                }
                int changes = f.changes;
                old.onLayoutChange(f.root, 0, 0, 320, 480, 0, 0, 320, 300);
                require(f.changes == changes, "retired callback reached owner");
                require(thrown(f.observer::readForCompose) instanceof AppearanceDescriptorV2.Failure, "retired read");
            }
        }
    }

    private static void valuesAndFailures() {
        try (Fixture f = new Fixture(37)) {
            ObserverHostProbe.contrast = -1f;
            require(!f.observer.readForCompose().value().accessibility().increasedContrast(), "negative contrast");
            ObserverHostProbe.contrast = .5f;
            require(f.observer.readForCompose().value().accessibility().increasedContrast(), "positive contrast");
            ObserverHostProbe.contrast = 0f;
            ObserverHostProbe.highContrast = true;
            require(f.observer.readForCompose().value().accessibility().increasedContrast(), "high-contrast text");
            f.activity.getResources().config.fontWeightAdjustment = 300;
            ObserverHostProbe.animator = 0;
            var environment = f.observer.readForCompose();
            require(environment.weightDelta() == 300 && environment.value().accessibility().boldText()
                && environment.value().accessibility().reduceMotion(), "bold text and reduced motion");
            f.activity.getResources().config.fontWeightAdjustment = -100;
            environment = f.observer.readForCompose();
            require(environment.weightDelta() == -100 && !environment.value().accessibility().boldText(),
                "negative weight");
            f.activity.getResources().config.fontWeightAdjustment =
                android.content.res.Configuration.FONT_WEIGHT_ADJUSTMENT_UNDEFINED;
            var unset = NativeEnvironmentPlatformV2.snapshotForCompose(f.activity, f.root).fontAdjustment;
            require(unset.status == NativeEnvironmentPlatformV2.Status.UNSET_PREFERENCE && unset.value == null,
                "unset font weight misclassified");
            environment = f.observer.readForCompose();
            require(environment.weightDelta() == 0 && !environment.value().accessibility().boldText(),
                "unset weight should use the shared role weights");
            for (String source : List.of("config", "metrics", "token", "direction", "locale", "dp",
                    "sp", "insets", "high", "contrast", "animator")) {
                SecurityException failure = new SecurityException(source);
                ObserverHostProbe.failingRead = source;
                ObserverHostProbe.readFailure = failure;
                require(thrown(f.observer::readForCompose) == failure, "failure became fallback at " + source);
            }
            ObserverHostProbe.failingRead = null;
            f.root.rootInsets = null;
            require(thrown(f.observer::readForCompose) instanceof AppearanceDescriptorV2.Failure, "missing exact insets");
        }
        try (Fixture f = new Fixture(28)) {
            ObserverHostProbe.readHook = () -> {
                ObserverHostProbe.readHook = null;
                f.observer.invalidate();
            };
            require(thrown(f.observer::readForCompose) instanceof AppearanceDescriptorV2.Failure,
                "observation crossed an invalidation during the read");
            require(f.observer.readForCompose().frameworkFitsInsets(), "observation did not recover");
            ObserverHostProbe.failingRead = "sp";
            SecurityException failure = new SecurityException("sp");
            ObserverHostProbe.readFailure = failure;
            require(thrown(f.observer::readForCompose) == failure, "old API hid required font scale failure");
        }
    }

    public static void main(String[] args) {
        sdkMatrix();
        valuesAndFailures();
        System.out.println("PASS Compose observation policies and listener cleanup for API 28 through 37 with host leaves");
    }
}
