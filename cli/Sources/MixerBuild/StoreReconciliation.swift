import Darwin
import Foundation
import MixerCore

public struct StoreStatusRequest: Sendable {
    let buildID: String
    let appID: String
    public static func parse(words: [String], options: [String: String]) throws -> Self {
        guard words == ["submit", "status"] else {
            throw MixerFailure("workflow.not-qualified", "submit requires native/guest/store integration that is still in progress. No build, release or submission has been performed. See mixer gates.")
        }
        guard Set(options.keys).isSubset(of: ["--provider", "--build-id", "--app-id", "--directory"]),
              options["--provider"] == "app-store-connect", let buildID = options["--build-id"], let appID = options["--app-id"],
              validID(buildID), validID(appID) else {
            throw MixerFailure("arguments.submit-status", "Usage: mixer submit status --provider app-store-connect --build-id BUILD_ID --app-id ASC_APP_ID [--directory PROJECT]")
        }
        return Self(buildID: buildID, appID: appID)
    }
    // Deliberately narrower than an arbitrary opaque string, so identity cannot alter URL paths.
    private static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 200 && value.utf8.allSatisfy { (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || $0 == 45 || $0 == 95 }
    }
}

public struct StoreBuildObservation: Codable, Sendable {
    struct ProviderValue: Codable, Sendable { let version: String; let processingState: String }
    let generation: UInt64
    public let observedAt: Date
    let providerValue: ProviderValue
    public var version: String { providerValue.version }
    public var processingState: String { providerValue.processingState }
    public var outcome: String {
        switch processingState {
        case "PROCESSING": "processing-pending"
        case "FAILED", "INVALID": "processing-failed"
        case "VALID": "processing-succeeded"
        default: "unresolved"
        }
    }
}

public struct StoreReconciliationReport: Encodable, Sendable {
    public let provider = "app-store-connect"
    public let qualification = "local-observation-only"
    public let buildID: String
    public let appID: String
    public let bundleID: String
    public let query: String
    public let code: StoreQueryFailure?
    public let observation: StoreBuildObservation?
    public let observationUpdated: Bool
    public let testFlightReadiness = "unverified"
    public let reviewApproval = "unverified"
    public let availability = "unverified"
    public var status: String { query == "observed" ? observation?.outcome ?? "unresolved" : "unresolved" }
    public var exitCode: Int32 { status == "processing-succeeded" ? 0 : status == "processing-pending" ? 2 : 1 }
    public var nextStep: String {
        if code == .credentialRequired || code == .authenticationRejected { return "Supply a valid short-lived MIXER_ASC_BEARER_TOKEN and query this existing build again." }
        if code == .accessForbidden { return "Check App Store Connect access and any account action in Apple's interface; this response does not identify an agreement or verification requirement." }
        if status == "processing-failed" { return "Inspect this build's processing diagnostics in App Store Connect; no upload was attempted." }
        return "Reconcile this existing build as needed. Testing, review, and release require separate evidence."
    }
    enum CodingKeys: String, CodingKey { case provider, qualification, buildID, appID, bundleID, query, code, observation, observationUpdated, testFlightReadiness, reviewApproval, availability, status, nextStep }
    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(provider, forKey: .provider); try c.encode(qualification, forKey: .qualification)
        try c.encode(buildID, forKey: .buildID); try c.encode(appID, forKey: .appID); try c.encode(bundleID, forKey: .bundleID)
        try c.encode(query, forKey: .query); try c.encodeIfPresent(code, forKey: .code); try c.encodeIfPresent(observation, forKey: .observation)
        try c.encode(observationUpdated, forKey: .observationUpdated); try c.encode(testFlightReadiness, forKey: .testFlightReadiness)
        try c.encode(reviewApproval, forKey: .reviewApproval); try c.encode(availability, forKey: .availability)
        try c.encode(status, forKey: .status); try c.encode(nextStep, forKey: .nextStep)
    }
}

