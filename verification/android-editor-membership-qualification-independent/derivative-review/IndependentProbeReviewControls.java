package dev.mixer.android;
import android.app.Activity;
import android.widget.EditText;
import android.view.inputmethod.BaseInputConnection;
import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

/** Independent host instrumentation checks. No product behavior matrix credit. */
public final class IndependentProbeReviewControls {
 private IndependentProbeReviewControls(){}
 private static int checks;
 private static final class Marker extends Error {private static final long serialVersionUID=1L;}
 private static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
 private static Field auditField(){try{return ConcreteHostProbe.class.getField("auditSink");}catch(NoSuchFieldException absent){return null;}}
 private static void audit(Consumer<ConcreteHostProbe.Event> observer)throws IllegalAccessException{Field field=auditField();if(field!=null)field.set(null,observer);}
 public static void main(String[] argv)throws Exception{
  Activity activity=new Activity();EditText field=new EditText(activity);field.setText("original");field.setSelection(8,8);BaseInputConnection target=new BaseInputConnection(field,true);
  List<NativeOutcomeProbe.Outcome> rows=new ArrayList<>();String mode=argv[0];
  if(mode.equals("audit-sink-witness")){
   check(auditField()!=null,"released original derivative has pre-count sink");
   Marker original=new Marker();int[] ordinary={0};ConcreteHostProbe.reset();
   NativeOutcomeProbe.begin(rows::add);ConcreteHostProbe.hook=(m,p)->ordinary[0]++;
   audit(event->{if(event.method.equals("BaseInputConnection.beginBatchEdit")&&event.phase.equals("beforeReturn"))throw original;});
   Throwable caught=null;try{target.beginBatchEdit();}catch(RuntimeException|Error thrown){caught=thrown;}
   audit(null);ConcreteHostProbe.hook=null;NativeOutcomeProbe.end();
   check(caught==original,"pre-count sink exception escaped unchanged");
   check(ConcreteHostProbe.count("BaseInputConnection.beginBatchEdit","entry")==1,"entry count recorded");
   check(ConcreteHostProbe.count("BaseInputConnection.beginBatchEdit","beforeReturn")==0,"sink prevents original count work");
   check(ordinary[0]==1,"ordinary beforeReturn hook bypassed");
   check(rows.isEmpty(),"sink exception is outside observation catch");
   check(NativeOutcomeProbe.clean()&&!NativeOutcomeProbe.failed(),"uncaptured sink throw leaves clean flag true");
   System.out.println("WITNESS pre-count auditSink throws before original count/hook; exact exception escapes; outcomes=0; clean=true; derivative acceptance refused");
  }else if(mode.equals("lifetime-reset-witness")){
   audit(null);ConcreteHostProbe.reset();Marker captureFailure=new Marker();
   NativeOutcomeProbe.begin(outcome->{throw captureFailure;});
   check(target.beginBatchEdit(),"evidence failure preserves original normal value");
   NativeOutcomeProbe.end();check(!NativeOutcomeProbe.clean()&&NativeOutcomeProbe.captureFailure()==captureFailure,"first attempt is dirty");
   NativeOutcomeProbe.begin(rows::add);check(target.beginBatchEdit(),"second attempt original value");NativeOutcomeProbe.end();
   check(NativeOutcomeProbe.clean()&&NativeOutcomeProbe.captureFailure()==null,"begin resets prior attempt failure");
   System.out.println("WITNESS failed first attempt is reset by second begin; final clean=true; trusted producer must latch each attempt result before next begin");
  }else if(mode.equals("positive")){
   audit(null);ConcreteHostProbe.reset();List<String> order=new ArrayList<>();
   NativeOutcomeProbe.begin(outcome->{if(outcome.method().equals("BaseInputConnection.beginBatchEdit"))order.add("actual-result");rows.add(outcome);});
   ConcreteHostProbe.hook=(method,phase)->{if(method.equals("BaseInputConnection.beginBatchEdit")&&phase.equals("beforeReturn")){check(ConcreteHostProbe.count(method,phase)==1,"ordinary hook after original count");order.add("ordinary");target.closed=true;}};
   Consumer<ConcreteHostProbe.Event> qualification=event->{if(event.method.equals("BaseInputConnection.beginBatchEdit")&&event.phase.equals("beforeReturn")){check(ConcreteHostProbe.count(event.method,event.phase)==1,"qualification after count");order.add("qualification");}};
   ConcreteHostProbe.installQualificationHook(qualification);boolean original=target.beginBatchEdit();ConcreteHostProbe.clearQualificationHook(qualification);ConcreteHostProbe.hook=null;NativeOutcomeProbe.end();
   check(original&&rows.size()==1&&Boolean.TRUE.equals(rows.get(0).value()),"actual original true captured once despite hook mutating source field");
   check(rows.get(0).receiver()==target&&rows.get(0).descriptor().equals("()Z"),"exact receiver and result descriptor");
   check(order.equals(List.of("ordinary","qualification","actual-result")),"original hook/order retained");check(NativeOutcomeProbe.clean(),"bounded normal attempt clean");
   for(boolean fatal:new boolean[]{false,true}){
    ConcreteHostProbe.reset();rows.clear();target.closed=false;Throwable thrown=fatal?new Marker():new IllegalStateException("ordinary");Marker observerFailure=new Marker();
    NativeOutcomeProbe.begin(outcome->{rows.add(outcome);throw observerFailure;});
    Consumer<ConcreteHostProbe.Event> hook=event->{if(event.method.equals("BaseInputConnection.beginBatchEdit")&&event.phase.equals("beforeReturn")){if(thrown instanceof Error error)throw error;throw (RuntimeException)thrown;}};
    ConcreteHostProbe.installQualificationHook(hook);Throwable caught=null;try{target.beginBatchEdit();}catch(RuntimeException|Error error){caught=error;}ConcreteHostProbe.clearQualificationHook(hook);NativeOutcomeProbe.end();
    check(caught==thrown,"same ordinary/fatal qualification-hook object rethrown despite failed observer");
    check(rows.size()==1&&rows.get(0).originalException()==thrown&&rows.get(0).completion().equals("exception"),"exact exception observation");
    check(!NativeOutcomeProbe.clean()&&NativeOutcomeProbe.captureFailure()==observerFailure,"observer failure refuses same attempt");
   }
   ConcreteHostProbe.reset();NativeOutcomeProbe.begin(outcome->{});Consumer<ConcreteHostProbe.Event> hook=event->{};ConcreteHostProbe.installQualificationHook(hook);ConcreteHostProbe.reset();
   check(ConcreteHostProbe.qualificationHookInstalled(),"original reset semantics keep qualification lifetime explicit");NativeOutcomeProbe.end();check(!NativeOutcomeProbe.clean(),"leaked qualification hook refuses attempt");ConcreteHostProbe.clearQualificationHook(hook);
   System.out.println("PASS independent passive-order/value/exception/lifetime controls checks="+checks);
  }else if(mode.equals("no-audit-sink")){
   check(auditField()==null,"corrected derivative removes pre-count audit sink");System.out.println("PASS pre-count audit sink absent");
  }else throw new IllegalArgumentException("unknown mode");
 }
}
