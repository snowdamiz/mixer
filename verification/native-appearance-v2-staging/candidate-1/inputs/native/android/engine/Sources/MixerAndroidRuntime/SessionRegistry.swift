import Foundation

/// Engines must preserve value semantics: exchange commits the candidate only
/// after serialization fits the caller's output buffer. Retained mutable references
/// in an engine's state would violate that application contract.
/// Factory/render/dispatch execute synchronously under the registry's lock. They
/// must not re-enter this registry, start asynchronous work or perform side effects.
/// Sendable by itself does not establish value semantics or transactional effects.
public protocol AndroidApplicationEngine: Sendable {
    func render() throws -> Data
    mutating func dispatch(_ input: Data) throws -> Data
}

/// Shared bounded C/JNI boundary. App entry points provide the engine factory;
/// the adapter never substitutes its checklist example for application features.
public final class AndroidSessionRegistry<Engine: AndroidApplicationEngine>: @unchecked Sendable {
    private let lock = NSLock()
    private var next: UInt64 = 1
    private var engines: [UInt64: Engine] = [:]
    private let factory: @Sendable () throws -> Engine
    public init(factory: @escaping @Sendable () throws -> Engine) { self.factory = factory }

    public func create() -> UInt64 {
        lock.lock(); defer { lock.unlock() }
        guard engines.count < 16, next < UInt64.max, let engine = try? factory() else { return 0 }
        let handle = next; next += 1; engines[handle] = engine
        return handle
    }
    public func destroy(_ handle: UInt64) -> Int32 {
        lock.lock(); defer { lock.unlock() }
        return engines.removeValue(forKey: handle) == nil ? 2 : 0
    }
    public func exchange(
        _ handle: UInt64, _ operation: UInt32,
        _ input: UnsafePointer<UInt8>?, _ inputLength: Int,
        _ output: UnsafeMutablePointer<UInt8>?, _ capacity: Int,
        _ written: UnsafeMutablePointer<Int>?
    ) -> Int32 {
        guard let written else { return 1 }
        written.pointee = 0
        guard inputLength >= 0, inputLength <= 131_072,
              capacity >= 0, capacity <= 1_048_576,
              inputLength == 0 || input != nil, capacity == 0 || output != nil,
              operation <= 1, operation != 0 || inputLength == 0 else { return 1 }
        lock.lock(); defer { lock.unlock() }
        guard var engine = engines[handle] else { return 2 }
        do {
            let bytes = operation == 0 ? try engine.render() : try engine.dispatch(
                inputLength == 0 ? Data() : Data(bytes: input!, count: inputLength))
            guard bytes.count <= 1_048_576 else { return 4 }
            written.pointee = bytes.count
            guard bytes.count <= capacity else { return 3 }
            if !bytes.isEmpty { bytes.copyBytes(to: output!, count: bytes.count) }
            engines[handle] = engine
            return 0
        } catch { return 4 }
    }
}
