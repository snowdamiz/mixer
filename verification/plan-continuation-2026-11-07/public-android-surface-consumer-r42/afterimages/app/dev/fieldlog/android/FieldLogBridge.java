package dev.fieldlog.android;
public final class FieldLogBridge {
 static { System.loadLibrary("mixer_android_jni"); }
 private FieldLogBridge() {}
 public static native int surfaceDiagnostic();
 public static native long createContext(FieldLogActivity receiver);
 public static native int submit(long context,byte[] command);
 public static native byte[] poll(long context,String requestID);
 public static native boolean hasReply(long context,String requestID);
 public static native boolean contextRetained(long context);
 private static native int beginClose(long context);
 static void closeContext(long context){
  if(android.os.Looper.myLooper()!=android.os.Looper.getMainLooper())throw new IllegalStateException("Android main thread required");
  if(beginClose(context)!=0)throw new IllegalStateException("JNI context close rejected: "+context);
  drainClosed(context,0);
 }
 private static void drainClosed(long context,int polls){
  if(!contextRetained(context))return;
  if(poll(context,"")==null)throw new IllegalStateException("JNI context close pump failed: "+context);
  if(!contextRetained(context))return;
  if(polls>=625)throw new IllegalStateException("Swift context close timeout: "+context);
  if(!new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(()->drainClosed(context,polls+1),16))
   throw new IllegalStateException("Context close pump rejected: "+context);
 }
}
