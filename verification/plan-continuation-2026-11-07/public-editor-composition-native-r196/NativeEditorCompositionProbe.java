package dev.fieldlog.probe.r196;

import android.app.Activity;
import android.app.Application;
import android.app.Instrumentation;
import android.content.ComponentName;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.Choreographer;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Iterator;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import org.json.JSONArray;
import org.json.JSONObject;

import android.text.Editable;
import android.view.inputmethod.BaseInputConnection;
public final class NativeEditorCompositionProbe extends Instrumentation {
    private static final String PACKAGE="dev.fieldlog.workspace111";
    private static final String ACTIVITY="dev.fieldlog.generatedr90.androidhost.PublicActivity";
    private static final String TITLE_HINT="What needs to happen?", PERSON_HINT="Responsible person (optional)";
    private static final long RPC_MS=1500;
    private final Handler main=new Handler(Looper.getMainLooper());
    private final List<OwnedConnection> owned=new ArrayList<>();
    private final AtomicReference<Activity> resumed=new AtomicReference<>();
    private volatile boolean unknownMainCall;
    private long deadline;
    private Application application;
    private boolean registered;
    private String phase="created";
    private final Application.ActivityLifecycleCallbacks lifecycle =
            new Application.ActivityLifecycleCallbacks() {
                @Override public void onActivityCreated(Activity a, Bundle state) { }
                @Override public void onActivityStarted(Activity a) { }
                @Override public void onActivityResumed(Activity a) {
                    if (ACTIVITY.equals(a.getClass().getName()) && PACKAGE.equals(a.getPackageName())) {
                        resumed.set(a);
                    }
                }
                @Override public void onActivityPaused(Activity a) { resumed.compareAndSet(a, null); }
                @Override public void onActivityStopped(Activity a) { }
                @Override public void onActivitySaveInstanceState(Activity a, Bundle state) { }
                @Override public void onActivityDestroyed(Activity a) { resumed.compareAndSet(a, null); }
            };


