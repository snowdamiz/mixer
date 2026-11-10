package dev.mixer.android;

import android.text.Layout;
import android.view.View;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;

/** R168's executed tail-only counterexample, using the exact R164 inert leaves. */
public final class ContainerFrameWitnessHostTests {
    static int cases,checks;
    static boolean baseline;
    static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    static Object get(Object owner,String name){
        for(Class<?> c=owner.getClass();c!=null;c=c.getSuperclass())try{
            Field f=c.getDeclaredField(name);f.setAccessible(true);return f.get(owner);
        }catch(NoSuchFieldException e){}catch(Exception e){throw new AssertionError(e);}
        throw new AssertionError("missing field "+name);
    }
    static void set(Object owner,String name,Object value){
        for(Class<?> c=owner.getClass();c!=null;c=c.getSuperclass())try{
            Field f=c.getDeclaredField(name);f.setAccessible(true);f.set(owner,value);return;
        }catch(NoSuchFieldException e){}catch(Exception e){throw new AssertionError(e);}
        throw new AssertionError("missing field "+name);
    }
    static boolean sourceFrame(UiPacket packet,Map<String,NativeAppearanceViewsV2.Record> records)throws Exception{
        Method m=NativeRenderer.class.getDeclaredMethod("sourceFrameV3",UiPacket.class,Map.class,String.class);
        m.setAccessible(true);return (boolean)m.invoke(null,packet,records,"task.responsible");
    }
    static void shift(View view,String a,String b,int delta){
        MeasuredAcknowledgmentHostTests.frame(view,a,delta);MeasuredAcknowledgmentHostTests.frame(view,b,delta);
    }
    static int[] local(View view){return new int[]{view.getLeft(),view.getTop(),view.getRight(),view.getBottom()};}
    static byte[] tailPacket(boolean metric){
        var p=CompleteHandoffHostTests.packet(MeasuredAcknowledgmentHostTests.packet(2,"",""));
        Json.object(CompleteHandoffHostTests.node(p,"tasks.empty").get("properties")).put("text","R168 changed later text");
        Layout.hostHeights.put("R168 changed later text",metric?100:52);
        return CompleteHandoffHostTests.encode(p);
    }
    static Throwable install(MeasuredAcknowledgmentHostTests.Fixture f,byte[] packet){
        try{f.owner.installExternal(packet,MeasuredAcknowledgmentHostTests.descriptor);return null;}
        catch(RuntimeException e){return e;}finally{ConcreteHostProbe.hook=null;}
    }
    static void mutate(Map<String,NativeAppearanceViewsV2.Record> records,UiPacket packet,String kind,View foreign){
        var list=records.get("task.form");var field=records.get("task.responsible");
        switch(kind){
            case "y" -> shift(list.group,"top","bottom",37);
            case "x" -> shift(list.group,"left","right",37);
            case "height" -> MeasuredAcknowledgmentHostTests.frame(list.group,"bottom",37);
            case "width" -> MeasuredAcknowledgmentHostTests.frame(list.group,"right",37);
            case "group-parent" -> set(list.group,"parent",foreign);
            case "field-parent" -> set(field.view,"parent",foreign);
            case "ancestor-parent" -> set(records.get("task.fields").view,"parent",foreign);
            case "root-parent" -> set(records.get(packet.root.id).view,"parent",foreign);
            case "origin-x" -> list.group.absoluteX++;
            case "origin-y" -> list.group.absoluteY++;
            case "content-height" -> list.geometry.contentHeight+=1024;
            default -> throw new AssertionError(kind);
        }
    }
    @SuppressWarnings("unchecked")
    static void container(String side,String kind,boolean metric)throws Exception{
        try(var f=new MeasuredAcknowledgmentHostTests.Fixture(false)){
            check(f.connection.setSelection(0,f.edit.getText().length())&&f.connection.commitText("",1),"native empty source control");
            var records=f.renderer.inspectV2();var list=records.get("task.form");
            check(list.group!=list.view&&list.view instanceof NativeAppearanceViewsV2.NativeScroll,"distinct native container");
            var oldPacket=f.renderer.packet;var buffer=f.edit.getText();var target=f.edit.lastConnection;
            var attempt=((NativeAppearanceViewsV2.NativeField)f.edit).attempt;
            int normalY=MeasuredAcknowledgmentPreservationHostTests.pos(f.edit)[1];boolean[] hit={false};int[] candidateY={-1};
            Object witness=records.get("task.responsible").geometry.preparedFrame;
            int[] declared=local(f.edit),listFrame=local(list.view);
            if(side.equals("old")){
                check(sourceFrame(oldPacket,records),"old prepared path initially valid");
                mutate(records,oldPacket,kind,f.root);hit[0]=true;
                check(Arrays.equals(declared,local(f.edit))&&Arrays.equals(listFrame,local(list.view))&&
                    records.get("task.responsible").geometry.preparedFrame==witness,"declared field/scroll/witness untouched");
                if(!baseline)check(!sourceFrame(oldPacket,records),"old complete native path invalid after "+kind);
            }
            if(side.equals("candidate"))ConcreteHostProbe.hook=(method,phase)->{
                if(hit[0]||!method.equals("View.getLocationInWindow")||!phase.equals("entry")||ConcreteHostProbe.lastEvent().receiver!=f.edit)return;
                Object pending=get(f.renderer,"v2Pending");if(pending==null)return;
                hit[0]=true;
                var next=(UiPacket)get(pending,"next");var shadow=(Map<String,NativeAppearanceViewsV2.Record>)get(pending,"detached");
                try{check(sourceFrame(next,shadow),"final prepared candidate initially valid");}catch(Exception e){throw new AssertionError(e);}
                var field=shadow.get("task.responsible");var scroll=shadow.get("task.form");
                int[] before=local(field.view),scrollBefore=local(scroll.view);Object prepared=field.geometry.preparedFrame;
                candidateY[0]=MeasuredAcknowledgmentPreservationHostTests.pos(field.view)[1];mutate(shadow,next,kind,f.root);
                check(Arrays.equals(before,local(field.view))&&Arrays.equals(scrollBefore,local(scroll.view))&&field.geometry.preparedFrame==prepared,"final candidate declared frame/witness untouched");
                if(kind.equals("y"))check(MeasuredAcknowledgmentPreservationHostTests.pos(field.view)[1]==candidateY[0]+37,"candidate actual 37px drift reached after final prepare");
                if(!baseline)try{check(!sourceFrame(next,shadow),"candidate complete native path invalid after "+kind);}catch(Exception e){throw new AssertionError(e);}
            };
            Throwable error=install(f,tailPacket(metric));boolean accepted=error==null&&f.owner.hasCommittedPresentation();
            if(!side.equals("none"))check(hit[0],"actual injection reached "+side+"/"+kind);
            if(side.equals("none"))check(accepted,"ordinary tail metric acknowledgment accepted "+error);
            else if(!baseline||!metric)check(!accepted&&f.renderer.packet==oldPacket&&f.owner.cleanupLedger().primary()!=null,"unprepared carrier refuses without publication "+side+"/"+kind+" "+error);
            else if(kind.equals("y"))check(accepted,"exact R164 unsafe Y admission reproduced "+side+" "+error);
            if(accepted){
                check(f.renderer.view("task.responsible")==f.edit&&f.edit.getText()==buffer&&f.edit.lastConnection==target&&
                    ((NativeAppearanceViewsV2.NativeField)f.edit).attempt==attempt,"exact retained native editor/Editable/attempt/target");
                check(MeasuredAcknowledgmentPreservationHostTests.pos(f.edit)[1]==normalY,"tail-only metric has no required Responsible frame movement");
                check(f.connection.commitText("!",1),"original connection remains usable");
            }
            cases++;System.out.println((accepted&&!side.equals("none")?"COUNTEREXAMPLE":"PASS")+" carrier side="+side+" kind="+kind+" metric="+metric+" baseline="+baseline+" accepted="+accepted+" normalY="+normalY+" candidateY="+candidateY[0]+" injected="+hit[0]);
        }
    }
    @SuppressWarnings("unchecked")
    static void finalTamper(String kind)throws Exception{
        try(var f=new MeasuredAcknowledgmentHostTests.Fixture(false)){
            var old=f.renderer.packet;boolean[] hit={false};
            ConcreteHostProbe.hook=(m,p)->{
                if(hit[0]||!m.equals("View.getLocationInWindow")||!p.equals("entry")||ConcreteHostProbe.lastEvent().receiver!=f.edit)return;
                Object candidate=get(f.renderer,"v2Pending");if(candidate==null)return;hit[0]=true;
                var records=(Map<String,NativeAppearanceViewsV2.Record>)get(candidate,"detached");
                var record=records.get(kind.equals("ancestor-y")?"task.fields":"task.responsible");View view=record.view;
                switch(kind){
                    case "y","ancestor-y" -> shift(view,"top","bottom",1);
                    case "x" -> shift(view,"left","right",1);
                    case "height" -> MeasuredAcknowledgmentHostTests.frame(view,"bottom",1);
                    case "width" -> MeasuredAcknowledgmentHostTests.frame(view,"right",1);
                    case "input" -> set(record,"input",null);
                    case "fence" -> set(record,"editorFence",null);
                    case "null-witness" -> record.geometry.preparedFrame=null;
                    case "box" -> {var b=record.geometry.box;record.geometry.box=new NativeAppearanceViewsV2.Box(b.x(),b.y()+1,b.width(),b.height());}
                    case "witness" -> {
                        Object w=record.geometry.preparedFrame;
                        try{
                            var components=w.getClass().getRecordComponents();Object[] args=new Object[components.length];
                            for(int i=0;i<args.length;i++){var accessor=components[i].getAccessor();accessor.setAccessible(true);args[i]=accessor.invoke(w);if(components[i].getName().equals("absoluteY"))args[i]=(long)args[i]+1;}
                            Constructor<?> c=w.getClass().getDeclaredConstructors()[0];c.setAccessible(true);set(record.geometry,"preparedFrame",c.newInstance(args));
                        }catch(Exception e){throw new AssertionError(e);}
                    }
                    default -> throw new AssertionError(kind);
                }
            };
            Throwable failure=install(f,MeasuredAcknowledgmentHostTests.packet(2,MeasuredAcknowledgmentHostTests.VALUE,""));
            check(hit[0]&&failure!=null&&!f.owner.hasCommittedPresentation()&&f.renderer.packet==old&&f.owner.cleanupLedger().primary()!=null,"final prepared refusal "+kind);
            cases++;System.out.println("PASS final prepared refusal "+kind);
        }
    }
    static void alreadyShaped()throws Exception{
        try(var f=new MeasuredAcknowledgmentHostTests.Fixture(false)){
            var record=f.renderer.inspectV2().get("task.responsible");check(record.geometry.nativeTextHeightPx==52,"published metric52");
            set(f.edit,"textLayout",new Layout(f.edit.getText(),f.edit.getTextSize(),1048576,1));
            check(f.edit.getLayout().getHeight()==64&&f.edit.getHeight()==115,"native already shaped64 under old frame115");
            check(install(f,MeasuredAcknowledgmentHostTests.packet(2,MeasuredAcknowledgmentHostTests.VALUE,""))==null&&
                f.edit.getTop()==298&&f.edit.getHeight()==116,"R161 already-shaped native acknowledgment");
            check(f.connection.commitText("!",1),"already shaped original connection works");
            cases++;System.out.println("PASS R161 current native Layout64 / old prepared52 -> top298 hit116");
        }
    }
    static void disableAndLegacy(Path packets)throws Exception{
        FocusedDisableOwnerTransitionHostTests.descriptor=Files.readAllBytes(packets.resolve("descriptor.json"));
        FocusedDisableOwnerTransitionHostTests.echo=Files.readAllBytes(packets.resolve("synthesized-acknowledged-presave.json"));
        FocusedDisableOwnerTransitionHostTests.busy=Files.readAllBytes(packets.resolve("201-2.json"));
        FocusedDisableOwnerTransitionHostTests.saved=Files.readAllBytes(packets.resolve("201-3.json"));
        FocusedDisableOwnerTransitionHostTests.opened=FocusedDisableOwnerTransitionHostTests.settledOpened();
        FocusedDisableOwnerTransitionHostTests.save(false,"");
        FocusedDisableOwnerTransitionHostTests.controls();FocusedDisableOwnerTransitionHostTests.legacy();
        for(String fault:List.of("finish","close","attach","rollback"))FocusedDisableOwnerTransitionHostTests.save(false,fault);
        System.out.println("PASS R98 actual save / legacy V2 / owner binding geometry guards / fault controls");
    }
    public static void main(String[] args)throws Exception{
        Path packets=Path.of(args[0]);baseline=args[1].equals("baseline");
        MeasuredAcknowledgmentHostTests.descriptor=Files.readAllBytes(packets.resolve("descriptor.json"));
        MeasuredAcknowledgmentHostTests.opened=Files.readAllBytes(packets.resolve("before-public-reset/00.json"));
        MeasuredAcknowledgmentPreservationHostTests.baseline=false;MeasuredAcknowledgmentPreservationHostTests.ordinaryRefresh();MeasuredAcknowledgmentPreservationHostTests.positive(false);MeasuredAcknowledgmentPreservationHostTests.positive(true);
        alreadyShaped();container("none","y",true);
        for(String side:List.of("old","candidate")){
            container(side,"y",true);container(side,"y",false);
            for(String kind:List.of("height","x","width","group-parent","field-parent","ancestor-parent","root-parent","origin-x","origin-y","content-height"))container(side,kind,true);
        }
        for(String kind:List.of("y","height","ancestor-y","x","width","input","fence","null-witness","box","witness"))finalTamper(kind);
        for(String kind:List.of("old-y","old-height","old-parent-y","recipe","binding","actions","generation","topology","revoked"))MeasuredAcknowledgmentHostTests.refusal(kind);
        MeasuredAcknowledgmentPreservationHostTests.rollback(false);MeasuredAcknowledgmentPreservationHostTests.rollback(true);
        if(!baseline)disableAndLegacy(Path.of(args[2]));
        System.out.println("PASS R172 focused host cases="+cases+" checks="+checks+" inheritedReviewCases="+MeasuredAcknowledgmentPreservationHostTests.cases+" inheritedReviewChecks="+MeasuredAcknowledgmentPreservationHostTests.checks+" authorCases="+MeasuredAcknowledgmentHostTests.cases+" authorChecks="+MeasuredAcknowledgmentHostTests.checks+" baseline="+baseline);
    }
}
