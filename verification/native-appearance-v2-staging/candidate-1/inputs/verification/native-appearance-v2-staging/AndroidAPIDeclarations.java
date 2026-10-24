package dev.mixer.android;

import android.content.Context;
import android.graphics.Typeface;
import android.graphics.drawable.ColorDrawable;
import android.graphics.fonts.Font;
import android.graphics.fonts.FontFamily;
import android.util.TypedValue;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.Switch;
import java.io.IOException;
import java.nio.ByteBuffer;

/** Compiler-only API29-prototype declaration probe. No native method executes. */
final class AndroidAPIDeclarations {
    private AndroidAPIDeclarations() {}

    static void toolkit(Context context, ByteBuffer ownedBytes) throws IOException {
        EditText field = new EditText(context);
        field.setTextSize(TypedValue.COMPLEX_UNIT_PX, 17);
        field.setIncludeFontPadding(false);
        field.setHighlightColor(0x3D0088FF);
        field.setTextCursorDrawable(new ColorDrawable(0xFF0088FF));
        Font font = new Font.Builder(ownedBytes.asReadOnlyBuffer()).build();
        int observedWeight = font.getStyle().getWeight();
        int observedSlant = font.getStyle().getSlant();
        Typeface typeface = new Typeface.CustomFallbackBuilder(new FontFamily.Builder(font).build()).build();
        field.setTypeface(typeface);
        Switch toggle = new Switch(context);
        toggle.setTrackDrawable(new ColorDrawable(0));
        toggle.setThumbDrawable(new ColorDrawable(0));
        FrameLayout root = new FrameLayout(context);
        root.suppressLayout(true);
        root.suppressLayout(false);
        if (observedWeight < 0 || observedSlant < 0) throw new IllegalStateException("unreachable API probe");
    }

    static android.graphics.Path realClosedPathConsumer(byte[] packet, byte[] descriptor,
            AppearanceResolverV2.Environment environment) {
        AppearanceResolverV2.Plan plan = AppearanceResolverV2.prepare(packet, descriptor, environment,
                AppearanceResolverV2.Platform.android);
        return AppearanceNativePathsV2.make(AppearanceGeometryV2.track(), plan.environment.density1024());
    }
}
