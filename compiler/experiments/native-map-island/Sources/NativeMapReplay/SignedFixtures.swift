import CryptoKit
import Foundation
import MixerUpdates

struct SignedFixture {
    static let scope = fieldLogScope(platform: "ios")
    static let androidScope = fieldLogScope(platform: "android")
    static let now: UInt64 = 100
    private let scope: UpdateScope
    private let key = Curve25519.Signing.PrivateKey()

    init(scope: UpdateScope = SignedFixture.scope) {
        self.scope = scope
    }

    var root: TrustRoot {
        .init(keyID: "map-replay", publicKey: key.publicKey.rawRepresentation, scope: scope,
              artifact: true, assignment: false)
    }

    func sign(_ payload: Data, for host: InstalledRuntime, sourceRevision: String) throws -> Data {
        guard host.scope == scope else { throw UpdateError("fixture.scope", "Signer and installed fixture scopes differ") }
        let scope = try StrictJSON.decode(CanonicalValue.self, from: JSONEncoder().encode(self.scope))
        let manifest = CanonicalValue.object([
            "schema": .uint(3), "scope": scope,
            "release_id": .text("fieldlog-map"), "source_commit": .text(sourceRevision),
            "provenance_id": .text("native-map-replay"),
            "runtime": .text(host.runtime), "protocol": .uint(host.protocolVersion),
            "guest_abi": .uint(host.guestABI), "ui_schema": .uint(host.uiSchema),
            "capability_hashes": .object(host.capabilityHashes.mapValues(CanonicalValue.text)),
            "capability_grants": .object([
                "schema": .uint(1), "schema_sha256": .text(VerifiedCapabilityGrantsV3.descriptorSHA256),
                "entries": .array([]),
            ]),
            "state_min": .uint(host.stateVersion), "state_max": .uint(host.stateVersion),
            "payload_sha256": .text(ReleaseVerifier.sha256(payload)),
            "compressed_bytes": .uint(UInt64(payload.count)), "expanded_bytes": .uint(UInt64(payload.count)),
            "compression": .text("none"), "asset_hashes": .object([:]),
            "source_map_sha256": .text(ReleaseVerifier.sha256(Data())),
            "limits": .object([
                "memory_bytes": .uint(host.limits.memoryBytes),
                "fuel": .uint(host.limits.fuel),
                "startup_milliseconds": .uint(host.limits.startupMilliseconds),
            ]),
            "key_id": .text(root.keyID), "created_at_unix": .uint(Self.now),
        ])
        let signature = try key.signature(for: Data("mixer.artifact.v3\0".utf8) + manifest.canonicalCBOR())
        return try JSONEncoder().encode(CanonicalValue.object([
            "manifest": manifest, "signature": .text(signature.base64EncodedString()),
        ]))
    }

    private static func fieldLogScope(platform: String) -> UpdateScope {
        .init(organization: "mixer", project: "fieldlog", app: "fieldlog",
              environment: "development", platform: platform)
    }
}

struct PlacementFixture {
    var manifestVersion: UInt64 = 1
    var islandID = ProjectSiteMapSchema.id
    var placementVersion = ProjectSiteMapSchema.version
    var schema: String
    var slot: ProjectSiteMapSlot = .belowDetails
    var latitude = "40.689200"
    var longitude = "-74.044500"
    var style: ProjectSiteMapStyle = .satellite

    func encode(grants: [String: String]) throws -> Data {
        try JSONEncoder().encode(CanonicalValue.object([
            "schema": .uint(manifestVersion),
            "island_grants": .object(grants.mapValues(CanonicalValue.text)),
            "placement": .object([
                "version": .uint(placementVersion), "island_id": .text(islandID), "schema_sha256": .text(schema),
                "slot": .text(slot.rawValue),
                "properties": .object([
                    "latitude_degrees": .text(latitude), "longitude_degrees": .text(longitude),
                    "style": .text(style.rawValue),
                ]),
            ]),
        ]))
    }
}
