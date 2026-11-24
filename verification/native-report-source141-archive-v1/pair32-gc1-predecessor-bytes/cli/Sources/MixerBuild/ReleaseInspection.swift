import CryptoKit
import Foundation
import MixerCapabilities
@_spi(GuestUIV1) import MixerGuest
import MixerRuntimeIdentity
import MixerUpdates

public struct ReleaseAssessment: Codable, Sendable {
    public var schema = 1
    public var application: String
    public var platforms: [String]
    public var sourceDigest: String
    public var sdkDigest: String
    public var technicalEligibility = "blocked"
    public var policyAssessment = "pending-project-review"
    public var publicationAllowed = false
    public var blockers = ["Independently pinned compiled behavior and installed-runtime qualification are required."]
    public var qualificationSHA256: String?
    public var targets: [Target]?

    public struct Target: Codable, Sendable {
        public let platform: String
        public let status: String
        public let reason: String?
        public let installedRuntime: String?
        public let candidateRuntime: String?
        public let baselineArtifactSHA256: String?
        public let candidateArtifactSHA256: String?
        public let behaviorReceiptSHA256: String?
    }

    public static func inspect(_ root: URL, qualification: URL? = nil, producerTrust: URL? = nil) throws -> Self {
        let config = try ApplicationConfiguration.load(root)
        let lock = try ProjectBuild.verifyLock(root: root)
        var report = Self(application: config.application, platforms: config.targets,
                          sourceDigest: try SourceDigest.tree(root), sdkDigest: lock.sdkDigest)
        if qualification == nil, producerTrust == nil { return report }
        guard let qualification, let producerTrust else {
            throw MixerFailure("release.qualification-input", "Qualification and the operator's local producer trust configuration are both required.")
        }
        let index = try ReleaseQualification(qualification, producerTrust: producerTrust)
        guard index.sourceDigest == report.sourceDigest, index.sdkDigest == report.sdkDigest,
              Set(index.targets.keys).isSubset(of: config.targets) else {
            throw MixerFailure("release.project-binding", "Qualification does not bind the current project, SDK and configured targets.")
        }
        let now = UInt64(Date().timeIntervalSince1970)
        let results = config.targets.map {
            index.inspect(platform: $0, application: config.applicationIdentifiers?[$0] ?? config.application, now: now)
        }
        report.qualificationSHA256 = index.sha256
        report.targets = results
        let eligible = results.filter { $0.status == "ota-compatible" }.count
        if eligible == results.count {
            report.technicalEligibility = "ota-compatible"
        } else if eligible > 0 {
            report.technicalEligibility = "ota-compatible-one-platform"
        } else if results.contains(where: { $0.status == "store-build-required" }) {
            report.technicalEligibility = "store-build-required"
        }
        report.blockers = results.compactMap { result in result.reason.map { "\(result.platform) \($0)" } }
        return report
    }
}

private struct ReleaseQualification {
    struct NativeBuild: Decodable, Equatable {
        let archiveSHA256: String
        let permissionsSHA256: String
        let identitySHA256: String
    }

    struct TargetPin: Decodable {
        let installed: NativeBuild
        let proposed: NativeBuild
        let baselineArtifactSHA256: String
        let candidateArtifactSHA256: String
        let behaviorReceiptSHA256: String
    }

    private struct OfferBinding: Decodable, Equatable {
        let platform: String
        let runtime: String
        let manifestSHA256: String
        let assignmentSHA256: String
        let payloadSHA256: String
        let acceptedSequence: UInt64
    }

    private struct AppleHostObservation: Decodable {
        struct Frame: Decodable {
            let revision: UInt64
            let childIDs: [String]
            let actionID: String
            let status: String
            let label: String
        }

        let candidateID: String
        let frames: [Frame]
        let ownerRetired: Bool
    }

    private struct Behavior: Decodable {
        struct Observation: Decodable {
            let offer: OfferBinding
            let hostObservationSHA256: String?
            let labels: [String]
            let workspaceSHA256: [String]
            let completed: [Bool]
            let revisions: [UInt64]
            let outboxCounts: [UInt64]

