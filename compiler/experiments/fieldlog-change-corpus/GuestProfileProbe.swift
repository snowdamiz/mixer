import Foundation
import FieldLogFeatures
import MixerUI
#if CHECK_GUEST_V1
@_spi(GuestUIV1) import MixerGuest
#endif

@main struct GuestProfileProbe {
    @MainActor static func main() throws {
        let input = URL(fileURLWithPath: CommandLine.arguments[1])
        let form = try TaskEditorPresentation { _, _ in .failed("Probe must not save") }
        let document = form.snapshot.render.document
        #if CHECK_GUEST_V1
        let codec = UIValidator(supportedTextFieldAxes: [.horizontal, .vertical])
        let frame = try codec.encode(document)
        let historical = try Data(contentsOf: input)
        let priorDocument = try codec.decode(historical).document
        precondition(priorDocument.root.id == "task.screen" && priorDocument.root.kind == .navigation)
        try requireLegacyRejection(historical, row: "F05")
        try requireLegacyRejection(frame, row: "F06")

        do {
            _ = try UIValidator().validate(document)
            fatalError("F06: default validator unexpectedly accepted the vertical field")
        } catch UIValidationError.unsupportedTextFieldAxis(.vertical) {
            print("F06 UIValidator.unsupportedTextFieldAxis(.vertical) at task.title")
        }
        let positive = try codec.encode(MixerUI.VStack("probe.stack") {
            MixerUI.Text("probe.text", "Guest UI V1 control")
        }.document(revision: 1))
        let exchange = try GuestUIExchangeV1(generation: 1)
        try exchange.finishTurn(exchange.claimStartup(), documentBytes: positive)
        let snapshot = exchange.snapshot()
        precondition(snapshot.latestRevision == 1 && snapshot.firstUIProtocolFailure == nil)
        print("Guest UI V1 control: accepted revision 1")
        #else
        let frame = try UIValidator().encode(document)
        try frame.write(to: input, options: .withoutOverwriting)
        print("F05 frame emitted by the original FieldLog TaskEditorPresentation")
        #endif

        try form.close()
    }

    #if CHECK_GUEST_V1
    private static func requireLegacyRejection(_ frame: Data, row: String) throws {
        let exchange = try GuestUIExchangeV1(generation: 1)
        do {
            try exchange.finishTurn(exchange.claimStartup(), documentBytes: frame)
            fatalError("\(row): Guest UI V1 unexpectedly accepted the real editor frame")
        } catch let error as GuestUIProtocolFailureV1 {
            precondition(error.phase == .startup && error.code == .document)
            let snapshot = exchange.snapshot()
            precondition(snapshot.firstUIProtocolFailure?.effectStage == .beforeIntent)
            precondition(snapshot.latestRevision == nil && !snapshot.effectsMayHaveOpened)
            print("\(row) GuestUIExchangeV1: startup/document, beforeIntent, no admitted revision")
        }
    }
    #endif
}
