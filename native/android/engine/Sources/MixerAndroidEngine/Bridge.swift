import MixerAndroidRuntime

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
