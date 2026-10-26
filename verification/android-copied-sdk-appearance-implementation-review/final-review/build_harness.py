from runner import HERE,run,identity
from pathlib import Path
import shutil,json
folder=HERE/'harness-source';(folder/'Sources/ReviewDriver').mkdir(parents=True,exist_ok=True)
sources=HERE/'candidate/cli/Sources/MixerBuild'
names=['Configuration.swift','ProcessRunner.swift','VerificationFile.swift','AndroidProject.swift','AndroidSDKCompatibility.swift','ProjectGenerator.swift','AppleProject.swift']
for name in names:shutil.copyfile(sources/name,folder/'Sources/ReviewDriver'/name)
shutil.copytree(sources/'Resources',folder/'Sources/ReviewDriver/Resources',dirs_exist_ok=True)
manifest='''// swift-tools-version: 6.0
import PackageDescription
let package = Package(name:"IndependentAndroidReview",platforms:[.macOS(.v14)],dependencies:[.package(path:"../candidate/sdk")],targets:[.executableTarget(name:"ReviewDriver",dependencies:[.product(name:"MixerUI",package:"sdk")],resources:[.copy("Resources")])])
'''
(folder/'Package.swift').write_text(manifest)
main='''import Foundation
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
} catch let failure as MixerFailure { print("REVIEW_REFUSED|\\(failure.code)|\\(failure.description)");exit(23) }
catch {print("REVIEW_REFUSED_OTHER|\\(error)");exit(24)}
'''
main = 'import Foundation\n@main struct ReviewEntry { static func main() {\n' + main.removeprefix('import Foundation\n') + '\n} }\n'
(folder/'Sources/ReviewDriver/main.swift').unlink(missing_ok=True)
(folder/'Sources/ReviewDriver/ReviewEntry.swift').write_text(main)
(HERE/'harness-source-binding.json').write_text(json.dumps({str(p.relative_to(folder)):identity(p.read_bytes()) for p in folder.rglob('*') if p.is_file()},indent=2)+'\n')
for mode in ['debug','release']:
    run('independent-harness-fixed-'+mode,['/usr/bin/swift','build','--package-path',folder,'--scratch-path',HERE/'scratch/harness-build','-c',mode,'--product','ReviewDriver','-j','4'],timeout=240)
