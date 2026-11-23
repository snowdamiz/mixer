
struct WitnessDelivery: Decodable {
    let offerSHA256: String
    let envelopeSHA256: String
    let payloadSHA256: String
    let payloadBytes: Int
    let artifact: String
    let sequence: UInt64

    private struct Offer: Decodable {
        let artifact_url: String
    }

    private struct Payload: Decodable {
        let payload: Data
    }

    @MainActor func stage(_ owner: CapabilityGuestUIRuntime, descriptor: CapabilityRuntimeIdentity, port: UInt16) async throws {
        let scope = descriptor.installedRuntime.scope
        let tenant = "organization=\(scope.organization)&project=\(scope.project)"
        let query = "/v3/updates?\(tenant)&app=\(scope.app)&environment=\(scope.environment)&platform=\(scope.platform)"
            + "&runtime=\(descriptor.fingerprint)&channel=beta&installation=\(WitnessInput.installation)"
        let path = "/v3/artifacts/\(artifact)?\(tenant)"
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 4
        config.urlCache = nil
        let session = URLSession(configuration: config)
        defer { session.invalidateAndCancel() }
        func fetch(_ path: String, digest: String) async throws -> Data {
            let url = try need(URL(string: "http://127.0.0.1:\(port)" + path), "Loopback URL")
            let (data, response) = try await session.data(from: url)
            try check((response as? HTTPURLResponse)?.statusCode == 200 && response.url == url
                && data.count <= 65_536 && ReleaseVerifier.sha256(data) == digest, "Stock wire mismatch for \(path)")
            return data
        }
        let offer = try await fetch(query, digest: offerSHA256)
        try check(JSONDecoder().decode(Offer.self, from: offer).artifact_url == path, "Stock artifact path")
        let envelope = try await fetch(path, digest: envelopeSHA256)
        let payload = try JSONDecoder().decode(Payload.self, from: envelope).payload
        try check(payload.count == payloadBytes && ReleaseVerifier.sha256(payload) == payloadSHA256, "Stock Wasm bytes")
        func signed(_ name: String, _ data: Data) throws -> Data {
            let object = try JSONSerialization.jsonObject(with: data) as? [String: Any]
            return try JSONSerialization.data(withJSONObject: need(object?[name], "Missing \(name)"))
        }
        try await owner.beginDownload(signedManifest: signed("signed_manifest", envelope),
                                      signedAssignment: signed("signed_assignment", offer))
        try await owner.appendDownload(payload, atOffset: 0)
        try await owner.finishDownload()
    }
}

struct ReleaseObservation: Codable {
    let candidate: String
    let launch: String
    let pid: Int32
}
