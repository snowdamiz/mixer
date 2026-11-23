import XCTest

@MainActor final class FieldLogHistoricalMoveTests: XCTestCase {
  func testHistoricalTaskMovesSurviveColdReopen() {
    continueAfterFailure = false
    let workspace = UUID()
    let app = XCUIApplication()
    app.launchArguments = ["--fieldlog-ui-workspace", workspace.uuidString]
    app.launch()
    XCTAssertTrue(app.staticTexts["test-workspace-badge"].waitForExistence(timeout: 15))
    let newProject = app.buttons["create-first-project"]
    XCTAssertTrue(newProject.waitForExistence(timeout: 15))
    newProject.tap()
    let project = app.textFields["project-name"]
    XCTAssertTrue(project.waitForExistence(timeout: 5))
    project.tap()
    project.typeText("Historical task ordering")
    app.buttons["save-project"].tap()
    let projectBar = app.navigationBars["Historical task ordering"]
    XCTAssertTrue(projectBar.waitForExistence(timeout: 10))

    add("Measure opening", app: app)
    add("Take field notes", app: app)
    let first = app.buttons["Measure opening, not completed"]
    let second = app.buttons["Take field notes, not completed"]
    assertPrecedes(first, second)
    move("Measure opening", direction: "Move down", app: app)
    assertPrecedes(second, first)
    app.terminate()
    app.launch()
    XCTAssertTrue(projectBar.waitForExistence(timeout: 15))
    assertPrecedes(second, first)
    move("Measure opening", direction: "Move up", app: app)
    assertPrecedes(first, second)
    app.terminate()
    app.launch()
    XCTAssertTrue(projectBar.waitForExistence(timeout: 15))
    assertPrecedes(first, second)
    let proof = XCTAttachment(string: workspace.uuidString.lowercased())
    proof.name = "F02 saved workspace UUID"
    proof.lifetime = .keepAlways
    add(proof)
    app.terminate()
  }

  private func add(_ name: String, app: XCUIApplication) {
    let button = app.buttons["Add task"]
    XCTAssertTrue(button.waitForExistence(timeout: 8))
    button.tap()
    let title = app.textFields["task-title"]
    XCTAssertTrue(title.waitForExistence(timeout: 5))
    title.tap()
    title.typeText(name)
    app.navigationBars["New task"].buttons["Add"].tap()
    XCTAssertTrue(app.buttons[name + ", not completed"].waitForExistence(timeout: 10))
  }

  private func move(_ name: String, direction: String, app: XCUIApplication) {
    let options = app.buttons["Task options: " + name]
    XCTAssertTrue(options.waitForExistence(timeout: 8))
    options.tap()
    let command = app.buttons[direction]
    XCTAssertTrue(command.waitForExistence(timeout: 5))
    XCTAssertTrue(command.isEnabled)
    command.tap()
  }

  private func assertPrecedes(_ before: XCUIElement, _ after: XCUIElement) {
    let ordered = NSPredicate { _, _ in
      before.exists && after.exists && before.frame.minY < after.frame.minY
    }
    expectation(for: ordered, evaluatedWith: nil)
    waitForExpectations(timeout: 10)
  }
}
