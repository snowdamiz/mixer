import Foundation

final class Response: @unchecked Sendable {
    var data: Data?
    var status: Int?
    var error: Error?
}
let args = CommandLine.arguments
let records = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: args[1]))) as! [[String: Any]]
let cap = ProcessInfo.processInfo.environment["MIXER_HOST_PROBE_CAPABILITY"]!
let endpoint = URL(string: args[2])!
var timings: [[String: Any]] = []
for (i, record) in records.enumerated() {
    let start = ProcessInfo.processInfo.systemUptime
    let body = try JSONSerialization.data(withJSONObject: ["settingsDiagnostic": record], options: [.sortedKeys, .withoutEscapingSlashes])
    let serialized = ProcessInfo.processInfo.systemUptime
    precondition(body.count <= 8192)
    var request = URLRequest(url: endpoint, timeoutInterval: 2)
    request.httpMethod = "POST"; request.httpBody = body
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.setValue(cap, forHTTPHeaderField: "X-Mixer-Capability")
    let result = Response(); let done = DispatchSemaphore(value: 0)
    let task = URLSession.shared.dataTask(with: request) { data, response, error in
        result.data = data; result.status = (response as? HTTPURLResponse)?.statusCode
        result.error = error; done.signal()
    }
    task.resume()
    guard done.wait(timeout: .now() + 2) == .success else { task.cancel(); fatalError("host request timeout") }
    let finish = ProcessInfo.processInfo.systemUptime
    guard result.error == nil, result.status == 200, let data = result.data, data.count <= 8192,
          (try JSONSerialization.jsonObject(with: data)) is [String: Any] else { fatalError("host request rejected at \(i): \(result.status ?? 0)") }
    timings.append(["ordinal": i, "serializationSeconds": serialized-start, "requestSeconds": finish-serialized, "bodyBytes": body.count])
}
let output = try JSONSerialization.data(withJSONObject: timings, options: [.sortedKeys])
FileHandle.standardOutput.write(output)
