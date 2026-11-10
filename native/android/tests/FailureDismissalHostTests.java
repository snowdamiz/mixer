package dev.mixer.android;

import android.view.inputmethod.EditorInfo;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/** Permanent regression: real failed-save packets and complete per-field refusal controls. */
public final class FailureDismissalHostTests {
    static byte[] failure,dismissal;
    static int cases;
    static void check(boolean value,String label){CompleteHandoffHostTests.check(value,label);}
    static CompleteHandoffHostTests.Fixture editing()throws Exception{
        var f=new CompleteHandoffHostTests.Fixture();
        f.owner.installExternal(CompleteHandoffHostTests.busy,CompleteHandoffHostTests.descriptor);
        f.owner.installExternal(failure,CompleteHandoffHostTests.descriptor);
        check(f.owner.hasCommittedPresentation()&&f.title.isEnabled()&&f.responsible.isEnabled(),"real failure UI enabled");
        check(f.title.requestFocus(),"fresh title focus");f.titleConnection=f.title.onCreateInputConnection(new EditorInfo());
        check(f.titleConnection!=null&&f.titleConnection.commitText(" retry",1),"first native edit after failure");
        ConcreteHostProbe.reset();return f;
    }
    static byte[] variant(String change){
        var p=CompleteHandoffHostTests.packet(dismissal);
        var field=CompleteHandoffHostTests.node(p,"task.responsible");
        var ancestor=CompleteHandoffHostTests.node(p,"task.fields");
        switch(change){
        case "other-buffer" -> {} // The live native buffer is changed independently below.
        case "field-style" -> Json.object(field.get("properties")).put("accessibilityIdentifier","foreign-style");
        case "field-actions" -> field.put("actions",List.of(Json.map("event","textChange","id","foreign.change")));
        case "field-generation" -> {
            for(Object i:Json.array(p.get("identities"))){var id=Json.object(i);if("task.responsible".equals(id.get("id")))id.put("generation",new Json.Num("999"));}
        }
        case "ancestor-style" -> Json.object(ancestor.get("properties")).put("title","Changed");
        case "ancestor-actions" -> ancestor.put("actions",List.of(Json.map("event","activate","id","foreign.activate")));
        case "ancestor-generation" -> {
            for(Object i:Json.array(p.get("identities"))){var id=Json.object(i);if("task.fields".equals(id.get("id")))id.put("generation",new Json.Num("999"));}
        }
        case "prefix-order" -> Collections.swap(Json.array(ancestor.get("children")),0,1);
        case "reparent" -> {
            Json.array(ancestor.get("children")).remove(field);
            Json.array(CompleteHandoffHostTests.node(p,"task.form").get("children")).add(field);
        }
        case "unknown-close" -> {} // Native disposition is changed below.
        default -> throw new AssertionError(change);
        }
        return CompleteHandoffHostTests.encode(p);
    }
    static void unchanged()throws Exception{
        try(var f=editing()){
            var titleRecord=f.renderer.inspectV2().get("task.title");var responsibleRecord=f.renderer.inspectV2().get("task.responsible");
            var titleBuffer=f.title.getText();var responsibleBuffer=f.responsible.getText();
            var title=(NativeAppearanceViewsV2.NativeField)f.title;var responsible=(NativeAppearanceViewsV2.NativeField)f.responsible;
            var titleAttempt=title.attempt;var responsibleAttempt=responsible.attempt;var target=title.lastConnection;
            int events=f.events.size();
            f.owner.installExternal(dismissal,CompleteHandoffHostTests.descriptor);
            check(f.owner.hasCommittedPresentation(),"ordinary failure dismissal accepted");
            check(f.renderer.inspectV2().get("task.title")==titleRecord&&f.renderer.inspectV2().get("task.responsible")==responsibleRecord,"same per-field records");
            check(f.title.getText()==titleBuffer&&f.responsible.getText()==responsibleBuffer&&title.attempt==titleAttempt&&
                responsible.attempt==responsibleAttempt&&title.lastConnection==target,"same buffers, attempts and target");
            check(f.events.size()==events&&ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry")==0&&
                ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==0,"model echo neither emits nor consumes predecessor");
            check(f.titleConnection.commitText(" later",1)&&f.events.size()==events+1,"unchanged active editor remains usable");
        }
        cases++;System.out.println("PASS failure dismissal retains both field owners and active target");
    }
    static void refusals()throws Exception{
        for(String change:List.of("field-style","field-actions","field-generation","ancestor-style","ancestor-actions","ancestor-generation","prefix-order","reparent","other-buffer","unknown-close")){
            try(var f=editing()){
                if(change.equals("other-buffer")){
                    check(f.responsible.requestFocus(),"other native focus");f.responsibleConnection=f.responsible.onCreateInputConnection(new EditorInfo());
                    check(f.responsibleConnection!=null&&f.responsibleConnection.commitText(" unacknowledged",1),"other field unacknowledged buffer");
                }else if(change.equals("unknown-close")){
                    var a=((NativeAppearanceViewsV2.NativeField)f.title).attempt;
                    a.revoked=true;a.close=NativeAppearanceViewsV2.NativeField.Close.FAILED_UNCERTAIN;
                }
                f.refused(variant(change),"dismissal "+change);
                check(!f.titleConnection.commitText("late",1),"title late input refused "+change);
            }
            cases++;System.out.println("PASS failure dismissal refusal "+change);
        }
    }
    public static void main(String[] args)throws Exception{
        Path p=Path.of(args[0]);CompleteHandoffHostTests.descriptor=Files.readAllBytes(p.resolve("descriptor.json"));
        Path flow=p.resolve("before-public-reset");
        CompleteHandoffHostTests.opened=Files.readAllBytes(flow.resolve("00.json"));
        CompleteHandoffHostTests.titleEcho=Files.readAllBytes(flow.resolve("01.json"));
        CompleteHandoffHostTests.echo=Files.readAllBytes(flow.resolve("02.json"));
        CompleteHandoffHostTests.busy=Files.readAllBytes(flow.resolve("03.json"));
        failure=Files.readAllBytes(p.resolve("after-public-failure/04.json"));dismissal=Files.readAllBytes(p.resolve("after-public-failure/05.json"));
        unchanged();refusals();
        System.out.println("PASS FailureDismissalHostTests cases="+cases+" checks="+CompleteHandoffHostTests.checks+" nativeRuntime=false");
    }
}
