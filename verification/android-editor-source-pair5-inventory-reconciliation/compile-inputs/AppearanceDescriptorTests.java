package dev.mixer.android;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.util.List;
import java.util.Map;

/** Host data-decoder checks; no Android resource or rendering authority. */
public final class AppearanceDescriptorTests {
    private static int checks;
    private static void require(boolean value, String name) { checks++; if (!value) throw new AssertionError(name); }
    private static void immutable(Object value) {
        if (value instanceof Map<?, ?>) {
            Map<?, ?> map = (Map<?, ?>)value;
            try { map.clear(); throw new AssertionError("mutable map"); } catch (UnsupportedOperationException expected) { checks++; }
            for (Object child : map.values()) immutable(child);
        } else if (value instanceof List<?>) {
            List<?> list = (List<?>)value;
            try { list.clear(); throw new AssertionError("mutable list"); } catch (UnsupportedOperationException expected) { checks++; }
            for (Object child : list) immutable(child);
        }
    }
    public static void main(String[] args) throws Exception {
        int accepted = 0, rejected = 0;
        for (String line : Files.readAllLines(Path.of(args[0]), StandardCharsets.US_ASCII)) {
            String[] fields = line.split("\t", -1);
            byte[] bytes = Base64.getDecoder().decode(fields[2]);
            boolean success = false; AppearanceDescriptorV1 descriptor = null;
            try { descriptor = AppearanceDescriptorV1.decode(bytes); success = true; } catch (IllegalArgumentException expected) { /* closed rejection */ }
            require(success == fields[1].equals("1"), fields[0]);
            if (success) {
                accepted++;
                immutable(descriptor.iOS); immutable(descriptor.android); immutable(descriptor.resources);
                String id = descriptor.id; java.util.Arrays.fill(bytes, (byte)'X');
                require(descriptor.id.equals(id), "source array retained");
                require(descriptor.platformSpecificReason != null || descriptor.iOS == descriptor.android, "shared single theme");
            } else rejected++;
        }
        try { AppearanceDescriptorV1.decode(null); throw new AssertionError("null accepted"); } catch (IllegalArgumentException expected) { checks++; }
        System.out.println("PASS descriptor cases=" + (accepted + rejected) + " accepted=" + accepted + " rejected=" + rejected + " assertions=" + checks);
    }
}
