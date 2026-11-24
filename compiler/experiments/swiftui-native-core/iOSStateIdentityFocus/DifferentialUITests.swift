import XCTest

private struct JourneyFailure: Error, CustomStringConvertible {
    let description: String
}

private struct Observation: Codable, Equatable {
    let checkpoint: String
    let rows: [String]
    let draft: [String]
    let readback: [String]
    let fieldCount: Int
    let fieldValue: String?
    let placeholder: String?
    let keyboardVisible: Bool
}

final class DifferentialUITests: XCTestCase {
    @MainActor
    func testStateIdentityFocus() {
        // Keep evidence from both launches even if one journey stops early.
        continueAfterFailure = true
        let apple = run(mode: "Apple SwiftUI", arguments: [])
        let mixer = run(mode: "MixerSwiftUI", arguments: ["--mixer"])
        XCTAssertEqual(apple.count, 8, "Apple SwiftUI must complete all checkpoints")
        XCTAssertEqual(mixer.count, 8, "MixerSwiftUI must complete all checkpoints")
        XCTAssertEqual(apple, mixer, "Native observations differ. See both GC4 traces.")
    }

    @MainActor
    private func run(mode: String, arguments: [String]) -> [Observation] {
        let app = XCUIApplication()
        app.launchArguments = arguments
        app.launch()
        var trace: [Observation] = []
        defer {
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            do {
                let data = try encoder.encode(trace)
                attach(XCTAttachment(data: data, uniformTypeIdentifier: "public.json"), "GC4 \(mode) trace")
            } catch {
                XCTFail("Could not encode \(mode) trace: \(error)")
            }
            attach(XCTAttachment(string: app.debugDescription), "GC4 \(mode) final accessibility tree")
            attach(XCTAttachment(screenshot: app.screenshot()), "GC4 \(mode) final screen")
            app.terminate()
        }

        let fields = app.textFields
        let field = fields.firstMatch
        let keyboard = app.keyboards.firstMatch

        func labels(prefix: String) -> [XCUIElement] {
            app.staticTexts.matching(NSPredicate(format: "label BEGINSWITH %@", prefix)).allElementsBoundByIndex
        }

        func observe(_ checkpoint: String) -> Observation {
            let fieldCount = fields.count
            return Observation(
                checkpoint: checkpoint,
                rows: labels(prefix: "Row ").sorted { $0.frame.midY < $1.frame.midY }.map(\.label),
                draft: labels(prefix: "Draft: ").map(\.label),
                readback: labels(prefix: "Readback: ").map(\.label),
                fieldCount: fieldCount,
                fieldValue: fieldCount == 1 ? field.value as? String : nil,
                placeholder: fieldCount == 1 ? field.placeholderValue : nil,
                keyboardVisible: keyboard.exists
            )
        }

        func check(
            _ checkpoint: String, rows: [String], draft: String = "empty",
            readback: String = "none", typed: String? = nil, keyboardVisible: Bool? = false
        ) throws {
            func matches(_ observed: Observation) -> Bool {
                observed.rows == rows && observed.draft == ["Draft: \(draft)"] &&
                    observed.readback == ["Readback: \(readback)"] && observed.fieldCount == 1 &&
                    (typed == nil || observed.fieldValue == typed) &&
                    (keyboardVisible == nil || observed.keyboardVisible == keyboardVisible)
            }

            let deadline = ProcessInfo.processInfo.systemUptime + 10
            var observed = observe(checkpoint)
            while !matches(observed) && ProcessInfo.processInfo.systemUptime < deadline {
                RunLoop.current.run(until: Date().addingTimeInterval(0.05))
                observed = observe(checkpoint)
            }
            trace.append(observed)
            guard matches(observed) else {
                throw JourneyFailure(description: "\(checkpoint) gave \(observed)")
            }
        }

        func tap(_ label: String) throws {
            let button = app.buttons[label]
            guard button.waitForExistence(timeout: 5), button.isHittable else {
                throw JourneyFailure(description: "Could not tap \(label)")
            }
            button.tap()
        }

        do {
            try check("launch", rows: ["Row A: 0", "Row B: 0"])
            try tap("Increment A")
            try check("increment A", rows: ["Row A: 1", "Row B: 0"])
            try tap("Move rows")
            try check("move B before A", rows: ["Row B: 0", "Row A: 1"])
            try tap("Increment B")
            let rows = ["Row B: 1", "Row A: 1"]
            try check("increment moved B", rows: rows)

            guard field.isHittable else { throw JourneyFailure(description: "Could not tap Draft field") }
            field.tap()
            try check("focus Draft", rows: rows, keyboardVisible: true)
            field.typeText("abc")
            try check("type abc", rows: rows, draft: "abc", typed: "abc", keyboardVisible: true)
            // XCUIElement.typeText requires focus. There is no refocus between batches.
            field.typeText("def")
            try check("type def without refocusing", rows: rows, draft: "abcdef",
                      typed: "abcdef", keyboardVisible: true)
            try tap("Read draft")
            try check("read accepted draft via Button", rows: rows, draft: "abcdef",
                      readback: "abcdef", typed: "abcdef", keyboardVisible: nil)
        } catch {
            XCTFail("\(mode): \(error)")
        }
        return trace
    }

    private func attach(_ attachment: XCTAttachment, _ name: String) {
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
