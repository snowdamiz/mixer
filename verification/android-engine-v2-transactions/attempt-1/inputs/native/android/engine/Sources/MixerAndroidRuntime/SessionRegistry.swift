import Foundation

/// Engines must preserve value semantics: exchange commits the candidate only
/// after serialization fits the caller's output buffer; the private V2 path
/// retains it until explicit native-attachment commit. Retained mutable references
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
    private var nextCandidate: UInt64 = 1
    private struct Pending {
        let token: UInt64
        let baseEpoch: UInt64
        let engine: Engine
    }
    private struct Session {
        var engine: Engine
        var epoch: UInt64 = 0
        var pending: Pending?
        var lastAborted: UInt64?
    }
    private var sessions: [UInt64: Session] = [:]
    private let factory: @Sendable () throws -> Engine
    public init(factory: @escaping @Sendable () throws -> Engine) { self.factory = factory }

    public func create() -> UInt64 {
        lock.lock(); defer { lock.unlock() }
        guard sessions.count < 16, next < UInt64.max, let engine = try? factory() else { return 0 }
        let handle = next; next += 1; sessions[handle] = Session(engine: engine)
        return handle
    }
    public func destroy(_ handle: UInt64) -> Int32 {
        lock.lock(); defer { lock.unlock() }
        return sessions.removeValue(forKey: handle) == nil ? 2 : 0
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
        guard var session = sessions[handle] else { return 2 }
        guard session.pending == nil else { return 5 }
        guard session.epoch < UInt64.max else { return 7 }
        var engine = session.engine
        do {
            let bytes = operation == 0 ? try engine.render() : try engine.dispatch(
                inputLength == 0 ? Data() : Data(bytes: input!, count: inputLength))
            guard bytes.count <= 1_048_576 else { return 4 }
            written.pointee = bytes.count
            guard bytes.count <= capacity else { return 3 }
            if !bytes.isEmpty { bytes.copyBytes(to: output!, count: bytes.count) }
            session.engine = engine
            session.epoch += 1
            sessions[handle] = session
            return 0
        } catch { return 4 }
    }

    /// Internal ordinary-native V2 staging. This is not signed presentation
    /// authority. Existing C/JNI entry points do not call this path yet.
    ///
    /// Status 0 returns a nonzero owner-bound token and a packet. Status 3
    /// reports required output bytes without retaining a candidate. Other
    /// failures zero written/token. Additional statuses: 5 pending candidate,
    /// 6 invalid/stale candidate, 7 monotonically assigned counter exhausted.
    /// One candidate is retained per session; its packet buffer is not retained.
    @_spi(MixerNativeAppearanceV2)
    public func prepareV2(
        _ handle: UInt64, _ operation: UInt32,
        _ input: UnsafePointer<UInt8>?, _ inputLength: Int,
        _ output: UnsafeMutablePointer<UInt8>?, _ capacity: Int,
        _ written: UnsafeMutablePointer<Int>?, _ token: UnsafeMutablePointer<UInt64>?
    ) -> Int32 {
        if let written { written.pointee = 0 }
        if let token { token.pointee = 0 }
        guard let written, let token,
              inputLength >= 0, inputLength <= 131_072,
              capacity >= 0, capacity <= 1_048_576,
              inputLength == 0 || input != nil, capacity == 0 || output != nil,
              operation <= 1, operation != 0 || inputLength == 0 else { return 1 }
        lock.lock(); defer { lock.unlock() }
        guard var session = sessions[handle] else { return 2 }
        guard session.pending == nil else { return 5 }
        guard nextCandidate < UInt64.max, session.epoch < UInt64.max else { return 7 }
        var candidate = session.engine
        do {
            let bytes = operation == 0 ? try candidate.render() : try candidate.dispatch(
                inputLength == 0 ? Data() : Data(bytes: input!, count: inputLength))
            guard bytes.count <= 1_048_576 else { return 4 }
            written.pointee = bytes.count
            guard bytes.count <= capacity else { return 3 }
            if !bytes.isEmpty { bytes.copyBytes(to: output!, count: bytes.count) }
            let issued = nextCandidate
            nextCandidate += 1
            session.pending = Pending(token: issued, baseEpoch: session.epoch, engine: candidate)
            sessions[handle] = session
            token.pointee = issued
            return 0
        } catch { return 4 }
    }

    /// Commit only after the matching native candidate is attached with event
    /// delivery gated. Does not render, dispatch, or allocate an output packet.
    /// Repeated/foreign commits fail; an unknown JNI outcome must retire the
    /// native coordinator rather than guessing which screen is authoritative.
    @_spi(MixerNativeAppearanceV2)
    public func commitV2(_ handle: UInt64, _ token: UInt64) -> Int32 {
        lock.lock(); defer { lock.unlock() }
        guard var session = sessions[handle] else { return 2 }
        guard token != 0, let pending = session.pending, pending.token == token,
              pending.baseEpoch == session.epoch else { return 6 }
        guard session.epoch < UInt64.max else { return 7 }
        session.engine = pending.engine
        session.epoch += 1
        session.pending = nil
        sessions[handle] = session
        return 0
    }

    /// Abort discards the candidate, leaving the committed engine unchanged.
    /// Retrying the most recently aborted token is harmless, even while a newer
    /// candidate is pending. It cannot discard that newer candidate. Older
    /// aborted tokens need not remain recognized after a subsequent abort.
    @_spi(MixerNativeAppearanceV2)
    public func abortV2(_ handle: UInt64, _ token: UInt64) -> Int32 {
        lock.lock(); defer { lock.unlock() }
        guard var session = sessions[handle] else { return 2 }
        guard token != 0 else { return 6 }
        if session.lastAborted == token { return 0 }
        guard let pending = session.pending, pending.token == token,
              pending.baseEpoch == session.epoch else { return 6 }
        session.pending = nil
        session.lastAborted = token
        sessions[handle] = session
        return 0
    }
}
