import AppKit
import SwiftUI
import Combine
import Foundation
import MixerCapabilities
import MixerUpdates
import MixerCapabilityActivation

@main
@MainActor
enum SignedWindowHarness {
    private static let delegate = SignedWindowDelegate()
    static func main() {
        let app = NSApplication.shared
        app.setActivationPolicy(.regular)
        app.delegate = delegate
        app.run()
    }
}

@MainActor
private final class SignedWindowDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    private var window: NSWindow?
    private var model: SignedWindowModel?
    func applicationDidFinishLaunching(_ notification: Notification) {
        do {
            let model = try SignedWindowModel(arguments: CommandLine.arguments)
            self.model = model
            let window = NSWindow(contentRect: NSRect(x: 180, y: 180, width: 620, height: 470),
                                  styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
            self.window = window; model.window = window
            window.title = "Mixer signed guest UI verification"
            window.isReleasedWhenClosed = false; window.delegate = self
            window.contentView = NSHostingView(rootView: SignedWindowContent(model: model))
            window.makeKeyAndOrderFront(nil)
            NSApplication.shared.activate()
            model.prepare()
        } catch {
            let alert = NSAlert()
            alert.messageText = "Signed harness could not start"
            alert.informativeText = String(describing: error)
            alert.runModal()
            NSApplication.shared.terminate(nil)
        }
    }
    func windowShouldClose(_ sender: NSWindow) -> Bool {
        model?.closeAndVerify()
        return false
    }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        guard let model, !model.closed else { return .terminateNow }
        model.closeAndVerify(quitAfter: true)
        return .terminateCancel
    }
}

@MainActor
private struct SignedWindowContent: View {
    @ObservedObject var model: SignedWindowModel
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Signed guest / native window check").font(.headline)
            Text(model.statusLine).accessibilityIdentifier("harness.status")
            if let runtime = model.runtime {
                MixerGuestScreen(presentation: runtime.presentation)
                    .disabled(model.savedObserved || model.closed)
                    .frame(maxWidth: .infinity, minHeight: 180, maxHeight: .infinity)
                    .padding(12).border(Color.secondary.opacity(0.5))
            } else {
                Text("Preparing signed runtime…").frame(maxWidth: .infinity, minHeight: 180)
            }
            Text(model.observationLine).font(.caption).accessibilityIdentifier("harness.observations")
            HStack {
                Button("Close and verify storage") { model.closeAndVerify() }
                    .disabled(model.runtime == nil || model.closing || model.closed)
                    .accessibilityIdentifier("harness.close")
                Button("Quit") { model.closeAndVerify(quitAfter: true) }
                    .disabled(model.closing).accessibilityIdentifier("harness.quit")
            }
        }.padding(20).frame(minWidth: 520, minHeight: 380)
    }
}

@MainActor
private final class SignedWindowModel: ObservableObject {
    @Published private(set) var runtime: CapabilityGuestUIRuntime?
    @Published private(set) var statusLine = "Opening the public signed runtime…"
    @Published private(set) var observationLine = "No guest revisions or health observed."
    @Published private(set) var savedObserved = false
    @Published private(set) var closing = false
    @Published private(set) var closed = false
    weak var window: NSWindow?
    private let output: URL
    private let dataRoot: URL
    private var fixture: GuestUISignedFixture?
    private var work: Task<Void, Never>?
    private var monitor: Task<Void, Never>?
    private var closeWork: Task<Void, Never>?
    private var presentationObservation: AnyCancellable?
    private var revisions: [UInt64] = []
    private var history: [[String: Any]] = []
    private var healthyObserved = false
    private var beforeClose: [String: Any]?
    private var recovery: [String: Any] = [:]
    private var status = "preparing"
    private var failure: String?
    private var stored: [String: Any]?
    private var moduleSHA256: String?
    private let launchedAt = Date().timeIntervalSince1970

