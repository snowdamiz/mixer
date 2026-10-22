import Foundation

private final class EngineRegistry: @unchecked Sendable {
  static let shared = EngineRegistry()
  let lock = NSLock()
  var next: UInt64 = 1
  var engines: [UInt64: ChecklistEngine] = [:]
}
@_cdecl("mixer_android_create")
public func mixerAndroidCreate() -> UInt64 {
  let registry = EngineRegistry.shared
  registry.lock.lock()
  defer { registry.lock.unlock() }
  guard registry.engines.count < 16, registry.next < UInt64.max, let engine = try? ChecklistEngine()
  else { return 0 }
  let handle = registry.next
  registry.next += 1
  registry.engines[handle] = engine
  return handle
}
@_cdecl("mixer_android_destroy")
public func mixerAndroidDestroy(_ handle: UInt64) -> Int32 {
  let registry = EngineRegistry.shared
  registry.lock.lock()
  defer { registry.lock.unlock() }
  return registry.engines.removeValue(forKey: handle) == nil ? 2 : 0
}
/// Caller owns output memory. A failed operation never commits Swift state.
@_cdecl("mixer_android_exchange")
public func mixerAndroidExchange(
  _ handle: UInt64, _ operation: UInt32,
  _ input: UnsafePointer<UInt8>?, _ inputLength: Int,
  _ output: UnsafeMutablePointer<UInt8>?, _ capacity: Int, _ written: UnsafeMutablePointer<Int>?
) -> Int32 {
  guard let written else { return 1 }
  written.pointee = 0
  guard inputLength >= 0, inputLength <= 131_072, capacity >= 0, capacity <= 1_048_576,
    inputLength == 0 || input != nil, capacity == 0 || output != nil, operation <= 1,
    operation != 0 || inputLength == 0
  else { return 1 }
  let registry = EngineRegistry.shared
  registry.lock.lock()
  defer { registry.lock.unlock() }
  guard var engine = registry.engines[handle] else { return 2 }
  do {
    let data: Data
    if operation == 0 {
      data = try engine.render()
    } else {
      data = try engine.dispatch(
        inputLength == 0 ? Data() : Data(bytes: input!, count: inputLength))
    }
    written.pointee = data.count
    guard data.count <= capacity else { return 3 }
    data.copyBytes(to: output!, count: data.count)
    registry.engines[handle] = engine
    return 0
  } catch { return 4 }
}
