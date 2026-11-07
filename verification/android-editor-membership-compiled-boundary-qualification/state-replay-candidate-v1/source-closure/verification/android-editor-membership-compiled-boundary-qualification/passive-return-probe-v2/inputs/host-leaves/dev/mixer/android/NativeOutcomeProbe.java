package dev.mixer.android;
import java.util.List;
import java.util.function.Consumer;
/** Host evidence only. Observation failures never change an original return or exception. */
public final class NativeOutcomeProbe {
 private NativeOutcomeProbe(){}
 public record Outcome(String method,String descriptor,Object receiver,String completion,Object value,Throwable originalException,List<ConcreteHostProbe.Site> productionFrames){}
 private static Consumer<Outcome> sink;
 private static Throwable captureFailure;
 private static boolean failed,active;
 private static int count;
 public static final int LIMIT=65536;
 public static void begin(Consumer<Outcome> observer){if(active||observer==null){failed=true;return;}sink=observer;captureFailure=null;failed=false;count=0;active=true;}
 public static void end(){if(!active||ConcreteHostProbe.qualificationHookInstalled())failed=true;sink=null;active=false;}
 public static boolean clean(){return !failed&&!active&&!ConcreteHostProbe.qualificationHookInstalled();}
 public static boolean failed(){return failed;}
 public static Throwable captureFailure(){return captureFailure;}
 static void captureFailed(Throwable failure){failed=true;if(captureFailure==null)captureFailure=failure;}
 private static void emit(String method,String descriptor,Object receiver,String completion,Object value,Throwable failure){
  if(!active)return;
  try{if(count>=LIMIT){failed=true;return;}count++;Consumer<Outcome> observer=sink;if(observer==null){failed=true;return;}observer.accept(new Outcome(method,descriptor,receiver,completion,value,failure,ConcreteHostProbe.outcomeFrames()));}
  catch(RuntimeException|Error evidenceFailure){captureFailed(evidenceFailure);}
 }
 static void hookException(ConcreteHostProbe.Event event,Throwable failure){emit(event.method,"hook-exception",event.receiver,"exception",null,failure);}
 public static <T>T returned(String method,String descriptor,Object receiver,T value){emit(method,descriptor,receiver,"return",value,null);return value;}
 public static boolean returned(String method,String descriptor,Object receiver,boolean value){emit(method,descriptor,receiver,"return",value,null);return value;}
 public static int returned(String method,String descriptor,Object receiver,int value){try{emit(method,descriptor,receiver,"return",value,null);}catch(RuntimeException|Error f){captureFailed(f);}return value;}
 public static long returned(String method,String descriptor,Object receiver,long value){try{emit(method,descriptor,receiver,"return",value,null);}catch(RuntimeException|Error f){captureFailed(f);}return value;}
 public static float returned(String method,String descriptor,Object receiver,float value){try{emit(method,descriptor,receiver,"return",value,null);}catch(RuntimeException|Error f){captureFailed(f);}return value;}
 public static double returned(String method,String descriptor,Object receiver,double value){try{emit(method,descriptor,receiver,"return",value,null);}catch(RuntimeException|Error f){captureFailed(f);}return value;}
 public static byte returned(String method,String descriptor,Object receiver,byte value){try{emit(method,descriptor,receiver,"return",value,null);}catch(RuntimeException|Error f){captureFailed(f);}return value;}
 public static short returned(String method,String descriptor,Object receiver,short value){try{emit(method,descriptor,receiver,"return",value,null);}catch(RuntimeException|Error f){captureFailed(f);}return value;}
 public static char returned(String method,String descriptor,Object receiver,char value){try{emit(method,descriptor,receiver,"return",value,null);}catch(RuntimeException|Error f){captureFailed(f);}return value;}
}
