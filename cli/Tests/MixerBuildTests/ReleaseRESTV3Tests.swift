import Foundation
import MixerUpdates
import Testing
@testable import MixerBuild

@Suite struct ReleaseRESTV3Tests {
    private let project = ReleaseRESTV3.Project(organizationID: "org-a", projectID: "project-a")
    private let prefix = "/v3/orgs/org-a/projects/project-a"
    private let digest = String(repeating: "a", count: 64)
    private let maximum = "18446744073709551615"

    private var signature: String { String(repeating: "A", count: 86) + "==" }

    private func signedJSON(_ field: String, value: String = #"{"schema":3}"#) -> String {
        " \n{\"signature\":\"\(signature)\", \"\(field)\": \(value)} \t\n"
    }

    private func verifyRequest<Response>(
        _ operation: ReleaseV3Operation<Response>, method: String, suffix: String,
        body: String, statuses: Set<Int> = [200], reason: String? = nil
    ) throws {
        let origin = try #require(URL(string: "http://127.0.0.1:12345"))
        let request = operation.urlRequest(origin: origin, token: "test-token")
        let path = prefix + suffix
        #expect(request.url?.absoluteString == "http://127.0.0.1:12345" + path)
        #expect(request.httpMethod == method)
        #expect(request.httpBody == Data(body.utf8))
        #expect(request.value(forHTTPHeaderField: "Content-Type") == "application/json")
        #expect(request.value(forHTTPHeaderField: "Authorization") == "Bearer test-token")
        #expect(request.value(forHTTPHeaderField: "X-Mixer-Reason") == reason)
        let intent = ["mixer-local-release-v3", method, path, reason ?? "", body].joined(separator: "\0")
        #expect(request.value(forHTTPHeaderField: "Idempotency-Key") == SourceDigest.sha256(Data(intent.utf8)))
        #expect(operation.statuses == statuses)
    }

    @Test func allRequestsPreservePinnedBytesAndIdempotency() throws {
        let manifestJSON = signedJSON("manifest")
        let assignmentJSON = signedJSON("assignment")
        let manifest = try ReleaseRESTV3.SignedManifest(Data(manifestJSON.utf8))
        let assignment = try ReleaseRESTV3.SignedAssignment(Data(assignmentJSON.utf8))
        let body = ReleaseRESTV3.AssignmentRequest(signedAssignment: assignment)

        try verifyRequest(
            ReleaseRESTV3.upload(project, manifestSHA256: digest,
                                 body: .init(signedManifest: manifest, payload: Data([0, 255]))),
            method: "PUT", suffix: "/artifacts/" + digest,
            body: "{\"signed_manifest\":\(manifestJSON),\"payload\":\"AP8=\"}", statuses: [200, 201])
        try verifyRequest(
            ReleaseRESTV3.validate(project, body: .init(artifactSHA256: digest)),
            method: "POST", suffix: "/releases/validate",
            body: "{\n  \"artifact_sha256\" : \"\(digest)\"\n}\n")
        let assignmentBody = "{\"signed_assignment\":\(assignmentJSON)}"
        try verifyRequest(
            ReleaseRESTV3.publish(project, channel: "dev", body: body),
            method: "POST", suffix: "/channels/dev/publish", body: assignmentBody)
        try verifyRequest(
            ReleaseRESTV3.promote(project, channel: "dev", body: body),
            method: "POST", suffix: "/channels/dev/promote", body: assignmentBody)
        try verifyRequest(
            ReleaseRESTV3.rollback(project, channel: "dev", body: body, reason: "--validation regression"),
            method: "POST", suffix: "/channels/dev/rollback", body: assignmentBody, reason: "--validation regression")

        let input = "{\"sequence\":9223372036854775808,\"activated\":\(maximum),\"pending\":0,\"adverse_signals\":9007199254740993}"
        let health = try StrictJSON.decode(ReleaseRESTV3.Health.self, from: Data(input.utf8))
        let expectedHealth = """
        {
          "activated" : \(maximum),
          "adverse_signals" : 9007199254740993,
          "pending" : 0,
          "sequence" : 9223372036854775808
        }

        """
        try verifyRequest(
            ReleaseRESTV3.halt(project, channel: "dev", body: .init(health: health, signedAssignment: assignment)),
            method: "POST", suffix: "/channels/dev/halt",
            body: "{\"health\":\(expectedHealth),\"signed_assignment\":\(assignmentJSON)}")
    }

    @Test func strictSignedInputAndRouteComponents() throws {
        let assignment = signedJSON("assignment", value: #"{"schema":3,"sequence":18446744073709551615}"#)
        let body = try ReleaseRESTV3.AssignmentRequest(signedAssignment: .init(Data(assignment.utf8)))
        #expect(body.signedAssignment.value["sequence"]?.uint == UInt64.max)
        #expect(throws: (any Error).self) { try ReleaseRESTV3.SignedManifest(Data(assignment.utf8)) }
        for object in [#"{"schema":3,"\u0073chema":3}"#, #"{"schema":3,"sequence":18446744073709551616}"#, #"{"schema":3.0}"#] {
            #expect(throws: (any Error).self) {
                try ReleaseRESTV3.SignedAssignment(Data(signedJSON("assignment", value: object).utf8))
            }
        }
        for channel in ["..", "dev/other", "dev%2Fother", "dev?query"] {
            #expect(throws: (any Error).self) { try ReleaseRESTV3.publish(project, channel: channel, body: body) }
        }
    }

