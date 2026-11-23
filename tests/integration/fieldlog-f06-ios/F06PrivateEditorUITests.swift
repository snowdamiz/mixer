import XCTest

final class F06PrivateEditorUITests: XCTestCase {
    private let bundleID = "dev.mixer.fieldlog.f06simulator"
    private let draft = "Inspect pump\nReplace filter"
    private let title = "Inspect pump P-17"
    private let ready = NSPredicate(format: "exists == true AND enabled == true AND hittable == true")

    @MainActor
    func testHistoricalMultilineRefusalCancelAndColdSingleLineCommit() {
        continueAfterFailure = false
        let app = XCUIApplication(bundleIdentifier: bundleID)
        app.launch()

        let field = app.descendants(matching: .any).matching(
            NSPredicate(format: "identifier == %@ AND (elementType == %d OR elementType == %d)",
                        "task-title", XCUIElement.ElementType.textField.rawValue, XCUIElement.ElementType.textView.rawValue)
        ).firstMatch
        let form = app.collectionViews["task.form"]
        let add = app.buttons["task.save"]

        expectEmpty(field, add: add)
        type(draft, into: field)
        expectExactValue(draft, on: field, in: app, "Multiline key echo")
        tapAction("task.save", label: "Add", in: form, app: app, titleField: field,
                  expectedTitle: draft, phase: "Multiline Add")
        awaitPredicate(NSPredicate(format: "exists == true AND enabled == true"), on: add,
                       "Refused Add must remain enabled", app: app)
        XCTAssertEqual(add.label, "Add")
        revealTitle(field, in: form, app: app)
        awaitPredicate(NSPredicate(format: "exists == true AND enabled == true"), on: field,
                       "Refused Add must keep the title enabled", app: app)
        expectExactValue(draft, on: field, in: app, "Title after refused Add")

        tapAction("task.cancel", label: "Cancel", in: form, app: app, titleField: field,
                  expectedTitle: draft, phase: "Cancel after refused Add")
        revealTitle(field, in: form, app: app)
        awaitPredicate(NSPredicate(format: "exists == true AND enabled == false"), on: field,
                       "Cancel must retire the rendered title", app: app)
        expectExactValue(draft, on: field, in: app, "Cancelled title must retain the exact LF")

        coldReopen(app)
        expectEmpty(field, add: add)
        type(title, into: field)
        expectExactValue(title, on: field, in: app, "Single-line key echo")
        tapAction("task.save", label: "Add", in: form, app: app, titleField: field,
                  expectedTitle: title, phase: "Single-line Add")
        awaitPredicate(NSPredicate(format: "exists == true AND enabled == false AND label == %@",
                                   "Add"), on: add, "Save must reach the terminal frame", app: app)
        revealTitle(field, in: form, app: app)
        awaitPredicate(NSPredicate(format: "exists == true AND enabled == false"), on: field,
                       "Save must retire the rendered title", app: app)
        expectExactValue(title, on: field, in: app, "Saved title")

        coldReopen(app)
        expectEmpty(field, add: add)
        app.terminate()
        XCTAssertEqual(app.state, .notRunning)
    }

    @MainActor
    private func coldReopen(_ app: XCUIApplication) {
        app.terminate()
        XCTAssertEqual(app.state, .notRunning)
        app.launch()
    }

    @MainActor
    private func expectEmpty(_ field: XCUIElement, add: XCUIElement) {
        awaitPredicate(ready, on: field, "Private renderer title must be ready after launch")
        XCTAssertTrue(field.placeholderValue == "What needs to happen?" || field.label == "What needs to happen?")
        let displayed = field.value as? String
        XCTAssertTrue(displayed == nil || displayed == "" || displayed == field.placeholderValue,
                      "Expected empty title, got \(String(describing: displayed))")
        XCTAssertTrue(add.exists)
        XCTAssertFalse(add.isEnabled)
        XCTAssertEqual(add.label, "Add")
    }

