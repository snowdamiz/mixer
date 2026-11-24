import Foundation
import MixerUI
import MixerUpdates

private func check(_ condition: Bool, _ label: String) throws {
    guard condition else { throw UpdateError("replay.assertion", label) }
}

private func expectRejection<E: Error & Equatable>(_ label: String, _ expected: E, _ attempt: () throws -> Void) throws {
    do {
        try attempt()
    } catch let actual as E where actual == expected {
        return
    }
    throw UpdateError("replay.assertion", "Unexpected acceptance of \(label)")
}

@main
struct NativeMapReplay {
    @MainActor static func main() throws {
        guard let sourceRevision = CommandLine.arguments.dropFirst().first else {
            throw UpdateError("replay.arguments", "Expected the source revision from replay.sh")
        }
        let signer = SignedFixture()
        let provider = OfflineMapProvider()
        let registry = try InstalledMapRegistry(makeSurface: provider.makeSurface)
        let nodeIdentity = UINodeIdentity(id: "project-site-map", generation: 1)
        let host = try MapIslandHost(scope: SignedFixture.scope, roots: [signer.root],
                                     identity: nodeIdentity, registry: registry)

        let digest = registry.schemaSHA256
        let mapGrant = [ProjectSiteMapSchema.id: digest]
        let changed = PlacementFixture(schema: digest)
        let initial = PlacementFixture(schema: digest, slot: .aboveDetails,
                                       latitude: "37.774900", longitude: "-122.419400", style: .standard)

        func sign(_ bytes: Data, using signingFixture: SignedFixture = signer) throws -> Data {
            try signingFixture.sign(bytes, for: host.installedRuntime, sourceRevision: sourceRevision)
        }
        func apply(_ fixture: PlacementFixture, grants: [String: String]) throws {
            let bytes = try fixture.encode(grants: grants)
            try host.apply(signedManifest: sign(bytes), payload: bytes, now: SignedFixture.now)
        }
        func rejections() throws {
            var unknown = changed
            unknown.islandID = "fieldlog.other-map"
            try expectRejection("signed unknown island", MapPlacementError.unknownIsland) {
                try apply(unknown, grants: [unknown.islandID: digest])
            }
            try expectRejection("installed island missing from the signed release grant table", MapPlacementError.ungrantedIsland) {
                try apply(changed, grants: [:])
            }
            let wrongDigest = String(repeating: "0", count: 64)
            try expectRejection("grant hash disagrees with the installed schema", MapPlacementError.schemaMismatch) {
                try apply(changed, grants: [ProjectSiteMapSchema.id: wrongDigest])
            }
            var wrongSchema = changed
            wrongSchema.schema = wrongDigest
            try expectRejection("placement hash disagrees with the installed schema", MapPlacementError.schemaMismatch) {
                try apply(wrongSchema, grants: mapGrant)
            }
            var wrongVersion = changed
            wrongVersion.placementVersion += 1
            try expectRejection("placement version is unsupported", MapPlacementError.unsupportedPlacementVersion) {
                try apply(wrongVersion, grants: mapGrant)
            }
            let invalidCoordinates = [
                ("90.000001", "-74"), ("40", "-180.000001"), ("NaN", "-74"), ("40", "Infinity"),
            ]
            for (latitude, longitude) in invalidCoordinates {
                var invalid = changed
                invalid.latitude = latitude
                invalid.longitude = longitude
                try expectRejection("invalid coordinate \(latitude), \(longitude)", MapPlacementError.invalidCoordinates) {
                    try apply(invalid, grants: mapGrant)
                }
            }
            let granted = try changed.encode(grants: mapGrant)
            let omitted = try changed.encode(grants: [:])
            let signedOmission = try sign(omitted)
            do {
                try host.apply(signedManifest: signedOmission, payload: granted, now: SignedFixture.now)
                throw UpdateError("replay.assertion", "Accepted a grant inserted after signing")
            } catch let error as UpdateError where error.code == "v3.payload.integrity" {}
            var movedAfterSigning = changed
            movedAfterSigning.latitude = "41.689200"
            let tampered = try movedAfterSigning.encode(grants: mapGrant)
            try check(granted.count == tampered.count, "Coordinate tamper must preserve payload length")
            do {
                try host.apply(signedManifest: sign(granted), payload: tampered, now: SignedFixture.now)
                throw UpdateError("replay.assertion", "Accepted a coordinate changed after signing")
            } catch let error as UpdateError where error.code == "v3.payload.integrity" {}
            let wrongAuthority = try sign(granted, using: SignedFixture())
            do {
                try host.apply(signedManifest: wrongAuthority, payload: granted, now: SignedFixture.now)
                throw UpdateError("replay.assertion", "Accepted release signed by an unpinned key")
            } catch let error as UpdateError where error.code == "v3.signature.invalid" {}
        }

        try rejections()
        try check(provider.surfaces.isEmpty && host.acceptedPlacement == nil, "A rejection invoked the cold factory")
        print("PASS cold refusals: unknown, missing grant, grant and node schema mismatch, version, coordinates, tamper, unpinned signer")

        try apply(initial, grants: mapGrant)
        guard let mounted = provider.surfaces.first else { throw UpdateError("replay.assertion", "Factory never mounted a map") }
        try check(mounted.placements.count == 1, "Initial placement did not reach the provider")
        try checkPlacement(mounted.placements[0], initial, identity: nodeIdentity)

        try apply(changed, grants: mapGrant)
        try check(provider.surfaces.count == 1 && provider.surfaces[0] === mounted && mounted.placements.count == 2,
                  "Update replaced the native island or failed to reach it")
        try checkPlacement(mounted.placements[1], changed, identity: nodeIdentity)
        print("PASS signed site, slot, and style change reused one provider surface and node identity")

        try rejections()
        try check(provider.surfaces.count == 1 && provider.surfaces[0] === mounted && mounted.placements.count == 2,
                  "A rejection invoked the factory or touched the mounted surface")
        try checkPlacement(host.acceptedPlacement, changed, identity: nodeIdentity)
        print("PASS warm refusals preserved the provider and last accepted placement")
        print("Installed map schema SHA-256 \(digest)")
    }

    private static func checkPlacement(_ placement: ProjectSiteMapPlacement?, _ fixture: PlacementFixture,
                                       identity: UINodeIdentity) throws {
        try check(placement?.identity == identity && placement?.slot == fixture.slot && placement?.style == fixture.style &&
                  placement?.coordinate.latitude == Double(fixture.latitude) &&
                  placement?.coordinate.longitude == Double(fixture.longitude), "Placement differs from the signed site")
    }
}
