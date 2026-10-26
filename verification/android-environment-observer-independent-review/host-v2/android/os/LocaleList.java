package android.os;
import java.util.Locale;
public final class LocaleList {
    public Locale get(int index) {
        if (index != 0) throw new IndexOutOfBoundsException(index);
        return Locale.US;
    }
}
