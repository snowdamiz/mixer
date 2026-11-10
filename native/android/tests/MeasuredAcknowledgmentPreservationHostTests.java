package dev.mixer.android;

import android.text.Layout;
import android.view.View;
import android.view.inputmethod.BaseInputConnection;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;

/** Independent assertions on actual production owner/renderer and controlled platform leaves. */
public final class MeasuredAcknowledgmentPreservationHostTests {
 static int cases,checks;static boolean baseline;
 static void check(boolean b,String m){checks++;if(!b)throw new AssertionError(m);}
 static Object get(Object o,String n){try{Field f=o.getClass().getDeclaredField(n);f.setAccessible(true);return f.get(o);}catch(Exception e){throw new AssertionError(e);}}
 static void set(Object o,String n,Object v){try{Field f=o.getClass().getDeclaredField(n);f.setAccessible(true);f.set(o,v);}catch(Exception e){throw new AssertionError(e);}}
 static void shift(View v,int d){MeasuredAcknowledgmentHostTests.frame(v,"top",d);MeasuredAcknowledgmentHostTests.frame(v,"bottom",d);}
 static int[] pos(View v){int x=v.getLeft(),y=v.getTop();for(var p=v.getParent();p instanceof View a;p=a.getParent()){
  if(a instanceof NativeAppearanceViewsV2.Gate||a instanceof android.widget.FrameLayout)break;x+=a.getLeft();y+=a.getTop();}return new int[]{x,y};}
 static int[] local(View v){return new int[]{v.getLeft(),v.getTop(),v.getRight(),v.getBottom()};}
 static boolean sourceFrame(NativeRenderer r,String id)throws Exception{
  Method m=NativeRenderer.class.getDeclaredMethod("sourceFrameV3",UiPacket.class,Map.class,String.class);m.setAccessible(true);
  return (boolean)m.invoke(null,r.packet,r.inspectV2(),id);
 }
 static Throwable install(MeasuredAcknowledgmentHostTests.Fixture f,byte[] p){try{f.owner.installExternal(p,MeasuredAcknowledgmentHostTests.descriptor);return null;}catch(RuntimeException e){return e;}finally{ConcreteHostProbe.hook=null;}}
 static void positive(boolean sibling)throws Exception{
  try(var f=new MeasuredAcknowledgmentHostTests.Fixture(sibling)){
   var rec=f.renderer.inspectV2().get("task.responsible");var buffer=f.edit.getText();var field=(NativeAppearanceViewsV2.NativeField)f.edit;
   var attempt=field.attempt;var target=f.edit.lastConnection;int acq=f.edit.connectionAcquisitions;
   int ss=f.edit.getSelectionStart(),se=f.edit.getSelectionEnd(),cs=BaseInputConnection.getComposingSpanStart(buffer),ce=BaseInputConnection.getComposingSpanEnd(buffer);
   int[] before=pos(f.edit);int localTop=f.edit.getTop(),height=f.edit.getHeight();
   if(!baseline)check(sourceFrame(f.renderer,"task.responsible")&&sourceFrame(f.renderer,"task.title"),"initial ordinary publication witnesses valid");
   Throwable e=install(f,MeasuredAcknowledgmentHostTests.packet(2,sibling?"":MeasuredAcknowledgmentHostTests.VALUE,sibling?"sibling":""));
   if(baseline){check(e!=null&&!f.owner.hasCommittedPresentation(),"old horizontal guard refuses measured reflow");}
   else{
    check(e==null&&f.owner.hasCommittedPresentation(),"legitimate measured acknowledgment publishes "+e);
    check(f.renderer.view("task.responsible")==f.edit&&f.edit.getText()==buffer&&field.attempt==attempt&&f.edit.lastConnection==target&&f.edit.connectionAcquisitions==acq,"exact editor, buffer, attempt, old target and no new InputConnection");
    check(f.edit.getSelectionStart()==ss&&f.edit.getSelectionEnd()==se&&BaseInputConnection.getComposingSpanStart(buffer)==cs&&BaseInputConnection.getComposingSpanEnd(buffer)==ce,"selection and composing range retained");
    if(!sibling)check(localTop==295&&height==115&&f.edit.getTop()==298&&f.edit.getHeight()==116&&rec.geometry.semanticHeight==1561,"independent exact R161 measurement assertion");
    check(sourceFrame(f.renderer,"task.responsible")&&sourceFrame(f.renderer,"task.title"),"post ack ordinary publication witnesses valid");
    check(ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry")==0&&ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==0,"no finish or close during acknowledgment");
    check(f.connection.commitText("!",1),"old wrapper remains usable after acknowledgment");
   }
   cases++;System.out.println("PASS positive sibling="+sibling+" baseline="+baseline+" pos="+Arrays.toString(before)+"->"+Arrays.toString(pos(f.edit))+" failure="+e);
  }
 }
 static void ordinaryRefresh()throws Exception{
  try(var f=new MeasuredAcknowledgmentHostTests.Fixture(false)){
   check(f.connection.setSelection(0,f.edit.getText().length())&&f.connection.commitText("",1),"restore native empty buffer for ordinary refresh");
   var buffer=f.edit.getText();var target=f.edit.lastConnection;
   for(int i=2;i<=4;i++){
    Throwable e=install(f,MeasuredAcknowledgmentHostTests.packet(i,"",""));
    check(e==null&&f.owner.hasCommittedPresentation(),"ordinary refresh revision="+i+" "+e);
    check(f.renderer.view("task.responsible")==f.edit&&f.edit.getText()==buffer&&f.edit.lastConnection==target,"ordinary refresh retains exact target");
    if(!baseline)for(String id:f.renderer.inspectV2().keySet())check(sourceFrame(f.renderer,id),"ordinary prepared witness "+id+" revision="+i);
   }
   cases++;System.out.println("PASS initial + three ordinary refreshes baseline="+baseline);
  }
 }
 static void rollback(boolean late)throws Exception{
  try(var f=new MeasuredAcknowledgmentHostTests.Fixture(false)){
   f.renderer.testFaultV2(0,late);int events=f.events.size();var old=f.renderer.packet;
   Throwable e=install(f,MeasuredAcknowledgmentHostTests.packet(2,MeasuredAcknowledgmentHostTests.VALUE,""));
   check(e!=null&&!f.owner.hasCommittedPresentation()&&f.renderer.packet==old,"failed attachment cannot publish");
   check(f.owner.cleanupLedger().primary().getMessage().equals("test-only V2 attachment fault"),"attachment primary survives rollback late="+late);
   int finish=ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry"),close=ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry");
   check(!f.connection.commitText("late",1)&&f.events.size()==events,"later callback refused after failed measured acknowledgment");
   check(finish==ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry")&&close==ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry"),"later callback cannot retry cleanup");
   cases++;System.out.println("PASS rollback lateFailure="+late+" finish="+finish+" close="+close+" lateCallbackRefused=true");
  }
 }
 public static void main(String[] args)throws Exception{
  Path p=Path.of(args[0]);baseline=args[1].equals("baseline");
  MeasuredAcknowledgmentHostTests.descriptor=Files.readAllBytes(p.resolve("descriptor.json"));MeasuredAcknowledgmentHostTests.opened=Files.readAllBytes(p.resolve("before-public-reset/00.json"));
  ordinaryRefresh();positive(false);positive(true);
  if(!baseline){rollback(false);rollback(true);}
  System.out.println("PASS independent review controls cases="+cases+" checks="+checks+" baseline="+baseline+"; counterexamples are observed unsafe admissions, host scope only");
 }
}
