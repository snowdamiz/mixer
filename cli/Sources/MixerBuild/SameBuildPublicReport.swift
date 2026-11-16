import Foundation
import Darwin

/// Explicit local observation of one existing public build; never a trusted builder claim.
public enum SameBuildPublicReport {
    public typealias FileIdentity = SamePublicBuildProvenance.FileIdentity
    public struct Evidence: Codable, Equatable, Sendable {
        public let originalReport: FileIdentity
        public let publicInvocation: FileIdentity
        public let identityProof: FileIdentity
        public let nativeCustody: FileIdentity
        public let observerImplementation: FileIdentity
        public init(originalReport: FileIdentity, publicInvocation: FileIdentity, identityProof: FileIdentity,
                    nativeCustody: FileIdentity, observerImplementation: FileIdentity) {
            self.originalReport = originalReport; self.publicInvocation = publicInvocation
            self.identityProof = identityProof; self.nativeCustody = nativeCustody
            self.observerImplementation = observerImplementation
        }
        var files: [FileIdentity] {
            [originalReport, publicInvocation, identityProof, nativeCustody, observerImplementation]
        }
        static let names = ["original-report.json", "public-invocation.json", "identity-proof.json",
                            "native-custody.json", "observer-implementation"]
        init(_ files: [FileIdentity]) {
            originalReport = files[0]; publicInvocation = files[1]; identityProof = files[2]
            nativeCustody = files[3]; observerImplementation = files[4]
        }
    }
    public struct Request: Codable, Sendable {
        public let version: Int
        public let projectRoot: String
        public let compilerRoot: String
        public let sdkRoot: String
        public let cliBinary: String
        public let lockFile: String
        public let nativeStore: String
        public let evidence: Evidence
        public let created: String
        public init(version: Int = 1, projectRoot: String, compilerRoot: String, sdkRoot: String,
                    cliBinary: String, lockFile: String, nativeStore: String, evidence: Evidence, created: String) {
            self.version = version; self.projectRoot = projectRoot; self.compilerRoot = compilerRoot
            self.sdkRoot = sdkRoot; self.cliBinary = cliBinary; self.lockFile = lockFile
            self.nativeStore = nativeStore; self.evidence = evidence; self.created = created
        }
    }
    public struct Descriptor: Codable, Sendable {
        public let version: Int
        public let completeness: String
        public let unsigned: Bool
        public let snapshot: BuildInputSnapshot.Descriptor
        public let sbom: SamePublicBuildSBOM.Descriptor
        public let provenance: SamePublicBuildProvenance.Descriptor
        public let evidence: Evidence
    }
    public enum Failure: Error { case version, path, identity, incomplete }
    public static let requestByteLimit = 1 << 20
    private static let evidenceByteLimit = 4 << 20

    public static func readRequest(_ url: URL) throws -> Request {
        try JSONDecoder().decode(Request.self, from: VerificationFile.read(url, maximumBytes: requestByteLimit))
    }

