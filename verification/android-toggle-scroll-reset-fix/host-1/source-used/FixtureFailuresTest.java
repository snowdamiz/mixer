package dev.mixer.android;

import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Consumer;

public final class FixtureFailuresTest {
    private static int checks;
    private static void require(boolean value){checks++;if(!value)throw new AssertionError("host fixture check "+checks);}
    public static void main(String[] args){
        AtomicInteger escaped=new AtomicInteger();
        Consumer<Runnable> main=action->{Thread thread=new Thread(action,"synthetic-main");thread.setUncaughtExceptionHandler((t,e)->escaped.incrementAndGet());thread.start();try{thread.join();}catch(InterruptedException e){Thread.currentThread().interrupt();throw new AssertionError(e);}};
        AtomicInteger successful=new AtomicInteger();FixtureFailures.main(main,successful::incrementAndGet);require(successful.get()==1);
        AssertionError original=new AssertionError("original assertion");
        try{FixtureFailures.main(main,()->{throw original;});throw new AssertionError("did not forward");}catch(AssertionError caught){require(caught==original);}
        require(escaped.get()==0);
        IllegalStateException runtime=new IllegalStateException("original runtime");
        try{FixtureFailures.main(main,()->{throw runtime;});throw new AssertionError("did not forward runtime");}catch(IllegalStateException caught){require(caught==runtime);}
        AssertionError cleanup=new AssertionError("cleanup failed");Throwable retained=FixtureFailures.attempt(original,()->{throw cleanup;});require(retained==original);require(original.getSuppressed().length==1&&original.getSuppressed()[0]==cleanup);
        AtomicInteger exports=new AtomicInteger();retained=FixtureFailures.attempt(retained,exports::incrementAndGet);require(retained==original&&exports.get()==1);
        AssertionError exportFailure=new AssertionError("result export failed");retained=FixtureFailures.attempt(retained,()->{throw exportFailure;});require(retained==original&&original.getSuppressed()[1]==exportFailure);
        String diagnostic=FixtureFailures.diagnostic(retained);require(diagnostic.contains("original assertion")&&diagnostic.contains("cleanup failed")&&diagnostic.contains("result export failed"));
        require(FixtureFailures.attempt(null,()->{throw cleanup;})==cleanup);
        require(FixtureFailures.attempt(original,()->{throw original;})==original&&original.getSuppressed().length==2);
        require(FixtureFailures.diagnostic(null).contains("passed-component-only"));
        System.out.println("RESULT {\"checks\":"+checks+",\"escapedMainThreadFailures\":"+escaped.get()+",\"scope\":\"host fixture plumbing only\"}");
    }
}