public enum StoreReconciliation {
    public static func status(request: StoreStatusRequest, directory: URL, environment: [String: String] = ProcessInfo.processInfo.environment, reader: AppStoreConnectBuildStatus = .init()) throws -> StoreReconciliationReport {
        let config: ApplicationConfiguration
        do { config = try ApplicationConfiguration.load(directory) }
        catch { throw MixerFailure("store.project", "Cannot load a valid project application identity from mixer.yml.") }
        let identity = StoreObservationFile.Identity(buildID: request.buildID, appID: request.appID, bundleID: config.application)
        let token = environment["MIXER_ASC_BEARER_TOKEN"] ?? ""
        guard token.isEmpty || ![identity.buildID, identity.appID, identity.bundleID].contains(where: { $0.contains(token) }) else {
            throw MixerFailure("store.credential-reflection", "The credential overlaps an application identity; refusing to persist or emit it.")
        }
        guard identity.bundleID.utf8.count <= 256 else { throw MixerFailure("store.project", "Project application identity exceeds the status reader limit.") }
        let file = try StoreObservationFile(root: directory, identity: identity, token: token)
        defer { file.close() }
        let generation = try file.reserve()
        let observation: StoreBuildObservation?
        let query: String
        let failure: StoreQueryFailure?
        let updated: Bool
        do {
            let value = try reader.read(buildID: request.buildID, appID: request.appID, bundleID: config.application, token: token)
            let result = try file.commit(.init(generation: generation, observedAt: Date(), providerValue: value))
            observation = result.0; updated = result.1; query = updated ? "observed" : "superseded"; failure = nil
        } catch let error as StoreQueryFailure {
            observation = try file.observation(); updated = false; query = "unresolved"; failure = error
        }
        return .init(buildID: identity.buildID, appID: identity.appID, bundleID: identity.bundleID, query: query, code: failure, observation: observation, observationUpdated: updated)
    }
}

