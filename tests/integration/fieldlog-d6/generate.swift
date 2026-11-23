import Foundation
import MixerBuild

let root = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
_ = try AppleProject.generate(root: root)
_ = try AppleProject.generate(root: root)
