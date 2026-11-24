import Foundation
import MixerUI
import MixerUpdates

private struct SignedPlacement: Encodable {
    let signedManifest: Data
    let payload: Data
}

private struct ReplayStep: Encodable {
    let name: String
    let artifact: SignedPlacement
    let refusalCode: String?
    let acceptedStep: String?
    let applyCount: Int
}

private struct ReplayVectors: Encodable {
    let version = 1
    let installedRuntime: InstalledRuntime
    let trustRoot: TrustRoot
    let now: UInt64
    let islandID: String
    let schemaSHA256: String
    let nodeID: String
    let nodeGeneration: UInt64
    let steps: [ReplayStep]
}

private func check(_ condition: Bool, _ label: String) throws {
    guard condition else { throw UpdateError("replay.assertion", label) }
}

private func placementCode(_ error: MapPlacementError) -> String {
    "placement.\(error)"
}

@main
struct NativeMapReplay {
    @MainActor static func main() throws {
        let arguments = Array(CommandLine.arguments.dropFirst())
        guard arguments.count == 1 || (arguments.count == 3 && arguments[1] == "--android-vectors") else {
            throw UpdateError("replay.arguments", "Expected source revision and optional --android-vectors PATH")
        }

        let ios = try run(scope: SignedFixture.scope, sourceRevision: arguments[0])
        if arguments.count == 3 {
            guard let iosMount = ios.steps.first(where: { $0.name == "mount" }) else {
                throw UpdateError("replay.assertion", "Missing admitted iOS mount")
            }
            let android = try run(scope: SignedFixture.androidScope, sourceRevision: arguments[0],
                                  wrongPlatform: iosMount.artifact)
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            let bytes = try encoder.encode(android)
            try bytes.write(to: URL(fileURLWithPath: arguments[2]), options: .withoutOverwriting)
            print("Android fixture vectors SHA-256 \(ReleaseVerifier.sha256(bytes))")
        }
    }

