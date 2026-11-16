import Foundation
import Darwin

/// Unsigned local observation of one retained build, without a trusted-build claim.
public enum SamePublicBuildProvenance {
    public struct FileIdentity: Codable, Equatable, Sendable {
        public let logicalPath: String
        public let path: String
        public let sha256: String
        public let sizeBytes: UInt64
        public init(logicalPath: String, path: String, sha256: String, sizeBytes: UInt64) {
            self.logicalPath = logicalPath; self.path = path; self.sha256 = sha256; self.sizeBytes = sizeBytes
        }
    }
    public struct Inputs: Sendable {
        public let snapshot: BuildInputSnapshot.Descriptor
        public let snapshotStore: URL
        public let originalReport: FileIdentity
        public let sbom: SamePublicBuildSBOM.Descriptor
        public let sbomStore: URL
        public let publicInvocation: FileIdentity
        public let identityProof: FileIdentity
        public let nativeCustody: FileIdentity
        public let observerImplementation: FileIdentity
        public init(snapshot: BuildInputSnapshot.Descriptor, snapshotStore: URL, originalReport: FileIdentity,
            sbom: SamePublicBuildSBOM.Descriptor, sbomStore: URL, publicInvocation: FileIdentity,
            identityProof: FileIdentity, nativeCustody: FileIdentity, observerImplementation: FileIdentity) {
            self.snapshot = snapshot; self.snapshotStore = snapshotStore; self.originalReport = originalReport
            self.sbom = sbom; self.sbomStore = sbomStore; self.publicInvocation = publicInvocation
            self.identityProof = identityProof; self.nativeCustody = nativeCustody
            self.observerImplementation = observerImplementation
        }
    }
    public struct Descriptor: Codable, Equatable, Sendable {
        public let sha256: String
        public let sizeBytes: UInt64
        public let ownedPath: String
        public let completeness: String
        public let unsigned: Bool
    }
    public enum Failure: Error { case identity, custody, path, corrupt, incomplete, io(Int32) }
    private struct Invocation: Decodable { let argv: [String]; let environment: [String: String] }
    private struct Proof: Decodable {
        struct Observed: Decodable {
            let cliExecutableSHA256: String; let compilerSourceDigest: String
            let lockSHA256: String; let projectSourceDigest: String; let sdkDigest: String
        }
        let allEqualToCapturedBinding: Bool
        let observed: Observed
    }
    private struct Custody: Decodable {
        let command: [String]; let directory: String; let exitCode: Int
        let state: String; let terminalCustody: Bool; let directChildReaped: Bool
        let stdoutEOF: Bool; let stderrEOF: Bool; let descriptorsClosed: Bool
        let ownedGroupAbsent: Bool; let released: Bool; let outputTruncated: Bool
        let pid: Int; let ownedPGID: Int; let ownedSession: Int
    }

