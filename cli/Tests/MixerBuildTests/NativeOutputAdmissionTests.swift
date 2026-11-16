import Foundation
import XCTest
import Darwin
@testable import MixerBuild

final class NativeOutputAdmissionTests: XCTestCase {
    private func temporary(_ body: (URL) throws -> Void) throws {
        let configured = ProcessInfo.processInfo.environment["TMPDIR"]
        let parent = configured.flatMap { $0.isEmpty ? nil : $0 }
            ?? FileManager.default.temporaryDirectory.path
        let pointer = parent.withCString { realpath($0, nil) }
        guard let pointer else { throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EINVAL) }
        let canonicalParent = String(cString: pointer)
        free(pointer)
        let root = URL(fileURLWithPath: canonicalParent, isDirectory: true)
            .appendingPathComponent("native-output-unit-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false,
            attributes: [.posixPermissions: 0o700])
        defer {
            do { try FileManager.default.removeItem(at: root) }
            catch { XCTFail("Owned temporary fixture cleanup failed: \(error)") }
        }
        try body(root)
    }
    private func directory(_ root: URL, _ name: String, mode: Int = 0o700) throws -> URL {
        let url = root.appendingPathComponent(name)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true,
            attributes: [.posixPermissions: mode])
        try FileManager.default.setAttributes([.posixPermissions: mode], ofItemAtPath: url.path)
        return url
    }
    private func manifest(_ store: URL, bytes: Data = Data("{}".utf8), mode: Int = 0o444) throws -> URL {
        let file = store.appendingPathComponent("native-build.json")
        try bytes.write(to: file)
        try FileManager.default.setAttributes([.posixPermissions: mode], ofItemAtPath: file.path)
        return file
    }
    private func refuses(_ code: String, file: StaticString = #filePath, line: UInt = #line,
                         _ body: () throws -> Void) {
        XCTAssertThrowsError(try body(), file: file, line: line) {
            XCTAssertEqual(($0 as? MixerFailure)?.code, code, file: file, line: line)
        }
    }
    private func captureRefuses(_ failure: NativeProductCapture.Failure, app: URL, symbols: URL, store: URL,
                                binding: String = String(repeating: "a", count: 64),
                                file: StaticString = #filePath, line: UInt = #line) throws {
        XCTAssertThrowsError(try NativeProductCapture.capture(app: app, dSYM: symbols, store: store,
            bindingSHA256: binding), file: file, line: line) {
            XCTAssertEqual($0 as? NativeProductCapture.Failure, failure, file: file, line: line)
        }
        XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: store.path), [], file: file, line: line)
    }
    func testUnsupportedPlatformAndTestModeRefuseBeforeProjectOrOutputAccess() throws {
        try temporary { root in
            for (platform, test) in [("host", false), ("android", false), ("ios", true), ("unknown", false)] {
                let output = root.appendingPathComponent(UUID().uuidString)
                refuses("build.output-platform") {
                    _ = try ProjectBuild.runRetainingNative(root: root.appendingPathComponent("missing-project"),
                        test: test, platform: platform, output: output)
                }
                XCTAssertFalse(FileManager.default.fileExists(atPath: output.path))
            }
        }
    }
    func testSourceTreeDestinationsRefuseBeforeLockOrCompiler() throws {
        try temporary { root in
            let project = try directory(root, "project")
            for output in [project, project.appendingPathComponent("retained")] {
                refuses("build.output-path") {
                    _ = try ProjectBuild.runRetainingNative(root: project, test: false, platform: "ios", output: output)
                }
            }
            XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: project.path), [])
        }
    }
    func testPrepareCreatesExclusivePrivateStoreAndDetectsModeDrift() throws {
        try temporary { root in
            let output = root.appendingPathComponent("store")
            let store = try NativeBuildOutput.prepare(output: output, root: root.appendingPathComponent("project"))
            try store.check()
            XCTAssertEqual((try FileManager.default.attributesOfItem(atPath: output.path)[.posixPermissions] as? NSNumber)?.intValue, 0o700)
            refuses("build.output-exists") { _ = try NativeBuildOutput.prepare(output: output, root: root.appendingPathComponent("project")) }
            try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: output.path)
            refuses("build.output-store") { try store.check() }
        }
    }
    func testPrepareRejectsNonprivateParentWithoutCreatingStore() throws {
        try temporary { root in
            let parent = try directory(root, "public-parent", mode: 0o755)
            let output = parent.appendingPathComponent("store")
            refuses("build.output-private") { _ = try NativeBuildOutput.prepare(output: output, root: root.appendingPathComponent("project")) }
            XCTAssertFalse(FileManager.default.fileExists(atPath: output.path))
        }
    }
    func testPrepareRejectsLinkedAncestor() throws {
        try temporary { root in
            let parent = try directory(root, "real")
            let link = root.appendingPathComponent("link")
            try FileManager.default.createSymbolicLink(at: link, withDestinationURL: parent)
            refuses("build.output-path") { _ = try NativeBuildOutput.prepare(output: link.appendingPathComponent("store"), root: root.appendingPathComponent("project")) }
            XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: parent.path), [])
        }
    }
    func testStoreIdentityReplacementIsRefused() throws {
        try temporary { root in
            let output = root.appendingPathComponent("store")
            let store = try NativeBuildOutput.prepare(output: output, root: root.appendingPathComponent("project"))
            try FileManager.default.moveItem(at: output, to: root.appendingPathComponent("original"))
            _ = try directory(root, "store")
            refuses("build.output-store") { try store.check() }
        }
    }
    func testRegularReadonlyManifestReachesDecoder() throws {
        try temporary { root in
            let store = try directory(root, "store")
            _ = try manifest(store)
            XCTAssertThrowsError(try NativeBuildOutput.reopen(store: store)) {
                XCTAssertTrue($0 is DecodingError, "Admitted boundary fixture must reach report decoding: \($0)")
            }
        }
    }
    func testManifestSymlinksRefuseBeforeDecoderForReadableMissingAndUnreadableTargets() throws {
        try temporary { root in
            let readable = root.appendingPathComponent("readable")
            let unreadable = root.appendingPathComponent("unreadable")
            try Data("{}".utf8).write(to: readable)
            try Data("{}".utf8).write(to: unreadable)
            try FileManager.default.setAttributes([.posixPermissions: 0], ofItemAtPath: unreadable.path)
            defer { try? FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: unreadable.path) }
            for (index, target) in [readable, unreadable, root.appendingPathComponent("missing")].enumerated() {
                let store = try directory(root, "store-\(index)")
                try FileManager.default.createSymbolicLink(at: store.appendingPathComponent("native-build.json"), withDestinationURL: target)
                refuses("build.output-manifest") { _ = try NativeBuildOutput.reopen(store: store) }
            }
            XCTAssertEqual(try Data(contentsOf: readable), Data("{}".utf8))
        }
    }
    func testManifestWritableAndExecutableModesRefuseBeforeDecoder() throws {
        try temporary { root in
            for mode in [0o600, 0o644, 0o400, 0o445] {
                let store = try directory(root, "store-\(mode)")
                _ = try manifest(store, mode: mode)
                refuses("build.output-manifest") { _ = try NativeBuildOutput.reopen(store: store) }
            }
        }
    }
    func testManifestHardlinkRefusesBeforeDecoder() throws {
        try temporary { root in
            let store = try directory(root, "store")
            let file = try manifest(store)
            try FileManager.default.linkItem(at: file, to: root.appendingPathComponent("second-name"))
            refuses("build.output-manifest") { _ = try NativeBuildOutput.reopen(store: store) }
        }
    }
    func testManifestDirectoryAndFIFORefuseWithoutBlocking() throws {
        try temporary { root in
            let first = try directory(root, "directory-store")
            _ = try directory(first, "native-build.json")
            refuses("build.output-manifest") { _ = try NativeBuildOutput.reopen(store: first) }
            let second = try directory(root, "fifo-store")
            XCTAssertEqual(mkfifo(second.appendingPathComponent("native-build.json").path, 0o444), 0)
            refuses("build.output-manifest") { _ = try NativeBuildOutput.reopen(store: second) }
        }
    }
    func testManifestSizeBoundaryIsAdmittedAndOversizeRefused() throws {
        try temporary { root in
            for size in [8 * 1_048_576, 8 * 1_048_576 + 1] {
                let store = try directory(root, "store-\(size)")
                let file = try manifest(store, mode: 0o600)
                let handle = try FileHandle(forWritingTo: file)
                do { try handle.truncate(atOffset: UInt64(size)); try handle.close() }
                catch { try? handle.close(); throw error }
                try FileManager.default.setAttributes([.posixPermissions: 0o444], ofItemAtPath: file.path)
                if size == 8 * 1_048_576 {
                    XCTAssertThrowsError(try NativeBuildOutput.reopen(store: store)) { XCTAssertTrue($0 is DecodingError) }
                } else {
                    refuses("build.output-manifest") { _ = try NativeBuildOutput.reopen(store: store) }
                }
            }
        }
    }
    func testStoreAndAncestorSymlinksRefuseBeforeManifestAccess() throws {
        try temporary { root in
            let parent = try directory(root, "parent")
            let store = try directory(parent, "store")
            _ = try manifest(store)
            let storeLink = root.appendingPathComponent("store-link")
            try FileManager.default.createSymbolicLink(at: storeLink, withDestinationURL: store)
            let parentLink = root.appendingPathComponent("parent-link")
            try FileManager.default.createSymbolicLink(at: parentLink, withDestinationURL: parent)
            for path in [storeLink, parentLink.appendingPathComponent("store")] {
                refuses("build.output-path") { _ = try NativeBuildOutput.reopen(store: path) }
            }
        }
    }
    func testUnsafeStoreModeAndMissingManifestRefuse() throws {
        try temporary { root in
            let unsafe = try directory(root, "unsafe", mode: 0o755)
            _ = try manifest(unsafe)
            refuses("build.output-store") { _ = try NativeBuildOutput.reopen(store: unsafe) }
            let empty = try directory(root, "empty")
            refuses("build.output-manifest") { _ = try NativeBuildOutput.reopen(store: empty) }
        }
    }
    func testMalformedCaptureBindingRefusesBeforeInputReads() throws {
        try temporary { root in
            let store = try directory(root, "store")
            for binding in ["", String(repeating: "A", count: 64), String(repeating: "a", count: 63)] {
                try captureRefuses(.malformedProduct, app: root.appendingPathComponent("absent.app"),
                    symbols: root.appendingPathComponent("absent.dSYM"), store: store, binding: binding)
            }
        }
    }
    func testEmptyProductRefusesWithoutRetainedObjects() throws {
        try temporary { root in
            try captureRefuses(.malformedProduct, app: directory(root, "Empty.app"),
                symbols: directory(root, "Empty.dSYM"), store: directory(root, "store"))
        }
    }
    func testCaptureRejectsNestedSymlinkFIFOAndHardlinkedInputsWithoutRetention() throws {
        try temporary { root in
            let symbols = try directory(root, "Empty.dSYM")
            let store = try directory(root, "store")
            for kind in ["symlink", "fifo", "hardlink"] {
                let app = try directory(root, kind + ".app")
                let file = app.appendingPathComponent("unexpected")
                let external = root.appendingPathComponent("external-" + kind)
                if kind == "symlink" {
                    try FileManager.default.createSymbolicLink(at: file, withDestinationURL: external)
                } else if kind == "fifo" {
                    XCTAssertEqual(mkfifo(file.path, 0o600), 0)
                } else {
                    try Data("not-a-native-product".utf8).write(to: external)
                    try FileManager.default.linkItem(at: external, to: file)
                }
                try captureRefuses(.unsafeFile, app: app, symbols: symbols, store: store)
            }
        }
    }
    func testCaptureRejectsNonExecutableProductWithoutRetention() throws {
        try temporary { root in
            let app = try directory(root, "Invalid.app")
            let plist = try PropertyListSerialization.data(fromPropertyList:
                ["CFBundleExecutable": "Invalid", "CFBundlePackageType": "APPL"], format: .xml, options: 0)
            try plist.write(to: app.appendingPathComponent("Info.plist"))
            try Data("deliberately not Mach-O".utf8).write(to: app.appendingPathComponent("Invalid"))
            try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: app.appendingPathComponent("Invalid").path)
            try captureRefuses(.malformedProduct, app: app, symbols: directory(root, "Empty.dSYM"), store: directory(root, "store"))
        }
    }
}

