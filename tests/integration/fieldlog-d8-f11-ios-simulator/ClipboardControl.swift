import CryptoKit
import Foundation
import UniformTypeIdentifiers

@main
struct ClipboardControl {
    @MainActor static func main() async throws {
        let seed = URL(fileURLWithPath: CommandLine.arguments[1])
        let workspace = try JSONSerialization.jsonObject(with: Data(contentsOf: seed)) as! [String: Any]
        let drafts = workspace["drafts"] as! [[String: Any]]
        let draft = drafts.first { ($0["id"] as? String)?.lowercased() == "f1100000-0000-4000-8000-000000000001" }!
        let note = draft["note"] as! String
        let expected = Data("Edited".utf8)
        for bytes in [expected, Data("Edited\u{0000}".utf8), Data([0xff])] {
            let data = await providerRoundTrip(bytes)
            precondition(data == bytes)
            precondition(data?.elementsEqual(expected) == (bytes == expected))
        }
        let end = (note as NSString).length
        precondition(end == note.utf16.count && end != note.utf8.count)
        let edited = (note as NSString).replacingCharacters(in: NSRange(location: end, length: 0), with: "Edited")
        let result = Data(edited.utf8)
        precondition(result.elementsEqual(note.utf8 + expected))
        precondition(result.filter { $0 == 10 }.count == 4)
        print("provider acceptance 1/3; end UTF-16 offset \(end); LF count 4; \(SHA256.hash(data: result))")
    }

    private static func providerRoundTrip(_ bytes: Data) async -> Data? {
        let provider = NSItemProvider()
        let type = UTType.utf8PlainText.identifier
        provider.registerDataRepresentation(forTypeIdentifier: type, visibility: .all) { completion in
            completion(bytes, nil)
            return nil
        }
        precondition(provider.hasItemConformingToTypeIdentifier(type))
        return await withCheckedContinuation { continuation in
            _ = provider.loadDataRepresentation(forTypeIdentifier: type) { data, error in
                precondition(error == nil)
                continuation.resume(returning: data)
            }
        }
    }
}