    @Override public void onCreate(Bundle arguments) { super.onCreate(arguments); start(); }
    @Override public void onStart() {
        deadline=SystemClock.elapsedRealtime()+60000;
        JSONObject result=new JSONObject();
        boolean passed=false;
        byte[] before=null;
        try {
            result.put("probe","public-editor-composition-r196").put("sdkInt",Build.VERSION.SDK_INT)
                    .put("scope","Direct real platform InputConnection composition/selection; no Save or OS IME-service parity")
                    .put("publicSDK","d2172767c3d0d1984bc853e32a98e698f46dd603").put("steps",new JSONArray());
            require(PACKAGE.equals(getTargetContext().getPackageName()),"Wrong target package");
            before=repository(); JSONObject baseline=new JSONObject(new String(before,StandardCharsets.UTF_8));
            require(baseline.getJSONArray("tasks").length()==6 && baseline.getJSONArray("outbox").length()==10,"Expected six tasks and ten outbox; preserve and stop");
            phase="async-activity-launch";
            application=(Application)getTargetContext().getApplicationContext();
            call(()->{ application.registerActivityLifecycleCallbacks(lifecycle);registered=true;
                Intent launch=new Intent().setComponent(new ComponentName(PACKAGE,ACTIVITY));launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);getTargetContext().startActivity(launch);return null; });
            await("ready empty native form",15000,()->{
                if(resumed.get()==null)return false;
                Fields f=fields();return f!=null && f.title.isShown() && f.person.isShown() && f.title.isEnabled() && f.person.isEnabled() && f.title.getText().length()==0 && f.person.getText().length()==0 && !f.save.isEnabled(); });
            phase="focus";
            call(()->{require(edit(TITLE_HINT).requestFocus(),"Native focus denied");return null;});
            await("focused native Title",5000,()->{EditText v=edit(TITLE_HINT);return v.isFocused() && v.hasWindowFocus() && resumed.get().getCurrentFocus()==v;});
            OwnedConnection c=call(()->{EditText v=edit(TITLE_HINT);InputConnection actual=v.onCreateInputConnection(new EditorInfo());require(actual!=null,"No real InputConnection");OwnedConnection value=new OwnedConnection(actual,v);owned.add(value);return value;});
            Editable editable=call(()->c.view.getText());
            phase="composing-batch";
            call(()->{
                require(c.input.beginBatchEdit(),"beginBatchEdit refused");
                require(c.input.setComposingText("caf",1),"First composing text refused");
                require(c.input.setComposingText("cafe\u0301",1),"Second composing text refused");
                // Direct editor endBatchEdit may return false when the final batch ends.
                result.put("endBatchEditResult",c.input.endBatchEdit());
                return null;
            });
            settle(c,editable,"cafe\u0301",result,"composing-ack");
            call(()->{require(BaseInputConnection.getComposingSpanStart(editable)==0 && BaseInputConnection.getComposingSpanEnd(editable)==5,"Composing range changed during acknowledgement");require(c.view.getSelectionStart()==5 && c.view.getSelectionEnd()==5,"Composing cursor changed");return null;});
            phase="composing-region";
            call(()->{require(c.input.setComposingRegion(0,5),"Composing region refused");require(BaseInputConnection.getComposingSpanStart(editable)==0 && BaseInputConnection.getComposingSpanEnd(editable)==5,"Composing region differs");return null;});
            phase="finish-composition";
            call(()->{require(c.input.finishComposingText(),"finishComposingText refused");require(BaseInputConnection.getComposingSpanStart(editable)==-1 && BaseInputConnection.getComposingSpanEnd(editable)==-1,"Composition did not finish");require("cafe\u0301".contentEquals(editable),"Finishing composition changed text");return null;});
            settle(c,editable,"cafe\u0301",result,"finished-ack");
            phase="selection-and-replacement";
            call(()->{require(c.input.setSelection(3,5),"Selection refused");require(c.view.getSelectionStart()==3 && c.view.getSelectionEnd()==5,"UTF16 selection differs");require(c.input.commitText("\u00e9",1),"Selection replacement refused");return null;});
            settle(c,editable,"caf\u00e9",result,"replacement-ack");
            call(()->{require(c.view.getSelectionStart()==4 && c.view.getSelectionEnd()==4,"Replacement cursor differs");return null;});
            phase="delete-surrounding";
            call(()->{require(c.input.deleteSurroundingText(1,0),"Surrounding deletion refused");return null;});
            settle(c,editable,"caf",result,"delete-ack");
            call(()->{require(c.view.getSelectionStart()==3 && c.view.getSelectionEnd()==3,"Deletion cursor differs");return null;});
            phase="repository-preservation";
            require(Arrays.equals(before,repository()),"Unsaved editing changed repository bytes");
            result.put("sameViewAndEditable",true).put("compositionSpanRetainedAcrossFrames",true)
                    .put("selectionReplacementExact",true).put("deletionExact",true).put("finalText","caf")
                    .put("repositoryUnchanged",true).put("tasks",6).put("outbox",10).put("SaveAttempted",false);
            passed=true;
        } catch(Throwable error) {put(result,"failurePhase",phase);put(result,"error",error.toString());}
        finally {
            try {
                require(!unknownMainCall,"Unknown main RPC: do not retry cleanup");
                for(OwnedConnection c:owned)closeOnce(c);
                if(registered)call(()->{application.unregisterActivityLifecycleCallbacks(lifecycle);registered=false;return null;});
                put(result,"testConnectionsClosed",true);
            } catch(Throwable error) {passed=false;put(result,"testConnectionsClosed",false);put(result,"cleanupError",error.toString());}
            put(result,"unknownMainCall",unknownMainCall);put(result,"ownedConnectionCount",owned.size());
            if(before!=null)try{boolean same=Arrays.equals(before,repository());put(result,"repositoryUnchangedAtExit",same);if(!same)passed=false;}catch(Throwable error){passed=false;put(result,"repositoryObservationError",error.toString());}
            put(result,"status",passed?"PASS":"FAIL");Bundle out=new Bundle();out.putString("r196_status",passed?"PASS":"FAIL");out.putString("r196_summary_json",result.toString());out.putString(REPORT_KEY_STREAMRESULT,"\nFIELDLOG_COMPOSITION_R196 "+result+"\n");finish(passed?Activity.RESULT_OK:Activity.RESULT_CANCELED,out);
        }
    }
    private byte[] repository() throws Exception {return Files.readAllBytes(new File(getTargetContext().getFilesDir(),"FieldLog/workspace.json").toPath());}
    private void settle(OwnedConnection c,Editable editable,String expected,JSONObject result,String checkpoint) throws Exception {
        phase=checkpoint;
        await("native echo/model Save ready",10000,()->edit(TITLE_HINT)==c.view && c.view.getText()==editable && expected.contentEquals(editable) && requireFields().save.isEnabled() && c.view.isFocused() && c.view.hasWindowFocus());
        for(int i=0;i<3;i++) {
            frame();Thread.sleep(100);
            call(()->{require(edit(TITLE_HINT)==c.view && c.view.getText()==editable && expected.contentEquals(editable),"Editor/Editable/text changed after frame");require(requireFields().save.isEnabled(),"Model disabled Save");return null;});
        }
        call(()->{result.getJSONArray("steps").put(new JSONObject().put("checkpoint",checkpoint).put("text",editable.toString()).put("selectionStart",c.view.getSelectionStart()).put("selectionEnd",c.view.getSelectionEnd()).put("composingStart",BaseInputConnection.getComposingSpanStart(editable)).put("composingEnd",BaseInputConnection.getComposingSpanEnd(editable)).put("sameView",edit(TITLE_HINT)==c.view).put("sameEditable",c.view.getText()==editable));return null;});
    }
    private void closeOnce(OwnedConnection connection) throws Exception {
        closeOnce(connection, () -> null);
    }

    private void closeOnce(OwnedConnection connection, Action<Void> beforeClose) throws Exception {
        if (connection.closeAttempted) {
            require(connection.closed, "Connection close was previously unresolved; preserve without retry");
            return;
        }
        call(() -> {
            beforeClose.run();
            connection.closeAttempted = true;
            connection.input.closeConnection();
            connection.closed = true;
            return null;
        });
    }

    private void frame() throws Exception {
        CountDownLatch frame = new CountDownLatch(1);
        call(() -> {
            Choreographer.getInstance().postFrameCallback(time -> frame.countDown());
            return null;
        });
        require(frame.await(budget(RPC_MS), TimeUnit.MILLISECONDS), "Native callback frame timed out");
    }

    private interface Action<T> { T run() throws Exception; }

    private <T> T call(Action<T> action) throws Exception {
        return call(action, deadline);
    }

    private <T> T call(Action<T> action, long until) throws Exception {
        long waitUntil = Math.min(until, SystemClock.elapsedRealtime() + budget(RPC_MS));
        require(Looper.myLooper() != Looper.getMainLooper(), "Test thread must never block the main Looper");
        require(!unknownMainCall, "Prior main-thread RPC is unknown; no further calls");
        CountDownLatch done = new CountDownLatch(1);
        AtomicInteger state = new AtomicInteger();
        AtomicReference<T> value = new AtomicReference<>();
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Runnable rpc = () -> {
            if (!state.compareAndSet(0, 1)) return;
            try { value.set(action.run()); }
            catch (Throwable error) { failure.set(error); }
            finally { state.set(2); done.countDown(); }
        };
        require(main.post(rpc), "Main Handler rejected RPC");
        if (!done.await(Math.max(0, waitUntil - SystemClock.elapsedRealtime()), TimeUnit.MILLISECONDS)) {
            if (state.compareAndSet(0, 3)) main.removeCallbacks(rpc);
            else unknownMainCall = true;
            throw new IllegalStateException("Main RPC deadline; running call custody=" + (unknownMainCall ? "UNKNOWN" : "cancelled-before-entry"));
        }
        if (failure.get() != null) throw new IllegalStateException("Main RPC failed", failure.get());
        return value.get();
    }

    private long budget(long maximum) {
        long remaining = deadline - SystemClock.elapsedRealtime();
        require(remaining > 0, "Probe deadline exceeded");
        return Math.min(remaining, maximum);
    }

    private void await(String description, long maximum, Action<Boolean> condition) throws Exception {
        long until = SystemClock.elapsedRealtime() + budget(maximum);
        while (SystemClock.elapsedRealtime() < until) {
            if (call(condition)) return;
            Thread.sleep(Math.min(40, budget(40)));
        }
        throw new IllegalStateException("Timed out: " + description);
    }

    private View decor() {
        Activity activity = resumed.get();
        require(activity != null && !activity.isFinishing() && !activity.isDestroyed(), "Exact Activity is not resumed");
        return activity.getWindow().getDecorView();
    }

    private Fields fields() {
        List<EditText> titles = new ArrayList<>();
        List<EditText> people = new ArrayList<>();
        List<Button> saves = new ArrayList<>();
        collect(decor(), titles, people, saves);
        if (titles.isEmpty() || people.isEmpty() || saves.isEmpty()) return null;
        require(titles.size() == 1 && people.size() == 1 && saves.size() == 1, "Ambiguous native form");
        return new Fields(titles.get(0), people.get(0), saves.get(0));
    }

    private Fields requireFields() {
        Fields value = fields();
        require(value != null, "Native form is unavailable");
        return value;
    }

    private EditText edit(String hint) {
        Fields fields = requireFields();
        return TITLE_HINT.equals(hint) ? fields.title : fields.person;
    }

    private static void collect(View view, List<EditText> titles, List<EditText> people, List<Button> saves) {
        if (view instanceof EditText) {
            EditText edit = (EditText) view;
            if (TITLE_HINT.contentEquals(edit.getHint() == null ? "" : edit.getHint())) titles.add(edit);
            if (PERSON_HINT.contentEquals(edit.getHint() == null ? "" : edit.getHint())) people.add(edit);
        }
        if (view instanceof Button) {
            Button button = (Button) view;
            String label = button.getText().toString();
            if ("Save".equals(label) || "Saved".equals(label) || "Saving…".equals(label)) saves.add(button);
        }
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) collect(group.getChildAt(i), titles, people, saves);
        }
    }

    private static boolean hasText(View view, String text) {
        if (view instanceof TextView && view.isShown() && text.contentEquals(((TextView) view).getText())) return true;
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) if (hasText(group.getChildAt(i), text)) return true;
        }
        return false;
    }

    private static void require(boolean condition, String message) { if (!condition) throw new IllegalStateException(message); }
    private static void put(JSONObject object, String key, Object value) {
        try { object.put(key, value); } catch (org.json.JSONException failure) { throw new IllegalStateException(failure); }
    }
    private static final class Fields {
        final EditText title, person;
        final Button save;
        Fields(EditText title, EditText person, Button save) { this.title = title; this.person = person; this.save = save; }
    }
    private static final class OwnedConnection {
        final InputConnection input;
        final EditText view;
        volatile boolean closeAttempted, closed;
        OwnedConnection(InputConnection input, EditText view) { this.input = input; this.view = view; }
    }
}