extension NativeOutputAdmissionTests {
    // Explicitly synthetic UNIT fixtures. No compiler, native build, process, or app runs.
    private func unitImage(symbols: Bool) -> Data {
        let commandBytes = symbols ? 280 : 48
        var bytes = [UInt8](repeating: 0, count: 32 + commandBytes + (symbols ? 2 : 0))
        func word(_ value: UInt32, _ offset: Int) {
            for i in 0..<4 { bytes[offset + i] = UInt8(truncatingIfNeeded: value >> (8 * i)) }
        }
        func name(_ value: String, _ offset: Int) {
            for (i, byte) in value.utf8.enumerated() { bytes[offset + i] = byte }
        }
        word(0xfeedfacf, 0); word(0x0100000c, 4); word(symbols ? 10 : 2, 12)
        word(symbols ? 3 : 2, 16); word(UInt32(commandBytes), 20)
        word(0x1b, 32); word(24, 36)
        for i in 0..<16 { bytes[40 + i] = UInt8(i + 1) }
        word(0x32, 56); word(24, 60); word(7, 64)
        if symbols {
            word(0x19, 80); word(232, 84); name("__DWARF", 88); word(2, 144)
            for (i, section) in ["__debug_info", "__debug_abbrev"].enumerated() {
                let offset = 152 + i * 80
                name(section, offset); name("__DWARF", offset + 16)
                word(1, offset + 40); word(UInt32(312 + i), offset + 48)
                bytes[312 + i] = 1
            }
        }
        return Data(bytes)
    }

