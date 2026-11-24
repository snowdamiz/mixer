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

        let field = app.textFields.firstMatch
        XCTAssertTrue(field.exists)
        field.tap()
        field.typeText("A")
        XCTAssertTrue(app.staticTexts["Draft: A"].waitForExistence(timeout: 5))
        XCTAssertEqual(field.value as? String, "A")

        app.buttons["Close feature"].tap()
        XCTAssertTrue(app.staticTexts["Feature closed"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["Increment"].exists)
        XCTAssertFalse(field.exists)
    }
}
