struct F11DisplayStamp: Equatable {
    let generation: UInt64
    let serial: UInt64
    let revision: UInt64
}

// Shared by the simulator's current-ticket check and the host admission control.
struct F11DisplayAdmission {
    let bindingMatches: Bool
    let attachmentMatches: Bool
    let current: F11DisplayStamp?
    let offered: F11DisplayStamp
    let exchangeExists: Bool
    let stopped: Bool
    let effectsConfirmed: Bool
    let exchangeGeneration: UInt64?
    let displayedRevision: UInt64?

    var refusal: String? {
        guard bindingMatches else { return "binding-mismatch" }
        guard attachmentMatches else { return "attachment-mismatch" }
        guard let current else { return "no-current-ticket" }
        guard exchangeExists else { return "no-exchange" }
        guard current.generation == offered.generation else { return "ticket-generation" }
        guard current.serial == offered.serial else { return "frame-serial" }
        guard current.revision == offered.revision else { return "ticket-revision" }
        guard !stopped else { return "exchange-stopped" }
        guard effectsConfirmed else { return "effects-unconfirmed" }
        guard exchangeGeneration == current.generation else { return "exchange-generation" }
        guard displayedRevision == current.revision else { return "displayed-revision" }
        return nil
    }
}
