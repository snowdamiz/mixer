package dev.mixer.android;

import android.app.Activity;
import android.widget.FrameLayout;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.atomic.AtomicReference;

/** Runs the actual-SDK compiled production coordinator bytecode with explicit test-only leaves. */
public final class NativeCoordinatorV2HostTests {
    private static int checks;
    private static int scenarios;

    static final class Fault extends RuntimeException {
        private static final long serialVersionUID = 1L;
        Fault(String stage) { super("test-only leaf fault: " + stage); }
    }

    static final class Rig {
        static final List<String> trace = new ArrayList<>();
        static final List<Integer> operations = new ArrayList<>();
        static final List<byte[]> rendererPackets = new ArrayList<>();
        static final Set<String> faults = new HashSet<>();
        static final Set<String> errors = new HashSet<>();
        static long createHandle;
        static long token;
        static int commitStatus;
        static int abortStatus;
        static int engineEffects;
        static boolean pending;
        static boolean destroyed;
        static boolean open;
        static boolean attachConsumed;
        static boolean tokenRead;
        static boolean environmentCurrent;
        static boolean nullCandidate;
        static boolean unknownStatusHasEffect;
        static byte[] nextPacket;
        static byte[] packetCopy;
        static byte[] lastInput;
        static String transientText;
        static String hookStage;
        static Runnable hook;
        static NativeCoordinatorV2 coordinator;
        static NativeRenderer renderer;
        static InstalledAppearanceV2 installed;
        static NativeEnvironmentV2 environment;

        static void reset() {
            trace.clear(); operations.clear(); rendererPackets.clear(); faults.clear(); errors.clear();
            createHandle = 17; token = Long.MIN_VALUE + 23; commitStatus = 0; abortStatus = 0;
            engineEffects = 0; pending = false; destroyed = false; open = false;
            attachConsumed = false; tokenRead = false; environmentCurrent = true;
            nullCandidate = false; unknownStatusHasEffect = false;
            nextPacket = new byte[] { 1, 2, 3 }; packetCopy = null; lastInput = null;
            transientText = "committed native input"; hookStage = null; hook = null;
            coordinator = null; renderer = null; installed = null; environment = null;
        }
        static void step(String stage) {
            trace.add(stage);
            if (stage.equals(hookStage)) {
                Runnable callback = hook;
                hook = null; hookStage = null;
                callback.run();
            }
            if (errors.contains(stage)) throw new OutOfMemoryError("test-only allocation fault: " + stage);
            if (faults.contains(stage)) throw new Fault(stage);
        }
        static void check(boolean value, String message) {
            checks++;
            if (!value) throw new AssertionError(message + "; trace=" + trace);
        }
    }

    private static NativeCoordinatorV2 fresh() {
        Activity activity = new Activity();
        NativeCoordinatorV2 coordinator = new NativeCoordinatorV2(activity, new FrameLayout(activity));
        Rig.coordinator = coordinator;
        return coordinator;
    }
    private static NativeCoordinatorV2 initialized() {
        NativeCoordinatorV2 coordinator = fresh();
        coordinator.renderInitial();
        Rig.trace.clear();
        return coordinator;
    }
    private static Throwable rejected(Runnable operation) {
        try { operation.run(); }
        catch (RuntimeException | Error failure) {
            if (failure instanceof AssertionError assertion) throw assertion;
            return failure;
        }
        throw new AssertionError("operation unexpectedly succeeded; trace=" + Rig.trace);
    }
    private static void absent(String stage) {
        Rig.check(!Rig.trace.contains(stage), "must not call " + stage);
    }
    private static void ordered(String... stages) {
        int position = -1;
        for (String stage : stages) {
            int found = Rig.trace.subList(position + 1, Rig.trace.size()).indexOf(stage);
            Rig.check(found >= 0, "ordered stage " + stage);
            position += found + 1;
        }
    }
    private static void retired(NativeCoordinatorV2 coordinator) {
        Rig.check(coordinator.isRetired(), "coordinator retired");
        Rig.check(!coordinator.hasCommittedPresentation(), "no authoritative presentation after retirement");
        Rig.check(Rig.trace.contains("renderer.dispose.before"), "native owner disposal attempted");
        Rig.check(Rig.trace.contains("engine.destroy.before"), "engine owner destruction attempted");
    }
    private static void scenario(String name, Runnable body) {
        Rig.reset();
        body.run();
        scenarios++;
        System.out.println("PASS " + name + " trace=" + Rig.trace);
    }

