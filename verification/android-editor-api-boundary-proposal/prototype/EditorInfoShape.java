package dev.mixer.editor.proposal;

import android.view.inputmethod.EditorInfo;
import java.util.Collections;

/** UNSELECTED metadata-signature experiment; never execute or package as Mixer. */
public final class EditorInfoShape {
    private EditorInfoShape() {}
    public static void configureShape(int sdk, EditorInfo info) {
        if (sdk >= 34) Api34.clearRefusedGestureAdvertisement(info);
        // These false values illustrate exact public method linkage only. Their
        // product policy remains separately unselected in the written contract.
        if (sdk >= 35) Api35.stylusPolicyShape(info);
        if (sdk >= 36) Api36.writingToolsPolicyShape(info);
    }
    static final class Api34 {
        private Api34() {}
        static void clearRefusedGestureAdvertisement(EditorInfo info) {
            info.setSupportedHandwritingGestures(Collections.emptyList());
            info.setSupportedHandwritingGesturePreviews(Collections.emptySet());
        }
    }
    static final class Api35 {
        private Api35() {}
        static void stylusPolicyShape(EditorInfo info) { info.setStylusHandwritingEnabled(false); }
    }
    static final class Api36 {
        private Api36() {}
        static void writingToolsPolicyShape(EditorInfo info) { info.setWritingToolsEnabled(false); }
    }
}
