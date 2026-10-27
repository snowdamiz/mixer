package dev.mixer.android;
import java.util.*;
import java.util.function.Consumer;
import android.view.inputmethod.BaseInputConnection;
/** Evidence faults must latch refusal without replacing the original leaf result or failure. */
public final class ObserverFailureControls {
 private ObserverFailureControls(){}private static int checks;
 private static void check(boolean value,String why){checks++;if(!value)throw new AssertionError(why);}
 private static final class Fatal extends Error {private static final long serialVersionUID=1L;}
 private static void passiveFailure(Throwable failure,boolean overflow){
  BaseInputConnection target=new BaseInputConnection(new android.view.View(new android.app.Activity()),true);
  ConcreteHostProbe.reset();OutcomeCapture capture=new OutcomeCapture();capture.begin();DirectBoundaryStates.Trace trace=new DirectBoundaryStates.Trace();
  if(overflow)for(int i=0;i<100001;i++)trace.sequence.add(null);
  Consumer<ConcreteHostProbe.Event> observer=event->{trace.event(event);if(!overflow)OutcomeCapture.observe(()->ConcreteHostProbe.fail(failure));};
  ConcreteHostProbe.installQualificationHook(observer);boolean actual;
  try{actual=target.requestCursorUpdates(0,0);}finally{ConcreteHostProbe.clearQualificationHook(observer);capture.end();}
  check(actual,"passive fault preserves the original filtered cursor boolean true");
  check(ConcreteHostProbe.count("BaseInputConnection.requestCursorUpdatesFiltered","entry")==1&&ConcreteHostProbe.count("BaseInputConnection.requestCursorUpdatesFiltered","beforeReturn")==1,"original entry/return hit counts preserved");
  check(!capture.clean()&&NativeOutcomeProbe.failed(),"each evidence fault dirties this attempt");
  if(!overflow)check(NativeOutcomeProbe.captureFailure()==failure,"same original evidence failure identity latched");
  check(capture.rows.stream().map(Json::object).anyMatch(row->"return".equals(row.get("completion"))&&"(II)Z".equals(row.get("descriptor"))&&Boolean.TRUE.equals(Json.object(row.get("value")).get("value"))),"actual typed normal return retained");
  check(capture.rows.stream().map(Json::object).noneMatch(row->"exception".equals(row.get("completion"))),"passive failure never becomes an original hook exception");
  OutcomeCapture next=new OutcomeCapture();next.begin();next.end();check(next.clean()&&!capture.clean(),"later begin cannot erase earlier refusal");ConcreteHostProbe.reset();
 }
 private static void intendedFailure(Throwable failure){
  BaseInputConnection target=new BaseInputConnection(new android.view.View(new android.app.Activity()),true);ConcreteHostProbe.reset();OutcomeCapture capture=new OutcomeCapture();capture.begin();
  Consumer<ConcreteHostProbe.Event> stimulus=event->{if(event.phase.equals("beforeReturn"))ConcreteHostProbe.fail(failure);};ConcreteHostProbe.installQualificationHook(stimulus);Throwable escaped=null;
  try{target.requestCursorUpdates(0,0);}catch(RuntimeException|Error original){escaped=original;}finally{ConcreteHostProbe.clearQualificationHook(stimulus);capture.end();}
  check(escaped==failure,"intended ordinary/fatal hook exception remains exact");check(capture.clean(),"intended callback stimulus is recorded without masquerading as an observation fault");
  check(capture.rows.stream().map(Json::object).anyMatch(row->"exception".equals(row.get("completion"))&&DirectBoundaryStates.identity(failure).equals(row.get("original_exception_identity"))),"same authored exception observed");ConcreteHostProbe.reset();
 }
 public static void main(String[] args){passiveFailure(new IllegalStateException("exact passive ordinary"),false);passiveFailure(new Fatal(),false);passiveFailure(null,true);intendedFailure(new IllegalStateException("exact intended ordinary"));intendedFailure(new Fatal());System.out.println("PASS passive observer fault isolation/latch controls checks="+checks);}
}
