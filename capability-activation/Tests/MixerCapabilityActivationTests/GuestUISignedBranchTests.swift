#if os(macOS) && canImport(SwiftUI) && canImport(MixerApple)
import Foundation
import XCTest
import MixerUI
import MixerUpdates
@_spi(GuestUIV1) import MixerGuest
@testable import MixerCapabilityActivation

final class GuestUISignedBranchTests: XCTestCase {
    @MainActor
    func testSignedBranchTablePresentsSelectedDocument() async throws {
        let payload = SignedBranchGuest.build()
        print("SIGNED_BRANCH payload bytes=\(payload.count) sha256=\(ReleaseVerifier.sha256(payload))")

        for (selector, expectedText) in [("0", "Zero"), ("1", "One!"), ("9", "Else")] {
            try await withOwner { fixture, owner in
                try await append(payload, signedFor: payload, fixture: fixture, owner: owner)
                try await owner.finishDownload()
                let staged = await owner.recoverySnapshot()
                XCTAssertNotNil(staged.staged)

                let startup = try await owner.start()
                XCTAssertEqual(startup.phase, .provisionalGuest)
                XCTAssertTrue(startup.effectsMayHaveOpened)
                let model = owner.presentation
                try await awaitPresentation { model.state == .displaying(revision: 1) }
                let attachment = try XCTUnwrap(model.claimNativeAttachment())
                try await awaitPresentation { model.inputEnabled }

                let host = try XCTUnwrap(model.renderHost)
                XCTAssertEqual(host.snapshot.document.root.children.map(\.id), ["pick0", "pick1", "pick9"])
                let identity = try XCTUnwrap(host.snapshot.identity(for: "pick\(selector)"))
                let action = try host.route(.init(revision: 1, identity: identity, event: .activate))
                XCTAssertEqual(action.actionID, "pick.\(selector)")
                XCTAssertEqual(model.lifecycleObservation?.counters.acceptedEvents, 0)
                model.actionHandler(host: host, attachment: attachment)(action)

                try await awaitPresentation {
                    model.state == .displaying(revision: 2) && model.lastEventResult?.outcome == .delivered
                }
                let expected = UIDocument(revision: 2, root: UINode(
                    id: "status", kind: .text, properties: ["text": .string(expectedText)]))
                let document = try XCTUnwrap(model.renderHost?.snapshot.document)
                XCTAssertEqual(document, expected)
                XCTAssertEqual(model.lastEventResult?.sequence, 1)
                XCTAssertEqual(model.lifecycleObservation?.counters.acceptedEvents, 1)
                XCTAssertEqual(model.lifecycleObservation?.counters.deliveredEvents, 1)
                XCTAssertEqual(model.lifecycleObservation?.counters.terminalEvents, 0)
                XCTAssertEqual(model.lifecycleObservation?.counters.producedFrames, 2)
                let recovery = await owner.recoverySnapshot()
                XCTAssertNil(recovery.healthy)
                XCTAssertNil(recovery.activation.firstBridgeFailure)
                XCTAssertNil(recovery.activation.firstUIProtocolFailure)
                XCTAssertNil(recovery.activation.terminalCause)
                let observedText = try XCTUnwrap(document.root.properties["text"]?.string)
                print("SIGNED_BRANCH selector=\(selector) revision=\(document.revision) text=\(observedText) sequence=\(model.lastEventResult?.sequence ?? 0)")
            }
        }
    }

    @MainActor
    func testSignedBranchPayloadMismatchLeavesColdOwnerWithoutPresentation() async throws {
        let payload = SignedBranchGuest.build()
        let replacement = SignedBranchGuest.build(defaultLabel: "Stop")
        XCTAssertEqual(replacement.count, payload.count)
        XCTAssertNotEqual(replacement, payload)
        try await withOwner { fixture, owner in
            try await append(replacement, signedFor: payload, fixture: fixture, owner: owner)
            do {
                try await owner.finishDownload()
                XCTFail("Staged bytes that differ from the signed payload")
            } catch let error as UpdateError {
                XCTAssertEqual(error.code, "v3.payload.integrity")
                print("SIGNED_BRANCH refusal=\(error.code)")
            }
            let startup = try await owner.start()
            XCTAssertEqual(startup.phase, .nativeFallback)
            XCTAssertFalse(startup.effectsMayHaveOpened)
            let recovery = await owner.recoverySnapshot()
            XCTAssertNil(recovery.staged)
            XCTAssertNil(recovery.healthy)
            XCTAssertFalse(recovery.incompleteAttempt)
            let model = owner.presentation
            XCTAssertEqual(model.state, .waiting)
            XCTAssertNil(model.renderHost)
            XCTAssertNil(model.lifecycleObservation)
            XCTAssertFalse(model.inputEnabled)
            print("SIGNED_BRANCH cold phase=\(startup.phase) presentation=\(model.state) input=\(model.inputEnabled)")
        }
    }

