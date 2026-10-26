package dev.mixer.android;

import android.content.Context;
import android.content.res.AssetManager;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/** Private installed capture for the repository native prototype, not a support proof. */
final class InstalledAppearanceV2 {
    static final String DESCRIPTOR = "MixerAppearanceV2/descriptor.json";
    private final Object owner;
    private final byte[] canonical;
    final AppearanceDescriptorV2 configuration;
    final String sha256;

    private InstalledAppearanceV2(Object owner, byte[] bytes, AppearanceDescriptorV2 descriptor) {
        this.owner = owner;
        canonical = bytes;
        configuration = descriptor;
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
            StringBuilder hex = new StringBuilder(64);
            for (byte value : digest) hex.append(String.format(java.util.Locale.ROOT, "%02x", value & 255));
            sha256 = hex.toString();
        } catch (NoSuchAlgorithmException impossible) { throw new AssertionError(impossible); }
    }

    static InstalledAppearanceV2 capture(Context context, Object owner) {
        NativeEnvironmentV2.requireMain();
        byte[] bytes;
        try (InputStream stream = context.getAssets().open(DESCRIPTOR, AssetManager.ACCESS_STREAMING)) {
            // The limit is enforced while reading, including streams whose available() lies.
            ByteArrayOutputStream output = new ByteArrayOutputStream(4096);
            byte[] chunk = new byte[4096];
            int count, total = 0;
            while ((count = stream.read(chunk, 0, Math.min(chunk.length, 65537 - total))) != -1) {
                total += count;
                if (total > 65536) throw reject(AppearanceDescriptorV2.Error.byteLimit);
                output.write(chunk, 0, count);
            }
            bytes = output.toByteArray();
        } catch (IOException failure) {
            AppearanceDescriptorV2.Failure rejected = reject(AppearanceDescriptorV2.Error.resourceCatalog);
            rejected.initCause(failure); throw rejected;
        }
        AppearanceDescriptorV2 descriptor = AppearanceDescriptorV2.decode(bytes);
        // Decode validates both complete platform themes and every catalog entry first.
        // This executable slice supports no resource kind, even an unused declaration.
        if (!descriptor.resources.isEmpty() ||
            !(descriptor.iOS.typography().font() instanceof AppearanceDescriptorV2.SystemSans) ||
            !(descriptor.android.typography().font() instanceof AppearanceDescriptorV2.SystemSans))
            throw reject(AppearanceDescriptorV2.Error.unsupportedNativeOperation);
        return new InstalledAppearanceV2(owner, bytes, descriptor);
    }

    boolean belongsTo(Object value) { return owner == value; }
    byte[] descriptorCopy() { return canonical.clone(); }
    private static AppearanceDescriptorV2.Failure reject(AppearanceDescriptorV2.Error error) {
        return new AppearanceDescriptorV2.Failure(error);
    }
}
