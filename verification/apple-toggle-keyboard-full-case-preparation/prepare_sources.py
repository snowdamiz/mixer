#!/usr/bin/env python3
"""One-time private source composition; never called by read-only verification."""
import difflib
import hashlib
import json
import pathlib
import shutil
BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, value): p.write_text(json.dumps(value, sort_keys=True, indent=2)+'\n')
if __name__ == '__main__':
    assert not (BASE/'packet-seal.json').exists(), 'Sealed preparation is immutable'
    names = [
      'apple-toggle-pan-origin-correction/harness.py', 'apple-toggle-pan-origin-correction/apps.py',
      'apple-toggle-pan-origin-correction/bridge.py', 'apple-toggle-pan-origin-correction/oracle.py',
      'apple-toggle-pan-commit-harness-v2/commit_oracle.py', 'apple-toggle-pan-commit-harness-v2/observation_reader.py',
      'apple-toggle-pan-commit-harness-v2/cases.json', 'apple-toggle-native-interruption/interruption_oracle.py',
      'apple-toggle-native-interruption/cases.json', 'apple-toggle-semantic-activation/semantic_oracle.py',
      'apple-toggle-native-failure-analysis/packet.py', 'apple-toggle-keyboard-focus/run.py',
      'apple-toggle-keyboard-focus/keyboard_oracle.py', 'apple-toggle-keyboard-focus/keyboard_bridge.py',
      'apple-toggle-keyboard-focus/cases.json', 'apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py',
      'apple-toggle-keyboard-focus-v9-preparation/durable_settings.py', 'apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py',
      'apple-toggle-keyboard-focus-v9-preparation/replay.py']
    inputs = {}
    for name in names:
        src = ROOT/'verification'/name
        dst = BASE/'inputs/runtime/verification'/name
        dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dst)
        inputs[str(src.relative_to(ROOT))] = sha(src)
    v7 = ROOT/'verification/apple-toggle-keyboard-focus-v7-preparation/harness'
    old = ROOT/'verification/apple-toggle-keyboard-focus/harness/UITests/ToggleUITests.swift'
    for src in v7.rglob('*'):
        if src.is_file():
            dst=BASE/'harness'/src.relative_to(v7);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
            inputs[str(src.relative_to(ROOT))] = sha(src)
    src = v7/'UITests/ToggleUITests.swift'
    proven = src.read_text(); original=old.read_text(); inputs[str(old.relative_to(ROOT))]=sha(old)
    # Preserve every original application helper and method byte-for-byte.
    app_fields=original[original.index('    private var app:'):original.index('    override func setUpWithError')]
    app_bridge=original[original.index('    private func bridge('):original.index('    private func settingsObservation(')]
    app_methods=original[original.index('    private func launchCase('):original.rfind('\n}')]
    result=proven.replace('    func testSuiteDidFinish(_ testSuite: XCTestSuite) { if testSuite.name == "ToggleUITests" { SettingsTelemetry.shared.bestEffortMark("suite-finished") } }\n','').replace('    func testBundleDidFinish(_ testBundle: Bundle) { SettingsTelemetry.shared.bestEffortMark("bundle-finished") }\n','')
    result=result.replace('/// Diagnostic public Settings setup only. No application keyboard cases exist here.', '/// Proven public Settings setup followed by the six original keyboard cases.')
    result=result.replace('    private static let observer = CompletionObserver()',app_fields+'    private static let observer = CompletionObserver()')
    result=result.replace('    private func snapshot(', '    override func tearDownWithError() throws { app?.terminate(); app = nil }\n\n'+app_bridge+'    private func snapshot(',1)
    result=result.replace('    func test000PublicSettingsFullKeyboardAccess() throws {\n', '    func test000PublicSettingsFullKeyboardAccess() throws {\n        Self.settingsReady = false\n')
    old_line='            print("MIXER_SETTINGS_DIAGNOSTIC enabled observed; six application cases remain unrun")'
    new_line='''            // Emit qualification evidence only after the measured terminal capture
            // and the unchanged within-window assertion above have succeeded.
            let tree = settings.debugDescription
            guard tree.utf8.count <= 200_000 else { throw Failure.settings("Settings observation exceeded fixed bound") }
            try jsonAttachment("Public Settings setup-enabled", ["schema": "mixer.apple-toggle.keyboard-settings.1", "step": "setup-enabled",
                "uptime": now, "bundle": "com.apple.Preferences", "passed": true,
                "route": ["Accessibility", "Keyboards & Typing", "Full Keyboard Access"],
                "fullKeyboardAccessValue": terminal.state["value"]!, "terminalSnapshot": terminal.state,
                "terminalSwitchWitness": terminal.witness, "observedEnabledWithinWindow": observedEnabled, "tree": tree])
            let picture = XCTAttachment(screenshot: settings.screenshot())
            picture.name = "Public Settings setup-enabled"; picture.lifetime = .keepAlways; add(picture)
            Self.settingsReady = true
            print("MIXER_SETTINGS_SETUP measured and asserted; dependent cases await host handoff")'''
    assert old_line in result;result=result.replace(old_line,new_line)
    result=result[:result.rfind('\n}')]+ '\n'+app_methods+'\n}\n'
    (BASE/'harness/UITests/ToggleUITests.swift').write_text(result)
    (BASE/'runner-source.delta.diff').write_text(''.join(difflib.unified_diff(proven.splitlines(True),result.splitlines(True),fromfile=str(src.relative_to(ROOT)),tofile=str((BASE/'harness/UITests/ToggleUITests.swift').relative_to(ROOT)))))
    for name in ['AGENTS.md','mixer-product-plan.md']:
        dst=BASE/'inputs/contracts'/name;dst.parent.mkdir(exist_ok=True,parents=True);shutil.copyfile(ROOT/name,dst);inputs[name]=sha(ROOT/name)
    write(BASE/'source-composition.json',dict(schema=1,originalInputs=inputs,applicationHelpersAndMethodsExact=True,setupDelta='Only observer lifecycle, actual asserted setup JSON attachment, and dependent-case readiness seam; exact resolver and transport files retained',nativeCompiled=False,nativeRun=False))