    private static void success() {
        scenario("initial-and-input-success-order-opaque-sign-bit-token", () -> {
            NativeCoordinatorV2 coordinator = fresh();
            coordinator.renderInitial();
            Rig.check(coordinator.hasCommittedPresentation() && !coordinator.isRetired(), "initial publication");
            Rig.check(Rig.open && Rig.engineEffects == 1, "both owners committed");
            Rig.check(Rig.rendererPackets.get(0) == Rig.packetCopy, "exact defensive copy used by renderer");
            ordered("capture.installed", "capture.environment", "engine.prepare.before", "engine.token",
                "engine.packet.copy", "renderer.prepare", "environment.current", "renderer.attach.preflight",
                "renderer.attach.return", "renderer.validate", "engine.commit.before", "engine.commit.after",
                "renderer.finish.before", "renderer.finish.after");
            int validate = Rig.trace.indexOf("renderer.validate");
            Rig.check(Rig.trace.get(validate + 1).equals("engine.commit.before"), "validate immediately before commit");
            int decision = Rig.trace.indexOf("engine.commit.after");
            Rig.check(Rig.trace.get(decision + 1).equals("renderer.finish.before"), "finish immediately after scalar commit");
            Rig.nextPacket[0] = 99;
            Rig.check(Rig.packetCopy[0] == 1, "copy detached from JNI candidate source");
            byte[] envelope = new byte[] { 9, 8 };
            Rig.renderer.fire(envelope);
            Rig.check(Rig.operations.equals(List.of(0, 1)), "initial and input use ordinary engine operations");
            Rig.check(Rig.lastInput == envelope && Rig.engineEffects == 2, "concrete callback forwards input exactly once");
            coordinator.close();
            retired(coordinator);
        });
        scenario("environment-only-exact-retained-packet-no-engine-transaction", () -> {
            NativeCoordinatorV2 coordinator = initialized();
            byte[] exact = Rig.rendererPackets.get(0);
            NativeEnvironmentV2 oldEnvironment = Rig.environment;
            coordinator.refreshEnvironment();
            Rig.check(Rig.rendererPackets.get(1) == exact, "environment refresh retains exact packet object");
            Rig.check(Rig.environment != oldEnvironment, "fresh concrete environment capture");
            Rig.check(Rig.engineEffects == 1 && Rig.operations.equals(List.of(0)), "no revision/reducer/engine transaction");
            absent("engine.prepare.before"); absent("engine.commit.before"); absent("engine.abort"); absent("engine.destroy.before");
            ordered("capture.installed", "capture.environment", "renderer.prepare", "environment.current",
                "renderer.attach.return", "renderer.validate", "renderer.finish.before");
            Rig.check(coordinator.hasCommittedPresentation() && Rig.open, "fresh environment published");
        });
    }

