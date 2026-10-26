package dev.mixer.android;

/** TEST ONLY: scripted concrete renderer leaf. No native presentation is implemented or accepted. */
final class NativeRenderer {
    interface Events { void send(byte[] envelope); }
    static final class Candidate { boolean used; }
    static final class AttachmentJournal {}
    private final Events events;
    private Candidate pending;
    private boolean committed;
    NativeRenderer(android.content.Context context, Events events) {
        this.events = events;
        NativeCoordinatorV2HostTests.Rig.step("renderer.create");
        NativeCoordinatorV2HostTests.Rig.renderer = this;
    }
    InstalledAppearanceV2 captureInstalledV2() {
        NativeCoordinatorV2HostTests.Rig.step("capture.installed");
        var result = new InstalledAppearanceV2();
        NativeCoordinatorV2HostTests.Rig.installed = result;
        return result;
    }
    NativeEnvironmentV2 captureEnvironmentV2(android.app.Activity activity,
                                             android.widget.FrameLayout root) {
        NativeCoordinatorV2HostTests.Rig.step("capture.environment");
        var result = new NativeEnvironmentV2();
        NativeCoordinatorV2HostTests.Rig.environment = result;
        return result;
    }
    Candidate prepareV2(byte[] bytes, InstalledAppearanceV2 installed, NativeEnvironmentV2 environment) {
        NativeCoordinatorV2HostTests.Rig.check(installed == NativeCoordinatorV2HostTests.Rig.installed,
            "actual installed capture forwarded unchanged");
        NativeCoordinatorV2HostTests.Rig.check(environment == NativeCoordinatorV2HostTests.Rig.environment,
            "actual environment capture forwarded unchanged");
        NativeCoordinatorV2HostTests.Rig.rendererPackets.add(bytes);
        NativeCoordinatorV2HostTests.Rig.step("renderer.prepare");
        pending = new Candidate();
        return pending;
    }
    AttachmentJournal attachV2(Candidate candidate, android.widget.FrameLayout root) {
        NativeCoordinatorV2HostTests.Rig.check(pending == candidate, "owned renderer candidate");
        // This fault leaves the candidate unconsumed, like actual pre-try validation/preflight.
        NativeCoordinatorV2HostTests.Rig.step("renderer.attach.preflight");
        NativeCoordinatorV2HostTests.Rig.open = false;
        try {
            NativeCoordinatorV2HostTests.Rig.step("renderer.attach.mutation");
        } catch (RuntimeException | Error failure) {
            candidate.used = true;
            pending = null;
            NativeCoordinatorV2HostTests.Rig.attachConsumed = true;
            throw failure;
        }
        NativeCoordinatorV2HostTests.Rig.step("renderer.attach.return");
        return new AttachmentJournal();
    }
    void validateAttachedV2(Candidate candidate, AttachmentJournal journal) {
        NativeCoordinatorV2HostTests.Rig.step("renderer.validate");
    }
    void finishV2(Candidate candidate, AttachmentJournal journal) {
        NativeCoordinatorV2HostTests.Rig.step("renderer.finish.before");
        committed = true;
        candidate.used = true;
        pending = null;
        NativeCoordinatorV2HostTests.Rig.open = true;
        NativeCoordinatorV2HostTests.Rig.step("renderer.finish.after");
    }
    void rollbackV2(Candidate candidate, AttachmentJournal journal) {
        NativeCoordinatorV2HostTests.Rig.check(!candidate.used && pending == candidate,
            "rollback requires a known returned unconsumed journal");
        NativeCoordinatorV2HostTests.Rig.step("renderer.rollback.before");
        candidate.used = true;
        pending = null;
        NativeCoordinatorV2HostTests.Rig.open = committed;
        NativeCoordinatorV2HostTests.Rig.step("renderer.rollback.after");
    }
    void discardV2(Candidate candidate) {
        NativeCoordinatorV2HostTests.Rig.check(!candidate.used && pending == candidate,
            "discard requires a known unattached candidate");
        NativeCoordinatorV2HostTests.Rig.step("renderer.discard.before");
        candidate.used = true;
        pending = null;
        NativeCoordinatorV2HostTests.Rig.step("renderer.discard.after");
    }
    void disposeV2() {
        if (NativeCoordinatorV2HostTests.Rig.coordinator != null) {
            NativeCoordinatorV2HostTests.Rig.check(NativeCoordinatorV2HostTests.Rig.coordinator.isRetired(),
                "local closed state precedes native disposal");
            NativeCoordinatorV2HostTests.Rig.check(
                !NativeCoordinatorV2HostTests.Rig.coordinator.hasCommittedPresentation(),
                "retirement clears authoritative packet before native disposal");
        }
        NativeCoordinatorV2HostTests.Rig.step("renderer.dispose.before");
        NativeCoordinatorV2HostTests.Rig.open = false;
        pending = null;
        NativeCoordinatorV2HostTests.Rig.step("renderer.dispose.after");
    }
    void fire(byte[] envelope) {
        NativeCoordinatorV2HostTests.Rig.transientText = "unacknowledged native input";
        events.send(envelope);
    }
}
