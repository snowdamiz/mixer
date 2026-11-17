#if canImport(Darwin)
import Foundation
import CMixerVM
@_spi(FeatureUIV3) import MixerGuest

/// Explicit opt-in static-library backend. Initialization acquires no runtime.
@_spi(FeatureUIV3) @MainActor public final class NativeSwiftFeatureBackend: SwiftFeatureRuntimeFactory {
    private let library = LinkedLibraryAuthority()
    public init() {}
    public func acquire(_ request: SwiftFeatureRuntimeRequest) -> SwiftFeatureAcquisition {
        guard request.profile == .development256, !request.packet.isEmpty else { return .refused(SwiftFeatureError.grant) }
        let handle = request.packet.withUnsafeBytes {
            mixer_swift_ui_open_profile_v1($0.bindMemory(to: UInt8.self).baseAddress!, $0.count, request.profile.rawValue)
        }
        guard let handle else { return .refused(SwiftFeatureError.vm("open refused before acquisition")) }
        return .ready(NativeOwner(handle, library: library))
    }
}
@MainActor private final class LinkedLibraryAuthority: SwiftFeatureCleanupAuthority {}
@MainActor private final class RetainedNativeAuthority: SwiftFeatureCleanupAuthority {
    private let handle: UnsafeMutableRawPointer
    private let library: LinkedLibraryAuthority
    init(_ handle: UnsafeMutableRawPointer, library: LinkedLibraryAuthority) { self.handle = handle; self.library = library }
}
@MainActor private final class NativeOwner: SwiftFeatureRuntimeOwner {
    private var handle: UnsafeMutableRawPointer?
    private let library: LinkedLibraryAuthority
    private var consumed = false
    init(_ handle: UnsafeMutableRawPointer, library: LinkedLibraryAuthority) { self.handle = handle; self.library = library }
    func frame() throws -> Data {
        guard let handle, !consumed else { throw SwiftFeatureError.closed }
        let length = mixer_swift_ui_frame_v1(handle, nil, 0)
        guard length > 0, length <= GuestUIProtocolV3.maximumBytes else { throw SwiftFeatureError.vm(diagnostic(handle)) }
        var data = Data(count: length)
        let copied = data.withUnsafeMutableBytes { mixer_swift_ui_frame_v1(handle, $0.bindMemory(to: UInt8.self).baseAddress!, $0.count) }
        guard copied == length else { throw SwiftFeatureError.vm(diagnostic(handle)) }
        return data
    }
    func event(_ bytes: Data) throws {
        guard let handle, !consumed, !bytes.isEmpty else { throw SwiftFeatureError.closed }
        let status = bytes.withUnsafeBytes { mixer_swift_ui_event_v1(handle, $0.bindMemory(to: UInt8.self).baseAddress!, $0.count) }
        guard status == 0 else { throw SwiftFeatureError.vm(diagnostic(handle)) }
    }
    private func diagnostic(_ handle: UnsafeMutableRawPointer) -> String {
        var bytes = [UInt8](repeating: 0, count: 8192)
        let count = bytes.withUnsafeMutableBufferPointer { mixer_swift_ui_error_v1(handle, $0.baseAddress!, $0.count) }
        guard count >= 0, count <= bytes.count else { return "invalid native diagnostic length" }
        return String(decoding: bytes.prefix(count), as: UTF8.self)
    }
    func consume() -> SwiftFeatureConsumption {
        guard let handle, !consumed else { return .retained(library, cause: SwiftFeatureError.closed) }
        consumed = true
        var ledger = [UInt64](repeating: .max, count: 16)
        let status = ledger.withUnsafeMutableBufferPointer { mixer_swift_ui_consume_v1(handle, $0.baseAddress!) }
        self.handle = nil
        if status == 1 {
            return .reportedClosed(SwiftFeatureLedgerObservation(currents: Array(ledger.prefix(14)), tickets: ledger[14], invariant: ledger[15]))
        }
        return .retained(RetainedNativeAuthority(handle, library: library), cause: SwiftFeatureError.vm("consume unresolved status \(status)"))
    }
}
#else
#error("MixerNativeBackend requires an explicitly qualified Darwin host and admitted archive")
#endif
