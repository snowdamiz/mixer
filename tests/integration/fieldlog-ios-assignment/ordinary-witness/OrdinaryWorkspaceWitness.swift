
extension FieldLogUITests {
  func testOrdinarySavedDraftPinAndSettingsSurviveColdLaunch() {
    continueAfterFailure = false
    let app = XCUIApplication()
    app.launchArguments = [
      "--fieldlog-ui-workspace", UUID().uuidString, "--fieldlog-ordinary-witness-readback",
      "-AppleLanguages", "(en)", "-AppleLocale", "en_US",
    ]
    let project = "Pump station witness"
    let draft = "Pressure reading"
    let note = "Gauge stable at 42 psi."
    app.launch()
    XCTAssertTrue(app.staticTexts["test-workspace-badge"].waitForExistence(timeout: 15))
    tapWitness(app.buttons["create-first-project"], in: app)
    typeWitness(project, into: app.textFields["project-name"], in: app)
    tapWitness(app.buttons["save-project"], in: app)
    XCTAssertTrue(app.navigationBars[project].waitForExistence(timeout: 10))

    // Leave the created project and explicitly open the saved list row.
    backWitness(from: project, to: "FieldLog", in: app)
    tapWitness(app.staticTexts[project], in: app)
    tapWitness(app.buttons["add-entry"], in: app)
    typeWitness(draft, into: witnessInput("entry-title", in: app), in: app)
    tapWitness(app.navigationBars["Field note"].buttons["Done"], in: app)
    openWitnessDraft(draft, in: app)
    typeWitness(note, into: app.textViews["entry-note"], in: app)
    tapWitness(app.buttons["Choose photo"], in: app)
    let photos = app.descendants(matching: .any).matching(
      NSPredicate(format: "label == %@ OR label BEGINSWITH %@", "Photo", "Photo,")
    )
    XCTAssertTrue(photos.firstMatch.waitForExistence(timeout: 10), app.debugDescription)
    XCTAssertEqual(photos.allElementsBoundByIndex.filter(\.isHittable).count, 1,
      "The owned Simulator library must contain exactly one selectable synthetic image.")
    if let photo = photos.allElementsBoundByIndex.first(where: \.isHittable) {
      tapWitness(photo, in: app)
    } else {
      XCTFail("The synthetic image cannot be selected.")
    }
    let done = app.navigationBars["Field note"].buttons["Done"]
    XCTAssertTrue(done.waitForExistence(timeout: 10))
    checkWitnessDraft(draft, note: note, in: app)
    tapWitness(done, in: app)

    tapWitness(app.buttons["project-site-map"], in: app, scrollingUp: false)
    tapWitness(app.buttons["Set site pin"], in: app)
    typeWitness("37.42", into: app.textFields["Latitude"], in: app)
    typeWitness("-122.08", into: app.textFields["Longitude"], in: app)
    tapWitness(app.buttons["Save site pin"], in: app)
    checkWitnessPin(in: app)
    backWitness(from: "Site map", to: project, in: app)

    tapWitness(app.tabBars.buttons["Settings"], in: app)
    XCTAssertTrue(app.navigationBars["Settings"].waitForExistence(timeout: 5))
    let appearance = app.buttons["settings-appearance"]
    XCTAssertTrue(appearance.waitForExistence(timeout: 5))
    XCTAssertEqual(appearance.value as? String, "System", "The install must have fresh Settings.")
    tapWitness(appearance, in: app)
    tapWitness(app.buttons["Dark"], in: app)
    checkWitnessSettings(in: app)
    let before = witnessDiskCheckpoint(in: app)

    app.terminate()
    XCTAssertTrue(app.wait(for: .notRunning, timeout: 5))
    app.launch()
    XCTAssertTrue(app.navigationBars[project].waitForExistence(timeout: 15),
      "The saved project must restore on cold launch.")
    let after = witnessDiskCheckpoint(in: app)
    XCTAssertEqual(after, before, "Workspace, durable photo and Settings must survive byte-for-byte.")
    let proof = XCTAttachment(string: "warm \(before)\ncold \(after)")
    proof.name = "Durable workspace, JPEG and Settings SHA-256"
    proof.lifetime = .keepAlways
    add(proof)
    tapWitness(app.tabBars.buttons["Settings"], in: app)
    checkWitnessSettings(in: app)
    tapWitness(app.tabBars.buttons["Projects"], in: app)
    tapWitness(app.buttons["project-site-map"], in: app)
    checkWitnessPin(in: app)
    backWitness(from: "Site map", to: project, in: app)
    openWitnessDraft(draft, in: app)
    checkWitnessDraft(draft, note: note, in: app)
    tapWitness(app.navigationBars["Field note"].buttons["Done"], in: app)
    XCTAssertTrue(app.navigationBars[project].waitForExistence(timeout: 10))
    app.terminate()
  }

