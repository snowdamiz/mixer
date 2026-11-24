import CGC3
import Foundation
import MixerUpdates

private enum Slot: String, CaseIterable {
    case aboveDetails, belowDetails

    var wireValue: Int32 {
        switch self {
        case .aboveDetails: Int32(GC3_ABOVE_DETAILS)
        case .belowDetails: Int32(GC3_BELOW_DETAILS)
        }
    }
}

private enum Style: String, CaseIterable {
    case standard, satellite

    var wireValue: Int32 {
        switch self {
        case .standard: Int32(GC3_STANDARD)
        case .satellite: Int32(GC3_SATELLITE)
        }
    }
}

private enum PlacementRefusal: String, Error {
    case malformed
    case unsupportedManifestVersion
    case unsupportedPlacementVersion
    case unknownIsland
    case ungrantedIsland
    case schemaMismatch
    case invalidProperties
    case invalidCoordinates
}

private struct InstalledMap {
    static let id = "fieldlog.project-site-map"
    static let nodeID = "project-site-map"
    static let nodeGeneration: Int64 = 1
    static let scope = UpdateScope(organization: "mixer", project: "fieldlog", app: "fieldlog",
                                   environment: "development", platform: "android")
    static let version: UInt64 = 1
    let schema: String
    let runtime: InstalledRuntime
    let verifier: ReleaseVerifierV3
    let rootSHA256: String

    init() throws {
        let descriptor = CanonicalValue.object([
            "island_id": .text(Self.id),
            "version": .uint(Self.version),
            "slots": .array(Slot.allCases.map { .text($0.rawValue) }),
            "properties": .object([
                "latitude_degrees": .text("decimal string with up to six fractional digits, inclusive -90...90"),
                "longitude_degrees": .text("decimal string with up to six fractional digits, inclusive -180...180"),
                "style": .array(Style.allCases.map { .text($0.rawValue) }),
            ]),
            "events": .array([]),
        ])
        schema = ReleaseVerifier.sha256(try descriptor.canonicalCBOR())
        let registry = CanonicalValue.object([
            "experiment": .text("fieldlog-map-island-v1"),
            Self.id: .text(schema),
        ])
        runtime = InstalledRuntime(scope: Self.scope, runtime: ReleaseVerifier.sha256(try registry.canonicalCBOR()),
                                   protocolVersion: 3, guestABI: 2, capabilityHashes: [:], stateVersion: 0,
                                   maxPayloadBytes: UInt64(GC3_MAX_PAYLOAD),
                                   limits: .init(memoryBytes: 65_536, fuel: 1_000, startupMilliseconds: 1_000))
        let key = Data(InstalledFixtureRoot.publicKey)
        rootSHA256 = ReleaseVerifier.sha256(key)
        verifier = try ReleaseVerifierV3(host: runtime, roots: [
            TrustRoot(keyID: "map-replay", publicKey: key, scope: Self.scope, artifact: true, assignment: false),
        ])
    }

    // Kept private to ensure the only source of a placement and grant pair is
    // the exact payload snapshot checked under this installed verifier.
    func admit(manifest: Data, payload: Data) throws -> CheckedPlacement {
        let artifact = try verifier.verifyArtifact(signedManifest: manifest, payload: payload, now: 100)
        let document: CanonicalValue
        do {
            document = try StrictJSON.decode(CanonicalValue.self, from: payload, maximumBytes: Int(GC3_MAX_PAYLOAD))
        } catch {
            throw PlacementRefusal.malformed
        }
        guard let fields = document.object, Set(fields.keys) == ["schema", "island_grants", "placement"],
              let grants = fields["island_grants"]?.object, grants.count <= 1,
              let node = fields["placement"]?.object,
              Set(node.keys) == ["version", "island_id", "schema_sha256", "slot", "properties"] else {
            throw PlacementRefusal.malformed
        }
        guard fields["schema"]?.uint == 1 else { throw PlacementRefusal.unsupportedManifestVersion }
        guard node["version"]?.uint == Self.version else { throw PlacementRefusal.unsupportedPlacementVersion }
        guard let id = node["island_id"]?.text, id.utf8.elementsEqual(Self.id.utf8) else {
            throw PlacementRefusal.unknownIsland
        }
        guard let grant = grants.first(where: { $0.key.utf8.elementsEqual(Self.id.utf8) })?.value else {
            throw PlacementRefusal.ungrantedIsland
        }
        guard let grantSchema = grant.text, grantSchema == schema, node["schema_sha256"]?.text == schema else {
            throw PlacementRefusal.schemaMismatch
        }
        guard let properties = node["properties"]?.object,
              Set(properties.keys) == ["latitude_degrees", "longitude_degrees", "style"],
              let slot = node["slot"]?.text.flatMap(Slot.init(rawValue:)),
              let style = properties["style"]?.text.flatMap(Style.init(rawValue:)) else {
            throw PlacementRefusal.invalidProperties
        }
        guard let latitude = Self.degrees(properties["latitude_degrees"], bounds: -90...90),
              let longitude = Self.degrees(properties["longitude_degrees"], bounds: -180...180) else {
            throw PlacementRefusal.invalidCoordinates
        }
        return CheckedPlacement(slot: slot, style: style, latitude: latitude, longitude: longitude,
                                installed: self, releaseGrantSchema: grantSchema, artifact: artifact,
                                signedManifestSHA256: ReleaseVerifier.sha256(manifest))
    }

