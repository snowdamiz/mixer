import Foundation
import XCTest

final class S4NativeUITests: XCTestCase {
    @MainActor
    func testInvalidFirstFrameBoundary() {
        continueAfterFailure = false
        let app = XCUIApplication(bundleIdentifier: "dev.mixer.fixture.s4native")
        defer { app.terminate() }
        let store = UUID()
        attach("fixture-ids", store.uuidString)
        open(app, store, "invalidFirst", status: "invalid first frame rejected")
        XCTAssertTrue(app.staticTexts["Ready"].exists)
        close(app, disk: "empty")
    }

    @MainActor
    func testSignedNativeFrameFailureStaleDeliveryAndOfflineRelaunch() throws {
        continueAfterFailure = false
        let app = XCUIApplication(bundleIdentifier: "dev.mixer.fixture.s4native")
        defer { app.terminate() }
        let store = UUID()
        let invalidStore = UUID()
        attach("fixture-ids", "\(store.uuidString)\n\(invalidStore.uuidString)")

        open(app, store, "cold", status: "bundled fallback")
        XCTAssertTrue(app.staticTexts["Ready"].exists)
        tap("Save sample", app)
        waitFor(app.staticTexts["s4-save"], "bundled action routed", app)
        XCTAssertTrue(app.staticTexts["s4-detail"].label.contains("effects=closed"))
        close(app, disk: "empty")

        open(app, invalidStore, "invalidFirst", status: "invalid first frame rejected")
        XCTAssertTrue(app.staticTexts["Ready"].exists)
        XCTAssertTrue(app.staticTexts["s4-detail"].label.contains("effects=closed"))
        close(app, disk: "empty")

        open(app, store, "baseline", status: "baseline healthy")
        let baseline = try evidence(app, phase: "baseline", sequence: "1")
        XCTAssertTrue(app.staticTexts["Ready"].exists)
        tap("Save sample", app)
        waitFor(app.staticTexts["s4-save"], "post-health tap delivered; stale envelope refused", app)
        XCTAssertTrue(app.staticTexts["Saved sample"].exists)
        close(app, disk: "AAH+/w==")

        open(app, store, "invalidRetained", status: "invalidRetained healthy")
        let recovered = try evidence(app, phase: "invalid-retained", sequence: "2")
        XCTAssertEqual(recovered["candidate"], baseline["candidate"])
        XCTAssertNotEqual(recovered["launch"], baseline["launch"])
        XCTAssertTrue(app.staticTexts["Ready"].exists)
        close(app, disk: "AAH+/w==")

        open(app, store, "reviewed", status: "reviewed healthy")
        let reviewed = try evidence(app, phase: "reviewed", sequence: "3")
        XCTAssertNotEqual(reviewed["candidate"], baseline["candidate"])
        XCTAssertTrue(app.staticTexts["فحص المضخة 07"].exists)
        XCTAssertTrue(app.buttons["وضع علامة مكتملة"].isHittable)
        close(app, disk: "AAH+/w==")

        open(app, store, "rollback", status: "rollback healthy")
        let rollback = try evidence(app, phase: "rollback", sequence: "4")
        XCTAssertNotEqual(rollback["candidate"], reviewed["candidate"])
        XCTAssertNotEqual(rollback["candidate"], baseline["candidate"])
        XCTAssertTrue(app.staticTexts["Ready"].exists)
        close(app, disk: "AAH+/w==")

        open(app, store, "offline", status: "offline healthy")
        let offline = try evidence(app, phase: "offline", sequence: "4")
        XCTAssertEqual(offline["candidate"], rollback["candidate"])
        XCTAssertNotEqual(offline["launch"], rollback["launch"])
        XCTAssertNotEqual(offline["instance"], rollback["instance"])
        XCTAssertEqual(offline["readback"], "AAH+/w==")
        XCTAssertTrue(app.staticTexts["Ready"].exists)
        close(app, disk: "AAH+/w==")
    }

