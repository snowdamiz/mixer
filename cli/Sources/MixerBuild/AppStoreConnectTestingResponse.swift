import Foundation

// Sparse GET /v1/builds/{id}; fields[buildBetaDetails] includes inverse build linkage.
struct ASCTestingResponse: Decodable {
    struct Linkage: Decodable { let type: String; let id: String }
    struct Relationship: Decodable {
        let data: Linkage?
        enum CodingKeys: String, CodingKey { case data }
        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            guard c.contains(.data) else { throw StoreQueryFailure.identityMismatch }
            data = try c.decodeIfPresent(Linkage.self, forKey: .data)
        }
    }
    struct Build: Decodable {
        struct Attributes: Decodable { let version: String; let processingState: String; let expired: Bool? }
        struct Relationships: Decodable { let app: Relationship; let buildBetaDetail: Relationship? }
        let type: String; let id: String; let attributes: Attributes; let relationships: Relationships
    }
    struct Included: Decodable {
        struct Attributes: Decodable { let bundleId: String?; let internalBuildState: String?; let externalBuildState: String? }
        struct Relationships: Decodable { let build: Relationship? }
        let type: String; let id: String; let attributes: Attributes?; let relationships: Relationships?
    }
    let data: Build
    let included: [Included]
    static func value(_ bytes: Data, buildID: String, appID: String, bundleID: String, token: String) throws -> StoreBuildObservation.ProviderValue {
        let response = try JSONDecoder().decode(Self.self, from: bytes)
        let build = response.data
        guard build.type == "builds", build.id == buildID, let appLink = build.relationships.app.data,
              appLink.type == "apps", appLink.id == appID else { throw StoreQueryFailure.identityMismatch }
        guard response.included.allSatisfy({ ["apps", "buildBetaDetails"].contains($0.type) }) else { throw StoreQueryFailure.identityMismatch }
        let apps = response.included.filter { $0.type == "apps" }, betas = response.included.filter { $0.type == "buildBetaDetails" }
        guard apps.count == 1, let app = apps.first, app.id == appID, app.attributes?.bundleId == bundleID, betas.count <= 1 else { throw StoreQueryFailure.identityMismatch }
        let internalState: String?, externalState: String?
        if let link = build.relationships.buildBetaDetail?.data {
            guard link.type == "buildBetaDetails", !link.id.isEmpty, link.id.utf8.count <= 200,
                  !link.id.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }),
                  let beta = betas.first, beta.id == link.id,
                  let inverse = beta.relationships?.build?.data, inverse.type == "builds", inverse.id == buildID else { throw StoreQueryFailure.identityMismatch }
            guard ![link.id, beta.id, inverse.id].contains(where: { $0.contains(token) }) else { throw StoreQueryFailure.redactedResponse }
            internalState = beta.attributes?.internalBuildState; externalState = beta.attributes?.externalBuildState
        } else {
            guard betas.isEmpty else { throw StoreQueryFailure.identityMismatch }
            internalState = nil; externalState = nil
        }
        let testing = StoreTestingValue(expired: build.attributes.expired, internalBuildState: internalState, externalBuildState: externalState)
        let version = build.attributes.version, state = build.attributes.processingState
        guard !version.isEmpty, version.utf8.count <= 256, !version.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }),
              StoreTestingValue.validState(state), testing.valid else { throw StoreQueryFailure.malformedResponse }
        guard !([version, state, app.id, bundleID, build.id] + testing.rawStates).contains(where: { $0.contains(token) }) else { throw StoreQueryFailure.redactedResponse }
        return .init(version: version, processingState: state, testing: testing)
    }
}
