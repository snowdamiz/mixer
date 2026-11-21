#if PROPERTY_WRAPPER_GUEST
private typealias Preview = PropertyWrapperPreview
private nonisolated(unsafe) var preview = Preview()
#elseif ASSOCIATED_TYPES_GUEST
private typealias Preview = AssociatedTypesPreview
#elseif RESULT_BUILDER_GUEST
private typealias Preview = ResultBuilderPreview
#elseif FIXED_SLOT_RESULT_BUILDER_GUEST
private typealias Preview = FixedSlotResultBuilderPreview
#elseif ENUM_TYPED_THROWS_GUEST
private typealias Preview = EnumTypedThrowsPreview
private nonisolated(unsafe) var preview = Preview()
#else
private typealias Preview = FloatingPointPreview
#endif

// The compact previews share the installed TaskCompletion adapter's header and memory bounds.
private let eventStart = 32
private let eventCapacity = 4096
private let documentStart = eventStart + eventCapacity
private nonisolated(unsafe) var memory = InlineArray<6176, UInt8>(repeating: 0)

@_cdecl("mixer_guest_ui_start_v1")
public func guestStart() -> UInt32 {
    withUnsafeMutableBytes(of: &memory) { buffer in
        let base = UInt32(UInt(bitPattern: buffer.baseAddress!))
        buffer.storeBytes(of: UInt32(827_672_909), as: UInt32.self)
        buffer.storeBytes(of: UInt32(eventStart), toByteOffset: 4, as: UInt32.self)
        buffer.storeBytes(of: base + UInt32(documentStart), toByteOffset: 8, as: UInt32.self)
        buffer.storeBytes(of: UInt32(Preview.outputSize), toByteOffset: 12, as: UInt32.self)
        buffer.storeBytes(of: base + UInt32(eventStart), toByteOffset: 16, as: UInt32.self)
        buffer.storeBytes(of: UInt32(eventCapacity), toByteOffset: 20, as: UInt32.self)
        return base
    }
}

@_cdecl("mixer_guest_ui_event_v1")
public func guestEvent(_ length: UInt32) -> UInt32 {
    guard length == UInt32(Preview.inputSize) else { return 1 }
    return withUnsafeMutableBytes(of: &memory) { buffer in
        let input = UnsafeRawBufferPointer(rebasing: buffer[eventStart ..< eventStart + Int(length)])
        let output = UnsafeMutableRawBufferPointer(
            rebasing: buffer[documentStart ..< documentStart + Preview.outputSize])
#if PROPERTY_WRAPPER_GUEST || ENUM_TYPED_THROWS_GUEST
        return preview.render(input, into: output) ? 0 : 1
#else
        return Preview.render(input, into: output) ? 0 : 1
#endif
    }
}

@_cdecl("mixer_guest_capability_ready_v1")
public func guestReady() {}
