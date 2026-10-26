package dev.mixer.android;

import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.HandwritingGesture;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.PreviewableHandwritingGesture;
import android.view.inputmethod.SelectGesture;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;

/** Supported official SelectGesture token; no platform constructor or behavior invoked. */
public final class MetadataReentryControls {
    private MetadataReentryControls() {}
    private static Object get(Object object,String name) throws ReflectiveOperationException {
        Field f=object.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(object);
    }
    private static final class Poison extends EditorInfo {
        final boolean payload;
        Poison(boolean payload){this.payload=payload;}
        @Override public void setSupportedHandwritingGesturePreviews(Set<Class<? extends PreviewableHandwritingGesture>> values) {
            super.setSupportedHandwritingGesturePreviews(values);
            if(payload) {
                inputType=99;hintText="repopulated-output";initialSelStart=initialSelEnd=0;
                super.setInitialSurroundingText("private-surrounding-output");
            } else {
                // SelectGesture is explicitly supported by BOTH pinned official setters.
                super.setSupportedHandwritingGestures(List.of(SelectGesture.class));
                super.setSupportedHandwritingGesturePreviews(Set.of(SelectGesture.class));
            }
        }
    }
    public static void main(String[] args) throws Exception {
        Field descriptor=IndependentEditorReviewTests.class.getDeclaredField("descriptor");
        descriptor.setAccessible(true);descriptor.set(null,Files.readAllBytes(Path.of(args[1])));
        Constructor<?> constructor=Class.forName("dev.mixer.android.IndependentEditorReviewTests$Fixture").getDeclaredConstructor();
        constructor.setAccessible(true);
        try(AutoCloseable fixture=(AutoCloseable)constructor.newInstance()) {
            NativeAppearanceViewsV2.NativeField edit=(NativeAppearanceViewsV2.NativeField)get(fixture,"edit");
            NativeOwnerV2 owner=(NativeOwnerV2)get(fixture,"owner");
            NativeOwnerV2.Fence fence=(NativeOwnerV2.Fence)get(owner,"fence");
            boolean payload=args[0].equals("payload");Poison info=new Poison(payload);
            android.widget.EditText.creatorNull=payload;
            InputConnection result=edit.onCreateInputConnection(info);
            if(payload) {
                System.out.println("OBSERVED adapter="+(result!=null)+" inputType="+info.inputType+" hint="+info.hintText+" privateSurrounding="+info.hostSurrounding()+" terminal="+fence.terminal);
                if(result!=null||info.inputType!=0||info.hintText!=null||info.hostSurrounding()!=null)
                    throw new AssertionError("failed creator scrub returns with repopulated public/private payload and no uncertainty report");
            } else {
                System.out.println("OBSERVED adapter="+(result!=null)+" gestures="+info.gestures+" previews="+info.previews+" terminal="+fence.terminal);
                if(result!=null&&(!info.gestures.isEmpty()||!info.previews.isEmpty()))
                    throw new AssertionError("usable adapter advertises refused supported SelectGesture after public setter reentry");
            }
        }
    }
}
