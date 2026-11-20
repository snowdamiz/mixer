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
            var unfocused=(NativeAppearanceViewsV2.NativeField)responsible;
            f.root.hostWindowFocus(false);
            f.root.windowFocus=true;
            check(unfocused.attempt==null&&!unfocused.hasFocus(),"restored field has no input connection");
            int drawableCalls=ConcreteHostProbe.count("View.drawableStateChanged","entry");
            unfocused.setPressed(true);
            check(ConcreteHostProbe.count("View.drawableStateChanged","entry")==drawableCalls&&
                unfocused.attempt==null&&unfocused.getText().toString().equals("Jo"),
                "drawable refresh with no predecessor has no editor effects");
            f.root.hostWindowFocus(true);
            install(f,"after-public-queue/04.json");
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
    static void pendingPressDuringWindowRestore()throws Exception{
        try(var f=new CompleteHandoffHostTests.Fixture()){
            var field=(NativeAppearanceViewsV2.NativeField)f.responsible;
            String text=field.getText().toString();
            field.clearFocus();
            f.root.hostWindowFocus(false);
            int closes=ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry");
            int start=field.getSelectionStart(),end=field.getSelectionEnd(),events=f.events.size();
            var predecessor=field.attempt;
            check(predecessor.revoked&&predecessor.close==NativeAppearanceViewsV2.NativeField.Close.RETURNED&&
                ConcreteHostProbe.events().stream().filter(e->e.receiver==predecessor.target&&
                    e.method.equals("BaseInputConnection.closeConnection")&&e.phase.equals("entry")).count()==1,
                "focus loss closes this predecessor once");
            // Deliver the View press after the window reports focus, before this field receives its gain callback.
            f.root.windowFocus=true;
            check(field.hasWindowFocus()&&!field.hasFocus(),"window focused before field focus");
            int drawableCalls=ConcreteHostProbe.count("View.drawableStateChanged","entry");
            Runnable pendingPress=()->field.setPressed(true);
            pendingPress.run();
            check(ConcreteHostProbe.count("View.drawableStateChanged","entry")==drawableCalls,
                "unowned pending press does not enter the native drawable suffix");
            check(field.attempt==predecessor&&predecessor.revoked&&
                !f.responsibleConnection.commitText("late",1)&&!f.responsibleConnection.setSelection(0,0)&&
                f.responsibleConnection.getSelectedText(0)==null,"press leaves the captured predecessor revoked");
            f.responsibleConnection.closeConnection();
            check(field.getText().toString().equals(text)&&field.getSelectionStart()==start&&
                field.getSelectionEnd()==end&&f.events.size()==events,"pending press has no editor effects");
            f.root.hostWindowFocus(true);
            check(f.owner.hasCommittedPresentation()&&field.requestFocus(),"window and field focus recover");
            check(field.onCreateInputConnection(new EditorInfo())==null,"focus alone does not reopen the sealed owner");
            field.setPressed(false);
            check(ConcreteHostProbe.count("View.drawableStateChanged","entry")==drawableCalls&&field.attempt==predecessor,
                "pending drawable refresh still inert while owner is sealed");
            install(f,"before-public-reset/02.json");
            check(f.renderer.view("task.responsible")==field,"republishing retains the same editor");
            drawableCalls=ConcreteHostProbe.count("View.drawableStateChanged","entry");
            field.setPressed(true);
            check(ConcreteHostProbe.count("View.drawableStateChanged","entry")==drawableCalls+1,
                "drawable suffix resumes with field authority");
            check(edit(f,field," continued")!=f.responsibleConnection,"focus admits a fresh input connection");
            check(ConcreteHostProbe.count("BaseInputConnection.closeConnection","entry")==closes,
                "press and refocus never reclose the predecessor");
        }
    }
    static void parkedEditorEffectsStayFenced()throws Exception{
        try(var f=new CompleteHandoffHostTests.Fixture()){
            var field=(NativeAppearanceViewsV2.NativeField)f.responsible;
            String text=field.getText().toString();
            f.root.hostWindowFocus(false);
            f.root.windowFocus=true;
            int events=f.events.size(),selections=ConcreteHostProbe.count("TextView.onSelectionChanged","entry");
            try{
                field.setText("unauthorized",EditText.BufferType.EDITABLE);
                throw new AssertionError("parked text replacement accepted");
            }catch(IllegalStateException expected){
                check(field.getText().toString().equals(text)&&f.events.size()==events,"parked text replacement has no effects");
            }
            IllegalStateException quarantine;
            try{
                field.onSelectionChanged(0,0);
                throw new AssertionError("unowned selection callback accepted");
            }catch(IllegalStateException expected){
                quarantine=expected;
                check(expected.getMessage().equals("unknown retired editor callback"),"selection still fails closed");
            }
            check(!f.owner.hasCommittedPresentation()&&f.events.size()==events&&
                ConcreteHostProbe.count("TextView.onSelectionChanged","entry")==selections,"unowned selection quarantines before native dispatch");
            int drawableCalls=ConcreteHostProbe.count("View.drawableStateChanged","entry");
            try{
                field.setPressed(true);
                throw new AssertionError("terminal drawable callback accepted");
            }catch(IllegalStateException expected){
                check(expected==quarantine&&ConcreteHostProbe.count("View.drawableStateChanged","entry")==drawableCalls,
                    "terminal drawable callback surfaces the original failure without native dispatch");
            }
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
        pendingPressDuringWindowRestore();resetAndSave();navigateAndRestore();failureSiblingAndRetry();parkedEditorEffectsStayFenced();
        System.out.println("PASS EditorTransactionHostTests cases=5 checks="+checks+" nativeRuntime=false storageExecuted=false");
    }
}
