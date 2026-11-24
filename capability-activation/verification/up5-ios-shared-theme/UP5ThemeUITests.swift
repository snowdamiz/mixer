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

    @MainActor
    func testIncreasedContrastOnBundledAndSignedGuest() throws {
        continueAfterFailure = false
        let app = XCUIApplication(bundleIdentifier: "dev.mixer.fixture.up5theme")
        defer { if app.state != .notRunning { app.terminate() } }

        for guest in [false, true] {
            app.launchArguments = guest ? ["--contrast-probe", "--signed-guest"] : ["--contrast-probe"]
            app.launch()
            let mode = guest ? "signed" : "bundled"
            wait(app.staticTexts["fixture-status"], for: guest ? "signed guest healthy" : "bundled", app: app)
            wait(app.staticTexts["contrast-observation"], for: "swiftui=true system=true", app: app)
            try expectContrast(app, phase: mode + "-contrast-light", dark: false)
            app.buttons["Use dark"].tap()
            XCTAssertTrue(app.buttons["Use light"].waitForExistence(timeout: 5))
            try expectContrast(app, phase: mode + "-contrast-dark", dark: true)

            app.buttons["Save sample"].tap()
            if guest {
                XCTAssertTrue(app.staticTexts["Saved sample"].waitForExistence(timeout: 10))
            } else {
                wait(app.staticTexts["fixture-result"], for: "bundled action routed", app: app)
            }
            app.buttons["Close fixture"].tap()
            wait(app.staticTexts["fixture-status"], for: guest ? "closed, disk=AAH+/w==" : "closed, disk=empty", app: app)
            if !guest { XCTAssertEqual(app.staticTexts["fixture-result"].label, "bundled action routed") }
            app.terminate()
        }
    }

    @MainActor
    func testHeldPressRendersPressedFillAndRoutesOnRelease() throws {
        continueAfterFailure = false
        let app = XCUIApplication(bundleIdentifier: "dev.mixer.fixture.up5theme")
        defer { if app.state != .notRunning { app.terminate() } }

        app.launchArguments = ["--contrast-probe", "--held-press-probe"]
        app.launch()
        wait(app.staticTexts["fixture-status"], for: "bundled", app: app)
        wait(app.staticTexts["contrast-observation"], for: "swiftui=false system=false", app: app)
        try expectTheme(capture(app, phase: "before-touch", palette: .light))
        XCTAssertEqual(app.staticTexts["fixture-result"].label, "empty")

        let holdDuration = 2.0
        let save = app.buttons["Save sample"]
        save.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).press(forDuration: holdDuration)
        let observation = app.staticTexts["held-sample"].label
        retain(XCTAttachment(string: observation), "native-held-pixels")
        let fields = observation.split(separator: " ")
        guard fields.count == 5, fields.first == "captured" else {
            XCTFail("Expected a native window sample while the touch was active: \(observation)")
            return
        }
        XCTAssertGreaterThan(try XCTUnwrap(Double(fields[1])), 0.95)
        XCTAssertLessThan(try XCTUnwrap(Double(fields[2])), 0.01)
        XCTAssertEqual(fields[3], "0", "Save must still be unrouted during the touch")
        let elapsed = try XCTUnwrap(Double(fields[4]))
        XCTAssertGreaterThanOrEqual(elapsed, 0.4)
        XCTAssertLessThan(elapsed, holdDuration)

        wait(app.staticTexts["fixture-result"], for: "bundled action routed", app: app)
        try expectTheme(capture(app, phase: "after-release", palette: .light))
        app.buttons["Close fixture"].tap()
        wait(app.staticTexts["fixture-status"], for: "closed, disk=empty", app: app)
        XCTAssertEqual(app.staticTexts["fixture-result"].label, "bundled action routed")
    }

    @MainActor
    func testBoldTextTraitLoanRendersHeavierGlyphs() throws {
        continueAfterFailure = false
        let app = XCUIApplication(bundleIdentifier: "dev.mixer.fixture.up5theme")
        defer { if app.state != .notRunning { app.terminate() } }

        func measure(_ loan: String) throws -> Sample {
            app.launchArguments = ["--contrast-probe", "--" + loan + "-loan"]
            app.launch()
            wait(app.staticTexts["fixture-status"], for: "bundled", app: app)
            wait(app.staticTexts["contrast-observation"], for: "swiftui=false system=false", app: app)
            let sample = try capture(app, phase: loan + "-trait-loan", palette: .light)
            expectTheme(sample)
            app.terminate()
            return sample
        }
        let regular = try measure("regular")
        let bold = try measure("bold")
        XCTAssertGreaterThan(bold.inkPixels, regular.inkPixels * 1.08)
        XCTAssertGreaterThan(bold.label, regular.label * 1.08)
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
        let inkPixels: Double
        let fill: Double
        let label: Double
        let disabledInk: Double
    }

    @MainActor
    private func capture(_ app: XCUIApplication, phase: String, palette: Palette) throws -> Sample {
        let (textPixels, buttonPixels, disabledPixels) = try screenshots(app, phase: phase)
        let ink = textPixels.fraction(of: palette.ink)
        let sample = Sample(
            ink: ink, inkPixels: ink * Double(textPixels.width * textPixels.height),
            fill: buttonPixels.fraction(of: palette.fill, x: 0.08..<0.14, y: 0.27..<0.73),
            label: buttonPixels.fraction(of: palette.label, x: 0.15..<0.85, y: 0.20..<0.80),
            disabledInk: disabledPixels.fraction(of: palette.disabledInk))
        retain(XCTAttachment(string: "text=\(sample.ink) inkPixels=\(sample.inkPixels) fill=\(sample.fill) label=\(sample.label) disabled=\(sample.disabledInk)"),
               phase + "-pixels")
        return sample
    }

    @MainActor
    private func expectContrast(_ app: XCUIApplication, phase: String, dark: Bool) throws {
        let (text, button, disabled) = try screenshots(app, phase: phase)
        let black = ThemePixels.RGB(0, 0, 0)
        let white = ThemePixels.RGB(255, 255, 255)
        let ink = dark ? white : black
        let backdrop = dark ? black : white
        let standard = dark ? Palette.dark : Palette.light
        let textInk = text.fraction(of: ink)
        let textBackdrop = text.fraction(of: backdrop)
        let fill = button.fraction(of: backdrop, x: 0.08..<0.14, y: 0.27..<0.73)
        let label = button.fraction(of: ink, x: 0.15..<0.85, y: 0.20..<0.80)
        let disabledFill = disabled.fraction(of: backdrop, x: 0.08..<0.14, y: 0.27..<0.73)
        let disabledLabel = disabled.fraction(of: ink, x: 0.15..<0.85, y: 0.20..<0.80)
        let edgeBackdrop = button.fraction(of: backdrop, x: 0.22..<0.78, y: 0..<0.02)
        let edge = button.fraction(of: ink, x: 0.22..<0.78, y: 0.025..<0.045)
        let dashedEdge = disabled.fraction(of: ink, x: 0.22..<0.78, y: 0.025..<0.045)
        retain(XCTAttachment(string: """
            textInk=\(textInk) textBackdrop=\(textBackdrop) fill=\(fill) label=\(label)
            disabledFill=\(disabledFill) disabledLabel=\(disabledLabel)
            outer=\(edgeBackdrop) inner=\(edge) dashed=\(dashedEdge)
            """), phase + "-pixels")
        XCTAssertGreaterThan(textInk, 0.02)
        XCTAssertGreaterThan(textBackdrop, 0.60)
        XCTAssertGreaterThan(fill, 0.95)
        XCTAssertGreaterThan(label, 0.01)
        XCTAssertGreaterThan(disabledFill, 0.95)
        XCTAssertGreaterThan(disabledLabel, 0.01)
        XCTAssertGreaterThan(edgeBackdrop, 0.80)
        XCTAssertGreaterThan(edge, 0.50)
        XCTAssertGreaterThan(dashedEdge, 0.12)
        XCTAssertLessThan(dashedEdge, edge * 0.85)
        XCTAssertLessThan(text.fraction(of: standard.ink), 0.002)
        XCTAssertLessThan(button.fraction(of: standard.fill), 0.002)
    }

    @MainActor
    private func screenshots(_ app: XCUIApplication, phase: String) throws -> (ThemePixels, ThemePixels, ThemePixels) {
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
        return try (ThemePixels(XCTUnwrap(textShot.image.cgImage)),
                    ThemePixels(XCTUnwrap(buttonShot.image.cgImage)),
                    ThemePixels(XCTUnwrap(disabledShot.image.cgImage)))
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
