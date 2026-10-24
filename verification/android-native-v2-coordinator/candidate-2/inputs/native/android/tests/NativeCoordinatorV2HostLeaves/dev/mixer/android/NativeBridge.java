package dev.mixer.android;

/** TEST ONLY: scripted JNI leaf; never loaded by the actual-SDK/native compile. */
final class NativeBridge {
    static final class Candidate {
        private final long token;
        private final byte[] bytes;
        Candidate(long token, byte[] bytes) { this.token = token; this.bytes = bytes.clone(); }
        long token() {
            NativeCoordinatorV2HostTests.Rig.step("engine.token");
            NativeCoordinatorV2HostTests.Rig.tokenRead = true;
            return token;
        }
        byte[] packet() {
            NativeCoordinatorV2HostTests.Rig.check(NativeCoordinatorV2HostTests.Rig.tokenRead,
                "opaque token retained before defensive-copy boundary");
            NativeCoordinatorV2HostTests.Rig.step("engine.packet.copy");
            byte[] result = bytes.clone();
            NativeCoordinatorV2HostTests.Rig.packetCopy = result;
            return result;
        }
    }
    static long create() {
        NativeCoordinatorV2HostTests.Rig.step("engine.create");
        return NativeCoordinatorV2HostTests.Rig.createHandle;
    }
    static Candidate prepareV2(long handle, int operation, byte[] input) {
        NativeCoordinatorV2HostTests.Rig.check(handle != 0, "nonzero owned handle");
        NativeCoordinatorV2HostTests.Rig.operations.add(operation);
        NativeCoordinatorV2HostTests.Rig.lastInput = input;
        NativeCoordinatorV2HostTests.Rig.step("engine.prepare.before");
        NativeCoordinatorV2HostTests.Rig.pending = true;
        NativeCoordinatorV2HostTests.Rig.step("engine.prepare.delivery");
        if (NativeCoordinatorV2HostTests.Rig.nullCandidate) return null;
        return new Candidate(NativeCoordinatorV2HostTests.Rig.token,
            NativeCoordinatorV2HostTests.Rig.nextPacket);
    }
    static int commitV2(long handle, long token) {
        NativeCoordinatorV2HostTests.Rig.check(token == NativeCoordinatorV2HostTests.Rig.token,
            "opaque token, including sign bit, preserved for commit");
        NativeCoordinatorV2HostTests.Rig.step("engine.commit.before");
        if (NativeCoordinatorV2HostTests.Rig.commitStatus == 0
            || NativeCoordinatorV2HostTests.Rig.unknownStatusHasEffect) {
            NativeCoordinatorV2HostTests.Rig.engineEffects++;
            NativeCoordinatorV2HostTests.Rig.pending = false;
        }
        NativeCoordinatorV2HostTests.Rig.step("engine.commit.after");
        return NativeCoordinatorV2HostTests.Rig.commitStatus;
    }
    static int abortV2(long handle, long token) {
        NativeCoordinatorV2HostTests.Rig.check(token == NativeCoordinatorV2HostTests.Rig.token,
            "retained opaque token used for abort");
        NativeCoordinatorV2HostTests.Rig.step("engine.abort");
        if (NativeCoordinatorV2HostTests.Rig.abortStatus == 0)
            NativeCoordinatorV2HostTests.Rig.pending = false;
        return NativeCoordinatorV2HostTests.Rig.abortStatus;
    }
    static void destroy(long handle) {
        NativeCoordinatorV2HostTests.Rig.step("engine.destroy.before");
        NativeCoordinatorV2HostTests.Rig.pending = false;
        NativeCoordinatorV2HostTests.Rig.destroyed = true;
        NativeCoordinatorV2HostTests.Rig.step("engine.destroy.after");
    }
    private NativeBridge() {}
}
