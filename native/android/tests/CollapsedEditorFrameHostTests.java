package dev.mixer.android;

import android.app.Activity;
import android.graphics.Insets;
import android.os.Handler;
import android.text.Layout;
import android.view.WindowInsets;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.FrameLayout;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

/** Exercises Android's cached layout path using the concrete renderer and editor. */
public final class CollapsedEditorFrameHostTests {
    private static final String RESPONSIBLE = "task.responsible";
    private static final String PREFIX = "Measured text before the editor section";
    private static final String SCOPE = "Saved local records only. Unsaved input and photo files are not included. Nothing is uploaded by FieldLog.";
    private static byte[] descriptor;

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static Map<String, Object> text(String id, String content) {
        return Json.map("id", id, "kind", "text", "children", List.of(), "actions", List.of(),
            "properties", Json.map("text", content, "style", "body", "selectable", false));
    }

    private static void identity(Map<String, Object> packet, String id, String generation) {
        Json.array(packet.get("identities")).add(Json.map("id", id, "generation", new Json.Num(generation)));
    }

    private record Frames(byte[] opened, byte[] busy, byte[] completed, String progress) {
        static Frames read(Path input, Path capture) throws Exception {
            if (capture != null) {
                return new Frames(Files.readAllBytes(capture.resolve("opened.json")),
                    Files.readAllBytes(capture.resolve("busy.json")),
                    Files.readAllBytes(capture.resolve("completed.json")), "1 of 1 tasks completed");
            }
            var p = CompleteHandoffHostTests.packet(Files.readAllBytes(input.resolve("before-public-reset/00.json")));
            Json.array(CompleteHandoffHostTests.node(p, "workspace.summary").get("children")).add(text("test.prefix", PREFIX));
            identity(p, "test.prefix", "12");
            byte[] opened = CompleteHandoffHostTests.encode(p);
            var list = Json.array(CompleteHandoffHostTests.node(p, "task.form").get("children"));
            list.add(2, Json.map("id", "test.feedback", "kind", "section", "actions", List.of(),
                "properties", Json.map(), "children", List.of(text("test.feedback.message", "Saving…"))));
            identity(p, "test.feedback", "13");
            identity(p, "test.feedback.message", "14");
            change(p, "2", true);
            byte[] busy = CompleteHandoffHostTests.encode(p);
            change(p, "3", false);
            Json.object(CompleteHandoffHostTests.node(p, "workspace.progress").get("properties")).put("text", "Completed");
            return new Frames(opened, busy, CompleteHandoffHostTests.encode(p), "Completed");
        }
        private static void change(Map<String, Object> packet, String revision, boolean disabled) {
            Json.object(packet.get("document")).put("revision", new Json.Num(revision));
            for (String id : List.of("task.title", RESPONSIBLE)) {
                Json.object(CompleteHandoffHostTests.node(packet, id).get("properties")).put("disabled", disabled);
            }
        }
    }

