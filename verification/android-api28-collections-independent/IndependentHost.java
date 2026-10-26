package dev.mixer.android;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/** Fresh reviewer tests of exact pure Java sources and JDK behavior, never D8/Android execution. */
final class IndependentHost {
    private static int assertions;
    private static void check(boolean value) { assertions++; if (!value) throw new AssertionError("assertion " + assertions); }
    private static void throwsType(Class<? extends Throwable> type, Runnable body) {
        assertions++;
        try { body.run(); } catch (Throwable failure) { if (type.isInstance(failure)) return; throw failure; }
        throw new AssertionError("expected " + type.getName());
    }
    private static void sameFailure(RuntimeException expected, Runnable body) {
        assertions++;
        try { body.run(); } catch (RuntimeException failure) { if (failure == expected) return; throw failure; }
        throw new AssertionError("missing original thread failure");
    }
    public static void main(String[] arguments) {
        var p = new AppearanceGeometryV2.Point(1, 2);
        var q = new AppearanceGeometryV2.Point(3, 4);
        var input = new ArrayList<>(List.of(p, q, p));
        var command = new AppearanceGeometryV2.Command(AppearanceGeometryV2.Op.cubic, input);
        input.clear();
        check(command.points().size() == 3);
        check(command.points().get(0) == p && command.points().get(1) == q && command.points().get(2) == p);
        throwsType(UnsupportedOperationException.class, () -> command.points().clear());
        throwsType(UnsupportedOperationException.class, () -> command.points().set(0, q));
        throwsType(NullPointerException.class, () -> new AppearanceGeometryV2.Command(AppearanceGeometryV2.Op.move, null));
        var withNull = new ArrayList<AppearanceGeometryV2.Point>(); withNull.add(null);
        throwsType(NullPointerException.class, () -> new AppearanceGeometryV2.Command(AppearanceGeometryV2.Op.move, withNull));
        var zero = AppearanceGeometryV2.group(0, 64, 0);
        check(zero.commands.isEmpty() && zero.width64 == 0 && zero.height64 == 64);
        var track = AppearanceGeometryV2.track();
        check(!track.commands.isEmpty());
        check(track.commands.get(0).op() == AppearanceGeometryV2.Op.move);
        check(track.commands.get(track.commands.size() - 1).op() == AppearanceGeometryV2.Op.close);
        check(track.commands.get(track.commands.size() - 1).points().isEmpty());
        throwsType(AppearanceGeometryV2.Failure.class, () -> AppearanceGeometryV2.group(-1, 0, -1));

        String packet = """
            {"schemaVersion":1,"document":{"schemaVersion":1,"revision":1,"root":
              {"id":"root","kind":"vStack","properties":{},"actions":[],"children":[
                {"id":"child","kind":"vStack","properties":{},"actions":[],"children":[
                  {"id":"leaf","kind":"text","properties":{"text":"hello"},"actions":[],"children":[]}
                ]}
              ]}},"identities":[{"id":"root","generation":1},{"id":"child","generation":2},{"id":"leaf","generation":3}]}
            """;
        byte[] bytes = packet.getBytes(StandardCharsets.UTF_8);
        UiPacket decoded = UiPacket.decode(bytes);
        check(decoded.root.children.size() == 1);
        check(decoded.root.children.get(0).children.size() == 1);
        check(decoded.root.children.get(0) == decoded.nodes.get("child"));
        check(decoded.root.children.get(0).children.get(0) == decoded.nodes.get("leaf"));
        check(decoded.nodes.get("leaf").text("text", "") .equals("hello"));
        bytes[0] = 0;
        check(decoded.nodes.size() == 3);
        throwsType(UnsupportedOperationException.class, () -> decoded.root.children.clear());
        throwsType(UnsupportedOperationException.class, () -> decoded.nodes.clear());
        throwsType(UnsupportedOperationException.class, () -> decoded.nodes.get("leaf").properties.put("text", "changed"));
        throwsType(UnsupportedOperationException.class, () -> decoded.nodes.get("leaf").actions.put("activate", "x"));

        Object activity = new Object(), root = new Object(), window = new Object(), resource = new Object();
        boolean[] block = {false};
        RuntimeException original = new IllegalStateException("independent-thread-check");
        OwnerLifecycleV2 core = new OwnerLifecycleV2(() -> { if (block[0]) throw original; }, activity, root);
        var owner = core.lifetime();
        var facts = new OwnerLifecycleV2.WindowFacts(activity, root, false, true, window, 80, 90, true);
        check(core.windowChanged(null, facts).isEmpty());
        check(core.drain(null, null, facts).isEmpty());
        check(core.focusChanged(null, true).isEmpty());
        check(core.pause(null).isEmpty());
        check(core.stop(null).isEmpty());
        check(core.resume(null).isEmpty());
        check(core.dispatchInput(null, null).isEmpty());
        check(core.complete(null, resource, true, null).isEmpty());
        check(core.invalidate(null).isEmpty());
        check(core.close(null).isEmpty());
        block[0] = true;
        sameFailure(original, () -> core.windowChanged(null, null));
        sameFailure(original, () -> core.drain(null, null, null));
        sameFailure(original, () -> core.focusChanged(null, true));
        sameFailure(original, () -> core.pause(null));
        sameFailure(original, () -> core.stop(null));
        sameFailure(original, () -> core.resume(null));
        sameFailure(original, () -> core.dispatchInput(null, null));
        sameFailure(original, () -> core.complete(null, null, false, null));
        sameFailure(original, () -> core.invalidate(null));
        sameFailure(original, () -> core.close(null));
        block[0] = false;
        var queued = core.windowChanged(owner, facts);
        check(queued.size() == 1 && queued.get(0).kind() == OwnerLifecycleV2.Kind.QUEUE_DRAIN);
        check(core.snapshot().pendingDrain() == queued.get(0).token());
        var opening = core.drain(owner, queued.get(0).token(), facts);
        check(opening.size() == 1 && opening.get(0).kind() == OwnerLifecycleV2.Kind.OPEN_INITIAL);
        check(core.snapshot().operation() == opening.get(0).token());
        throwsType(UnsupportedOperationException.class, () -> opening.clear());
        var completed = core.complete(opening.get(0).token(), resource, true, null);
        check(completed.isEmpty());
        check(core.snapshot().phase() == OwnerLifecycleV2.Phase.LIVE && core.snapshot().resource() == resource);
        var closed = core.close(owner);
        check(closed.size() == 4 && closed.size() <= OwnerLifecycleV2.MAX_DECISIONS);
        check(closed.get(0).kind() == OwnerLifecycleV2.Kind.SEAL && closed.get(0).token() == owner);
        check(closed.get(1).kind() == OwnerLifecycleV2.Kind.CANCEL_QUEUED);
        check(closed.get(2).kind() == OwnerLifecycleV2.Kind.UNREGISTER);
        check(closed.get(3).kind() == OwnerLifecycleV2.Kind.CLOSE && closed.get(3).resource() == resource);
        check(opening.size() == 1 && queued.size() == 1);
        check(core.snapshot().phase() == OwnerLifecycleV2.Phase.RETIRED);
        throwsType(UnsupportedOperationException.class, () -> closed.remove(0));
        int sourceAssertions = assertions;

        // This is a distinct counterexample, not a pass for universal factory equivalence.
        throwsType(UnsupportedOperationException.class, () -> List.of().clear());
        throwsType(UnsupportedOperationException.class, () -> List.of().removeIf(value -> false));
        throwsType(UnsupportedOperationException.class, () -> Map.of().clear());
        throwsType(UnsupportedOperationException.class, () -> Map.of().remove("absent"));
        Collections.emptyList().clear(); check(true);
        check(!Collections.emptyList().removeIf(value -> false));
        Collections.emptyMap().clear(); check(true);
        check(Collections.emptyMap().remove("absent") == null);
        System.out.println("PASS " + sourceAssertions + " exact pure-source host assertions; " + (assertions - sourceAssertions)
            + " separate JDK empty-mutator mismatch assertions; no Android or D8 helper execution");
    }
}
