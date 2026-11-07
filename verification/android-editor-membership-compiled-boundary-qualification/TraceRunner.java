package dev.mixer.android;
import java.io.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
/** Read-only supplementary observer. Never invokes product methods or edits authority. */
public final class TraceRunner {
 private TraceRunner(){}
 private static final IdentityHashMap<Object,Integer> ids=new IdentityHashMap<>();
 private static int nextId=1,sequence;
 private static String id(Object value){if(value==null)return null;return value.getClass().getName()+"@"+ids.computeIfAbsent(value,k->nextId++);}
 private static Object get(Object value,String name){if(value==null)return null;for(Class<?> c=value.getClass();c!=null;c=c.getSuperclass())try{Field f=c.getDeclaredField(name);f.setAccessible(true);return f.get(value);}catch(NoSuchFieldException ignored){}catch(IllegalAccessException e){throw new AssertionError(e);}return null;}
 private static Map<String,Object> fields(Object value,String...names){Map<String,Object> out=new LinkedHashMap<>();out.put("identity",id(value));for(String name:names){Object v=get(value,name);out.put(name,v==null||v instanceof Number||v instanceof Boolean||v instanceof String?v:v instanceof Enum<?> e?e.name():id(v));}return out;}
 static Map<String,Object> authority(Object receiver){
  Object editor=receiver instanceof android.view.inputmethod.BaseInputConnection?get(receiver,"editor"):receiver;
  Object record=get(editor,"record"),attempt=get(editor,"attempt"),fence=get(record,"editorFence"),lease=get(record,"editorCallbackLease"),scope=get(record,"scoped"),preservation=get(record,"fieldPreservation"),replacement=get(record,"replacementCallback");
  Map<String,Object> out=new LinkedHashMap<>();out.put("receiver",id(receiver));out.put("record",fields(record,"id","generation","kind","binding","changing","constructed"));out.put("editor",fields(editor,"phase","depth","permanent","firstFatal","primary","attempt","replacement","finishing"));out.put("attempt",fields(attempt,"editable","output","target","adapter","revoked","close"));out.put("fence",fields(fence,"operation","presentation","terminal","drawAllowed","inputAllowed","commitFinish"));out.put("lease",fields(lease,"original","parent","hook","entered","ended","nativeExecuting"));out.put("scoped",fields(scope,"mode","fence","token","editorLease","replacementLease","fieldLease"));out.put("fieldPreservation",fields(preservation,"original","before","selected","entered","counted","ended","released","lossObservation","callbacks","checking"));out.put("replacement",fields(replacement,"original","stage","registered","nativeExecuting","callbacks","eventClaimed","lost","lossObservation"));out.put("jni",Map.of("create",NativeBridge.createCalls,"prepare",NativeBridge.prepareCalls,"commit",NativeBridge.commitCalls,"abort",NativeBridge.abortCalls,"destroy",NativeBridge.destroyCalls));return out;
 }
 private static void json(StringBuilder b,Object v){if(v==null)b.append("null");else if(v instanceof Boolean||v instanceof Number)b.append(v);else if(v instanceof Map<?,?> m){b.append('{');boolean comma=false;for(var e:m.entrySet()){if(comma)b.append(',');comma=true;json(b,e.getKey().toString());b.append(':');json(b,e.getValue());}b.append('}');}else if(v instanceof Iterable<?> values){b.append('[');boolean comma=false;for(Object x:values){if(comma)b.append(',');comma=true;json(b,x);}b.append(']');}else{b.append('"');String s=v.toString();for(int i=0;i<s.length();i++){char c=s.charAt(i);switch(c){case '"'->b.append("\\\"");case '\\'->b.append("\\\\");case '\n'->b.append("\\n");case '\r'->b.append("\\r");case '\t'->b.append("\\t");default->{if(c<32)b.append(String.format("\\u%04x",(int)c));else b.append(c);}}}b.append('"');}}
 public static void main(String[] args)throws Throwable{
  try(PrintWriter out=new PrintWriter(Files.newBufferedWriter(Path.of(args[0])))){
   ConcreteHostProbe.auditSink=event->{if(sequence>=300000)throw new AssertionError("bounded trace event limit");Map<String,Object> row=new LinkedHashMap<>();row.put("sequence",++sequence);row.put("method",event.method);row.put("phase",event.phase);row.put("authority",authority(event.receiver));List<Object> frames=new ArrayList<>();for(var f:event.productionFrames)frames.add(Map.of("class",f.className(),"method",f.methodName(),"descriptor",f.descriptor(),"bci",f.bytecodeIndex(),"line",f.line()));row.put("frames",frames);StringBuilder b=new StringBuilder();json(b,row);out.println(b);};
   try{Class<?> type=Class.forName(args[1]);if(args.length>2&&args[2].equals("--v1-original")){Method m=type.getDeclaredMethod("v1Baselines");m.setAccessible(true);m.invoke(null);System.out.println("PASS unmodified original V1 five controls");}else type.getMethod("main",String[].class).invoke(null,(Object)Arrays.copyOfRange(args,2,args.length));}
   catch(InvocationTargetException failure){throw failure.getCause();}
   finally{ConcreteHostProbe.auditSink=null;out.flush();}
  }
 }
}