    @MainActor
    func testSignedSwiftValidateTrapDiagnostic() async throws {
        guard let directory = ProcessInfo.processInfo.environment["MIXER_SIGNED_SWIFT_DIAGNOSTIC_MODULES"] else {
            throw XCTSkip("Requires the compact Swift event fixtures from the W15 installed-host replay")
        }
        let expected = UIDocument(revision: 1, root: UINode(
            id: "button", kind: .button, properties: ["label": .string("Validate")],
            actions: [.init(id: "validate", event: .activate)]))
        let moduleDirectory = URL(fileURLWithPath: directory, isDirectory: true)

        for variant in ["matched", "stripped"] {
            let payload = try Data(contentsOf: moduleDirectory.appendingPathComponent(variant + ".wasm"))
            try await withOwner(checkFallbackAfterRetirement: true) { fixture, owner in
                try await append(payload, signedFor: payload, fixture: fixture, owner: owner)
                try await owner.finishDownload()
                let staged = await owner.recoverySnapshot()
                XCTAssertNotNil(staged.staged)
                XCTAssertEqual(staged.acceptedSequence, 1)

                let startup = try await owner.start()
                guard startup.phase == .provisionalGuest else {
                    return XCTFail("Signed Swift startup reached \(startup.phase), cause \(String(describing: startup.terminalCause))")
                }
                XCTAssertTrue(startup.effectsMayHaveOpened)
                XCTAssertEqual(startup.candidateID, staged.staged)
                XCTAssertNil(startup.firstBridgeFailure)

                let model = owner.presentation
                try await awaitPresentation { model.state == .displaying(revision: 1) }
                let attachment = try XCTUnwrap(model.claimNativeAttachment())
                try await awaitPresentation { model.inputEnabled }
                let host = try XCTUnwrap(model.renderHost)
                XCTAssertEqual(host.snapshot.document, expected)

                @MainActor
                func routeValidate() throws -> RoutedUIAction {
                    let identity = try XCTUnwrap(host.snapshot.identity(for: "button"))
                    let action = try host.route(.init(revision: 1, identity: identity, event: .activate))
                    XCTAssertEqual(action.actionID, "validate")
                    return action
                }

                model.actionHandler(host: host, attachment: attachment)(try routeValidate())
                try await awaitPresentation {
                    model.lastEventResult?.outcome == .delivered && model.inputEnabled
                }
                XCTAssertEqual(model.lastEventResult?.sequence, 1)
                XCTAssertEqual(model.state, .displaying(revision: 1))
                XCTAssertEqual(model.renderHost?.snapshot.document, expected)
                XCTAssertEqual(model.lifecycleObservation?.counters.acceptedEvents, 1)
                XCTAssertEqual(model.lifecycleObservation?.counters.deliveredEvents, 1)
                XCTAssertEqual(model.lifecycleObservation?.counters.terminalEvents, 0)
                // Returning the same document keeps the existing revision on screen.
                XCTAssertEqual(model.lifecycleObservation?.counters.producedFrames, 1)
                let beforeTrap = await owner.recoverySnapshot()
                XCTAssertEqual(beforeTrap.activation.phase, .provisionalGuest)
                XCTAssertNil(beforeTrap.activation.firstBridgeFailure)
                XCTAssertNil(beforeTrap.activation.firstUIProtocolFailure)
                XCTAssertNil(beforeTrap.healthy)
                print("SIGNED_SWIFT \(variant) bytes=\(payload.count) sha256=\(ReleaseVerifier.sha256(payload)) accepted=\(staged.acceptedSequence) label=Validate revision=\(host.snapshot.document.revision) delivered=\(model.lastEventResult?.sequence ?? 0)")

                let oldHandler = model.actionHandler(host: host, attachment: attachment)
                let action = try routeValidate()
                oldHandler(action)
                try await awaitPresentation {
                    model.state == .stopped && model.lastEventResult?.outcome == .terminal(turnBegan: true)
                }
                XCTAssertEqual(model.lastEventResult?.sequence, 2)
                XCTAssertFalse(model.inputEnabled)
                XCTAssertNil(model.renderHost)
                let terminalResult = model.lastEventResult
                oldHandler(action)
                XCTAssertEqual(model.lastEventResult, terminalResult)
                XCTAssertFalse(model.inputEnabled)

                let deadline = ContinuousClock.now + .seconds(5)
                var recovery = await owner.recoverySnapshot()
                while (recovery.activation.firstBridgeFailure == nil || recovery.busy || recovery.incompleteAttempt ||
                       recovery.activation.cleanupPending || !recovery.requiresReopen), ContinuousClock.now < deadline {
                    try await Task.sleep(for: .milliseconds(2))
                    recovery = await owner.recoverySnapshot()
                }
                let failure = try XCTUnwrap(recovery.activation.firstBridgeFailure)
                let location = try XCTUnwrap(failure.location)
                XCTAssertEqual(failure.kind, .guestTrap(.unreachable))
                XCTAssertEqual(failure.operation, .invocation)
                XCTAssertEqual(failure.code, "unreachable")
                XCTAssertEqual(failure.nativeStatus, 2)
                XCTAssertEqual(location.functionIndex, 3)
                XCTAssertEqual(location.byteOffset, 514)
                if variant == "matched" {
                    let source = try XCTUnwrap(location.source)
                    XCTAssertEqual(source.file, "SwiftEventGuest.swift")
                    XCTAssertEqual(source.line, 32)
                    XCTAssertEqual(source.column, 9)
                } else {
                    XCTAssertNil(location.source)
                }
                XCTAssertEqual(recovery.activation.terminalCause, .bridge)
                XCTAssertNil(recovery.activation.firstUIProtocolFailure)
                XCTAssertEqual(recovery.activation.phase, .recoveryRequired)
                XCTAssertTrue(recovery.activation.effectsMayHaveOpened)
                XCTAssertTrue(recovery.requiresReopen)
                XCTAssertTrue(recovery.activation.requiresReopen)
                XCTAssertFalse(recovery.incompleteAttempt)
                XCTAssertFalse(recovery.busy)
                XCTAssertFalse(recovery.activation.cleanupPending)
                XCTAssertNil(recovery.staged)
                XCTAssertNil(recovery.healthy)
                XCTAssertNil(recovery.previousHealthy)
                let source = location.source.map { "\($0.file):\($0.line):\($0.column ?? 0)" } ?? "none"
                print("SIGNED_SWIFT \(variant) kind=\(failure.kind) operation=\(failure.operation) status=\(failure.nativeStatus ?? 0) code=\(failure.code) function=\(location.functionIndex ?? 0) offset=\(location.byteOffset) source=\(source)")
                print("SIGNED_SWIFT \(variant) terminalSequence=\(terminalResult?.sequence ?? 0) outcome=\(String(describing: terminalResult?.outcome)) phase=\(recovery.activation.phase) requiresReopen=\(recovery.requiresReopen) input=\(model.inputEnabled) renderHost=\(model.renderHost != nil)")
            }
        }
    }

