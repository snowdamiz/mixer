import XCTest

@MainActor
final class FieldLogInstalledUpgradeTests: XCTestCase {
  private let project = "Migration pump station"
  private let task = "Inspect pump, not completed"
  private let title = "Migration photo draft"
  private let note = "Keep  two spaces."
  private let addition = " Checked on site."
  private var app: XCUIApplication { XCUIApplication(bundleIdentifier: "dev.mixer.fieldlog") }

  func testCreateOrdinaryWorkspace() {
    continueAfterFailure = false
    let app = self.app
    defer { stop(app) }
    launch(app)
    ready(app.buttons["create-first-project"]).tap()
    type(project, into: app.textFields["project-name"])
    ready(app.buttons["save-project"]).tap()
    XCTAssertTrue(app.navigationBars[project].waitForExistence(timeout: 15))

    reveal(app.buttons["Add task"], in: app).tap()
    type("Inspect pump", into: input("task-title", app))
    ready(app.navigationBars["New task"].buttons["Add"]).tap()
    XCTAssertTrue(app.buttons[task].waitForExistence(timeout: 15))

    reveal(app.buttons["add-entry"], in: app).tap()
    type(title, into: input("entry-title", app))
    let editor = app.textViews["entry-note"]
    type(note, into: reveal(editor, in: app))
    XCTAssertEqual(editor.value as? String, note)

    reveal(app.buttons["attach-file"], in: app).tap()
    selectSeededFile(in: app)
    XCTAssertTrue(app.images["Attached field photo"].waitForExistence(timeout: 8),
      app.debugDescription)
    photo(in: app, name: "02-prior-draft-with-photo")
    reveal(app.staticTexts["Draft saved on this device. You can return to it later."], in: app)
    // Leave the editor open so the next cold launch exercises actual scene restoration.
  }

  func testReopenOrdinaryWorkspace() {
    continueAfterFailure = false
    let app = self.app
    defer { stop(app) }
    launch(app)
    restoredDraft(in: app, image: "03-prior-cold-restored")
  }

  func testRestoreAndEditReplacement() {
    continueAfterFailure = false
    let app = self.app
    defer { stop(app) }
    launch(app)
    restoredDraft(in: app, image: "04-replacement-cold-restored")

    let editor = reveal(app.textViews["entry-note"], in: app, swipeUp: false)
    editor.tap()
    // The one-line note leaves trailing whitespace inside the editor.
    // Tapping that space moves the insertion point to the end of the line.
    XCTAssertEqual(editor.value as? String, note)
    editor.coordinate(withNormalizedOffset: CGVector(dx: 0.88, dy: 0.08)).tap()
    editor.typeText(addition)
    XCTAssertEqual(editor.value as? String, note + addition)
    reveal(app.buttons["save-entry"], in: app).tap()

    XCTAssertTrue(app.navigationBars["Field note"].waitForNonExistence(timeout: 15))
    XCTAssertTrue(app.navigationBars[project].waitForExistence(timeout: 15))
    reveal(app.staticTexts[title], in: app)
    screenshot("05-entry-saved", app)
  }

  func testReadEditedEntryAfterColdLaunch() {
    continueAfterFailure = false
    let app = self.app
    defer { stop(app) }
    launch(app)
    XCTAssertTrue(app.navigationBars[project].waitForExistence(timeout: 15))
    XCTAssertFalse(app.navigationBars["Field note"].exists)
    XCTAssertTrue(app.buttons[task].waitForExistence(timeout: 15))
    reveal(app.staticTexts[title], in: app).tap()
    XCTAssertTrue(app.navigationBars[title].waitForExistence(timeout: 10))
    XCTAssertTrue(app.staticTexts[note + addition].waitForExistence(timeout: 10))
    photo(in: app, name: "06-committed-entry-after-cold-launch")

    ready(app.tabBars.buttons["On device"]).tap()
    for label in ["3 PENDING CHANGES", "Project created", "Task updated", "Entry saved"] {
      XCTAssertTrue(app.staticTexts[label].waitForExistence(timeout: 10), app.debugDescription)
    }
    screenshot("07-pending-outbox", app)
  }

  private enum PickerTarget {
    case photo(CGPoint)
    case folder(CGPoint)
    case browse(CGPoint)
  }

