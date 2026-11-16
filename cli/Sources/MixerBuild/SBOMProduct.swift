import Foundation
import CryptoKit
import Darwin

/// SPDX 2.3 evidence for an explicitly verified subset, never a dependency-closure claim.
public enum SBOMProduct {
    public enum Kind: String, Codable, Sendable { case sbom }
    public enum Completeness: String, Codable, Sendable { case verifiedSubset = "verified_subset" }
    public struct Material: Codable, Equatable, Sendable {
        public let logicalPath: String
        public let path: String
        public let sizeBytes: UInt64
        public let sha256: String
        public init(logicalPath: String, path: String, sizeBytes: UInt64, sha256: String) {
            self.logicalPath = logicalPath; self.path = path; self.sizeBytes = sizeBytes; self.sha256 = sha256
        }
    }
    public struct Inputs: Sendable {
        public let capture: NativeProductCapture.Result
        public let captureStore: URL
        public let inventory: ResourceInventoryProduct.Descriptor
        public let inventoryStore: URL
        public let expectedBindingSHA256: String
        public let materials: [Material]
        public let created: String
        public init(capture: NativeProductCapture.Result, captureStore: URL,
            inventory: ResourceInventoryProduct.Descriptor, inventoryStore: URL,
            expectedBindingSHA256: String, materials: [Material], created: String) {
            self.capture = capture; self.captureStore = captureStore; self.inventory = inventory
            self.inventoryStore = inventoryStore; self.expectedBindingSHA256 = expectedBindingSHA256
            self.materials = materials; self.created = created
        }
    }
    public struct Descriptor: Codable, Equatable, Sendable {
        public let kind: Kind
        public let sha256: String
        public let sizeBytes: UInt64
        public let ownedPath: String
        public let completeness: Completeness
        public let gaps: [String]
    }
    public enum Failure: Error, Equatable {
        case invalidIdentity, invalidPath, unsafeFile, corruptObject, mutation, incomplete, io(Int32)
    }
    public static let gaps = ["build-provenance-not-established", "dependency-closure-not-established",
        "licenses-not-determined", "platform-component-identities-not-established", "source-to-output-derivation-not-established"]

    public static func requireAggregateEligible(_ descriptor: Descriptor) throws {
        // This producer has no evidence path capable of establishing complete closure.
        throw Failure.incomplete
    }

