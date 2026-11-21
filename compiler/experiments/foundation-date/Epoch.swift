import Foundation

@_cdecl("epoch_readback")
public func epochReadback(_ index: Int32) -> Double {
    Date(timeIntervalSince1970: epochSeconds(index)).timeIntervalSinceReferenceDate
}
