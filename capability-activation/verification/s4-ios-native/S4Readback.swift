// Compiled only in the isolated fixture package, like FieldLog's signed iOS observations.
#if os(iOS)
import Foundation
import MixerApple
import MixerUI
@_spi(GuestUIV1) import MixerGuest

public struct S4DisplayTicket: Equatable, CustomStringConvertible {
    public let generation: UInt64
    public let frameSerial: UInt64
    public let revision: UInt64

    init(_ proof: CapabilityGuestUIDisplayTicket) {
        generation = proof.ticket.generation
        frameSerial = proof.ticket.frameSerial
        revision = proof.ticket.revision
    }

    public var description: String { "\(generation)/\(frameSerial)/\(revision)" }
}

extension GuestUIPresentation {
    public var s4Document: UIDocument? { renderHost?.snapshot.document }
    public var s4AcceptedEvents: UInt64? { lifecycleObservation?.counters.acceptedEvents }
    public var s4DeliveredEvents: UInt64? { lifecycleObservation?.counters.deliveredEvents }
    public var s4PendingNativeReceipt: UInt64? { lifecycleObservation?.pendingPresentationReceipt?.revision }
    public var s4InputEnabled: Bool { inputEnabled }

    func s4RecordNativeCallback(_ action: RoutedUIAction, callback: @escaping @MainActor (RoutedUIAction) -> Void) {
        s4NativeCallbackCount += 1
        s4LastNativeCallback = { callback(action) }
        callback(action)
    }

    public var s4EffectsConfirmed: Bool? { lifecycleObservation?.effectsConfirmed }

    func s4Installed(_ callback: @escaping @MainActor (RoutedUIAction) -> Void, inputEnabled: Bool)
        -> @MainActor (RoutedUIAction) -> Void {
        s4LastInstalledCallback = callback
        s4LastInstalledWithInputEnabled = inputEnabled
        return callback
    }

    /// Pairs the last renderer-installed handler with a real routed action for
    /// a node of the current document. Invoking it later grants no authority.
    public func s4CaptureInstalledCallback(nodeID: String, requiringEnabledInput: Bool = false) -> (@MainActor () -> Void)? {
        guard !requiringEnabledInput || (inputEnabled && s4LastInstalledWithInputEnabled),
              let callback = s4LastInstalledCallback, let host = renderHost,
              let identity = host.snapshot.identity(for: nodeID),
              let action = try? host.route(UIEventEnvelope(revision: host.snapshot.document.revision,
                                                           identity: identity, event: .activate)) else { return nil }
        return { callback(action) }
    }

    public func s4ReplayLastNativeCallback() -> Bool {
        guard let callback = s4LastNativeCallback else { return false }
        s4LastNativeCallback = nil
        callback()
        return true
    }

    public var s4PresentationReadback: String {
        let ui = lifecycleObservation
        return [
            "presentation=\(state)", "documentRevision=\(s4Value(s4Document?.revision))",
            "inputEnabled=\(inputEnabled)", "probeAppeared=\(s4Value(s4NativeProbeAppeared))",
            "probeHasAppeared=\(s4Value(s4NativeProbeHasAppeared))",
            "observedNativeDisplay=\(s4ObservedNativeDisplay)",
            "heldTicket=\(s4Value(s4HeldDisplayTicket))",
            "acknowledgedTicket=\(s4Value(s4AcknowledgedDisplayTicket))",
            "receiptRevision=\(s4Value(ui?.pendingPresentationReceipt?.revision))",
            "receiptSerial=\(s4Value(ui?.pendingPresentationReceipt?.frameSerial))",
            "effectsConfirmed=\(s4Value(ui?.effectsConfirmed))",
            "nativeCallbacks=\(s4NativeCallbackCount)",
            "acceptedEvents=\(s4Value(ui?.counters.acceptedEvents))",
            "deliveredEvents=\(s4Value(ui?.counters.deliveredEvents))"
        ].joined(separator: " ")
    }

    public func s4SelectSharedTheme(_ theme: S4NativeTheme) -> Bool {
        guard let renderHost else { return false }
        renderHost.s4SharedTheme = theme
        return true
    }

    public func s4SaveEnvelope() -> UIEventEnvelope? {
        guard let snapshot = renderHost?.snapshot, let identity = snapshot.identity(for: "save") else { return nil }
        return UIEventEnvelope(revision: snapshot.document.revision, identity: identity, event: .activate)
    }

    public func s4RejectsStaleEnvelope(_ envelope: UIEventEnvelope) -> Bool {
        guard let host = renderHost else { return false }
        do { _ = try host.route(envelope); return false }
        catch UIRoutingError.staleRevision { return true }
        catch { return false }
    }
}

extension CapabilityGuestUIRuntime {
    public var s4Retired: Bool { ownerRetired }
}

public func s4Value<T>(_ value: T?) -> String {
    value.map { String(describing: $0) } ?? "nil"
}
#endif
