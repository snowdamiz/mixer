@_cdecl("epoch_input_control")
public func epochInputControl(_ index: Int32) -> Double {
    epochSeconds(index)
}

@_cdecl("presentation_input_control")
public func presentationInputControl(_ index: Int32, _ field: Int32) -> Double {
    let input = presentationCase(index)
    switch field {
    case 0: return input.seconds
    case 1: return Double(input.locale)
    case 2: return Double(input.offset)
    default: preconditionFailure()
    }
}
