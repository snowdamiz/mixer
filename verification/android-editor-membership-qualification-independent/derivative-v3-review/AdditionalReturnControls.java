package dev.mixer.android;
import android.app.Activity;
import android.os.Handler;
import android.widget.EditText;
import android.view.inputmethod.BaseInputConnection;
import java.util.*;
import java.util.function.Consumer;
/** Only the two additive leaf outcomes; product adapter getHandler remains pure null. */
public final class AdditionalReturnControls {
 private AdditionalReturnControls(){}private static int checks;
 private static final class Marker extends Error{private static final long serialVersionUID=1L;}
 private static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
 private static Object invoke(BaseInputConnection target,boolean handler){return handler?target.getHandler():target.requestCursorUpdates(0,0);}
 private static String method(boolean handler){return handler?"BaseInputConnection.getHandler":"BaseInputConnection.requestCursorUpdatesFiltered";}
 private static void raise(Throwable failure){if(failure instanceof Error error)throw error;throw (RuntimeException)failure;}
 public static void main(String[] args){
  Activity activity=new Activity();EditText field=new EditText(activity);BaseInputConnection target=new BaseInputConnection(field,true);
  for(boolean handler:new boolean[]{false,true}){
   String selected=method(handler);String descriptor=handler?"()Landroid/os/Handler;":"(II)Z";
   ConcreteHostProbe.reset();List<String> order=new ArrayList<>();List<NativeOutcomeProbe.Outcome> rows=new ArrayList<>();
   NativeOutcomeProbe.begin(outcome->{check(outcome.method().equals(selected),"no unexpected outcome");rows.add(outcome);order.add("outcome");});
   ConcreteHostProbe.hook=(method,phase)->{if(method.equals(selected)){check(ConcreteHostProbe.count(method,phase)==1,"ordinary hook after original count");order.add("ordinary-"+phase);target.closed=true;}};
   Consumer<ConcreteHostProbe.Event> qualification=event->{if(event.method.equals(selected)){check(ConcreteHostProbe.count(event.method,event.phase)==1,"qualification after original count");order.add("qualification-"+event.phase);}};
   ConcreteHostProbe.installQualificationHook(qualification);Object actual=invoke(target,handler);ConcreteHostProbe.clearQualificationHook(qualification);ConcreteHostProbe.hook=null;NativeOutcomeProbe.end();
   check(rows.size()==1&&rows.get(0).receiver()==target&&rows.get(0).descriptor().equals(descriptor),"one exact result/receiver/descriptor");
   check(handler?actual instanceof Handler&&rows.get(0).value()==actual:Boolean.TRUE.equals(actual)&&Boolean.TRUE.equals(rows.get(0).value()),"original Handler reference or boolean value captured");
   check(order.equals(handler?List.of("ordinary-entry","qualification-entry","outcome"):List.of("ordinary-entry","qualification-entry","ordinary-beforeReturn","qualification-beforeReturn","outcome")),"existing event/count/hook order preserved");
   check(ConcreteHostProbe.count(selected,"entry")==1&&ConcreteHostProbe.count(selected,"beforeReturn")== (handler?0:1),"original getter no-beforeReturn versus filtered done shape");check(NativeOutcomeProbe.clean(),"normal attempt clean");
   if(handler){ConcreteHostProbe.reset();rows.clear();NativeOutcomeProbe.begin(rows::add);Object next=invoke(target,true);NativeOutcomeProbe.end();check(next!=actual&&rows.size()==1&&rows.get(0).value()==next,"constructor expression evaluates once per actual call and fresh reference preserved");check(NativeOutcomeProbe.clean(),"second getter attempt clean");}
   for(String phase:handler?List.of("entry"):List.of("entry","beforeReturn"))for(boolean qualified:new boolean[]{false,true})for(boolean fatal:new boolean[]{false,true}){
    ConcreteHostProbe.reset();rows.clear();Throwable original=fatal?new Marker():new IllegalStateException("ordinary");NativeOutcomeProbe.begin(rows::add);
    Consumer<ConcreteHostProbe.Event> fault=event->{if(event.method.equals(selected)&&event.phase.equals(phase))raise(original);};
    if(qualified)ConcreteHostProbe.installQualificationHook(fault);else ConcreteHostProbe.hook=(method,p)->{if(method.equals(selected)&&p.equals(phase))raise(original);};
    Throwable caught=null;try{invoke(target,handler);}catch(RuntimeException|Error failure){caught=failure;}
    if(qualified)ConcreteHostProbe.clearQualificationHook(fault);ConcreteHostProbe.hook=null;NativeOutcomeProbe.end();
    check(caught==original,"ordinary/fatal ordinary/qualification hook exact same object escapes");
    check(rows.size()==1&&rows.get(0).completion().equals("exception")&&rows.get(0).originalException()==original,"exception observed without fabricated normal return");
    check(ConcreteHostProbe.count(selected,phase)==1,"throw after original selected count");check(NativeOutcomeProbe.clean(),"exact hook exception capture clean");
   }
   ConcreteHostProbe.reset();Marker evidenceFailure=new Marker();NativeOutcomeProbe.begin(outcome->{throw evidenceFailure;});Object kept=invoke(target,handler);NativeOutcomeProbe.end();
   check(handler?kept instanceof Handler:Boolean.TRUE.equals(kept),"observation failure cannot replace original normal result");check(!NativeOutcomeProbe.clean()&&NativeOutcomeProbe.captureFailure()==evidenceFailure,"failed observation refuses attempt");
   ConcreteHostProbe.reset();RuntimeException original=new IllegalArgumentException("first original");NativeOutcomeProbe.begin(outcome->{throw evidenceFailure;});ConcreteHostProbe.hook=(method,phase)->{if(method.equals(selected)&&phase.equals("entry"))throw original;};Throwable caught=null;try{invoke(target,handler);}catch(RuntimeException|Error failure){caught=failure;}ConcreteHostProbe.hook=null;NativeOutcomeProbe.end();
   check(caught==original&&!NativeOutcomeProbe.clean()&&NativeOutcomeProbe.captureFailure()==evidenceFailure,"failed exception capture preserves original throw and refuses attempt");
  }
  System.out.println("PASS two additive actual-return/reference/descriptor/order/count/ordinary+fatal/evidence-failure controls checks="+checks+"; host leaf utility only");
 }
}
