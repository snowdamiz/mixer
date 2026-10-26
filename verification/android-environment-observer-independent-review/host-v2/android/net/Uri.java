package android.net;
public final class Uri {
    private final String text;
    public Uri(String value) { text = value; }
    @Override public String toString() { return text; }
}
