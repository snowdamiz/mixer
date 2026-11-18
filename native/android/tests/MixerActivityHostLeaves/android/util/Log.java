package android.util;

public class Log {
    public static int e(String tag, String message, Throwable error) {
        throw new AssertionError(message, error);
    }
}
