import Foundation
import MixerApple
import MixerCapabilityActivation
import MixerUI
import MixerUpdates
import SwiftUI

@main
struct S4NativeApp: App {
    @StateObject private var run = S4Run()

    var body: some Scene {
        WindowGroup {
            VStack {
                Text(run.status).accessibilityIdentifier("s4-status")
                    .accessibilityValue(Text(run.boundaryEvidence))
                Text(run.detail).accessibilityIdentifier("s4-detail")
                Text(run.saveObservation).accessibilityIdentifier("s4-save")
                if let owner = run.owner, run.showsGuest {
                    // A replacement owner always mounts a new native screen.
                    MixerGuestScreen(presentation: owner.presentation).id(ObjectIdentifier(owner))
                    if run.showsDuplicate {
                        // A second real wrapper for the same presentation. Production
                        // refuses its attachment claim and invalidates the exact probe.
                        MixerGuestScreen(presentation: owner.presentation).frame(height: 44)
                    }
                } else if let bundled = run.bundled {
                    MixerNativeView(host: bundled) { action in
                        run.observeBundledAction(action)
                    }
                }
                if run.mayConfirmRefusedTap {
                    Button("Check refused Save tap") { run.confirmRefusedTap() }
                }
                if run.mayAttachDuplicate {
                    Button("Attach duplicate guest screen") { run.attachDuplicate() }
                }
                if run.mayReleaseReceipt {
                    Button("Release display acknowledgment") { run.releaseReceipt() }
                }
                if run.mayReplaceHealthyRenderer {
                    Button("Replace healthy S4 owner") { Task { await run.replaceHealthyRenderer() } }
                }
                Button("Close S4 owner") { Task { await run.close() } }
                    .disabled(!run.mayClose)
            }
            .padding()
            .preferredColorScheme(run.themeTrial ? .light : nil)
            .task { await run.start() }
        }
    }
}

@MainActor
private final class S4Run: ObservableObject {
    enum Mode: String {
        case cold, baseline, invalidFirst, invalidRetained, reviewed, rollback, offline
        case tapBeforeReceipt, tapAfterReceipt
        case postIntentFailure, postIntentFailureExit, postIntentOffline
        case healthyRendererReplacement

        var isPostIntentFailure: Bool {
            self == .postIntentFailure || self == .postIntentFailureExit
        }
    }
    @Published private(set) var owner: CapabilityGuestUIRuntime?
    @Published private(set) var bundled: MixerUIHost?
    @Published private(set) var status = "starting"
    @Published private(set) var detail = "pending"
    @Published private(set) var boundaryEvidence = "pending"
    @Published private(set) var saveObservation = "no guest save"
    @Published private(set) var showsGuest = false
    @Published private(set) var mayClose = false
    @Published private(set) var mayReleaseReceipt = false
    @Published private(set) var mayConfirmRefusedTap = false
    @Published private(set) var mayAttachDuplicate = false
    @Published private(set) var showsDuplicate = false
    @Published private(set) var mayReplaceHealthyRenderer = false
    private var duplicateRequested = false
    private var capturedRetiredCallback: (@MainActor () -> Void)?
    private var confirmedRefusedTap = false
    private var receiptReleased = false
    private var stagedPayloadSHA256: String?

    let mode: Mode?
    let themeTrial: Bool
    private let sharedTheme: S4NativeTheme?
    private let fixtureID: UUID?
    private let instance = UUID()
    private var fixture: S4SignedFixture?
    private var started = false

    init() {
        let args = ProcessInfo.processInfo.arguments
        let usesSharedTheme = args.contains("--s4-shared-theme")
        themeTrial = usesSharedTheme || args.contains("--s4-platform-control")
        sharedTheme = usesSharedTheme ? S4SharedTheme.light : nil
        if let flag = args.firstIndex(of: "--s4-fixture"), args.count > flag + 2 {
            fixtureID = UUID(uuidString: args[flag + 1])
            mode = Mode(rawValue: args[flag + 2])
        } else {
            fixtureID = nil
            mode = nil
        }
    }

    func start() async {
        guard !started else { return }
        started = true
        do { try await run() }
        catch { status = "ERROR \(error)"; mayClose = owner != nil }
    }

