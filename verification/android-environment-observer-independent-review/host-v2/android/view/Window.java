package android.view;
import android.content.Context;
import dev.mixer.android.IndependentFaults;
public final class Window {
    public final View decor;
    public Window(Context context) { decor = new View(context); }
    public View getDecorView() { IndependentFaults.read(); return decor; }
}
