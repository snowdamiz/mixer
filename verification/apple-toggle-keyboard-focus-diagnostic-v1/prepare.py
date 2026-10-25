#!/usr/bin/env python3
"""Generate a compact patch from digest-bound sources; never import them."""
import argparse
import difflib
import hashlib
import json
import pathlib

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
V3 = 'verification/apple-toggle-keyboard-full-case-preparation-v3/'
V9 = 'verification/apple-toggle-keyboard-focus-v9-preparation/'
INPUTS = {
    V9 + 'source/Prototype/DiagnosticTrace.swift': '57fe781c74a17a75ad522e7262ce65434ba90973f74f6ac4be57da38433b7bc0',
    V9 + 'source/Prototype/main.swift': '1abf36ab5430793ef1300a779d489d185ee81a69d906e3f4b81c14e0b0138b93',
    V9 + 'source/Prototype/AuthoredToggleCarrier.swift': '7849c633f69b314205ba0b293514ae45ba7b93f083b8e99c0913ea9541a27815',
    V3 + 'harness/UITests/ToggleUITests.swift': '6da53dd1f1a0e5b62a60532e4ced62e1b25f5609ed5581aec1d43c2856326a93',
    V3 + 'inputs/runtime/verification/apple-toggle-keyboard-focus/keyboard_bridge.py': 'dadede5c6a74ff3aeefbfe598708fe2071c93fc4b6fd924bfe2e1d86e278870a',
    V3 + 'inputs/runtime/verification/apple-toggle-keyboard-focus/keyboard_oracle.py': '24419f56c21e48b1788af8944acb2427bb7e03cf6b81a7d6d5dd4ba290f63e49',
    V3 + 'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py': 'feefd59c5796966f68fd9b342f9eae396779cccea4ee74031f6623f203318582',
    V3 + 'runtime/captures/0001-keyboard-witness-1.json': '6fe7c0f5959465b4241c449d6a448b43530f483203044cf57efd394a714a44e2',
    V3 + 'runtime/captures/0001-after-1.json': '4ff8bf462828d9c715a6cc5942645f29399fdc9176facbc11ba7a88a88307efc',
    'docs/apple-toggle-keyboard-v3-failure-analysis.md': 'adc69876c117248e9ed1acc8c41b1db5d420ad04c991c5b1a9cd2c4a7266acee',
    'verification/apple-toggle-keyboard-full-case-root-review/v3-failure-analysis/acceptance.json': 'c3cfb73ec206a265706d534303842aeb4c326e846e64c82b66e46ad79e21c6c5',
}
EXECUTION_SEAL = '7baff6c525359b0647caa2808d0fa73b7d1e8cc54146408d904570eabd80e3b7'
INHERITED_REVIEW_REVISION = 'ba9ad4372f94463ba4d363cdfd76dd565c96413f'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stable_json(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def verified_inputs():
    values = {}
    for name, expected in INPUTS.items():
        path = ROOT / name
        if path.is_symlink() or not path.is_file() or path.resolve() != path:
            raise ValueError('Noncanonical source: ' + name)
        data = path.read_bytes()
        if sha(data) != expected:
            raise ValueError('Immutable source changed: ' + name)
        values[name] = data
    return values


def once(value, old, new):
    if value.count(old) != 1:
        raise ValueError('Expected one exact patch anchor: ' + old[:100])
    return value.replace(old, new, 1)


def render(inputs=None):
    inputs = verified_inputs() if inputs is None else inputs
    original = {}
    for name in ('DiagnosticTrace.swift', 'main.swift', 'AuthoredToggleCarrier.swift'):
        original['source/Prototype/' + name] = inputs[V9 + 'source/Prototype/' + name].decode()
    original['harness/UITests/ToggleUITests.swift'] = inputs[V3 + 'harness/UITests/ToggleUITests.swift'].decode()
    bridge_target = 'runtime/verification/apple-toggle-keyboard-focus/keyboard_bridge.py'
    original[bridge_target] = inputs[V3 + 'inputs/runtime/verification/apple-toggle-keyboard-focus/keyboard_bridge.py'].decode()
    changed = dict(original)

    name = 'source/Prototype/DiagnosticTrace.swift'
    context = (BASE / 'snippets/focus-context.swift').read_text()
    changed[name] = once(changed[name], '    func append(_ kind:', context + '    func append(_ kind:')

    name = 'source/Prototype/main.swift'
    changed[name] = once(changed[name], '    var lastTraceRevision = 0\n', '    var lastTraceRevision = 0\n    var lastFocusContextRevision = 0\n')
    changed[name] = once(changed[name], 'self.lastTraceRevision != DiagnosticTrace.shared.revision',
                         '(self.lastTraceRevision != DiagnosticTrace.shared.revision || self.lastFocusContextRevision != DiagnosticTrace.shared.focusContextRevision)')
    changed[name] = once(changed[name], '"diagnosticTraceDropped": trace.dropped,',
                         '"diagnosticTraceDropped": trace.dropped, "focusContextSchema": "mixer.apple-toggle.focus-context.1", "focusContexts": trace.focusContextEntries, "focusContextDropped": trace.focusContextDropped, "focusContextRevision": trace.focusContextRevision,')
    changed[name] = once(changed[name], '        lastTraceRevision = trace.revision\n',
                         '        lastTraceRevision = trace.revision\n        lastFocusContextRevision = trace.focusContextRevision\n')
    changed[name] = once(changed[name], '    override var preferredFocusEnvironments:',
                         '    override func didUpdateFocus(in context: UIFocusUpdateContext, with coordinator: UIFocusAnimationCoordinator) {\n'
                         '        super.didUpdateFocus(in: context, with: coordinator)\n'
                         '        DiagnosticTrace.shared.focusContext("controller", context)\n'
                         '    }\n    override var preferredFocusEnvironments:')

    name = 'source/Prototype/AuthoredToggleCarrier.swift'
    changed[name] = once(changed[name], '        super.didUpdateFocus(in: context, with: coordinator)\n',
                         '        super.didUpdateFocus(in: context, with: coordinator)\n        DiagnosticTrace.shared.focusContext("carrier", context)\n')

    name = 'harness/UITests/ToggleUITests.swift'
    value = changed[name]
    begin = value.index('    private func ax() throws -> [String: Any] {')
    end = value.index('    private func focus(', begin)
    value = value[:begin] + (BASE / 'snippets/ax.swift').read_text() + value[end:]
    value = once(value, '        let before = try ax()\n',
                 '        focusDiagnosticObservations = []; focusDiagnosticObservationsDropped = 0\n        let before = try ax("before")\n')
    value = once(value, '        var after = try ax(); let end = ProcessInfo.processInfo.systemUptime + 1\n',
                 '        var after = try ax("after-primary"); let end = ProcessInfo.processInfo.systemUptime + 1\n')
    value = once(value, 'after = try ax()\n', 'after = try ax("after-poll")\n')
    value = once(value, '        let result = try bridge("evaluate", ["keyboardWitness": witness])\n',
                 '        // This one follow-up cannot choose the authoritative sample or alter its verdict.\n'
                 '        let followUp = focusOnlyDiagnostic((before["uptime"] as! Double) + 12.0)\n'
                 '        var focusDiagnostic: [String: Any] = ["schema": "mixer.apple-toggle.focus-diagnostic.1", "authoritative": false,\n'
                 '            "case": caseName, "generation": baseline["generation"]!, "actionIndex": baseline["actionIndex"]!,\n'
                 '            "atomic": false, "observations": focusDiagnosticObservations, "observationsDropped": focusDiagnosticObservationsDropped, "followUp": followUp]\n'
                 '        if let bytes = try? JSONSerialization.data(withJSONObject: focusDiagnostic), bytes.count <= 4096 {}\n'
                 '        else { focusDiagnostic = ["schema": "mixer.apple-toggle.focus-diagnostic.1", "authoritative": false,\n'
                 '            "case": caseName, "generation": baseline["generation"]!, "actionIndex": baseline["actionIndex"]!,\n'
                 '            "captureStatus": "incomplete-record-size", "observationsDropped": focusDiagnosticObservationsDropped] }\n'
                 '        let result = try bridge("evaluate", ["keyboardWitness": witness, "focusDiagnostic": focusDiagnostic])\n')
    changed[name] = value

    name = bridge_target
    changed[name] = once(changed[name], 'import keyboard_oracle as o\n', 'import keyboard_oracle as o\nimport focus_diagnostic as focus_diagnostic\n')
    changed[name] = once(changed[name], '        def _request(self,op,body):\n',
                         '        def _request(self,op,body):\n'
                         '            if op==\'evaluate\' and self.current is not None and \'baseline\' in self.current:\n'
                         '                body=focus_diagnostic.strip_and_retain(body,{\'case\':self.current[\'case\'],\'generation\':self.generation,\'actionIndex\':self.current[\'actionIndex\']},self.save)\n')
    new_name = 'runtime/verification/apple-toggle-keyboard-focus/focus_diagnostic.py'
    changed[new_name] = (BASE / 'focus_diagnostic.py').read_text()
    return original, changed


def artifacts():
    inputs = verified_inputs()
    original, changed = render(inputs)
    patch = ''.join(''.join(difflib.unified_diff(original.get(name, '').splitlines(True), value.splitlines(True),
                    fromfile='a/' + name if name in original else '/dev/null', tofile='b/' + name))
                    for name, value in sorted(changed.items())).encode()
    input_rows = {name: {'sha256': sha(data), 'bytes': len(data)} for name, data in inputs.items()}
    local_inputs = ['prepare.py', 'focus_diagnostic.py', 'snippets/focus-context.swift', 'snippets/ax.swift']
    local_rows = {name: {'sha256': sha((BASE / name).read_bytes()), 'bytes': (BASE / name).stat().st_size} for name in local_inputs}
    outputs = {name: {'sha256': sha(value.encode()), 'bytes': len(value.encode()),
                     'kind': 'patched-existing-source' if name in original else 'new-diagnostic-support'}
               for name, value in changed.items()}
    manifest = {'schema': 1, 'scope': 'source-preparation-only', 'executionSealUnchanged': EXECUTION_SEAL,
                'inheritedReviewRevisionLabel': INHERITED_REVIEW_REVISION, 'gitQueried': False,
                'immutableInputs': input_rows, 'preparationInputs': local_rows,
                'inputTreeSHA256': sha(stable_json(input_rows)), 'preparationTreeSHA256': sha(stable_json(local_rows)),
                'preparedSources': outputs, 'preparedSourceTreeSHA256': sha(stable_json(outputs)),
                'patchSHA256': sha(patch), 'patchBytes': len(patch),
                'materializedSourceFiles': 0, 'nativeOrCompilerExecuted': False,
                'commandFinalizationChanged': False, 'runtimeSelected': False,
                'limits': {'contexts': 128, 'perActionObservations': 4, 'secondFocusPasses': 1,
                           'secondFocusRows': 3, 'secondFocusAllowanceSeconds': .250,
                           'diagnosticRecordBytes': 4096, 'bridgeBodyBytesUnchanged': 8192,
                           'strictWitnessWindowSecondsUnchanged': 12},
                'limitations': ['Swift uncompiled; UIKit/XCTest behavior unverified.',
                    'Public synchronous XCUI reads cannot be preempted; late read is incomplete and ends pass.',
                    'No authority or selected runtime imports/execution; host adapter controls only.',
                    'No new command-runner finalization instrumentation; separate review remains pending.',
                    'No build/native/simulator/device/physical-phone/carrier/dogfood/GA acceptance.']}
    return patch, stable_json(manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Compare retained patch and manifest without rewriting')
    args = parser.parse_args()
    patch, manifest = artifacts()
    for name, payload in [('source.patch', patch), ('prepared.json', manifest)]:
        target = BASE / name
        if args.check:
            if target.read_bytes() != payload:
                raise ValueError('Generated artifact differs: ' + name)
        else:
            target.write_bytes(payload)
    print('PASS: digest-bound six-source patch; no source tree or selected runtime materialized/imported')


if __name__ == '__main__':
    main()
