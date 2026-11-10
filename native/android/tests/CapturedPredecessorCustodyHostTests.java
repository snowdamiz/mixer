package dev.mixer.android;

import android.view.View;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/** Recorded public packets, production owner/renderer, instrumented platform leaves. */
public final class CapturedPredecessorCustodyHostTests {
    static int cases,checks;
    static void check(boolean value,String label){checks++;if(!value)throw new AssertionError(label);}
    static NativeAppearanceViewsV2.NativeField field(CompleteHandoffHostTests.Fixture f,String name){
        return (NativeAppearanceViewsV2.NativeField)(name.equals("title")?f.title:f.responsible);
    }
    static long count(Object receiver,String method){return ConcreteHostProbe.events().stream().filter(e->e.receiver==receiver&&e.method.equals("BaseInputConnection."+method)&&e.phase.equals("entry")).count();}
    static void passed(String label){cases++;System.out.println("PASS "+label);}
    static void replacement(String name,String method,String phase,String replacement,boolean error)throws Exception{
        String label=name+"/"+method+"/"+phase+"/"+replacement+"/error="+error;
        var f=new CompleteHandoffHostTests.Fixture();
        var field=field(f,name);var original=field.attempt;
        var foreign=new NativeAppearanceViewsV2.NativeField.Attempt(original.editable,new EditorInfo());
        foreign.target=new BaseInputConnection(field,true);
        if(replacement.equals("consumed")){foreign.revoked=true;foreign.close=NativeAppearanceViewsV2.NativeField.Close.RETURNED;}
        var injected=new IllegalStateException("captured prefix "+label);
        boolean[] hit={false};NativeAppearanceViewsV2.FieldTransition[] captured={null};
        ConcreteHostProbe.hook=(m,p)->{
            if(hit[0]||!m.equals("BaseInputConnection."+method)||!p.equals(phase)||ConcreteHostProbe.lastEvent().receiver!=original.target)return;
            hit[0]=true;captured[0]=field.record.fieldTransition;
            check(captured[0]!=null&&captured[0].predecessor==original&&captured[0].target==original.target&&captured[0].editable==original.editable,"immutable capture "+label);
            field.attempt=replacement.equals("null")?null:foreign;
            if(error)throw injected;
        };
        f.quarantined=true;
        try{
            f.refused(CompleteHandoffHostTests.queue,label);
            check(hit[0],"boundary reached "+label);
            var scope=captured[0];
            check(scope.registered&&!scope.ended&&field.record.fieldTransition==scope&&f.renderer.editorDisposalBusyV2(),"captured custody retained "+label);
            check(count(original.target,"finishComposingText")==1&&count(original.target,"closeConnection")== (method.equals("closeConnection")?1:0),"original prefix exactly once "+label);
            check(count(foreign.target,"finishComposingText")==0&&count(foreign.target,"closeConnection")==0,"current slot never supplies cleanup authority "+label);
            if(error)check(f.owner.cleanupLedger().primary()==injected,"original injected error retained "+label);
            else check(f.owner.cleanupLedger().primary()!=null,"original refusal retained "+label);
            if(method.equals("closeConnection")){
                check(scope.closeReturned==!error,"actual close return evidence "+label);
                check(original.close==(error?NativeAppearanceViewsV2.NativeField.Close.FAILED_UNCERTAIN:NativeAppearanceViewsV2.NativeField.Close.RETURNED),"captured close disposition "+label);
            }else check(!scope.closeReturned&&original.close!=NativeAppearanceViewsV2.NativeField.Close.FAILED_UNCERTAIN,"no invented close attempt "+label);
            var primary=f.owner.cleanupLedger().primary();f.close();
            check(f.owner.cleanupLedger().primary()==primary,"cleanup keeps original error "+label);
        }catch(Throwable failure){ConcreteHostProbe.hook=null;throw failure;}
        passed(label);
    }
    static void noEffect(String name,boolean mismatch)throws Exception{
        String label="no-effect/"+name+"/mismatch="+mismatch;
        var f=new CompleteHandoffHostTests.Fixture();var field=field(f,name);var original=field.attempt;
        var injected=new IllegalStateException(label);boolean[] hit={false};NativeAppearanceViewsV2.FieldTransition[] captured={null};
        ConcreteHostProbe.hook=(m,p)->{
            var scope=field.record.fieldTransition;
            if(hit[0]||!m.equals("TextView.getEditableText")||!p.equals("entry")||ConcreteHostProbe.lastEvent().receiver!=field||scope==null||scope.irreversible)return;
            hit[0]=true;captured[0]=scope;
            if(mismatch)field.attempt=null;else throw injected;
        };
        try(f){
            f.refused(CompleteHandoffHostTests.queue,label);check(hit[0],"no effect boundary reached");
            check(!captured[0].irreversible&&captured[0].ended&&!captured[0].registered&&!f.renderer.editorDisposalBusyV2(),"no effect scope released");
            check(original.close!=NativeAppearanceViewsV2.NativeField.Close.FAILED_UNCERTAIN&&!captured[0].closeReturned,"membership mismatch did not fabricate uncertain close");
            check(count(original.target,"finishComposingText")==0,"no finish began");
            if(!mismatch)check(f.owner.cleanupLedger().primary()==injected,"no effect original error retained");
        }
        passed(label);
    }
    static void refusedFinish(String name)throws Exception{
        var f=new CompleteHandoffHostTests.Fixture();var field=field(f,name);var original=field.attempt;boolean[] hit={false};
        ConcreteHostProbe.hook=(m,p)->{
            if(!hit[0]&&m.equals("BaseInputConnection.finishComposingText")&&p.equals("entry")&&ConcreteHostProbe.lastEvent().receiver==original.target){hit[0]=true;((BaseInputConnection)original.target).closed=true;}
        };
        f.quarantined=true;
        try(f){
            f.refused(CompleteHandoffHostTests.queue,"finish refused "+name);check(hit[0],"finish refusal reached");
            check(field.record.fieldTransition!=null&&field.record.fieldTransition.registered,"refused finish retains original permit");
            check(count(original.target,"finishComposingText")==1&&count(original.target,"closeConnection")==0,"refused finish never retried");
            check(f.owner.cleanupLedger().primary().getMessage().equals("native composition finish refused"),"finish refusal remains primary");
        }
        passed("refused-finish/"+name);
    }
    static boolean descendant(View view,View ancestor){
        for(View at=view;at!=null;at=at.getParent() instanceof View parent?parent:null)if(at==ancestor)return true;
        return false;
    }
    static void traceScope(String label,NativeAppearanceViewsV2.FieldTransition scope,Object receiver){
        var call=scope.removalCall;
        System.out.println("TRACE "+label+" scope="+System.identityHashCode(scope)+" field="+System.identityHashCode(scope.field)+
            " phase="+scope.phase+" hooks="+scope.hooks+" registered="+scope.registered+" ended="+scope.ended+
            " executing="+(call!=null&&call.executing)+" returned="+(call!=null&&call.returned)+
            " parent="+(call==null?0:System.identityHashCode(call.parent))+" child="+(call==null?0:System.identityHashCode(call.child))+
            " receiver="+System.identityHashCode(receiver)+" removalLosses="+scope.removalLosses+
            " closeReturned="+scope.closeReturned+" finish="+count(scope.target,"finishComposingText")+" close="+count(scope.target,"closeConnection"));
    }
    static void platformRemoval()throws Exception{
        System.setProperty("mixer.host.modelRemovalOrder","true");
        try(var f=new CompleteHandoffHostTests.Fixture()){
            var title=field(f,"title");var responsible=field(f,"responsible");
            var a=title.attempt;var b=responsible.attempt;
            NativeAppearanceViewsV2.FieldTransition[] scopes={null,null};
            ConcreteHostProbe.hook=(m,p)->{
                if(m.equals("ViewGroup.removeViewAt")&&p.equals("entry")){
                    for(int i=0;i<2;i++){
                        var scope=(i==0?title:responsible).record.fieldTransition;
                        if(scope!=null&&scope.removalCall!=null){
                            traceScope("platform/"+(i==0?"title":"responsible")+"/removeEntry",scope,ConcreteHostProbe.lastEvent().receiver);
                            if(scope.removalCall.executing){
                                scopes[i]=scope;
                                check(!scope.removalCall.returned&&scope.removalCall.parent==ConcreteHostProbe.lastEvent().receiver,"parent-bound removal before platform entry");
                                check(descendant(scope.field,scope.removalCall.child)&&scope.removalCall.child.getParent()==scope.removalCall.parent,"exact captured removal descendant before entry");
                                check(scope.removalCall.original==scope.original&&java.util.Arrays.asList(scope.removalCall.scopes).contains(scope),"original mutation and exact descendant cohort");
                            }
                        }
                    }
                }
                if(m.equals("ViewGroup.removeViewAt")&&p.equals("beforeReturn")||m.startsWith("View.on")&&(ConcreteHostProbe.lastEvent().receiver==title||ConcreteHostProbe.lastEvent().receiver==responsible)){
                    for(var scope:scopes)if(scope!=null&&scope.removalCall.executing)traceScope("platform/"+m+"/"+p,scope,ConcreteHostProbe.lastEvent().receiver);
                }
            };
            f.owner.installExternal(CompleteHandoffHostTests.queue,CompleteHandoffHostTests.descriptor);ConcreteHostProbe.hook=null;
            check(f.owner.hasCommittedPresentation()&&!f.renderer.editorDisposalBusyV2(),"model removal commits without custody leak");
            check(!f.renderer.inspectV2().containsKey("task.title")&&!f.renderer.inspectV2().containsKey("task.responsible"),"both fields removed");
            for(var scope:scopes){
                check(scope!=null&&scope.removalCall.returned&&!scope.removalCall.executing&&scope.ended&&!scope.registered,"one completed owned removal");
                for(var event:List.of(NativeAppearanceViewsV2.FieldLifecycle.WINDOW_VISIBILITY,NativeAppearanceViewsV2.FieldLifecycle.WINDOW_FOCUS,NativeAppearanceViewsV2.FieldLifecycle.AGGREGATE,NativeAppearanceViewsV2.FieldLifecycle.DETACH))
                    check((scope.removalLosses&event.bit())!=0,"owned platform lifecycle "+event);
            }
            check(count(a.target,"finishComposingText")==1&&count(a.target,"closeConnection")==1&&count(b.target,"finishComposingText")==1&&count(b.target,"closeConnection")==1,"two actual predecessor pairs once");
            int events=f.events.size();check(!f.titleConnection.commitText("late",1)&&!f.responsibleConnection.commitText("late",1)&&f.events.size()==events,"both old connections fenced");
            var trace=ConcreteHostProbe.events();
            int visibility=-1,detach=-1;
            for(int i=0;i<trace.size();i++){var event=trace.get(i);if(event.receiver==responsible&&event.phase.equals("entry")){if(event.method.equals("View.onWindowVisibilityChanged"))visibility=i;if(event.method.equals("View.onDetachedFromWindow"))detach=i;}}
            check(visibility>=0&&detach>visibility,"visibility precedes actual detach in platform leaf");
        }finally{System.clearProperty("mixer.host.modelRemovalOrder");}
        passed("production-removeViewAt/platform-visibility-focus-aggregate-detach");
    }
    static void unownedLoss(String name,String kind)throws Exception{
        System.setProperty("mixer.host.modelRemovalOrder","true");
        var f=new CompleteHandoffHostTests.Fixture();var field=field(f,name);var original=field.attempt;
        boolean[] hit={false};NativeAppearanceViewsV2.FieldTransition[] scope={null};
        ConcreteHostProbe.hook=(m,p)->{
            if(hit[0]||!p.equals("entry"))return;
            boolean outside=kind.equals("outside")&&m.equals("BaseInputConnection.finishComposingText")&&ConcreteHostProbe.lastEvent().receiver==original.target;
            boolean inside=!kind.equals("outside")&&m.equals("View.onWindowVisibilityChanged")&&ConcreteHostProbe.lastEvent().receiver==field;
            if(!outside&&!inside)return;
            hit[0]=true;scope[0]=field.record.fieldTransition;
            traceScope("unowned/"+name+"/"+kind+"/inject",scope[0],ConcreteHostProbe.lastEvent().receiver);
            if(outside)field.hostWindowVisibility(View.INVISIBLE);
            else if(kind.equals("reentrant"))field.hostWindowFocus(false);
            else if(kind.equals("duplicate"))field.hostWindowVisibility(View.INVISIBLE);
            else field.hostAttach(new Object());
        };
        f.quarantined=true;
        try(f){
            f.refused(CompleteHandoffHostTests.queue,"unowned "+name+"/"+kind);check(hit[0],"unowned lifecycle reached");
            traceScope("unowned/"+name+"/"+kind+"/refused",scope[0],field);
            System.out.println("TRACE primary="+f.owner.cleanupLedger().primary()+" busy="+f.renderer.editorDisposalBusyV2());
            check(scope[0]!=null&&scope[0].registered&&!scope[0].ended&&f.renderer.editorDisposalBusyV2(),"unowned removal/loss retains custody");
            if(!kind.equals("outside"))check(scope[0].removalCall!=null&&!scope[0].removalCall.returned,"failed removal cannot be retried");
            check(count(original.target,"finishComposingText")==1&&count(original.target,"closeConnection")<=1,"unowned loss never repeats prefix");
            check(f.owner.cleanupLedger().primary()!=null,"unowned lifecycle primary retained");
        }finally{System.clearProperty("mixer.host.modelRemovalOrder");}
        passed("unowned/"+name+"/"+kind);
    }
    public static void main(String[] args)throws Exception{
        Path p=Path.of(args[0]),flow=p.resolve("before-public-reset");
        CompleteHandoffHostTests.descriptor=Files.readAllBytes(p.resolve("descriptor.json"));
        CompleteHandoffHostTests.opened=Files.readAllBytes(flow.resolve("00.json"));
        CompleteHandoffHostTests.titleEcho=Files.readAllBytes(flow.resolve("01.json"));
        CompleteHandoffHostTests.echo=Files.readAllBytes(flow.resolve("02.json"));
        CompleteHandoffHostTests.busy=Files.readAllBytes(flow.resolve("03.json"));
        CompleteHandoffHostTests.saved=Files.readAllBytes(flow.resolve("04.json"));
        CompleteHandoffHostTests.reset=Files.readAllBytes(flow.resolve("05.json"));
        CompleteHandoffHostTests.queue=Files.readAllBytes(p.resolve("before-public-queue/03.json"));
        for(String name:List.of("title","responsible")){
            for(String method:List.of("finishComposingText","closeConnection"))for(String phase:List.of("entry","beforeReturn"))
                for(String replacement:List.of("null","consumed","active"))for(boolean error:new boolean[]{false,true})replacement(name,method,phase,replacement,error);
            for(boolean mismatch:new boolean[]{false,true})noEffect(name,mismatch);
            refusedFinish(name);
        }
        platformRemoval();
        for(String name:List.of("title","responsible"))for(String kind:List.of("outside","reentrant","duplicate","foreign-gain"))unownedLoss(name,kind);
        System.out.println("PASS CapturedPredecessorCustodyHostTests cases="+cases+" checks="+checks+" nativeRuntime=false");
    }
}
