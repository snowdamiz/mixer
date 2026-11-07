package dev.mixer.android;
import java.lang.reflect.*;
import java.nio.file.*;
import java.io.*;
import java.util.*;
import java.util.zip.GZIPOutputStream;
/** Bounded recovery driver; invokes the unchanged original legacy row body once. */
public final class LegacyBoundarySingleState {
 private LegacyBoundarySingleState(){}
 public static void main(String[] args)throws Exception{
  if(args.length!=5||!Set.of("clean","terminal-at-entry","terminal-before-return","dirty-at-entry","dirty-before-return","ordinary-throw-after-callback","fatal-throw-after-callback").contains(args[3]))throw new AssertionError("exact one historical state required");
  Field descriptor=NativeOwnerV2ConcreteHostTests.class.getDeclaredField("descriptor");descriptor.setAccessible(true);descriptor.set(null,Files.readAllBytes(Path.of(args[0])));
  Map<String,Object> root=Json.object(Json.parse(Files.readAllBytes(Path.of(args[1])))),item=null;
  for(Object candidate:Json.array(root.get("records")))if(Json.object(candidate).get("historical_id").equals(args[2])){if(item!=null)throw new AssertionError("duplicate historical binding");item=Json.object(candidate);}
  if(item==null)throw new AssertionError("unknown original historical binding");
  Method original=LegacyBoundaryStates.class.getDeclaredMethod("run",Map.class,String.class);original.setAccessible(true);Map<String,Object> row;
  try{row=Json.object(original.invoke(null,item,args[3]));}catch(InvocationTargetException failure){if(failure.getCause()instanceof Error error)throw error;if(failure.getCause()instanceof RuntimeException error)throw error;if(failure.getCause()instanceof Exception error)throw error;throw new AssertionError(failure.getCause());}
  try(PrintWriter raw=new PrintWriter(new OutputStreamWriter(new GZIPOutputStream(Files.newOutputStream(Path.of(args[4]))),java.nio.charset.StandardCharsets.UTF_8));PrintWriter compact=CompactEvidence.writer(Path.of(args[4]+".compact.jsonl"))){raw.println(DirectBoundaryStates.json(row));compact.println(DirectBoundaryStates.json(CompactEvidence.project(row)));}
  if(!args[2].equals(row.get("historical_id"))||!args[3].equals(row.get("state"))||!"passed-callback-scope-state; outcome-review-required".equals(row.get("status"))||row.get("validation_failure")!=null||!Boolean.TRUE.equals(row.get("outcome_probe_clean")))throw new AssertionError("retained unchanged-body state failure");
  System.out.println("PASS unchanged LegacyBoundaryStates.run "+args[2]+" "+args[3]+"; helper outcomes remain pending");
 }
}
