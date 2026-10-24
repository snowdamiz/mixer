@_spi(MixerNativeAppearanceV2) import MixerAndroidRuntime

extension ChecklistEngine: AndroidApplicationEngine {}
private let registry = AndroidSessionRegistry { try ChecklistEngine() }

@_cdecl("mixer_android_create")
public func mixerAndroidCreate() -> UInt64 { registry.create() }

@_cdecl("mixer_android_destroy")
public func mixerAndroidDestroy(_ handle: UInt64) -> Int32 { registry.destroy(handle) }

/// Caller owns output memory. A failed operation never commits Swift state.
@_cdecl("mixer_android_exchange")
public func mixerAndroidExchange(
    _ handle: UInt64, _ operation: UInt32,
    _ input: UnsafePointer<UInt8>?, _ inputLength: Int,
    _ output: UnsafeMutablePointer<UInt8>?, _ capacity: Int, _ written: UnsafeMutablePointer<Int>?
) -> Int32 { registry.exchange(handle, operation, input, inputLength, output, capacity, written) }

/// Internal ordinary-native staging ABI. The caller decides only after native
/// preparation/attachment; neither this export nor the token grants signed authority.
@_spi(MixerNativeAppearanceV2)
@_cdecl("mixer_android_prepare_v2")
public func mixerAndroidPrepareV2(
    _ handle: UInt64, _ operation: UInt32,
    _ input: UnsafePointer<UInt8>?, _ inputLength: Int,
    _ output: UnsafeMutablePointer<UInt8>?, _ capacity: Int,
    _ written: UnsafeMutablePointer<Int>?, _ token: UnsafeMutablePointer<UInt64>?
) -> Int32 {
    registry.prepareV2(handle, operation, input, inputLength, output, capacity, written, token)
}

@_spi(MixerNativeAppearanceV2)
@_cdecl("mixer_android_commit_v2")
public func mixerAndroidCommitV2(_ handle: UInt64, _ token: UInt64) -> Int32 {
    registry.commitV2(handle, token)
}

@_spi(MixerNativeAppearanceV2)
@_cdecl("mixer_android_abort_v2")
public func mixerAndroidAbortV2(_ handle: UInt64, _ token: UInt64) -> Int32 {
    registry.abortV2(handle, token)
}
