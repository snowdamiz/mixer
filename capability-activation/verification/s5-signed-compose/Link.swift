import Foundation
import MixerAndroid
import MixerCapabilityActivation
@_spi(GuestUIV2) import MixerGuest
import MixerUI
import MixerUpdates

// Keep the same dependency graph as the signed editor in the Android image.
public func linkSignedEditor(
    _ document: UIDocument, configuration: CapabilityColdStartConfiguration,
    execution: InstalledCapabilityExecution, installed: InstalledRuntime, roots: [TrustRoot]
) async throws -> Data {
    _ = try ReleaseVerifierV3(host: installed, roots: roots)
    let owner = try await CapabilityColdStartRuntime.open(configuration: configuration, execution: execution)
    await owner.close()
    _ = AndroidComposePresentationV1<String>()
    return try GuestUIDocumentCodecV2(textValuePolicy: .standard).encode(document)
}
