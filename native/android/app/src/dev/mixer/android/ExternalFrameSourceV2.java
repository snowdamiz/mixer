package dev.mixer.android;
import java.util.Arrays;
import java.util.Objects;

/** Immutable public-host delivery. No engine operations and no app effects during installation. */
final class ExternalFrameSourceV2 {
    static final class Frame {
        final byte[] packet, descriptor;
        Frame(byte[] packet, byte[] descriptor) {
            this.packet=Objects.requireNonNull(packet).clone();
            this.descriptor=Objects.requireNonNull(descriptor).clone();
        }
    }
    private final NativeRenderer.Events events;
    private Frame current;
    private boolean inputEnabled;
    void gateInput() { inputEnabled=false; }
    void openInput() { inputEnabled=true; }
    boolean inputEnabled() { return inputEnabled; }
    ExternalFrameSourceV2(NativeRenderer.Events events) { this.events=Objects.requireNonNull(events); }
    void offer(byte[] packet, byte[] descriptor) {
        NativeEnvironmentV2.requireMain();
        if(current!=null&&!Arrays.equals(current.descriptor,descriptor))throw new IllegalStateException("external appearance changed");
        current=new Frame(packet,descriptor);
    }
    Frame current() {
        NativeEnvironmentV2.requireMain();
        if(current==null)throw new IllegalStateException("external frame unavailable");
        return current;
    }
    void input(byte[] envelope) { events.send(envelope.clone()); }
}
