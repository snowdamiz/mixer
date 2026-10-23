// Original linker-model probe. This is not FieldLog or language qualification.
@_cdecl("mixer_linker_probe_add")
public func mixerLinkerProbeAdd(_ lhs: Int32, _ rhs: Int32) -> Int32 {
    lhs &+ rhs
}