    public static func produce(inputs: Inputs, store: URL) throws -> Descriptor {
        let bytes = try canonical(inputs)
        let digest = hash(bytes)
        let descriptor = Descriptor(kind: .sbom, sha256: digest, sizeBytes: UInt64(bytes.count),
            ownedPath: store.path + "/" + digest, completeness: .verifiedSubset, gaps: gaps)
        let root = try directory(store.path, privateStore: true); defer { close(root) }
        let stage = ".sbom-" + UUID().uuidString
        let fd = openat(root, stage, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        try check(fd)
        defer { close(fd); unlinkat(root, stage, 0) }
        try bytes.withUnsafeBytes { buffer in
            var offset = 0
            while offset < buffer.count {
                let count = Darwin.write(fd, buffer.baseAddress!.advanced(by: offset), buffer.count - offset)
                if count < 0 && errno == EINTR { continue }
                guard count > 0 else { throw Failure.io(errno) }; offset += count
            }
        }
        try check(fchmod(fd, 0o444)); try check(fsync(fd))
        if linkat(root, stage, root, digest, 0) != 0, errno != EEXIST { throw Failure.io(errno) }
        try check(unlinkat(root, stage, 0)); try check(fsync(root))
        guard try read(path: descriptor.ownedPath, size: descriptor.sizeBytes, sha256: digest, immutable: true) == bytes else {
            throw Failure.corruptObject
        }
        return descriptor
    }

    public static func revalidate(_ descriptor: Descriptor, inputs: Inputs, store: URL) throws {
        guard descriptor.completeness == .verifiedSubset, descriptor.gaps == gaps,
            descriptor.ownedPath == store.path + "/" + descriptor.sha256 else { throw Failure.corruptObject }
        let root = try directory(store.path, privateStore: true); close(root)
        let actual = try read(path: descriptor.ownedPath, size: descriptor.sizeBytes, sha256: descriptor.sha256, immutable: true)
        guard actual == (try canonical(inputs)) else { throw Failure.corruptObject }
    }

    private static func canonical(_ inputs: Inputs) throws -> Data {
        let inventory = try ResourceInventoryProduct.revalidate(inputs.inventory, capture: inputs.capture,
            captureStore: inputs.captureStore, store: inputs.inventoryStore, expectedBindingSHA256: inputs.expectedBindingSHA256)
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        guard let date = formatter.date(from: inputs.created), formatter.string(from: date) == inputs.created,
            !inputs.materials.isEmpty, inputs.materials.count <= 10000 else { throw Failure.invalidIdentity }
        var logical = Set<String>(); var locations = Set<String>()
        let materials = inputs.materials.sorted { $0.logicalPath < $1.logicalPath }
        for material in materials {
            guard relative(material.logicalPath), logical.insert(material.logicalPath.lowercased()).inserted,
                locations.insert(material.path).inserted else { throw Failure.invalidIdentity }
            _ = try read(path: material.path, size: material.sizeBytes, sha256: material.sha256)
        }
        let binding = inputs.expectedBindingSHA256
        let nativeArchive = inputs.capture.nativeBinary
        let appBytes = try read(path: nativeArchive.ownedPath, size: nativeArchive.sizeBytes,
            sha256: nativeArchive.sha256, immutable: true)
        // R2990 has validated this archive; slice its payload using that exact inventory.
        let magic = Data("MXNATIVE1\n".utf8)
        guard appBytes.count >= magic.count + 8, appBytes.prefix(magic.count) == magic else { throw Failure.corruptObject }
        let headerLength = appBytes[magic.count..<magic.count + 8].reduce(UInt64(0)) { ($0 << 8) | UInt64($1) }
        guard headerLength <= appBytes.count - magic.count - 8 else { throw Failure.corruptObject }
        var cursor = magic.count + 8 + Int(headerLength)
        var files: [[String: Any]] = []
        for entry in inventory.entries where entry.kind == .file {
            guard entry.sizeBytes <= appBytes.count - cursor else { throw Failure.corruptObject }
            let payload = appBytes.subdata(in: cursor..<cursor + Int(entry.sizeBytes))
            guard hash(payload) == entry.sha256 else { throw Failure.corruptObject }
            cursor += payload.count
            files.append(file(name: "./retained-app/" + entry.path, bytes: payload,
                comment: "Retained app file; role=" + (entry.classification?.rawValue ?? "unclassified")))
        }
        guard cursor == appBytes.count else { throw Failure.corruptObject }
        for material in materials {
            let payload = try read(path: material.path, size: material.sizeBytes, sha256: material.sha256)
            files.append(file(name: "./materials/" + material.logicalPath, bytes: payload,
                comment: "Explicit caller material verified byte-for-byte; source-to-output derivation is unasserted."))
        }
        let symbols = inputs.capture.debugSymbols
        let symbolBytes = try read(path: symbols.ownedPath, size: symbols.sizeBytes, sha256: symbols.sha256, immutable: true)
        files.append(file(name: "./retained-symbols/" + symbols.sha256, bytes: symbolBytes,
            comment: "Exact retained debug-symbol archive; UUID=" + inputs.capture.uuid))
        files.sort { ($0["fileName"] as! String) < ($1["fileName"] as! String) }
        let native = inputs.capture.nativeBinary
        let packageID = "SPDXRef-Native-" + native.sha256
        let package: [String: Any] = ["SPDXID": packageID, "name": inputs.capture.executable,
            "packageFileName": native.sha256, "downloadLocation": "NOASSERTION", "filesAnalyzed": false,
            "checksums": [["algorithm": "SHA256", "checksumValue": native.sha256]],
            "licenseConcluded": "NOASSERTION", "licenseDeclared": "NOASSERTION",
            "copyrightText": "NOASSERTION", "primaryPackagePurpose": "ARCHIVE",
            "comment": "Single-file MXNATIVE1 retained archive, not a distribution package; binding=" + binding]
        var relationships: [[String: String]] = [
            ["spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES", "relatedSpdxElement": packageID],
            ["spdxElementId": packageID, "relationshipType": "DEPENDS_ON", "relatedSpdxElement": "NOASSERTION"]]
        for item in files {
            relationships.append(["spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES",
                "relatedSpdxElement": item["SPDXID"] as! String])
        }
        let scope: [String: Any] = ["completeness": Completeness.verifiedSubset.rawValue, "gaps": gaps,
            "bindingSHA256": binding, "inventorySHA256": inputs.inventory.sha256,
            "observedPlatformLoadNames": inputs.capture.dependencies,
            "unknownPlatformVersionsLicensesAndTransitiveDependencies": true,
            "aggregateEligible": false]
        let scopeBytes = try JSONSerialization.data(withJSONObject: scope, options: [.sortedKeys, .withoutEscapingSlashes])
        var document: [String: Any] = ["spdxVersion": "SPDX-2.3", "dataLicense": "CC0-1.0", "SPDXID": "SPDXRef-DOCUMENT",
            "name": inputs.capture.executable + "-verified-subset", "creationInfo": ["created": inputs.created,
                "creators": ["Tool: Mixer-SBOMProduct-1"]], "comment": String(decoding: scopeBytes, as: UTF8.self),
            "packages": [package], "files": files, "relationships": relationships]
        // Namespace covers every document field except the namespace itself.
        let seed = try JSONSerialization.data(withJSONObject: document, options: [.sortedKeys, .withoutEscapingSlashes])
        document["documentNamespace"] = "https://spdx.org/spdxdocs/mixer-subset-" + hash(seed)
        // Recheck the frozen sources and retained parents before returning publishable bytes.
        for material in materials { _ = try read(path: material.path, size: material.sizeBytes, sha256: material.sha256) }
        _ = try ResourceInventoryProduct.revalidate(inputs.inventory, capture: inputs.capture, captureStore: inputs.captureStore,
            store: inputs.inventoryStore, expectedBindingSHA256: binding)
        return try JSONSerialization.data(withJSONObject: document, options: [.sortedKeys, .withoutEscapingSlashes])
    }
    private static func file(name: String, bytes: Data, comment: String) -> [String: Any] {
        // SPDX 2.3 section 8.4.1 requires SHA1 for interoperability; SHA256 remains the integrity identity.
        let sha1 = Insecure.SHA1.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
        return ["SPDXID": "SPDXRef-File-" + hash(Data(name.utf8)), "fileName": name,
            "checksums": [["algorithm": "SHA1", "checksumValue": sha1],
                ["algorithm": "SHA256", "checksumValue": hash(bytes)]],
            "licenseConcluded": "NOASSERTION", "licenseInfoInFiles": ["NOASSERTION"],
            "copyrightText": "NOASSERTION", "comment": comment]
    }
    private static func hash(_ bytes: Data) -> String { SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined() }
    private static func digest(_ s: String) -> Bool { s.utf8.count == 64 && s.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) } }
    private static func relative(_ s: String) -> Bool {
        !s.isEmpty && !s.hasPrefix("/") && !s.utf8.contains(0) &&
            s.split(separator: "/", omittingEmptySubsequences: false).allSatisfy { !$0.isEmpty && $0 != "." && $0 != ".." }
    }
    private static func check(_ code: Int32) throws { guard code >= 0 else { throw Failure.io(errno) } }
    private static func directory(_ path: String, privateStore: Bool = false) throws -> Int32 {
        guard path.hasPrefix("/"), relative(String(path.dropFirst())) else { throw Failure.invalidPath }
        var fd = open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC); try check(fd)
        do {
            for part in path.split(separator: "/") {
                let next = openat(fd, String(part), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
                try check(next); close(fd); fd = next
            }
            var info = stat(); try check(fstat(fd, &info))
            guard !privateStore || (info.st_uid == geteuid() && info.st_mode & 0o777 == 0o700) else { throw Failure.unsafeFile }
            return fd
        } catch { close(fd); throw error }
    }
    private static func stable(_ a: stat, _ b: stat) -> Bool {
        a.st_dev == b.st_dev && a.st_ino == b.st_ino && a.st_size == b.st_size && a.st_nlink == b.st_nlink &&
            a.st_mode == b.st_mode && a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec && a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec &&
            a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec && a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec
    }
    private static func read(path: String, size: UInt64, sha256: String, immutable: Bool = false) throws -> Data {
        guard path.hasPrefix("/"), relative(String(path.dropFirst())), digest(sha256), size <= 256 * 1024 * 1024 else { throw Failure.invalidIdentity }
        let url = URL(fileURLWithPath: path)
        let root = try directory(url.deletingLastPathComponent().path); defer { close(root) }
        let fd = openat(root, url.lastPathComponent, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
        try check(fd); defer { close(fd) }
        var before = stat(); try check(fstat(fd, &before))
        guard before.st_mode & S_IFMT == S_IFREG, before.st_nlink == 1, before.st_uid == geteuid(),
            before.st_size >= 0, UInt64(before.st_size) == size,
            !immutable || before.st_mode & 0o777 == 0o444 else { throw Failure.unsafeFile }
        var bytes = Data(); var buffer = [UInt8](repeating: 0, count: 65536)
        while true {
            let n = Darwin.read(fd, &buffer, buffer.count)
            if n < 0 && errno == EINTR { continue }; guard n >= 0 else { throw Failure.io(errno) }
            if n == 0 { break }; guard bytes.count + n <= Int(size) else { throw Failure.mutation }
            bytes.append(contentsOf: buffer.prefix(n))
        }
        var after = stat(); try check(fstat(fd, &after))
        guard stable(before, after), bytes.count == Int(size) else { throw Failure.mutation }
        guard hash(bytes) == sha256 else { throw Failure.corruptObject }
        return bytes
    }
}
