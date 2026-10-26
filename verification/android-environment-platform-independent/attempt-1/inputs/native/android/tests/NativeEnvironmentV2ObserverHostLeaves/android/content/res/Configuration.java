package android.content.res;
public final class Configuration {
    public static final int FONT_WEIGHT_ADJUSTMENT_UNDEFINED=Integer.MAX_VALUE, UI_MODE_NIGHT_MASK=48, UI_MODE_NIGHT_YES=32, UI_MODE_NIGHT_NO=16;
    public int fontWeightAdjustment, uiMode=UI_MODE_NIGHT_NO;
    public android.os.LocaleList locales=new android.os.LocaleList();
    public android.os.LocaleList getLocales() { dev.mixer.android.ObserverHostProbe.read("locale",28); return locales; }
}
