import Foundation
import XCTest
import MixerUpdates
@testable import MixerCapabilityActivation
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

final class CapabilityDurableDirectoryTests: XCTestCase {
    private func root() throws -> URL {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-capability-io-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: false)
        addTeardownBlock { try FileManager.default.removeItem(at: url) }
        return url
    }
    private let digest = String(repeating: "a", count: 64)

    func testExclusiveLockCloseAndReopenPreserveState() throws {
        let url = try root().appendingPathComponent("private")
        let directory = try CapabilityDurableDirectory(url: url, fault: nil)
        XCTAssertTrue(directory.wasCreated)
        try directory.atomicState(Data("exact-state".utf8))
        XCTAssertThrowsError(try CapabilityDurableDirectory(url: url, fault: nil))
        XCTAssertGreaterThan(try directory.availableBytes(), 0)
        directory.close(); directory.close()
        XCTAssertThrowsError(try directory.read("state.json", maximumBytes: 100))
        let reopened = try CapabilityDurableDirectory(url: url, fault: nil)
        defer { reopened.close() }
        XCTAssertFalse(reopened.wasCreated)
        XCTAssertEqual(try reopened.read("state.json", maximumBytes: 100), Data("exact-state".utf8))
    }

    func testDirectoryAndEntrySymlinksHardlinksFIFOReject() throws {
        let parent = try root(), real = parent.appendingPathComponent("real")
        try FileManager.default.createDirectory(at: real, withIntermediateDirectories: false)
        let alias = parent.appendingPathComponent("alias")
        try FileManager.default.createSymbolicLink(at: alias, withDestinationURL: real)
        XCTAssertThrowsError(try CapabilityDurableDirectory(url: alias, fault: nil))
        let directory = try CapabilityDurableDirectory(url: real, fault: nil)
        defer { directory.close() }
        let outside = parent.appendingPathComponent("outside")
        try Data("keep".utf8).write(to: outside)
        try FileManager.default.createSymbolicLink(at: real.appendingPathComponent("sym"), withDestinationURL: outside)
        try FileManager.default.linkItem(at: outside, to: real.appendingPathComponent("hard"))
        let fifo = real.appendingPathComponent("fifo")
        XCTAssertEqual(fifo.withUnsafeFileSystemRepresentation { mkfifo($0!, 0o600) }, 0)
        for name in ["sym", "hard", "fifo"] {
            XCTAssertThrowsError(try directory.read(name, maximumBytes: 100), name)
            XCTAssertThrowsError(try directory.size(name), name)
        }
        for name in ["../outside", "/outside", "", ".", "..", "nul\0name"] {
            XCTAssertThrowsError(try directory.read(name, maximumBytes: 100), name)
        }
        XCTAssertEqual(try Data(contentsOf: outside), Data("keep".utf8))
    }

    func testReadAppendAndStateCeilingsBeforeMutation() throws {
        let url = try root(), directory = try CapabilityDurableDirectory(url: url, fault: nil)
        defer { directory.close() }
        try directory.append(Data([1, 2]), to: "part", offset: 0, maximumBytes: 4)
        XCTAssertThrowsError(try directory.append(Data([3]), to: "part", offset: 0, maximumBytes: 4))
        XCTAssertThrowsError(try directory.append(Data([3, 4, 5]), to: "part", offset: 2, maximumBytes: 4))
        XCTAssertThrowsError(try directory.append(Data(repeating: 0, count: 1_048_577), to: "oversize", offset: 0, maximumBytes: 4_194_304))
        XCTAssertThrowsError(try directory.append(Data(), to: "overflow", offset: .max, maximumBytes: .max))
        XCTAssertFalse(FileManager.default.fileExists(atPath: url.appendingPathComponent("oversize").path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: url.appendingPathComponent("overflow").path))
        XCTAssertThrowsError(try directory.read("part", maximumBytes: 1))
        XCTAssertThrowsError(try directory.read("part", maximumBytes: -1))
        XCTAssertThrowsError(try directory.read("part", maximumBytes: 4_194_305))
        XCTAssertEqual(try directory.read("part", maximumBytes: 2), Data([1, 2]))
        try directory.atomicState(Data([9]))
        XCTAssertThrowsError(try directory.atomicState(Data(repeating: 0, count: 1_048_577)))
        XCTAssertEqual(try directory.read("state.json", maximumBytes: 1), Data([9]))
        try directory.append(Data([3, 4]), to: "part", offset: 2, maximumBytes: 4)
        XCTAssertEqual(try directory.size("part"), 4)
    }

    func testStateFaultsExposeOldOrNewExactBytesAndReopen() throws {
        let parent = try root()
        for point in [CapabilityDurabilityFaultPoint.beforeStateWrite, .beforeStateFileSync, .beforeStateRename, .afterStateRename, .afterStateDirectorySync] {
            let url = parent.appendingPathComponent(point.rawValue)
            let initial = try CapabilityDurableDirectory(url: url, fault: nil)
            try initial.atomicState(Data("old".utf8)); initial.close()
            let interrupted = try CapabilityDurableDirectory(url: url, fault: { if $0 == point { throw UpdateError("test.fault", point.rawValue) } })
            XCTAssertThrowsError(try interrupted.atomicState(Data("new".utf8)))
            interrupted.close()
            let reopened = try CapabilityDurableDirectory(url: url, fault: nil)
            let expected = [CapabilityDurabilityFaultPoint.afterStateRename, .afterStateDirectorySync].contains(point) ? "new" : "old"
            XCTAssertEqual(try reopened.read("state.json", maximumBytes: 3), Data(expected.utf8), point.rawValue)
            XCTAssertFalse(try FileManager.default.contentsOfDirectory(atPath: url.path).contains(where: { $0.hasPrefix(".state-") }))
            reopened.close()
        }
    }

    func testPayloadFaultsRetainActualWriteOrRenameOutcome() throws {
        let parent = try root()
        for point in [CapabilityDurabilityFaultPoint.beforePayloadWrite, .beforePayloadSync, .beforePayloadRename, .afterPayloadRename, .afterPayloadDirectorySync] {
            let url = parent.appendingPathComponent(point.rawValue)
            let initial = try CapabilityDurableDirectory(url: url, fault: nil)
            let isAppend = [CapabilityDurabilityFaultPoint.beforePayloadWrite, .beforePayloadSync].contains(point)
            if !isAppend { try initial.append(Data([7]), to: "part", offset: 0, maximumBytes: 1) }
            initial.close()
            let interrupted = try CapabilityDurableDirectory(url: url, fault: { if $0 == point { throw UpdateError("test.fault", point.rawValue) } })
            if isAppend { XCTAssertThrowsError(try interrupted.append(Data([7]), to: "part", offset: 0, maximumBytes: 1)) }
            else { XCTAssertThrowsError(try interrupted.publishPayload("part", as: "payload")) }
            interrupted.close()
            let reopened = try CapabilityDurableDirectory(url: url, fault: nil)
            if isAppend { XCTAssertEqual(try reopened.size("part"), point == .beforePayloadWrite ? 0 : 1) }
            else {
                let renamed = point != .beforePayloadRename
                XCTAssertEqual(try reopened.read(renamed ? "payload" : "part", maximumBytes: 1), Data([7]))
                XCTAssertNil(try reopened.size(renamed ? "part" : "payload"))
            }
            reopened.close()
        }
    }

    func testPruningOnlyOwnedNamesAndPinnedDescriptorAfterRename() throws {
        let parent = try root(), url = parent.appendingPathComponent("private"), moved = parent.appendingPathComponent("moved")
        let directory = try CapabilityDurableDirectory(url: url, fault: nil)
        defer { directory.close() }
        let stale = digest + ".payload", keep = digest + ".payload.part", temporary = ".state-" + UUID().uuidString + ".tmp"
        for name in [stale, keep, temporary, "user-data", "not-a-digest.payload", ".state-invalid.tmp"] { try Data([1]).write(to: url.appendingPathComponent(name)) }
        try FileManager.default.moveItem(at: url, to: moved)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: false)
        try Data([2]).write(to: url.appendingPathComponent(stale))
        try directory.pruneOwnedFiles(keeping: [keep])
        XCTAssertEqual(try Data(contentsOf: url.appendingPathComponent(stale)), Data([2]))
        XCTAssertFalse(FileManager.default.fileExists(atPath: moved.appendingPathComponent(stale).path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: moved.appendingPathComponent(temporary).path))
        for name in [keep, "user-data", "not-a-digest.payload", ".state-invalid.tmp", ".lock"] { XCTAssertTrue(FileManager.default.fileExists(atPath: moved.appendingPathComponent(name).path), name) }
        try directory.pruneOwnedFiles(keeping: [keep]) // Each listing starts at the beginning.
    }

    func testPruningTooManyEntriesRejectsBeforeDeletion() throws {
        let url = try root(), directory = try CapabilityDurableDirectory(url: url, fault: nil)
        defer { directory.close() }
        let owned = digest + ".payload"
        try Data([9]).write(to: url.appendingPathComponent(owned))
        for index in 0..<1023 { try Data().write(to: url.appendingPathComponent("foreign-\(index)")) }
        XCTAssertThrowsError(try directory.pruneOwnedFiles(keeping: []))
        XCTAssertEqual(try directory.read(owned, maximumBytes: 1), Data([9]))
    }
}
