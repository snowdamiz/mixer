import XCTest

final class BundledUITests: XCTestCase {
    @MainActor
    func testNativeStarter() {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.staticTexts["Feature ready"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["Bundled starter"].exists)
        XCTAssertTrue(app.staticTexts["Count: 0"].exists)
        app.buttons["Increment"].tap()
        XCTAssertTrue(app.staticTexts["Count: 1"].waitForExistence(timeout: 5))
    }

    @MainActor
    func testHeldKeyboardAndLifecycleDetach() {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.staticTexts["Feature ready"].waitForExistence(timeout: 10))

        let field = app.textFields.firstMatch
        XCTAssertTrue(field.exists)
        XCTAssertTrue(app.staticTexts["Draft: empty"].exists)
        app.buttons["Hold next display"].tap()
        field.tap()
        field.typeText("A")
        XCTAssertTrue(app.staticTexts["Display held"].waitForExistence(timeout: 5))
        field.typeText("BC")
        XCTAssertEqual(field.value as? String, "ABC")
        XCTAssertTrue(app.staticTexts["Draft: empty"].exists)
        XCTAssertFalse(app.staticTexts["Draft: ABC"].exists)

        app.buttons["Release display"].tap()
        XCTAssertTrue(app.staticTexts["Draft: ABC"].waitForExistence(timeout: 5))
        XCTAssertEqual(field.value as? String, "ABC")
        if !app.keyboards.firstMatch.exists { field.tap() }
        field.typeText("DEF")
        XCTAssertTrue(app.staticTexts["Draft: ABCDEF"].waitForExistence(timeout: 5))
        XCTAssertEqual(field.value as? String, "ABCDEF")

        // The shell removes the view without calling cancel or releasing its mount.
        app.buttons["Close feature"].tap()
        XCTAssertTrue(app.staticTexts["Feature closed"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["Increment"].exists)
        XCTAssertFalse(field.exists)
    }
}