    @MainActor
    private func append(_ bytes: Data, signedFor payload: Data, fixture: GuestUISignedFixture,
                        owner: CapabilityGuestUIRuntime) async throws {
        let (manifest, assignment) = try fixture.documents(payload)
        try await owner.beginDownload(signedManifest: manifest, signedAssignment: assignment)
        try await owner.appendDownload(bytes, atOffset: 0)
    }

    @MainActor
    private func withOwner(checkFallbackAfterRetirement: Bool = false,
                           _ exercise: (GuestUISignedFixture, CapabilityGuestUIRuntime) async throws -> Void) async throws {
        let files = FileManager.default
        let root = files.temporaryDirectory.appendingPathComponent("mixer-signed-branch-" + UUID().uuidString)
        try files.createDirectory(at: root, withIntermediateDirectories: false)
        var removable = true
        defer {
            if removable {
                do {
                    try files.removeItem(at: root)
                    XCTAssertFalse(files.fileExists(atPath: root.path))
                    print("SIGNED_BRANCH removed=\(root.path)")
                } catch {
                    XCTFail("Could not remove test fixture at \(root.path). \(error)")
                }
            } else {
                XCTFail("Retaining fixture while owner retirement is unconfirmed at \(root.path)")
            }
        }

        let baseline = CapabilityAttemptReservation.occupiedSlots
        let fixture = try GuestUISignedFixture(root: root)
        removable = false
        let owner = try await CapabilityGuestUIRuntime.open(configuration: fixture.configuration, execution: fixture.execution)
        var failure: Error?
        do { try await exercise(fixture, owner) }
        catch { failure = error }

        let recovery = try await retire(owner, baseline: baseline)
        removable = recovery.closed && !recovery.activation.cleanupPending
        XCTAssertTrue(removable)
        if let failure { throw failure }

        if checkFallbackAfterRetirement {
            removable = false
            let reopened = try await CapabilityGuestUIRuntime.open(configuration: fixture.configuration, execution: fixture.execution)
            do {
                let fallback = try await reopened.start()
                XCTAssertEqual(fallback.phase, .nativeFallback)
                XCTAssertFalse(fallback.effectsMayHaveOpened)
                XCTAssertEqual(reopened.presentation.state, .waiting)
                XCTAssertNil(reopened.presentation.renderHost)
                XCTAssertFalse(reopened.presentation.inputEnabled)
                print("SIGNED_SWIFT reopened=\(fallback.phase) presentation=\(reopened.presentation.state) input=\(reopened.presentation.inputEnabled)")
            } catch { failure = error }
            let recovered = try await retire(reopened, baseline: baseline)
            removable = recovered.closed && !recovered.activation.cleanupPending
            XCTAssertTrue(removable)
            if let failure { throw failure }
        }
    }