// One descriptor-anchored directory, bounded nonblocking flock, atomic rename and fsync.
// Generation reservation happens before HTTP, so completion order cannot regress observations.
final class StoreObservationFile {
    struct Identity: Codable, Equatable { let buildID: String; let appID: String; let bundleID: String }
    private struct CredentialFingerprint: Codable, Equatable {
        let bytes: Int
        let sha256: String
    }
    private struct Record: Codable {
        var schema: Int
        let identity: Identity
        var issued: UInt64
        var observation: StoreBuildObservation?
        var discardedThrough: UInt64?
        var redactions: [CredentialFingerprint]?
        var redactionsExhausted: Bool?
    }
    private let directory: Int32
    private let lock: Int32
    private let name: String
    private let identity: Identity
    private let token: String
    init(root: URL, identity: Identity, token: String) throws {
        self.identity = identity
        self.token = token
        name = SourceDigest.sha256(Data((identity.bundleID + "\u{0}" + identity.appID + "\u{0}" + identity.buildID).utf8)) + ".json"
        var descriptor = Darwin.open(root.path, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW)
        guard descriptor >= 0 else { throw Self.failure() }
        do {
            for component in [".mixer", "store"] {
                if mkdirat(descriptor, component, 0o700) != 0 && errno != EEXIST { throw Self.failure() }
                let next = openat(descriptor, component, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
                guard next >= 0 else { throw Self.failure() }
                guard fsync(descriptor) == 0 else { let e = errno; Darwin.close(next); throw MixerFailure("store.local-record", "constructor-parent-fsync errno \(e)") }
                Darwin.close(descriptor); descriptor = next
            }
            let flags = O_RDWR | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC
            var opened = openat(descriptor, name + ".lock", flags | O_CREAT | O_EXCL, 0o600)
            if opened < 0 && errno == EEXIST { opened = openat(descriptor, name + ".lock", flags) }
            guard opened >= 0 else { throw Self.failure() }
            var info = stat()
            guard fstat(opened, &info) == 0, info.st_mode & S_IFMT == S_IFREG, info.st_nlink == 1 else { Darwin.close(opened); throw Self.failure() }
            directory = descriptor; lock = opened
        } catch { Darwin.close(descriptor); throw error }
    }
    func close() { Darwin.close(lock); Darwin.close(directory) }
    private static func failure(line: UInt = #line) -> MixerFailure { .init("store.local-record", "Cannot safely read or atomically retain the local store observation (step \(line), errno \(errno)); no provider mutation was attempted.") }
    private func locked<T>(_ body: () throws -> T) throws -> T {
        let deadline = DispatchTime.now().uptimeNanoseconds + 2_000_000_000
        while flock(lock, LOCK_EX | LOCK_NB) != 0 {
            guard errno == EWOULDBLOCK || errno == EAGAIN, DispatchTime.now().uptimeNanoseconds < deadline else { throw Self.failure() }
            usleep(10_000)
        }
        defer { flock(lock, LOCK_UN) }
        return try body()
    }
    private func read() throws -> Record {
        let fd = openat(directory, name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
        guard fd >= 0 else {
            if errno == ENOENT { return .init(schema: 1, identity: identity, issued: 0, observation: nil) }
            throw Self.failure()
        }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? handle.close() }
        var info = stat()
        guard fstat(fd, &info) == 0, info.st_mode & S_IFMT == S_IFREG, info.st_nlink == 1, info.st_size <= 16_384 else { throw Self.failure() }
        do {
            let data = try handle.read(upToCount: 16_385) ?? Data()
            try JSONInputGuard.validate(data, limits: JSONInputLimits(maximumBytes: 16_384, maximumDepth: 8, maximumValues: 100))
            let record = try JSONDecoder().decode(Record.self, from: data)
            guard (record.schema == 1 || record.schema == 2), record.identity == identity,
                  record.observation.map({ !$0.version.isEmpty && $0.version.utf8.count <= 256 && !$0.processingState.isEmpty && $0.processingState.utf8.count <= 128 }) ?? true,
                  record.schema == 1 || (record.redactions == nil && record.redactionsExhausted == nil),
                  record.observation.map({ $0.generation > 0 && $0.generation <= record.issued }) ?? true,
                  record.discardedThrough.map({ $0 > 0 && $0 <= record.issued }) ?? true,
                  (record.redactions?.count ?? 0) <= 16,
                  record.redactions?.allSatisfy({ $0.bytes > 0 && $0.bytes <= 256 && $0.sha256.utf8.count == 64 && $0.sha256.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) } }) ?? true else { throw Self.failure() }
            return record
        } catch let error as MixerFailure { throw error }
        catch { throw Self.failure() }
    }
    private func write(_ record: Record) throws {
        let temporary = ".observation-" + UUID().uuidString
        let fd = openat(directory, temporary, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard fd >= 0 else { throw Self.failure() }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
        defer { try? handle.close(); unlinkat(directory, temporary, 0) }
        do {
            let data = try JSONFile.data(record)
            try JSONInputGuard.validate(data, limits: JSONInputLimits(maximumBytes: 16_384, maximumDepth: 8, maximumValues: 100))
            try handle.write(contentsOf: data)
            guard fsync(fd) == 0, renameat(directory, temporary, directory, name) == 0, fsync(directory) == 0 else { throw Self.failure() }
        } catch let error as MixerFailure { throw error }
        catch { throw Self.failure() }
    }
    private static func indexFailure() -> MixerFailure {
        .init("store.credential-index", "Credential recognition storage is unavailable, corrupt, or unwritable. Restore its integrity and retry; no provider mutation was attempted.")
    }

    // Fixed 256 length roots and compressed SHA-256 paths bound reads and memory.
    // Immutable child hashes distinguish non-membership from lost referenced nodes.
    // All calls occur under the observation identity's flock.
    private final class CredentialIndex {
        private let directory: Int32
        private var roots = [String](repeating: "", count: 256)
        private var cache: [String: Node] = [:]
        private struct Node {
            let key: String
            let bit: Int
            let left: String
            let right: String
            var data: Data {
                Data((bit == 256 ? "L\n\(key)\n" : "B\n\(bit)\n\(key)\n\(left)\n\(right)\n").utf8)
            }
        }
        private static func hash(_ value: String) -> Bool {
            value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
        }
        private static func header(_ roots: [String]) -> Data {
            let body = Data(("mixer-credential-tree-v1\n" + roots.joined(separator: "\n") + "\n").utf8)
            return body + Data((SourceDigest.sha256(body) + "\n").utf8)
        }
        init(parent: Int32, name: String, create: Bool) throws {
            var created = false
            if create {
                if mkdirat(parent, name, 0o700) == 0 { created = true }
                else if errno != EEXIST { throw StoreObservationFile.indexFailure() }
            }
            let fd = openat(parent, name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard fd >= 0 else { throw StoreObservationFile.indexFailure() }
            directory = fd
            do {
                if created { try atomic(Self.header(roots), name: "roots") }
                guard let data = try read("roots", maximum: 17_000) else { throw StoreObservationFile.indexFailure() }
                let lines = String(decoding: data, as: UTF8.self).components(separatedBy: "\n")
                guard lines.count == 259 else { throw StoreObservationFile.indexFailure() }
                let decoded = Array(lines[1...256])
                guard decoded.allSatisfy({ $0.isEmpty || Self.hash($0) }), data == Self.header(decoded) else { throw StoreObservationFile.indexFailure() }
                roots = decoded
                if let pending = try read("pending", maximum: Self.maximumPendingBytes) { try finishRecognition(Self.decodePending(pending)) }
                guard fsync(directory) == 0, fsync(parent) == 0 else { throw StoreObservationFile.indexFailure() }
            } catch { Darwin.close(fd); throw error }
        }
        deinit { Darwin.close(directory) }
        private func read(_ name: String, maximum: Int, synchronize: Bool = false) throws -> Data? {
            let fd = openat(directory, name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
            guard fd >= 0 else {
                if errno == ENOENT { return nil }
                throw StoreObservationFile.indexFailure()
            }
            let file = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
            defer { try? file.close() }
            var info = stat()
            guard fstat(fd, &info) == 0, info.st_mode & S_IFMT == S_IFREG, info.st_nlink == 1,
                  info.st_size >= 0, info.st_size <= maximum else { throw StoreObservationFile.indexFailure() }
            do {
                let data = try file.read(upToCount: maximum + 1) ?? Data()
                guard data.count == info.st_size, data.count <= maximum,
                      !synchronize || fsync(fd) == 0 else { throw StoreObservationFile.indexFailure() }
                return data
            } catch { throw StoreObservationFile.indexFailure() }
        }
        private func atomic(_ data: Data, name: String) throws {
            let temporary = ".credential-" + UUID().uuidString
            let fd = openat(directory, temporary, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
            guard fd >= 0 else { throw StoreObservationFile.indexFailure() }
            let file = FileHandle(fileDescriptor: fd, closeOnDealloc: true)
            defer { try? file.close(); unlinkat(directory, temporary, 0) }
            do {
                try file.write(contentsOf: data)
                guard fsync(fd) == 0, renameat(directory, temporary, directory, name) == 0,
                      fsync(directory) == 0 else { throw StoreObservationFile.indexFailure() }
            } catch { throw StoreObservationFile.indexFailure() }
        }
        private static let pendingHeader = "mixer-credential-v2\n"
        // Header, 1...256 byte length, separator, fingerprint, checksum and newlines.
        private static let maximumPendingBytes = pendingHeader.utf8.count + 3 + 1 + 64 + 1 + 64 + 1
        private static func entry(_ fingerprint: CredentialFingerprint) -> Data {
            let body = Data((pendingHeader + "\(fingerprint.bytes)-\(fingerprint.sha256)\n").utf8)
            return body + Data((SourceDigest.sha256(body) + "\n").utf8)
        }
        private static func decodePending(_ data: Data) throws -> CredentialFingerprint {
            let lines = String(decoding: data, as: UTF8.self).components(separatedBy: "\n")
            // Unchecked v1 history cannot be certified by rewriting it as v2.
            guard lines.count == 4, lines[0] + "\n" == pendingHeader,
                  Self.hash(lines[2]), lines[3].isEmpty else { throw StoreObservationFile.indexFailure() }
            let parts = lines[1].split(separator: "-", maxSplits: 1)
            guard parts.count == 2, let bytes = Int(parts[0]), (1...256).contains(bytes), String(bytes) == parts[0], Self.hash(String(parts[1])) else { throw StoreObservationFile.indexFailure() }
            let fingerprint = CredentialFingerprint(bytes: bytes, sha256: String(parts[1]))
            guard data == Self.entry(fingerprint) else { throw StoreObservationFile.indexFailure() }
            return fingerprint
        }
        private func load(_ reference: String) throws -> Node {
            if let node = cache[reference] { return node }
            guard Self.hash(reference), let data = try read(reference + ".node", maximum: 256), SourceDigest.sha256(data) == reference else { throw StoreObservationFile.indexFailure() }
            let parts = String(decoding: data, as: UTF8.self).components(separatedBy: "\n")
            let node: Node
            if parts.count == 3, parts[0] == "L", Self.hash(parts[1]), parts[2].isEmpty {
                node = .init(key: parts[1], bit: 256, left: "", right: "")
            } else if parts.count == 6, parts[0] == "B", let bit = Int(parts[1]), (0..<256).contains(bit),
                      Self.hash(parts[2]), Self.hash(parts[3]), Self.hash(parts[4]), parts[3] != parts[4], parts[5].isEmpty {
                node = .init(key: parts[2], bit: bit, left: parts[3], right: parts[4])
            } else { throw StoreObservationFile.indexFailure() }
            guard data == node.data else { throw StoreObservationFile.indexFailure() }
            // Cache eviction never changes durable recognition. Bound memory independently of history.
            if cache.count >= 512 { cache.removeAll(keepingCapacity: true) }
            cache[reference] = node
            return node
        }
        private func save(_ node: Node) throws -> String {
            let data = node.data, reference = SourceDigest.sha256(node.data)
            if let existing = try read(reference + ".node", maximum: 256, synchronize: true) {
                guard existing == data else { throw StoreObservationFile.indexFailure() }
            } else { try atomic(data, name: reference + ".node") }
            return reference
        }
        private func nibble(_ byte: UInt8) -> UInt8 { byte <= 57 ? byte - 48 : byte - 87 }
        private func bit(_ key: String, _ position: Int) -> Int {
            let byte = key.utf8[key.utf8.index(key.utf8.startIndex, offsetBy: position / 4)]
            return Int((nibble(byte) >> (3 - position % 4)) & 1)
        }
        private func common(_ a: String, _ b: String) -> Int {
            for (i, pair) in zip(a.utf8, b.utf8).enumerated() {
                let difference = nibble(pair.0) ^ nibble(pair.1)
                if difference != 0 {
                    for j in 0..<4 where difference & (8 >> j) != 0 { return i * 4 + j }
                }
            }
            return 256
        }
        private func child(_ node: Node, direction: Int) throws -> (String, Node) {
            let reference = direction == 0 ? node.left : node.right
            let next = try load(reference)
            guard next.bit > node.bit, common(next.key, node.key) >= node.bit, bit(next.key, node.bit) == direction else { throw StoreObservationFile.indexFailure() }
            return (reference, next)
        }
        private func containsHash(_ hash: String, root: String) throws -> Bool {
            if root.isEmpty { return false }
            var node = try load(root)
            while true {
                if common(hash, node.key) < node.bit { return false }
                if node.bit == 256 { return true }
                node = try child(node, direction: bit(hash, node.bit)).1
            }
        }
        private func insert(_ hash: String, reference: String, node: Node) throws -> String {
            let shared = common(hash, node.key)
            if shared < node.bit {
                let leaf = try save(.init(key: hash, bit: 256, left: "", right: ""))
                let zero = bit(hash, shared) == 0
                return try save(.init(key: hash, bit: shared, left: zero ? leaf : reference, right: zero ? reference : leaf))
            }
            if node.bit == 256 { return reference }
            let direction = bit(hash, node.bit), next = try child(node, direction: bit(hash, node.bit))
            let changed = try insert(hash, reference: next.0, node: next.1)
            if changed == next.0 { return reference }
            return try save(.init(key: node.key, bit: node.bit, left: direction == 0 ? changed : node.left, right: direction == 1 ? changed : node.right))
        }
        private func finishRecognition(_ fingerprint: CredentialFingerprint) throws {
            let old = roots[fingerprint.bytes - 1]
            let updated: String
            if old.isEmpty { updated = try save(.init(key: fingerprint.sha256, bit: 256, left: "", right: "")) }
            else { updated = try insert(fingerprint.sha256, reference: old, node: load(old)) }
            if updated != old {
                roots[fingerprint.bytes - 1] = updated
                try atomic(Self.header(roots), name: "roots")
            }
            guard fsync(directory) == 0, unlinkat(directory, "pending", 0) == 0, fsync(directory) == 0 else { throw StoreObservationFile.indexFailure() }
        }
        func recognize(_ fingerprint: CredentialFingerprint) throws {
            if try containsHash(fingerprint.sha256, root: roots[fingerprint.bytes - 1]) { return }
            try atomic(Self.entry(fingerprint), name: "pending")
            try finishRecognition(fingerprint)
        }
        func contains(_ value: String) throws -> Bool {
            let bytes = Array(value.utf8)
            guard !bytes.isEmpty else { return false }
            for length in 1...min(bytes.count, 256) where !roots[length - 1].isEmpty {
                for offset in 0...(bytes.count - length) {
                    let hash = SourceDigest.sha256(Data(bytes[offset..<(offset + length)]))
                    if try containsHash(hash, root: roots[length - 1]) { return true }
                }
            }
            return false
        }
    }
    private func prepare(_ record: inout Record) throws -> (CredentialIndex, Bool) {
        // R2 saturation discarded unknown later fingerprints. Clearing it would
        // falsely claim complete history; this unreleased schema needs explicit recovery.
        guard record.redactionsExhausted != true else {
            throw MixerFailure("store.credential-history-incomplete", "This unreleased record discarded credential history. Automatic migration cannot safely reconstruct it; restore complete recognition evidence before migration.")
        }
        let index = try CredentialIndex(parent: directory, name: name + ".credentials", create: record.schema == 1)
        for fingerprint in record.redactions ?? [] { try index.recognize(fingerprint) }
        if !token.isEmpty && token.utf8.count <= 256 {
            try index.recognize(.init(bytes: token.utf8.count, sha256: SourceDigest.sha256(Data(token.utf8))))
        }
        let migrated = record.schema == 1
        record.schema = 2; record.redactions = nil; record.redactionsExhausted = nil
        let sanitized = try sanitize(&record, index: index)
        return (index, migrated || sanitized)
    }
    private func reflectsCredential(_ observation: StoreBuildObservation, index: CredentialIndex) throws -> Bool {
        for value in [observation.version, observation.processingState] {
            if !token.isEmpty && value.contains(token) { return true }
            if try index.contains(value) { return true }
        }
        return false
    }
    private func sanitize(_ record: inout Record, index: CredentialIndex) throws -> Bool {
        if let observation = record.observation, try reflectsCredential(observation, index: index) {
            record.discardedThrough = max(record.discardedThrough ?? 0, observation.generation)
            record.observation = nil
            return true
        }
        return false
    }
    func reserve() throws -> UInt64 {
        try locked {
            var record = try read()
            let (_, sanitized) = try prepare(&record)
            guard record.issued < UInt64.max else {
                if sanitized { try write(record) }
                throw Self.failure()
            }
            record.issued += 1
            try write(record)
            return record.issued
        }
    }
    func commit(_ observation: StoreBuildObservation) throws -> (StoreBuildObservation?, Bool) {
        try locked {
            var record = try read()
            let (index, sanitized) = try prepare(&record)
            if sanitized { try write(record) }
            guard observation.generation <= record.issued else { throw Self.failure() }
            guard observation.generation > max(record.observation?.generation ?? 0, record.discardedThrough ?? 0) else { return (record.observation, false) }
            guard try !reflectsCredential(observation, index: index) else { throw StoreQueryFailure.redactedResponse }
            record.observation = observation; try write(record); return (observation, true)
        }
    }
    func observation() throws -> StoreBuildObservation? {
        try locked {
            var record = try read()
            let (_, sanitized) = try prepare(&record)
            if sanitized { try write(record) }
            return record.observation
        }
    }
}
