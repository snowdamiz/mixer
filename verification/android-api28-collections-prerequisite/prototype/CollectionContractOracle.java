package dev.mixer.android;

import java.util.AbstractCollection;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Independently authored finite host oracle; the prototype remains UNSELECTED. */
public final class CollectionContractOracle {
    private static int checks;
    private static void check(boolean value) { checks++; if (!value) throw new AssertionError("check " + checks); }
    private static void throwsType(Class<? extends Throwable> type, Runnable call) {
        checks++;
        try { call.run(); } catch (Throwable thrown) {
            if (type.isInstance(thrown)) return;
            throw new AssertionError("expected " + type + " got " + thrown, thrown);
        }
        throw new AssertionError("expected " + type);
    }
    private static void sameFailure(Throwable expected, Runnable call) {
        checks++;
        try { call.run(); } catch (Throwable actual) { if (actual == expected) return; throw new AssertionError(actual); }
        throw new AssertionError("failure was swallowed");
    }
    private static <E> void immutable(List<E> list, E sample) {
        throwsType(UnsupportedOperationException.class, () -> list.add(sample));
        throwsType(UnsupportedOperationException.class, () -> list.addAll(Collections.emptyList()));
        throwsType(UnsupportedOperationException.class, () -> list.clear());
        throwsType(UnsupportedOperationException.class, () -> list.removeIf(value -> false));
        throwsType(UnsupportedOperationException.class, () -> list.replaceAll(value -> value));
        throwsType(UnsupportedOperationException.class, () -> list.sort((left,right) -> 0));
        throwsType(UnsupportedOperationException.class, () -> list.subList(0,0).clear());
        if (!list.isEmpty()) {
            throwsType(UnsupportedOperationException.class, () -> list.set(0,sample));
            Iterator<E> iterator = list.iterator(); iterator.next();
            throwsType(UnsupportedOperationException.class, iterator::remove);
            var cursor = list.listIterator(); cursor.next();
            throwsType(UnsupportedOperationException.class, () -> cursor.set(sample));
            throwsType(UnsupportedOperationException.class, () -> cursor.add(sample));
        }
    }
    private static void lists() {
        Object first = new Object(), second = new Object();
        var input = new ArrayList<>(Arrays.asList(first,second,first));
        var snapshot = CollectionSnapshotsPrototype.copyList(input);
        check(snapshot.size() == 3 && snapshot.get(0) == first && snapshot.get(1) == second && snapshot.get(2) == first);
        check(snapshot.equals(List.copyOf(input)) && snapshot.hashCode() == List.copyOf(input).hashCode());
        input.clear(); check(snapshot.size() == 3);
        Object[] output = snapshot.toArray(); output[0] = second; check(snapshot.get(0) == first);
        Object[] arguments = {first,second,first};
        var literal = CollectionSnapshotsPrototype.list(arguments); arguments[0] = second; check(literal.get(0) == first);
        immutable(snapshot,first); immutable(literal,first); immutable(CollectionSnapshotsPrototype.list(),first);
        immutable(CollectionSnapshotsPrototype.copyList(Collections.emptyList()),first);
        throwsType(NullPointerException.class, () -> CollectionSnapshotsPrototype.copyList(null));
        throwsType(NullPointerException.class, () -> CollectionSnapshotsPrototype.copyList(Arrays.asList(first,null)));
        throwsType(NullPointerException.class, () -> CollectionSnapshotsPrototype.list((Object[])null));
        throwsType(NullPointerException.class, () -> CollectionSnapshotsPrototype.list(first,null));
        // Snapshot is shallow: borrow element identity, never clone ownership tokens or native records.
        var mutable = new ArrayList<String>(); var shallow = CollectionSnapshotsPrototype.list(mutable);
        mutable.add("visible"); check(shallow.get(0) == mutable && shallow.get(0).size() == 1);
        var liveInput = new ArrayList<>(Arrays.asList(first)); var badLiveView = Collections.unmodifiableList(liveInput);
        liveInput.clear(); check(badLiveView.isEmpty() && !snapshot.isEmpty());
        RuntimeException ordinary = new IllegalStateException("source failure"); Error fatal = new LinkageError("source fatal");
        for (Throwable failure : new Throwable[]{ordinary,fatal}) {
            var throwing = new AbstractCollection<Object>() {
                public int size() { throw new AssertionError("unexpected size"); }
                public Iterator<Object> iterator() { throw new AssertionError("unexpected iterator"); }
                public Object[] toArray() { if (failure instanceof Error value) throw value; throw (RuntimeException)failure; }
            };
            sameFailure(failure, () -> CollectionSnapshotsPrototype.copyList(throwing));
        }
    }
    private static void maps() {
        Object first = new Object(), second = new Object();
        var input = new LinkedHashMap<String,Object>(); input.put("b",first); input.put("a",second);
        var snapshot = CollectionSnapshotsPrototype.copyMap(input);
        check(snapshot.equals(Map.copyOf(input)) && snapshot.hashCode() == Map.copyOf(input).hashCode());
        input.clear(); check(snapshot.size() == 2 && snapshot.get("b") == first);
        throwsType(UnsupportedOperationException.class, () -> snapshot.put("c",first));
        throwsType(UnsupportedOperationException.class, () -> snapshot.clear());
        throwsType(UnsupportedOperationException.class, () -> snapshot.putAll(Collections.emptyMap()));
        throwsType(UnsupportedOperationException.class, () -> snapshot.replaceAll((key,value) -> value));
        throwsType(UnsupportedOperationException.class, () -> snapshot.computeIfAbsent("b", key -> first));
        throwsType(UnsupportedOperationException.class, () -> snapshot.remove("absent",first));
        throwsType(UnsupportedOperationException.class, () -> snapshot.keySet().remove("b"));
        throwsType(UnsupportedOperationException.class, () -> snapshot.values().clear());
        throwsType(UnsupportedOperationException.class, () -> snapshot.entrySet().iterator().next().setValue(second));
        var empty = CollectionSnapshotsPrototype.emptyMap(); check(empty.isEmpty());
        throwsType(UnsupportedOperationException.class, empty::clear);
        throwsType(UnsupportedOperationException.class, () -> empty.putAll(Collections.emptyMap()));
        throwsType(NullPointerException.class, () -> CollectionSnapshotsPrototype.copyMap(null));
        var nullable = new HashMap<String,Object>(); nullable.put(null,first);
        throwsType(NullPointerException.class, () -> CollectionSnapshotsPrototype.copyMap(nullable));
        nullable.clear(); nullable.put("key",null);
        throwsType(NullPointerException.class, () -> CollectionSnapshotsPrototype.copyMap(nullable));
    }
    private static void actualOwnedViewWitness() {
        var children = new ArrayList<UiPacket.Node>();
        var properties = new LinkedHashMap<String,Object>(); var actions = new LinkedHashMap<String,String>();
        var parent = new UiPacket.Node("p","vStack","1",properties,children,actions,false);
        var child = new UiPacket.Node("c","text","2",new HashMap<>(),new ArrayList<>(),new HashMap<>(),false);
        children.add(child);
        check(parent.children.size() == 1 && parent.children.get(0) == child);
        throwsType(UnsupportedOperationException.class, () -> parent.children.clear());
        // The current constructor deliberately keeps a builder-owned live view until decode finishes.
        // It is not a general defensive-copy constructor. Replacing this view early would lose children.
        properties.put("text","owned"); check("owned".equals(parent.text("text",null)));
    }
    private static void actualCoreBoundaries() {
        Object activity = new Object(), root = new Object(), window = new Object();
        boolean[] allowed = {true}; RuntimeException threadFailure = new IllegalStateException("wrong thread");
        var core = new OwnerLifecycleV2(() -> { if (!allowed[0]) throw threadFailure; },activity,root);
        var lifetime = core.lifetime();
        allowed[0] = false;
        sameFailure(threadFailure, () -> core.close(null));
        sameFailure(threadFailure, () -> core.windowChanged(null,null));
        allowed[0] = true;
        var refused = core.close(null); check(refused.isEmpty()); immutable(refused,null);
        var queued = core.windowChanged(lifetime,new OwnerLifecycleV2.WindowFacts(activity,root,false,true,window,100,100,true));
        check(queued.size() == 1 && queued.get(0).kind() == OwnerLifecycleV2.Kind.QUEUE_DRAIN);
        var drain = queued.get(0).token();
        var terminal = core.close(lifetime);
        check(terminal.size() == 3 && terminal.get(0).kind() == OwnerLifecycleV2.Kind.SEAL &&
            terminal.get(1).kind() == OwnerLifecycleV2.Kind.CANCEL_QUEUED && terminal.get(1).resource() == drain &&
            terminal.get(2).kind() == OwnerLifecycleV2.Kind.UNREGISTER);
        check(queued.get(0).token() == drain && core.snapshot().phase() == OwnerLifecycleV2.Phase.RETIRED);
        immutable(terminal,null);
    }
    public static void main(String[] args) {
        lists(); maps(); actualOwnedViewWitness(); actualCoreBoundaries();
        System.out.println("PASS " + checks + " host assertions; UNSELECTED prototype; no Android execution");
    }
}
