import AppFeatures
import Foundation
import MixerUI
@_spi(ComposeHost) import MixerAndroid

@main struct BundledFrame {
    enum Failure: Error { case arguments, inputRequiresLiveOwner, missingIdentity }

    static func main() throws {
        guard CommandLine.arguments.count == 2 else { throw Failure.arguments }
        let output = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
        let validator = UIValidator()
        var reconciler = UIReconciler(validator: validator)
        try reconciler.apply(ProjectFeature.document(entries: [], revision: 1))
        let presentation = AndroidComposePresentation<Void>(validator: validator, isOnExecutor: { Thread.isMainThread })
        let frame = try presentation.prepare(owner: presentation.owner, snapshot: reconciler.currentSnapshot()) { _, _ in
            throw Failure.inputRequiresLiveOwner
        }
        var generations = Data()
        func appendGenerations(_ node: UINode) throws {
            guard node.actions.isEmpty, ![.textField, .toggle, .button].contains(node.kind) else {
                throw Failure.inputRequiresLiveOwner
            }
            guard let identity = frame.snapshot.identity(for: node.id) else { throw Failure.missingIdentity }
            var bits = identity.generation.bigEndian
            withUnsafeBytes(of: &bits) { generations.append(contentsOf: $0) }
            for child in node.children { try appendGenerations(child) }
        }
        try appendGenerations(frame.snapshot.document.root)
        try frame.documentUTF8.write(to: output.appendingPathComponent("bundled-document.json"), options: .withoutOverwriting)
        try generations.write(to: output.appendingPathComponent("bundled-generations.bin"), options: .withoutOverwriting)
    }
}