            func proves(review: Bool, binding: OfferBinding) -> Bool {
                let steps = review ? 3 : 2
                guard offer == binding, workspaceSHA256.count == steps,
                      revisions.count == steps, outboxCounts.count == steps,
                      workspaceSHA256.allSatisfy(ReleaseQualification.isSHA256),
                      let initialRevision = revisions.first, initialRevision < UInt64.max,
                      let initialOutbox = outboxCounts.first, initialOutbox < UInt64.max else { return false }
                return labels == (review ? ["Complete task", "Confirm completion", "Reopen task"] : ["Complete task", "Reopen task"])
                    && completed == (review ? [false, false, true] : [false, true])
                    && revisions == (review ? [initialRevision, initialRevision, initialRevision + 1] : [initialRevision, initialRevision + 1])
                    && outboxCounts == (review ? [initialOutbox, initialOutbox, initialOutbox + 1] : [initialOutbox, initialOutbox + 1])
                    && (!review || workspaceSHA256[0] == workspaceSHA256[1])
                    && workspaceSHA256.first != workspaceSHA256.last
            }
        }
        let baseline: Observation
        let candidate: Observation
    }

    private struct ProducerTrust: Decodable {
        let schema: Int
        let publicKey: Data
        let producerSHA256: String
    }

    private static func isSHA256(_ value: String) -> Bool {
        value.utf8.count == 64 && value.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) }
    }

    private struct Scope: Decodable {
        let organization: String
        let project: String
        let app: String
        let environment: String

        func on(_ platform: String) -> UpdateScope {
            .init(organization: organization, project: project, app: app, environment: environment, platform: platform)
        }
    }

    private struct Index: Decodable {
        let schema: Int
        let sourceDigest: String
        let sdkDigest: String
        let sourceCommit: String
        let baselineSourceDigest: String
        let producerSHA256: String
        let toolchainSHA256: String
        let scope: Scope
        let targets: [String: TargetPin]
    }

    let directory: URL
    private let index: Index
    let sha256: String
    var sourceDigest: String { index.sourceDigest }
    var sdkDigest: String { index.sdkDigest }
    var targets: [String: TargetPin] { index.targets }

    init(_ directory: URL, producerTrust: URL) throws {
        self.directory = directory
        let bundle = directory.resolvingSymlinksInPath().path
        let anchor = producerTrust.resolvingSymlinksInPath().path
        guard anchor != bundle, !anchor.hasPrefix(bundle + "/") else {
            throw MixerFailure("release.producer-trust", "The local producer trust configuration must be outside the qualification.")
        }
        let trust = try StrictJSON.decode(ProducerTrust.self,
            from: VerificationFile.read(producerTrust, maximumBytes: 4096), maximumBytes: 4096)
        let exact = try Self.read(directory, "qualification.json")
        let signature = try Self.read(directory, "qualification.ed25519", limit: 64)
        let key = try Curve25519.Signing.PublicKey(rawRepresentation: trust.publicKey)
        guard trust.schema == 1, Self.isSHA256(trust.producerSHA256),
              key.isValidSignature(signature, for: Data("mixer.local.build-provenance.v1\0".utf8) + exact) else {
            throw MixerFailure("release.producer-signature", "Qualification was not signed by the locally trusted build producer.")
        }
        let decoded = try StrictJSON.decode(Index.self, from: exact, maximumBytes: 65_536)
        let toolchain = try Self.read(directory, "toolchain.json", limit: 65_536)
        guard decoded.schema == 3, (1...2).contains(decoded.targets.count),
              decoded.scope.environment == "development", decoded.producerSHA256 == trust.producerSHA256,
              decoded.toolchainSHA256 == SourceDigest.sha256(toolchain),
              Self.isSHA256(decoded.baselineSourceDigest), decoded.baselineSourceDigest != decoded.sourceDigest else {
            throw MixerFailure("release.qualification-schema", "Unsupported build provenance or mismatched producer and toolchain.")
        }
        self.index = decoded
        self.sha256 = SourceDigest.sha256(exact)
    }

    private static func verifyNative(_ target: URL, name: String, build: NativeBuild,
                                     material: RuntimeMaterial) throws {
        let permissions = try read(target, name + ".permissions.json")
        guard build.permissionsSHA256 == SourceDigest.sha256(permissions),
              material.identity.descriptor.object?["build"]?.object?["permissions_sha256"]?.text == build.permissionsSHA256,
              try VerificationFile.sha256(target.appendingPathComponent(name + ".native"), maximumBytes: 256 * 1_048_576)
                == build.archiveSHA256 else {
            throw MixerFailure("release.native-build", "Packaged native output or effective permissions differ from build provenance.")
        }
    }

    func inspect(platform: String, application: String, now: UInt64) -> ReleaseAssessment.Target {
        do {
            guard let pin = targets[platform] else {
                throw MixerFailure("release.target-missing", "Qualified inputs are missing for this target.")
            }
            let target = directory.appendingPathComponent(platform, isDirectory: true)
            let installed = try RuntimeMaterial(target.appendingPathComponent("installed"), pin: pin.installed.identitySHA256)
            let candidate = pin.proposed.identitySHA256 == pin.installed.identitySHA256 ? installed :
                try RuntimeMaterial(target.appendingPathComponent("proposed"), pin: pin.proposed.identitySHA256)
            guard installed.identity.installedRuntime.scope == candidate.identity.installedRuntime.scope,
                  installed.identity.installedRuntime.scope == index.scope.on(platform),
                  installed.bundleID == application, candidate.bundleID == application else {
                throw MixerFailure("release.runtime-scope", "Installed and candidate identities must bind the configured app and target.")
            }

            try Self.verifyNative(target, name: "installed", build: pin.installed, material: installed)
            if pin.proposed != pin.installed {
                try Self.verifyNative(target, name: "proposed", build: pin.proposed, material: candidate)
            }

            func artifact(_ variant: String, runtime: RuntimeMaterial, digest: String,
                          lastSequence: UInt64) throws -> (VerifiedArtifactV3, OfferBinding) {
                let signed = try Self.read(target, variant + ".manifest.json")
                let payload = try Self.read(target, variant + ".wasm", limit: Int(runtime.identity.installedRuntime.maxPayloadBytes))
                let verified = try runtime.verifier.verifyArtifact(signedManifest: signed, payload: payload, now: now)
                guard verified.artifactSHA256 == digest else {
                    throw MixerFailure("release.artifact-binding", "Signed artifact differs from the qualification record.")
                }
                let sourceMap = try Self.read(target, variant + ".source-map.json")
                guard verified.manifest.object?["source_map_sha256"]?.text == SourceDigest.sha256(sourceMap) else {
                    throw MixerFailure("release.source-map", "Source map differs from the signed artifact.")
                }
                let assignment = try Self.read(target, variant + ".assignment.json")
                let verifiedAssignment = try runtime.verifier.verifyAssignment(signedAssignment: assignment,
                    artifact: verified, channel: "beta", installation: "fieldlog-\(platform)-local-1",
                    lastSequence: lastSequence, now: now)
                return (verified, OfferBinding(platform: platform, runtime: runtime.identity.fingerprint,
                    manifestSHA256: SourceDigest.sha256(signed), assignmentSHA256: SourceDigest.sha256(assignment),
                    payloadSHA256: verified.payloadSHA256, acceptedSequence: verifiedAssignment.sequence))
            }
            let (baseline, baselineOffer) = try artifact("baseline", runtime: installed,
                digest: pin.baselineArtifactSHA256, lastSequence: 0)
            try installed.requireInstalledGrants(baseline.capabilityGrants)
            let (update, candidateOffer) = try artifact("candidate", runtime: candidate,
                digest: pin.candidateArtifactSHA256, lastSequence: baselineOffer.acceptedSequence)
            guard update.manifest.object?["source_commit"]?.text == index.sourceCommit else {
                throw MixerFailure("release.source-commit", "Candidate manifest differs from the qualified source commit.")
            }

            func result(status: String, reason: String? = nil, receipt: String? = nil) -> ReleaseAssessment.Target {
                .init(platform: platform, status: status, reason: reason, installedRuntime: installed.identity.fingerprint,
                      candidateRuntime: candidate.identity.fingerprint, baselineArtifactSHA256: baseline.artifactSHA256,
                      candidateArtifactSHA256: update.artifactSHA256, behaviorReceiptSHA256: receipt)
            }
            try candidate.requireInstalledGrants(update.capabilityGrants)
            let behavior = try Self.read(target, "behavior.json", limit: 65_536)
            guard baseline.payloadSHA256 != update.payloadSHA256,
                  SourceDigest.sha256(behavior) == pin.behaviorReceiptSHA256 else {
                throw MixerFailure("release.behavior", "Compiled payloads or VM behavior evidence differ from build provenance.")
            }
            let observed = try StrictJSON.decode(Behavior.self, from: behavior, maximumBytes: 65_536)
            guard observed.baseline.proves(review: false, binding: baselineOffer),
                  observed.candidate.proves(review: true, binding: candidateOffer),
                  observed.baseline.workspaceSHA256.first == observed.candidate.workspaceSHA256.first else {
                throw MixerFailure("release.behavior", "Owned VM observations do not establish persisted confirmation for this target's signed offers.")
            }
            if platform == "ios" {
                try Self.verifyAppleHost(target, variant: "baseline", observed: observed.baseline)
                try Self.verifyAppleHost(target, variant: "candidate", observed: observed.candidate)
            }
            if pin.installed.permissionsSHA256 != pin.proposed.permissionsSHA256 {
                return result(status: "store-build-required", reason: "Effective native permissions changed in the packaged build.")
            }
            if installed.identity.fingerprint != candidate.identity.fingerprint || pin.installed != pin.proposed {
                return result(status: "store-build-required", reason: "The packaged candidate requires a different native build.")
            }
            return result(status: "ota-compatible", receipt: pin.behaviorReceiptSHA256)
        } catch {
            let reason: String
            if let failure = error as? MixerFailure {
                reason = "\(failure.code) \(failure.description)"
            } else if let failure = error as? UpdateError {
                reason = failure.code
            } else {
                reason = "release.invalid-evidence"
            }
            return .init(platform: platform, status: "blocked", reason: reason, installedRuntime: nil, candidateRuntime: nil,
                         baselineArtifactSHA256: nil, candidateArtifactSHA256: nil, behaviorReceiptSHA256: nil)
        }
    }

    private static func verifyAppleHost(_ target: URL, variant: String, observed: Behavior.Observation) throws {
        let bytes = try read(target, variant + ".host-observation.json", limit: 4096)
        let binding = try StrictJSON.decode(OfferBinding.self, from: bytes, maximumBytes: 4096)
        let host = try StrictJSON.decode(AppleHostObservation.self, from: bytes, maximumBytes: 4096)
        let statuses = variant == "baseline" ? ["Open", "Completed"] : ["Open", "Review required", "Completed"]
        guard observed.hostObservationSHA256 == SourceDigest.sha256(bytes), binding == observed.offer,
              host.ownerRetired, isSHA256(host.candidateID),
              host.frames.map(\.revision) == (1...statuses.count).map(UInt64.init),
              host.frames.map(\.status) == statuses, host.frames.map(\.label) == observed.labels,
              host.frames.allSatisfy({ $0.actionID == "task.action" && $0.childIDs == ["status", "toggle"] }) else {
            throw MixerFailure("release.behavior", "Apple host observations do not bind the iOS action and tree to this signed offer.")
        }
    }

    static func read(_ directory: URL, _ file: String, limit: Int = 65_536) throws -> Data {
        try VerificationFile.read(directory.appendingPathComponent(file), maximumBytes: limit)
    }
}

