import Foundation

let arguments = Array(CommandLine.arguments.dropFirst())
do {
    switch arguments.first {
    case "sign" where arguments.count == 9, "sign-tools" where arguments.count == 9,
         "sign-authority" where arguments.count == 9:
        try AppleCommitMaterial.sign(
            fixtures: URL(fileURLWithPath: arguments[1]), guest: URL(fileURLWithPath: arguments[2]),
            output: URL(fileURLWithPath: arguments[3]), engineHash: arguments[4], sourceHash: arguments[5],
            linkHash: arguments[6], revision: arguments[7], metadata: URL(fileURLWithPath: arguments[8]),
            draftTools: arguments[0] == "sign-tools",
            authorityControl: arguments[0] == "sign-authority")
    case "run" where (3...5).contains(arguments.count):
        try await AppleEditorReplay.run(material: URL(fileURLWithPath: arguments[1]),
                                        root: URL(fileURLWithPath: arguments[2]),
                                        scenarioName: arguments.count >= 4 ? arguments[3] : nil,
                                        draftTools: arguments.count == 5 ? URL(fileURLWithPath: arguments[4]) : nil)
    default:
        print("Usage: Replay {sign|sign-tools|sign-authority} FIXTURES {WASM|DRAFT_TOOLS_WASM_DIR} OUTPUT ENGINE_SHA256 SOURCE_SHA256 LINK_SHA256 MIXER_REVISION METADATA_JSON | run MATERIAL ROOT [CASE|all [DRAFT_TOOLS_MATERIAL]]")
        exit(2)
    }
} catch {
    FileHandle.standardError.write(Data("\(error)\n".utf8))
    exit(1)
}
