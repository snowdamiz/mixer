private protocol ChecklistFormatter {
    func mark(_ completed: UInt8) -> UInt16
}

private struct DoneFormatter: ChecklistFormatter {
    func mark(_ completed: UInt8) -> UInt16 {
        UInt16(68) | UInt16(48 + completed) << 8
    }
}

private struct LeftFormatter: ChecklistFormatter {
    func mark(_ completed: UInt8) -> UInt16 {
        UInt16(76) | UInt16(51 - completed) << 8
    }
}

enum ChecklistFormatterPreview {
    static let inputSize = 2
    static let outputSize = 4

    static func render(_ input: UnsafeRawBufferPointer, into output: UnsafeMutableRawBufferPointer) -> Bool {
        guard input.count == inputSize, input[0] <= 1, input[1] <= 7 else { return false }
        let completed = UInt8(input[1].nonzeroBitCount)
        let mark = format(style: input[0], completed: completed)
        output[0] = UInt8(truncatingIfNeeded: mark)
        output[1] = UInt8(mark >> 8)
        output[2] = 47
        output[3] = 51
        return true
    }

    private static func format(style: UInt8, completed: UInt8) -> UInt16 {
#if STATIC_FORMATTER
        if style == 0 {
            return DoneFormatter().mark(completed)
        }
        return LeftFormatter().mark(completed)
#else
        let formatter: any ChecklistFormatter = selectedFormatter(for: style)
        return formatter.mark(completed)
#endif
    }

#if !STATIC_FORMATTER
    @inline(never)
    private static func selectedFormatter(for style: UInt8) -> any ChecklistFormatter {
        if style == 0 { return DoneFormatter() }
        return LeftFormatter()
    }
#endif
}

// The pinned compact guest adapter selects this name in its default branch.
typealias FloatingPointPreview = ChecklistFormatterPreview
