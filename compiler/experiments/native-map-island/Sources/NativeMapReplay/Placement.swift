import CoreLocation
import Foundation
import MixerUI
import MixerUpdates

enum ProjectSiteMapSlot: String, CaseIterable {
    case aboveDetails, belowDetails
}

enum ProjectSiteMapStyle: String, CaseIterable {
    case standard, satellite
}

struct ProjectSiteMapPlacement {
    let identity: UINodeIdentity
    let slot: ProjectSiteMapSlot
    let coordinate: CLLocationCoordinate2D
    let style: ProjectSiteMapStyle
}

enum MapPlacementError: Error, Equatable {
    case malformed
    case unsupportedManifestVersion
    case unsupportedPlacementVersion
    case unknownIsland
    case ungrantedIsland
    case schemaMismatch
    case invalidCoordinates
    case invalidProperties
}

enum ProjectSiteMapSchema {
    static let id = "fieldlog.project-site-map"
    static let version: UInt64 = 1

    static func digest() throws -> String {
        let descriptor = CanonicalValue.object([
            "island_id": .text(id),
            "version": .uint(version),
            "slots": .array(ProjectSiteMapSlot.allCases.map { .text($0.rawValue) }),
            "properties": .object([
                "latitude_degrees": .text("decimal string with up to six fractional digits, inclusive -90...90"),
                "longitude_degrees": .text("decimal string with up to six fractional digits, inclusive -180...180"),
                "style": .array(ProjectSiteMapStyle.allCases.map { .text($0.rawValue) }),
            ]),
            "events": .array([]),
        ])
        return ReleaseVerifier.sha256(try descriptor.canonicalCBOR())
    }
}

private struct MapIslandRelease {
    static let maximumBytes = 4_096

    let grants: [String: CanonicalValue]
    let placement: [String: CanonicalValue]

    // Called only on the snapshot authenticated by the installed verifier.
    init(verifiedPayload: Data) throws {
        let value = try StrictJSON.decode(CanonicalValue.self, from: verifiedPayload, maximumBytes: Self.maximumBytes)
        guard let fields = value.object, Set(fields.keys) == ["schema", "island_grants", "placement"],
              let grants = fields["island_grants"]?.object, grants.count <= 1,
              let placement = fields["placement"]?.object,
              Set(placement.keys) == ["version", "island_id", "schema_sha256", "slot", "properties"] else {
            throw MapPlacementError.malformed
        }
        guard fields["schema"]?.uint == 1 else { throw MapPlacementError.unsupportedManifestVersion }
        guard placement["version"]?.uint == ProjectSiteMapSchema.version else {
            throw MapPlacementError.unsupportedPlacementVersion
        }
        self.grants = grants
        self.placement = placement
    }
}

@MainActor
protocol ProjectSiteMapSurface: AnyObject {
    func apply(_ placement: ProjectSiteMapPlacement)
}

// Constructed by the installed app. The release cannot add registrations or factories.
@MainActor
struct InstalledMapRegistry {
    let schemaSHA256: String
    let makeSurface: () -> any ProjectSiteMapSurface

    init(makeSurface: @escaping () -> any ProjectSiteMapSurface) throws {
        schemaSHA256 = try ProjectSiteMapSchema.digest()
        self.makeSurface = makeSurface
    }

    fileprivate func authorize(_ release: MapIslandRelease, identity: UINodeIdentity) throws -> ProjectSiteMapPlacement {
        let node = release.placement
        guard let id = node["island_id"]?.text, id.utf8.elementsEqual(ProjectSiteMapSchema.id.utf8) else {
            throw MapPlacementError.unknownIsland
        }
        guard let grant = release.grants[id] else { throw MapPlacementError.ungrantedIsland }
        guard grant.text == schemaSHA256, node["schema_sha256"]?.text == schemaSHA256 else {
            throw MapPlacementError.schemaMismatch
        }
        guard let properties = node["properties"]?.object,
              Set(properties.keys) == ["latitude_degrees", "longitude_degrees", "style"],
              let slot = node["slot"]?.text.flatMap(ProjectSiteMapSlot.init(rawValue:)),
              let style = properties["style"]?.text.flatMap(ProjectSiteMapStyle.init(rawValue:)) else {
            throw MapPlacementError.invalidProperties
        }
        guard let latitude = properties["latitude_degrees"].flatMap(Self.degrees),
              let longitude = properties["longitude_degrees"].flatMap(Self.degrees) else {
            throw MapPlacementError.invalidCoordinates
        }
        let coordinate = CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
        guard CLLocationCoordinate2DIsValid(coordinate) else { throw MapPlacementError.invalidCoordinates }
        return .init(identity: identity, slot: slot, coordinate: coordinate, style: style)
    }

    private static func degrees(_ value: CanonicalValue) -> Double? {
        guard let text = value.text, text.utf8.count <= 11,
              text.wholeMatch(of: /-?(0|[1-9][0-9]{0,2})(\.[0-9]{1,6})?/) != nil,
              let degrees = Double(text), degrees.isFinite else { return nil }
        return degrees
    }
}

@MainActor
final class MapIslandHost {
    let installedRuntime: InstalledRuntime
    private let verifier: ReleaseVerifierV3
    private let registry: InstalledMapRegistry
    private let identity: UINodeIdentity
    private var surface: (any ProjectSiteMapSurface)?
    private(set) var acceptedPlacement: ProjectSiteMapPlacement?

    init(scope: UpdateScope, roots: [TrustRoot], identity: UINodeIdentity, registry: InstalledMapRegistry) throws {
        let registryFingerprint = CanonicalValue.object([
            "experiment": .text("fieldlog-map-island-v1"),
            ProjectSiteMapSchema.id: .text(registry.schemaSHA256),
        ])
        installedRuntime = InstalledRuntime(scope: scope,
            runtime: ReleaseVerifier.sha256(try registryFingerprint.canonicalCBOR()),
            protocolVersion: 3, guestABI: 2, capabilityHashes: [:], stateVersion: 0,
            maxPayloadBytes: UInt64(MapIslandRelease.maximumBytes),
            limits: .init(memoryBytes: 65_536, fuel: 1_000, startupMilliseconds: 1_000))
        verifier = try ReleaseVerifierV3(host: installedRuntime, roots: roots)
        self.identity = identity
        self.registry = registry
    }

    func apply(signedManifest: Data, payload: Data, now: UInt64) throws {
        guard payload.count <= MapIslandRelease.maximumBytes else { throw MapPlacementError.malformed }
        let snapshot = payload.withUnsafeBytes { Data($0) }
        _ = try verifier.verifyArtifact(signedManifest: signedManifest, payload: snapshot, now: now)
        let release = try MapIslandRelease(verifiedPayload: snapshot)
        let placement = try registry.authorize(release, identity: identity)

        let mounted = surface ?? registry.makeSurface()
        mounted.apply(placement)
        surface = mounted
        acceptedPlacement = placement
    }
}