    @MainActor
    func testNativeTapBeforeAndAfterDisplayAcknowledgment() throws {
        continueAfterFailure = false
        let app = XCUIApplication(bundleIdentifier: "dev.mixer.fixture.s4native")
        defer { app.terminate() }
        let beforeStore = UUID()
        let afterStore = UUID()
        let offlineStore = UUID()
        attach("fixture-ids", """
            beforeReceipt=\(beforeStore)
            retiredCallback=\(afterStore)
            freshProcess=\(offlineStore)
            """)

        open(app, beforeStore, "tapBeforeReceipt", status: "revision 1 proof held, provisional")
        let before = try evidence(app, phase: "before-receipt-trial", sequence: "1")
        let saveBeforeReceipt = app.buttons["Save sample"]
        XCTAssertTrue(saveBeforeReceipt.exists)
        XCTAssertFalse(saveBeforeReceipt.isEnabled)
        XCTAssertFalse(saveBeforeReceipt.frame.isEmpty)
        // A coordinate gesture still reaches the presented control's location
        // when XCTest would refuse an accessibility action on a disabled button.
        saveBeforeReceipt.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
        tap("Check refused Save tap", app)
        waitFor(app.staticTexts["s4-save"], "pre-receipt tap refused; no callback or write", app)
        XCTAssertTrue(app.staticTexts["Ready"].exists)
        XCTAssertFalse(app.staticTexts["Saved sample"].exists)
        tap("Release display acknowledgment", app)
        waitFor(app.staticTexts["s4-status"], "tapBeforeReceipt healthy", app)
        close(app, disk: "empty")

        open(app, afterStore, "tapAfterReceipt", status: "revision 1 proof held, provisional")
        let after = try evidence(app, phase: "after-receipt-trial", sequence: "1")
        XCTAssertNotEqual(before["candidate"], after["candidate"])
        let beforePayload = try XCTUnwrap(before["payload"])
        let afterPayload = try XCTUnwrap(after["payload"])
        XCTAssertEqual(beforePayload.count, 64)
        XCTAssertEqual(beforePayload, afterPayload)
        XCTAssertFalse(app.buttons["Save sample"].isEnabled)
        XCTAssertNotEqual(before["launch"], after["launch"])
        XCTAssertNotEqual(before["instance"], after["instance"])
        XCTAssertEqual(before["readback"], "empty")
        XCTAssertEqual(after["readback"], "empty")
        saveAfterReceipt(app)

        let failed = try triggerPostIntentFailure(app, store: afterStore, mode: "postIntentFailure",
                                                  retained: after, phase: "retired-callback")
        waitFor(app.staticTexts["s4-status"], "post-intent recovered healthy", app)
        waitFor(app.staticTexts["s4-save"], "retired callback refused across owner replacement", app)
        let recovered = try evidence(app, phase: "post-intent-replacement", sequence: "2")
        XCTAssertEqual(recovered["candidate"], after["candidate"])
        XCTAssertEqual(recovered["pid"], failed["pid"])
        XCTAssertNotEqual(recovered["launch"], failed["launch"])
        XCTAssertTrue(app.staticTexts["Ready"].exists)
        XCTAssertFalse(app.staticTexts["فحص المضخة 07"].exists)
        XCTAssertFalse(app.staticTexts["Saved sample"].exists)
        close(app, disk: "AAH+/w==")

        // The offline store has no intervening retained launch or ordinary close.
        open(app, offlineStore, "tapAfterReceipt", status: "revision 1 proof held, provisional")
        let offlineBaseline = try evidence(app, phase: "offline-baseline-trial", sequence: "1")
        XCTAssertEqual(offlineBaseline["payload"], afterPayload)
        XCTAssertEqual(offlineBaseline["readback"], "empty")
        saveAfterReceipt(app)
        let offlineFailed = try triggerPostIntentFailure(app, store: offlineStore, mode: "postIntentFailureExit",
                                                         retained: offlineBaseline, phase: "fresh-process")
        let settled = "post-intent owner closed, disk=AAH+/w=="
        waitFor(app.staticTexts["s4-status"], settled, app)
        attach("post-intent-settled-before-exit", settled)
        app.terminate()
        XCTAssertEqual(app.state, .notRunning)

        open(app, offlineStore, "postIntentOffline", status: "postIntentOffline healthy")
        let offline = try evidence(app, phase: "post-intent-offline", sequence: "2")
        XCTAssertEqual(offline["candidate"], offlineBaseline["candidate"])
        XCTAssertNotEqual(offline["launch"], offlineFailed["launch"])
        XCTAssertNotEqual(offline["pid"], offlineFailed["pid"])
        XCTAssertNotEqual(offline["instance"], offlineFailed["instance"])
        XCTAssertEqual(offline["readback"], "AAH+/w==")
        XCTAssertTrue(app.staticTexts["Ready"].exists)
        XCTAssertFalse(app.staticTexts["فحص المضخة 07"].exists)
        XCTAssertFalse(app.staticTexts["Saved sample"].exists)
        close(app, disk: "AAH+/w==")
    }

