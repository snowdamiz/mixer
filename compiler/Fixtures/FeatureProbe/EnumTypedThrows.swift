private struct LineItem {
    let quantity: UInt8
    let unitPrice: UInt8
}

private enum QuoteAction {
    case item(LineItem)
    case flatFee(UInt8)
}

private enum QuoteRefusal: Error {
    case overLimit(total: UInt32)
}

struct EnumTypedThrowsPreview {
    static let inputSize = 3
    static let outputSize = 8

    private var refusedTotal: UInt32 = 0

    private static func quote(_ action: QuoteAction) throws(QuoteRefusal) -> UInt32 {
        switch action {
        case .item(let item):
            let total = UInt32(item.quantity) * UInt32(item.unitPrice)
            guard total <= 1_000 else { throw .overLimit(total: total) }
            return total
        case .flatFee(let fee):
            return UInt32(fee)
        }
    }

    mutating func render(_ input: UnsafeRawBufferPointer, into output: UnsafeMutableRawBufferPointer) -> Bool {
        guard input.count == Self.inputSize else { return false }
        let action: QuoteAction
        switch input[0] {
        case 0:
            action = .item(LineItem(quantity: input[1], unitPrice: input[2]))
        case 1:
            action = .flatFee(input[1])
        default:
            return false
        }

        do {
            let total = try Self.quote(action)
            output.storeBytes(of: total.littleEndian, as: UInt32.self)
            output.storeBytes(of: refusedTotal.littleEndian, toByteOffset: 4, as: UInt32.self)
            refusedTotal = 0
            return true
        } catch {
            switch error {
            case .overLimit(let total):
                refusedTotal = total
            }
            return false
        }
    }
}
