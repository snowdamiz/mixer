package dev.mixer.fixture.f06ime;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.inputmethodservice.InputMethodService;
import android.text.InputType;
import android.util.Log;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.Button;

public final class TitleCommitIme extends InputMethodService {
    private static final String TARGET = "dev.mixer.fieldlog.f06signed";
    private static final String TAG = "F06CommitIme";
    private boolean issued;

    private static final String COMMIT = "dev.mixer.fixture.f06ime.COMMIT_TITLE";
    private final BroadcastReceiver driver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            if (COMMIT.equals(intent.getAction())) commitTitle();
        }
    };

    @Override public void onCreate() {
        super.onCreate();
        registerReceiver(driver, new IntentFilter(COMMIT), "android.permission.DUMP", null, Context.RECEIVER_EXPORTED);
    }

    @Override public void onDestroy() {
        unregisterReceiver(driver);
        super.onDestroy();
    }

    @Override public View onCreateInputView() {
        Button commit = new Button(this);
        commit.setText("Commit synthetic F06 title");
        commit.setAllCaps(false);
        commit.setOnClickListener(view -> commitTitle());
        return commit;
    }

    @Override public boolean onEvaluateInputViewShown() {
        EditorInfo editor = getCurrentInputEditorInfo();
        return editor != null && TARGET.equals(editor.packageName);
    }

    @Override public void onStartInput(EditorInfo editor, boolean restarting) {
        super.onStartInput(editor, restarting);
        if (editor != null && TARGET.equals(editor.packageName)) {
            Log.i(TAG, "Target editor bound");
            requestShowSelf(0);
        }
    }

    private void commitTitle() {
        EditorInfo editor = getCurrentInputEditorInfo();
        InputConnection connection = getCurrentInputConnection();
        if (issued || editor == null || connection == null || !TARGET.equals(editor.packageName)) return;
        if ((editor.inputType & InputType.TYPE_TEXT_FLAG_MULTI_LINE) == 0
                || (editor.imeOptions & EditorInfo.IME_MASK_ACTION) != EditorInfo.IME_ACTION_NONE
                || (editor.imeOptions & EditorInfo.IME_FLAG_NO_ENTER_ACTION) == 0) {
            Log.e(TAG, "Expected the F06 vertical title IME flags");
            return;
        }
        issued = true;
        boolean first = connection.commitText("Inspect ", 1);
        boolean second = connection.commitText("pump P-17", 1);
        Log.i(TAG, "vertical=true action=none noEnter=true commitResults=" + first + "," + second);
    }
}
