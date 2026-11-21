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
            if value == "--help" { positional.append("help") }
            else if value == "--json" { json = true }
            else if value.hasPrefix("--") {
                guard ["--directory", "--application", "--sdk-path", "--android-adapter-path", "--android-host", "--platform", "--output", "--swiftpm-description", "--device", "--provider", "--build-id", "--app-id", "--version-code", "--track", "--request", "--artifact", "--qualification", "--producer-trust"].contains(value), index + 1 < values.count, !values[index + 1].hasPrefix("--"), options[value] == nil else { throw MixerFailure("arguments.option", "Unknown, missing, or duplicate option: \(value)") }
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

#if MIXER_LOCAL_STORE_FIXTURE
let fixtureHelp = """

  mixer submit request|reconcile --provider app-store-connect --build-id BUILD_ID --app-id APP_ID
    --artifact FILE [--directory PROJECT]
  mixer submit request|reconcile --provider play --version-code CODE --track TRACK
    --artifact FILE [--directory PROJECT]
    Synthetic loopback only. Sends the development artifact's SHA-256, with no upload.
"""
#else
let fixtureHelp = ""
#endif

let help = """
mixer 0.1.0-dev — owned Swift mobile platform (development preview)

  mixer create NAME [--directory PATH] [--application ID] [--sdk-path PATH]
    [--platform ios|android] [--android-adapter-path PATH] [--android-host legacy-v1|public-v3|public-v4]
  mixer doctor [--json]
  mixer config validate [--directory PATH]
  mixer build [--platform host|ios|android] [--directory PATH] [--output NEW_PRIVATE_STORE (ios or android)]
  mixer report --request REQUEST.json --output NEW_PRIVATE_STORE
  mixer test [--platform host] [--directory PATH]
  mixer run ios --device SIMULATOR_UUID [--directory PATH]
  mixer import PATH [--swiftpm-description DESCRIPTION.json] [--output REPORT.json]
    Use JSON from swift package describe --type json for advisory local target causes.
  mixer release inspect [--directory PATH] [--qualification DIR --producer-trust LOCAL_TRUST.json]
  mixer export PATH [--directory SOURCE]
  mixer upgrade PATH --sdk-path PATH [--android-adapter-path PATH] [--directory SOURCE]
  mixer vm validate|inventory|invoke FILE [EXPORT [i32:N|i64:N ...]]
  mixer update verify --manifest FILE --payload FILE --host FILE --roots FILE
    --assignment FILE --channel NAME --installation ID --last-sequence N --now UNIX
  mixer update publish CANDIDATE --channel NAME --rollout PERCENT
    --organization ORG --project PROJECT --assignment FILE
  mixer update promote ARTIFACT_SHA256 --rollout PERCENT [--channel NAME]
    --organization ORG --project PROJECT --assignment FILE
  mixer update promote-environment DIRECTION --organization ORG --project PROJECT --application APP
    --source-ios-sequence N --source-android-sequence N --ios-assignment FILE --android-assignment FILE
    --reason REASON
  mixer update rollback ARTIFACT_SHA256 --reason REASON [--channel NAME]
    --organization ORG --project PROJECT --assignment FILE
  mixer update halt ARTIFACT_SHA256 --channel NAME --health SAMPLE
    --organization ORG --project PROJECT --assignment FILE
    CANDIDATE contains signed-manifest.json and payload.wasm. FILE is a signed v3 assignment.
    Use MIXER_RELEASE_ORIGIN=http://127.0.0.1:PORT and MIXER_RELEASE_TOKEN.
  mixer submit status --provider app-store-connect --build-id BUILD_ID --app-id ASC_APP_ID
    [--directory PROJECT]
  mixer submit testing-status --provider app-store-connect --build-id BUILD_ID --app-id ASC_APP_ID
    [--directory PROJECT]
  mixer submit testing-status --provider play --version-code CODE --track TRACK
    [--directory PROJECT]
    Read-only; uses mixer.yml application and MIXER_PLAY_BEARER_TOKEN.
    Published-on-track does not establish tester access or testing readiness.
  mixer gates\(fixtureHelp)

All commands emit structured JSON. Build/test errors preserve compiler diagnostics.
Creation bundles a hashed SDK source snapshot for local development. Mobile host,
guest, hosted distribution and GA qualification remain explicit open gates.
"""

func withRetainedBuildClosure<T>(_ build: () throws -> T) throws -> T {
    let result: T
    do {
        result = try build()
    } catch {
        try ProcessExecutionContext.localDevelopment.acknowledgeWorkerClosure()
        throw error
    }
    try ProcessExecutionContext.localDevelopment.acknowledgeWorkerClosure()
    return result
}

do {
    let raw = Array(CommandLine.arguments.dropFirst())
    if raw.starts(with: ["update", "verify"]) {
        let verifier = ProcessInfo.processInfo.environment["MIXER_UPDATE_TOOL"] ?? repository.appendingPathComponent("updates/.build/debug/mixer-update").path
        let vm = ProcessInfo.processInfo.environment["MIXER_VM"] ?? repository.appendingPathComponent("vm/target/release/mixer-vm").path
        guard FileManager.default.isExecutableFile(atPath: verifier), FileManager.default.isExecutableFile(atPath: vm) else { throw MixerFailure("update.tools", "Build updates/ (Swift) and vm/ (cargo build --release), or set MIXER_UPDATE_TOOL and MIXER_VM.") }
        let report = try LocalUpdateValidation.verify(arguments: Array(raw.dropFirst(2)), verifier: verifier, vm: vm)
        try output(report)
        exit(report.status == "local-candidate-verified" ? 0 : report.status == "executable-rejected" ? 2 : 1)
    }
    if raw.starts(with: ["update", "promote-environment"]) {
        try await output(LocalUpdateRelease.promoteEnvironment(arguments: Array(raw.dropFirst(2))))
        exit(0)
    }
    if raw.count >= 2, raw[0] == "update", let action = LocalUpdateRelease.Action(rawValue: raw[1]) {
        try await output(LocalUpdateRelease.run(action, arguments: Array(raw.dropFirst(2))))
        exit(0)
    }
    let arguments = try Arguments(Array(CommandLine.arguments.dropFirst()))
    let words = arguments.positional
    let allowedOptions: [String: Set<String>] = [
        "create": ["--directory", "--application", "--sdk-path", "--platform", "--android-adapter-path", "--android-host"], "config": ["--directory"],
        "build": ["--directory", "--platform", "--output"], "test": ["--directory", "--platform"],
        "run": ["--directory", "--device"], "import": ["--output", "--swiftpm-description"],
        "release": ["--directory", "--qualification", "--producer-trust"], "export": ["--directory"],
        "upgrade": ["--directory", "--sdk-path", "--android-adapter-path"],
        "report": ["--request", "--output"],
        "submit": ["--provider", "--build-id", "--app-id", "--version-code", "--track", "--directory", "--artifact"]
    ]
    guard Set(arguments.options.keys).isSubset(of: allowedOptions[words.first ?? "help"] ?? []) else { throw MixerFailure("arguments.unused-option", "An option does not apply to this command.") }
    let root = path(arguments.options["--directory"] ?? ".")
    switch words.first ?? "help" {
    case "help", "-h", "--help": print(help)
    case "version": try output(SuccessOutput(detail: "0.1.0-dev"))
    case "create":
        guard words.count == 2 else { throw MixerFailure("arguments.create", "Usage: mixer create NAME [--directory PATH] [--application ID] [--sdk-path PATH]") }
        let name = words[1]
        let target = path(arguments.options["--directory"] ?? name)
        let sdk = path(arguments.options["--sdk-path"] ?? ProcessInfo.processInfo.environment["MIXER_SDK_PATH"] ?? repository.appendingPathComponent("sdk").path)
        let platform = arguments.options["--platform"] ?? "ios"
        guard platform == "android" || arguments.options["--android-adapter-path"] == nil else { throw MixerFailure("arguments.unused-option", "--android-adapter-path requires --platform android.") }
        let androidHost: AndroidApplicationHost?
        if let value = arguments.options["--android-host"] {
            guard platform == "android", let selected = AndroidApplicationHost(rawValue: value) else { throw MixerFailure("arguments.android-host", "--android-host requires --platform android and legacy-v1, public-v3 or public-v4.") }
            androidHost = selected
        } else { androidHost = nil }
        let adapter = path(arguments.options["--android-adapter-path"] ?? ProcessInfo.processInfo.environment["MIXER_ANDROID_ADAPTER_PATH"] ?? repository.appendingPathComponent("native/android").path)
        try output(ProjectGenerator.create(name: name, application: arguments.options["--application"] ?? "com.example.\(name.lowercased())", destination: target, sdk: sdk, platform: platform, androidAdapter: platform == "android" ? adapter : nil, androidHost: androidHost))
    case "doctor":
        let checks = Doctor.inspect()
        let ready = checks.allSatisfy(\.ready)
        try output(DoctorOutput(status: ready ? "ready-for-qualification" : "incomplete", checks: checks))
        if !ready { exit(2) }
    case "config":
        guard words == ["config", "validate"] else { throw MixerFailure("arguments.config", "Usage: mixer config validate") }
        try output(ApplicationConfiguration.load(root))
    case "report":
        guard words == ["report"], !arguments.json,
              Set(arguments.options.keys) == Set(["--request", "--output"]),
              let request = arguments.options["--request"], let destination = arguments.options["--output"] else {
            throw MixerFailure("arguments.report", "Usage: mixer report --request REQUEST.json --output NEW_PRIVATE_STORE")
        }
        try output(SameBuildPublicReport.observe(request: SameBuildPublicReport.readRequest(path(request)),
                                                output: path(destination)))
    case "build", "test":
        guard words.count == 1 else { throw MixerFailure("arguments.build", "Unexpected positional argument") }
        if let destination = arguments.options["--output"] {
            if words[0] == "build", arguments.options["--platform"] == "android" {
                try withRetainedBuildClosure {
                    try output(AndroidBuildOutput.build(root: root, output: path(destination)))
                }
                exit(0)
            }
            guard words[0] == "build", arguments.options["--platform"] == "ios" else {
                throw MixerFailure("arguments.output-platform", "--output requires an explicit --platform ios or android build.")
            }
            let code = try withRetainedBuildClosure {
                let report = try ProjectBuild.runRetainingNative(root: root, test: false, platform: "ios", output: path(destination))
                try output(report)
                return report.succeeded ? 0 : (report.commandResult.exitCode == 0 ? 1 : report.commandResult.exitCode)
            }
            exit(code)
        }
        let result = try ProjectBuild.run(root: root, test: words[0] == "test", platform: arguments.options["--platform"] ?? "host")
        try output(result)
        if !result.succeeded { exit(result.exitCode == 0 ? 1 : result.exitCode) }
    case "import":
        guard words.count == 2 else { throw MixerFailure("arguments.import", "Usage: mixer import PATH [--swiftpm-description DESCRIPTION.json] [--output REPORT.json]") }
        let report = try MigrationInspector.inspect(
            path(words[1]), swiftPMDescription: arguments.options["--swiftpm-description"].map(path)
        )
        if let file = arguments.options["--output"] {
            guard !FileManager.default.fileExists(atPath: path(file).path) else { throw MixerFailure("import.report-exists", "Refusing to overwrite report.") }
            try JSONFile.write(report, to: path(file))
        }
        try output(report)
    case "release":
        guard words == ["release", "inspect"] else { throw MixerFailure("arguments.release", "Use mixer release inspect.") }
        let evidence = arguments.options["--qualification"].map(path)
        let trust = arguments.options["--producer-trust"].map(path)
        guard (evidence == nil) == (trust == nil) else {
            throw MixerFailure("arguments.release-qualification", "Supply both the qualification directory and the operator's local producer trust configuration.")
        }
        let report = try ReleaseAssessment.inspect(root, qualification: evidence, producerTrust: trust)
        try output(report)
        exit(report.technicalEligibility == "ota-compatible" ? 0 : 2)
    case "upgrade":
        guard words.count == 2, let sdk = arguments.options["--sdk-path"] else {
            throw MixerFailure("arguments.upgrade", "Usage: mixer upgrade DESTINATION --sdk-path PATH [--android-adapter-path PATH] [--directory SOURCE]")
        }
        let digest = try ProjectBuild.upgrade(root: root, destination: path(words[1]), sdk: path(sdk),
                                             androidAdapter: arguments.options["--android-adapter-path"].map(path))
        try output(SuccessOutput(detail: "Upgraded project copy; digest \(digest)"))
    case "export":
        guard words.count == 2 else { throw MixerFailure("arguments.export", "Usage: mixer export DESTINATION [--directory SOURCE]") }
        try output(SuccessOutput(detail: "Exported source and pinned SDK; digest \(try ProjectBuild.export(root: root, destination: path(words[1])))"))
    case "vm":
        guard words.count >= 3, ["validate", "inventory", "invoke"].contains(words[1]) else { throw MixerFailure("arguments.vm", "Usage: mixer vm validate|inventory|invoke FILE [EXPORT [ARGS...]]") }
        let vm = ProcessInfo.processInfo.environment["MIXER_VM"] ?? repository.appendingPathComponent("vm/target/debug/mixer-vm").path
        guard FileManager.default.isExecutableFile(atPath: vm) else { throw MixerFailure("vm.unavailable", "Build vm/ with cargo build or set MIXER_VM to the owned interpreter executable.") }
        let result = try ProcessRunner.run([vm] + words.dropFirst(), policy: .localValidation)
        FileHandle.standardOutput.write(Data(result.output.utf8))
        if !result.succeeded { exit(result.exitCode) }
    case "gates":
        FileHandle.standardOutput.write(try Data(contentsOf: repository.appendingPathComponent("gates/ga.json")))
    case "run":
        guard words == ["run", "ios"], let device = arguments.options["--device"] else { throw MixerFailure("arguments.run", "Usage: mixer run ios --device SIMULATOR_UUID. Android/physical installation is still being integrated.") }
        let result = try AppleProject.run(root: root, simulator: device)
        try output(result)
        if !result.succeeded { exit(1) }
    case "submit":
        #if MIXER_LOCAL_STORE_FIXTURE
        try LocalStoreFixture.validate()
        if words == ["submit", "request"] || words == ["submit", "reconcile"] {
            guard let artifact = arguments.options["--artifact"] else {
                throw MixerFailure("store.fixture-artifact", "Specify the development artifact with --artifact FILE.")
            }
            let report = try await LocalStoreSubmission.run(
                create: words.last == "request", options: arguments.options, directory: root, artifact: path(artifact)
            )
            try output(report)
            exit(report.exitCode)
        }
        #endif
        if arguments.options["--provider"] == "play" {
            let applicationID: String
            do { applicationID = try ApplicationConfiguration.load(root).applicationIdentifier(for: "android") }
            catch { throw MixerFailure("play.configuration-invalid", "Play status requires a valid application configuration.") }
            let request = try PlayTestingRequest.parse(words: words, options: arguments.options, applicationID: applicationID)
            let report = try await PlayReleaseStatus().status(
                request: request,
                token: ProcessInfo.processInfo.environment["MIXER_PLAY_BEARER_TOKEN"] ?? ""
            )
            try output(report); exit(report.exitCode)
        }
        let request = try StoreStatusRequest.parse(words: words, options: arguments.options)
        if words == ["submit", "testing-status"] {
            let report = try StoreReconciliation.testingStatus(request: request, directory: root)
            try output(report); exit(report.exitCode)
        }
        let report = try StoreReconciliation.status(request: request, directory: root)
        try output(report); exit(report.exitCode)
    case "update":
        throw MixerFailure("workflow.not-qualified", "\(words[0]) requires native/guest/store integration that is still in progress. No build, release or submission has been performed. See mixer gates.")
    default: throw MixerFailure("arguments.command", "Unknown command: \(words[0]). Run mixer help.")
    }
} catch let failure as PlayStatusFailure {
    let code: String
    let message: String
    switch failure {
    case .invalidRequest:
        code = "play.invalid-request"
        message = "Usage: mixer submit testing-status --provider play --version-code CODE --track TRACK [--directory PROJECT]."
    case .redactedResponse:
        code = "play.redacted-response"
        message = "Play status cannot safely report this request."
    default:
        code = "play.status-failed"
        message = "Play status could not be resolved."
    }
    try? output(FailureOutput(code: code, message: message)); exit(1)
} catch let failure as MixerFailure {
    try? output(FailureOutput(code: failure.code, message: failure.description)); exit(1)
} catch {
    try? output(FailureOutput(code: "operation.failed", message: String(describing: error))); exit(1)
}