    @MainActor
    private func type(_ value: String, into field: XCUIElement) {
        field.tap()
        var rendered = ""
        for key in value {
            awaitPredicate(ready, on: field, "Title must be ready for the next key")
            field.typeText(String(key))
            rendered.append(key)
            awaitPredicate(NSPredicate(format: "value == %@", rendered), on: field,
                           "Exact native title after key: \(rendered.debugDescription)")
        }
    }

    @MainActor
    private func tapAction(_ identifier: String, label: String, in form: XCUIElement,
                           app: XCUIApplication, titleField: XCUIElement, expectedTitle: String,
                           phase: String) {
        var observations: [String] = []
        for attempt in 0...2 {
            expectExactValue(expectedTitle, on: titleField, in: app, "Title before \(phase)")
            let (coordinate, frames) = actionLabelCoordinate(identifier, label: label, in: form, app: app)
            let observation = "F06 \(phase) after \(attempt) reveal drags: \(frames)"
            print(observation)
            observations.append(observation)
            if let coordinate {
                coordinate.tap()
                return
            }
            guard attempt < 2, dragForm(form, app: app, towardActions: true) else { break }
        }

        let geometry = XCTAttachment(string: observations.joined(separator: "\n"))
        geometry.name = "F06 \(phase) refused tap geometry"
        add(geometry)
        attachFailureContext(app)
        XCTFail("\(phase): no usable label geometry for enabled \(identifier)")
    }

    @MainActor
    private func actionLabelCoordinate(_ identifier: String, label: String, in form: XCUIElement,
                                       app: XCUIApplication) -> (XCUICoordinate?, String) {
        guard form.exists else { return (nil, "task.form missing") }
        let appFrame = app.frame
        let formFrame = form.frame
        let rows = form.cells.containing(.button, identifier: identifier).allElementsBoundByIndex
        let rowFrames = rows.map { $0.frame }
        var frames = "app=\(appFrame) form=\(formFrame) \(identifier) rows=\(rowFrames)"
        guard rows.count == 1, let row = rows.first, let rowFrame = rowFrames.first else { return (nil, frames) }

        let wrappers = row.otherElements.matching(identifier: "task.actions")
            .containing(.button, identifier: identifier).allElementsBoundByIndex
        let labelFrames = wrappers.map { $0.frame }
        frames += " task.actions=\(labelFrames)"
        guard wrappers.count == 1, let wrapper = wrappers.first, wrapper.identifier == "task.actions",
              let labelFrame = labelFrames.first else { return (nil, frames) }

        let buttons = wrapper.buttons.matching(identifier: identifier).allElementsBoundByIndex
        let buttonFrames = buttons.map { $0.frame }
        frames += " buttons=\(buttonFrames)"
        guard buttons.count == 1, let button = buttons.first, let buttonFrame = buttonFrames.first
        else { return (nil, frames) }
        let enabled = button.isEnabled
        let actualLabel = button.label
        let actualID = button.identifier
        frames += " id=\(actualID) label=\(actualLabel.debugDescription) enabled=\(enabled)"
        guard actualID == identifier, actualLabel == label, enabled else { return (nil, frames) }

        let visible = formFrame.intersection(appFrame)
        guard [appFrame, formFrame, rowFrame, buttonFrame, labelFrame, visible].allSatisfy(usableFrame),
              rowFrame.contains(labelFrame), buttonFrame.contains(labelFrame) else { return (nil, frames) }

        // The keys' AX frame starts below the input accessory, which can also intercept a tap.
        let inputChrome = app.otherElements.matching(NSPredicate(
            format: "identifier == %@ OR identifier == %@", "inputView", "SystemInputAssistantView"))
        let keyboardFrames = (app.keyboards.allElementsBoundByIndex + inputChrome.allElementsBoundByIndex)
            .map { $0.frame }
        frames += " keyboard/accessory=\(keyboardFrames)"
        guard keyboardFrames.allSatisfy(usableFrame) else { return (nil, frames) }

        let keyboardTop = keyboardFrames.filter {
            $0.maxX > visible.minX && $0.minX < visible.maxX && $0.maxY > visible.minY
        }.map(\.minY).min() ?? visible.maxY
        let navigation = app.navigationBars["New task"]
        let visibleTop = navigation.exists ? max(visible.minY, navigation.frame.maxY) : visible.minY
        let visibleBottom = min(visible.maxY, keyboardTop)
        frames += " usableFormY=\(visibleTop)...\(visibleBottom)"

        let point = CGPoint(x: labelFrame.midX, y: labelFrame.midY)
        guard labelFrame.width > 4, labelFrame.height > 4,
              point.x > visible.minX + 8, point.x < visible.maxX - 8,
              point.y > visibleTop + 8, point.y < visibleBottom - 8 else { return (nil, frames) }

        let origin = app.coordinate(withNormalizedOffset: .zero)
        let coordinate = origin.withOffset(CGVector(dx: point.x - appFrame.minX, dy: point.y - appFrame.minY))
        return (coordinate, frames + " tap=\(point)")
    }

