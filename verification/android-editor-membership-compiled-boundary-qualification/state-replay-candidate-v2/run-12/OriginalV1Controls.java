package dev.mixer.android;
import java.lang.reflect.*;
/** Executes the exact unchanged original V1 body/assertions; no substitute assertions. */
public final class OriginalV1Controls {
 private OriginalV1Controls(){}
 public static void main(String[] args)throws Throwable{Field count=NativeOwnerV2ConcreteHostTests.class.getDeclaredField("checks");count.setAccessible(true);int before=count.getInt(null);Method original=NativeOwnerV2ConcreteHostTests.class.getDeclaredMethod("v1Baselines");original.setAccessible(true);try{original.invoke(null);}catch(InvocationTargetException failure){throw failure.getCause();}int delta=count.getInt(null)-before;if(delta!=10)throw new AssertionError("exact unchanged V1 assertion count");System.out.println("PASS exact unchanged original V1 body assertions="+delta);}
}
