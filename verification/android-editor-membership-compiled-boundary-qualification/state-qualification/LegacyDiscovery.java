package dev.mixer.android;
import java.lang.reflect.*;import java.nio.file.*;import java.io.*;import java.util.*;import java.util.zip.GZIPOutputStream;
/** Invokes unchanged original scenario bodies; passive discovery never grants state credit. */
public final class LegacyDiscovery {
 private LegacyDiscovery(){}
 public static void main(String[] args)throws Throwable{
  Class<?> type=NativeOwnerV2ConcreteHostTests.class;Field d=type.getDeclaredField("descriptor");d.setAccessible(true);d.set(null,Files.readAllBytes(Path.of(args[0])));Method run=type.getDeclaredMethod("runScenario",String.class);run.setAccessible(true);DirectBoundaryStates.Trace trace=new DirectBoundaryStates.Trace();ConcreteHostProbe.auditSink=trace::event;Throwable failure=null;
  try{run.invoke(null,args[1]);}catch(InvocationTargetException f){failure=f.getCause();}finally{ConcreteHostProbe.auditSink=null;ConcreteHostProbe.reset();}
  Map<String,Object> result=new LinkedHashMap<>();result.put("scenario",args[1]);result.put("status",failure==null?"passed":"failed");result.put("failure",failure==null?null:failure.toString());result.put("native_sequence",trace.sequence);result.put("frame_sets",trace.frameSets);try(PrintWriter out=new PrintWriter(new OutputStreamWriter(new GZIPOutputStream(Files.newOutputStream(Path.of(args[2]))),java.nio.charset.StandardCharsets.UTF_8))){out.println(DirectBoundaryStates.json(result));}
  if(failure!=null)throw failure;System.out.println("PASS unchanged legacy scenario "+args[1]+" events="+trace.sequence.size());
 }
}