    public static func observe(request: Request, output: URL) throws -> Descriptor {
        guard request.version == 1 else { throw Failure.version }
        let project = try absolute(request.projectRoot), compiler = try absolute(request.compilerRoot)
        let sdk = try absolute(request.sdkRoot), cli = try absolute(request.cliBinary)
        let lock = try absolute(request.lockFile), native = try absolute(request.nativeStore)
        guard output.isFileURL else { throw Failure.path }
        _ = try absolute(output.path)
        let originals = request.evidence.files
        guard Set(originals.map(\.logicalPath)).count == originals.count,
              Set(originals.map(\.path)).count == originals.count else { throw Failure.identity }
        // Read bounded, explicit evidence before acquiring an output store.
        let bytes = try originals.map(read)
        guard bytes[0] == (try VerificationFile.read(native.appendingPathComponent("native-build.json"),
                                                    maximumBytes: evidenceByteLimit)) else { throw Failure.identity }
        for input in [project, compiler, sdk, cli, lock, native] + (try originals.map { try absolute($0.path) }) {
            guard !overlaps(output.path, input.path) else { throw Failure.path }
        }
        let owner = try NativeBuildOutput.prepare(output: output, root: project)
        let evidenceRoot = output.appendingPathComponent("evidence")
        for root in [evidenceRoot, output.appendingPathComponent("sbom"), output.appendingPathComponent("provenance")] {
            try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false,
                attributes: [.posixPermissions: 0o700])
        }
        var retained: [FileIdentity] = []
        for (index, original) in originals.enumerated() {
            let target = evidenceRoot.appendingPathComponent(Evidence.names[index])
            try persist(bytes[index], at: target)
            retained.append(.init(logicalPath: original.logicalPath, path: target.path,
                                  sha256: original.sha256, sizeBytes: original.sizeBytes))
        }
        let evidence = Evidence(retained)
        let snapshotStore = output.appendingPathComponent("snapshot")
        let snapshot = try BuildInputSnapshot.produce(inputs: .init(projectRoot: project, compilerRoot: compiler,
            sdkRoot: sdk, cliBinary: cli, lockFile: lock), parentStore: native, output: snapshotStore)
        let sbom = try SamePublicBuildSBOM.produce(snapshot: snapshot, snapshotStore: snapshotStore,
            originalReport: URL(fileURLWithPath: evidence.originalReport.path), created: request.created,
            output: output.appendingPathComponent("sbom"))
        let inputs = provenanceInputs(snapshot: snapshot, sbom: sbom, evidence: evidence, output: output)
        // The existing producer validates literal terminal custody, genuine argv shape, and all bindings.
        let provenance = try SamePublicBuildProvenance.produce(inputs: inputs,
            store: output.appendingPathComponent("provenance"))
        let descriptor = Descriptor(version: 1, completeness: "verified_subset", unsigned: true,
            snapshot: snapshot, sbom: sbom, provenance: provenance, evidence: evidence)
        try validate(descriptor, at: output)
        for (index, original) in originals.enumerated() {
            guard try read(original) == bytes[index] else { throw Failure.identity }
        }
        try owner.check()
        // Publication is last; partial stores on refusal are not a successful report.
        try persist(JSONFile.data(descriptor), at: output.appendingPathComponent("report.json"))
        try owner.check()
        return descriptor
    }

    /// Reopens retained outputs without consulting any original material root or native store.
    public static func reopen(output: URL) throws -> Descriptor {
        _ = try absolute(output.path)
        let bytes = try VerificationFile.read(output.appendingPathComponent("report.json"),
                                               maximumBytes: requestByteLimit)
        let descriptor = try JSONDecoder().decode(Descriptor.self, from: bytes)
        try validate(descriptor, at: output)
        return descriptor
    }

    public static func requireAggregateEligible(_ descriptor: Descriptor) throws { throw Failure.incomplete }

    private static func validate(_ d: Descriptor, at output: URL) throws {
        guard d.version == 1, d.completeness == "verified_subset", d.unsigned else { throw Failure.identity }
        for (index, file) in d.evidence.files.enumerated() {
            guard file.path == output.appendingPathComponent("evidence").appendingPathComponent(Evidence.names[index]).path
            else { throw Failure.path }
            _ = try read(file)
        }
        _ = try BuildInputSnapshot.reopen(d.snapshot, store: output.appendingPathComponent("snapshot"))
        try SamePublicBuildSBOM.reopen(d.sbom, snapshotStore: output.appendingPathComponent("snapshot"),
            originalReport: URL(fileURLWithPath: d.evidence.originalReport.path), output: output.appendingPathComponent("sbom"))
        try SamePublicBuildProvenance.reopen(d.provenance,
            inputs: provenanceInputs(snapshot: d.snapshot, sbom: d.sbom, evidence: d.evidence, output: output),
            store: output.appendingPathComponent("provenance"))
    }
    private static func provenanceInputs(snapshot: BuildInputSnapshot.Descriptor, sbom: SamePublicBuildSBOM.Descriptor,
                                         evidence: Evidence, output: URL) -> SamePublicBuildProvenance.Inputs {
        .init(snapshot: snapshot, snapshotStore: output.appendingPathComponent("snapshot"),
            originalReport: evidence.originalReport, sbom: sbom, sbomStore: output.appendingPathComponent("sbom"),
            publicInvocation: evidence.publicInvocation, identityProof: evidence.identityProof,
            nativeCustody: evidence.nativeCustody, observerImplementation: evidence.observerImplementation)
    }
    private static func absolute(_ path: String) throws -> URL {
        let url = URL(fileURLWithPath: path)
        guard path.hasPrefix("/"), path.utf8.count <= 4096, !path.utf8.contains(0),
              path == url.standardizedFileURL.path else { throw Failure.path }
        return url
    }
    private static func overlaps(_ a: String, _ b: String) -> Bool {
        a == b || a.hasPrefix(b + "/") || b.hasPrefix(a + "/")
    }
    private static func read(_ identity: FileIdentity) throws -> Data {
        let url = try absolute(identity.path)
        guard !identity.logicalPath.isEmpty, identity.logicalPath.utf8.count <= 4096 else { throw Failure.identity }
        let bytes = try VerificationFile.read(url, maximumBytes: evidenceByteLimit)
        guard UInt64(bytes.count) == identity.sizeBytes, SourceDigest.sha256(bytes) == identity.sha256
        else { throw Failure.identity }
        return bytes
    }
    private static func persist(_ bytes: Data, at url: URL) throws {
        try bytes.write(to: url, options: .withoutOverwriting)
        let (handle, _) = try VerificationFile.openRegular(url)
        defer { try? handle.close() }
        guard fchmod(handle.fileDescriptor, 0o444) == 0, fsync(handle.fileDescriptor) == 0
        else { throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EIO) }
        let parent = open(url.deletingLastPathComponent().path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard parent >= 0 else { throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EIO) }
        defer { close(parent) }
        guard fsync(parent) == 0 else { throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EIO) }
    }
}
