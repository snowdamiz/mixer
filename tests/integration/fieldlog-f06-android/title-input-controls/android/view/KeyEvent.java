package android.view;

// Host-only platform leaf. The API 36 build uses Android's own KeyEvent.
public final class KeyEvent {
    public static final int ACTION_DOWN = 0;
    private final int codePoint;
    public KeyEvent(int codePoint) { this.codePoint = codePoint; }
    public KeyEvent(KeyEvent other) { this(other.codePoint); }
    public int getAction() { return ACTION_DOWN; }
    public boolean isAltPressed() { return false; }
    public boolean isCtrlPressed() { return false; }
    public boolean isMetaPressed() { return false; }
    public int getUnicodeChar() { return codePoint; }
    public int getKeyCode() { return codePoint; }
}
