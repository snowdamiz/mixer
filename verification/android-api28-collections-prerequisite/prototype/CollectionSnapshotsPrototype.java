package dev.mixer.android;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/** UNSELECTED source-only semantic prototype. Not product code or an Android runtime receipt. */
final class CollectionSnapshotsPrototype {
    private CollectionSnapshotsPrototype() {}

    static <E> List<E> copyList(Collection<? extends E> source) {
        ArrayList<E> owned = new ArrayList<>(Objects.requireNonNull(source));
        for (E element : owned) Objects.requireNonNull(element);
        return Collections.unmodifiableList(owned);
    }

    @SafeVarargs static <E> List<E> list(E... elements) {
        Objects.requireNonNull(elements);
        ArrayList<E> owned = new ArrayList<>(elements.length);
        for (E element : elements) owned.add(Objects.requireNonNull(element));
        return Collections.unmodifiableList(owned);
    }

    static <K,V> Map<K,V> copyMap(Map<? extends K,? extends V> source) {
        Objects.requireNonNull(source);
        HashMap<K,V> owned = new HashMap<>();
        for (Map.Entry<? extends K,? extends V> entry : source.entrySet())
            owned.put(Objects.requireNonNull(entry.getKey()), Objects.requireNonNull(entry.getValue()));
        return Collections.unmodifiableMap(owned);
    }

    static <K,V> Map<K,V> emptyMap() {
        return Collections.unmodifiableMap(new HashMap<K,V>());
    }
}