    private func run() async throws {
        let mode = try require(mode, "mode")
        let fixtureID = try require(fixtureID, "fixture UUID")
        let support = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
                                                  appropriateFor: nil, create: true)
        let root = support.appendingPathComponent("S4-" + fixtureID.uuidString, isDirectory: true)
        let isReceiptTrial = [.tapBeforeReceipt, .tapAfterReceipt].contains(mode)
        let createsStore = isReceiptTrial || [.cold, .invalidFirst, .healthyRendererReplacement].contains(mode)
        if createsStore {
            try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        }
        let fixture = try S4SignedFixture(root: root)
        let existingValue = try createsStore ? fixture.liveSavedValue() : await fixture.savedValue()
        self.fixture = fixture
        if mode == .postIntentOffline {
            try recordRecovery(fixture, at: "freshProcessBeforeOpen", expected: "ui_protocol_after_effects")
        }
        let owner = try await CapabilityGuestUIRuntime.open(configuration: fixture.configuration,
                                                             execution: fixture.execution)
        self.owner = owner
        if isReceiptTrial || mode.isPostIntentFailure { owner.presentation.s4HoldNativeAcknowledgment = true }
        let prior = await owner.recoverySnapshot()
        var candidate: String?
        var expectedSequence = prior.acceptedSequence
        switch mode {
        case .cold: try check(prior.acceptedSequence == 0, "cold scope was already assigned")
        case .baseline, .tapBeforeReceipt, .tapAfterReceipt, .healthyRendererReplacement:
            try check(prior.acceptedSequence == 0 && existingValue == "empty", "baseline scope is dirty")
            expectedSequence = 1
            candidate = try await stage(.valid, sequence: expectedSequence, owner: owner, fixture: fixture)
        case .invalidFirst:
            expectedSequence = 1
            candidate = try await stage(.invalidHeader, sequence: expectedSequence, owner: owner, fixture: fixture)
        case .invalidRetained:
            try check(prior.acceptedSequence == 1 && existingValue == "AAH+/w==", "baseline did not persist")
            expectedSequence = 2
            _ = try await stage(.invalidHeader, sequence: expectedSequence, owner: owner, fixture: fixture)
            candidate = try require(prior.healthy, "retained baseline")
        case .reviewed:
            try check(prior.acceptedSequence == 2 && existingValue == "AAH+/w==", "review starting state")
            expectedSequence = 3
            candidate = try await stage(.localizedChecklist, sequence: expectedSequence, owner: owner, fixture: fixture)
        case .rollback:
            try check(prior.acceptedSequence == 3 && existingValue == "AAH+/w==", "rollback starting state")
            expectedSequence = 4
            candidate = try await stage(.valid, sequence: expectedSequence, owner: owner, fixture: fixture)
            try await rejectOldOffer(owner, fixture: fixture, staged: candidate)
        case .postIntentFailure, .postIntentFailureExit:
            // Starts from the saved tapAfterReceipt store: one healthy launch and committed bytes.
            try check(prior.acceptedSequence == 1 && existingValue == "AAH+/w==" && prior.healthy != nil &&
                      prior.staged == nil && prior.downloading == nil && !prior.incompleteAttempt,
                      "post-intent trial requires the saved receipt baseline")
            expectedSequence = 2
            candidate = try await stage(.localizedChecklist, sequence: expectedSequence, owner: owner, fixture: fixture)
            try check(candidate != prior.healthy, "post-intent candidate equals the retained baseline")
        case .postIntentOffline:
            try recordRecovery(fixture, at: "freshProcessAfterOpen", expected: "ui_protocol_after_effects")
            boundaryEvidence += "\n" + recoveryReadback(prior)
            try check(prior.acceptedSequence == 2 && existingValue == "AAH+/w==" && prior.staged == nil &&
                      prior.downloading == nil && !prior.incompleteAttempt && !prior.requiresReopen &&
                      !prior.activation.effectsMayHaveOpened && !owner.presentation.s4InputEnabled,
                      "offline relaunch did not begin from the recovered retained state")
            candidate = try require(prior.healthy, "retained healthy after post-intent failure")
        case .offline:
            try check(prior.acceptedSequence == 4 && existingValue == "AAH+/w==" && prior.staged == nil &&
                      prior.downloading == nil, "offline did not begin from the saved rollback")
            candidate = try require(prior.healthy, "cached rollback")
        }
        let launch = try await owner.start()
        if mode == .invalidFirst {
            let recovery = await owner.recoverySnapshot()
            boundaryEvidence = [
                "invalidFirst stagedCandidate=\(s4Value(candidate))",
                activationReadback(launch),
                recoveryReadback(recovery),
                owner.presentation.s4PresentationReadback
            ].joined(separator: "\n")
        }
        if [.invalidFirst, .invalidRetained].contains(mode) {
            let state = try JSONDecoder().decode(S4FailureReadback.self, from:
                Data(contentsOf: fixture.configuration.directory.appendingPathComponent("state.json")))
            if mode == .invalidFirst {
                boundaryEvidence += "\nlastRecovery=\(s4Value(state.lastRecovery))"
            }
            try check(state.lastRecovery == "ui_protocol_before_effects", "missing typed pre-effects rejection")
        }
        if mode == .cold || mode == .invalidFirst {
            try check(launch.phase == .nativeFallback, "fallback phase missing")
            try check(!launch.effectsMayHaveOpened, "fallback opened guest effects")
            try check(owner.presentation.s4Document == nil, "fallback retained a guest document")
            if mode == .cold {
                try check(launch.candidateID == nil && launch.launchID == nil, "cold fallback reported a guest attempt")
            } else {
                let rejected = try require(candidate, "rejected candidate")
                try check(launch.candidateID == rejected && launch.launchID.flatMap(UUID.init(uuidString:)) != nil,
                          "fallback did not identify the rejected attempt")
                let terminal = try require(launch.firstUIProtocolFailure, "typed startup rejection")
                try check(terminal.failure.phase == .startup && terminal.failure.code == .header &&
                          terminal.effectStage == .beforeIntent && launch.terminalCause == .protocolViolation(terminal) &&
                          launch.firstBridgeFailure == nil, "wrong invalid-header terminal classification")
                let state = await owner.recoverySnapshot()
                try check(!state.incompleteAttempt && !state.requiresReopen && state.staged == nil &&
                          state.downloading == nil && state.healthy == nil && state.acceptedSequence == expectedSequence &&
                          !launch.cleanupPending && owner.presentation.state == .stopped &&
                          !owner.presentation.s4InputEnabled && !owner.presentation.s4ObservedNativeDisplay &&
                          owner.presentation.s4PendingNativeReceipt == nil, "rejected attempt remained active")
            }
            let host = try MixerUIHost(document: Self.document(revision: 1, status: "Ready"))
            host.s4SharedTheme = sharedTheme
            bundled = host
            detail = "sequence=\(expectedSequence) effects=closed instance=\(instance) pid=\(getpid())"
            status = mode == .cold ? "bundled fallback" : "invalid first frame rejected"
            mayClose = true
            return
        }
        let id = try require(candidate, "selected candidate")
        let launchID = try require(launch.launchID, "launch ID")
        try check(launch.candidateID == id && launch.acceptedSequence == expectedSequence, "wrong guest selected")
        // Select the app's theme on the admitted host before mounting the themed screen.
        if sharedTheme == nil { showsGuest = true }
        let initial = (mode == .reviewed || mode.isPostIntentFailure) ? Self.reviewedDocument : Self.document(revision: 1, status: "Ready")
        try await wait("initial guest document") { owner.presentation.s4Document != nil }
        try assertDocument(owner.presentation.s4Document, equals: initial)
        if let sharedTheme {
            try check(owner.presentation.s4SelectSharedTheme(sharedTheme), "missing admitted renderer for shared theme")
            boundaryEvidence = "exact bundled and guest UIDocument bytes at revision 1"
            showsGuest = true
        }
        detail = "sequence=\(expectedSequence) candidate=\(id) launch=\(launchID) instance=\(instance) pid=\(getpid()) readback=\(existingValue)"