    private static func degrees(_ value: CanonicalValue?, bounds: ClosedRange<Double>) -> Double? {
        guard let text = value?.text, text.utf8.count <= 11,
              text.wholeMatch(of: /-?(0|[1-9][0-9]{0,2})(\.[0-9]{1,6})?/) != nil,
              let degrees = Double(text), bounds.contains(degrees) else { return nil }
        return degrees
    }
}

private struct CheckedPlacement {
    let slot: Slot
    let style: Style
    let latitude: Double
    let longitude: Double
    let installed: InstalledMap
    let releaseGrantSchema: String
    let artifact: VerifiedArtifactV3
    let signedManifestSHA256: String

    func send(to context: UnsafeMutableRawPointer?, accept: GC3Accept) {
        // Copy the finite set of ASCII strings into buffers borrowed by JNI
        // only during the synchronous callback.
        let strings = [
            InstalledMap.nodeID, InstalledMap.id, installed.runtime.runtime, installed.schema, releaseGrantSchema,
            artifact.releaseID, artifact.artifactSHA256, signedManifestSHA256, artifact.payloadSHA256,
            installed.rootSHA256,
        ].map { string in
            let bytes = string.utf8CString
            let copy = UnsafeMutablePointer<CChar>.allocate(capacity: bytes.count)
            bytes.withUnsafeBufferPointer { copy.initialize(from: $0.baseAddress!, count: $0.count) }
            return copy
        }
        defer { strings.forEach { $0.deallocate() } }
        var placement = GC3MapPlacement(
            slot: slot.wireValue, style: style.wireValue, latitude: latitude, longitude: longitude,
            node_generation: InstalledMap.nodeGeneration,
            node_id: strings[0], island_id: strings[1], installed_runtime: strings[2], installed_schema: strings[3],
            release_grant_schema: strings[4], release_id: strings[5], artifact_sha256: strings[6],
            signed_manifest_sha256: strings[7], payload_sha256: strings[8], root_sha256: strings[9]
        )
        accept(context, &placement)
    }
}

@_cdecl("gc3_map_admit")
public func admitMap(
    _ manifest: UnsafePointer<UInt8>?, _ manifestSize: Int,
    _ payload: UnsafePointer<UInt8>?, _ payloadSize: Int,
    _ context: UnsafeMutableRawPointer?, _ accept: GC3Accept, _ refuse: GC3Refuse
) {
    func reject(_ code: String) { code.withCString { refuse(context, $0) } }
    guard (1...Int(GC3_MAX_MANIFEST)).contains(manifestSize), let manifest else {
        reject("v3.document.size")
        return
    }
    guard (1...Int(GC3_MAX_PAYLOAD)).contains(payloadSize), let payload else {
        reject("placement.malformed")
        return
    }
    do {
        let placement = try InstalledMap().admit(
            manifest: Data(bytes: manifest, count: manifestSize), payload: Data(bytes: payload, count: payloadSize))
        placement.send(to: context, accept: accept)
    } catch let error as PlacementRefusal {
        reject("placement.\(error.rawValue)")
    } catch let error as UpdateError {
        reject(error.code)
    } catch {
        reject("placement.internal")
    }
}
