"""Add network ingress to the reviewed native F11 witness in an owned export."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent


def compose(stage, work):
    native = stage / "tests/integration/fieldlog-d8-f11-ios-simulator"
    receipt = json.loads((stage / "verification/receipts/l08-d8-f11-ios-note-native-20261123.json").read_bytes())
    for name, expected in receipt["fixtureSourceSHA256"].items():
        assert hashlib.sha256((native / name).read_bytes()).hexdigest() == expected, name
    sys.path.insert(0, str(native))
    replace = runpy.run_path(str(native / "prepare.py"))["checked_replace"]
    source = work / "export/source"
    runpy.run_path(str(native / "overlay.py"))["overlay"](source)
    recipe = runpy.run_path(str(native / "build.py"))["setup"](work)

    def edit(path, *changes):
        original = path.read_text()
        for old, new in changes:
            original = replace(original, old, new)
        path.write_text(original)

    file = source / "capability-activation/Sources/MixerCapabilityActivation/CapabilityRecoverySelection.swift"
    edit(file, ("import Foundation", "import Foundation\nimport MixerUpdates"),
         ("    private let key: CapabilityRecoverySelectionKey\n    private var input:",
          """#if os(iOS) && targetEnvironment(simulator) && MIXER_F11_IOS_FIXTURE
    let f11Prior: Bool
#endif
    private let key: CapabilityRecoverySelectionKey
    private var input:"""),
         ("        self.key = key; self.input = input",
          f"""        self.key = key; self.input = input
#if os(iOS) && targetEnvironment(simulator) && MIXER_F11_IOS_FIXTURE
        f11Prior = ReleaseVerifier.sha256(input.module) == "{hashlib.sha256((work / 'export/guest/prior.wasm').read_bytes()).hexdigest()}"
