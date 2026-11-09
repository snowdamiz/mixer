import Foundation
import Darwin
@testable import MixerBuild

enum SuiteOwnedRunner {
    static func check() {
        if let hold = ProcessExecutionContext.localDevelopment.custodyHold {
            if let p = ProcessInfo.processInfo.environment["MIXER_SUITE_HOLD"] {
                let value = ["receiptDirectory": hold.receiptDirectory, "retainedInputDirectories": hold.retainedInputDirectories.joined(separator: "\n"), "reason": hold.reason]
                if let data = try? JSONSerialization.data(withJSONObject: value) { try? data.write(to: URL(fileURLWithPath: p), options: .atomic) }
            }
            Darwin._exit(125)
        }
    }
    static func guarded<T>(_ body: () throws -> T) throws -> T {
        check()
        do { let value = try body(); check(); return value }
        catch { check(); throw error }
    }
    static func run(_ command: [String]) throws -> CommandResult { try guarded { try ProcessRunner.run(command) } }
    static func verifyLock(root: URL, androidRequired: Bool = false) throws -> ToolchainLock { try guarded { try ProjectBuild.verifyLock(root: root, androidRequired: androidRequired) } }
    static func projectRun(root: URL, test: Bool, platform: String) throws -> CommandResult { try guarded { try ProjectBuild.run(root: root, test: test, platform: platform) } }
    static func export(root: URL, destination: URL) throws -> String { try guarded { try ProjectBuild.export(root: root, destination: destination) } }
    static func create(name: String, application: String, destination: URL, sdk: URL, platform: String = "ios", androidAdapter: URL? = nil) throws -> GeneratedProject { try guarded { try ProjectGenerator.create(name: name, application: application, destination: destination, sdk: sdk, platform: platform, androidAdapter: androidAdapter) } }
}
