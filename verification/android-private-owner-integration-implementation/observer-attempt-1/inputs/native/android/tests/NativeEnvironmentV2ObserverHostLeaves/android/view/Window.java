package android.view;
public final class Window { private final View decor; public Window(android.content.Context context) { decor = new View(context); } public View getDecorView() { return decor; } }