#endif"""))
    file = file.with_name("CapabilityColdStartWorker.swift")
    edit(file, ("let exchange = try makeExchange(generation: selection.generation, installed: installed)",
        """let exchange: (any CapabilityAttemptUI)?
#if os(iOS) && targetEnvironment(simulator) && MIXER_F11_IOS_FIXTURE
        if installed.fieldLogNoteFixture && selection.f11Prior && presentation != nil {
            exchange = try GuestUIExchangeV1(generation: selection.generation, allowsDeferredStartup: true)
        } else {
            exchange = try makeExchange(generation: selection.generation, installed: installed)
        }
#else
        exchange = try makeExchange(generation: selection.generation, installed: installed)
#endif"""))

    file = recipe / "WitnessInput.swift"
    edit(file, ("    func open() async throws", """    func open(phase: String, port: UInt16?) async throws"""),
         ("""        try FileManager.default.createDirectory(at: .applicationSupportDirectory, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        try FileManager.default.createDirectory(at: workspace, withIntermediateDirectories: false)
        try seed.write(to: workspace.appendingPathComponent("workspace.json"), options: .withoutOverwriting)""",
          """        if phase == "prior" {
            try FileManager.default.createDirectory(at: .applicationSupportDirectory, withIntermediateDirectories: true)
            try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
            try FileManager.default.createDirectory(at: workspace, withIntermediateDirectories: false)
            try seed.write(to: workspace.appendingPathComponent("workspace.json"), options: .withoutOverwriting)
        } else if phase == "successor" {
            try check(read(workspace, "workspace.json") == seed, "Prior changed the seed")
        } else {
            _ = try await coldCommit()
        }"""),
         ("""            let wasm = try read(packet, "payload.wasm")
            try check(ReleaseVerifier.sha256(wasm) == Self.wasmHash, "Wasm bytes")
            try await owner.beginDownload(signedManifest: read(packet, "signed-manifest.json"),
                                          signedAssignment: read(packet, "assignment.json"))
            try await owner.appendDownload(wasm, atOffset: 0)
            try await owner.finishDownload()
            let staged = await owner.recoverySnapshot()
            let started = try await owner.start()
            try check(started.launchID != nil && started.candidateID == staged.staged, "Signed candidate launch")""",
          """            let phases = try JSONDecoder().decode([String: WitnessDelivery].self, from: read(packet, "delivery.json"))
            let delivery = try need(phases[phase == "offline" ? "rollback" : phase], "Unknown delivery phase")
            if phase == "successor" {
                try check(delivery.payloadSHA256 == Self.wasmHash, "Exact historical successor")
            }
            if phase == "offline" {
                try check(port == nil, "Offline launch must not have a delivery port")
            } else {
                try await delivery.stage(owner, descriptor: descriptor, port: need(port, "Missing loopback origin"))
            }
            let staged = await owner.recoverySnapshot()
            let candidate = try need(phase == "offline" ? staged.healthy : staged.staged, "Staged or retained candidate")
            let started = try await owner.start()
            try check(started.launchID != nil && started.candidateID == candidate
                && started.phase == .provisionalGuest && started.acceptedSequence == delivery.sequence,
                "Signed candidate or sequence differed")"""))
    with file.open("a") as stream:
        stream.write((HERE / "OnlineInput.inc").read_text())
        stream.write((HERE / "Observations.inc").read_text())

    file = recipe / "WitnessApp.swift"
    edit(file, ('            Text(session.status).accessibilityIdentifier("f11.status")\n            Button',
          '''            Text(session.status).accessibilityIdentifier("f11.status")
            if session.phase != "successor" {
                Button("Close read-only release") { Task { await session.closeReadOnly() } }
                    .accessibilityIdentifier("f11.close")
                    .disabled(!session.status.hasPrefix("Healthy "))
            }
            Button'''),
         ('    private var busy = false', '''    private var busy = false
    private(set) var phase = ""'''),
         ('            let (owner, repository, storage) = try await input.open()',
          '''            phase = try need(args.first(where: { ["prior", "successor", "rollback", "offline"].contains($0) }),
                             "Missing release phase")
            let port = args.first(where: { $0.hasPrefix("--origin=") })
                .flatMap { UInt16($0.dropFirst("--origin=".count)) }
            let (owner, repository, storage) = try await input.open(phase: phase, port: port)'''),
         ('            status = "Ready"\n        } catch { status = "Failed: \\(error)" }',
          '''            try await input.recordHealthy(owner, phase: phase)
            status = "Healthy " + phase
        } catch {
            await owner?.close()
            await repository?.close()
            owner = nil
            repository = nil
            status = "Failed: \\(error)"
        }'''),
         ('!busy && revision == action.expectedRevision && owner != nil',
          '''phase == "successor" && status != "Restoring" && !busy
            && revision == action.expectedRevision && owner != nil'''),
         ('    func perform(_ action:', (HERE / "Close.inc").read_text() + '\n    func perform(_ action:'))

    file = recipe / "WitnessUITests.swift"
    edit(file, ('import XCTest', 'import XCTest\nimport os'),
         ('        app.launchArguments = [run]\n        app.launch()', '''        let control = try XCTUnwrap(ProcessInfo.processInfo.environment["F11_CONTROL_PORT"].flatMap(UInt16.init))
        try open("prior", app: app, run: run, control: control)
        closeReadOnly(app, phase: "prior")
        try open("successor", app: app, run: run, control: control)'''),
         ('        waitForLabel("Cold commit " + hash, on: status)\n    }',
          '''        waitForLabel("Cold commit " + hash, on: status)
        app.terminate()

        try open("rollback", app: app, run: run, control: control)
        closeReadOnly(app, phase: "rollback")
        _ = try advance("offline", control: control)
        app.launchArguments = [run, "offline"]
        app.launch()
        waitForLabel("Healthy offline", on: status)
        closeReadOnly(app, phase: "offline")
    }''' + (HERE / "TestDelivery.inc").read_text()))

    project = recipe / "F11NativeWitness.xcodeproj/project.pbxproj"
    edit(project, ("INFOPLIST_KEY_UILaunchScreen_Generation = YES;",
                   'INFOPLIST_KEY_UILaunchScreen_Generation = YES; INFOPLIST_FILE = Loopback.plist;'))
    (recipe / "Loopback.plist").write_text('''<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict><key>NSAppTransportSecurity</key><dict>
<key>NSAllowsLocalNetworking</key><true/>
</dict></dict></plist>
''')
    return recipe


if __name__ == "__main__":
    compose(*map(Path, sys.argv[1:]))
