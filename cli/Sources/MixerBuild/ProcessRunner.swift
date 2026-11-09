import Foundation

public struct CommandResult: Codable, Sendable {
    public var command: [String]
    public var exitCode: Int32
    public var output: String
    public var outputTruncated = false
    public var succeeded: Bool { exitCode == 0 }
}

public enum ProcessRunner {
    /// Runs a literal argv through /usr/bin/env, with explicit local-development limits and durable custody receipts.
    public static func run(_ command: [String], at directory: URL? = nil, environment: [String: String]? = nil,
                           policy: ProcessPolicy = .developmentBuild,
                           context: ProcessExecutionContext = .localDevelopment, retaining inputs: [URL] = []) throws -> CommandResult {
        guard !command.isEmpty else { throw MixerFailure("command.empty", "Empty command") }
        let selectedEnvironment = environment ?? ProcessInfo.processInfo.environment
        guard command.allSatisfy({ !$0.utf8.contains(0) }), directory?.path.utf8.contains(0) != true,
              selectedEnvironment.allSatisfy({ !$0.key.isEmpty && !$0.key.contains("=") && !$0.key.utf8.contains(0) && !$0.value.utf8.contains(0) }),
              policy.runtimeSeconds > 0, policy.cleanupSeconds > 0, policy.generatedOutputBytes > 0 else {
            throw MixerFailure("command.invalid", "Invalid argv, cwd, environment or command limits")
        }
        return try context.run(command: command, directory: directory, environment: selectedEnvironment, policy: policy, retainedInputs: inputs + (directory.map { [$0] } ?? []))
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
            let result = try? ProcessRunner.run(command, policy: .toolInspection)
            var ready = result?.succeeded == true
            if name == "Android devices" { ready = ready && result?.output.range(of: "(?m)^\\S+\\s+device\\s", options: .regularExpression) != nil }
            if name == "iOS devices" { ready = ready && result?.output.contains("physical") == true }
            return DoctorCheck(name: name, ready: ready, detail: result?.output.trimmingCharacters(in: .whitespacesAndNewlines) ?? "Command could not start", remediation: remediation)
        }
        let sdk = try? ProcessRunner.run(["swift", "sdk", "list"], policy: .toolInspection)
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
