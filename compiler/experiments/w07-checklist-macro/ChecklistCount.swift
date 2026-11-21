@inline(never)
func boundedChecklistCount(_ mask: UInt8) -> UInt8 {
    (mask & 1) &+ ((mask >> 1) & 1) &+ ((mask >> 2) & 1)
}
