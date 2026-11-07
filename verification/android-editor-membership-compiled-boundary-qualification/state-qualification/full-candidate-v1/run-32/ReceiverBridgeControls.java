package dev.mixer.android;
import java.nio.file.*;
import java.util.*;
import java.util.function.Consumer;
import android.view.inputmethod.BaseInputConnection;
/** Serializes actual distinct same-class receiver objects for hostile map tests. */
public final class ReceiverBridgeControls {
 private ReceiverBridgeControls(){}
 public static void main(String[] args)throws Exception{
  BaseInputConnection original=new BaseInputConnection(new android.view.View(new android.app.Activity()),true),foreign=new BaseInputConnection(new android.view.View(new android.app.Activity()),true);
  String originalIdentity=DirectBoundaryStates.identity(original),foreignIdentity=DirectBoundaryStates.identity(foreign);
  ConcreteHostProbe.reset();DirectBoundaryStates.Trace trace=new DirectBoundaryStates.Trace();OutcomeCapture outcomes=new OutcomeCapture();outcomes.begin(trace);boolean[] nested={false};
  ConcreteHostProbe.hook=(method,phase)->{if(!nested[0]&&method.equals("BaseInputConnection.requestCursorUpdatesFiltered")&&phase.equals("entry")){nested[0]=true;if(!foreign.requestCursorUpdates(0,0))throw new AssertionError("actual foreign result");}};
  Consumer<ConcreteHostProbe.Event> observer=trace::event;ConcreteHostProbe.installQualificationHook(observer);boolean result;
  try{result=original.requestCursorUpdates(0,0);result&=original.requestCursorUpdates(0,0);}finally{ConcreteHostProbe.clearQualificationHook(observer);ConcreteHostProbe.hook=null;trace.event(null);outcomes.end();}
  if(!result||!outcomes.clean()||trace.receiverBindings.size()!=2||outcomes.rows.size()!=3||trace.sequence.size()!=6)throw new AssertionError("actual bounded receiver bridge fixture");
  Map<String,Object> row=new LinkedHashMap<>();row.put("schema","actual-same-class-receiver-bridge-control-v1");row.put("original_target",originalIdentity);row.put("foreign_target",foreignIdentity);row.put("native_sequence",trace.sequence);row.put("frame_sets",trace.frameSets);row.put("native_receiver_bindings",List.copyOf(trace.receiverBindings));row.put("actual_native_outcomes",outcomes.rows);row.put("selected_event",List.of(Map.of("sequence_index",0,"authority",Map.of("receiver",originalIdentity))));row.put("outcome_capture_diagnostic",outcomes.diagnostic());row.put("qualified",false);
  Files.writeString(Path.of(args[0]),DirectBoundaryStates.json(row)+"\n",java.nio.charset.StandardCharsets.UTF_8);ConcreteHostProbe.reset();System.out.println("PASS actual two same-class receivers, six events and three original returns; consistency fixture only");
 }
}
