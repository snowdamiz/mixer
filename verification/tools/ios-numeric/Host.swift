import Foundation
import SwiftUI

enum Qualification {
    struct Failure: Error, CustomStringConvertible { let description: String }

    static func run() throws -> Int {
        var total = 0
        for count in [27944, 1290, 560] {
            guard let folder = Bundle.main.resourceURL?.appendingPathComponent("oracle") else {
                throw Failure(description: "Missing oracle resource folder")
            }
            let data = try Data(contentsOf: folder.appendingPathComponent("\(count).input"))
            let expected = try String(contentsOf: folder.appendingPathComponent("\(count).expected"), encoding: .utf8)
                .split(separator: "\n").map(String.init)
            guard let cases = try JSONSerialization.jsonObject(with: data) as? [[String: Any]],
                  cases.count == count, expected.count == count else {
                throw Failure(description: "Oracle count mismatch")
            }
            for (index, item) in cases.enumerated() {
                guard let hex = item["hex"] as? String, let width = item["width"] as? Int,
                      let nanAllowed = item["nan"] as? Bool, let canonical = item["canonical"] as? Bool else {
                    throw Failure(description: "Oracle case schema mismatch")
                }
                let characters = Array(hex.utf8)
                guard characters.count % 2 == 0 else { throw Failure(description: "Invalid hex length") }
                func nibble(_ byte: UInt8) throws -> UInt8 {
                    switch byte {
                    case 48...57: return byte - 48
                    case 97...102: return byte - 87
                    default: throw Failure(description: "Invalid lowercase hex byte")
                    }
                }
                var module = [UInt8]()
                module.reserveCapacity(characters.count / 2)
                for i in stride(from: 0, to: characters.count, by: 2) {
                    module.append(try nibble(characters[i]) << 4 | nibble(characters[i + 1]))
                }
                var report = MixerVmReport()
                let export = Array("run".utf8)
                let status = module.withUnsafeBufferPointer { bytes in
                    export.withUnsafeBufferPointer { name in
                        mixer_vm_invoke_numeric_v2(bytes.baseAddress, bytes.count,
                            name.baseAddress, name.count, nil, 0, nil, &report)
                    }
                }
                let actual: String
                if status == 2 {
                    actual = "trap"
                } else if status == 0 {
                    guard report.value_type == 1 || report.value_type == 2 else {
                        throw Failure(description: "Reference result must be reinterpreted integer")
                    }
                    let bits = report.value_type == 1
                        ? UInt64(UInt32(truncatingIfNeeded: report.value)) : UInt64(bitPattern: report.value)
                    let isNaN = width == 32
                        ? bits & 0x7f800000 == 0x7f800000 && bits & 0x7fffff != 0
                        : bits & 0x7ff0000000000000 == 0x7ff0000000000000 && bits & 0xfffffffffffff != 0
                    if nanAllowed && isNaN {
                        let quiet = width == 32 ? bits & 0x400000 != 0 : bits & 0x8000000000000 != 0
                        let isCanonical = width == 32 ? bits & 0x7fffffff == 0x7fc00000
                            : bits & 0x7fffffffffffffff == 0x7ff8000000000000
                        guard quiet && (!canonical || isCanonical) else {
                            throw Failure(description: "Invalid NaN at \(count):\(index)")
                        }
                        actual = "nan"
                    } else {
                        actual = String(report.value)
                    }
                } else {
                    throw Failure(description: "Validation/API/panic status \(status) at \(count):\(index)")
                }
                guard actual == expected[index] else {
                    throw Failure(description: "Mismatch at \(count):\(index): \(actual) != \(expected[index])")
                }
                total += 1
            }
            print("MIXER_NUMERIC_GROUP_PASSED \(count)")
        }
        return total
    }
}

@main
struct NumericHost: App {
    var body: some Scene {
        WindowGroup {
            VStack(spacing: 16) {
                ProgressView()
                Text("Checking the owned numeric runtime")
                Text("Development qualification only").foregroundStyle(.secondary)
            }
            .task {
                let result = await Task.detached(priority: .userInitiated) { () -> String in
                    do { return "MIXER_NUMERIC_IOS_PASSED \(try Qualification.run())" }
                    catch { return "MIXER_NUMERIC_IOS_FAILED \(error)" }
                }.value
                print(result)
                fflush(nil)
                // This dedicated development harness exits after emitting its receipt.
                exit(result == "MIXER_NUMERIC_IOS_PASSED 29794" ? 0 : 1)
            }
        }
    }
}
