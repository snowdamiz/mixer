import Foundation

private struct NativeChecklist: TaskPath {
    private var output = Data(count: ChecklistFormatterPreview.outputSize)

    func frame() -> Data { output }

    mutating func activate(_ bytes: [UInt8]) -> Bool {
        bytes.withUnsafeBytes { input in
            output.withUnsafeMutableBytes { ChecklistFormatterPreview.render(input, into: $0) }
        }
    }
}

private struct Readback: Encodable {
    let name: String
    let inputHex: String?
    let accepted: Bool?
    let frameHex: String
    let fuel: UInt64?
}

@main private enum Replay {
    static func main() throws {
        let arguments = CommandLine.arguments
        if arguments.count == 1 {
            var native = NativeChecklist()
            try exercise(&native)
        } else {
            try check(arguments.count == 2, "expected a single Wasm path")
            var owned = OwnedTask(try Data(contentsOf: URL(fileURLWithPath: arguments[1])), measureComponents: false)
            try owned.open()
            try exercise(&owned, owned: owned)
        }
    }

    private static func exercise(_ path: inout some TaskPath, owned: OwnedTask? = nil) throws {
        let cases: [(String, [UInt8], String?)] = [
            ("done", [0, 5], "44322f33"),  // D2/3
            ("left", [1, 5], "4c312f33"),  // L1/3, same checklist
            ("unknown-style", [2, 5], nil),
            ("out-of-range-mask", [1, 8], nil),
            ("truncated", [1], nil),
            ("oversized", [0, 5, 0], nil),
            ("done-empty", [0, 0], "44302f33"),
            ("left-all-done", [1, 7], "4c302f33"),
        ]
        let initial = try path.frame()
        try check(initial == Data(count: 4), "invalid initial frame")
        var prior = initial
        var rows = [Readback(name: "initial", inputHex: nil, accepted: nil, frameHex: hex(initial), fuel: nil)]
        for (name, input, expected) in cases {
            let accepted = try path.activate(input)
            let frame = try path.frame()
            try check(accepted == (expected != nil), "\(name): wrong event status")
            try check(hex(frame) == (expected ?? hex(prior)), "\(name): wrong frame \(hex(frame))")
            if let owned { try check((1...1_000_000).contains(owned.fuel), "\(name): fuel out of scope") }
            rows.append(Readback(name: name, inputHex: hex(input), accepted: accepted,
                                 frameHex: hex(frame), fuel: owned?.fuel))
            prior = frame
        }
        try owned?.closeAndCheckReclamation(initialFrame: initial)
        print(String(decoding: try JSONEncoder().encode(rows), as: UTF8.self))
    }

    private static func hex(_ bytes: some Sequence<UInt8>) -> String {
        bytes.map { String(format: "%02x", $0) }.joined()
    }
}
