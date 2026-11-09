package dev.mixer.android;

import android.app.Activity;
import android.os.Handler;
import android.text.Editable;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.TextView;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;

/** Independent modeled host lifecycle. Model frames are supplied, never persisted. */
public final class TwoFieldSavingReviewR5Tests {
    private static int checks;
    private static byte[] descriptor;
    private static void require(boolean ok, String reason) {
        checks++;
        if (!ok) throw new AssertionError(reason);
    }
    private static Object inspect(Object object, String name) {
        try {
            Field field = object.getClass().getDeclaredField(name);
            field.setAccessible(true);
            return field.get(object);
        } catch (ReflectiveOperationException error) { throw new AssertionError(error); }
    }
    private static void encode(StringBuilder out, Object value) {
        if (value instanceof Map<?, ?> map) {
            out.append('{'); boolean comma = false;
            for (var entry : map.entrySet()) {
                if (comma) out.append(','); comma = true;
                Json.write(out, entry.getKey()); out.append(':'); encode(out, entry.getValue());
            }
            out.append('}');
        } else if (value instanceof List<?> list) {
            out.append('[');
            for (int i = 0; i < list.size(); i++) { if (i > 0) out.append(','); encode(out, list.get(i)); }
            out.append(']');
        } else Json.write(out, value);
    }
    private static Object node(String id, String kind, Map<String,Object> properties, List<Object> children, String action) {
        List<Object> actions = kind.equals("button") ? List.of(Json.map("id", action, "event", "activate"))
            : kind.equals("textField") ? List.of(Json.map("id", id + "Change", "event", "textChange"), Json.map("id", id + "Submit", "event", "submit")) : List.of();
        return Json.map("id", id, "kind", kind, "properties", properties, "children", children, "actions", actions);
    }
    private static final Map<String,Integer> GENERATIONS = Map.of("root", 1, "status", 2, "fieldA", 3, "fieldB", 4, "button", 5, "list", 6, "savedA", 7, "savedB", 8);
    private static void identities(Object value, List<Object> result) {
        var n = Json.object(value); String id = (String)n.get("id");
        result.add(Json.map("id", id, "generation", new Json.Num(Integer.toString(GENERATIONS.get(id)))));
        for (Object child : Json.array(n.get("children"))) identities(child, result);
    }
    private static byte[] packet(int revision, boolean aFirst, String phase, String a, String b) {
        List<Object> children = new ArrayList<>();
        children.add(node("status", "text", Json.map("text", phase.equals("saving") ? "Saving…" : phase.equals("list") ? "Saved" : "Edit"), List.of(), ""));
        List<Object> fields = new ArrayList<>();
        for (String id : aFirst ? List.of("fieldA", "fieldB") : List.of("fieldB", "fieldA")) {
            String value = id.equals("fieldA") ? a : b;
            fields.add(phase.equals("list")
                ? node(id.equals("fieldA") ? "savedA" : "savedB", "text", Json.map("text", value), List.of(), "")
                : node(id, "textField", Json.map("label", id, "value", value, "axis", "vertical", "disabled", phase.equals("saving")), List.of(), ""));
        }
        if (phase.equals("list")) children.add(node("list", "list", Map.of(), fields, "")); else children.addAll(fields);
        children.add(node("button", "button", Json.map("label", phase.equals("saving") ? "Model completion" : phase.equals("list") ? "Reopen" : "Add"), List.of(), phase + "Action"));
        Object root = node("root", "vStack", Map.of(), children, ""); List<Object> ids = new ArrayList<>(); identities(root, ids);
        StringBuilder out = new StringBuilder(); encode(out, Json.map("schemaVersion", new Json.Num("1"), "document", Json.map("schemaVersion", new Json.Num("1"), "revision", new Json.Num(Integer.toString(revision)), "root", root), "identities", ids));
        return out.toString().getBytes(StandardCharsets.UTF_8);
    }
    private static final class Fixture implements AutoCloseable {
        final NativeOwnerV2 owner;
        final Handler queue;
        final Object coordinator;
        final NativeRenderer renderer;
        final boolean aFirst;
        Fixture(boolean aFirst) {
            this.aFirst = aFirst;
            ConcreteHostProbe.reset(); NativeBridge.reset();
            Activity activity = new Activity(); FrameLayout root = new FrameLayout(activity);
            activity.assets.put(InstalledAppearanceV2.DESCRIPTOR, descriptor);
            root.layout(0, 0, 1000, 1500); activity.window.getDecorView().layout(0, 0, 1000, 1500); root.hostAttach(new Object());
            byte[] initial = packet(1, aFirst, "edit", "First", "Second"); NativeBridge.preparedPacket = initial;
            owner = new NativeOwnerV2(activity, root, null); queue = (Handler)inspect(owner, "handler");
            owner.onResume(); owner.start(); queue.drainAll(4);
            coordinator = inspect(owner, "coordinator"); renderer = (NativeRenderer)inspect(coordinator, "renderer");
            stage(1, initial, "initial");
        }
        EditText editor(String id) { return (EditText)renderer.view(id); }
        void stage(int revision, byte[] expected, String label) {
            var fence = (NativeOwnerV2.Fence)inspect(owner, "fence");
            require(!fence.terminal && owner.hasCommittedPresentation(), label + " live: " + owner.cleanupLedger().primary());
            require(renderer.packet.revision.equals(Integer.toString(revision)), label + " packet revision");
            require(Arrays.equals((byte[])inspect(renderer, "v2PacketBytes"), expected), label + " exact packet bytes");
            require(NativeBridge.prepareCalls == revision && NativeBridge.commitCalls == revision && NativeBridge.abortCalls == 0, label + " exactly one prepare/commit per event");
            require(NativeBridge.createCalls == 1 && NativeBridge.destroyCalls == 0 && inspect(owner, "coordinator") == coordinator, label + " owner/coordinator unchanged");
            require(queue.queued() == 0 && inspect(owner, "pendingCloseResource") == null && inspect(owner, "pendingCloseToken") == null, label + " no deferred cleanup");
            for (String counter : List.of("outstandingFieldTransitions", "outstandingEditorNativeCalls", "outstandingFieldPreservations")) require((Integer)inspect(renderer, counter) == 0, label + " zero " + counter);
        }
        void event(int priorRevision, String id, String event, String value) {
            var input = Json.object(Json.parse(NativeBridge.lastInput));
            require(((Json.Num)input.get("revision")).raw.equals(Integer.toString(priorRevision)), "event revision, no replay");
            require(Json.object(input.get("identity")).get("id").equals(id) && input.get("event").equals(event), "exact event identity/type");
            require(java.util.Objects.equals(input.get("value"), value), "exact event value");
            System.out.println("EVENT " + new String(NativeBridge.lastInput, StandardCharsets.UTF_8));
        }
        void publish(int revision, String phase, String a, String b) {
            Object previous = renderer.packet;
            String previousPhase = revision == 3 ? "edit" : revision == 4 ? "saving" : "list";
            require(renderer.packet.nodes.get("button").actions.get("activate").equals(previousPhase + "Action"), "current modeled action binding");
            byte[] next = packet(revision, aFirst, phase, a, b); NativeBridge.preparedPacket = next;
            renderer.view("button").performClick(); queue.drainAll(4);
            stage(revision, next, phase); require(renderer.packet != previous, phase + " publishes new packet"); event(revision - 1, "button", "activate", null);
        }
        @Override public void close() {
            owner.close(); queue.drainAll(4);
            require(NativeBridge.destroyCalls == 1 && queue.queued() == 0, "ordinary final disposal exactly once");
            require(owner.cleanupLedger().coordinator() == NativeOwnerV2.Outcome.RETURNED, "normal cleanup ledger returned");
            require(inspect(owner, "pendingCloseResource") == null && inspect(owner, "pendingCloseToken") == null, "normal cleanup owns no pending resource");
            ConcreteHostProbe.reset();
        }
    }
    private static void stale(InputConnection old, int revision) {
        int delegated = ConcreteHostProbe.count("BaseInputConnection.commitText", "entry");
        require(!old.commitText("late replay", 1) && !old.setSelection(0, 0), "retired editor stays fenced");
        require(ConcreteHostProbe.count("BaseInputConnection.commitText", "entry") == delegated, "stale commit not forwarded");
        require(NativeBridge.prepareCalls == revision && NativeBridge.commitCalls == revision, "stale editor emits no event");
        require(ConcreteHostProbe.count("BaseInputConnection.closeConnection", "entry") == 1, "old target retired exactly once");
    }
    private static void sequence(boolean aFirst, String active) {
        int beforeChecks = checks;
        try (Fixture f = new Fixture(aFirst)) {
            EditText a = f.editor("fieldA"), b = f.editor("fieldB"), editor = f.editor(active);
            var recordA = f.renderer.inspectV2().get("fieldA"); var recordB = f.renderer.inspectV2().get("fieldB");
            String draft = "New task\n世界 😀 مرحبا";
            String modelA = active.equals("fieldA") ? draft : "First", modelB = active.equals("fieldB") ? draft : "Second";
            editor.requestFocus(); editor.setSelection(0, editor.getText().length());
            InputConnection old = editor.onCreateInputConnection(new EditorInfo()); require(old != null, "active editor acquired");
            byte[] echo = packet(2, aFirst, "edit", modelA, modelB); NativeBridge.preparedPacket = echo;
            require(old.setComposingText(draft, 1), "multiline composition accepted"); f.queue.drainAll(4); f.stage(2, echo, "composition"); f.event(1, active, "textChange", draft);
            Editable bufferA = a.getText(), bufferB = b.getText();
            require(BaseInputConnection.getComposingSpanStart(editor.getText()) >= 0, "active composing span exists");
            f.publish(3, "saving", modelA, modelB);
            require(f.renderer.inspectV2().get("fieldA") == recordA && f.renderer.inspectV2().get("fieldB") == recordB, "Saving retains both records");
            require(f.editor("fieldA") == a && f.editor("fieldB") == b && a.getText() == bufferA && b.getText() == bufferB, "Saving retains exact two fields and buffers");
            require(!a.isEnabled() && !b.isEnabled() && !a.hasFocus() && !b.hasFocus(), "Saving disables both and retires focus");
            require(a.getText().toString().equals(modelA) && b.getText().toString().equals(modelB), "Saving retains both model values");
            require(BaseInputConnection.getComposingSpanStart(editor.getText()) == -1, "retirement finishes composition");
            require(a.onCreateInputConnection(new EditorInfo()) == null && b.onCreateInputConnection(new EditorInfo()) == null, "disabled fields cannot reacquire"); stale(old, 3);
            f.publish(4, "list", modelA, modelB);
            require(!f.renderer.inspectV2().containsKey("fieldA") && !f.renderer.inspectV2().containsKey("fieldB"), "completion removes both editors");
            require(f.renderer.packet.nodes.get("list").kind.equals("list"), "modeled completion is a list");
            require(((TextView)f.renderer.view("savedA")).getText().toString().equals(modelA) && ((TextView)f.renderer.view("savedB")).getText().toString().equals(modelB), "list renders both saved model values"); stale(old, 4);
            f.publish(5, "edit", modelA, modelB);
            EditText reopenedA = f.editor("fieldA"), reopenedB = f.editor("fieldB");
            require(reopenedA != a && reopenedB != b && reopenedA.isEnabled() && reopenedB.isEnabled(), "reopen creates two enabled fields");
            require(reopenedA.getText().toString().equals(modelA) && reopenedB.getText().toString().equals(modelB), "reopened values match modeled completion");
            EditText reopened = f.editor(active); reopened.requestFocus(); reopened.setSelection(reopened.getText().length());
            InputConnection fresh = reopened.onCreateInputConnection(new EditorInfo()); require(fresh != null && fresh != old && fresh.setSelection(0, 1), "reopened fresh editor operates"); stale(old, 5);
            require(NativeBridge.createCalls == 1 && NativeBridge.destroyCalls == 0, "no reset across entire sequence");
            System.out.println("PASS two-field order=" + (aFirst ? "A,B" : "B,A") + " active=" + active + " revisions=1,2,3,4,5 prepare=5 commit=5 oldCloses=1 create=1 destroy=0 holds=0 queued=0 checks=" + (checks-beforeChecks));
        }
    }
    public static void main(String[] args) throws Exception {
        descriptor = Files.readAllBytes(Path.of(args[0])); NativeBridge.testProfile = AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3;
        for (boolean aFirst : List.of(true, false)) for (String active : List.of("fieldA", "fieldB")) sequence(aFirst, active);
        System.out.println("PASS independent two-field modeled Saving/completion/list/reopen checks=" + checks + " traces=4; no durable FieldLog/JNI/native evidence");
    }
}