    private func unitFixture(_ root: URL) throws -> (inputs: BuildInputSnapshot.Inputs, parent: URL, report: NativeBuildOutput.Report) {
        let project = try directory(root, "project"), compiler = try directory(root, "compiler")
        let sdk = try directory(root, "sdk"), cli = try directory(root, "cli"), locks = try directory(root, "locks")
        for (base, name) in [(project, "main.unit"), (compiler, "compiler.unit"), (sdk, "sdk.unit")] {
            try Data("synthetic UNIT input".utf8).write(to: base.appendingPathComponent(name))
        }
        let executable = cli.appendingPathComponent("mixer"), lockFile = locks.appendingPathComponent("mixer.lock")
        try Data("synthetic UNIT non-executable CLI bytes".utf8).write(to: executable)
        let lock = ToolchainLock(sdkDigest: try SourceDigest.tree(sdk), swiftVersion: "synthetic UNIT fixture")
        try JSONFile.write(lock, to: lockFile)
        let binding = NativeBuildOutput.Binding(authoritativeSourceDigest: try SourceDigest.tree(project),
            lockSHA256: SourceDigest.sha256(try Data(contentsOf: lockFile)), lock: lock,
            sdkDigest: try SourceDigest.tree(sdk), compilerSourceDigest: try SourceDigest.tree(compiler),
            cliExecutableSHA256: SourceDigest.sha256(try Data(contentsOf: executable)),
            command: ["UNIT_FIXTURE_NO_COMPILER"], environment: [:], resourceInventoryPolicy: .retainedAppFilesV1)
        let app = try directory(root, "Unit.app"), symbols = try directory(root, "Unit.dSYM")
        try PropertyListSerialization.data(fromPropertyList: ["CFBundleExecutable": "Unit", "CFBundlePackageType": "APPL"],
            format: .xml, options: 0).write(to: app.appendingPathComponent("Info.plist"))
        try unitImage(symbols: false).write(to: app.appendingPathComponent("Unit"))
        try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: app.appendingPathComponent("Unit").path)
        let dwarf = try directory(symbols, "Contents/Resources/DWARF")
        try unitImage(symbols: true).write(to: dwarf.appendingPathComponent("Unit"))
        let parent = root.appendingPathComponent("parent")
        let store = try NativeBuildOutput.prepare(output: parent, root: project)
        let digest = SourceDigest.sha256(try JSONFile.data(binding))
        let capture = try NativeProductCapture.capture(app: app, dSYM: symbols, store: parent, bindingSHA256: digest)
        let inventory = try ResourceInventoryProduct.produce(capture: capture, captureStore: parent, store: parent, expectedBindingSHA256: digest)
        let report = NativeBuildOutput.Report(commandResult: .init(command: binding.command, exitCode: 0, output: "synthetic UNIT fixture"),
            nativeProduct: capture, binding: binding, scope: "unsigned-simulator/local-development", formatVersion: 2, resourceInventory: inventory)
        try store.persist(report)
        XCTAssertTrue(try NativeBuildOutput.reopen(store: parent).succeeded)
        return (.init(projectRoot: project, compilerRoot: compiler, sdkRoot: sdk, cliBinary: executable, lockFile: lockFile), parent, report)
    }

    private func unitRewrite(_ bytes: Data, at path: URL) throws {
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: path.path)
        try bytes.write(to: path)
        try FileManager.default.setAttributes([.posixPermissions: 0o444], ofItemAtPath: path.path)
    }

    func testUnitTypedInventoryVersionPolicyAndDeletionRefuse() throws {
        try temporary { root in
            let f = try unitFixture(root), path = f.parent.appendingPathComponent("native-build.json")
            let original = try Data(contentsOf: path)
            let value = try XCTUnwrap(JSONSerialization.jsonObject(with: original) as? [String: Any])
            for mutation in ["version-one", "version-future", "version-deleted", "inventory-deleted", "policy-deleted", "all-deleted", "unknown-policy"] {
                var changed = value, binding = try XCTUnwrap(value["binding"] as? [String: Any])
                switch mutation {
                case "version-one": changed["formatVersion"] = 1
                case "version-future": changed["formatVersion"] = 3
                case "version-deleted": changed.removeValue(forKey: "formatVersion")
                case "inventory-deleted": changed.removeValue(forKey: "resourceInventory")
                case "policy-deleted": binding.removeValue(forKey: "resourceInventoryPolicy"); changed["binding"] = binding
                case "all-deleted":
                    changed.removeValue(forKey: "formatVersion"); changed.removeValue(forKey: "resourceInventory")
                    binding.removeValue(forKey: "resourceInventoryPolicy"); changed["binding"] = binding
                default: binding["resourceInventoryPolicy"] = "unknown-policy"; changed["binding"] = binding
                }
                try unitRewrite(JSONSerialization.data(withJSONObject: changed, options: [.sortedKeys]), at: path)
                XCTAssertThrowsError(try NativeBuildOutput.reopen(store: f.parent), mutation)
            }
            try unitRewrite(original, at: path)
            XCTAssertTrue(try NativeBuildOutput.reopen(store: f.parent).succeeded)
        }
    }

    func testUnitSnapshotPrewriteIsolationIncludesNormalizedParentTraversal() throws {
        try temporary { root in
            let f = try unitFixture(root)
            let before = try SourceDigest.tree(root)
            for input in [f.inputs.projectRoot, f.inputs.compilerRoot, f.inputs.sdkRoot, f.parent,
                          f.inputs.cliBinary.deletingLastPathComponent(), f.inputs.lockFile.deletingLastPathComponent()] {
                let output = input.appendingPathComponent("absent/../snapshot")
                XCTAssertThrowsError(try BuildInputSnapshot.produce(inputs: f.inputs, parentStore: f.parent, output: output)) {
                    XCTAssertEqual($0 as? BuildInputSnapshot.Failure, .path)
                }
                XCTAssertFalse(FileManager.default.fileExists(atPath: input.appendingPathComponent("snapshot").path))
                XCTAssertFalse(FileManager.default.fileExists(atPath: input.appendingPathComponent("absent").path))
            }
            XCTAssertEqual(try SourceDigest.tree(root), before)
        }
    }

    func testUnitSnapshotDetectsCorruptedRetainedMaterialAndPreservesInputs() throws {
        try temporary { root in
            let f = try unitFixture(root), output = root.appendingPathComponent("snapshot")
            let descriptor = try BuildInputSnapshot.produce(inputs: f.inputs, parentStore: f.parent, output: output)
            let report = try BuildInputSnapshot.reopen(descriptor, store: output)
            let material = try XCTUnwrap(report.materials.first)
            let originalInputDigest = try SourceDigest.tree(f.inputs.projectRoot)
            try unitRewrite(Data("corrupt retained UNIT material".utf8), at: output.appendingPathComponent(material.objectPath))
            XCTAssertThrowsError(try BuildInputSnapshot.retainedMaterials(descriptor, store: output)) {
                XCTAssertEqual($0 as? BuildInputSnapshot.Failure, .corrupt)
            }
            XCTAssertEqual(try SourceDigest.tree(f.inputs.projectRoot), originalInputDigest)
            XCTAssertTrue(try NativeBuildOutput.reopen(store: f.parent).succeeded)
        }
    }

    func testUnitSnapshotRevalidatesRetainedParent() throws {
        try temporary { root in
            let f = try unitFixture(root), output = root.appendingPathComponent("snapshot")
            let descriptor = try BuildInputSnapshot.produce(inputs: f.inputs, parentStore: f.parent, output: output)
            _ = try BuildInputSnapshot.reopen(descriptor, store: output)
            let parent = try NativeBuildOutput.reopen(store: output.appendingPathComponent("parents"))
            let capture = try XCTUnwrap(parent.nativeProduct)
            try unitRewrite(Data("corrupt retained UNIT parent".utf8), at: URL(fileURLWithPath: capture.nativeBinary.ownedPath))
            XCTAssertThrowsError(try BuildInputSnapshot.reopen(descriptor, store: output)) {
                XCTAssertEqual($0 as? NativeProductCapture.Failure, .corruptObject)
            }
            XCTAssertTrue(try NativeBuildOutput.reopen(store: f.parent).succeeded)
        }
    }

    func testUnitSBOMDescriptorBindsSnapshotAndAllParentProducts() throws {
        try temporary { root in
            let f = try unitFixture(root), snapshot = root.appendingPathComponent("snapshot")
            let descriptor = try BuildInputSnapshot.produce(inputs: f.inputs, parentStore: f.parent, output: snapshot)
            let output = try directory(root, "sbom"), original = f.parent.appendingPathComponent("native-build.json")
            let sbom = try SamePublicBuildSBOM.produce(snapshot: descriptor, snapshotStore: snapshot,
                originalReport: original, created: "2026-11-16T00:00:00Z", output: output)
            try SamePublicBuildSBOM.reopen(sbom, snapshotStore: snapshot, originalReport: original, output: output)
            let value = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONFile.data(sbom)) as? [String: Any])
            for key in ["bindingSHA256", "nativeSHA256", "symbolsSHA256", "inventorySHA256", "originalReportSHA256", "materialRows"] {
                var changed = value
                if key == "materialRows" { changed[key] = sbom.materialRows + 1 }
                else { changed[key] = String(repeating: "0", count: 64) }
                let bad = try JSONDecoder().decode(SamePublicBuildSBOM.Descriptor.self, from: JSONSerialization.data(withJSONObject: changed))
                XCTAssertThrowsError(try SamePublicBuildSBOM.reopen(bad, snapshotStore: snapshot, originalReport: original, output: output), key) {
                    XCTAssertTrue($0 is SamePublicBuildSBOM.Failure)
                }
            }
            XCTAssertThrowsError(try SamePublicBuildSBOM.requireAggregateEligible(sbom))
            XCTAssertThrowsError(try BuildInputSnapshot.requireAggregateEligible(descriptor))
        }
    }

    func testUnitProvenanceDescriptorRejectsForeignPathAndExpandedClaims() throws {
        try temporary { root in
            let snapshot = BuildInputSnapshot.Descriptor(sha256: String(repeating: "a", count: 64), sizeBytes: 1)
            let sbomProduct = try JSONDecoder().decode(SBOMProduct.Descriptor.self, from: Data("{\"kind\":\"sbom\",\"sha256\":\"unit\",\"sizeBytes\":1,\"ownedPath\":\"unit\",\"completeness\":\"verified_subset\",\"gaps\":[]}".utf8))
            let sbom = SamePublicBuildSBOM.Descriptor(snapshot: snapshot, originalReportSHA256: "unit", bindingSHA256: "unit",
                nativeSHA256: "unit", symbolsSHA256: "unit", inventorySHA256: "unit", materialRows: 1, created: "unit", sbom: sbomProduct)
            let evidence = root.appendingPathComponent("evidence")
            func identity(_ name: String) -> SamePublicBuildProvenance.FileIdentity {
                .init(logicalPath: name, path: evidence.appendingPathComponent(name).path, sha256: "unit", sizeBytes: 1)
            }
            let inputs = SamePublicBuildProvenance.Inputs(snapshot: snapshot, snapshotStore: root.appendingPathComponent("snapshot"),
                originalReport: identity("original"), sbom: sbom, sbomStore: root.appendingPathComponent("sbom"),
                publicInvocation: identity("invocation"), identityProof: identity("proof"), nativeCustody: identity("custody"), observerImplementation: identity("observer"))
            let output = try directory(root, "provenance"), digest = String(repeating: "a", count: 64)
            for descriptor in [
                SamePublicBuildProvenance.Descriptor(sha256: digest, sizeBytes: 1, ownedPath: root.appendingPathComponent(digest).path, completeness: "verified_subset", unsigned: true),
                .init(sha256: digest, sizeBytes: 1, ownedPath: output.path + "/" + digest, completeness: "complete", unsigned: true),
                .init(sha256: digest, sizeBytes: 1, ownedPath: output.path + "/" + digest, completeness: "verified_subset", unsigned: false)
            ] {
                XCTAssertThrowsError(try SamePublicBuildProvenance.reopen(descriptor, inputs: inputs, store: output)) {
                    guard case SamePublicBuildProvenance.Failure.identity = $0 else { return XCTFail("Wrong descriptor refusal: \($0)") }
                }
                XCTAssertThrowsError(try SamePublicBuildProvenance.requireAggregateEligible(descriptor))
            }
            XCTAssertEqual(try FileManager.default.contentsOfDirectory(atPath: output.path), [])
        }
    }

    // These records are synthetic UNIT evidence, never native execution qualification.
    private func unitPublicRequest(_ root: URL, custody: [String: Any]? = nil) throws -> SameBuildPublicReport.Request {
        let fixture = try unitFixture(root)
        let evidence = try directory(root, "evidence")
        func identity(_ name: String, _ data: Data) throws -> SamePublicBuildProvenance.FileIdentity {
            let target = evidence.appendingPathComponent(name)
            try data.write(to: target)
            return .init(logicalPath: name, path: target.path, sha256: SourceDigest.sha256(data), sizeBytes: UInt64(data.count))
        }
        func json(_ object: [String: Any]) throws -> Data {
            try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        }
        let binding = fixture.report.binding
        let original = fixture.parent.appendingPathComponent("native-build.json")
        let raw = try Data(contentsOf: original)
        let originalIdentity = SamePublicBuildProvenance.FileIdentity(logicalPath: "original-report.json",
            path: original.path, sha256: SourceDigest.sha256(raw), sizeBytes: UInt64(raw.count))
        let invocation = try identity("invocation.json", json(["argv": [fixture.inputs.cliBinary.path,
            "build", "--platform", "ios", "--directory", fixture.inputs.projectRoot.path,
            "--output", fixture.parent.path], "environment": [String: String]()]))
        let proof = try identity("proof.json", json(["allEqualToCapturedBinding": true, "observed": [
            "cliExecutableSHA256": binding.cliExecutableSHA256, "compilerSourceDigest": binding.compilerSourceDigest,
            "lockSHA256": binding.lockSHA256, "projectSourceDigest": binding.authoritativeSourceDigest,
            "sdkDigest": binding.sdkDigest]]))
        let record = custody ?? ["command": binding.command, "directory": fixture.inputs.projectRoot.path,
            "exitCode": 0, "state": "TERMINAL", "terminalCustody": true, "directChildReaped": true,
            "stdoutEOF": true, "stderrEOF": true, "descriptorsClosed": true, "ownedGroupAbsent": true,
            "released": true, "outputTruncated": false, "pid": 1, "ownedPGID": 1, "ownedSession": 1]
        let native = try identity("custody.json", json(record))
        let observer = try identity("observer.swift", Data("synthetic UNIT observer".utf8))
        return .init(projectRoot: fixture.inputs.projectRoot.path, compilerRoot: fixture.inputs.compilerRoot.path,
            sdkRoot: fixture.inputs.sdkRoot.path, cliBinary: fixture.inputs.cliBinary.path,
            lockFile: fixture.inputs.lockFile.path, nativeStore: fixture.parent.path,
            evidence: .init(originalReport: originalIdentity, publicInvocation: invocation, identityProof: proof,
                nativeCustody: native, observerImplementation: observer), created: "2026-11-16T00:00:00Z")
    }
    func testUnitPublicReportCompositionReopensWithoutOriginalRoots() throws {
        try temporary { root in
            let request = try unitPublicRequest(root), output = root.appendingPathComponent("report")
            let result = try SameBuildPublicReport.observe(request: request, output: output)
            XCTAssertEqual(result.completeness, "verified_subset"); XCTAssertTrue(result.unsigned)
            XCTAssertThrowsError(try SameBuildPublicReport.requireAggregateEligible(result))
            for path in ["project", "compiler", "sdk", "cli", "locks", "parent", "evidence"] {
                try FileManager.default.removeItem(at: root.appendingPathComponent(path))
            }
            let reopened = try SameBuildPublicReport.reopen(output: output)
            XCTAssertEqual(reopened.sbom.nativeSHA256, result.sbom.nativeSHA256)
            XCTAssertEqual(reopened.provenance.sha256, result.provenance.sha256)
            XCTAssertEqual(reopened.snapshot, result.snapshot)
        }
    }
    func testUnitPublicReportCommandResultAloneCannotClaimCustody() throws {
        try temporary { root in
            let request = try unitPublicRequest(root, custody: ["command": ["UNIT_FIXTURE_NO_COMPILER"],
                "exitCode": 0, "output": "synthetic UNIT exit alone", "outputTruncated": false])
            let output = root.appendingPathComponent("report")
            XCTAssertThrowsError(try SameBuildPublicReport.observe(request: request, output: output))
            XCTAssertFalse(FileManager.default.fileExists(atPath: output.appendingPathComponent("report.json").path))
        }
    }
    func testUnitPublicReportChangedRawEvidenceRefusesBeforeOutput() throws {
        try temporary { root in
            let request = try unitPublicRequest(root), output = root.appendingPathComponent("report")
            try unitRewrite(Data("changed raw invocation".utf8), at: URL(fileURLWithPath: request.evidence.publicInvocation.path))
            XCTAssertThrowsError(try SameBuildPublicReport.observe(request: request, output: output))
            XCTAssertFalse(FileManager.default.fileExists(atPath: output.path))
        }
    }
    func testUnitPublicReportFailedCompilerAndMissingInventoryRefusePublication() throws {
        for mutation in ["compiler", "inventory", "policy"] {
            try temporary { root in
                let request = try unitPublicRequest(root)
                let original = URL(fileURLWithPath: request.evidence.originalReport.path)
                var raw = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: original)) as? [String: Any])
                if mutation == "compiler" {
                    var command = try XCTUnwrap(raw["commandResult"] as? [String: Any])
                    command["exitCode"] = 1; raw["commandResult"] = command
                } else if mutation == "inventory" { raw.removeValue(forKey: "resourceInventory") }
                else {
                    var binding = try XCTUnwrap(raw["binding"] as? [String: Any])
                    binding.removeValue(forKey: "resourceInventoryPolicy"); raw["binding"] = binding
                }
                let bytes = try JSONSerialization.data(withJSONObject: raw, options: [.sortedKeys])
                try unitRewrite(bytes, at: original)
                let evidence = SameBuildPublicReport.Evidence(originalReport: .init(logicalPath: "original-report.json",
                    path: original.path, sha256: SourceDigest.sha256(bytes), sizeBytes: UInt64(bytes.count)),
                    publicInvocation: request.evidence.publicInvocation, identityProof: request.evidence.identityProof,
                    nativeCustody: request.evidence.nativeCustody, observerImplementation: request.evidence.observerImplementation)
                let changed = SameBuildPublicReport.Request(projectRoot: request.projectRoot, compilerRoot: request.compilerRoot,
                    sdkRoot: request.sdkRoot, cliBinary: request.cliBinary, lockFile: request.lockFile,
                    nativeStore: request.nativeStore, evidence: evidence, created: request.created)
                let output = root.appendingPathComponent("report")
                XCTAssertThrowsError(try SameBuildPublicReport.observe(request: changed, output: output))
                XCTAssertFalse(FileManager.default.fileExists(atPath: output.appendingPathComponent("report.json").path))
            }
        }
    }
    func testUnitPublicReportRequestIsBoundedAndRejectsSymlink() throws {
        try temporary { root in
            let file = root.appendingPathComponent("request.json")
            let request = try unitPublicRequest(root)
            let valid = try JSONEncoder().encode(request)
            XCTAssertLessThan(valid.count, SameBuildPublicReport.requestByteLimit)
            let oversized = valid + Data(repeating: 32,
                count: SameBuildPublicReport.requestByteLimit + 1 - valid.count)
            let uncheckedOversized = try JSONDecoder().decode(SameBuildPublicReport.Request.self, from: oversized)
            XCTAssertEqual(uncheckedOversized.compilerRoot, request.compilerRoot)
            try oversized.write(to: file)
            XCTAssertThrowsError(try SameBuildPublicReport.readRequest(file)) { error in
                XCTAssertEqual((error as? MixerFailure)?.code, "update.input-size")
            }
            let target = root.appendingPathComponent("valid-request.json")
            try valid.write(to: target)
            let admitted = try SameBuildPublicReport.readRequest(target)
            XCTAssertEqual(admitted.compilerRoot, request.compilerRoot)
            let link = root.appendingPathComponent("link.json")
            try FileManager.default.createSymbolicLink(at: link, withDestinationURL: target)
            let uncheckedSymlink = try JSONDecoder().decode(SameBuildPublicReport.Request.self,
                from: Data(contentsOf: link))
            XCTAssertEqual(uncheckedSymlink.compilerRoot, request.compilerRoot)
            XCTAssertThrowsError(try SameBuildPublicReport.readRequest(link)) { error in
                XCTAssertEqual((error as? MixerFailure)?.code, "update.input-type")
            }
        }
    }

    func testUnitPublicReportEntrypointRegistersRequestAndOutput() throws {
        try temporary { root in
            let environment = ProcessInfo.processInfo.environment
            let executable = try XCTUnwrap(environment["MIXER_STORE_TEST_CLI"])
            let original = try XCTUnwrap(environment["R3974_ORIGINAL_CLI"])
            let missing = root.appendingPathComponent("missing-request.json")
            let output = root.appendingPathComponent("report")
            let arguments = ["report", "--request", missing.path, "--output", output.path]
            let baseline = try StoreCLIChild.run(original, arguments, environment: environment)
            XCTAssertEqual(baseline.0, 1)
            let baselineJSON = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(baseline.1.utf8)) as? [String: Any])
            XCTAssertEqual(baselineJSON["code"] as? String, "arguments.unused-option")
            let corrected = try StoreCLIChild.run(executable, arguments, environment: environment)
            XCTAssertEqual(corrected.0, 1)
            let correctedJSON = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(corrected.1.utf8)) as? [String: Any])
            XCTAssertEqual(correctedJSON["code"] as? String, "update.input-type")
            XCTAssertFalse(FileManager.default.fileExists(atPath: output.path))
        }
    }
}
