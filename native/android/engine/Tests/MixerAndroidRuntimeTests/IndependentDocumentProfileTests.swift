import Foundation
import MixerUI
import MixerAndroid
import XCTest
@_spi(MixerNativeAppearanceV2) import MixerAndroidRuntime

final class IndependentDocumentProfileTests: XCTestCase {
    private static func make(_ profile: AndroidUIProfile) throws -> AndroidDocumentSession<String> {
        try AndroidDocumentSession(state: "seed", profile: profile, document: { value, revision in
            var field = TextField("field", "Field", value: value, action: "edit").uiNode
            if value == "vertical" { field.properties["axis"] = .string("vertical") }
            if value == "horizontal" { field.properties["axis"] = .string("horizontal") }
            if value == "bad-axis" { field.properties["axis"] = .string("unknown") }
            var children = [field]
            if value == "overflow" {
                children += (0..<11).map { Text("new.\($0)", String(repeating: "\0", count: 16_384)).uiNode }
            }
            return UIDocument(revision: revision, root: UINode(id: "root", kind: .vStack, children: children))
        }, reduce: { state, action in
            guard case .string(let value) = action.value else { throw AndroidDocumentError.invalidEvent }
            state = value
        })
    }
    private func input(_ packet: Data, _ value: String) throws -> Data {
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: packet) as? [String: Any])
        let document = try XCTUnwrap(object["document"] as? [String: Any])
        let identities = try JSONDecoder().decode([UINodeIdentity].self, from: JSONSerialization.data(withJSONObject: XCTUnwrap(object["identities"])))
        return try JSONEncoder().encode(UIEventEnvelope(revision: try XCTUnwrap(document["revision"] as? UInt64),
            identity: try XCTUnwrap(identities.first { $0.id == "field" }), event: .textChange, value: .string(value)))
    }
    func testClonesDoNotInferOrLoseProfileAfterAxisFreeRender() throws {
        for profile in [AndroidUIProfile.measuredMultilineV2, .measuredMultilineRetirementV3] {
            let original = try Self.make(profile)
            let initial = try original.render()
            for failure in ["bad-axis", "overflow"] {
                var candidate = original
                XCTAssertThrowsError(try candidate.dispatch(input(initial, failure)))
                XCTAssertEqual(candidate.state, "seed")
                XCTAssertEqual(candidate.revision, 1)
                XCTAssertEqual(try candidate.render(), initial)
                var control = original
                let vertical = try candidate.dispatch(input(initial, "vertical"))
                XCTAssertEqual(vertical, try control.dispatch(input(initial, "vertical")))
                XCTAssertTrue(String(decoding: vertical, as: UTF8.self).contains(#""axis":"vertical""#))
                let horizontal = try candidate.dispatch(input(vertical, "horizontal"))
                XCTAssertTrue(String(decoding: horizontal, as: UTF8.self).contains(#""axis":"horizontal""#))
                XCTAssertEqual(try original.render(), initial)
            }
            var legacy = try Self.make(.legacyHorizontal)
            XCTAssertThrowsError(try legacy.dispatch(input(initial, "vertical"))) {
                XCTAssertEqual($0 as? UIValidationError, .unsupportedTextFieldAxis(.vertical))
            }
            XCTAssertThrowsError(try legacy.dispatch(input(initial, "horizontal"))) {
                guard case AndroidDocumentError.unsupportedUI = $0 else { return XCTFail("\($0)") }
            }
            XCTAssertEqual(try legacy.render(), initial)
        }
    }
    func testAxisIntroductionSurvivesPrepareAbortCommitAndRepeatedFailures() throws {
        let transport = TransactionTests()
        for profile in [AndroidUIProfile.measuredMultilineV2, .measuredMultilineRetirementV3] {
            let registry = AndroidSessionRegistry { try Self.make(profile) }
            let handle = registry.create()
            XCTAssertNotEqual(handle, 0)
            defer { XCTAssertEqual(registry.destroy(handle), 0) }
            let initial = transport.render(registry, handle).bytes
            let verticalInput = try input(initial, "vertical")
            let small = transport.call(registry, handle, staged: true, input: verticalInput, capacity: 1)
            XCTAssertEqual(small.status, 3); XCTAssertEqual(small.token, 0)
            XCTAssertEqual(transport.render(registry, handle).bytes, initial)
            let aborted = transport.call(registry, handle, staged: true, input: verticalInput)
            XCTAssertEqual(aborted.status, 0); XCTAssertNotEqual(aborted.token, 0)
            XCTAssertEqual(registry.abortV2(handle, aborted.token), 0)
            XCTAssertEqual(transport.render(registry, handle).bytes, initial)
            let committed = transport.call(registry, handle, staged: true, input: verticalInput)
            XCTAssertEqual(committed.status, 0); XCTAssertEqual(committed.bytes, aborted.bytes)
            XCTAssertEqual(registry.commitV2(handle, committed.token), 0)
            for failure in ["bad-axis", "overflow"] {
                let rejected = transport.call(registry, handle, staged: true, input: try input(committed.bytes, failure))
                XCTAssertEqual(rejected.status, 4); XCTAssertEqual(rejected.token, 0); XCTAssertEqual(rejected.written, 0)
                XCTAssertEqual(transport.render(registry, handle).bytes, committed.bytes)
            }
            let horizontal = transport.call(registry, handle, staged: true, input: try input(committed.bytes, "horizontal"))
            XCTAssertEqual(horizontal.status, 0)
            XCTAssertEqual(registry.commitV2(handle, horizontal.token), 0)
            XCTAssertTrue(String(decoding: horizontal.bytes, as: UTF8.self).contains(#""axis":"horizontal""#))
            let stale = transport.call(registry, handle, staged: true, input: verticalInput)
            XCTAssertEqual(stale.status, 4); XCTAssertEqual(stale.token, 0)
            XCTAssertEqual(transport.render(registry, handle).bytes, horizontal.bytes)
        }
    }
}