  private func witnessInput(_ identifier: String, in app: XCUIApplication) -> XCUIElement {
    app.descendants(matching: .any).matching(identifier: identifier).firstMatch
  }

  private func tapWitness(
    _ element: XCUIElement, in app: XCUIApplication, scrollingUp: Bool = true
  ) {
    for _ in 0..<5 {
      if element.isHittable && element.isEnabled { break }
      if element.isHittable { break }
      if scrollingUp { app.swipeUp() } else { app.swipeDown() }
    }
    XCTAssertTrue(element.waitForExistence(timeout: 5), app.debugDescription)
    let ready = XCTNSPredicateExpectation(
      predicate: NSPredicate(format: "hittable == true AND enabled == true"), object: element)
    XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 6), .completed, app.debugDescription)
    element.tap()
  }

  private func backWitness(from screen: String, to destination: String, in app: XCUIApplication) {
    let bar = app.navigationBars[screen]
    let named = bar.buttons[destination]
    tapWitness(named.exists ? named : bar.buttons["Back"], in: app)
    XCTAssertTrue(app.navigationBars[destination].waitForExistence(timeout: 10))
  }

  private func typeWitness(_ value: String, into element: XCUIElement, in app: XCUIApplication) {
    tapWitness(element, in: app)
    element.typeText(value)
  }

  private func openWitnessDraft(_ title: String, in app: XCUIApplication) {
    tapWitness(app.buttons.matching(NSPredicate(format: "label CONTAINS %@", title)).firstMatch, in: app)
    XCTAssertTrue(app.navigationBars["Field note"].waitForExistence(timeout: 10))
  }

  private func checkWitnessDraft(_ title: String, note: String, in app: XCUIApplication) {
    let titleInput = witnessInput("entry-title", in: app)
    XCTAssertTrue(titleInput.waitForExistence(timeout: 5))
    XCTAssertEqual(titleInput.value as? String, title)
    XCTAssertEqual(app.textViews["entry-note"].value as? String, note)
    let photoCount = app.staticTexts["PHOTOS · 1/8"]
    for _ in 0..<4 {
      if photoCount.waitForExistence(timeout: 2) { return }
      app.swipeUp()
    }
    XCTFail("The ordinary editor never showed one attached photo.")
  }

  private func checkWitnessPin(in app: XCUIApplication) {
    XCTAssertTrue(app.navigationBars["Site map"].waitForExistence(timeout: 5))
    XCTAssertTrue(app.buttons["Edit site pin"].waitForExistence(timeout: 10), app.debugDescription)
    for expected in ["37.42", "122.08"] {
      let coordinate = app.descendants(matching: .any).matching(
        NSPredicate(format: "label CONTAINS %@ OR value CONTAINS %@", expected, expected)
      ).firstMatch
      XCTAssertTrue(coordinate.waitForExistence(timeout: 5), app.debugDescription)
    }
  }

  private func checkWitnessSettings(in app: XCUIApplication) {
    let appearance = app.buttons["settings-appearance"]
    XCTAssertTrue(appearance.waitForExistence(timeout: 5))
    XCTAssertEqual(appearance.value as? String, "Dark")
    XCTAssertFalse(app.staticTexts["settings-save-failed"].exists)
  }

  private func witnessDiskCheckpoint(in app: XCUIApplication) -> String {
    tapWitness(app.tabBars.buttons["On device"], in: app)
    XCTAssertTrue(app.staticTexts["1 PENDING CHANGE"].waitForExistence(timeout: 5))
    let readback = witnessInput("ordinary-witness-storage", in: app)
    XCTAssertTrue(readback.waitForExistence(timeout: 10), app.debugDescription)
    let ready = XCTNSPredicateExpectation(
      predicate: NSPredicate(format: "value BEGINSWITH %@", "verified:"), object: readback)
    XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 10), .completed,
      "Invalid durable checkpoint: \(String(describing: readback.value))")
    let value = readback.value as? String ?? ""
    XCTAssertNotNil(value.range(of: #"^verified(?::[0-9a-f]{64}){3}$"#, options: .regularExpression))
    return value
  }
}