    @MainActor
    private static func run(scope: UpdateScope, sourceRevision: String,
                            wrongPlatform: SignedPlacement? = nil) throws -> ReplayVectors {
        let signer = SignedFixture(scope: scope)
        let provider = OfflineMapProvider()
        let registry = try InstalledMapRegistry(makeSurface: provider.makeSurface)
        let nodeIdentity = UINodeIdentity(id: "project-site-map", generation: 1)
        let host = try MapIslandHost(scope: scope, roots: [signer.root], identity: nodeIdentity, registry: registry)

        let digest = registry.schemaSHA256
        let mapGrant = [ProjectSiteMapSchema.id: digest]
        let initial = PlacementFixture(schema: digest, slot: .aboveDetails,
                                       latitude: "37.774900", longitude: "-122.419400", style: .standard)
        let changed = PlacementFixture(schema: digest)
        let refused = PlacementFixture(schema: digest, slot: .aboveDetails,
                                       latitude: "51.500700", longitude: "-0.124600", style: .standard)

        func signed(_ payload: Data, using fixture: SignedFixture = signer) throws -> SignedPlacement {
            .init(signedManifest: try fixture.sign(payload, for: host.installedRuntime, sourceRevision: sourceRevision),
                  payload: payload)
        }
        func signed(_ placement: PlacementFixture, grants: [String: String] = mapGrant) throws -> SignedPlacement {
            try signed(placement.encode(grants: grants))
        }

        var steps: [ReplayStep] = []
        var mounted: OfflineMapSurface?
        var applyCount = 0
        var accepted: (step: String, frame: PlacementFixture)?

        func submit(_ name: String, _ artifact: SignedPlacement, refusal: String? = nil,
                    accepting frame: PlacementFixture? = nil) throws {
            var actualRefusal: String?
            do {
                try host.apply(signedManifest: artifact.signedManifest, payload: artifact.payload, now: SignedFixture.now)
            } catch let error as MapPlacementError {
                actualRefusal = placementCode(error)
            } catch let error as UpdateError {
                actualRefusal = error.code
            }
            try check(actualRefusal == refusal,
                      "\(name): expected \(refusal ?? "acceptance"), got \(actualRefusal ?? "acceptance")")

            if let frame {
                accepted = (name, frame)
                applyCount += 1
                mounted = mounted ?? provider.surfaces.first
            }
            if let accepted, let mounted {
                try check(provider.surfaces.count == 1 && provider.surfaces.first === mounted &&
                          mounted.placements.count == applyCount, "\(name): provider identity or apply count changed")
                try checkPlacement(mounted.placements.last, accepted.frame, identity: nodeIdentity, step: name)
                try checkPlacement(host.acceptedPlacement, accepted.frame, identity: nodeIdentity, step: name)
            } else {
                try check(applyCount == 0 && provider.surfaces.isEmpty && host.acceptedPlacement == nil,
                          "\(name): unexpected cold mount or missing accepted surface")
            }
            steps.append(.init(name: name, artifact: artifact, refusalCode: refusal,
                               acceptedStep: accepted?.step, applyCount: applyCount))
        }

        var unknown = refused
        unknown.islandID = "fieldlog.other-map"
        let otherGrant = [unknown.islandID: digest]
        let wrongDigest = String(repeating: "0", count: 64)
        var wrongSchema = refused
        wrongSchema.schema = wrongDigest
        var wrongNodeVersion = refused
        wrongNodeVersion.placementVersion += 1
        var wrongGrantManifestVersion = refused
        wrongGrantManifestVersion.manifestVersion += 1

        var denials: [(name: String, artifact: SignedPlacement, code: String)] = try [
            ("unknown-island", signed(unknown, grants: otherGrant), placementCode(.unknownIsland)),
            ("missing-grant", signed(refused, grants: [:]), placementCode(.ungrantedIsland)),
            ("grant-for-other-id", signed(refused, grants: otherGrant), placementCode(.ungrantedIsland)),
            ("grant-schema", signed(refused, grants: [ProjectSiteMapSchema.id: wrongDigest]), placementCode(.schemaMismatch)),
            ("node-schema", signed(wrongSchema), placementCode(.schemaMismatch)),
            ("node-version", signed(wrongNodeVersion), placementCode(.unsupportedPlacementVersion)),
            ("grant-manifest-version", signed(wrongGrantManifestVersion), placementCode(.unsupportedManifestVersion)),
        ]
        let invalidCoordinates = [
            ("90.000001", "-74"), ("40", "-180.000001"), ("NaN", "-74"), ("40", "Infinity"),
        ]
        for (index, (latitude, longitude)) in invalidCoordinates.enumerated() {
            var invalid = refused
            invalid.latitude = latitude
            invalid.longitude = longitude
            denials.append(("invalid-coordinate-\(index + 1)", try signed(invalid), placementCode(.invalidCoordinates)))
        }

        let granted = try signed(refused)
        let omission = try signed(refused, grants: [:])
        denials.append(("grant-inserted-after-signing",
                        .init(signedManifest: omission.signedManifest, payload: granted.payload), "v3.payload.integrity"))
        var edited = refused
        edited.latitude = "52.500700"
        let editedPayload = try edited.encode(grants: mapGrant)
        try check(granted.payload.count == editedPayload.count, "Coordinate edit must preserve payload length")
        denials.append(("coordinate-edited-after-signing",
                        .init(signedManifest: granted.signedManifest, payload: editedPayload), "v3.payload.integrity"))
        let unpinned = try signed(granted.payload, using: SignedFixture(scope: scope))
        denials.append(("unpinned-signer", unpinned, "v3.signature.invalid"))
        if let wrongPlatform {
            denials.append(("wrong-platform", wrongPlatform, "v3.manifest.compatibility"))
        }

        for denial in denials {
            try submit("cold-\(denial.name)", denial.artifact, refusal: denial.code)
        }
        try submit("mount", signed(initial), accepting: initial)
        try submit("move", signed(changed), accepting: changed)
        for denial in denials {
            try submit("warm-\(denial.name)", denial.artifact, refusal: denial.code)
        }
        print("PASS \(scope.platform)-scoped Swift host: \(denials.count) cold refusals, mount and move on one surface, \(denials.count) warm refusals preserving the accepted frame")
        print("Installed map schema SHA-256 \(digest)")

        return .init(installedRuntime: host.installedRuntime, trustRoot: signer.root, now: SignedFixture.now,
                     islandID: ProjectSiteMapSchema.id, schemaSHA256: digest, nodeID: nodeIdentity.id,
                     nodeGeneration: nodeIdentity.generation, steps: steps)
    }

    private static func checkPlacement(_ placement: ProjectSiteMapPlacement?, _ fixture: PlacementFixture,
                                       identity: UINodeIdentity, step: String) throws {
        try check(placement?.identity == identity && placement?.slot == fixture.slot && placement?.style == fixture.style &&
                  placement?.coordinate.latitude == Double(fixture.latitude) &&
                  placement?.coordinate.longitude == Double(fixture.longitude), "\(step): placement differs from accepted frame")
    }
}