    @Test func stagePromotionKeepsBothSignedInputsAndFullWidthSequences() throws {
        let iosJSON = signedJSON("assignment", value: #"{"schema":3,"sequence":18446744073709551615}"#)
        let androidJSON = signedJSON("assignment", value: #"{"sequence":9007199254740993,"schema":3}"#)
        let request = try ReleaseRESTV3.StagePromotionRequest(
            sourceIosSequence: .max, sourceAndroidSequence: 9_007_199_254_740_993,
            iosSignedAssignment: .init(Data(iosJSON.utf8)),
            androidSignedAssignment: .init(Data(androidJSON.utf8)))
        let operation = try ReleaseRESTV3.stagePromote(
            project, applicationID: "fieldlog", directionID: "beta-to-prod", body: request, reason: "Reviewed")
        try verifyRequest(
            operation, method: "POST", suffix: "/apps/fieldlog/release-promotions/beta-to-prod",
            body: "{\"source_ios_sequence\":\(maximum),\"source_android_sequence\":9007199254740993," +
                "\"ios_signed_assignment\":\(iosJSON),\"android_signed_assignment\":\(androidJSON)}",
            reason: "Reviewed")
        #expect(throws: (any Error).self) {
            try ReleaseRESTV3.stagePromote(project, applicationID: "fieldlog", directionID: "../other",
                                          body: request, reason: "Reviewed")
        }

        let variant = "{\"sequence\":\(maximum),\"artifact_sha256\":\"\(digest)\",\"rollout_basis_points\":1}"
        let receipt = "{\"ios\":\(variant),\"android\":\(variant),\"delivery\":\"local_only\"}"
        let response = try operation.decodeSuccess(Data(receipt.utf8))
        #expect(response.ios.sequence == UInt64.max)
        #expect(response.android.artifactSHA256 == digest)
        #expect(response.delivery == "local_only")
        for invalid in [receipt.replacingOccurrences(of: maximum, with: "18446744073709551616"),
                        receipt.replacingOccurrences(of: maximum, with: "1e1"),
                        receipt.replacingOccurrences(of: "rollout_basis_points", with: "unexpected")] {
            #expect(throws: (any Error).self) {
                try operation.decodeSuccess(Data(invalid.utf8))
            }
        }
    }

    @Test func typedResponsesPreserveFullWidthAndFieldPolicies() throws {
        let signed = try ReleaseRESTV3.SignedAssignment(Data(signedJSON("assignment").utf8))
        let publish = try ReleaseRESTV3.publish(project, channel: "dev", body: .init(signedAssignment: signed))
        let responsePrefix = "{\"artifact_sha256\":\"\(digest)\",\"rollout_basis_points\":2500,\"delivery\":\"local_only\",\"sequence\":"
        let channel = responsePrefix + maximum + ",\"extension\":{\"n\":1}}"
        #expect(try publish.decodeSuccess(Data(channel.utf8)).sequence == UInt64.max)
        let padded = channel + String(repeating: " ", count: 4096 - channel.utf8.count)
        #expect(try publish.decodeSuccess(Data(padded.utf8)).sequence == UInt64.max)
        #expect(throws: (any Error).self) { try publish.decodeSuccess(Data((padded + " ").utf8)) }

        for invalid in ["18446744073709551616", "-1", "1.0", "1e1", "true", "null", "\"1\"", #"1,"\u0073equence":1"#] {
            #expect(throws: (any Error).self) {
                try publish.decodeSuccess(Data((responsePrefix + invalid + "}").utf8))
            }
        }

        let healthJSON = "{\"sequence\":9223372036854775808,\"activated\":\(maximum),\"pending\":0,\"adverse_signals\":1}"
        let health = try StrictJSON.decode(ReleaseRESTV3.Health.self, from: Data(healthJSON.utf8))
        let halt = try ReleaseRESTV3.halt(project, channel: "dev", body: .init(health: health, signedAssignment: signed))
        let haltPrefix = "{\"scope\":{\"organization\":\"org-a\",\"project\":\"project-a\"},\"runtime\":\"\(digest)\",\"channel\":\"dev\",\"artifact_sha256\":\"\(digest)\",\"halt_sequence\":\(maximum),\"health\":"
        let receipt = try halt.decodeSuccess(Data((haltPrefix + healthJSON + "}").utf8))
        #expect(receipt.haltSequence == UInt64.max)
        #expect(receipt.health == health)
        #expect(receipt.health.activated == UInt64.max)
        #expect(throws: (any Error).self) {
            try halt.decodeSuccess(Data((haltPrefix + healthJSON + ",\"extra\":1}").utf8))
        }
        let extraHealthField = healthJSON.dropLast() + ",\"extra\":1}"
        #expect(throws: (any Error).self) {
            try halt.decodeSuccess(Data((haltPrefix + extraHealthField + "}").utf8))
        }
    }

    @Test func artifactResponsesValidateKnownFlagsAndAllowOtherFields() throws {
        let manifest = try ReleaseRESTV3.SignedManifest(Data(signedJSON("manifest").utf8))
        let upload = try ReleaseRESTV3.upload(
            project, manifestSHA256: digest, body: .init(signedManifest: manifest, payload: Data([0])))
        let validate = try ReleaseRESTV3.validate(project, body: .init(artifactSHA256: digest))
        let prefix = "{\"artifact_sha256\":\"\(digest)\","
        #expect(try upload.decodeSuccess(Data((prefix + #""immutable":true,"extra":1}"#).utf8)).immutable)
        #expect(try validate.decodeSuccess(Data((prefix + #""protocol_valid":true,"mobile_qualified":false}"#).utf8)).protocolValid)
        #expect(throws: (any Error).self) {
            try upload.decodeSuccess(Data((prefix + #""immutable":true,"protocol_valid":1}"#).utf8))
        }
        #expect(throws: (any Error).self) {
            try validate.decodeSuccess(Data((prefix + #""protocol_valid":true,"immutable":"true"}"#).utf8))
        }
    }
}