private struct RuntimeMaterial {
    private struct Grant: Decodable {
        let capability_id: String
        let schema_sha256: String
        let permissions: Set<String>
        let origins: Set<String>
        let methods: Set<String>
        let namespaces: Set<String>
    }

    let identity: CapabilityRuntimeIdentity
    let verifier: ReleaseVerifierV3
    private let installedGrants: [String: Grant]
    var bundleID: String? { identity.descriptor.object?["application"]?.object?["bundle_id"]?.text }

    init(_ directory: URL, pin: String) throws {
        let descriptor = try ReleaseQualification.read(directory, "identity.json", limit: CapabilityRuntimeIdentity.maximumDescriptorBytes)
        guard SourceDigest.sha256(descriptor) == pin else {
            throw MixerFailure("release.identity-pin", "Runtime descriptor differs from the independently pinned installed identity.")
        }
        let identity = try CapabilityRuntimeIdentity(json: descriptor)
        try Self.requireGuestUI(identity)
        let roots = try Self.material(directory, "roots.json", digest: identity.descriptor.object?["build"]?.object?["trust_roots_sha256"]?.text)
        _ = try Self.material(directory, "bridge.json", digest: identity.capabilityExecution.bridgePolicySHA256)
        let schemas = [CapabilitySchemas.httpID: CapabilitySchemas.httpSHA256, CapabilitySchemas.storageID: CapabilitySchemas.storageSHA256]
        var grants: [String: Grant] = [:]
        for capability in identity.capabilities {
            guard schemas[capability.id] == capability.schemaSHA256, capability.nativeSHA256 == CapabilityNativeIdentity.sha256 else {
                throw MixerFailure("release.capability-schema", "Installed capability schema or native ABI is outside the linked SDK contract.")
            }
            _ = try Self.material(directory, "configuration." + capability.id + ".json", digest: capability.configurationSHA256)
            let grant = try Self.material(directory, "grant." + capability.id + ".json", digest: capability.grantsSHA256)
            let decoded = try StrictJSON.decode(Grant.self, from: grant, maximumBytes: 65_536)
            guard decoded.capability_id == capability.id, decoded.schema_sha256 == capability.schemaSHA256 else {
                throw MixerFailure("release.grant-binding", "Installed grant does not bind its capability schema.")
            }
            grants[capability.id] = decoded
        }
        self.identity = identity
        self.verifier = try ReleaseVerifierV3(host: identity.installedRuntime,
            roots: StrictJSON.decode([TrustRoot].self, from: roots, maximumBytes: 65_536))
        self.installedGrants = grants
    }

