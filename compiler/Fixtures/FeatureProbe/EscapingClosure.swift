private enum InspectionSelection {
    case title(UInt8)
    case inspection(UInt8)

    var kind: UInt8 {
        switch self {
        case .title: 1
        case .inspection: 2
        }
    }

    func render(_ adjustment: UInt8) -> UInt8 {
        switch self {
        case .title(let value): value &+ adjustment
        case .inspection(let value): value &- adjustment
        }
    }
}

#if !ESCAPING_CLOSURE_VALUE_ONLY
private final class InspectionCapture {
    nonisolated(unsafe) static var releaseCount: UInt8 = 0
    nonisolated(unsafe) static var lastReleasedKind: UInt8 = 0

    let selection: InspectionSelection

    init(_ selection: InspectionSelection) {
        self.selection = selection
    }

    deinit {
        Self.releaseCount &+= 1
        Self.lastReleasedKind = selection.kind
    }
}
#endif

struct EscapingClosurePreview {
    static let inputSize = 2
    static let outputSize = 4

    private var inspect: ((UInt8) -> UInt8)?
    private var selectedKind: UInt8 = 0

    @inline(never)
    private static func makeInspection(for selection: InspectionSelection) -> (UInt8) -> UInt8 {
#if ESCAPING_CLOSURE_VALUE_ONLY
        return { selection.render($0) }
#else
        let capture = InspectionCapture(selection)
        return { capture.selection.render($0) }
#endif
    }

    mutating func render(_ input: UnsafeRawBufferPointer, into output: UnsafeMutableRawBufferPointer) -> Bool {
        guard input.count == Self.inputSize else { return false }
        let operand = input[1]
        let value: UInt8
        switch input[0] {
        case 1, 2:
            let selection: InspectionSelection = input[0] == 1 ? .title(operand) : .inspection(operand)
            inspect = Self.makeInspection(for: selection)
            selectedKind = selection.kind
            value = 0
        case 3:
            guard let inspect else { return false }
            value = inspect(operand)
        case 4:
            guard operand == 0 else { return false }
            inspect = nil
            selectedKind = 0
            value = 0
        default:
            return false
        }

        output[0] = selectedKind
        output[1] = value
#if ESCAPING_CLOSURE_VALUE_ONLY
        output[2] = 0
        output[3] = 0
#else
        output[2] = InspectionCapture.releaseCount
        output[3] = InspectionCapture.lastReleasedKind
#endif
        return true
    }
}
