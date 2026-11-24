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

    @MainActor
    func testSettingsBoldTextRendersHeavierGlyphs() throws {
        // Keep cleanup reachable even if an XCTest interaction records a failure.
        continueAfterFailure = true
        let app = XCUIApplication(bundleIdentifier: "dev.mixer.fixture.up5theme")
        let settings = XCUIApplication(bundleIdentifier: "com.apple.Preferences")
        app.launchArguments = ["--contrast-probe", "--system-bold-text-probe"]
        defer { if app.state != .notRunning { app.terminate() } }

        retain(XCTAttachment(string: "com.apple.Preferences initial state: \(settings.state)"),
               "settings-launch")
        let original: Bool
        do {
            let rawValue = try settingsBoldTextSwitch(in: settings).value
            original = try boldTextValue(rawValue)
            recordSettings(settings, phase: "baseline", enabled: original, rawValue: rawValue)
        } catch {
            recordSettingsFailure(settings, phase: "baseline", error: error)
            throw error
        }

        let baseline = try captureSystemBoldText(app, enabled: original, phase: "baseline")
        app.terminate()
        defer {
            do {
                try setSettingsBoldText(original, in: settings, phase: "restored")
                app.launch()
                wait(app.staticTexts["fixture-status"], for: "bundled", app: app)
                let restoredSize = try observeSystemBoldText(app, enabled: original, phase: "restored")
                XCTAssertEqual(restoredSize, baseline.size, "Dynamic Type after restoring Bold Text")
            } catch {
                recordSettingsFailure(settings, phase: "restoration", error: error)
                XCTFail("Could not verify restoration to Bold Text \(original ? "On" : "Off"): \(error)")
            }
        }

        do {
            try setSettingsBoldText(!original, in: settings, phase: "changed")
        } catch {
            recordSettingsFailure(settings, phase: "change", error: error)
            throw error
        }
        let changed = try captureSystemBoldText(app, enabled: !original, phase: "changed")
        app.terminate()

        XCTAssertEqual(changed.size, baseline.size, "Bold Text comparison requires the same Dynamic Type size")
        let (regular, bold) = original ? (changed.sample, baseline.sample) : (baseline.sample, changed.sample)
        XCTAssertGreaterThan(bold.inkPixels, regular.inkPixels * 1.08)
        XCTAssertGreaterThan(bold.labelPixels, regular.labelPixels * 1.08)
    }

    private struct BoldTextFailure: LocalizedError {
        let errorDescription: String?
        init(_ message: String) { errorDescription = message }
    }

    @MainActor
    private func settingsBoldTextSwitch(in settings: XCUIApplication) throws -> XCUIElement {
        settings.activate()
        guard settings.wait(for: .runningForeground, timeout: 8) else {
            throw BoldTextFailure("com.apple.Preferences did not reach the foreground (\(settings.state))")
        }
        let displayPage = settings.navigationBars["Display & Text Size"]
        // Scope the switch to the system page before reading or changing it.
        if !displayPage.exists {
            if !settings.navigationBars["Accessibility"].exists {
                try openSettingsRow("Accessibility", in: settings)
            }
            try openSettingsRow("Display & Text Size", in: settings)
        }
        guard displayPage.waitForExistence(timeout: 5) else {
            throw BoldTextFailure("Expected the Display & Text Size navigation bar")
        }

        let boldLabel = NSPredicate(format: "label == %@", "Bold Text")
        let labeledSwitch = settings.switches.matching(boldLabel)
        let rowSwitch = settings.cells.containing(.staticText, identifier: "Bold Text").switches
        if labeledSwitch.firstMatch.waitForExistence(timeout: 3), labeledSwitch.count == 1 {
            return labeledSwitch.firstMatch
        }
        if rowSwitch.firstMatch.waitForExistence(timeout: 3), rowSwitch.count == 1 {
            return rowSwitch.firstMatch
        }
        throw BoldTextFailure("Expected one Bold Text switch on Display & Text Size")
    }

    @MainActor
    private func openSettingsRow(_ label: String, in settings: XCUIApplication) throws {
        let matches = settings.staticTexts.matching(NSPredicate(format: "label == %@", label))
        let row = matches.firstMatch
        for _ in 0..<4 {
            if row.waitForExistence(timeout: 2) { break }
            settings.swipeUp()
        }
        // XCUIElement.tap scrolls to an offscreen element in a scrollable container.
        guard row.waitForExistence(timeout: 5), matches.count == 1 else {
            throw BoldTextFailure("Expected one Settings row labeled \(label)")
        }
        row.tap()
    }

    private func boldTextValue(_ rawValue: Any?) throws -> Bool {
        switch (rawValue as? String)?.lowercased() {
        case "1", "on": true
        case "0", "off": false
        default: throw BoldTextFailure("Unreadable Bold Text switch value: \(String(reflecting: rawValue))")
        }
    }

    @MainActor
    private func setSettingsBoldText(_ enabled: Bool, in settings: XCUIApplication, phase: String) throws {
        let toggle = try settingsBoldTextSwitch(in: settings)
        let before = toggle.value
        if try boldTextValue(before) != enabled {
            guard toggle.isEnabled && toggle.isHittable else {
                throw BoldTextFailure("The Bold Text switch cannot be tapped in phase \(phase)")
            }
            let frame = toggle.frame
            guard !frame.isEmpty, frame.width.isFinite, frame.height.isFinite else {
                throw BoldTextFailure("Invalid Bold Text switch frame in phase \(phase): \(frame)")
            }
            // English LTR Settings on iOS 26.5 exposes a 321-by-28 pt switch frame
            // that spans the label and control. The track sits at the trailing edge.
            let spansRow = frame.width >= 3 * frame.height
            let dx = spansRow ? (frame.width - 25) / frame.width : 0.5
            let target = toggle.coordinate(withNormalizedOffset: CGVector(dx: dx, dy: 0.5))
            let point = target.screenPoint
            guard frame.contains(point) else {
                throw BoldTextFailure("Bold Text tap \(point) is outside the switch frame \(frame) in phase \(phase)")
            }
            retain(XCTAttachment(string: "identifier=\(toggle.identifier) rawBefore=\(String(reflecting: before)) frame=\(frame) tap=\(point)"),
                   phase + "-settings-tap")
            target.tap()
        }
        let values = enabled ? ["1", "On", "on", "ON"] : ["0", "Off", "off", "OFF"]
        let readback = NSPredicate(format: "exists == true AND value IN %@", values)
        let waiter = XCTNSPredicateExpectation(predicate: readback, object: toggle)
        let result = XCTWaiter.wait(for: [waiter], timeout: 8)
        let after = toggle.value
        guard result == .completed, try boldTextValue(after) == enabled else {
            throw BoldTextFailure("The Bold Text switch did not read back \(enabled) in phase \(phase). Before: \(String(reflecting: before)). After: \(String(reflecting: after)).")
        }
        recordSettings(settings, phase: phase, enabled: enabled, rawValue: after)
    }

    @MainActor
    private func recordSettings(_ settings: XCUIApplication, phase: String, enabled: Bool, rawValue: Any?) {
        let description = "Settings Bold Text \(phase): \(enabled ? "On" : "Off")"
        XCTContext.runActivity(named: description) { _ in
            retain(XCTAttachment(string: "\(description)\nrawValue=\(String(reflecting: rawValue))"),
                   phase + "-settings-value")
            retain(XCTAttachment(screenshot: settings.screenshot()), phase + "-settings-switch")
        }
    }

    @MainActor
    private func recordSettingsFailure(_ settings: XCUIApplication, phase: String, error: Error) {
        retain(XCTAttachment(string: "\(error.localizedDescription)\nstate=\(settings.state)\n\(settings.debugDescription)"),
               phase + "-settings-diagnostics")
        if settings.state == .runningForeground {
            retain(XCTAttachment(screenshot: settings.screenshot()), phase + "-settings-failure")
        }
    }

    @MainActor
    private func observeSystemBoldText(_ app: XCUIApplication, enabled: Bool, phase: String) throws -> String {
        let observation = app.staticTexts["bold-text-observation"]
        let weight = enabled ? "bold" : "(regular|unspecified)"
        let condition = NSPredicate(format: "exists == true AND label MATCHES %@",
                                    "system=\(enabled) swiftui=\(weight) size=.+")
        let expectation = XCTNSPredicateExpectation(predicate: condition, object: observation)
        let result = XCTWaiter.wait(for: [expectation], timeout: 10)
        let label = observation.exists ? observation.label : "missing"
        retain(XCTAttachment(string: label), phase + "-native-bold-text-readback")
        guard result == .completed, let size = label.split(separator: " ").last else {
            retain(XCTAttachment(screenshot: app.screenshot()), phase + "-fixture-failure")
            throw BoldTextFailure("Expected UIKit and SwiftUI Bold Text \(enabled) in phase \(phase); observed \(label)")
        }
        return String(size)
    }

    @MainActor
    private func captureSystemBoldText(_ app: XCUIApplication, enabled: Bool, phase: String) throws -> (sample: Sample, size: String) {
        app.launch()
        wait(app.staticTexts["fixture-status"], for: "bundled", app: app)
        wait(app.staticTexts["contrast-observation"], for: "swiftui=false system=false", app: app)
        let size = try observeSystemBoldText(app, enabled: enabled, phase: phase)
        let sample = try capture(app, phase: phase + "-settings-bold-text-" + (enabled ? "on" : "off"), palette: .light)
        expectTheme(sample)
        let text = app.staticTexts["Ready"]
        let save = app.buttons["Save sample"]
        let disabled = app.buttons["Unavailable"]
        retain(XCTAttachment(string: """
            \(text.elementType) \(text.label)
            \(save.elementType) \(save.label) enabled=\(save.isEnabled)
            \(disabled.elementType) \(disabled.label) enabled=\(disabled.isEnabled)
            """), phase + "-native-roles")
        return (sample, size)
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
        let labelPixels: Double
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
            labelPixels: buttonPixels.fraction(of: palette.label) * Double(buttonPixels.width * buttonPixels.height),
            disabledInk: disabledPixels.fraction(of: palette.disabledInk))
        retain(XCTAttachment(string: "text=\(sample.ink) inkPixels=\(sample.inkPixels) fill=\(sample.fill) label=\(sample.label) labelPixels=\(sample.labelPixels) disabled=\(sample.disabledInk)"),
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
