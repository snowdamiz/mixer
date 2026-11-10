import MixerUI

/// Select only with the matching native adapter artifact. Selection is not proof
/// of runtime support and does not grant installation or event authority.
public enum AndroidUIProfile: String, CaseIterable, Sendable {
    case legacyHorizontal = "LEGACY_HORIZONTAL"
    case measuredMultilineV2 = "MEASURED_MULTILINE_V2"
    /// Sealed native operation/editor-cohort retirement only; never app-effect replay.
    case measuredMultilineRetirementV3 = "MEASURED_MULTILINE_RETIREMENT_V3"

    case measuredMultilineLongNotesV4 = "MEASURED_MULTILINE_LONG_NOTES_V4"

    public var textValuePolicy: UITextValuePolicy { self == .measuredMultilineLongNotesV4 ? .longNoteV1 : .standard }
    public var maximumEventBytes: Int { self == .measuredMultilineLongNotesV4 ? 1_048_576 : 131_072 }

    public var capabilities: AndroidUICapabilities {
        AndroidUICapabilities(kinds: Set(NodeKind.allCases),
            textFieldAxes: self == .legacyHorizontal ? [.horizontal] : [.horizontal, .vertical],
            appearanceV2: true)
    }

    public func prepareAppearance(snapshot: UIRenderSnapshot,
                                  configuration: UIAppearanceConfigurationV2,
                                  environment: UIAppearanceEnvironmentV2) throws -> UIResolvedAppearancePlanV2 {
        try UIAppearanceResolverV2.prepare(snapshot: snapshot, configuration: configuration,
            environment: environment, platform: .android, supportedTextFieldAxes: capabilities.textFieldAxes, textValuePolicy: textValuePolicy)
    }
}