        let oldEnvelope = owner.presentation.s4SaveEnvelope()
        if mode.isPostIntentFailure {
            try await failAfterIntent(owner, candidate: id, retained: try require(prior.healthy, "retained"),
                                      replaceInProcess: mode == .postIntentFailure)
            return
        }
        if isReceiptTrial {
            detail += " payload=\(try require(stagedPayloadSHA256, "signed payload digest"))"
            try await compareReceiptBoundary(owner, mode: mode, candidate: id,
                                             initialEnvelope: try require(oldEnvelope, "initial save envelope"))
            return
        }

        try await wait("real native first screen health") {
            let state = await owner.recoverySnapshot()
            return state.activation.phase == .healthyGuest && state.healthy == id
        }
        try check(owner.presentation.s4ObservedNativeDisplay == true, "missing matching native observation")
        if mode == .healthyRendererReplacement {
            mayReplaceHealthyRenderer = true
            status = "original renderer healthy"
            return
        }
        if mode == .postIntentOffline {
            let state = await recordReceiptBoundary(owner, at: "freshProcessHealthy")
            try recordRecovery(fixture, at: "freshProcessHealthy", expected: "ui_protocol_after_effects")
            let presentation = owner.presentation
            try check(state.acceptedSequence == 2 && state.healthy == id && state.activation.effectsMayHaveOpened &&
                      presentation.s4InputEnabled && presentation.s4NativeCallbackCount == 0 &&
                      presentation.s4AcceptedEvents == 0 && presentation.s4DeliveredEvents == 0 &&
                      fixture.liveSavedValue() == "AAH+/w==", "offline health changed input, selection or saved bytes")
        }
        mayClose = true
        status = "\(mode.rawValue) healthy"
        if mode == .baseline {
            try await observeSave(owner, oldEnvelope: try require(oldEnvelope, "initial save envelope"))
            saveObservation = "post-health tap delivered; stale envelope refused"
        }
    }

    private func compareReceiptBoundary(_ owner: CapabilityGuestUIRuntime, mode: Mode,
                                        candidate: String, initialEnvelope: UIEventEnvelope) async throws {
        let presentation = owner.presentation
        let preReceiptTap = mode == .tapBeforeReceipt
        do {
            try await wait("native proof for revision 1 with input closed") {
                presentation.s4HeldDisplayTicket?.revision == 1 && !presentation.s4InputEnabled
            }
            let expected = try await checkReceiptHeld(owner, at: "initialNativeProof")
            mayConfirmRefusedTap = preReceiptTap
            mayReleaseReceipt = !preReceiptTap
            status = "revision 1 proof held, provisional"
            if preReceiptTap {
                try await wait("explicit refused tap check", seconds: 30) { self.confirmedRefusedTap }
                let afterTap = try await checkReceiptHeld(owner, at: "afterPreReceiptTap")
                try check(afterTap == expected, "proof changed after refused tap")
                mayReleaseReceipt = true
                saveObservation = "pre-receipt tap refused; no callback or write"
            }
            try await wait("explicit native acknowledgment release", seconds: 30) { self.receiptReleased }
            try await wait("exact native receipt and healthy candidate") {
                guard presentation.s4AcknowledgedDisplayTicket == expected, presentation.s4InputEnabled else { return false }
                let state = await owner.recoverySnapshot()
                return state.activation.phase == .healthyGuest && state.healthy == candidate
            }
            _ = await recordReceiptBoundary(owner, at: "exactReceiptAcknowledged")
            let fixture = try require(self.fixture, "opened fixture")
            try check(presentation.s4ObservedNativeDisplay && presentation.s4Document?.revision == 1 &&
                      presentation.s4NativeCallbackCount == 0 && presentation.s4AcceptedEvents == 0 &&
                      presentation.s4DeliveredEvents == 0 && fixture.liveSavedValue() == "empty",
                      "unexpected callback, event or write at first receipt")
            status = "\(mode.rawValue) healthy"
            if !preReceiptTap {
                try await observeSave(owner, oldEnvelope: initialEnvelope)
                try check(presentation.s4NativeCallbackCount == 1 && fixture.liveSavedValue() == "AAH+/w==",
                          "the native tap did not commit the exact bytes once")
                let replayed = presentation.s4ReplayLastNativeCallback()
                try check(replayed && presentation.s4AcceptedEvents == 1 && presentation.s4DeliveredEvents == 1 &&
                          presentation.s4NativeCallbackCount == 1, "late callback entered the guest")
                try check(presentation.s4AcknowledgedDisplayTicket == expected, "acknowledgment changed after the tap")
                _ = await recordReceiptBoundary(owner, at: "afterPostReceiptTapAndLateCallback")
                saveObservation = "post-receipt tap delivered once; late callback refused"
            }
            mayClose = true
        } catch {
            _ = await recordReceiptBoundary(owner, at: "trialFailed")
            throw error
        }
    }

    /// Post-intent first-frame failure. The signed candidate has confirmed effects
    /// and its first frame is natively displayed, but the fixture holds the exact
    /// receipt. A second real wrapper then trips the production attachment invariant.
    private func failAfterIntent(_ failed: CapabilityGuestUIRuntime, candidate: String, retained: String,
                                 replaceInProcess: Bool) async throws {
        let presentation = failed.presentation
        let fixture = try require(self.fixture, "opened fixture")
        do {
            try await wait("post-intent native proof with input closed") {
                presentation.s4HeldDisplayTicket?.revision == 1 && !presentation.s4InputEnabled
            }
            _ = try await checkReceiptHeld(failed, at: "postIntentProofHeld", retained: retained, disk: "AAH+/w==")
            let provisional = await failed.recoverySnapshot()
            try check(presentation.s4EffectsConfirmed == true && provisional.activation.effectsMayHaveOpened,
                      "first frame was not after effects intent")
            status = "post-intent proof held, provisional"
            mayAttachDuplicate = true
            try await wait("explicit duplicate attachment", seconds: 30) { self.duplicateRequested }
            let retiredCallback = try require(capturedRetiredCallback, "captured provisional callback")
            try await wait("post-intent recovery settled") {
                let state = await failed.recoverySnapshot()
                return state.activation.phase == .recoveryRequired && state.requiresReopen && !state.incompleteAttempt
            }
            let state = await recordReceiptBoundary(failed, at: "afterDuplicateAttachment")
            let terminal = try require(state.activation.firstUIProtocolFailure, "typed presentation failure")
            try check(terminal.failure.phase == .presentation && terminal.failure.code == .presentationInvariant &&
                      terminal.effectStage == .intentEntered && state.activation.terminalCause == .protocolViolation(terminal) &&
                      state.activation.effectsMayHaveOpened && state.activation.candidateID == candidate,
                      "wrong post-intent terminal classification")
            try recordRecovery(fixture, at: "failedOwnerSettled", expected: "ui_protocol_after_effects")
            try check(state.requiresReopen && state.healthy == retained && state.staged == nil &&
                      state.downloading == nil && !state.incompleteAttempt && state.acceptedSequence == 2,
                      "post-intent failure did not retain the healthy baseline")
            try check(!presentation.s4InputEnabled && !presentation.s4ObservedNativeDisplay &&
                      presentation.s4AcknowledgedDisplayTicket == nil && presentation.s4NativeCallbackCount == 0 &&
                      presentation.state == .stopped && presentation.s4Document == nil &&
                      fixture.liveSavedValue() == "AAH+/w==", "failed owner kept input, display or wrote")
            showsDuplicate = false
            showsGuest = false
            await failed.close()
            try await wait("failed owner retirement", seconds: 8) { failed.s4Retired }
            let closed = await recordReceiptBoundary(failed, at: "failedOwnerClosed")
            try recordRecovery(fixture, at: "failedOwnerClosed", expected: "ui_protocol_after_effects")
            let saved = try await fixture.savedValue()
            try check(closed.closed && !closed.incompleteAttempt && !closed.activation.cleanupPending &&
                      closed.acceptedSequence == 2 && closed.healthy == retained && saved == "AAH+/w==",
                      "failed-owner close changed the retained selection or saved bytes")
            owner = nil
            capturedRetiredCallback = nil
            if !replaceInProcess {
                status = "post-intent owner closed, disk=\(saved)"
                return
            }

            // A real replacement owner in the same process selects only the retained baseline.
            let replacement = try await CapabilityGuestUIRuntime.open(configuration: fixture.configuration,
                                                                       execution: fixture.execution)
            owner = replacement
            let prior = await recordReceiptBoundary(replacement, at: "replacementOpened")
            try recordRecovery(fixture, at: "replacementOpened", expected: "ui_protocol_after_effects")
            try check(prior.healthy == retained && prior.staged == nil && prior.acceptedSequence == 2 &&
                      prior.downloading == nil && !prior.incompleteAttempt && !prior.requiresReopen,
                      "replacement did not start from the retained baseline")
            let launch = try await replacement.start()
            _ = await recordReceiptBoundary(replacement, at: "replacementStarted")
            try recordRecovery(fixture, at: "replacementStarted", expected: "ui_protocol_after_effects")
            let launchID = try require(launch.launchID, "replacement launch ID")
            try check(launch.candidateID == retained, "replacement selected the failed candidate")
            showsGuest = true
            let next = replacement.presentation
            try await wait("replacement guest document") { next.s4Document != nil }
            try assertDocument(next.s4Document, equals: Self.document(revision: 1, status: "Ready"))
            try await wait("replacement native health") {
                let s = await replacement.recoverySnapshot()
                return s.activation.phase == .healthyGuest && s.healthy == retained
            }
            _ = await recordReceiptBoundary(replacement, at: "replacementHealthy")
            try recordRecovery(fixture, at: "replacementHealthy", expected: "ui_protocol_after_effects")
            try check(next.s4ObservedNativeDisplay && next.s4InputEnabled, "replacement lacks native receipt")
            retiredCallback()
            try await Task.sleep(for: .milliseconds(300))
            _ = await recordReceiptBoundary(replacement, at: "afterRetiredCallback")
            boundaryEvidence += "\nfailedOwner " + presentation.s4PresentationReadback
            try check(next.s4AcceptedEvents == 0 && next.s4DeliveredEvents == 0 && next.s4NativeCallbackCount == 0 &&
                      next.s4Document?.revision == 1 && presentation.s4AcceptedEvents == nil &&
                      presentation.s4NativeCallbackCount == 0 && fixture.liveSavedValue() == "AAH+/w==",
                      "retired callback reached an owner or storage")
            let after = await replacement.recoverySnapshot()
            try check(after.activation.phase == .healthyGuest && after.healthy == retained,
                      "retired callback changed replacement health")
            detail = "sequence=2 candidate=\(retained) launch=\(launchID) instance=\(instance) pid=\(getpid()) readback=AAH+/w=="
            saveObservation = "retired callback refused across owner replacement"
            status = "post-intent recovered healthy"
            mayClose = true
        } catch {
            if let owner { _ = await recordReceiptBoundary(owner, at: "postIntentFailed") }
            try? recordRecovery(fixture, at: "postIntentFailed")
            throw error
        }
    }

    func attachDuplicate() {
        guard mayAttachDuplicate, let owner else { return }
        mayAttachDuplicate = false
        // Capture the exact handler the provisional native renderer installed.
        capturedRetiredCallback = owner.presentation.s4CaptureInstalledCallback(nodeID: "toggle")
        duplicateRequested = true
        showsDuplicate = true
    }

    func confirmRefusedTap() {
        guard mayConfirmRefusedTap else { return }
        mayConfirmRefusedTap = false
        confirmedRefusedTap = true
    }

    func releaseReceipt() {
        guard mayReleaseReceipt, let owner else { return }
        mayReleaseReceipt = false
        receiptReleased = true
        owner.presentation.s4HoldNativeAcknowledgment = false
    }

    private func recordReceiptBoundary(_ owner: CapabilityGuestUIRuntime,
                                       at boundary: String) async -> CapabilityGuestUIRecoverySnapshot {
        let state = await owner.recoverySnapshot()
        let readback = [
            "\(boundary) uptime=\(ProcessInfo.processInfo.systemUptime) releaseRequested=\(receiptReleased)",
            activationReadback(state.activation),
            recoveryReadback(state),
            owner.presentation.s4PresentationReadback,
            "liveDisk=\(s4Value(try? fixture?.liveSavedValue()))"
        ].joined(separator: "\n")
        boundaryEvidence = boundaryEvidence == "pending" ? readback : boundaryEvidence + "\n\n" + readback
        return state
    }

    private func recordRecovery(_ fixture: S4SignedFixture, at boundary: String,
                                expected: String? = nil) throws {
        let url = fixture.configuration.directory.appendingPathComponent("state.json")
        let state = try JSONDecoder().decode(S4FailureReadback.self, from: Data(contentsOf: url))
        let readback = "\(boundary) lastRecovery=\(s4Value(state.lastRecovery))"
        boundaryEvidence = boundaryEvidence == "pending" ? readback : boundaryEvidence + "\n" + readback
        if let expected {
            try check(state.lastRecovery == expected, "\(readback), expected \(expected)")
        }
    }

    private func checkReceiptHeld(_ owner: CapabilityGuestUIRuntime, at boundary: String,
                                  retained: String? = nil, disk: String = "empty") async throws -> S4DisplayTicket {
        let state = await recordReceiptBoundary(owner, at: boundary)
        let presentation = owner.presentation
        let ticket = try require(presentation.s4HeldDisplayTicket, "held native proof")
        try check(!receiptReleased && presentation.s4HoldNativeAcknowledgment &&
                  ticket.revision == 1 && presentation.s4Document?.revision == 1 &&
                  presentation.s4NativeProbeHasAppeared == true && !presentation.s4InputEnabled,
                  "\(boundary): expected native proof and disabled input while the receipt is held")
        try check(!presentation.s4ObservedNativeDisplay && presentation.s4PendingNativeReceipt == nil &&
                  presentation.s4AcknowledgedDisplayTicket == nil,
                  "\(boundary): native display was acknowledged before release")
        let fixture = try require(self.fixture, "opened fixture")
        try check(state.activation.phase == .provisionalGuest && state.healthy == retained &&
                  presentation.s4NativeCallbackCount == 0 &&
                  presentation.s4AcceptedEvents == 0 && presentation.s4DeliveredEvents == 0 &&
                  fixture.liveSavedValue() == disk,
                  "\(boundary): callback, event or storage write before the receipt")
        return ticket
    }

    private func activationReadback(_ launch: CapabilityGuestUIActivationSnapshot) -> String {
        let terminal = launch.firstUIProtocolFailure
        return [
            "phase=\(launch.phase)", "effectsMayHaveOpened=\(launch.effectsMayHaveOpened)",
            "candidateID=\(s4Value(launch.candidateID))", "launchID=\(s4Value(launch.launchID))",
            "activationSequence=\(launch.acceptedSequence)", "cleanupPending=\(launch.cleanupPending)",
            "terminalCause=\(s4Value(launch.terminalCause))", "bridgeFailure=\(s4Value(launch.firstBridgeFailure))",
            "protocolPhase=\(s4Value(terminal?.failure.phase))", "protocolCode=\(s4Value(terminal?.failure.code))",
            "effectStage=\(s4Value(terminal?.effectStage))"
        ].joined(separator: " ")
    }

    private func recoveryReadback(_ state: CapabilityGuestUIRecoverySnapshot) -> String {
        return [
            "healthy=\(s4Value(state.healthy))", "staged=\(s4Value(state.staged))",
            "downloading=\(s4Value(state.downloading))", "incompleteAttempt=\(state.incompleteAttempt)",
            "requiresReopen=\(state.requiresReopen)", "recoverySequence=\(state.acceptedSequence)"
        ].joined(separator: " ")
    }

    private func observeSave(_ owner: CapabilityGuestUIRuntime, oldEnvelope: UIEventEnvelope) async throws {
        try await wait("native Save tap completed", seconds: 30) {
            owner.presentation.s4Document?.revision == 3
        }
        try assertDocument(owner.presentation.s4Document, equals: Self.document(revision: 3, status: "Saved sample"))
        let presentation = owner.presentation
        try check(presentation.s4RejectsStaleEnvelope(oldEnvelope), "revision-1 envelope still routes")
        try check(presentation.s4AcceptedEvents == 1 && presentation.s4DeliveredEvents == 1, "unexpected event counters")
        if sharedTheme != nil {
            boundaryEvidence += "\nexact bundled and guest UIDocument bytes at revision 3; accepted=1 delivered=1"
        }
    }

    func observeBundledAction(_ action: RoutedUIAction) {
        saveObservation = action.actionID == "sample.save" ? "bundled action routed" : "unexpected bundled action"
    }

    func close() async {
        guard mayClose, let owner, let fixture else { return }
        mayClose = false
        status = "closing"
        let retained = mode == .postIntentFailure ? await owner.recoverySnapshot().healthy : nil
        await owner.close()
        do {
            try await wait("owner retirement", seconds: 8) { owner.s4Retired }
            let closed = await owner.recoverySnapshot()
            if mode == .postIntentFailure {
                _ = await recordReceiptBoundary(owner, at: "replacementClosed")
                try recordRecovery(fixture, at: "replacementClosed", expected: "effects_closed")
                try check(closed.acceptedSequence == 2 && retained != nil && closed.healthy == retained,
                          "replacement close lost retained health")
            }
            try check(closed.closed && !closed.incompleteAttempt && !closed.activation.cleanupPending, "incomplete owner close")
            showsGuest = false
            self.owner = nil
            bundled = nil
            let data = try await fixture.savedValue()
            status = "owner closed, disk=\(data)"
        } catch { status = "ERROR \(error)" }
    }

    private func stage(_ variant: GuestUISignedProgram.Mode, sequence: UInt64,
                       owner: CapabilityGuestUIRuntime, fixture: S4SignedFixture) async throws -> String {
        let payload = GuestUISignedProgram.build(variant)
        let offer = try fixture.offer(payload, sequence: sequence)
        stagedPayloadSHA256 = ReleaseVerifier.sha256(payload)
        try await owner.beginDownload(signedManifest: offer.manifest, signedAssignment: offer.assignment)
        try await owner.appendDownload(payload, atOffset: 0)
        try await owner.finishDownload()
        let staged = await owner.recoverySnapshot()
        try check(staged.acceptedSequence == sequence, "wrong staged sequence")
        return try require(staged.staged, "staged candidate")
    }

    private func rejectOldOffer(_ owner: CapabilityGuestUIRuntime, fixture: S4SignedFixture,
                                staged: String?) async throws {
        let old = try fixture.offer(GuestUISignedProgram.build(), sequence: 1)
        do {
            try await owner.beginDownload(signedManifest: old.manifest, signedAssignment: old.assignment)
            throw UpdateError("s4.stale", "Stale signed assignment entered download")
        } catch let error as UpdateError where error.code == "v3.assignment.replay" {
            let state = await owner.recoverySnapshot()
            boundaryEvidence = "staleOffer=\(error.code) rejectedSequence=1 expectedStaged=\(s4Value(staged))\n" +
                recoveryReadback(state) + "\n" + activationReadback(state.activation)
            try check(state.acceptedSequence == 4 && state.staged == staged && state.downloading == nil &&
                      !state.activation.effectsMayHaveOpened, "stale assignment changed selection or effects")
        }
    }

    private func assertDocument(_ actual: MixerUI.UIDocument?, equals expected: MixerUI.UIDocument) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let rendered = try encoder.encode(require(actual, "guest document"))
        let bundled = try encoder.encode(MixerUIHost(document: expected).snapshot.document)
        try check(rendered == bundled, "bundled and guest document bytes differ")
    }

    private static func document(revision: UInt64, status: String) -> MixerUI.UIDocument {
        MixerUI.UIDocument(revision: revision, root: UINode(id: "root", kind: .vStack, children: [
            UINode(id: "status", kind: .text, properties: ["text": .string(status)]),
            UINode(id: "save", kind: .button, properties: ["label": .string("Save sample")],
                   actions: [UIActionBinding(id: "sample.save", event: .activate)])
        ]))
    }

    private static var reviewedDocument: MixerUI.UIDocument {
        MixerUI.UIDocument(revision: 1, root: UINode(id: "fieldlog-task", kind: .vStack, children: [
            UINode(id: "task", kind: .text, properties: ["text": .string("فحص المضخة 07")]),
            UINode(id: "status", kind: .text, properties: ["text": .string("الفحص قيد التنفيذ")]),
            UINode(id: "toggle", kind: .button, properties: ["label": .string("وضع علامة مكتملة")],
                   actions: [UIActionBinding(id: "task.toggle", event: .activate)])
        ]))
    }

    private func wait(_ boundary: String, seconds: Int = 15, _ condition: () async -> Bool) async throws {
        let deadline = ContinuousClock.now + .seconds(seconds)
        while !(await condition()) {
            try check(ContinuousClock.now < deadline, "Timed out at \(boundary)")
            try await Task.sleep(for: .milliseconds(20))
        }
    }
}

