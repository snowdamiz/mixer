// Review-only internal consumer. @testable is intentionally not a public API
// claim; the linked production library and its source are unmodified.
import Foundation
import MixerUpdates
@testable import MixerCapabilityActivation
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

struct ProbeFailure: Error { let message: String }
var checks = 0
@MainActor func check(_ value: @autoclosure () throws -> Bool, _ message: String) throws {
    checks += 1
    guard try value() else { throw ProbeFailure(message: message) }
}
@MainActor func rejects(_ message: String, _ body: () throws -> Void) throws {
    var rejected = false
    do { try body() } catch { rejected = true }
    try check(rejected, message)
}

let root = FileManager.default.temporaryDirectory.appendingPathComponent("mixer-io-independent-" + UUID().uuidString, isDirectory: true)
try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
defer { try? FileManager.default.removeItem(at: root) }
let digest = String(repeating: "c", count: 64)

do {
    let location = root.appendingPathComponent("inventory"), directory = try CapabilityDurableDirectory(url: location, fault: nil)
    defer { directory.close() }
    let owned = digest + ".payload"
    try Data([7]).write(to: location.appendingPathComponent(owned))
    for index in 0..<1022 { try Data().write(to: location.appendingPathComponent("foreign-\(index)")) }
    // .lock +1022 foreign +1 owned is the exact1024-entry permitted inventory.
    try directory.pruneOwnedFiles(keeping: [])
    try check(!FileManager.default.fileExists(atPath: location.appendingPathComponent(owned).path), "exact1024 inventory must prune")
    try check(try FileManager.default.contentsOfDirectory(atPath: location.path).count == 1023, "foreign inventory retained")
    try Data([8]).write(to: location.appendingPathComponent(owned))
    try directory.pruneOwnedFiles(keeping: [owned])
    try check(try directory.read(owned, maximumBytes: 1) == Data([8]), "fresh listing and keep set")
    try Data().write(to: location.appendingPathComponent("over-limit"))
    try rejects("1025 inventory must reject") { try directory.pruneOwnedFiles(keeping: []) }
    try check(try directory.read(owned, maximumBytes: 1) == Data([8]), "over-limit inventory makes no deletion")
}

do {
    let location = root.appendingPathComponent("original"), moved = root.appendingPathComponent("moved"), outside = root.appendingPathComponent("replacement")
    let directory = try CapabilityDurableDirectory(url: location, fault: nil)
    defer { directory.close() }
    try directory.atomicState(Data("before".utf8))
    try directory.append(Data([1]), to: "part", offset: 0, maximumBytes: 2)
    try FileManager.default.moveItem(at: location, to: moved)
    try FileManager.default.createDirectory(at: outside, withIntermediateDirectories: false)
    try Data("outside".utf8).write(to: outside.appendingPathComponent("state.json"))
    try Data([9]).write(to: outside.appendingPathComponent(digest + ".payload"))
    try FileManager.default.createSymbolicLink(at: location, withDestinationURL: outside)
    try directory.atomicState(Data("after".utf8))
    try directory.append(Data([2]), to: "part", offset: 1, maximumBytes: 2)
    try directory.publishPayload("part", as: digest + ".payload")
    try check(try directory.read("state.json", maximumBytes: 5) == Data("after".utf8), "state operations stay on held fd")
    try check(try directory.read(digest + ".payload", maximumBytes: 2) == Data([1,2]), "payload operations stay on held fd")
    try check(try directory.size(digest + ".payload") == 2, "size stays on held fd")
    try directory.pruneOwnedFiles(keeping: [])
    try check(try directory.size(digest + ".payload") == nil, "prune removed held-directory payload")
    try check(try Data(contentsOf: outside.appendingPathComponent("state.json")) == Data("outside".utf8), "replacement state untouched")
    try check(try Data(contentsOf: outside.appendingPathComponent(digest + ".payload")) == Data([9]), "replacement owned-looking name untouched")
    try directory.remove("state.json")
    try check(try directory.read("state.json", maximumBytes: 5) == nil, "remove stays on held fd")
}

for kind in ["symlink", "hardlink", "fifo"] {
    let location = root.appendingPathComponent("lock-" + kind), target = root.appendingPathComponent("target-" + kind)
    try FileManager.default.createDirectory(at: location, withIntermediateDirectories: false)
    try Data([4,5,6]).write(to: target)
    let lock = location.appendingPathComponent(".lock")
    if kind == "symlink" { try FileManager.default.createSymbolicLink(at: lock, withDestinationURL: target) }
    else if kind == "hardlink" { try FileManager.default.linkItem(at: target, to: lock) }
    else { try check(lock.withUnsafeFileSystemRepresentation { mkfifo($0!, 0o600) } == 0, "create lock FIFO") }
    try rejects("nonprivate regular lock rejected: " + kind) { _ = try CapabilityDurableDirectory(url: location, fault: nil) }
    try check(try Data(contentsOf: target) == Data([4,5,6]), "lock rejection cannot modify outside target")
}

do {
    let location = root.appendingPathComponent("fifo-append"), directory = try CapabilityDurableDirectory(url: location, fault: nil)
    let fifo = location.appendingPathComponent("fifo")
    try check(fifo.withUnsafeFileSystemRepresentation { mkfifo($0!, 0o600) } == 0, "create append FIFO")
    try rejects("FIFO append must reject without hanging or writing") { try directory.append(Data([1]), to: "fifo", offset: 0, maximumBytes: 1) }
    try directory.atomicState(Data([1])); directory.close()
    try rejects("closed state mutation") { try directory.atomicState(Data([2])) }
    try rejects("closed append") { try directory.append(Data([2]), to: "part", offset: 0, maximumBytes: 1) }
    try rejects("closed publish") { try directory.publishPayload("part", as: "payload") }
    try rejects("closed remove") { try directory.remove("state.json") }
    try rejects("closed size") { _ = try directory.size("state.json") }
    try rejects("closed disk query") { _ = try directory.availableBytes() }
    try rejects("closed prune") { try directory.pruneOwnedFiles(keeping: []) }
    try check(try Data(contentsOf: location.appendingPathComponent("state.json")) == Data([1]), "closed operations preserve state")
}
print("internal unmodified-library durable I/O probe passed \(checks) checks")
