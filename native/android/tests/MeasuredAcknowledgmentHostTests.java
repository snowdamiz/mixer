package dev.mixer.android;

import android.app.Activity;
import android.graphics.Insets;
import android.os.Handler;
import android.text.Editable;
import android.text.Layout;
import android.view.View;
import android.view.WindowInsets;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.EditText;
import android.widget.FrameLayout;
import java.lang.reflect.Field;
import java.nio.file.*;
import java.util.*;

/** Actual owner/renderer/editor contracts; controlled native Layout metrics. */
public final class MeasuredAcknowledgmentHostTests {
 static byte[] descriptor,opened;static int cases,checks;
 static final String TITLE="Stable title\nsecond line",VALUE="Zoë · 李";
 static void check(boolean ok,String message){checks++;if(!ok)throw new AssertionError(message);}
 static Object get(Object o,String n)throws Exception{Field f=o.getClass().getDeclaredField(n);f.setAccessible(true);return f.get(o);}
 static void frame(View v,String edge,int delta){try{Field f=View.class.getDeclaredField(edge);f.setAccessible(true);f.setInt(v,f.getInt(v)+delta);}catch(Exception e){throw new AssertionError(e);}}
 static byte[] packet(long rev,String value,String change){
  var p=CompleteHandoffHostTests.packet(opened);Json.object(p.get("document")).put("revision",new Json.Num(Long.toString(rev)));
  Json.object(CompleteHandoffHostTests.node(p,"task.title").get("properties")).put("value",TITLE);
  var n=CompleteHandoffHostTests.node(p,"task.responsible");var props=Json.object(n.get("properties"));props.put("value",value);
  switch(change){
   case "recipe" -> props.put("label","Changed recipe");
   case "binding" -> props.put("accessibilityIdentifier","Changed binding");
   case "actions" -> n.put("actions",List.of(Json.map("event","textChange","id","foreign.change")));
   case "generation" -> {for(Object x:Json.array(p.get("identities"))){var i=Json.object(x);if("task.responsible".equals(i.get("id")))i.put("generation",new Json.Num("999"));}}
   case "topology" -> Collections.swap(Json.array(CompleteHandoffHostTests.node(p,"task.fields").get("children")),0,1);
   case "sibling" -> Json.object(CompleteHandoffHostTests.node(p,"task.title").get("properties")).put("value",TITLE+"\nthird line");
  }
  return CompleteHandoffHostTests.encode(p);
 }
 static final class Fixture implements AutoCloseable {
  final Activity activity=new Activity();final FrameLayout root=new FrameLayout(activity);final List<byte[]> events=new ArrayList<>();
  final NativeOwnerV2 owner;final NativeRenderer renderer;final EditText edit;final Handler queue;final InputConnection connection;
  Fixture(boolean sibling)throws Exception{
   ConcreteHostProbe.reset();Layout.hostDefaultHeight=52;Layout.hostHeights.put(TITLE,127);Layout.hostHeights.put(TITLE+"\nthird line",180);Layout.hostHeights.put(VALUE,64);
   activity.resources.metrics.density=2.625f;activity.resources.metrics.scaledDensity=2.625f;activity.resources.metrics.densityDpi=420;
   activity.assets.put(InstalledAppearanceV2.DESCRIPTOR,descriptor);root.layout(0,0,1080,2400);activity.window.decor.layout(0,0,1080,2400);
   root.rootInsets=new WindowInsets(Insets.of(0,136,0,63));root.hostAttach(new Object());
   owner=NativeOwnerV2.external(activity,root,new ExternalFrameSourceV2(events::add));queue=(Handler)get(owner,"handler");owner.installExternal(packet(1,"",""),descriptor);
   renderer=(NativeRenderer)get(get(owner,"coordinator"),"renderer");edit=(EditText)renderer.view("task.responsible");
   if(sibling){
    EditText title=(EditText)renderer.view("task.title");check(title.requestFocus(),"sibling native focus");
    InputConnection input=title.onCreateInputConnection(new EditorInfo());check(input!=null&&input.setSelection(0,title.getText().length())&&
     input.setComposingText(TITLE+"\nthird line",1),"complete sibling native buffer awaiting source acknowledgement");
   }
   check(edit.requestFocus(),"native focus");connection=edit.onCreateInputConnection(new EditorInfo());check(connection!=null,"native connection");
   if(!sibling)check(connection.setComposingText(VALUE,1),"native composition");
   ConcreteHostProbe.reset();
  }
  public void close(){ConcreteHostProbe.hook=null;owner.close();if(renderer.editorDisposalBusyV2()){if(queue.queued()>0)queue.drainOne();for(Runnable r:queue.snapshot())queue.removeCallbacks(r);}else queue.drainAll(8);ConcreteHostProbe.reset();Layout.hostHeights.clear();Layout.hostDefaultHeight=-1;}
 }
 static void positive(boolean baseline,boolean sibling)throws Exception{
  try(var f=new Fixture(sibling)){
   var record=f.renderer.inspectV2().get("task.responsible");var title=f.renderer.view("task.title");
   var buffer=f.edit.getText();var nativeField=(NativeAppearanceViewsV2.NativeField)f.edit;var attempt=nativeField.attempt;var target=f.edit.lastConnection;
   int start=f.edit.getSelectionStart(),end=f.edit.getSelectionEnd(),cs=BaseInputConnection.getComposingSpanStart(buffer),ce=BaseInputConnection.getComposingSpanEnd(buffer);
   int oldY=f.edit.getTop(),oldH=f.edit.getHeight(),oldTitleY=title.getTop(),oldTitleH=title.getHeight();long oldRow=record.geometry.box.y();
   check(record.geometry.semanticHeight==1408&&record.geometry.box.height()==2816,"old semantic/hit distinction");
   check(oldRow==7181&&oldY==295&&oldH==115,"R161 old row and pixel edges observed row="+oldRow+" y="+oldY+" h="+oldH);
   Throwable failure=null;try{f.owner.installExternal(packet(2,sibling?"":VALUE,sibling?"sibling":""),descriptor);}catch(RuntimeException e){failure=e;}
   if(baseline){check(failure!=null&&!f.owner.hasCommittedPresentation(),"canonical measured ack reproduces refusal");System.out.println("PASS preserved canonical baseline refusal "+f.owner.cleanupLedger().primary());cases++;return;}
   check(failure==null&&f.owner.hasCommittedPresentation(),"source-owned measured ack: "+failure+" / "+f.owner.diagnostic());
   check(f.renderer.view("task.responsible")==f.edit&&f.edit.getText()==buffer,"exact native View and Editable retained");
   check(nativeField.attempt==attempt&&f.edit.lastConnection==target,"exact InputConnection attempt and target retained");
   check(f.edit.getSelectionStart()==start&&f.edit.getSelectionEnd()==end,"selection preserved");
   check(BaseInputConnection.getComposingSpanStart(buffer)==cs&&BaseInputConnection.getComposingSpanEnd(buffer)==ce,"composition preserved");
   check(ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry")==0&&ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==0,"ack does not consume predecessor");
   if(!sibling){
    check(record.geometry.semanticHeight==1561&&record.geometry.box.height()==2816,"new semantic metric without changed logical hit envelope");
    check(record.geometry.box.y()==7258&&f.edit.getTop()==298&&f.edit.getHeight()==116,"R161 +77 logical units / +3 top pixels / +1 height pixel");
    check(title.getTop()==oldTitleY&&title.getHeight()==oldTitleH,"Title frame unchanged");
   }else check(f.edit.getTop()>oldY,"sibling measurement moves retained horizontal field");
   check(f.connection.commitText("!",1),"retained connection accepts next native edit");
   cases++;System.out.println("PASS "+(sibling?"sibling source-owned placement":"exact R161 52->64 measured ack")+" y="+oldY+"->"+f.edit.getTop()+" h="+oldH+"->"+f.edit.getHeight());
  }
 }
 @SuppressWarnings("unchecked")
 static void refusal(String change)throws Exception{
  try(var f=new Fixture(false)){
   var old=f.renderer.packet;var parent=f.renderer.inspectV2().get("task.fields").view;
   if(change.equals("old-y")){frame(f.edit,"top",1);frame(f.edit,"bottom",1);}
   if(change.equals("old-height"))frame(f.edit,"bottom",1);
   if(change.equals("old-parent-y")){frame(parent,"top",1);frame(parent,"bottom",1);}
   if(change.equals("revoked"))((NativeAppearanceViewsV2.NativeField)f.edit).attempt.revoked=true;
   boolean[] hit={false};
   if(change.startsWith("candidate-"))ConcreteHostProbe.hook=(m,phase)->{
    if(hit[0]||!m.equals("View.getLocationInWindow")||!phase.equals("entry")||ConcreteHostProbe.lastEvent().receiver!=f.edit)return;
    try{
     Object pending=get(f.renderer,"v2Pending");if(pending==null)return;
     Map<String,NativeAppearanceViewsV2.Record> records=(Map<String,NativeAppearanceViewsV2.Record>)get(pending,"detached");
     View v=records.get(change.equals("candidate-parent-y")?"task.fields":"task.responsible").view;hit[0]=true;
     if(change.equals("candidate-width"))frame(v,"right",1);
     else if(change.equals("candidate-x")){frame(v,"left",1);frame(v,"right",1);}
     else if(change.equals("candidate-height"))frame(v,"bottom",1);
     else{frame(v,"top",1);frame(v,"bottom",1);}
    }catch(Exception failure){throw new AssertionError("final prepared candidate injection",failure);}
   };
   Throwable failure=null;try{f.owner.installExternal(packet(2,VALUE,change),descriptor);}catch(RuntimeException e){failure=e;}finally{ConcreteHostProbe.hook=null;}
   check(failure!=null&&!f.owner.hasCommittedPresentation(),"unexpected source/frame refused "+change);
   check(f.renderer.packet==old,"refusal cannot publish candidate "+change);
   if(change.startsWith("candidate-"))check(hit[0],"candidate tamper reached "+change);
   check(f.owner.cleanupLedger().primary()!=null,"primary error preserved "+change);
   cases++;System.out.println("PASS refusal "+change);
  }
 }
 static void lateFailure()throws Exception{
  try(var f=new Fixture(false)){
   var old=f.renderer.packet;int events=f.events.size();f.renderer.testFaultV2(0,true);
   Throwable error=null;try{f.owner.installExternal(packet(2,VALUE,""),descriptor);}catch(RuntimeException failure){error=failure;}
   var ledger=f.renderer.cleanupLedger();Throwable primary=f.owner.cleanupLedger().primary();
   check(error!=null&&!f.owner.hasCommittedPresentation()&&f.renderer.packet==old,"failed attachment cannot publish");
   check(get(ledger,"cause")==NativeEnvironmentV2.RendererCause.ROLLBACK_FAILED,"later renderer rollback cleanup failure actually reached");
   check(primary==ledger.primary()&&primary.getMessage().equals("test-only V2 attachment fault"),"late cleanup preserves original primary failure");
   int finish=ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry"),close=ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry");
   check(!f.connection.commitText("late",1)&&f.events.size()==events,"late input fenced after failed acknowledgement");
   check(finish==ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry")&&close==ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry"),"late input cannot repeat cleanup");
   cases++;System.out.println("PASS later rollback cleanup failure preserves attachment primary");
  }
 }
 public static void main(String[] args)throws Exception{
  Path p=Path.of(args[0]);descriptor=Files.readAllBytes(p.resolve("descriptor.json"));opened=Files.readAllBytes(p.resolve("before-public-reset/00.json"));
  boolean baseline=args[1].equals("baseline");positive(baseline,false);if(baseline)return;
  positive(false,true);
  for(String c:List.of("old-y","old-height","old-parent-y","candidate-y","candidate-height","candidate-parent-y","candidate-x","candidate-width","recipe","binding","actions","generation","topology","revoked"))refusal(c);
  lateFailure();System.out.println("PASS measured acknowledgment cases="+cases+" checks="+checks+" controlled native metrics; no device claim");
 }
}
