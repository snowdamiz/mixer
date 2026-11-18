
extension FieldLogUITests {
  func testAssignmentNotificationOpensOrdinaryTask() throws {
    continueAfterFailure = false
    let app = XCUIApplication()
    app.launch()
    XCTAssertTrue(app.buttons["create-first-project"].waitForExistence(timeout: 15))
    XCTAssertFalse(app.staticTexts["test-workspace-badge"].exists)
    app.buttons["create-first-project"].tap()
    let projectName = app.textFields["project-name"]
    XCTAssertTrue(projectName.waitForExistence(timeout: 5))
    projectName.tap()
    projectName.typeText("Assignment workshop")
    app.buttons["save-project"].tap()
    XCTAssertTrue(app.navigationBars["Assignment workshop"].waitForExistence(timeout: 10))
    let add = app.buttons["Add task"]
    reveal(add, in: app)
    add.tap()
    let title = app.descendants(matching: .any).matching(NSPredicate(format: "placeholderValue == %@", "What needs to happen?")).firstMatch
    XCTAssertTrue(title.waitForExistence(timeout: 10), app.debugDescription)
    title.tap()
    title.typeText("Read gauge")
    let assignee = app.textFields.matching(NSPredicate(format: "placeholderValue == %@", "Responsible person (optional)")).firstMatch
    XCTAssertTrue(assignee.exists, app.debugDescription)
    assignee.tap()
    assignee.typeText("Rae")
    app.navigationBars["New task"].buttons["Add"].tap()
    let post = app.buttons["Post test assignment notification for Read gauge"]
    XCTAssertTrue(post.waitForExistence(timeout: 10))
    let spring = XCUIApplication(bundleIdentifier: "com.apple.springboard")
    let allow = spring.alerts.buttons["Allow"]
    let banner = spring.descendants(matching: .any).matching(
      NSPredicate(format: "label CONTAINS[c] %@", "FieldLog assignment")
    ).firstMatch
    for _ in 0..<2 {
      XCTAssertTrue(post.isHittable, app.debugDescription)
      post.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
      if allow.waitForExistence(timeout: 5) {
        allow.tap()
        break
      }
      if banner.exists { break }
    }
    XCTAssertTrue(banner.waitForExistence(timeout: 15), spring.debugDescription)
    banner.tap()
    XCTAssertTrue(app.navigationBars["Assigned task"].waitForExistence(timeout: 15), app.debugDescription)
    XCTAssertTrue(app.staticTexts["Read gauge"].exists)
    let status = app.descendants(matching: .any).matching(
      NSPredicate(format: "value == %@ OR label IN %@", "Open", ["Open", "Status, Open", "Status: Open"])
    ).firstMatch
    XCTAssertTrue(status.waitForExistence(timeout: 5), app.debugDescription)
    screenshot("assigned-task-from-notification", app)
    app.navigationBars["Assigned task"].buttons["Back"].tap()
    XCTAssertTrue(app.buttons["Read gauge, not completed"].waitForExistence(timeout: 10))
    screenshot("returned-to-project", app)
    app.terminate()
  }
}
