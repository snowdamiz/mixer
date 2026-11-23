"""Enable the historical note fixture only in this exported simulator SDK."""
from pathlib import Path
import shutil
import sys

from prepare import checked_replace as replace

HERE = Path(__file__).resolve().parent
SIM = "os(iOS) && targetEnvironment(simulator) && MIXER_F11_IOS_FIXTURE"
MAC = "os(macOS) && MIXER_PRIVATE_FIELDLOG_EDITOR"
NOTE = f"({SIM}) || ({MAC})"


def overlay(source):
    def edit(relative, *changes):
        path = source / relative
        content = path.read_text()
        for old, new in changes:
            content = replace(content, old, new)
        path.write_text(content)

    activate = "capability-activation/Sources/MixerCapabilityActivation/"
    guest = "sdk/Sources/MixerGuest/"
    updates = "updates/Sources/MixerUpdates/"
    runtime = "runtime-identity/Sources/MixerRuntimeIdentity/CapabilityRuntimeIdentity.swift"
    edit(guest + "GuestUIFieldLogNoteFixture.swift", (f"#if {MAC}", f"#if {NOTE}"))
    edit(guest + "GuestUIExchangeV1.swift",
         ("    @_spi(PrivateFieldLogEditor)\n    public init(fieldLogNoteFixtureGeneration",
          f"#endif\n#if {NOTE}\n    @_spi(PrivateFieldLogEditor)\n    public init(fieldLogNoteFixtureGeneration"),
         ("    @_spi(PrivateFieldLogEditor)\n    public func offerFieldLogEditorAction",
          f"#endif\n#if {MAC}\n    @_spi(PrivateFieldLogEditor)\n    public func offerFieldLogEditorAction"),
         (f"#if {MAC}\n        if requiresDeferredStartup", f"#if {NOTE}\n        if requiresDeferredStartup"))
    edit(updates + "FieldLogEditorDevelopment.swift", ("    public static let bundleID",
         f"""#if {SIM}
    public static let noteFixtureScope = UpdateScope(organization: "mixer-local", project: "fieldlog",
        app: "fieldlog-f11-ios", environment: "development", platform: "ios")
    public static let noteFixtureBundleID = "dev.mixer.fieldlog.f11simulator"
#else
    public static let noteFixtureScope = scope
    public static let noteFixtureBundleID = bundleID
#endif
    public static let bundleID"""))
    edit(runtime,
         ("    @_spi(PrivateFieldLogEditor)\n    public init(privateDevelopmentFieldLogNoteFixtureJSON",
          f"#endif\n#if {NOTE}\n    @_spi(PrivateFieldLogEditor)\n    public init(privateDevelopmentFieldLogNoteFixtureJSON"),
         ("        let privateMacOS = privateF10 || privateEditor != nil", f"""#if {SIM}
        let privateSimulator = privateEditor == .noteFixture
#else
        let privateSimulator = false
#endif
        let privateMacOS = privateF10 || (privateEditor != nil && !privateSimulator)"""),
         ("        if privateMacOS {\n            guard environment", """        if privateSimulator {
            guard environment == "development", os == "ios", deployment == "simulator",
                  architecture == "arm64", minimumOS == "26.0",
                  target == "arm64-apple-ios26.0-simulator" else { throw capabilityIdentityError("platform") }
        } else if privateMacOS {
            guard environment"""),
         ("            guard scope == FieldLogEditorDevelopment.scope, bundleID == FieldLogEditorDevelopment.bundleID else {",
          """            let note = privateEditor == .noteFixture
            guard scope == (note ? FieldLogEditorDevelopment.noteFixtureScope : FieldLogEditorDevelopment.scope),
                  bundleID == (note ? FieldLogEditorDevelopment.noteFixtureBundleID : FieldLogEditorDevelopment.bundleID) else {"""),
         ('privateMacOS ? ["debug"] : ["debug", "release"]', '(privateMacOS || privateSimulator) ? ["debug"] : ["debug", "release"]'))
    edit(updates + "VerifierV3.swift",
         ("    private init(host: InstalledRuntime, roots: [TrustRoot], privateF10:", f"""#if {SIM}
    @_spi(PrivateFieldLogEditor)
    public init(privateDevelopmentFieldLogNoteFixture host: InstalledRuntime, roots: [TrustRoot]) throws {{
        guard host.scope == FieldLogEditorDevelopment.noteFixtureScope else {{
            throw V3Rules.error("scope.invalid", "Expected the F11 simulator development scope")
        }}
        try self.init(host: host, roots: roots, privateF10: false, privateEditor: true)
    }}
#endif
    private init(host: InstalledRuntime, roots: [TrustRoot], privateF10:"""),
         ("        try V3Rules.scope(host.scope, privateF10: privateF10 || privateEditor)",
          """        let privateMacOS = privateF10 || (privateEditor && host.scope.platform == "macos")
        try V3Rules.scope(host.scope, privateF10: privateMacOS)"""),
         ("try V3Rules.scope(root.scope, privateF10: privateF10 || privateEditor)",
          "try V3Rules.scope(root.scope, privateF10: privateMacOS)"))
    edit(activate + "FieldLogTaskRetryStorage.swift", (f"#if {MAC}", f"#if {NOTE}"))
    edit(activate + "InstalledCapabilityExecution.swift",
         (f"#if {MAC}\n@_spi(PrivateFieldLogEditor) import MixerRuntimeIdentity",
          f"#if {NOTE}\n@_spi(PrivateFieldLogEditor) import MixerRuntimeIdentity"),
         ("    @_spi(PrivateFieldLogEditor)\n    public init(privateDevelopmentFieldLogNoteFixtureJSON",
          f"#endif\n#if {NOTE}\n    @_spi(PrivateFieldLogEditor)\n    public init(privateDevelopmentFieldLogNoteFixtureJSON"),
         (f"#if {MAC}\n        if fieldLogEditorID != nil || fieldLogNoteFixture", f"""#if {SIM}
        if fieldLogNoteFixture {{
            verifier = try ReleaseVerifierV3(privateDevelopmentFieldLogNoteFixture: identity.installedRuntime, roots: roots)
        }} else {{
            verifier = try Self.ordinaryVerifier(identity, roots, privateF10: privateF10)
        }}
#elseif {MAC}
        if fieldLogEditorID != nil || fieldLogNoteFixture"""))
    edit(activate + "CapabilityInstalledExecutionMode.swift",
         (f"#if {MAC}\n    static func requireFieldLogNoteFixture",
          f"#if {NOTE}\n    static func requireFieldLogNoteFixture"),
         ("identity.installedRuntime.scope == FieldLogEditorDevelopment.scope,\n              identity.installedRuntime.uiSchema == 1,\n              dependencies",
          "identity.installedRuntime.scope == FieldLogEditorDevelopment.noteFixtureScope,\n              identity.installedRuntime.uiSchema == 1,\n              dependencies"),
         ("    static func requireFieldLogEditor", f"#endif\n#if {MAC}\n    static func requireFieldLogEditor"))
    edit(activate + "CapabilityColdStartWorker.swift",
         (f"#if {MAC}\n@_spi(PrivateFieldLogEditor) import MixerGuest", f"#if {NOTE}\n@_spi(PrivateFieldLogEditor) import MixerGuest"),
         (f"#if {MAC}\n        if installed.fieldLogNoteFixture", f"#if {NOTE}\n        if installed.fieldLogNoteFixture"),
         ("        if installed.fieldLogEditorID != nil { return try GuestUIExchangeV1(fieldLogEditorGeneration:",
          f"#endif\n#if {MAC}\n        if installed.fieldLogEditorID != nil {{ return try GuestUIExchangeV1(fieldLogEditorGeneration:"))
    edit(activate + "CapabilityRecoveryStore.swift",
         (f"#if {MAC}\n        if installed.fieldLogNoteFixture", f"#if {NOTE}\n        if installed.fieldLogNoteFixture"),
         ("        if installed.fieldLogEditorID != nil && guestUI", f"#endif\n#if {MAC}\n        if installed.fieldLogEditorID != nil && guestUI"))
    edit(activate + "CapabilityGuestUIRuntime.swift",
         (f"#if {MAC}\n    @_spi(PrivateFieldLogEditor)", f"#if {NOTE}\n    @_spi(PrivateFieldLogEditor)"),
         (f"#if {MAC}\n        if installed.fieldLogNoteFixture", f"#if {NOTE}\n        if installed.fieldLogNoteFixture"))
    edit(activate + "CapabilityExecutionPolicy.swift",
         (f"#if {MAC}\n        if installed.fieldLogEditorID != nil || installed.fieldLogNoteFixture {{\n            let namespace = installed.fieldLogNoteFixture ? FieldLogEditorDevelopment.noteFixtureNamespace : FieldLogEditorStorage.namespace",
          f"""#if {MAC}
        let compactNamespace = installed.fieldLogEditorID == nil ? nil : FieldLogEditorStorage.namespace
#else
        let compactNamespace: String? = nil
#endif
#if {NOTE}
        if let namespace = installed.fieldLogNoteFixture ? FieldLogEditorDevelopment.noteFixtureNamespace : compactNamespace {{"""))
    presentation = source / activate / "CapabilityGuestUIPresentation.swift"
    text = presentation.read_text()
    insertion, layout, offer, acknowledge, view = (HERE / "Presentation.inc").read_text().split("\n// SECTION\n")
    text = replace(text, "    internal func actionHandler(", insertion + "\n    internal func actionHandler(")
    text = replace(text, "                model.ticket = nil", layout + "\n                model.ticket = nil")
    text = replace(text, "        guard attachment === identity, !observedNativeDisplay",
                   offer + "\n        guard attachment === identity, !observedNativeDisplay")
    text = replace(text, "        guard isCurrentNativeDisplay(value), !observedNativeDisplay",
                   acknowledge + "\n        guard isCurrentNativeDisplay(value), !observedNativeDisplay")
    text = replace(text, "        observedNativeDisplay = true\n        return true",
        f"""        observedNativeDisplay = true
#if {SIM}
        if f11UsesNoteRenderer && value.ticket.revision == 1 {{ f11NativeRevision = 1 }}
#endif
        return true""")
    presentation.write_text(text)
    apple = source / activate / "CapabilityGuestUIApple.swift"
    text = apple.read_text()
    start = text.index("                    MixerNativeView(host: host, onAction:")
    end = text.index("\n                }", start)
    original = text[start:end]
    text = text[:start] + view.rstrip() + text[end:]
    point = "\n}\n\n#if canImport(UIKit)"
    renderer = "\n    private func renderer(_ host: MixerUIHost, height: CGFloat) -> some View {\n"
    renderer += original.replace("viewport.size.height", "height") + "\n    }"
    apple.write_text(replace(text, point, renderer + point))
    shutil.copyfile(HERE / "NativeNote.swift", source / activate / "F11NativeNote.swift")


if __name__ == "__main__":
    overlay(Path(sys.argv[1]))