    @MainActor
    private func retire(_ owner: CapabilityGuestUIRuntime, baseline: Int) async throws -> CapabilityGuestUIRecoverySnapshot {
        var closeReturned = false
        let close = Task {
            await owner.close()
            closeReturned = true
        }
        try await awaitPresentation { closeReturned && owner.ownerRetired }
        await close.value
        let recovery = await owner.recoverySnapshot()
        XCTAssertEqual(owner.presentation.state, .stopped)
        XCTAssertNil(owner.presentation.renderHost)
        XCTAssertFalse(owner.presentation.inputEnabled)
        let slots = CapabilityAttemptReservation.occupiedSlots
        XCTAssertEqual(slots, baseline)
        print("SIGNED_BRANCH retired=\(owner.ownerRetired) closed=\(recovery.closed) cleanupPending=\(recovery.activation.cleanupPending) slots=\(baseline)->\(slots)")
        return recovery
    }
}

// Hand-authored core Wasm in the signed runtime fixture style. The v77 C
// control uses the same UI-v1 frame shape. This signed module uses its own
// layout and passes through the Swift admission and presentation path.
private enum SignedBranchGuest {
    static func build(defaultLabel: String = "Else") -> Data {
        let headerOffset = 7
        let eventOffset = 8192
        let pointersOffset = 65_527
        let resultOffsets = [0x0823, 0x0c45, 0x1067]
        let eventPrefix = #"{"actionID":"pick."#
        let event = #"{"actionID":"pick.0","event":"activate","nodeID":"pick0","revision":1,"schemaVersion":1,"sequence":1,"value":null}"#
        let buttons = ["0", "1", "9"].map { digit in
            #"{"id":"pick\#(digit)","kind":"button","properties":{"label":"\#(digit)"},"children":[],"actions":[{"id":"pick.\#(digit)","event":"activate"}]}"#
        }.joined(separator: ",")
        let initialFrame = Array(#"{"schemaVersion":1,"revision":1,"root":{"id":"root","kind":"vStack","properties":{},"children":[\#(buttons)],"actions":[]}}"#.utf8)
        let results = ["Zero", "One!", defaultLabel].map { label in
            Array(#"{"schemaVersion":1,"revision":2,"root":{"id":"status","kind":"text","properties":{"text":"\#(label)"},"children":[],"actions":[]}}"#.utf8)
        }

        let header = [0x3155494d, 32, 512, initialFrame.count, eventOffset, 4096, 0, 0].flatMap { word in
            [0, 8, 16, 24].map { UInt8(truncatingIfNeeded: word >> $0) }
        }
        // Entry 0 reads an odd address. The default load reaches the last byte of the page.
        let pointers: [UInt8] = [0x23, 0x08, 0xa5, 0x45, 0x0c, 0xa5, 0xa5, 0x67, 0x10]

        var handleEvent: [UInt8] = [0x20, 0] // local.get byteLength
        handleEvent += constant(event.utf8.count)
        handleEvent += [0x47, 0x04, 0x40, 0x00, 0x0b] // trap on unexpected packet length
        handleEvent += constant(headerOffset + 8)
        handleEvent += [0x02, 0x7f, 0x02, 0x40, 0x02, 0x40, 0x02, 0x40] // result + three selector blocks
        handleEvent += constant(eventOffset + eventPrefix.utf8.count)
        handleEvent += [0x2d, 0, 0] // i32.load8_u
        handleEvent += constant(48) // ASCII 0
        handleEvent += [0x6b, 0x0e, 2, 0, 1, 2, 0x0b] // i32.sub; br_table 0 1 default 2; end
        handleEvent += constant(pointersOffset - 1)
        handleEvent += [0x0c, 2, 0x0b] // entry 0 exits with its pointer base
        handleEvent += constant(pointersOffset + 2)
        handleEvent += [0x0c, 1, 0x0b] // entry 1 exits with its pointer base
        handleEvent += constant(pointersOffset + 6)
        handleEvent += [0x0b, 0x2f, 0, 1, 0x36, 0, 0] // end result; load16_u offset=1; store
        handleEvent += constant(headerOffset + 12)
        handleEvent += constant(results[0].count)
        handleEvent += [0x36, 0, 0, 0x41, 0, 0x0b] // store length; return 0

        var module: [UInt8] = [0, 97, 115, 109, 1, 0, 0, 0]
        module += section(1, [3, 0x60, 0, 1, 0x7f, 0x60, 1, 0x7f, 1, 0x7f, 0x60, 0, 0])
        module += section(3, [3, 0, 1, 2])
        module += section(5, [1, 1, 1, 1]) // one fixed page
        var exports: [UInt8] = [3]
        for (index, name) in ["mixer_guest_ui_start_v1", "mixer_guest_ui_event_v1", "mixer_guest_capability_ready_v1"].enumerated() {
            exports += sized(Array(name.utf8)) + [0, UInt8(index)]
        }
        module += section(7, exports)
        var code: [UInt8] = [3]
        for body in [constant(headerOffset) + [0x0b], handleEvent, [0x0b]] {
            code += sized([0] + body) // no locals
        }
        module += section(10, code)
        var data: [UInt8] = [6]
        let segments = [(headerOffset, header), (512, initialFrame)] + Array(zip(resultOffsets, results)) + [(pointersOffset, pointers)]
        for (offset, bytes) in segments {
            data += [0] + constant(offset) + [0x0b] + sized(bytes)
        }
        return Data(module + section(11, data))
    }

    private static func section(_ id: UInt8, _ bytes: [UInt8]) -> [UInt8] {
        [id] + sized(bytes)
    }

    private static func sized(_ bytes: [UInt8]) -> [UInt8] {
        var remaining = bytes.count
        var prefix: [UInt8] = []
        repeat {
            let low = UInt8(remaining & 0x7f)
            remaining >>= 7
            prefix.append(low | (remaining == 0 ? 0 : 0x80))
        } while remaining != 0
        return prefix + bytes
    }

    private static func constant(_ value: Int) -> [UInt8] {
        var remaining = value
        var bytes: [UInt8] = [0x41]
        while remaining >= 64 {
            bytes.append(UInt8(remaining & 0x7f) | 0x80)
            remaining >>= 7
        }
        bytes.append(UInt8(remaining))
        return bytes
    }
}
#endif
