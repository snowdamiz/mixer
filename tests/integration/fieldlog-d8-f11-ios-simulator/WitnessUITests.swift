import XCTest

final class F11WitnessUITests: XCTestCase {
    @MainActor func testPasteSaveAndCommitRestoredNote() throws {
        continueAfterFailure = false
        let original = "Café e\u{0301} 👩🏽‍🔬\n東京\n\nLast line\n"
        let run = UUID().uuidString
        let app = XCUIApplication()
        app.launchArguments = [run]
        app.launch()
        let note = app.textViews["f11.note"]
        let paste = app.descendants(matching: .any)["f11.paste"].firstMatch
        let save = app.buttons["f11.save"]
        let commit = app.buttons["f11.commit"]
        let status = app.staticTexts["f11.status"]

        try expectNote(original, note, paste: paste, stage: "Initial revision 1 bytes")
        XCTAssertFalse(save.isEnabled)
        XCTAssertFalse(commit.isEnabled)
        note.tap()
        waitForPasteAuthority(paste)
        paste.tap()
        try expectNote(original + "Edited", note, paste: paste, stage: "After one paste")
        waitForAction(save)
        save.tap()
        waitForLabel("Cold draft revision 2", on: status)
        waitForAction(commit)
        commit.tap()
        waitForLabel("Committed ", on: status, prefix: true)
        let hash = String(status.label.dropFirst("Committed ".count))
        XCTAssertEqual(hash.count, 64)
        app.terminate()
        app.launchArguments = [run, "--readback"]
        app.launch()
        waitForLabel("Cold commit " + hash, on: status)
    }

    @MainActor private func expectNote(_ expected: String, _ note: XCUIElement, paste: XCUIElement,
                                       stage: String) throws {
        let match = NSPredicate { object, _ in
            guard let field = object as? XCUIElement, field.exists, let text = field.value as? String else { return false }
            return text.utf8.elementsEqual(expected.utf8)
        }
        let result = XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: match, object: note)], timeout: 12)
        attachDiagnostic(stage, paste)
        XCTAssertEqual(result, .completed)
        let bytes = Array(try XCTUnwrap(note.value as? String).utf8)
        XCTAssertEqual(bytes, Array(expected.utf8))
        XCTAssertEqual(bytes.filter { $0 == 10 }.count, 4)
    }

    @MainActor private func attachDiagnostic(_ stage: String, _ paste: XCUIElement) {
        let diagnostic = paste.exists ? (paste.value as? String).flatMap(allowlistedDiagnostic) : nil
        let accessibility = "exists=\(paste.exists) enabled=\(paste.exists && paste.isEnabled)"
            + " hittable=\(paste.exists && paste.isHittable)"
        let attachment = XCTAttachment(string: "\(accessibility)\n\(diagnostic ?? "diagnostic unavailable")")
        attachment.name = "F11 \(stage)"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func allowlistedDiagnostic(_ value: String) -> String? {
        // The fixture supplies fixed status tokens, bounded counters and ticket numbers.
        guard value.utf8.count <= 2048,
              value.wholeMatch(of: /paste=(waiting|type-rejected|inactive|provider focus=(true|false) selection=-?[0-9]{1,4},-?[0-9]{1,4}|stale|bytes-rejected|bytes-accepted) edit=(waiting|range-rejected|edit-rejected|inserted=-?[0-9]{1,4},0 bytes=6) route=(waiting|rejected|unconfirmed|accepted) document=[0-9]{1,20}( [a-zA-Z][a-zA-Z0-9]*=[a-zA-Z0-9,\/-]+)+/) != nil
        else { return nil }
        return value
    }

    @MainActor private func waitForPasteAuthority(_ paste: XCUIElement) {
        let ready = NSPredicate { object, _ in
            guard let button = object as? XCUIElement, button.exists, button.isEnabled, button.isHittable,
                  let value = button.value as? String, let diagnostic = self.allowlistedDiagnostic(value) else {
                return false
            }
            let fields = Set(diagnostic.split(separator: " "))
            return fields.isSuperset(of: ["document=1", "native=1", "observed=true", "observe=accepted",
                                          "effects=true", "displayed=1", "authority=true", "enabled=true",
                                          "target=true", "editable=true", "sameWindow=true", "requested=false",
                                          "submitted=false", "callbacks=0", "paste=waiting"])
        }
        let result = XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: ready, object: paste)], timeout: 12)
        attachDiagnostic("Revision 1 paste admission", paste)
        XCTAssertEqual(result, .completed, "Expected UIKit's current revision 1 acknowledgment and an authorized paste target")
    }

    @MainActor private func waitForAction(_ button: XCUIElement) {
        let ready = NSPredicate(format: "exists == true AND enabled == true AND hittable == true")
        XCTAssertEqual(XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: ready, object: button)], timeout: 12), .completed)
    }

    @MainActor private func waitForLabel(_ text: String, on status: XCUIElement, prefix: Bool = false) {
        let expected = NSPredicate(format: prefix ? "label BEGINSWITH %@" : "label == %@", text)
        XCTAssertEqual(XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: expected, object: status)], timeout: 12), .completed,
                       status.exists ? status.label : "Status missing")
    }
}