    @MainActor
    private func saveAfterReceipt(_ app: XCUIApplication) {
        tap("Release display acknowledgment", app)
        waitFor(app.staticTexts["s4-status"], "tapAfterReceipt healthy", app)
        tap("Save sample", app)
        waitFor(app.staticTexts["s4-save"], "post-receipt tap delivered once; late callback refused", app)
        XCTAssertTrue(app.staticTexts["Saved sample"].exists)
        close(app, disk: "AAH+/w==")
    }

    @MainActor
    private func triggerPostIntentFailure(_ app: XCUIApplication, store: UUID, mode: String,
                                          retained: [String: String], phase: String) throws -> [String: String] {
        open(app, store, mode, status: "post-intent proof held, provisional")
        let failed = try evidence(app, phase: "\(phase)-post-intent-failed", sequence: "2")
        XCTAssertNotEqual(failed["candidate"], retained["candidate"])
        XCTAssertEqual(failed["readback"], "AAH+/w==")
        XCTAssertTrue(app.staticTexts["فحص المضخة 07"].exists)
        let provisionalToggle = app.buttons["وضع علامة مكتملة"]
        XCTAssertTrue(provisionalToggle.exists)
        XCTAssertFalse(provisionalToggle.isEnabled)
        tap("Attach duplicate guest screen", app)
        return failed
    }

    @MainActor
    func testSharedThemeRendersInBundledAndSignedGuest() throws {
        continueAfterFailure = false
        let app = XCUIApplication(bundleIdentifier: "dev.mixer.fixture.s4native")
        defer { app.terminate() }
        let controlStore = UUID()
        let themedStore = UUID()
        attach("fixture-ids", "\(controlStore.uuidString)\n\(themedStore.uuidString)")

        open(app, controlStore, "cold", status: "bundled fallback", flag: "--s4-platform-control")
        let control = try themeSample(app, phase: "platform-bundled-r1")
        control.assertDefault()
        close(app, disk: "empty")

        open(app, themedStore, "cold", status: "bundled fallback", flag: "--s4-shared-theme")
        let bundled = try themeSample(app, phase: "themed-bundled-r1")
        bundled.assertTheme()
        tap("Save sample", app)
        waitFor(app.staticTexts["s4-save"], "bundled action routed", app)
        close(app, disk: "empty")

        open(app, themedStore, "baseline", status: "baseline healthy", flag: "--s4-shared-theme")
        _ = try evidence(app, phase: "themed-signed-guest", sequence: "1")
        let guest = try themeSample(app, phase: "themed-guest-r1")
        guest.assertTheme()
        guest.assertMatches(bundled)
        tap("Save sample", app)
        waitFor(app.staticTexts["s4-save"], "post-health tap delivered; stale envelope refused", app)
        XCTAssertTrue(app.staticTexts["Saved sample"].exists)
        close(app, disk: "AAH+/w==")
    }

    @MainActor
    private func themeSample(_ app: XCUIApplication, phase: String) throws -> S4ThemeSample {
        let ready = app.staticTexts["Ready"]
        let save = app.buttons["Save sample"]
        XCTAssertTrue(ready.exists)
        XCTAssertTrue(save.exists && save.isEnabled && save.isHittable)
        attachScreenshot(app.screenshot(), name: phase + "-window")
        let readyShot = ready.screenshot()
        let saveShot = save.screenshot()
        attachScreenshot(readyShot, name: phase + "-ready")
        attachScreenshot(saveShot, name: phase + "-save")
        let sample = try S4ThemeSample(readyPixels: S4ThemePixels(readyShot), savePixels: S4ThemePixels(saveShot))
        attach(phase + "-pixels", sample.evidence)
        return sample
    }

