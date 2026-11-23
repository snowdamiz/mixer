@main
struct DisplayAdmissionControl {
    static func main() {
        let stamp = F11DisplayStamp(generation: 7, serial: 9, revision: 1)
        let edited = F11DisplayStamp(generation: 7, serial: 10, revision: 2)
        func check(_ expected: String?, binding: Bool = true, attachment: Bool = true,
                   current: F11DisplayStamp? = stamp, offered: F11DisplayStamp = stamp,
                   exchange: Bool = true, stopped: Bool = false, effects: Bool = true,
                   generation: UInt64? = 7, displayed: UInt64? = 1) {
            let result = F11DisplayAdmission(bindingMatches: binding, attachmentMatches: attachment,
                current: current, offered: offered, exchangeExists: exchange, stopped: stopped,
                effectsConfirmed: effects, exchangeGeneration: generation, displayedRevision: displayed)
            precondition(result.refusal == expected, "Unexpected display admission: \(String(describing: result.refusal))")
        }
        check("binding-mismatch", binding: false, attachment: false)
        check("attachment-mismatch", attachment: false)
        check("no-current-ticket", current: nil)
        check("no-exchange", exchange: false)
        check("ticket-generation", offered: .init(generation: 8, serial: 9, revision: 1))
        check("frame-serial", current: edited, displayed: 2)
        check("ticket-revision", offered: .init(generation: 7, serial: 9, revision: 2))
        check("exchange-stopped", stopped: true, effects: false)
        check("effects-unconfirmed", effects: false)
        check("exchange-generation", generation: 8)
        check("displayed-revision", displayed: nil)
        check("displayed-revision", displayed: 2)
        check(nil)
        check(nil, current: edited, offered: edited, displayed: 2)
        print("14 display admission cases passed (invalid, stale, current revision 1 and revision 2)")
    }
}
