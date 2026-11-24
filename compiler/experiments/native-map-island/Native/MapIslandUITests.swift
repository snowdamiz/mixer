import XCTest

@MainActor
final class MapIslandUITests: XCTestCase {
    func testSignedSiteMoveAndRefusedPlacementsPreserveVisibleMap() {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launch()

        let pin = app.descendants(matching: .any).matching(identifier: "site-pin").firstMatch
        let camera = app.staticTexts["map-camera-center"]
        let surface = app.staticTexts["map-surface-identity"]
        let accepted = app.staticTexts["map-accepted-state"]
        let details = app.staticTexts["site-details"]
        let result = app.staticTexts["release-result"]

        XCTAssertTrue(result.waitForExistence(timeout: 15), app.debugDescription)
        XCTAssertEqual(result.label, "Initial site accepted")
        XCTAssertTrue(pin.waitForExistence(timeout: 15), app.debugDescription)
        XCTAssertEqual(pin.value as? String, "37.774900,-122.419400")
        XCTAssertLessThan(pin.frame.midY, details.frame.midY)
        XCTAssertEqual(accepted.label, "standard · 1")
        let mountedIdentity = surface.value as? String
        XCTAssertTrue(mountedIdentity?.hasSuffix("/project-site-map/1") == true)

        app.buttons["Apply signed update"].tap()
        XCTAssertTrue(result.wait(for: \.label, toEqual: "Signed update accepted", timeout: 10))
        let movedPin = app.descendants(matching: .any).matching(NSPredicate(
            format: "identifier == %@ AND value == %@", "site-pin", "40.689200,-74.044500"
        )).firstMatch
        XCTAssertTrue(movedPin.waitForExistence(timeout: 15), app.debugDescription)
        let movedCamera = app.staticTexts.matching(NSPredicate(
            format: "identifier == %@ AND label BEGINSWITH %@ AND label CONTAINS %@",
            "map-camera-center", "40.68", ",-74.04"
        )).firstMatch
        XCTAssertTrue(movedCamera.waitForExistence(timeout: 15), camera.label)
        XCTAssertTrue(Self.isNearUpdatedSite(camera.label), camera.label)
        XCTAssertGreaterThan(pin.frame.midY, details.frame.midY)
        XCTAssertEqual(surface.value as? String, mountedIdentity)
        XCTAssertEqual(accepted.label, "satellite · 2")

        for (button, refusal) in [
            ("Try unknown island", "Refused unknown island"),
            ("Try missing grant", "Refused missing grant"),
            ("Try wrong schema", "Refused schema mismatch"),
        ] {
            app.buttons[button].tap()
            XCTAssertTrue(result.wait(for: \.label, toEqual: refusal, timeout: 10))
            XCTAssertEqual(pin.value as? String, "40.689200,-74.044500")
            XCTAssertGreaterThan(pin.frame.midY, details.frame.midY)
            XCTAssertTrue(Self.isNearUpdatedSite(camera.label), camera.label)
            XCTAssertEqual(surface.value as? String, mountedIdentity)
            XCTAssertEqual(accepted.label, "satellite · 2")
        }
    }

    private static func isNearUpdatedSite(_ reading: String) -> Bool {
        let components = reading.split(separator: ",").compactMap { Double($0) }
        guard components.count == 2 else { return false }
        return abs(components[0] - 40.6892) < 0.005 && abs(components[1] - -74.0445) < 0.005
    }
}
