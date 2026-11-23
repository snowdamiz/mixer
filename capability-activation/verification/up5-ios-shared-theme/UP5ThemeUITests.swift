import XCTest

final class UP5ThemeUITests: XCTestCase {
    @MainActor
    func testProductThemeOnBundledAndSignedGuest() throws {
        continueAfterFailure = false
        let app = XCUIApplication(bundleIdentifier: "dev.mixer.fixture.up5theme")
        defer { if app.state != .notRunning { app.terminate() } }

        app.launchArguments = ["--platform-control"]
        app.launch()
        wait(app.staticTexts["fixture-status"], for: "bundled", app: app)
        let reference = try capture(app, phase: "unthemed-light", palette: .light)
        XCTAssertLessThan(reference.ink, 0.002)
        XCTAssertLessThan(reference.fill, 0.002)
        app.terminate()

        for guest in [false, true] {
            app.launchArguments = guest ? ["--signed-guest"] : []
            app.launch()
            let mode = guest ? "signed" : "bundled"
            wait(app.staticTexts["fixture-status"], for: guest ? "signed guest healthy" : "bundled", app: app)
            try expectTheme(capture(app, phase: mode + "-light", palette: .light))
            app.buttons["Use dark"].tap()
            try expectTheme(capture(app, phase: mode + "-dark", palette: .dark))

            let disabled = app.buttons["Unavailable"]
            XCTAssertTrue(disabled.exists)
            XCTAssertFalse(disabled.isEnabled)
            XCTAssertTrue(app.staticTexts["Ready"].exists)
            app.buttons["Save sample"].tap()
            if guest {
                XCTAssertTrue(app.staticTexts["Saved sample"].waitForExistence(timeout: 10))
            } else {
                wait(app.staticTexts["fixture-result"], for: "bundled action routed", app: app)
            }
            app.buttons["Close fixture"].tap()
            wait(app.staticTexts["fixture-status"], for: guest ? "closed, disk=AAH+/w==" : "closed, disk=empty", app: app)
            app.terminate()
        }
    }

    private struct Palette {
        let ink: ThemePixels.RGB
        let fill: ThemePixels.RGB
        let label: ThemePixels.RGB
        let disabledInk: ThemePixels.RGB

        static let light = Palette(ink: .init(8, 123, 103), fill: .init(82, 36, 138),
                                   label: .init(218, 255, 171), disabledInk: .init(169, 81, 43))
        static let dark = Palette(ink: .init(250, 170, 81), fill: .init(16, 117, 163),
                                  label: .init(255, 239, 199), disabledInk: .init(190, 152, 228))
    }

    private struct Sample {
        let ink: Double
        let fill: Double
        let label: Double
        let disabledInk: Double
    }

    @MainActor
    private func capture(_ app: XCUIApplication, phase: String, palette: Palette) throws -> Sample {
        let text = app.staticTexts["Ready"]
        let button = app.buttons["Save sample"]
        let disabled = app.buttons["Unavailable"]
        XCTAssertTrue(text.exists)
        XCTAssertTrue(button.exists && button.isEnabled && button.isHittable)
        XCTAssertTrue(disabled.exists && !disabled.isEnabled)
        let textShot = text.screenshot()
        let buttonShot = button.screenshot()
        let disabledShot = disabled.screenshot()
        for (name, shot) in [("window", app.screenshot()), ("text", textShot),
                             ("button", buttonShot), ("disabled", disabledShot)] {
            retain(XCTAttachment(screenshot: shot), phase + "-" + name)
        }
        let textPixels = try ThemePixels(textShot)
        let buttonPixels = try ThemePixels(buttonShot)
        let disabledPixels = try ThemePixels(disabledShot)
        let sample = Sample(
            ink: textPixels.fraction(of: palette.ink),
            fill: buttonPixels.fraction(of: palette.fill, x: 0.08..<0.14, y: 0.27..<0.73),
            label: buttonPixels.fraction(of: palette.label, x: 0.15..<0.85, y: 0.20..<0.80),
            disabledInk: disabledPixels.fraction(of: palette.disabledInk))
        retain(XCTAttachment(string: "text=\(sample.ink) fill=\(sample.fill) label=\(sample.label) disabled=\(sample.disabledInk)"),
               phase + "-pixels")
        return sample
    }

    private func expectTheme(_ sample: Sample, file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertGreaterThan(sample.ink, 0.008, file: file, line: line)
        XCTAssertGreaterThan(sample.fill, 0.95, file: file, line: line)
        XCTAssertGreaterThan(sample.label, 0.01, file: file, line: line)
        XCTAssertGreaterThan(sample.disabledInk, 0.008, file: file, line: line)
    }

    @MainActor
    private func wait(_ element: XCUIElement, for value: String, app: XCUIApplication) {
        let condition = NSPredicate(format: "exists == true AND label == %@", value)
        let result = XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: condition, object: element)], timeout: 22)
        XCTAssertEqual(result, .completed, "Expected \(value); status=\(app.staticTexts["fixture-status"].label)")
    }

    private func retain(_ attachment: XCTAttachment, _ name: String) {
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
