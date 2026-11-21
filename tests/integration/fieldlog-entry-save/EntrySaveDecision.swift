public enum EntrySaveDecision {
    case eligible, wrongProject, titleTooLong, titleRequired, titleNUL, noteTooLong, noteNUL, invalidDate

    public struct Facts: Sendable {
        public let counts: UInt64
        public let flags: UInt8

        public init(projectMatches: Bool, commit: Bool, titleBytes: UInt32, titleBlank: Bool,
                    titleHasNUL: Bool, noteBytes: UInt32, noteHasNUL: Bool, dateIsFinite: Bool) {
            counts = (UInt64(titleBytes) << 32) | UInt64(noteBytes)
            flags = (projectMatches ? 1 : 0) | (commit ? 2 : 0) | (titleBlank ? 4 : 0)
                | (titleHasNUL ? 8 : 0) | (noteHasNUL ? 16 : 0) | (dateIsFinite ? 32 : 0)
        }

        public init?(commitCounts counts: UInt64, flags: UInt8) {
            guard flags & 0xc2 == 2 else { return nil }
            self.counts = counts
            self.flags = flags
            guard titleBytes != 0 || (titleBlank && !titleHasNUL),
                  !titleBlank || !titleHasNUL, noteBytes != 0 || !noteHasNUL else { return nil }
        }

        private var titleBytes: UInt32 { UInt32(counts >> 32) }
        private var noteBytes: UInt32 { UInt32(truncatingIfNeeded: counts) }
        private var titleBlank: Bool { flags & 4 != 0 }
        private var titleHasNUL: Bool { flags & 8 != 0 }
        private var noteHasNUL: Bool { flags & 16 != 0 }

        public var decision: EntrySaveDecision {
            guard flags & 1 != 0 else { return .wrongProject }
            guard titleBytes <= 160 else { return .titleTooLong }
            guard flags & 2 == 0 || !titleBlank else { return .titleRequired }
            guard !titleHasNUL else { return .titleNUL }
            guard noteBytes <= 100_000 else { return .noteTooLong }
            guard !noteHasNUL else { return .noteNUL }
            guard flags & 32 != 0 else { return .invalidDate }
            return .eligible
        }
    }

    public var message: StaticString {
        switch self {
        case .eligible: "Entry is eligible to save."
        case .wrongProject: "This record is no longer available. Your changes have not been discarded."
        case .titleTooLong: "Entry title is too long (maximum 160 UTF-8 bytes)."
        case .titleRequired: "Entry title can't be empty."
        case .titleNUL: "Entry title contains an unsupported character."
        case .noteTooLong: "Note is too long (maximum 100000 UTF-8 bytes)."
        case .noteNUL: "Note contains an unsupported character."
        case .invalidDate: "Choose a valid entry date."
        }
    }
}
