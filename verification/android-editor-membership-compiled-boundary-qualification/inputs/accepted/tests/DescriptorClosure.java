import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import java.util.TreeSet;

/** Independent actual compiled shape check. Does not call an editor or constructor. */
public final class DescriptorClosure {
    private DescriptorClosure() {}
    private static final Set<String> EXPECTED = Set.of(
        "beginBatchEdit()Z", "clearMetaKeyStates(I)Z", "closeConnection()V",
        "commitCompletion(Landroid/view/inputmethod/CompletionInfo;)Z",
        "commitContent(Landroid/view/inputmethod/InputContentInfo;ILandroid/os/Bundle;)Z",
        "commitCorrection(Landroid/view/inputmethod/CorrectionInfo;)Z",
        "commitText(Ljava/lang/CharSequence;I)Z",
        "commitText(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z",
        "deleteSurroundingText(II)Z", "deleteSurroundingTextInCodePoints(II)Z",
        "endBatchEdit()Z", "finishComposingText()Z", "getCursorCapsMode(I)I",
        "getExtractedText(Landroid/view/inputmethod/ExtractedTextRequest;I)Landroid/view/inputmethod/ExtractedText;",
        "getHandler()Landroid/os/Handler;", "getSelectedText(I)Ljava/lang/CharSequence;",
        "getSurroundingText(III)Landroid/view/inputmethod/SurroundingText;",
        "getTextAfterCursor(II)Ljava/lang/CharSequence;", "getTextBeforeCursor(II)Ljava/lang/CharSequence;",
        "performContextMenuAction(I)Z", "performEditorAction(I)Z",
        "performHandwritingGesture(Landroid/view/inputmethod/HandwritingGesture;Ljava/util/concurrent/Executor;Ljava/util/function/IntConsumer;)V",
        "performPrivateCommand(Ljava/lang/String;Landroid/os/Bundle;)Z", "performSpellCheck()Z",
        "previewHandwritingGesture(Landroid/view/inputmethod/PreviewableHandwritingGesture;Landroid/os/CancellationSignal;)Z",
        "replaceText(IILjava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z",
        "reportFullscreenMode(Z)Z", "requestCursorUpdates(I)Z", "requestCursorUpdates(II)Z",
        "requestTextBoundsInfo(Landroid/graphics/RectF;Ljava/util/concurrent/Executor;Ljava/util/function/Consumer;)V",
        "sendKeyEvent(Landroid/view/KeyEvent;)Z", "setComposingRegion(II)Z",
        "setComposingRegion(IILandroid/view/inputmethod/TextAttribute;)Z",
        "setComposingText(Ljava/lang/CharSequence;I)Z",
        "setComposingText(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z",
        "setImeConsumesInput(Z)Z", "setSelection(II)Z",
        "takeSnapshot()Landroid/view/inputmethod/TextSnapshot;"
    );

    private static String descriptor(Class<?> type) {
        if (type.isArray()) return type.getName().replace('.', '/');
        if (!type.isPrimitive()) return "L" + type.getName().replace('.', '/') + ";";
        if (type == void.class) return "V";
        if (type == boolean.class) return "Z";
        if (type == byte.class) return "B";
        if (type == char.class) return "C";
        if (type == short.class) return "S";
        if (type == int.class) return "I";
        if (type == long.class) return "J";
        if (type == float.class) return "F";
        if (type == double.class) return "D";
        throw new AssertionError(type);
    }

    private static String signature(Method method) {
        StringBuilder out = new StringBuilder(method.getName()).append('(');
        for (Class<?> type : method.getParameterTypes()) out.append(descriptor(type));
        return out.append(')').append(descriptor(method.getReturnType())).toString();
    }

    private static Set<String> declaredShape(Class<?> type) {
        Set<String> shape = new TreeSet<>();
        for (Method method : type.getDeclaredMethods())
            if (!Modifier.isStatic(method.getModifiers())) shape.add(signature(method));
        return shape;
    }

    private static void same(Set<String> actual, Set<String> expected, String context) {
        Set<String> missing = new TreeSet<>(expected); missing.removeAll(actual);
        Set<String> extra = new TreeSet<>(actual); extra.removeAll(expected);
        if (!missing.isEmpty() || !extra.isEmpty())
            throw new AssertionError(context + " missing=" + missing + " extra=" + extra);
    }

    public static void main(String[] names) throws Exception {
        ClassLoader loader = DescriptorClosure.class.getClassLoader();
        Class<?> input = Class.forName("android.view.inputmethod.InputConnection", false, loader);
        same(declaredShape(input), EXPECTED, "official-or-host InputConnection");
        if (EXPECTED.size() != 38) throw new AssertionError("oracle size");
        for (String name : names) {
            Class<?> adapter = Class.forName(name, false, loader);
            if (!input.isAssignableFrom(adapter)) throw new AssertionError("not InputConnection " + name);
            Set<Class<?>> authored = new HashSet<>();
            for (Class<?> type = adapter; type != Object.class; type = type.getSuperclass()) {
                if (type == null || !type.getName().startsWith("dev.mixer.android."))
                    throw new AssertionError("platform/default superclass in adapter chain " + name);
                authored.add(type);
            }
            Set<String> actual = new TreeSet<>();
            for (Method method : adapter.getMethods()) {
                String key = signature(method);
                if (method.getName().equals("setTarget")) throw new AssertionError("setTarget exposed");
                if (EXPECTED.contains(key)) {
                    if (!authored.contains(method.getDeclaringClass()) || method.isDefault()
                            || Modifier.isAbstract(method.getModifiers()))
                        throw new AssertionError("inherited platform/default/abstract dispatch " + key);
                    actual.add(key);
                }
            }
            same(actual, EXPECTED, "adapter " + name);
        }
        System.out.println("descriptor closure: 38; inspected adapters=" + Arrays.toString(names));
    }
}
