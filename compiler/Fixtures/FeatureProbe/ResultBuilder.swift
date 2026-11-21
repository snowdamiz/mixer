private struct MenuChildren {
    var cells: UInt32 = 0
    private var count = 0

    init() {}

    init(_ label: UInt8) {
        cells = UInt32(label)
        count = 1
    }

    mutating func append(_ children: Self) {
        cells |= children.cells << (count * 8)
        count += children.count
    }
}

@resultBuilder
private enum MenuBuilder {
    static func buildBlock(_ child: MenuChildren) -> MenuChildren { child }

    static func buildBlock(_ status: MenuChildren, _ rows: MenuChildren) -> MenuChildren {
        var result = status
        result.append(rows)
        return result
    }

    static func buildEither(first: MenuChildren) -> MenuChildren { first }
    static func buildEither(second: MenuChildren) -> MenuChildren { second }

    static func buildArray(_ rows: [MenuChildren]) -> MenuChildren {
        var result = MenuChildren()
        for row in rows {
            result.append(row)
        }
        return result
    }
}

struct ResultBuilderPreview {
    static let inputSize = 3
    static let outputSize = 4

    @MenuBuilder
    private static func menu(priority: Bool, first: UInt8, count: UInt8) -> MenuChildren {
        if priority {
            MenuChildren(0x21) // !
        } else {
            MenuChildren(0x2e) // .
        }
        for index in 0 ..< count {
            MenuChildren(0x30 + first + index)
        }
    }

    static func render(_ input: UnsafeRawBufferPointer, into output: UnsafeMutableRawBufferPointer) -> Bool {
        guard input.count == inputSize else { return false }
        let priority = input[0]
        let first = input[1]
        let count = input[2]
        guard priority <= 1, count <= 3, first <= 9, first + count <= 10 else { return false }

        let children = menu(priority: priority == 1, first: first, count: count)
        output.storeBytes(of: children.cells.littleEndian, as: UInt32.self)
        return true
    }
}
