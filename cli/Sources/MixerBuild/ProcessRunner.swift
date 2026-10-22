import Foundation

public struct CommandResult: Codable, Sendable {
    public var command: [String]
    public var exitCode: Int32
    public var output: String
    public var outputTruncated = false
    public var succeeded: Bool { exitCode == 0 }
}

public enum ProcessRunner {
    // Output is spooled to a private temporary file so compiler diagnostics cannot
    // deadlock a full pipe while the parent waits for termination.
    public static func run(_ command: [String], at directory: URL? = nil, environment: [String: String]? = nil) throws -> CommandResult {
        guard !command.isEmpty else { throw MixerFailure("command.empty", "Empty command") }
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-process-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        defer { try? FileManager.default.removeItem(at: folder) }
        let log = folder.appendingPathComponent("output")
        FileManager.default.createFile(atPath: log.path, contents: nil, attributes: [.posixPermissions: 0o600])
        let handle = try FileHandle(forWritingTo: log)
        defer { try? handle.close() }
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = command; process.currentDirectoryURL = directory
        process.environment = environment ?? ProcessInfo.processInfo.environment
        process.standardOutput = handle; process.standardError = handle
        try process.run(); process.waitUntilExit()
        try handle.synchronize()
        let reader = try FileHandle(forReadingFrom: log)
        defer { try? reader.close() }
        let length = try reader.seekToEnd(), maximum: UInt64 = 8 * 1_048_576
        try reader.seek(toOffset: length > maximum ? length - maximum : 0)
        let bytes = try reader.read(upToCount: Int(maximum)) ?? Data()
        return CommandResult(command: command, exitCode: process.terminationStatus, output: String(decoding: bytes, as: UTF8.self), outputTruncated: length > maximum)
    }
}

public struct DoctorCheck: Codable, Sendable {
    public var name: String
    public var ready: Bool
    public var detail: String
    public var remediation: String
}

public enum Doctor {
    public static func inspect() -> [DoctorCheck] {
        let env = ProcessInfo.processInfo.environment
        let androidRoot = env["ANDROID_HOME"] ?? env["ANDROID_SDK_ROOT"] ?? "/opt/homebrew/share/android-commandlinetools"
        let probes: [(String, [String], String)] = [
            ("Swift host", ["swift", "--version"], "Install a supported Swift toolchain and pin its exact version."),
            ("Xcode", ["xcodebuild", "-version"], "Install Xcode and select it with xcode-select."),
            ("Java", ["java", "-version"], "Set JAVA_HOME to a supported JDK for the Android Gradle plugin."),
            ("Gradle", ["gradle", "--version"], "Install the pinned Gradle distribution and JDK."),
            ("Android devices", [androidRoot + "/platform-tools/adb", "devices", "-l"], "Set ANDROID_HOME and connect an authorized Android device."),
            ("iOS devices", ["xcrun", "devicectl", "list", "devices"], "Pair a physical iPhone and enable Developer Mode.")
        ]
        var checks = probes.map { name, command, remediation in
            let result = try? ProcessRunner.run(command)
            var ready = result?.succeeded == true
            if name == "Android devices" { ready = ready && result?.output.range(of: "(?m)^\\S+\\s+device\\s", options: .regularExpression) != nil }
            if name == "iOS devices" { ready = ready && result?.output.contains("physical") == true }
            return DoctorCheck(name: name, ready: ready, detail: result?.output.trimmingCharacters(in: .whitespacesAndNewlines) ?? "Command could not start", remediation: remediation)
        }
        let sdk = try? ProcessRunner.run(["swift", "sdk", "list"])
        for (name, marker) in [("Android Swift SDK", "_android"), ("Wasm Swift SDK", "_wasm")] {
            checks.append(DoctorCheck(name: name, ready: sdk?.succeeded == true && sdk?.output.contains(marker) == true, detail: sdk?.output ?? "SDK inventory unavailable", remediation: "Install the official SDK matching the open-source host Swift compiler exactly. Xcode Swift is not interchangeable."))
        }
        let hostVersion = checks.first?.detail ?? ""
        let matching = (sdk?.output.components(separatedBy: .newlines) ?? []).filter { $0.contains("_android") || $0.contains("_wasm") }.allSatisfy { line in
            guard let range = line.range(of: "[0-9]+\\.[0-9]+\\.[0-9]+", options: .regularExpression) else { return false }
            return hostVersion.contains("Swift version \(line[range]) (") && hostVersion.contains("RELEASE")
        }
        checks.append(DoctorCheck(name: "Cross-compiler version match", ready: matching && !(sdk?.output.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ?? true), detail: matching ? "SDK version IDs match the active open-source compiler." : "Active Swift does not exactly match all installed cross SDKs.", remediation: "Select the official open-source Swift release matching the intended Android/Wasm SDK. Use target-specific SDK selection to avoid ambiguous architecture matches."))
        return checks
    }
}
