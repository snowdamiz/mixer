package android.content.res;
import android.os.LocaleList;
public final class Configuration {
    public static final int FONT_WEIGHT_ADJUSTMENT_UNDEFINED = Integer.MAX_VALUE;
    public static final int UI_MODE_NIGHT_MASK = 0x30;
    public static final int UI_MODE_NIGHT_YES = 0x20;
    public int fontWeightAdjustment;
    public int uiMode;
    public LocaleList getLocales() { return new LocaleList(); }
}
