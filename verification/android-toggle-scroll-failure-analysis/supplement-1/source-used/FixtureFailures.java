package dev.mixer.android;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Consumer;

/** Private fixture plumbing only; no product behavior or native acceptance oracle. */
final class FixtureFailures {
    private FixtureFailures() {}
    static void main(Consumer<Runnable> dispatcher,Runnable action) {
        AtomicReference<Throwable> caught=new AtomicReference<>();
        dispatcher.accept(()->{try{action.run();}catch(Throwable failure){caught.set(failure);}});
        Throwable failure=caught.get();
        if(failure instanceof Error error)throw error;
        if(failure instanceof RuntimeException exception)throw exception;
        if(failure!=null)throw new AssertionError(failure);
    }
    static Throwable attempt(Throwable primary,Runnable action) {
        try{action.run();}catch(Throwable failure){
            if(primary==null)return failure;
            if(primary!=failure)primary.addSuppressed(failure);
        }
        return primary;
    }
    static String diagnostic(Throwable failure) {
        StringWriter output=new StringWriter();
        PrintWriter writer=new PrintWriter(output);
        writer.println("Private component fixture diagnostics; no product cause inferred.");
        if(failure==null)writer.println("passed-component-only");else failure.printStackTrace(writer);
        writer.flush();return output.toString();
    }
}