    private static void prepareAndAttachmentFaults() {
        String[] stages = { "capture.installed", "capture.environment", "engine.prepare.before",
            "engine.prepare.delivery", "engine.token", "engine.packet.copy", "renderer.prepare",
            "environment.current", "renderer.attach.preflight", "renderer.attach.mutation",
            "renderer.attach.return", "renderer.validate" };
        for (String stage : stages) for (boolean error : new boolean[] { false, true }) {
            scenario("initial-" + stage + (error ? "-Error" : "-exception"), () -> {
                NativeCoordinatorV2 coordinator = fresh();
                (error ? Rig.errors : Rig.faults).add(stage);
                rejected(coordinator::renderInitial);
                Rig.check(Rig.engineEffects == 0, "no engine commit before final validation");
                boolean recoverable = Set.of("engine.packet.copy", "renderer.prepare", "environment.current",
                    "renderer.validate").contains(stage);
                Rig.check(coordinator.isRetired() != recoverable, "precise initial failure disposition");
                if (recoverable) {
                    Rig.check(!coordinator.hasCommittedPresentation(), "initial failure publishes no packet");
                    Rig.check(!Rig.pending, "confirmed abort consumes retained engine candidate");
                    ordered(stage, "engine.abort");
                    Rig.faults.clear(); Rig.errors.clear();
                    coordinator.renderInitial();
                    Rig.check(coordinator.hasCommittedPresentation(), "confirmed initial rejection permits retry");
                } else {
                    retired(coordinator);
                }
                if (stage.startsWith("renderer.attach")) {
                    ordered(stage, "engine.abort", "renderer.dispose.before", "engine.destroy.before");
                    absent("renderer.rollback.before"); absent("renderer.discard.before");
                    Rig.check(Rig.attachConsumed == stage.equals("renderer.attach.mutation"),
                        "test covers both consumed and unconsumed throwing attachment");
                }
            });
        }
        scenario("stale-after-prepare-discards-unattached-candidate", () -> {
            NativeCoordinatorV2 coordinator = fresh();
            Rig.environmentCurrent = false;
            rejected(coordinator::renderInitial);
            ordered("renderer.prepare", "environment.current", "engine.abort", "renderer.discard.before");
            absent("renderer.attach.preflight"); absent("renderer.rollback.before");
            Rig.check(!coordinator.isRetired() && !Rig.pending, "confirmed discard permits initial retry");
        });
        scenario("prepare-null-delivery-retires-without-invented-token", () -> {
            NativeCoordinatorV2 coordinator = fresh(); Rig.nullCandidate = true;
            rejected(coordinator::renderInitial); retired(coordinator); absent("engine.abort");
        });
        scenario("prepare-invalid-zero-token-retires", () -> {
            NativeCoordinatorV2 coordinator = fresh(); Rig.token = 0;
            rejected(coordinator::renderInitial); retired(coordinator); absent("engine.abort");
        });
    }

    private static void commitDispositions() {
        for (int status = 1; status <= 7; status++) {
            final int code = status;
            scenario("known-commit-code-" + code + "-confirmed-abort", () -> {
                NativeCoordinatorV2 coordinator = fresh(); Rig.commitStatus = code;
                rejected(coordinator::renderInitial);
                Rig.check(Rig.engineEffects == 0, "known rejection has no engine effect");
                ordered("engine.commit.after", "engine.abort");
                absent("renderer.finish.before");
                if (code == 2) {
                    retired(coordinator); absent("renderer.rollback.before");
                } else {
                    ordered("engine.abort", "renderer.rollback.before", "renderer.rollback.after");
                    Rig.check(!coordinator.isRetired() && !Rig.pending, "known rejection cleaned up");
                    Rig.commitStatus = 0; coordinator.renderInitial();
                    Rig.check(coordinator.hasCommittedPresentation(), "session reusable after confirmed rejection");
                }
            });
        }
        for (String stage : List.of("engine.commit.before", "engine.commit.after")) {
            for (boolean error : new boolean[] { false, true }) {
                scenario("unknown-commit-" + stage + (error ? "-Error" : "-exception"), () -> {
                    NativeCoordinatorV2 coordinator = fresh();
                    (error ? Rig.errors : Rig.faults).add(stage);
                    rejected(coordinator::renderInitial); retired(coordinator);
                    Rig.check(Rig.engineEffects == (stage.endsWith("after") ? 1 : 0),
                        "test separately simulates unknown outcome before/after effect");
                    absent("engine.abort"); absent("renderer.rollback.before"); absent("renderer.discard.before");
                });
            }
        }
        for (int code : new int[] { -1, 8, Integer.MAX_VALUE }) for (boolean effect : new boolean[] { false, true }) {
            scenario("unexpected-commit-code-" + code + "-effect-" + effect, () -> {
                NativeCoordinatorV2 coordinator = fresh();
                Rig.commitStatus = code; Rig.unknownStatusHasEffect = effect;
                rejected(coordinator::renderInitial); retired(coordinator);
                Rig.check(Rig.engineEffects == (effect ? 1 : 0), "unexpected status may conceal effect");
                absent("engine.abort"); absent("renderer.rollback.before"); absent("renderer.finish.before");
            });
        }
        for (String stage : List.of("renderer.finish.before", "renderer.finish.after")) {
            scenario("successful-commit-then-" + stage + "-failure", () -> {
                NativeCoordinatorV2 coordinator = fresh(); Rig.faults.add(stage);
                rejected(coordinator::renderInitial); retired(coordinator);
                Rig.check(Rig.engineEffects == 1, "engine already committed");
                absent("engine.abort"); absent("renderer.rollback.before"); absent("renderer.discard.before");
            });
        }
    }

