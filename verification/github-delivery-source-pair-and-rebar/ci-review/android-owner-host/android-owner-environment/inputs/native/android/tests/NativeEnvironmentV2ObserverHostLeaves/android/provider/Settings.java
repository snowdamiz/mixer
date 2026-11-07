package android.provider;
public final class Settings {
    public static final class SettingNotFoundException extends Exception {
        private static final long serialVersionUID=1L;
        public SettingNotFoundException(String name) { super(name); }
    }
    public static final class Global {
        public static final String ANIMATOR_DURATION_SCALE="animator";
        public static android.net.Uri getUriFor(String name) { return new android.net.Uri(); }
        public static float getFloat(android.content.ContentResolver resolver,String name) throws SettingNotFoundException {
            dev.mixer.android.ObserverHostProbe.read("animator",28);
            if(dev.mixer.android.ObserverHostProbe.animatorMissing) throw new SettingNotFoundException(name);
            return dev.mixer.android.ObserverHostProbe.animator;
        }
    }
}