    private func attachScreenshot(_ screenshot: XCUIScreenshot, name: String) {
        let attachment = XCTAttachment(screenshot: screenshot)
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    @MainActor
    private func open(_ app: XCUIApplication, _ store: UUID, _ mode: String, status: String, flag: String? = nil) {
        app.launchArguments = ["--s4-fixture", store.uuidString, mode]
        if let flag { app.launchArguments.append(flag) }
        app.launchEnvironment = [:]
        app.launch()
        waitFor(app.staticTexts["s4-status"], status, app)
    }

    @MainActor
    private func close(_ app: XCUIApplication, disk: String) {
        tap("Close S4 owner", app)
        let value = "owner closed, disk=" + disk
        waitFor(app.staticTexts["s4-status"], value, app)
        attach("after-close", value)
        app.terminate()
        XCTAssertEqual(app.state, .notRunning)
    }

    @MainActor
    private func waitFor(_ element: XCUIElement, _ label: String, _ app: XCUIApplication) {
        let status = app.staticTexts["s4-status"]
        let predicate = NSPredicate(
            format: "(target.exists == true AND target.label == %@) OR (status.exists == true AND status.label BEGINSWITH %@)",
            label, "ERROR "
        )
        let expectation = XCTNSPredicateExpectation(predicate: predicate, object: ["target": element, "status": status])
        let result = XCTWaiter.wait(for: [expectation], timeout: 22)
        let actualStatus = status.exists ? status.label : "missing"
        let readback = status.exists ? (status.value as? String ?? "missing") : "missing"
        if readback != "pending" { attach("s4-boundary-readback", readback) }
        let matched = result == .completed && !actualStatus.hasPrefix("ERROR ") && element.exists && element.label == label
        if !matched {
            XCTFail("Expected \(label); status=\(actualStatus); readback=\(readback); tree=\(app.debugDescription)")
        }
    }

    @MainActor
    private func tap(_ title: String, _ app: XCUIApplication) {
        let button = app.buttons[title]
        let expectation = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == true AND enabled == true AND hittable == true"),
                                                    object: button)
        XCTAssertEqual(XCTWaiter.wait(for: [expectation], timeout: 7), .completed,
                       "Native \(title) is not reachable; status=\(app.staticTexts["s4-status"].label)")
        button.tap()
    }

    @MainActor
    private func evidence(_ app: XCUIApplication, phase: String, sequence: String) throws -> [String: String] {
        let marker = app.staticTexts["s4-detail"].label
        let fields = marker.split(separator: " ").map { $0.split(separator: "=", maxSplits: 1).map(String.init) }
        XCTAssertEqual(fields.count, phase.hasSuffix("-trial") ? 7 : 6)
        XCTAssertTrue(fields.allSatisfy { $0.count == 2 })
        let result = Dictionary(uniqueKeysWithValues: fields.map { ($0[0], $0[1]) })
        XCTAssertEqual(result["sequence"], sequence)
        for field in ["candidate", "launch", "instance", "pid", "readback"] {
            _ = try XCTUnwrap(result[field])
        }
        attach(phase, marker)
        return result
    }

    private func attach(_ name: String, _ value: String) {
        let attachment = XCTAttachment(string: value)
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}

extension S4NativeUITests {
    @MainActor
    func testDelayedHealthyRendererCallbackAcrossOwnerReplacement() throws {
        continueAfterFailure = false
        let app = XCUIApplication(bundleIdentifier: "dev.mixer.fixture.s4native")
        defer { app.terminate() }
        let store = UUID()
        attach("fixture-ids", store.uuidString)
        open(app, store, "healthyRendererReplacement", status: "original renderer healthy")
        let original = try evidence(app, phase: "original-renderer", sequence: "1")
        XCTAssertTrue(app.buttons["Save sample"].isEnabled)

        tap("Replace healthy S4 owner", app)
        waitFor(app.staticTexts["s4-status"], "replacement healthy; delayed callback refused", app)
        let replacement = try evidence(app, phase: "replacement-renderer", sequence: "1")
        XCTAssertEqual(replacement["candidate"], original["candidate"])
        XCTAssertEqual(replacement["instance"], original["instance"])
        XCTAssertEqual(replacement["pid"], original["pid"])
        XCTAssertNotEqual(replacement["launch"], original["launch"])
        XCTAssertEqual(replacement["readback"], "empty")

        tap("Save sample", app)
        waitFor(app.staticTexts["s4-save"], "replacement Save delivered once", app)
        close(app, disk: "AAH+/w==")
    }
}
