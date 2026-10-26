import Foundation
let args=Array(CommandLine.arguments.dropFirst())
let root=URL(fileURLWithPath:args.count > 1 ? args[1] : ".")
do {
    switch args[0] {
    case "verify": _ = try ProjectBuild.verifyLock(root:root)
    case "required": _ = try ProjectBuild.verifyLock(root:root,androidRequired:true)
    case "direct": _ = try AndroidProject.build(root:root)
    case "run": _ = try ProjectBuild.run(root:root,test:args[3] == "test",platform:args[2])
    case "export": _ = try ProjectBuild.export(root:root,destination:URL(fileURLWithPath:args[2]))
    case "render":
        let template=try String(contentsOf:root,encoding:.utf8)
        let value=try AndroidSDKCompatibility.renderDriver(template)
        try value.write(to:URL(fileURLWithPath:args[2]),atomically:true,encoding:.utf8)
    case "profile": FileHandle.standardOutput.write(try JSONFile.data(AndroidSDKCompatibility.profile))
    case "admit-sdk":try AndroidSDKCompatibility.admitSDK(root)
    default: fatalError("unknown review mode")
    }
    if args[0] != "profile" { print("REVIEW_ENTRYPOINT_ACCEPTED") }
} catch let failure as MixerFailure { print("REVIEW_REFUSED|\(failure.code)|\(failure.description)");exit(23) }
catch {print("REVIEW_REFUSED_OTHER|\(error)");exit(24)}
