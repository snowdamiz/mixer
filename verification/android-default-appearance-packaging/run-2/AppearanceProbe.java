package dev.mixer.android;
import java.nio.file.Files;
import java.nio.file.Path;
public final class AppearanceProbe {
  public static void main(String[] args) throws Exception {
    byte[] bytes = Files.readAllBytes(Path.of(args[0]));
    AppearanceDescriptorV2 value = AppearanceDescriptorV2.decode(bytes);
    if (value.mode != AppearanceDescriptorV2.Mode.shared || !value.resources.isEmpty()
        || !(value.android.typography().font() instanceof AppearanceDescriptorV2.SystemSans)) throw new AssertionError("shape");
    System.out.println("production Java codec accepted shared empty-catalog systemSans; bytes=" + bytes.length + "; id=" + value.id);
  }
}