extension S4Run {
    func replaceHealthyRenderer() async {
        guard mayReplaceHealthyRenderer, let original = owner, let fixture else { return }
        mayReplaceHealthyRenderer = false
        do {
            let old = original.presentation
            let prior = await recordReceiptBoundary(original, at: "healthyRendererBeforeClose")
            let candidate = try require(prior.healthy, "retained baseline")
            let originalLaunch = try require(prior.activation.launchID, "original launch")
            try check(prior.activation.phase == .healthyGuest && old.s4AcknowledgedDisplayTicket?.revision == 1 &&
                      old.s4Document?.revision == 1 && old.s4NativeCallbackCount == 0 &&
                      old.s4AcceptedEvents == 0 && old.s4DeliveredEvents == 0 && fixture.liveSavedValue() == "empty",
                      "expected a healthy renderer with an untouched revision-1 Save")
            let delayed = try require(old.s4CaptureInstalledCallback(nodeID: "save", requiringEnabledInput: true),
                                      "renderer-installed Save handler from enabled revision 1")

            showsGuest = false
            await original.close()
            try await wait("original owner retired", seconds: 8) { original.s4Retired }
            let closed = await recordReceiptBoundary(original, at: "healthyRendererClosed")
            try check(closed.closed && !closed.incompleteAttempt && !closed.activation.cleanupPending &&
                      old.s4Document == nil && !old.s4InputEnabled, "original renderer retained authority")

            let replacement = try await CapabilityGuestUIRuntime.open(configuration: fixture.configuration,
                                                                      execution: fixture.execution)
            owner = replacement
            let launch = try await replacement.start()
            let launchID = try require(launch.launchID, "replacement launch")
            try check(launch.candidateID == candidate && launchID != originalLaunch, "replacement launch mismatch")
            showsGuest = true
            let next = replacement.presentation
            try await wait("replacement renderer healthy") {
                let recovery = await replacement.recoverySnapshot()
                return recovery.activation.phase == .healthyGuest && recovery.healthy == candidate &&
                    next.s4AcknowledgedDisplayTicket?.revision == 1 && next.s4InputEnabled
            }
            try assertDocument(next.s4Document, equals: Self.document(revision: 1, status: "Ready"))
            let envelope = try require(next.s4SaveEnvelope(), "replacement Save envelope")
            _ = await recordReceiptBoundary(replacement, at: "beforeDelayedHealthyCallback")
            let retiredReadback = old.s4PresentationReadback
            delayed()
            try await Task.sleep(for: .milliseconds(300))
            let after = await recordReceiptBoundary(replacement, at: "afterDelayedHealthyCallback")
            boundaryEvidence += "\nretired renderer " + old.s4PresentationReadback
            try check(old.s4PresentationReadback == retiredReadback && next.s4NativeCallbackCount == 0 &&
                      next.s4AcceptedEvents == 0 && next.s4DeliveredEvents == 0 &&
                      after.activation.phase == .healthyGuest && after.healthy == candidate &&
                      fixture.liveSavedValue() == "empty", "delayed callback reached an owner or storage")
            try assertDocument(next.s4Document, equals: Self.document(revision: 1, status: "Ready"))
            detail = "sequence=\(after.acceptedSequence) candidate=\(candidate) launch=\(launchID) instance=\(instance) pid=\(getpid()) readback=empty"
            status = "replacement healthy; delayed callback refused"

            try await observeSave(replacement, oldEnvelope: envelope)
            _ = await recordReceiptBoundary(replacement, at: "afterReplacementSave")
            try check(next.s4NativeCallbackCount == 1 && fixture.liveSavedValue() == "AAH+/w==",
                      "replacement input control did not save")
            saveObservation = "replacement Save delivered once"
            mayClose = true
        } catch {
            status = "ERROR \(error)"
            mayClose = owner != nil
        }
    }
}

private struct S4FailureReadback: Decodable {
    let lastRecovery: String?
}
