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