    private func usableFrame(_ frame: CGRect) -> Bool {
        !frame.isEmpty && [frame.minX, frame.minY, frame.maxX, frame.maxY].allSatisfy(\.isFinite)
    }

    @MainActor
    private func revealTitle(_ field: XCUIElement, in form: XCUIElement, app: XCUIApplication) {
        for _ in 0..<2 {
            if field.exists && field.frame.intersects(form.frame) { return }
            if !dragForm(form, app: app, towardActions: false) { break }
        }
    }

    @MainActor
    private func dragForm(_ form: XCUIElement, app: XCUIApplication, towardActions: Bool) -> Bool {
        guard form.exists else { return false }
        let formFrame = form.frame
        let appFrame = app.frame
        let visible = formFrame.intersection(appFrame)
        guard !visible.isNull, !visible.isInfinite else { return false }

        let keyboard = app.keyboards.firstMatch
        var bottom = visible.maxY
        if keyboard.exists {
            let keyboardFrame = keyboard.frame
            if keyboardFrame.intersects(visible) {
                bottom = min(bottom, keyboardFrame.minY)
            }
        }
        let height = bottom - visible.minY
        guard visible.width >= 80, height >= 180 else { return false }

        // Drag in the right side of the form, clear of the active title and keyboard.
        let x = visible.minX + visible.width * 0.88
        let lower = visible.minY + height * 0.78
        let upper = lower - min(125, height * 0.34)
        let origin = app.coordinate(withNormalizedOffset: .zero)
        let low = origin.withOffset(CGVector(dx: x - appFrame.minX, dy: lower - appFrame.minY))
        let high = origin.withOffset(CGVector(dx: x - appFrame.minX, dy: upper - appFrame.minY))
        let start = towardActions ? low : high
        let end = towardActions ? high : low
        start.press(forDuration: 0.05, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0)
        return true
    }

    @MainActor
    private func expectExactValue(_ expected: String, on field: XCUIElement,
                                  in app: XCUIApplication, _ message: String) {
        let actual = field.value as? String
        guard actual?.utf8.elementsEqual(expected.utf8) == true else {
            attachFailureContext(app)
            XCTAssertEqual(actual.map { Array($0.utf8) }, Array(expected.utf8), message)
            return
        }
    }

    @MainActor
    private func awaitPredicate(_ predicate: NSPredicate, on element: XCUIElement, _ message: String,
                                app: XCUIApplication? = nil) {
        let expectation = XCTNSPredicateExpectation(predicate: predicate, object: element)
        let result = XCTWaiter.wait(for: [expectation], timeout: 10)
        if result != .completed, let app { attachFailureContext(app) }
        XCTAssertEqual(result, .completed, message)
    }

    @MainActor
    private func attachFailureContext(_ app: XCUIApplication) {
        let screenshot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        screenshot.name = "F06 form on failure"
        add(screenshot)
        let hierarchy = XCTAttachment(string: app.debugDescription)
        hierarchy.name = "F06 accessibility hierarchy on failure"
        add(hierarchy)
    }
}
