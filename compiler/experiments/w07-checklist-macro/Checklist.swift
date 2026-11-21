@freestanding(expression)
macro checklistCount(_ mask: UInt8) -> UInt8 =
    #externalMacro(module: "MixerChecklistMacros", type: "ChecklistCountMacro")

struct Checklist {
    private var revision: UInt8 = 1
    private var count: UInt8 = 0

    mutating func accept(_ input: UnsafeRawBufferPointer) -> Bool {
        guard input.count == 2, input[0] == revision, revision < 9 else { return false }
        let mask = input[1]
        guard mask <= 7 else { return false }
        count = #checklistCount(mask)
        revision += 1
        return true
    }

    func frame(into output: UnsafeMutableRawBufferPointer) -> Int {
        var index = 0
        append(#"{"schemaVersion":1,"revision":"#, into: output, at: &index)
        output[index] = revision + 48
        index += 1
        append(#","root":{"id":"checklist","kind":"vStack","properties":{},"actions":[],"children":[{"id":"count","kind":"text","properties":{"text":""#, into: output, at: &index)
        output[index] = count + 48
        index += 1
        append(#" of 3 complete"},"children":[],"actions":[]}]}}"#, into: output, at: &index)
        return index
    }

    private func append(_ text: StaticString, into output: UnsafeMutableRawBufferPointer, at index: inout Int) {
        for offset in 0..<text.utf8CodeUnitCount {
            output[index] = text.utf8Start[offset]
            index += 1
        }
    }
}
