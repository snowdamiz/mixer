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

        try expectNote(original, note)
        XCTAssertFalse(save.isEnabled)
        XCTAssertFalse(commit.isEnabled)
        note.tap()
        waitForAction(paste)
        paste.tap()
        try expectNote(original + "Edited", note)
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

    @MainActor private func expectNote(_ expected: String, _ note: XCUIElement) throws {
        let match = NSPredicate { object, _ in
            guard let field = object as? XCUIElement, field.exists, let text = field.value as? String else { return false }
            return text.utf8.elementsEqual(expected.utf8)
        }
        XCTAssertEqual(XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: match, object: note)], timeout: 12), .completed)
        let bytes = Array(try XCTUnwrap(note.value as? String).utf8)
        XCTAssertEqual(bytes, Array(expected.utf8))
        XCTAssertEqual(bytes.filter { $0 == 10 }.count, 4)
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