  private func selectSeededFile(in app: XCUIApplication) {
    let photoCells = app.cells.matching(NSPredicate(format: "identifier == %@", "FieldLog upgrade photo, png"))
    let folderCells = app.cells.matching(NSPredicate(format: "label == %@", "FieldLog, 1 item"))
    let browse = app.tabBars["DOC.browsingModeTabBar"].buttons["Browse"]

    func iconPoint(in cells: XCUIElementQuery) -> CGPoint? {
      for cell in cells.allElementsBoundByIndex {
        let tile = cell.frame
        guard !tile.isEmpty else { continue }
        let screen = app.frame
        if let thumbnail = cell.images.allElementsBoundByIndex.first?.frame,
           !thumbnail.isEmpty, tile.contains(thumbnail), screen.contains(thumbnail) {
          return CGPoint(x: thumbnail.midX, y: thumbnail.midY)
        }
        // In the observed Files grid, both icons center 46 points below the tile top.
        let icon = CGPoint(x: tile.midX, y: tile.minY + 46)
        if tile.width >= 84, tile.height >= 88, screen.contains(icon) {
          return icon
        }
      }
      return nil
    }

    func waitForTarget(folder: Bool, browseTab: Bool = false) -> PickerTarget? {
      var target: PickerTarget?
      let ready = NSPredicate { _, _ in
        if let point = iconPoint(in: photoCells) {
          target = .photo(point)
        } else if folder, let point = iconPoint(in: folderCells) {
          target = .folder(point)
        } else if browseTab, browse.exists, !browse.isSelected {
          let tab = browse.frame
          if !tab.isEmpty, app.frame.contains(tab) {
            target = .browse(CGPoint(x: tab.midX, y: tab.midY))
          }
        }
        return target != nil
      }
      _ = XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: ready, object: nil)], timeout: 30)
      return target
    }

    var target = waitForTarget(folder: true, browseTab: true)
    if case .browse(let point) = target {
      screenTap(point, in: app)
      target = waitForTarget(folder: true)
    }
    if case .folder(let point) = target {
      screenTap(point, in: app)
      target = waitForTarget(folder: false)
    }
    guard case .photo(let point) = target else {
      screenshot("files-picker-selection-failed", app)
      XCTFail("Could not find the seeded FieldLog upgrade photo.png tile. \(app.debugDescription)")
      return
    }
    screenshot("01-files-picker", app)
    screenTap(point, in: app)
  }

  private func screenTap(_ point: CGPoint, in app: XCUIApplication) {
    app.coordinate(withNormalizedOffset: CGVector(dx: 0, dy: 0))
      .withOffset(CGVector(dx: point.x, dy: point.y)).tap()
  }

  private func launch(_ app: XCUIApplication) {
    app.launchArguments = []
    app.launchEnvironment = [:]
    app.launch()
    XCTAssertFalse(app.staticTexts["test-workspace-badge"].exists)
  }

  private func stop(_ app: XCUIApplication) {
    app.terminate()
    XCTAssertTrue(app.wait(for: .notRunning, timeout: 15))
  }

  private func restoredDraft(in app: XCUIApplication, image: String) {
    XCTAssertTrue(app.navigationBars["Field note"].waitForExistence(timeout: 15),
      "Expected the saved draft editor to reopen automatically")
    XCTAssertEqual(input("entry-title", app).value as? String, title)
    XCTAssertEqual(app.textViews["entry-note"].value as? String, note)
    photo(in: app, name: image)
  }

  private func photo(in app: XCUIApplication, name: String) {
    let preview = app.images["Attached field photo"]
    reveal(preview, in: app)
    XCTAssertEqual(app.images.matching(identifier: "Attached field photo").count, 1)
    XCTAssertFalse(app.staticTexts["Photo unavailable on this device"].exists)
    screenshot(name, app)
  }

  private func input(_ id: String, _ app: XCUIApplication) -> XCUIElement {
    let field = app.descendants(matching: .any).matching(NSPredicate(
      format: "identifier == %@ AND (elementType == %d OR elementType == %d)", id,
      XCUIElement.ElementType.textField.rawValue, XCUIElement.ElementType.textView.rawValue
    )).firstMatch
    XCTAssertTrue(field.waitForExistence(timeout: 10), app.debugDescription)
    return field
  }

  private func type(_ text: String, into element: XCUIElement) {
    ready(element).tap()
    element.typeText(text)
  }

  @discardableResult private func ready(_ element: XCUIElement) -> XCUIElement {
    let predicate = NSPredicate(format: "exists == true AND enabled == true AND hittable == true")
    XCTAssertEqual(XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: predicate,
      object: element)], timeout: 12), .completed)
    return element
  }

  @discardableResult private func reveal(
    _ element: XCUIElement, in app: XCUIApplication, swipeUp: Bool = true
  ) -> XCUIElement {
    for _ in 0..<7 {
      if element.exists, element.isHittable { return ready(element) }
      if swipeUp { app.swipeUp() } else { app.swipeDown() }
    }
    XCTAssertTrue(element.exists && element.isHittable, app.debugDescription)
    return element
  }

  private func screenshot(_ name: String, _ app: XCUIApplication) {
    let attachment = XCTAttachment(screenshot: app.screenshot())
    attachment.name = name
    attachment.lifetime = .keepAlways
    add(attachment)
  }
}
