import Foundation
import MixerBuild

struct Arguments {
    var positional: [String] = []
    var options: [String: String] = [:]
    var json = false
    init(_ values: [String]) throws {
        var index = 0
        while index < values.count {
            let value = values[index]
            if value == "--json" { json = true }
            else if value.hasPrefix("--") {
                guard ["--directory", "--application", "--sdk-path", "--platform", "--output", "--device"].contains(value), index + 1 < values.count, !values[index + 1].hasPrefix("--"), options[value] == nil else { throw MixerFailure("arguments.option", "Unknown, missing, or duplicate option: \(value)") }
                index += 1; options[value] = values[index]
            } else { positional.append(value) }
            index += 1
        }
    }
}

struct FailureOutput: Encodable { let status = "error"; let code: String; let message: String }
struct DoctorOutput: Encodable { let status: String; let qualification = "inventory-only"; let checks: [DoctorCheck] }
struct SuccessOutput: Encodable { let status = "ok"; let detail: String }

func output<T: Encodable>(_ value: T) throws { FileHandle.standardOutput.write(try JSONFile.data(value)) }
func path(_ value: String) -> URL { URL(fileURLWithPath: value, relativeTo: URL(fileURLWithPath: FileManager.default.currentDirectoryPath, isDirectory: true)).standardizedFileURL }
let repository = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()

let help = """
mixer 0.1.0-dev — owned Swift mobile platform (development preview)

  mixer create NAME [--directory PATH] [--application ID] [--sdk-path PATH]
  mixer doctor [--json]
  mixer config validate [--directory PATH]
  mixer build [--platform host|ios] [--directory PATH]
  mixer test [--platform host] [--directory PATH]
  mixer run ios --device SIMULATOR_UUID [--directory PATH]
  mixer import PATH [--output REPORT.json]
  mixer release inspect [--directory PATH]
  mixer export PATH [--directory SOURCE]
  mixer vm validate|inventory|invoke FILE [EXPORT [i32:N|i64:N ...]]
  mixer gates

All commands emit structured JSON. Build/test errors preserve compiler diagnostics.
Creation bundles a hashed SDK source snapshot for local development. Mobile host,
guest, hosted distribution and GA qualification remain explicit open gates.
"""

do {
    let arguments = try Arguments(Array(CommandLine.arguments.dropFirst()))
    let words = arguments.positional
    let root = path(arguments.options["--directory"] ?? ".")
    switch words.first ?? "help" {
    case "help", "-h", "--help": print(help)
    case "version": try output(SuccessOutput(detail: "0.1.0-dev"))
    case "create":
        guard words.count == 2 else { throw MixerFailure("arguments.create", "Usage: mixer create NAME [--directory PATH] [--application ID] [--sdk-path PATH]") }
        let name = words[1]
        let target = path(arguments.options["--directory"] ?? name)
        let sdk = path(arguments.options["--sdk-path"] ?? ProcessInfo.processInfo.environment["MIXER_SDK_PATH"] ?? repository.appendingPathComponent("sdk").path)
        try output(ProjectGenerator.create(name: name, application: arguments.options["--application"] ?? "com.example.\(name.lowercased())", destination: target, sdk: sdk))
    case "doctor":
        let checks = Doctor.inspect()
        let ready = checks.allSatisfy(\.ready)
        try output(DoctorOutput(status: ready ? "ready-for-qualification" : "incomplete", checks: checks))
        if !ready { exit(2) }
    case "config":
        guard words == ["config", "validate"] else { throw MixerFailure("arguments.config", "Usage: mixer config validate") }
        try output(ApplicationConfiguration.load(root))
    case "build", "test":
        guard words.count == 1 else { throw MixerFailure("arguments.build", "Unexpected positional argument") }
        let result = try ProjectBuild.run(root: root, test: words[0] == "test", platform: arguments.options["--platform"] ?? "host")
        try output(result)
        if !result.succeeded { exit(result.exitCode == 0 ? 1 : result.exitCode) }
    case "import":
        guard words.count == 2 else { throw MixerFailure("arguments.import", "Usage: mixer import PATH [--output REPORT.json]") }
        let report = try MigrationInspector.inspect(path(words[1]))
        if let file = arguments.options["--output"] {
            guard !FileManager.default.fileExists(atPath: path(file).path) else { throw MixerFailure("import.report-exists", "Refusing to overwrite report.") }
            try JSONFile.write(report, to: path(file))
        }
        try output(report)
    case "release":
        guard words == ["release", "inspect"] else { throw MixerFailure("arguments.release", "Only release inspect is available until signed dual-target qualification is integrated.") }
        try output(ReleaseAssessment.inspect(root)); exit(2)
    case "export":
        guard words.count == 2 else { throw MixerFailure("arguments.export", "Usage: mixer export DESTINATION [--directory SOURCE]") }
        try output(SuccessOutput(detail: "Exported source and pinned SDK; digest \(try ProjectBuild.export(root: root, destination: path(words[1])))"))
    case "vm":
        guard words.count >= 3, ["validate", "inventory", "invoke"].contains(words[1]) else { throw MixerFailure("arguments.vm", "Usage: mixer vm validate|inventory|invoke FILE [EXPORT [ARGS...]]") }
        let vm = ProcessInfo.processInfo.environment["MIXER_VM"] ?? repository.appendingPathComponent("vm/target/debug/mixer-vm").path
        guard FileManager.default.isExecutableFile(atPath: vm) else { throw MixerFailure("vm.unavailable", "Build vm/ with cargo build or set MIXER_VM to the owned interpreter executable.") }
        let result = try ProcessRunner.run([vm] + words.dropFirst())
        FileHandle.standardOutput.write(Data(result.output.utf8))
        if !result.succeeded { exit(result.exitCode) }
    case "gates":
        FileHandle.standardOutput.write(try Data(contentsOf: repository.appendingPathComponent("gates/ga.json")))
    case "run":
        guard words == ["run", "ios"], let device = arguments.options["--device"] else { throw MixerFailure("arguments.run", "Usage: mixer run ios --device SIMULATOR_UUID. Android/physical installation is still being integrated.") }
        let result = try AppleProject.run(root: root, simulator: device)
        try output(result)
        if !result.succeeded { exit(1) }
    case "update", "submit":
        throw MixerFailure("workflow.not-qualified", "\(words[0]) requires native/guest/store integration that is still in progress. No build, release or submission has been performed. See mixer gates.")
    default: throw MixerFailure("arguments.command", "Unknown command: \(words[0]). Run mixer help.")
    }
} catch let failure as MixerFailure {
    try? output(FailureOutput(code: failure.code, message: failure.description)); exit(1)
} catch {
    try? output(FailureOutput(code: "operation.failed", message: String(describing: error))); exit(1)
}
