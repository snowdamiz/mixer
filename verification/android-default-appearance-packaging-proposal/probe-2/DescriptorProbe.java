package dev.mixer.android;
import java.nio.file.Files;
import java.nio.file.Path;
final class DescriptorProbe {
    public static void main(String[] args) throws Exception {
        byte[] bytes = Files.readAllBytes(Path.of(args[0]));
        AppearanceDescriptorV2 value = AppearanceDescriptorV2.decode(bytes);
        if (value.mode != AppearanceDescriptorV2.Mode.shared || value.iOS != value.android ||
            value.platformSpecificReason != null || !value.resources.isEmpty() ||
            !(value.iOS.typography().font() instanceof AppearanceDescriptorV2.SystemSans))
            throw new AssertionError("unexpected default");
        byte[] noncanonical = java.util.Arrays.copyOf(bytes, bytes.length + 1);
        noncanonical[bytes.length] = ' ';
        try { AppearanceDescriptorV2.decode(noncanonical); throw new AssertionError("accepted whitespace"); }
        catch (AppearanceDescriptorV2.Failure rejected) {
            if (rejected.code != AppearanceDescriptorV2.Error.noncanonical) throw rejected;
        }
        System.out.println("hostJava=shared identicalTheme=true emptyCatalog=true systemSans=true rejectsTrailingSpace=true");
    }
}
