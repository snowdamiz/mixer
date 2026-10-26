package dev.mixer.android;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Recording platform boundary only; contains no observer lifetime decisions. */
public final class IndependentFaults {
    private IndependentFaults() { }
    public static final List<String> SLOTS = List.of("component", "layout", "attach", "window-focus",
        "insets", "contrast", "high-contrast", "animator-settings");
    public record Event(String kind, String slot, Object target, Object listener) { }
    public record Registration(String slot, Object target, Object listener) { }
    public static final List<Event> events = new ArrayList<>();
    public static final List<Registration> active = new ArrayList<>();
    public static final Map<String, Throwable> removeFaults = new HashMap<>();
    public static final Set<String> delayedRemoval = new HashSet<>();
    public static String addFaultSlot;
    public static String addFaultPhase;
    public static Throwable addFault;
    public static String addHookSlot;
    public static String addHookPhase;
    public static Runnable addHook;
    public static String removeHookSlot;
    public static String removeHookPhase;
    public static Runnable removeHook;
    public static boolean addHookFired;
    public static boolean removeHookFired;
    public static boolean failRemovalAfterEffect;
    public static int reads;

    public static void reset() {
        events.clear(); active.clear(); removeFaults.clear(); delayedRemoval.clear();
        addFaultSlot = null; addFaultPhase = null; addFault = null;
        addHookSlot = null; addHookPhase = null; addHook = null; addHookFired = false;
        removeHookSlot = null; removeHookPhase = null; removeHook = null; removeHookFired = false;
        failRemovalAfterEffect = false; reads = 0;
    }
    public static void read() { reads++; }
    public static void add(String slot, Object target, Object listener) {
        add(slot, target, listener, () -> { });
    }
    public static void add(String slot, Object target, Object listener, Runnable acquisition) {
        events.add(new Event("add.enter", slot, target, listener));
        addPhase(slot, "before", target, listener);
        acquisition.run();
        active.add(new Registration(slot, target, listener));
        events.add(new Event("add.acquire", slot, target, listener));
        addPhase(slot, "after", target, listener);
        events.add(new Event("add.return", slot, target, listener));
    }
    private static void addPhase(String slot, String phase, Object target, Object listener) {
        if (!addHookFired && slot.equals(addHookSlot) && phase.equals(addHookPhase)) {
            addHookFired = true;
            events.add(new Event("add.hook." + phase, slot, target, listener));
            addHook.run();
        }
        if (slot.equals(addFaultSlot) && phase.equals(addFaultPhase)) {
            events.add(new Event("add.throw." + phase, slot, target, listener));
            raise(addFault);
        }
    }
    public static void remove(String slot, Object target, Object listener) {
        remove(slot, target, listener, () -> { });
    }
    public static void remove(String slot, Object target, Object listener, Runnable removal) {
        events.add(new Event("remove.enter", slot, target, listener));
        removePhase(slot, "before", target, listener);
        Throwable fault = removeFaults.get(slot);
        if (fault != null && !failRemovalAfterEffect) {
            events.add(new Event("remove.throw.before", slot, target, listener));
            raise(fault);
        }
        if (!delayedRemoval.contains(slot)) {
            active.removeIf(r -> r.slot().equals(slot) && r.target() == target && r.listener() == listener);
            removal.run();
            events.add(new Event("remove.effect", slot, target, listener));
        }
        removePhase(slot, "after", target, listener);
        if (fault != null) {
            events.add(new Event("remove.throw.after", slot, target, listener));
            raise(fault);
        }
        events.add(new Event("remove.return", slot, target, listener));
    }
    private static void removePhase(String slot, String phase, Object target, Object listener) {
        if (!removeHookFired && slot.equals(removeHookSlot) && phase.equals(removeHookPhase)) {
            removeHookFired = true;
            events.add(new Event("remove.hook." + phase, slot, target, listener));
            removeHook.run();
        }
    }
    public static void raise(Throwable failure) {
        if (failure instanceof RuntimeException ordinary) throw ordinary;
        if (failure instanceof Error fatal) throw fatal;
        throw new AssertionError("Independent leaf requires an injected unchecked failure", failure);
    }
    public static long count(String kind, String slot) {
        return events.stream().filter(e -> e.kind().equals(kind) && e.slot().equals(slot)).count();
    }
    public static int position(String kind, String slot) {
        for (int i = 0; i < events.size(); i++) {
            Event event = events.get(i);
            if (event.kind().equals(kind) && event.slot().equals(slot)) return i;
        }
        return -1;
    }
    public static long active(String slot) { return active.stream().filter(r -> r.slot().equals(slot)).count(); }
}
