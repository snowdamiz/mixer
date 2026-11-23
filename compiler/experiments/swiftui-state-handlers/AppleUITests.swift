import XCTest

private struct JourneyFailure: Error, CustomStringConvertible {
    let description: String
}

private func expect(_ condition: @autoclosure () -> Bool, _ message: String) throws {
    guard condition() else { throw JourneyFailure(description: message) }
}

final class AppleUITests: XCTestCase {
    @MainActor
    func testStateJourney() throws {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launch()
        let labels = app.staticTexts.matching(NSPredicate(
            format: "label BEGINSWITH %@ OR label BEGINSWITH %@ OR label BEGINSWITH %@",
            "Values ", "Row ", "Branch "
        ))

        func displayedLabels() -> [String] {
            labels.allElementsBoundByIndex
                .map { (position: $0.frame.midY, label: $0.label) }
                .sorted { $0.position < $1.position }
                .map(\.label)
        }

        var trace: [String] = []
        for (index, checkpoint) in Checkpoint.journey.enumerated() {
            if let action = checkpoint.action {
                let button = app.buttons[action]
                try expect(button.waitForExistence(timeout: 5), action)
                try expect(button.isHittable, action)
                button.tap()
            }
            let deadline = ProcessInfo.processInfo.systemUptime + 5
            var observed = displayedLabels()
            while observed != checkpoint.labels && ProcessInfo.processInfo.systemUptime < deadline {
                RunLoop.main.run(until: Date().addingTimeInterval(0.05))
                observed = displayedLabels()
            }
            try expect(observed == checkpoint.labels, "checkpoint \(index): \(observed)")
            trace.append("s3 checkpoint \(index) | " + observed.joined(separator: " | "))
        }

        let attachment = XCTAttachment(
            data: Data((trace.joined(separator: "\n") + "\n").utf8),
            uniformTypeIdentifier: "public.utf8-plain-text"
        )
        attachment.name = "S3 Apple SwiftUI trace"
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