    private static void cleanupFaults() {
        for (int code : new int[] { 0, 1, 2, 3, 4, 5, 6, 7, 99 }) {
            scenario("abort-code-" + code, () -> {
                NativeCoordinatorV2 coordinator = fresh(); Rig.faults.add("renderer.validate"); Rig.abortStatus = code;
                rejected(coordinator::renderInitial);
                if (code == 0) Rig.check(!coordinator.isRetired(), "only status zero confirms usable abort");
                else { retired(coordinator); absent("renderer.rollback.before"); }
            });
        }
        for (String stage : List.of("engine.abort", "renderer.rollback.before", "renderer.rollback.after")) {
            for (boolean error : new boolean[] { false, true }) {
                scenario("cleanup-" + stage + (error ? "-Error" : "-exception"), () -> {
                    NativeCoordinatorV2 coordinator = fresh(); Rig.faults.add("renderer.validate");
                    (error ? Rig.errors : Rig.faults).add(stage);
                    Throwable failure = rejected(coordinator::renderInitial); retired(coordinator);
                    Rig.check(failure.getSuppressed().length == 1, "original validation rejection retains cleanup failure");
                });
            }
        }
        for (String stage : List.of("renderer.discard.before", "renderer.discard.after")) {
            scenario("cleanup-" + stage, () -> {
                NativeCoordinatorV2 coordinator = fresh(); Rig.environmentCurrent = false; Rig.faults.add(stage);
                Throwable failure = rejected(coordinator::renderInitial); retired(coordinator);
                Rig.check(failure.getSuppressed().length == 1, "discard failure retained");
                absent("renderer.rollback.before");
            });
        }
        for (String stage : List.of("renderer.attach.preflight", "renderer.attach.mutation")) {
            scenario("attach-throw-and-abort-throw-" + stage, () -> {
                NativeCoordinatorV2 coordinator = fresh(); Rig.faults.add(stage); Rig.faults.add("engine.abort");
                rejected(coordinator::renderInitial); retired(coordinator);
                ordered(stage, "engine.abort", "renderer.dispose.before", "engine.destroy.before");
                absent("renderer.rollback.before"); absent("renderer.discard.before");
            });
        }
        for (String nativeStage : List.of("renderer.dispose.before", "renderer.dispose.after")) {
            for (String engineStage : List.of("engine.destroy.before", "engine.destroy.after")) {
                scenario("both-owner-cleanup-fail-" + nativeStage + "-" + engineStage, () -> {
                    NativeCoordinatorV2 coordinator = initialized(); Rig.faults.add(nativeStage); Rig.errors.add(engineStage);
                    Throwable failure = rejected(coordinator::close); retired(coordinator);
                    Rig.check(failure.getSuppressed().length == 1, "second owner error retained");
                    ordered("renderer.dispose.before", "engine.destroy.before");
                    int traceLength = Rig.trace.size(); rejected(coordinator::close);
                    Rig.check(Rig.trace.size() == traceLength, "closed owner is never disposed twice");
                });
            }
        }
        scenario("transaction-retirement-attempts-both-disposals-despite-errors", () -> {
            NativeCoordinatorV2 coordinator = fresh();
            Rig.faults.addAll(List.of("engine.commit.after", "renderer.dispose.before", "engine.destroy.before"));
            Throwable failure = rejected(coordinator::renderInitial); retired(coordinator);
            Rig.check(failure.getSuppressed().length == 2, "both cleanup failures retained on primary rejection");
        });
    }

