#if os(WASI) && !ICU_CONTROL
import FoundationEssentials
#else
import Foundation
#endif

@main
enum Command {
    @MainActor
    static func main() async throws {
        let journey = Journey()
        await journey.load()
        journey.openRecord()
        journey.tryBlankSave()
        journey.saveEdit()
        try journey.reopen()
        #if ICU_CONTROL
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "fr_FR")
        formatter.dateStyle = .long
        precondition(!formatter.string(from: Date(timeIntervalSince1970: journey.result.created)).isEmpty)
        #endif
        let encoder = JSONEncoder()
        encoder.outputFormatting = .sortedKeys
        print(String(decoding: try encoder.encode(journey.result), as: UTF8.self))
    }
}