    init(arguments: [String]) throws {
        let base = (Bundle.main.object(forInfoDictionaryKey: "MixerHarnessEvidenceDirectory") as? String)
            ?? FileManager.default.temporaryDirectory.appendingPathComponent("mixer-signed-window").path
        var outputPath = URL(fileURLWithPath: base).appendingPathComponent("runs/default/progress.json").path
        var rootPath = URL(fileURLWithPath: base).appendingPathComponent("runs/default/data").path
        var position = 1
        while position < arguments.count {
            guard position + 1 < arguments.count else { throw HarnessError.invalidArguments }
            let name = arguments[position], value = arguments[position + 1]
            guard value.hasPrefix("/") else { throw HarnessError.invalidArguments }
            if name == "--output" { outputPath = value }
            else if name == "--run-root" { rootPath = value }
            else { throw HarnessError.invalidArguments }
            position += 2
        }
        output = URL(fileURLWithPath: outputPath); dataRoot = URL(fileURLWithPath: rootPath)
        guard !FileManager.default.fileExists(atPath: dataRoot.path) else { throw HarnessError.existingRunRoot }
        try FileManager.default.createDirectory(at: output.deletingLastPathComponent(), withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
        publish()
    }

    func prepare() {
        guard work == nil else { return }
        work = Task { @MainActor [weak self] in
            guard let self else { return }
            do {
                let fixture = try GuestUISignedFixture(root: self.dataRoot)
                self.fixture = fixture
                // The only runtime constructor used by this harness is public.
                let runtime = try await CapabilityGuestUIRuntime.open(configuration: fixture.configuration, execution: fixture.execution)
                self.runtime = runtime
                self.presentationObservation = runtime.presentation.$state.sink { [weak self] value in
                    self?.observe(value)
                }
                self.statusLine = "Downloading through the public signed ingress…"
                let bytes = GuestUISignedProgram.build()
                self.moduleSHA256 = ReleaseVerifier.sha256(bytes)
                let documents = try fixture.documents(bytes, storage: true)
                try await runtime.beginDownload(signedManifest: documents.0, signedAssignment: documents.1)
                try await runtime.appendDownload(bytes, atOffset: 0)
                try await runtime.finishDownload()
                self.status = "awaiting_foreground_start"
                self.statusLine = "Signed payload staged. Activate this visible window to start."
                self.publish()
                // This only delays public start until the operator's window is
                // foreground. It does not report presentation or health.
                let end = ContinuousClock.now + .seconds(600)
                while !self.foregroundWindow() {
                    try Task.checkCancellation()
                    guard ContinuousClock.now < end else { throw HarnessError.foregroundTimeout }
                    try await Task.sleep(for: .milliseconds(100))
                }
                _ = try await runtime.start()
                self.status = "awaiting_guest_save"
                self.statusLine = "Click the guest’s Save sample button once."
                self.publish()
                self.startMonitor(runtime)
            } catch is CancellationError {
                if !self.closing { self.fail("Public setup was cancelled") }
            } catch { self.fail(String(describing: error)) }
        }
    }

    private func foregroundWindow() -> Bool {
        guard let window else { return false }
        return NSApplication.shared.isActive && window.isVisible && window.isKeyWindow &&
            !window.isMiniaturized && window.occlusionState.contains(.visible)
    }

    private func observe(_ value: GuestUIPresentationState) {
        if case .displaying(let revision) = value {
            if !revisions.contains(revision), revisions.count < 8 { revisions.append(revision) }
            savedObserved = revisions.contains(3)
        }
        let state = String(describing: value)
        if history.last?["state"] as? String != state, history.count < 16 {
            history.append(["state": state, "atUnix": Date().timeIntervalSince1970])
        }
        updateObservationLine(); publish()
    }

    private func startMonitor(_ runtime: CapabilityGuestUIRuntime) {
        monitor = Task { @MainActor [weak self, runtime] in
            while !Task.isCancelled {
                guard let self, !self.closing else { return }
                let snapshot = await runtime.recoverySnapshot()
                self.recovery = self.describe(snapshot)
                if snapshot.healthy != nil && snapshot.activation.phase == .healthyGuest { self.healthyObserved = true }
                if snapshot.activation.firstBridgeFailure != nil || snapshot.activation.firstUIProtocolFailure != nil ||
                    snapshot.activation.requiresReopen {
                    self.fail("Public runtime reported a terminal failure or required reopen")
                    return
                }
                if self.savedObserved {
                    self.status = self.healthyObserved ? "ready_to_close" : "saved_waiting_health"
                    self.statusLine = self.healthyObserved ? "Saved revision observed; native display health committed. Close and verify storage." :
                        "Saved revision observed. Waiting for native display health."
                }
                self.updateObservationLine(); self.publish()
                do { try await Task.sleep(for: .milliseconds(100)) }
                catch { return }
            }
        }
    }

    func closeAndVerify(quitAfter: Bool = false) {
        if closed {
            if quitAfter { NSApplication.shared.terminate(nil) }
            return
        }
        guard closeWork == nil else { return }
        closing = true; work?.cancel(); monitor?.cancel()
        statusLine = "Closing the public runtime and checking committed storage…"
        closeWork = Task { @MainActor [weak self] in
            guard let self else { return }
            if let runtime = self.runtime {
                let before = await runtime.recoverySnapshot()
                self.beforeClose = self.describe(before)
                if before.healthy != nil && before.activation.phase == .healthyGuest { self.healthyObserved = true }
                await runtime.close()
                let end = ContinuousClock.now + .seconds(10)
                var after = await runtime.recoverySnapshot()
                while after.activation.cleanupPending && ContinuousClock.now < end {
                    try? await Task.sleep(for: .milliseconds(50))
                    after = await runtime.recoverySnapshot()
                }
                self.recovery = self.describe(after)
                if after.activation.cleanupPending { self.failure = "Native cleanup remained pending after public close" }
                else {
                    do {
                        let reader = try AppPrivateKeyValueStore(directory: self.dataRoot.appendingPathComponent("material_test"), namespaces: ["material_test"])
                        let value = try await reader.get(.init(namespace: "material_test", key: "binary"))
                        await reader.close()
                        self.stored = ["found": value.found, "valueBase64": value.valueBase64,
                                       "expectedValueBase64": "AAH+/w==", "matchesExpectedBytes": value.found && value.valueBase64 == "AAH+/w=="]
                    } catch { self.failure = "Storage reopen failed: " + String(describing: error) }
                }
            }
            let complete = self.revisions.contains(1) && self.revisions.contains(2) && self.revisions.contains(3) &&
                self.healthyObserved && self.stored?["matchesExpectedBytes"] as? Bool == true && self.failure == nil
            self.closed = true; self.closing = false
            self.status = complete ? "passed" : "closed_without_full_qualification"
            self.statusLine = complete ? "PASS: signed guest event, committed bytes, native display health, and joined close." :
                "Closed. Full qualification was not earned; inspect progress.json."
            self.updateObservationLine(); self.publish()
            if quitAfter { NSApplication.shared.terminate(nil) }
        }
    }

    private func updateObservationLine() {
        observationLine = "Guest revisions: \(revisions.map(String.init).joined(separator: " → ")); native health: \(healthyObserved ? "observed via public snapshot" : "pending")."
    }
    private func describe(_ value: CapabilityGuestUIRecoverySnapshot) -> [String: Any] {
        ["phase": String(describing: value.activation.phase), "candidateID": value.activation.candidateID as Any? ?? NSNull(),
         "launchID": value.activation.launchID as Any? ?? NSNull(), "healthy": value.healthy as Any? ?? NSNull(),
         "closed": value.closed, "busy": value.busy, "cleanupPending": value.activation.cleanupPending,
         "incompleteAttempt": value.incompleteAttempt, "requiresReopen": value.requiresReopen,
         "effectsMayHaveOpened": value.activation.effectsMayHaveOpened,
         "firstBridgeFailure": value.activation.firstBridgeFailure.map { String(describing: $0) } as Any? ?? NSNull(),
         "firstUIProtocolFailure": value.activation.firstUIProtocolFailure.map { String(describing: $0) } as Any? ?? NSNull(),
         "terminalCause": value.activation.terminalCause.map { String(describing: $0) } as Any? ?? NSNull()]
    }
    private func fail(_ message: String) {
        failure = message; status = "failed"; statusLine = "Verification failed: " + message; publish()
    }
    private func publish() {
        let record: [String: Any] = [
            "schemaVersion": 1, "status": status, "statusLine": statusLine, "launchedAtUnix": launchedAt,
            "updatedAtUnix": Date().timeIntervalSince1970, "runRoot": dataRoot.path,
            "moduleSHA256": moduleSHA256 as Any? ?? NSNull(), "presentationRevisions": revisions,
            "presentationHistory": history, "nativeHealthObservedThroughPublicRecoverySnapshot": healthyObserved,
            "recovery": recovery, "beforeCloseRecovery": beforeClose as Any? ?? NSNull(),
            "stored": stored as Any? ?? NSNull(), "failure": failure as Any? ?? NSNull(),
            "window": ["visible": window?.isVisible ?? false, "key": window?.isKeyWindow ?? false,
                       "occlusionRaw": window?.occlusionState.rawValue ?? 0,
                       "occlusionVisible": window?.occlusionState.contains(.visible) ?? false,
                       "applicationActive": NSApplication.shared.isActive],
            "scope": "Original local signed bytecode fixture; public runtime ingress/presentation/recovery only. Operator performs native guest button. Model revision history is not pixel/compositor proof. No physical device or published-consumer/GA qualification."]
        do {
            let bytes = try JSONSerialization.data(withJSONObject: record, options: [.prettyPrinted, .sortedKeys])
            try bytes.write(to: output, options: .atomic)
        } catch {
            statusLine = "Could not write progress evidence: " + String(describing: error)
        }
    }
}

private enum HarnessError: Error {
    case invalidArguments, existingRunRoot, foregroundTimeout
}
