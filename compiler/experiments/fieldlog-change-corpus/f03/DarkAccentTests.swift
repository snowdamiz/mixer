import XCTest

@MainActor final class DarkAccentTests: XCTestCase {
  func testHistoricalDarkAccentIsRendered() {
    continueAfterFailure = false
    let app = XCUIApplication()
    app.launchArguments = ["--fieldlog-ui-workspace", UUID().uuidString]
    app.launch()
    XCTAssertTrue(app.staticTexts["test-workspace-badge"].waitForExistence(timeout: 15))
    let emptyAction = app.buttons["create-first-project"]
    XCTAssertTrue(emptyAction.waitForExistence(timeout: 15))
    capture("F03 empty dark", app: app, controls: ["firstProject": emptyAction])
    emptyAction.tap()
    let title = app.textFields["project-name"]
    XCTAssertTrue(title.waitForExistence(timeout: 5))
    title.tap()
    title.typeText("Dark palette inspection")
    app.buttons["save-project"].tap()
    XCTAssertTrue(app.navigationBars["Dark palette inspection"].waitForExistence(timeout: 10))

    let newEntry = app.buttons["add-entry"]
    for _ in 0..<3 where !newEntry.isHittable {
      app.swipeUp()
    }
    XCTAssertTrue(newEntry.waitForExistence(timeout: 5))
    XCTAssertTrue(newEntry.isHittable)
    newEntry.tap()
    let done = app.buttons["Done"]
    XCTAssertTrue(done.waitForExistence(timeout: 8))
    let category = app.staticTexts["Category"]
    XCTAssertTrue(category.exists)
    capture("F03 draft dark", app: app, controls: ["done": done, "category": category])
    done.tap()
    XCTAssertTrue(app.navigationBars["Dark palette inspection"].waitForExistence(timeout: 15))
    app.terminate()
  }

  private func capture(_ label: String, app: XCUIApplication, controls: [String: XCUIElement]) {
    func coordinates(_ frame: CGRect) -> [Double] {
      [Double(frame.minX), Double(frame.minY), Double(frame.width), Double(frame.height)]
    }
    let metadata = ["app": coordinates(app.frame)].merging(
      controls.mapValues { coordinates($0.frame) }, uniquingKeysWith: { original, _ in original })
    let object = try! JSONSerialization.data(withJSONObject: metadata, options: [.sortedKeys])
    let geometry = XCTAttachment(string: String(decoding: object, as: UTF8.self))
    geometry.name = label + " frames"
    geometry.lifetime = .keepAlways
    add(geometry)
    let image = XCTAttachment(screenshot: app.screenshot())
    image.name = label + " image"
    image.lifetime = .keepAlways
    add(image)
  }
}
