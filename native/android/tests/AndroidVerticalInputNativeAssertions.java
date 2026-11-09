package dev.mixer.android;

import android.os.Build;
import android.text.InputType;
import android.view.Gravity;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.EditText;

/** Prospective API37 instrumentation assertions. Root supplies an attached,
 * focused field from the new public surface after JNI/executor review. */
public final class AndroidVerticalInputNativeAssertions {
    private AndroidVerticalInputNativeAssertions() {}
    private static void check(boolean value,String why){if(!value)throw new AssertionError(why);}
    public static InputConnection exercise(EditText field) {
        check(Build.VERSION.SDK_INT==37,"API37 witness required");
        check(field.isAttachedToWindow()&&field.hasFocus(),"live owner and focused native field");
        check((field.getInputType()&InputType.TYPE_TEXT_FLAG_MULTI_LINE)!=0,"multiline input type");
        check((field.getImeOptions()&EditorInfo.IME_MASK_ACTION)==EditorInfo.IME_ACTION_NONE,"Enter inserts newline");
        check((field.getImeOptions()&EditorInfo.IME_FLAG_NO_ENTER_ACTION)!=0,"no implicit submit");
        check(field.getMaxLines()==Integer.MAX_VALUE&&field.getEllipsize()==null,"no line clamp or ellipsis");
        check((field.getGravity()&Gravity.VERTICAL_GRAVITY_MASK)==Gravity.TOP,"top aligned multiline");
        check(field.getTransformationMethod()==null,"no single-line transformation");
        InputConnection connection=field.onCreateInputConnection(new EditorInfo());
        check(connection!=null,"real guarded native connection");
        String value="Café\n漢字 e\u0301 🏗️\nمسؤول";
        check(connection.setSelection(0,field.length()),"select existing content");
        check(connection.commitText(value,1),"Unicode multiline commit");
        check(field.getText().toString().equals(value),"exact multiline Editable");
        check(connection.setSelection(0,4),"selection range");
        check("Café".contentEquals(connection.getSelectedText(0)),"selected text");
        check(connection.setComposingRegion(0,4),"composition region");
        check(BaseInputConnection.getComposingSpanStart(field.getText())==0&&BaseInputConnection.getComposingSpanEnd(field.getText())==4,"native composition offsets");
        check(connection.setComposingText("Étage\n二",1),"multiline composition");
        check(field.getText().toString().equals("Étage\n二"+value.substring(4)),"composition retains Unicode suffix");
        check(connection.finishComposingText(),"finish composition");
        return connection;
    }
    public static void measured(EditText field) {
        check(field.getLayout()!=null&&field.getLayout().getLineCount()>=3,"native multiline layout");
        check(field.getHeight()>=field.getLayout().getHeight()+field.getCompoundPaddingTop()+field.getCompoundPaddingBottom(),"full shaped height");
    }
    public static void revoked(InputConnection old,EditText field) {
        String before=field.getText().toString();
        check(!old.commitText("late",1),"retired connection refuses mutation");
        check(field.getText().toString().equals(before),"retirement preserves content");
    }
}
