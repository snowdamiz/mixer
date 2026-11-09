package dev.mixer.android;

import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;

/** Fresh bounded calls into the hash-verified R25 B product/classes, isolated from closure A. */
public final class NativeFieldAdmissionDiscriminator {
    private static int checks;
    private static void check(boolean condition,String message) { checks++; if(!condition)throw new AssertionError(message); }
    private static Field member(Class<?> type,String name) throws Exception {
        Field value=type.getDeclaredField(name); value.setAccessible(true); return value;
    }
    private static Object call(Object target,String name,Class<?>[] types,Object... args) throws Exception {
        Method method=target.getClass().getDeclaredMethod(name,types); method.setAccessible(true);
        try { return method.invoke(target,args); }
        catch(InvocationTargetException failure) {
            if(failure.getCause() instanceof Exception ordinary)throw ordinary;
            if(failure.getCause() instanceof Error fatal)throw fatal;
            throw failure;
        }
    }
    private static void unavailable(Object editor) throws Exception {
        try { call(editor,"available",new Class<?>[]{boolean.class},true); }
        catch(IllegalStateException expected) {
            check(expected.getMessage().equals("editor replacement unavailable"),"unexpected rejection: "+expected);
            return;
        }
        throw new AssertionError("editor capture admitted forbidden state");
    }
    public static void main(String[] args) throws Exception {
        try(URLClassLoader loader=new URLClassLoader(new java.net.URL[]{Path.of(args[0]).toUri().toURL()},ClassLoader.getPlatformClassLoader())) {
            Class<?> tests=loader.loadClass("dev.mixer.android.NativeOwnerV2ConcreteHostTests");
            member(tests,"descriptor").set(null,Files.readAllBytes(Path.of(args[1])));
            Class<?> type=loader.loadClass("dev.mixer.android.NativeOwnerV2ConcreteHostTests$Fixture");
            var constructor=type.getDeclaredConstructor(String.class); constructor.setAccessible(true);
            Object fixture=constructor.newInstance("field");
            try {
                call(fixture,"ready",new Class<?>[]{});
                Object renderer=call(fixture,"renderer",new Class<?>[]{});
                Object editor=call(renderer,"view",new Class<?>[]{String.class},"field");
                Field phase=member(editor.getClass(),"phase"); Object settled=phase.get(editor);
                check(settled.toString().equals("IDLE"),"control field is not settled");
                call(editor,"available",new Class<?>[]{boolean.class},true); checks++;
                Object root=member(type,"root").get(fixture);
                root.getClass().getMethod("hostWindowFocus",boolean.class).invoke(root,false);
                check(member(editor.getClass(),"windowFocusLost").getBoolean(editor),"focus loss not observed");
                check(phase.get(editor)==settled,"loss unexpectedly changed settled phase");
                unavailable(editor);
                root.getClass().getMethod("hostWindowFocus",boolean.class).invoke(root,true);
                check(!member(editor.getClass(),"windowFocusLost").getBoolean(editor),"focus gain did not settle denial");
                call(editor,"available",new Class<?>[]{boolean.class},true); checks++;
                for(Object candidate:phase.getType().getEnumConstants()) {
                    if(java.util.Set.of("CREATING","DRAINING","CLOSING","QUARANTINED").contains(candidate.toString())) {
                        phase.set(editor,candidate); unavailable(editor);
                    }
                }
                phase.set(editor,settled);
                call(editor,"available",new Class<?>[]{boolean.class},true); checks++;
                System.out.println("PASS H2 real NativeField checks="+checks+"; settled IDLE rejects windowFocusLost, focus gain restores admission; all four unsafe phases still reject");
            } finally { call(fixture,"close",new Class<?>[]{}); }
        }
    }
}
