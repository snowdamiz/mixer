
    private struct Port: Decodable { let port: UInt16 }

    @MainActor private func advance(_ phase: String, control: UInt16) throws -> Data {
        let url = try XCTUnwrap(URL(string: "http://127.0.0.1:\(control)/\(phase)"))
        var request = URLRequest(url: url, timeoutInterval: 12)
        request.httpMethod = "POST"
        let token = try XCTUnwrap(ProcessInfo.processInfo.environment["F11_CONTROL_TOKEN"])
        request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
        let finished = expectation(description: "Stock controller " + phase)
        let result = OSAllocatedUnfairLock<Result<Data, any Error>?>(initialState: nil)
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            result.withLock { value in
                if let error { value = .failure(error) }
                else if (response as? HTTPURLResponse)?.statusCode == 200, let data { value = .success(data) }
                else { value = .failure(URLError(.badServerResponse)) }
            }
            finished.fulfill()
        }
        task.resume()
        defer { task.cancel() }
        XCTAssertEqual(XCTWaiter.wait(for: [finished], timeout: 14), .completed)
        return try XCTUnwrap(result.withLock { $0 }).get()
    }

    @MainActor private func open(_ phase: String, app: XCUIApplication, run: String, control: UInt16) throws {
        let port = try JSONDecoder().decode(Port.self, from: advance(phase, control: control)).port
        app.launchArguments = [run, phase, "--origin=\(port)"]
        app.launch()
        waitForLabel("Healthy " + phase, on: app.staticTexts["f11.status"])
    }

    @MainActor private func closeReadOnly(_ app: XCUIApplication, phase: String) {
        let staticFrame = app.staticTexts["Read-only Note release"]
        XCTAssertTrue(staticFrame.waitForExistence(timeout: 5))
        XCTAssertFalse(app.textViews["f11.note"].exists)
        XCTAssertFalse(app.buttons["f11.save"].isEnabled)
        XCTAssertFalse(app.buttons["f11.commit"].isEnabled)
        app.buttons["f11.close"].tap()
        waitForLabel("Closed " + phase, on: app.staticTexts["f11.status"])
        app.terminate()
    }