    private static void run(Frames frames, String mode, boolean baseline) throws Exception {
        ConcreteHostProbe.reset();
        Activity activity = new Activity();
        activity.resources.metrics.density = 2.625f;
        activity.resources.metrics.scaledDensity = 2.625f;
        activity.resources.metrics.densityDpi = 420;
        activity.assets.put(InstalledAppearanceV2.DESCRIPTOR, descriptor);
        FrameLayout root = new FrameLayout(activity);
        root.rootInsets = new WindowInsets(Insets.of(0, 136, 0, 0));
        root.layout(0, 0, 1080, 2337);
        activity.window.decor.layout(0, 0, 1080, 2337);
        root.hostAttach(new Object());
        List<byte[]> events = new ArrayList<>();
        var owner = NativeOwnerV2.external(activity, root, new ExternalFrameSourceV2(events::add),
            AndroidUIProfile.MEASURED_MULTILINE_LONG_NOTES_V4);
        try {
            owner.installExternal(frames.opened(), descriptor);
            var renderer = (NativeRenderer) CompleteHandoffHostTests.get(
                CompleteHandoffHostTests.get(owner, "coordinator"), "renderer");
            var oldPacket = renderer.packet;
            var section = renderer.view("task.fields");
            var responsible = (NativeAppearanceViewsV2.NativeField) renderer.view(RESPONSIBLE);
            int[] sectionBounds = ContainerFrameWitnessHostTests.local(section);
            check(Arrays.equals(MeasuredAcknowledgmentPreservationHostTests.pos(responsible), new int[]{84, 1183})
                && responsible.getWidth() == 912 && responsible.getHeight() == 116, "expanded field bounds");
            check(ContainerFrameWitnessHostTests.sourceFrame(oldPacket, renderer.inspectV2()), "expanded frame witness");

            renderer.view("task.form").scrollTo(0, 356);
            check(renderer.inspectV2().get("task.screen").geometry.collapsed, "navigation collapsed");
            check(Arrays.equals(sectionBounds, ContainerFrameWitnessHostTests.local(section)), "section pixel bounds unchanged");
            check(ContainerFrameWitnessHostTests.sourceFrame(oldPacket, renderer.inspectV2()) != baseline, "collapsed frame witness");
            int expectedY = baseline ? 1183 : 1184;
            int expectedHeight = baseline ? 116 : 115;
            check(Arrays.equals(MeasuredAcknowledgmentPreservationHostTests.pos(responsible), new int[]{84, expectedY})
                && responsible.getWidth() == 912 && responsible.getHeight() == expectedHeight, "collapsed field bounds");

            InputConnection connection = null;
            if (mode.equals("focused") || mode.equals("composing")) {
                check(responsible.requestFocus() && responsible.hasFocus(), "focused foreign editor");
                if (mode.equals("composing")) {
                    connection = responsible.onCreateInputConnection(new EditorInfo());
                    check(connection != null && connection.setComposingText("Local draft", 1), "live foreign composition");
                }
            } else {
                check(responsible.modelHandoffConsumed() && !responsible.hasLiveTarget(), "settled predecessor");
                if (mode.equals("tampered")) {
                    MeasuredAcknowledgmentHostTests.frame(responsible, "top", -1);
                    MeasuredAcknowledgmentHostTests.frame(responsible, "bottom", 1);
                }
            }

            boolean accepted = !baseline && mode.equals("passive");
            int beforeEvents = events.size();
            try {
                owner.installExternal(frames.busy(), descriptor);
                check(accepted, "unexpected publication");
            } catch (IllegalStateException failure) {
                check(!accepted && owner.cleanupLedger().primary() instanceof AppearanceDescriptorV2.Failure error
                    && error.code == AppearanceDescriptorV2.Error.unsupportedNativeOperation, "expected preflight refusal");
            }
            if (accepted) {
                check(owner.hasCommittedPresentation() && renderer.view(RESPONSIBLE) == responsible
                    && !responsible.isEnabled(), "busy frame disabled the retained editor");
                owner.installExternal(frames.completed(), descriptor);
                check(owner.hasCommittedPresentation() && renderer.view(RESPONSIBLE) == responsible
                    && responsible.isEnabled(), "completion reenabled the retained editor");
                check(renderer.packet.nodes.get("workspace.progress").text("text", "").equals(frames.progress()),
                    "completed progress published");
                if (frames.progress().startsWith("1 of")) {
                    check(renderer.packet.nodes.values().stream().anyMatch(n -> n.text("label", "").equals("Reopen: MixerVerified")),
                        "reopen button published");
                }
                check(renderer.view("task.form").getScrollY() == 356, "scroll preserved");
            } else {
                check(!owner.hasCommittedPresentation() && renderer.packet == oldPacket, "refusal kept candidate unpublished");
                if (connection != null) check(!connection.commitText("Late", 1), "retired connection fenced");
            }
            check(events.size() == beforeEvents, "transition emitted no editor events");
            System.out.printf("PASS %s collapsed frame [84,%d] 912x%d, baseline=%s, published=%s%n",
                mode, expectedY, expectedHeight, baseline, accepted);
        } finally {
            owner.close();
            ((Handler) CompleteHandoffHostTests.get(owner, "handler")).drainAll(8);
        }
    }

    public static void main(String[] args) throws Exception {
        System.setProperty("mixer.host.cachedLayout", "true");
        Path fixtures = Path.of(args[0]);
        descriptor = Files.readAllBytes(fixtures.resolve("descriptor.json"));
        boolean baseline = args[1].equals("baseline");
        Path capture = args.length == 3 ? Path.of(args[2]) : null;
        var frames = Frames.read(fixtures, capture);
        Layout.hostDefaultHeight = 52;
        Layout.hostHeights.put(PREFIX, 429);
        Layout.hostHeights.put(SCOPE, 156);
        Layout.hostHeights.put("Add a task to start your checklist.", 900);
        for (String mode : baseline ? List.of("passive") : List.of("passive", "focused", "composing", "tampered")) {
            run(frames, mode, baseline);
        }
    }
}
