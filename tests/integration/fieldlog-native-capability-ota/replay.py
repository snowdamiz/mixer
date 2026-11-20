#!/usr/bin/env python3
"""Replay the FieldLog native capability refusal with the maintained calculation host."""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
CALCULATION = HERE.parent / "fieldlog-task-calculation"
SPEC = importlib.util.spec_from_file_location("calculation_replay", CALCULATION / "replay.py")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)

REVISION = "71e6ffa51e857d5a1eda3f74c26941996ed275de"
TREE = "94cde08bd37868e84e4d623e059926a77e86fbbc"
base.MIXER = {"commit": REVISION, "tree": TREE}
base.PINS["archivesSHA256"]["mixer-source"] = "02866d7be8f615dcb3ad768b779007ae85f4857513760a1e9faf70d42fafe430"


class NativeCapabilityReplay(base.Replay):
    def __init__(self, run):
        super().__init__(run)
        self.report["requirement"] = "22.2.12"
        for path in (HERE / "replay.py", HERE / "Scenario.swift"):
            self.report["inputs"]["native-capability/" + path.name] = base.sha(path)

    def patch(self, name, directory):
        super().patch(name, directory)
        if name != "row-host-completion-preview":
            return
        fixture = directory / "RowFixture.swift"
        self.replace(fixture, "    let signed: SignedPair?", "    let signed: SignedPair?\n    let signingKey: Curve25519.Signing.PrivateKey?")
        self.replace(fixture, "        if let key, let archiveSHA256 {", "        signingKey = key\n        if let key, let archiveSHA256 {")
        self.replace(fixture, "        let files = try Self.materials.map", '''        let files = try Self.materials.filter { !$0.0.hasPrefix("http") }.map''')
        self.replace(fixture, '        identity["capabilities"] = capabilities',
                     '        identity["capabilities"] = capabilities.filter { $0["id"] as? String == CapabilitySchemas.storageID }')
        self.replace(fixture, "    private static func sign(", "    static func sign(")

        loopback = directory / "FieldLogReleaseV3Loopback.swift"
        self.replace(loopback, "name: String, actor: String) throws", "name: String, actor: String, additionalHosts: [InstalledRuntime] = []) throws")
        self.replace(loopback, "try FieldLogReleaseV3Fixture.object(FieldLogReleaseV3Fixture.encoder.encode(host))",
                     '''try ([host] + additionalHosts).map {
            try FieldLogReleaseV3Fixture.object(FieldLogReleaseV3Fixture.encoder.encode($0))
        }''')
        self.replace(loopback, '"hosts": [hostObject]', '"hosts": hostObject')
        self.replace(loopback, "func updates(installation: String, status: Int = 200)",
                     "func updates(installation: String, status: Int = 200, runtime: String? = nil)")
        self.replace(loopback, r"\(host.runtime)", r"\(runtime ?? host.runtime)")

        # Appending in the disposable package keeps access to the existing display,
        # storage, and owner-retirement assertions without changing them.
        completion = directory / "CompletionTests.swift"
        self.replace(completion, 'if stage != "offline" {', 'if stage != "offline" && stage != "retained" {')
        with completion.open("a") as stream:
            stream.write("\n" + (HERE / "Scenario.swift").read_text())

    def run(self, name, *args, **kwargs):
        if name in ("online-test", "offline-test"):
            args = (*args[:-1], args[-1] + "NativeCapability")
        return super().run(name, *args, **kwargs)


if __name__ == "__main__":
    base.Replay = NativeCapabilityReplay
    base.main()
