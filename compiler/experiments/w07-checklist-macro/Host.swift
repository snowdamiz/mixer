import Foundation

private struct NativeChecklist: TaskPath {
    var checklist = Checklist()

    mutating func activate(_ bytes: [UInt8]) -> Bool {
        bytes.withUnsafeBytes { checklist.accept($0) }
    }

    func frame() -> Data {
        var output = Data(count: 2048)
        let length = output.withUnsafeMutableBytes { checklist.frame(into: $0) }
        return output.prefix(length)
    }
}

private struct Turn: Encodable {
    let inputHex: String?
    let accepted: Bool?
    let frame: String
    let fuel: UInt64?
}

private func replay(_ path: inout some TaskPath) throws -> [Turn] {
    let cases: [([UInt8], Bool)] = [
        ([1, 5], true),
        ([2, 8], false),
        ([2], false),
        ([2, 7], true),
        ([3, 0], true),
    ]
    var last = try path.frame()
    var turns = [Turn(inputHex: nil, accepted: nil, frame: String(decoding: last, as: UTF8.self), fuel: nil)]
    for (input, expectedAcceptance) in cases {
        let accepted = try path.activate(input)
        let frame = try path.frame()
        try check(accepted == expectedAcceptance, "unexpected checklist event result")
        try check(accepted || frame == last, "refused checklist event changed its frame")
        turns.append(Turn(inputHex: input.map { String(format: "%02x", $0) }.joined(), accepted: accepted,
                          frame: String(decoding: frame, as: UTF8.self), fuel: (path as? OwnedTask)?.fuel))
        last = frame
    }
    return turns
}

private struct Replay: Encodable {
    let native: [Turn]
    let guest: [Turn]?
    let guestClosedAndStaleHandleRefused: Bool?
    let guestRegistrySlotReclaimed: Bool?
}

@main private enum Host {
    static func main() {
        do {
            let args = CommandLine.arguments
            try check(args.count == 1 || args.count == 2, "expected an optional Wasm path")
            var native = NativeChecklist()
            let nativeTurns = try replay(&native)
            var guestTurns: [Turn]?
            if args.count == 2 {
                var guest = OwnedTask(try Data(contentsOf: URL(fileURLWithPath: args[1])), measureComponents: false)
                try guest.open()
                let initialFrame = try guest.frame()
                guestTurns = try replay(&guest)
                try guest.closeAndCheckReclamation(initialFrame: initialFrame)
            }
            let result = Replay(native: nativeTurns, guest: guestTurns,
                                guestClosedAndStaleHandleRefused: guestTurns.map { _ in true },
                                guestRegistrySlotReclaimed: guestTurns.map { _ in true })
            print(String(decoding: try JSONEncoder().encode(result), as: UTF8.self))
        } catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            exit(1)
        }
    }
}
