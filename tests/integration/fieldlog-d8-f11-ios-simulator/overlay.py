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
    event_result = "        if let result = claim.eventResult { model.pendingInput = nil; model.lastEventResult = result }"
    text = replace(text, event_result, event_result + rf"""
#if {SIM}
        if model.f11UsesNoteRenderer, let result = claim.eventResult {{
            let outcome = result.outcome == .delivered ? "delivered" : "terminal"
            F11NativeNote.log.notice("event=\(outcome, privacy: .public)")
        }}
#endif""")
    current_start = text.index("    internal func isCurrentNativeDisplay(")
    current_body = text.index("        guard value.binding", current_start)
    current_end = text.index("\n    }", current_body)
    text = (text[:current_body] + f"#if {SIM}\n"
            + "        return f11CurrentDisplayRefusal(value) == nil\n#else\n"
            + text[current_body:current_end] + "\n#endif" + text[current_end:])
    text = replace(text, "        guard exchange.observePresentation(value.ticket) else { return false }",
                   f"""#if {SIM}
        let accepted = exchange.observePresentation(value.ticket)
        f11Trace.observation = accepted ? "accepted" : "exchange-refused"
        f11Trace.transition("observe-presentation")
        guard accepted else {{ return false }}
#else
        guard exchange.observePresentation(value.ticket) else {{ return false }}
#endif""")
    decision = "        guard isCurrentNativeDisplay(value), !observedNativeDisplay, let exchange else { return false }"
    text = replace(text, decision, f"""#if {SIM}
        if let refusal = f11CurrentDisplayRefusal(value) {{
            f11Trace.observation = refusal
            f11Trace.transition("observe-refused")
            return false
        }}
        guard !observedNativeDisplay, let exchange else {{
            f11Trace.observation = observedNativeDisplay ? "already-observed" : "no-exchange"
            f11Trace.transition("observe-refused")
            return false
        }}
#else
{decision}
#endif""")
    text = replace(text, "        model.refreshInput()\n        model.attachmentObserver?.presentationChanged()",
                   f"""        model.refreshInput()
#if {SIM}
        model.f11Trace.transition("readiness-changed")
#endif
        model.attachmentObserver?.presentationChanged()""")
    text = replace(text, "            model.refreshInput()\n            model.attachmentObserver?.presentationChanged()",
                   f"""            model.refreshInput()
#if {SIM}
            model.f11Trace.transition(claim.frame == nil ? "claim-without-frame" : "claim-frame")
#endif
            model.attachmentObserver?.presentationChanged()""")
    presentation.write_text(text)
    apple = source / activate / "CapabilityGuestUIApple.swift"
    text = apple.read_text()
    text = replace(text, "import QuartzCore", f"import QuartzCore\n#if {SIM}\n@_spi(GuestUIV1) import MixerGuest\n#endif")
    start = text.index("                    MixerNativeView(host: host, onAction:")
    end = text.index("\n                }", start)
    original = text[start:end]
    text = text[:start] + view.rstrip() + text[end:]
    point = "\n}\n\n#if canImport(UIKit)"
    renderer = "\n    private func renderer(_ host: MixerUIHost, height: CGFloat) -> some View {\n"
    renderer += original.replace("viewport.size.height", "height") + "\n    }"
    text = replace(text, point, renderer + point)
    probe = text.index("@MainActor\nprivate final class CapabilityGuestUIIOSProbe")
    probe_end = text.index("#elseif canImport(AppKit)", probe)
    text = (text[:probe] + f"#if {SIM}\n" + (HERE / "Probe.inc").read_text()
            + "#else\n" + text[probe:probe_end] + "#endif\n" + text[probe_end:])
    for old, new in [
        ("override func didMoveToWindow() { super.didMoveToWindow(); owner?.attachmentChanged() }",
         f"""override func didMoveToWindow() {{
        super.didMoveToWindow()
#if {SIM}
        owner?.trace(window == nil ? "window-detached" : "window-attached")
#endif
        owner?.attachmentChanged()
    }}"""),
        ("    @objc private func sceneChanged(_ notification: Notification) {",
         f"""#if {SIM}
    func trace(_ event: String) {{ presentation?.f11Trace.transition(event) }}
#endif
    @objc private func sceneChanged(_ notification: Notification) {{"""),
        ("              scene === view.window?.windowScene else { return }\n        attachmentChanged()",
         f"""              scene === view.window?.windowScene else {{ return }}
#if {SIM}
        trace(notification.name == UIScene.didActivateNotification ? "scene-activated" : "scene-deactivating")
#endif
        attachmentChanged()"""),
    ]:
        text = replace(text, old, new)
    apple.write_text(text)
    shutil.copyfile(HERE / "DisplayAdmission.swift", source / activate / "F11DisplayAdmission.swift")
    shutil.copyfile(HERE / "NativeNote.swift", source / activate / "F11NativeNote.swift")


if __name__ == "__main__":
    overlay(Path(sys.argv[1]))