    private static void nativeInputAndEnvironment() {
        String[] stages = { "capture.installed", "capture.environment", "engine.prepare.before",
            "engine.packet.copy", "renderer.prepare", "environment.current", "renderer.attach.preflight",
            "renderer.attach.mutation", "renderer.validate", "engine.commit.before" };
        for (String stage : stages) {
            scenario("failed-native-input-" + stage, () -> {
                NativeCoordinatorV2 coordinator = initialized(); Rig.faults.add(stage);
                Rig.renderer.fire(new byte[] { 7 }); retired(coordinator);
                Rig.check(coordinator.lastNativeInputFailure() != null, "native callback records contained rejection");
                Rig.check(Rig.transientText.equals("unacknowledged native input"),
                    "no synthetic text/composition restoration after rejected native mutation");
                if (stage.equals("renderer.validate")) ordered("engine.abort", "renderer.rollback.before", "renderer.dispose.before");
            });
        }
        for (int code = 1; code <= 7; code++) {
            final int status = code;
            scenario("native-input-known-commit-code-" + status + "-still-retires", () -> {
                NativeCoordinatorV2 coordinator = initialized(); Rig.commitStatus = status;
                Rig.renderer.fire(new byte[] { 7 }); retired(coordinator);
                Rig.check(coordinator.lastNativeInputFailure() != null, "scalar rejection diagnostic is observable");
                ordered("engine.abort", "renderer.dispose.before");
            });
        }
        scenario("programmatic-rejected-input-still-throws", () -> {
            NativeCoordinatorV2 coordinator = initialized(); Rig.faults.add("renderer.validate");
            Throwable failure = rejected(() -> coordinator.dispatchInput(new byte[] { 7 })); retired(coordinator);
            Rig.check(failure instanceof Fault && coordinator.lastNativeInputFailure() == null,
                "programmatic rejection stays explicit and distinct from callback diagnostic");
        });
        scenario("native-callback-stale-before-attach-discards-then-retires", () -> {
            NativeCoordinatorV2 coordinator = initialized(); Rig.environmentCurrent = false;
            Rig.renderer.fire(new byte[] { 7 }); retired(coordinator);
            ordered("engine.abort", "renderer.discard.before", "renderer.dispose.before");
            Rig.check(coordinator.lastNativeInputFailure() != null, "confirmed discard does not reopen unacknowledged native input");
        });
        scenario("native-callback-propagates-discard-Error", () -> {
            NativeCoordinatorV2 coordinator = initialized(); Rig.environmentCurrent = false;
            Rig.errors.add("renderer.discard.before");
            Throwable failure = rejected(() -> Rig.renderer.fire(new byte[] { 7 })); retired(coordinator);
            Rig.check(failure instanceof OutOfMemoryError, "unattached discard Error/OOM propagates");
        });
        for (String stage : List.of("engine.packet.copy", "engine.commit.after", "renderer.finish.before")) {
            scenario("native-callback-propagates-Error-" + stage, () -> {
                NativeCoordinatorV2 coordinator = initialized(); Rig.errors.add(stage);
                Throwable failure = rejected(() -> Rig.renderer.fire(new byte[] { 7 })); retired(coordinator);
                Rig.check(failure instanceof OutOfMemoryError, "Error/OOM never contained as ordinary input failure");
            });
        }
        for (String stage : List.of("engine.abort", "renderer.rollback.before", "renderer.dispose.before", "engine.destroy.before")) {
            scenario("native-callback-propagates-suppressed-cleanup-Error-" + stage, () -> {
                NativeCoordinatorV2 coordinator = initialized();
                Rig.faults.add("renderer.validate"); Rig.errors.add(stage);
                Throwable failure = rejected(() -> Rig.renderer.fire(new byte[] { 7 })); retired(coordinator);
                Rig.check(failure instanceof OutOfMemoryError, "cleanup Error/OOM must propagate through RuntimeException wrapper");
                Rig.check(coordinator.lastNativeInputFailure() != null, "original retired rejection diagnostic retained");
            });
        }
        for (String stage : List.of("renderer.prepare", "renderer.validate", "renderer.finish.before")) {
            scenario("unexpected-reentrant-native-callback-" + stage, () -> {
                NativeCoordinatorV2 coordinator = fresh(); Rig.hookStage = stage;
                Rig.hook = () -> Rig.renderer.fire(new byte[] { 7 });
                Throwable failure = rejected(coordinator::renderInitial); retired(coordinator);
                Rig.check(failure.getMessage().contains("reentrant native input"), "unexpected reentrant callback propagates");
                Rig.check(coordinator.lastNativeInputFailure() == null, "unexpected reentrancy is never contained as edit rejection");
                Rig.check(java.util.Collections.frequency(Rig.trace, "engine.destroy.before") == 1,
                    "outer rejection never disposes already retired owners again");
            });
        }
        for (String stage : List.of("capture.installed", "capture.environment", "renderer.prepare", "environment.current",
            "renderer.attach.preflight", "renderer.attach.mutation", "renderer.validate", "renderer.finish.before", "renderer.finish.after")) {
            scenario("failed-environment-only-" + stage, () -> {
                NativeCoordinatorV2 coordinator = initialized(); Rig.faults.add(stage);
                rejected(coordinator::refreshEnvironment); retired(coordinator);
                absent("engine.prepare.before"); absent("engine.commit.before"); absent("engine.abort");
                Rig.check(Rig.engineEffects == 1, "environment rejection does not generate a revision");
                if (stage.startsWith("renderer.attach") || stage.startsWith("renderer.finish")) {
                    absent("renderer.discard.before"); absent("renderer.rollback.before");
                }
            });
        }
        scenario("environment-only-stale-unattached-discard", () -> {
            NativeCoordinatorV2 coordinator = initialized(); Rig.environmentCurrent = false;
            rejected(coordinator::refreshEnvironment); retired(coordinator);
            ordered("environment.current", "renderer.discard.before", "renderer.dispose.before");
            absent("engine.abort"); absent("engine.prepare.before");
        });
        scenario("environment-only-rollback-failure-still-disposes-both", () -> {
            NativeCoordinatorV2 coordinator = initialized();
            Rig.faults.addAll(List.of("renderer.validate", "renderer.rollback.before"));
            Throwable failure = rejected(coordinator::refreshEnvironment); retired(coordinator);
            Rig.check(failure.getSuppressed().length == 1, "environment rollback failure retained");
        });
    }

