package dev.mixer.android;

import java.util.Collections;
import java.util.List;
import java.util.Map;

/** Actual JDK witness of the exception-contract mismatch, not execution of Android or D8 code. */
public final class EmptyMutationOracle {
    private static int assertions;
    private static void unsupported(Runnable call) {
        assertions++;
        try { call.run(); } catch (UnsupportedOperationException expected) { return; }
        throw new AssertionError("expected UnsupportedOperationException");
    }
    public static void main(String[] args) {
        unsupported(() -> List.of().clear());
        Collections.emptyList().clear(); assertions++;
        unsupported(() -> List.of().removeIf(item -> false));
        if (Collections.emptyList().removeIf(item -> false)) throw new AssertionError(); assertions++;
        unsupported(() -> Map.of().clear());
        Collections.emptyMap().clear(); assertions++;
        unsupported(() -> Map.of().remove("absent"));
        if (Collections.emptyMap().remove("absent") != null) throw new AssertionError(); assertions++;
        System.out.println("PASS " + assertions + " host assertions; four empty-mutator exception mismatches; Android behavior pending");
    }
}