    public static func produce(inputs: Inputs, store: URL) throws -> Descriptor {
        try isolate(store, inputs)
        let bytes = try statement(inputs)
        let digest = SourceDigest.sha256(bytes)
        let root = try directory(store, privateStore: true); defer { close(root) }
        let file = openat(root, digest, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard file >= 0 else { throw Failure.io(errno) }; defer { close(file) }
        try bytes.withUnsafeBytes { raw in
            var offset = 0
            while offset < raw.count {
                let n = Darwin.write(file, raw.baseAddress!.advanced(by: offset), raw.count - offset)
                if n < 0 && errno == EINTR { continue }
                guard n > 0 else { throw Failure.io(errno) }; offset += n
            }
        }
        guard fchmod(file, 0o444) == 0, fsync(file) == 0, fsync(root) == 0 else { throw Failure.io(errno) }
        let descriptor = Descriptor(sha256: digest, sizeBytes: UInt64(bytes.count),
            ownedPath: store.path + "/" + digest, completeness: "verified_subset", unsigned: true)
        guard try read(.init(logicalPath: "provenance.json", path: descriptor.ownedPath,
            sha256: digest, sizeBytes: descriptor.sizeBytes)) == bytes else { throw Failure.corrupt }
        return descriptor
    }

    public static func reopen(_ descriptor: Descriptor, inputs: Inputs, store: URL) throws {
        try isolate(store, inputs)
        let fd = try directory(store, privateStore: true); close(fd)
        guard descriptor.completeness == "verified_subset", descriptor.unsigned,
              descriptor.ownedPath == store.path + "/" + descriptor.sha256 else { throw Failure.identity }
        let actual = try read(.init(logicalPath: "provenance.json", path: descriptor.ownedPath,
            sha256: descriptor.sha256, sizeBytes: descriptor.sizeBytes))
        guard actual == (try statement(inputs)) else { throw Failure.corrupt }
    }

    public static func requireAggregateEligible(_ descriptor: Descriptor) throws { throw Failure.incomplete }

    private static func statement(_ i: Inputs) throws -> Data {
        let snapshot = try BuildInputSnapshot.reopen(i.snapshot, store: i.snapshotStore)
        let original = try read(i.originalReport)
        let parent = try JSONDecoder().decode(NativeBuildOutput.Report.self, from: original)
        guard i.originalReport.sha256 == snapshot.originalParentSHA256,
              try JSONFile.data(parent) == JSONFile.data(snapshot.originalParent),
              parent.succeeded, parent.commandResult.command == parent.binding.command,
              !parent.commandResult.outputTruncated else { throw Failure.identity }
        try SamePublicBuildSBOM.reopen(i.sbom, snapshotStore: i.snapshotStore,
            originalReport: URL(fileURLWithPath: i.originalReport.path), output: i.sbomStore)
        guard i.sbom.snapshot == i.snapshot else { throw Failure.identity }
        let invocationBytes = try read(i.publicInvocation)
        let proofBytes = try read(i.identityProof)
        let custodyBytes = try read(i.nativeCustody)
        _ = try read(i.observerImplementation)
        let invocation = try JSONDecoder().decode(Invocation.self, from: invocationBytes)
        let proof = try JSONDecoder().decode(Proof.self, from: proofBytes)
        let custody = try JSONDecoder().decode(Custody.self, from: custodyBytes)
        let binding = parent.binding
        guard proof.allEqualToCapturedBinding,
              proof.observed.cliExecutableSHA256 == binding.cliExecutableSHA256,
              proof.observed.compilerSourceDigest == binding.compilerSourceDigest,
              proof.observed.lockSHA256 == binding.lockSHA256,
              proof.observed.projectSourceDigest == binding.authoritativeSourceDigest,
              proof.observed.sdkDigest == binding.sdkDigest,
              invocation.argv.count == 8, invocation.argv[1...3] == ["build", "--platform", "ios"],
              invocation.argv[4] == "--directory", invocation.argv[6] == "--output",
              invocation.argv[5] == custody.directory,
              invocation.argv[7] == URL(fileURLWithPath: snapshot.originalParent.nativeProduct!.nativeBinary.ownedPath).deletingLastPathComponent().path,
              invocation.environment.allSatisfy({ binding.environment[$0.key] == $0.value }),
              custody.command == binding.command else { throw Failure.identity }
        guard custody.exitCode == 0, custody.state == "TERMINAL", custody.terminalCustody,
              custody.directChildReaped, custody.stdoutEOF, custody.stderrEOF, custody.descriptorsClosed,
              custody.ownedGroupAbsent, custody.released, !custody.outputTruncated,
              custody.pid > 0, custody.ownedPGID == custody.pid, custody.ownedSession == custody.pid
        else { throw Failure.custody }
        let materials = try BuildInputSnapshot.retainedMaterials(i.snapshot, store: i.snapshotStore)
        guard let capture = parent.nativeProduct, let inventory = parent.resourceInventory else { throw Failure.identity }
        func resource(_ name: String, _ sha: String, _ size: UInt64) -> [String: Any] {
            ["name": name, "digest": ["sha256": sha], "size": size]
        }
        var dependencies = materials.map { resource("retained-inputs/" + $0.logicalPath, $0.sha256, $0.sizeBytes) }
        let evidence = [i.originalReport, i.publicInvocation, i.identityProof, i.nativeCustody, i.observerImplementation]
        guard Set(evidence.map(\.logicalPath)).count == evidence.count,
              Set(evidence.map(\.path)).count == evidence.count else { throw Failure.identity }
        for item in evidence { dependencies.append(resource("evidence/" + item.logicalPath, item.sha256, item.sizeBytes)) }
        dependencies.append(resource("evidence/build-input-snapshot.json", i.snapshot.sha256, i.snapshot.sizeBytes))
        dependencies.append(resource("evidence/sbom.spdx.json", i.sbom.sbom.sha256, i.sbom.sbom.sizeBytes))
        dependencies.sort { ($0["name"] as! String) < ($1["name"] as! String) }
        guard Set(dependencies.map { $0["name"] as! String }).count == dependencies.count else { throw Failure.identity }
        let subjects: [[String: Any]] = [
            ["name": "retained-native/" + capture.executable + ".app.mixer-archive", "digest": ["sha256": capture.nativeBinary.sha256]],
            ["name": "retained-symbols/" + capture.executable + ".dSYM.mixer-archive", "digest": ["sha256": capture.debugSymbols.sha256]],
            ["name": "resource-inventory.json", "digest": ["sha256": inventory.sha256]]]
        let scope: [String: Any] = ["completeness": "verified_subset", "unsigned": true, "aggregateEligible": false,
            "gaps": BuildInputSnapshot.gaps + ["trusted-original-builder-identity-not-established", "source-to-output-derivation-not-established"],
            "sbom": resource("sbom.spdx.json", i.sbom.sbom.sha256, i.sbom.sbom.sizeBytes),
            "originalReportSHA256": snapshot.originalParentSHA256, "relocatedReportSHA256": snapshot.retainedParentSHA256,
            "relocation": "Exactly nativeBinary, debugSymbols and resourceInventory ownedPath fields only.",
            "bindingSHA256": snapshot.bindingSHA256, "originalNativeCustody": "positive-retained-local-record",
            "originalBuildIdentity": "Original compiler and CLI identities are observed inputs, not this observer builder."]
        let external: [String: Any] = ["operation": "observe-and-retain-existing-public-build",
            "originalPublicBuildArgv": invocation.argv, "originalCompilerArgv": binding.command,
            "originalCompilerEnvironment": binding.environment, "toolchainLock": try JSONSerialization.jsonObject(with: JSONFile.data(binding.lock)),
            "originalIdentities": ["projectTree": binding.authoritativeSourceDigest, "compilerTree": binding.compilerSourceDigest,
                "sdkTree": binding.sdkDigest, "cliBinary": binding.cliExecutableSHA256, "lock": binding.lockSHA256],
            "scope": scope]
        let buildDefinition: [String: Any] = ["buildType": "https://mixer.local/buildtypes/retained-public-build-observation/v1",
            "externalParameters": external, "resolvedDependencies": dependencies]
        let seed = try JSONSerialization.data(withJSONObject: buildDefinition, options: [.sortedKeys, .withoutEscapingSlashes])
        let statement: [String: Any] = ["_type": "https://in-toto.io/Statement/v1", "subject": subjects,
            "predicateType": "https://slsa.dev/provenance/v1", "predicate": ["buildDefinition": buildDefinition,
                "runDetails": ["builder": ["id": "https://mixer.local/builders/unsigned-retained-build-observer/v1",
                    "version": ["implementation-sha256": i.observerImplementation.sha256]],
                    "metadata": ["invocationId": "urn:sha256:" + SourceDigest.sha256(seed)]]]]
        // Repeat input owner validation before exposing the artifact.
        _ = try BuildInputSnapshot.reopen(i.snapshot, store: i.snapshotStore)
        for item in evidence { _ = try read(item) }
        return try JSONSerialization.data(withJSONObject: statement, options: [.sortedKeys, .withoutEscapingSlashes])
    }

    private static func isolate(_ store: URL, _ i: Inputs) throws {
        guard store.isFileURL, store.path == store.standardizedFileURL.path else { throw Failure.path }
        for root in [i.snapshotStore, i.sbomStore] + [i.originalReport, i.publicInvocation, i.identityProof,
            i.nativeCustody, i.observerImplementation].map({ URL(fileURLWithPath: $0.path).deletingLastPathComponent() }) {
            let path = root.standardizedFileURL.path
            guard store.path != path, !store.path.hasPrefix(path + "/"), !path.hasPrefix(store.path + "/") else { throw Failure.path }
        }
    }
    private static func relative(_ path: String) -> Bool {
        !path.isEmpty && !path.utf8.contains(0) && path.split(separator: "/", omittingEmptySubsequences: false).allSatisfy { !$0.isEmpty && $0 != "." && $0 != ".." }
    }
    private static func directory(_ url: URL, privateStore: Bool = false) throws -> Int32 {
        guard url.isFileURL, url.path.hasPrefix("/"), url.path == url.standardizedFileURL.path,
              relative(String(url.path.dropFirst())) else { throw Failure.path }
        var fd = open("/", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard fd >= 0 else { throw Failure.io(errno) }
        do {
            for part in url.path.split(separator: "/") {
                let next = openat(fd, String(part), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
                guard next >= 0 else { throw Failure.path }; close(fd); fd = next
                var st = stat()
                guard fstat(fd, &st) == 0, st.st_mode & 0o022 == 0, st.st_uid == 0 || st.st_uid == geteuid() else { throw Failure.path }
            }
            var st = stat()
            guard fstat(fd, &st) == 0, !privateStore || (st.st_uid == geteuid() && st.st_mode & 0o7777 == 0o700) else { throw Failure.path }
            return fd
        } catch { close(fd); throw error }
    }
    private static func read(_ item: FileIdentity) throws -> Data {
        guard relative(item.logicalPath), item.sha256.count == 64,
              item.sha256.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }),
              item.sizeBytes <= 64 * 1024 * 1024 else { throw Failure.identity }
        let url = URL(fileURLWithPath: item.path)
        guard url.path == item.path else { throw Failure.path }
        let root = try directory(url.deletingLastPathComponent()); defer { close(root) }
        let fd = openat(root, url.lastPathComponent, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)
        guard fd >= 0 else { throw Failure.path }; defer { close(fd) }
        var before = stat()
        guard fstat(fd, &before) == 0, before.st_mode & S_IFMT == S_IFREG, before.st_mode & 0o7777 == 0o444,
              before.st_uid == geteuid(), before.st_nlink == 1, before.st_size >= 0,
              UInt64(before.st_size) == item.sizeBytes else { throw Failure.identity }
        var bytes = Data(); var buffer = [UInt8](repeating: 0, count: 65536)
        while true {
            let n = Darwin.read(fd, &buffer, buffer.count)
            if n < 0 && errno == EINTR { continue }; guard n >= 0 else { throw Failure.io(errno) }
            if n == 0 { break }; guard bytes.count + n <= item.sizeBytes else { throw Failure.corrupt }
            bytes.append(contentsOf: buffer.prefix(n))
        }
        var after = stat(), named = stat()
        func same(_ a: stat, _ b: stat) -> Bool {
            a.st_dev == b.st_dev && a.st_ino == b.st_ino && a.st_mode == b.st_mode && a.st_uid == b.st_uid &&
            a.st_nlink == b.st_nlink && a.st_size == b.st_size && a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec &&
            a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec && a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec && a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec
        }
        guard fstat(fd, &after) == 0, fstatat(root, url.lastPathComponent, &named, AT_SYMLINK_NOFOLLOW) == 0,
              same(before, after), same(after, named), bytes.count == item.sizeBytes,
              SourceDigest.sha256(bytes) == item.sha256 else { throw Failure.corrupt }
        return bytes
    }
}
