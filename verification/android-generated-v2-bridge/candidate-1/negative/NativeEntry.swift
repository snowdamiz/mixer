import AppFeatures
@_spi(MixerNativeAppearanceV2) import MixerAndroidRuntime
// App-owned native entry point; state, document and reducer live in shared Swift.
// State must remain a value type; callbacks are synchronous, non-reentrant and
// free of I/O/async/shared mutable references. Sendable alone is insufficient.
private let sessions = AndroidSessionRegistry {
    try AndroidDocumentSession(state: ProjectFeatureState(),
        document: { ProjectFeature.document(state: $0, revision: $1) },
        reduce: { try ProjectFeature.handle($1, state: &$0) })
}
@_cdecl("mixer_android_create")
public func mixerAndroidCreate() -> UInt64 { sessions.create() }
@_cdecl("mixer_android_destroy")
public func mixerAndroidDestroy(_ handle: UInt64) -> Int32 { sessions.destroy(handle) }
@_cdecl("mixer_android_exchange")
public func mixerAndroidExchange(_ handle: UInt64, _ operation: UInt32,
    _ input: UnsafePointer<UInt8>?, _ inputLength: Int,
    _ output: UnsafeMutablePointer<UInt8>?, _ capacity: Int, _ written: UnsafeMutablePointer<Int>?
) -> Int32 { sessions.exchange(handle, operation, input, inputLength, output, capacity, written) }
// Private ordinary-native staging. This does not opt the Activity into V2.
@_spi(MixerNativeAppearanceV2)
@_cdecl("mixer_android_prepare_v2")
public func mixerAndroidPrepareV2(_ handle: UInt64, _ operation: UInt32,
    _ input: UnsafePointer<UInt8>?, _ inputLength: Int,
    _ output: UnsafeMutablePointer<UInt8>?, _ capacity: Int,
    _ written: UnsafeMutablePointer<Int>?, _ token: UnsafeMutablePointer<UInt64>?
) -> Int32 { sessions.prepareV2(handle, operation, input, inputLength, output, capacity, written, token) }
@_spi(MixerNativeAppearanceV2)
// deliberate missing C export
public func mixerAndroidCommitV2(_ handle: UInt64, _ token: UInt64) -> Int32 { sessions.commitV2(handle, token) }
@_spi(MixerNativeAppearanceV2)
@_cdecl("mixer_android_abort_v2")
public func mixerAndroidAbortV2(_ handle: UInt64, _ token: UInt64) -> Int32 { sessions.abortV2(handle, token) }
