import Foundation
import Testing
@testable import MixerBuild

private struct Pair7SnapshotFailure: Error { let message: String }
private func pair7Require(_ condition: Bool, _ message: String) throws {
    if !condition { throw Pair7SnapshotFailure(message: message) }
}
private struct Pair7JavaMember: Decodable {
    let canonical_path: String
    let generated_path: String
    let bytes: Int
    let sha256: String
}
private struct Pair7JavaClosure: Decodable {
    let profile_id: String
    let product_java_members: Int
    let product_java_bytes: Int
    let members: [Pair7JavaMember]
}
private func pair7Identity(_ file: URL) throws -> [String: Any] {
    let flags = try file.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey])
    try pair7Require(flags.isRegularFile == true && flags.isSymbolicLink != true,
                     "Expected an ordinary file: \(file.path)")
    let data = try Data(contentsOf: file)
    return ["bytes": data.count, "sha256": SourceDigest.sha256(data)]
}
private func pair7Write(_ object: [String: Any], to file: URL) throws {
    var data = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys, .prettyPrinted])
    data.append(10)
    try data.write(to: file, options: .withoutOverwriting)
}

// Proposal-only test. The workflow copies this exact reviewed file into the CLI
// test target in its isolated checkout. No canonical test is changed.
@Test func pair7RetainedActualAndroidSnapshotForJavaCI() throws {
    let env = ProcessInfo.processInfo.environment
    let fm = FileManager.default
    let repository = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent().deletingLastPathComponent()
        .deletingLastPathComponent().deletingLastPathComponent()
    let root = repository.standardizedFileURL
    try pair7Require(root.path == env["GITHUB_WORKSPACE"], "Exact CI workspace required")
    try pair7Require(env["GITHUB_REPOSITORY"] == "snowdamiz/mixer", "Exact repository required")
    try pair7Require(env["GITHUB_JOB"] == "snapshot", "Exact snapshot job required")
    try pair7Require(["push", "pull_request"].contains(env["GITHUB_EVENT_NAME"] ?? ""),
                     "Ordinary push or pull request required")
    try pair7Require(env["GITHUB_RUN_ATTEMPT"] == "1", "No retry allowance")
    let run = env["GITHUB_RUN_ID"] ?? ""
    try pair7Require(!run.isEmpty && run.allSatisfy(\.isNumber), "Run id required")
    let head = env["GITHUB_SHA"] ?? ""
    try pair7Require(head.utf8.count == 40 && head.utf8.allSatisfy {
        (48...57).contains($0) || (97...102).contains($0)
    }, "Immutable checkout head required")
    guard let tempPath = env["RUNNER_TEMP"], let outputPath = env["MIXER_PAIR7_SNAPSHOT_OUT"] else {
        throw Pair7SnapshotFailure(message: "Explicit fresh CI output required")
    }
    let temp = URL(fileURLWithPath: tempPath, isDirectory: true).standardizedFileURL
    try pair7Require(temp.path == temp.resolvingSymlinksInPath().path, "Ordinary runner temp required")
    let output = temp.appendingPathComponent("pair7-java-snapshot-\(run)-1", isDirectory: true)
    try pair7Require(output.path == outputPath && !fm.fileExists(atPath: output.path),
                     "Output must be the fresh selected CI-owned directory")
    let packet = root.appendingPathComponent("verification/pair7-java-compile-ci-proposal/v3")
    let closureFile = packet.appendingPathComponent("exact-java-closure.json")
    let closureData = try Data(contentsOf: closureFile)
    let closure = try JSONDecoder().decode(Pair7JavaClosure.self, from: closureData)
    try pair7Require(closure.profile_id == "mixer.android-source-pair.7" &&
                     AndroidSDKCompatibility.profile.id == closure.profile_id &&
                     closure.product_java_members == 18 && closure.product_java_bytes == 393165 &&
                     closure.members.count == 18, "Exact reviewed pair7 Java closure required")
    let paths = closure.members.map(\.generated_path)
    try pair7Require(Set(paths).count == 18, "Duplicate generated source path")
    var before: [[String: Any]] = []
    for member in closure.members {
        try pair7Require(member.canonical_path.hasPrefix("native/android/app/src/dev/mixer/android/") &&
                         member.generated_path == "Generated/MixerAndroid/" + String(member.canonical_path.dropFirst("native/android/".count)) &&
                         !member.canonical_path.contains(".."), "Exact source mapping required")
        let file = root.appendingPathComponent(member.canonical_path)
        let info = try pair7Identity(file)
        try pair7Require(info["bytes"] as? Int == member.bytes && info["sha256"] as? String == member.sha256,
                         "Canonical Java source drift: \(member.canonical_path)")
        before.append(["path": member.canonical_path, "bytes": member.bytes, "sha256": member.sha256])
    }
    try fm.createDirectory(at: output, withIntermediateDirectories: false)
    try pair7Write(["status": "started", "source_head": head,
                    "source_manifest_sha256": SourceDigest.sha256(closureData),
                    "native_runtime_started": false], to: output.appendingPathComponent("started.json"))
    let generated = output.appendingPathComponent("consumer/Generated/MixerAndroid", isDirectory: true)
    // This is the actual product generation API. It does not inspect tools,
    // launch a compiler, build Swift/JNI/APK or call ProjectGenerator.create.
    let digest = try AndroidProject.snapshot(adapter: root.appendingPathComponent("native/android"),
                                            destination: generated)
    try pair7Require(try SourceDigest.tree(generated) == digest, "Actual snapshot digest drift")
    let javaRoot = generated.appendingPathComponent("app/src", isDirectory: true)
    let emitted = try SourceDigest.files(in: javaRoot)
    let actualPaths = emitted.map { "Generated/MixerAndroid/" + String($0.path.dropFirst(generated.path.count + 1)) }
    try pair7Require(Set(actualPaths) == Set(paths), "Actual generated Java membership differs")
    var generatedRows: [[String: Any]] = []
    for member in closure.members {
        let file = output.appendingPathComponent("consumer/" + member.generated_path)
        let info = try pair7Identity(file)
        try pair7Require(info["bytes"] as? Int == member.bytes && info["sha256"] as? String == member.sha256,
                         "Actual generated Java differs: \(member.generated_path)")
        try pair7Require(try Data(contentsOf: file) == Data(contentsOf: root.appendingPathComponent(member.canonical_path)),
                         "Actual and canonical Java differ")
        generatedRows.append(["path": member.generated_path, "bytes": member.bytes, "sha256": member.sha256])
    }
    var treeRows: [[String: Any]] = []
    for file in try SourceDigest.files(in: generated) {
        var row = try pair7Identity(file)
        row["path"] = String(file.path.dropFirst(generated.path.count + 1))
        treeRows.append(row)
    }
    for member in closure.members {
        let info = try pair7Identity(root.appendingPathComponent(member.canonical_path))
        try pair7Require(info["bytes"] as? Int == member.bytes && info["sha256"] as? String == member.sha256,
                         "Canonical source changed during snapshot")
    }
    try pair7Require(try Data(contentsOf: closureFile) == closureData, "Closure changed during snapshot")
    let record: [String: Any] = [
        "schema": 1, "status": "actual-snapshot-java-source-data-only",
        "repository": "snowdamiz/mixer", "source_head": head,
        "run_id": run, "run_attempt": 1, "producer_job": "snapshot",
        "producer": "AndroidProject.snapshot(adapter:destination:)",
        "profile_id": closure.profile_id, "generated_snapshot_digest": digest,
        "source_manifest_sha256": SourceDigest.sha256(closureData),
        "producer_package_source_manifest_sha256": SourceDigest.sha256(try Data(contentsOf: packet.appendingPathComponent("snapshot-source-manifest.json"))),
        "producer_source_sha256": SourceDigest.sha256(try Data(contentsOf: URL(fileURLWithPath: #filePath))),
        "generator_source_sha256": SourceDigest.sha256(try Data(contentsOf: root.appendingPathComponent("cli/Sources/MixerBuild/AndroidProject.swift"))),
        "installed_workflow_sha256": SourceDigest.sha256(try Data(contentsOf: root.appendingPathComponent(".github/workflows/pair7-java-compile.yml"))),
        "apple_toolchain_receipt_sha256": SourceDigest.sha256(try Data(contentsOf: temp.appendingPathComponent("pair7-java-source-\(run)-1/apple-toolchain.json"))),
        "canonical_before_and_after": before, "generated_java": generatedRows,
        "generated_tree": treeRows, "additional_app_owned_Java": [],
        "actual_full_project_create": false, "actual_consumer_compile": false,
        "java_compiler_started_by_test": false, "native_runtime_started": false,
        "scratch_disposition": "Retained under this unique CI-owned output for artifact transfer."
    ]
    try pair7Write(record, to: output.appendingPathComponent("snapshot-receipt.json"))
    print("PAIR7_ACTUAL_SNAPSHOT_EXPORTED members=18 bytes=393165 source_head=\(head)")
}