    private static func requireGuestUI(_ identity: CapabilityRuntimeIdentity) throws {
        guard identity.execution.startupExport == GuestUIProtocolV1.startupExport,
              case let .array(dependencies) = identity.descriptor.object?["dependencies"] else {
            throw MixerFailure("release.guest-ui-abi", "Installed runtime does not declare the supported Guest UI ABI.")
        }
        let pins = [
            "mixer.guest-ui-event-v1": GuestUIProtocolV1.contractSHA256,
            "mixer.guest-ui-native-header-v1": GuestUIProtocolV1.nativeHeaderSHA256,
        ]
        for (id, digest) in pins {
            let fields = dependencies.first { $0.object?["id"]?.text == id }?.object
            guard fields?["version"]?.text == "1", fields?["artifact_sha256"]?.text == digest else {
                throw MixerFailure("release.guest-ui-abi", "Installed Guest UI ABI dependency differs from the linked SDK.")
            }
        }
    }

    func firstMissingGrant(_ grants: VerifiedCapabilityGrantsV3) -> String? {
        grants.entries.first { requested in
            guard let installed = installedGrants[requested.capabilityID] else { return true }
            return !installed.permissions.isSuperset(of: requested.permissions) ||
                !installed.origins.isSuperset(of: requested.origins) ||
                !installed.methods.isSuperset(of: requested.methods) ||
                !installed.namespaces.isSuperset(of: requested.namespaces)
        }?.capabilityID
    }

    func requireInstalledGrants(_ grants: VerifiedCapabilityGrantsV3) throws {
        guard firstMissingGrant(grants) == nil else {
            throw MixerFailure("release.grant-scope", "Artifact requests grants beyond its bound native material.")
        }
    }

    private static func material(_ directory: URL, _ file: String, digest: String?) throws -> Data {
        let bytes = try ReleaseQualification.read(directory, file)
        guard SourceDigest.sha256(bytes) == digest else {
            throw MixerFailure("release.material-pin", "Public capability or trust material differs from the pinned identity.")
        }
        return bytes
    }
}