    private static void lifecycle() {
        scenario("closed-and-uninitialized-operation-rejection", () -> {
            NativeCoordinatorV2 coordinator = fresh();
            rejected(() -> coordinator.dispatchInput(new byte[] { 1 })); rejected(coordinator::refreshEnvironment);
            Rig.check(!coordinator.isRetired() && Rig.operations.isEmpty(), "precondition rejection makes no engine call");
            coordinator.renderInitial(); int count = Rig.operations.size();
            rejected(coordinator::renderInitial);
            Rig.check(Rig.operations.size() == count && coordinator.hasCommittedPresentation(), "duplicate initial render rejected");
            coordinator.close(); int traceLength = Rig.trace.size();
            rejected(coordinator::renderInitial); rejected(coordinator::refreshEnvironment);
            rejected(() -> coordinator.dispatchInput(new byte[] { 2 })); rejected(coordinator::close);
            rejected(() -> Rig.renderer.fire(new byte[] { 3 }));
            Rig.check(Rig.trace.size() == traceLength, "retired calls never reach either owner");
        });
        for (String action : List.of("initial", "input", "environment", "close")) {
            for (String stage : List.of("capture.installed", "renderer.prepare", "renderer.validate", "renderer.finish.before")) {
                scenario("reentrant-" + action + "-during-" + stage, () -> {
                    NativeCoordinatorV2 coordinator = fresh();
                    Rig.hookStage = stage;
                    Rig.hook = () -> {
                        Runnable call = switch (action) {
                            case "initial" -> coordinator::renderInitial;
                            case "input" -> () -> coordinator.dispatchInput(new byte[] { 1 });
                            case "environment" -> coordinator::refreshEnvironment;
                            case "close" -> coordinator::close;
                            default -> throw new AssertionError(action);
                        };
                        Throwable failure = rejected(call);
                        Rig.check(failure.getMessage().contains("reentrant"), "reentrant mutation rejected");
                    };
                    coordinator.renderInitial();
                    Rig.check(coordinator.hasCommittedPresentation() && Rig.engineEffects == 1, "outer transaction preserved");
                });
            }
        }
        scenario("main-looper-confinement-including-lifecycle-and-queries", () -> {
            NativeCoordinatorV2 coordinator = initialized();
            AtomicReference<Throwable> unexpected = new AtomicReference<>();
            Thread worker = new Thread(() -> {
                try {
                    for (Runnable operation : Arrays.<Runnable>asList(coordinator::renderInitial,
                        () -> coordinator.dispatchInput(new byte[] { 1 }), coordinator::refreshEnvironment,
                        coordinator::close, () -> coordinator.isRetired(), () -> coordinator.hasCommittedPresentation(),
                        () -> coordinator.lastNativeInputFailure(),
                        () -> new NativeCoordinatorV2(new Activity(), new FrameLayout(new Activity())))) {
                        Throwable failure = rejected(operation);
                        Rig.check(failure.getMessage().contains("main Looper"), "off-main rejection before leaf call");
                    }
                } catch (Throwable failure) { unexpected.set(failure); }
            }, "test-only-non-main-thread");
            worker.start();
            try { worker.join(); }
            catch (InterruptedException interrupted) { throw new AssertionError(interrupted); }
            if (unexpected.get() != null) throw new AssertionError(unexpected.get());
            Rig.check(Rig.trace.isEmpty() && coordinator.hasCommittedPresentation(), "no off-main owner mutation");
        });
        scenario("creation-failure-disposes-native-owner", () -> {
            Rig.faults.add("engine.create"); rejected(NativeCoordinatorV2HostTests::fresh);
            ordered("engine.create", "renderer.dispose.before"); absent("engine.destroy.before");
        });
        scenario("creation-zero-handle-disposes-native-owner", () -> {
            Rig.createHandle = 0; rejected(NativeCoordinatorV2HostTests::fresh);
            ordered("engine.create", "renderer.dispose.before"); absent("engine.destroy.before");
        });
    }

    public static void main(String[] arguments) {
        // Initialize the test-only main identity here, before any worker is created.
        android.os.Looper.getMainLooper();
        success(); prepareAndAttachmentFaults(); commitDispositions(); cleanupFaults();
        nativeInputAndEnvironment(); lifecycle();
        System.out.println("PASS production-coordinator-bytecode decision scenarios=" + scenarios + " checks=" + checks);
        System.out.println("SCOPE host JVM decision behavior with explicit test-only leaves; Android/JNI/Swift/view/IME/native acceptance NOT RUN");
    }
    private NativeCoordinatorV2HostTests() {}
}
