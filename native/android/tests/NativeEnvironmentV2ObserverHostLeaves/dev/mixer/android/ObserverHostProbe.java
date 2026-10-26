package dev.mixer.android;
import java.util.ArrayList;
import java.util.List;
public final class ObserverHostProbe {
    public static final List<String> calls = new ArrayList<>();
    public static final Object[] live = new Object[8], last = new Object[8], targets = new Object[8];
    public static final Runnable[][] hooks = new Runnable[4][8];
    public static final Throwable[][] faults = new Throwable[4][8];
    public static final java.util.Map<String,Integer> readCounts=new java.util.HashMap<>();
    public static String failingRead;
    public static Throwable readFailure;
    public static Runnable readHook;
    public static float animator=1,contrast,dp=1,sp=17;
    public static boolean highContrast,animatorMissing;
    public static final Object[] executors=new Object[8];
    public static void read(String name,int floor) {
        if(android.os.Build.VERSION.SDK_INT<floor) throw new AssertionError("new API read below floor "+name);
        readCounts.merge(name,1,Integer::sum);
        if(readHook!=null) readHook.run();
        if(name.equals(failingRead)) {
            if(readFailure instanceof Error) throw (Error)readFailure;
            throw (RuntimeException)readFailure;
        }
    }
    public static int reads, tokenReads;
    public static void reset() {
        calls.clear(); reads = tokenReads = 0;
        readCounts.clear();failingRead=null;readFailure=null;readHook=null;
        animator=1;contrast=0;dp=1;sp=17;highContrast=false;animatorMissing=false;
        java.util.Arrays.fill(executors,null);
        android.os.Build.VERSION.SDK_INT=36;
        java.util.Arrays.fill(live, null); java.util.Arrays.fill(last, null); java.util.Arrays.fill(targets, null);
        for (Runnable[] row : hooks) java.util.Arrays.fill(row, null);
        for (Throwable[] row : faults) java.util.Arrays.fill(row, null);
        android.os.Looper.mainThread = true;
    }
    private static void event(int phase, int slot) {
        Runnable hook = hooks[phase][slot]; if (hook != null) { hooks[phase][slot] = null; hook.run(); }
        Throwable failure = faults[phase][slot];
        if (failure instanceof Error) throw (Error)failure;
        if (failure != null) throw (RuntimeException)failure;
    }
    public static void add(int slot, Object target, Object listener) {
        calls.add("add" + slot); last[slot] = listener; targets[slot] = target;
        event(0,slot); live[slot] = listener; event(1,slot);
    }
    public static void remove(int slot, Object target, Object listener) {
        calls.add("remove" + slot);
        if (targets[slot] != target || last[slot] != listener) throw new AssertionError("wrong removal identity " + slot);
        event(2,slot); live[slot] = null; event(3,slot);
    }
}
