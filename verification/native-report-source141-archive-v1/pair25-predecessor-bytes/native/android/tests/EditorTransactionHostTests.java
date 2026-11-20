package dev.mixer.android;

import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.EditText;
import java.nio.file.Files;
import java.nio.file.Path;

/** Replay exact first-party C-entry frames; storage and native IME remain separate. */
public final class EditorTransactionHostTests {
    static Path packets;
    static int checks;
    static void check(boolean value,String label){checks++;if(!value)throw new AssertionError(label);}
    static byte[] frame(String name)throws Exception{return Files.readAllBytes(packets.resolve(name));}
    static void install(CompleteHandoffHostTests.Fixture f,String name)throws Exception{
        f.owner.installExternal(frame(name),CompleteHandoffHostTests.descriptor);
        check(f.owner.hasCommittedPresentation(),"committed "+name);
    }
    static InputConnection edit(CompleteHandoffHostTests.Fixture f,EditText field,String value)throws Exception{
        check(field.requestFocus(),"fresh editor focus");
        InputConnection connection=field.onCreateInputConnection(new EditorInfo());
        check(connection!=null&&connection.commitText(value,1),"fresh native edit");
        return connection;
    }
    static void resetAndSave()throws Exception{
        try(var f=new CompleteHandoffHostTests.Fixture()){
            f.settled();
            install(f,"before-public-reset/05.json");
            check(f.title.getText().toString().isEmpty()&&f.responsible.getText().toString().isEmpty(),"both fields reset");
            check(!f.titleConnection.commitText("stale",1)&&!f.responsibleConnection.commitText("stale",1),"consumed predecessors stay fenced");
            check(ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==0,"reset never recloses predecessors");
            var title=edit(f,f.title,CompleteHandoffHostTests.value(frame("after-public-reset/06.json"),"task.title"));
            install(f,"after-public-reset/06.json");
            var responsible=edit(f,f.responsible,CompleteHandoffHostTests.value(frame("after-public-reset/07.json"),"task.responsible"));
            install(f,"after-public-reset/07.json");
            ConcreteHostProbe.reset();install(f,"after-public-reset/08.json");install(f,"after-public-reset/09.json");
            check(!title.commitText("late",1)&&!responsible.commitText("late",1),"second save consumes new predecessors");
            check(ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry")==2&&ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==2,"second save retires each new editor once");
        }
    }
    static void navigateAndRestore()throws Exception{
        System.setProperty("mixer.host.modelRemovalOrder","true");
        try(var f=new CompleteHandoffHostTests.Fixture()){
            install(f,"before-public-queue/03.json");
            check(!f.renderer.inspectV2().containsKey("task.title")&&!f.renderer.inspectV2().containsKey("task.responsible"),"queue removes both editor views");
            check(!f.titleConnection.commitText("late",1)&&!f.responsibleConnection.commitText("late",1),"removed connections fenced");
            check(ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry")==2&&ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==2,"navigation retires each captured predecessor once");
            install(f,"after-public-queue/04.json");
            var title=(EditText)f.renderer.view("task.title");var responsible=(EditText)f.renderer.view("task.responsible");
            check(title.getText().toString().equals(CompleteHandoffHostTests.value(CompleteHandoffHostTests.echo,"task.title"))&&responsible.getText().toString().equals("Jo"),"both drafts restored");
            edit(f,responsible," continued");
        }finally{System.clearProperty("mixer.host.modelRemovalOrder");}
    }
    static void failureSiblingAndRetry()throws Exception{
        try(var f=FailureDismissalHostTests.editing()){
            Object siblingBuffer=f.responsible.getText();
            Object siblingRecord=f.renderer.inspectV2().get("task.responsible");
            f.owner.installExternal(FailureDismissalHostTests.dismissal,CompleteHandoffHostTests.descriptor);
            check(f.owner.hasCommittedPresentation()&&f.responsible.getText()==siblingBuffer&&f.renderer.inspectV2().get("task.responsible")==siblingRecord,"failure edit preserves unchanged sibling");
            check(f.responsible.getText().toString().equals("Jo"),"failure dismissal preserves sibling value");
            edit(f,f.responsible," retry");install(f,"after-public-failure-r136/06.json");
            ConcreteHostProbe.reset();install(f,"after-public-failure-r136/07.json");install(f,"after-public-failure-r136/08.json");
            check(ConcreteHostProbe.count("BaseInputConnection.finishComposingText","entry")==2&&ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==2,"retry retires two fresh editors once");
        }
    }
    public static void main(String[] args)throws Exception{
        packets=Path.of(args[0]);
        CompleteHandoffHostTests.descriptor=frame("descriptor.json");
        CompleteHandoffHostTests.opened=frame("before-public-reset/00.json");
        CompleteHandoffHostTests.titleEcho=frame("before-public-reset/01.json");
        CompleteHandoffHostTests.echo=frame("before-public-reset/02.json");
        CompleteHandoffHostTests.busy=frame("before-public-reset/03.json");
        CompleteHandoffHostTests.saved=frame("before-public-reset/04.json");
        CompleteHandoffHostTests.reset=frame("before-public-reset/05.json");
        CompleteHandoffHostTests.queue=frame("before-public-queue/03.json");
        FailureDismissalHostTests.failure=frame("after-public-failure/04.json");
        FailureDismissalHostTests.dismissal=frame("after-public-failure/05.json");
        resetAndSave();navigateAndRestore();failureSiblingAndRetry();
        System.out.println("PASS EditorTransactionHostTests cases=3 checks="+checks+" nativeRuntime=false storageExecuted=false");
    }
}
