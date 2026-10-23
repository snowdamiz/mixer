#!/usr/bin/env python3
"""Make labelled review copies from explicit hash-checked frozen source inputs.

This helper does not build, qualify, or modify the production checkout. The input
manifest is supplied only after the root announces the immutable candidate.
"""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    source, destination = args.source_root.resolve(), args.destination.resolve()
    if source == REPO.resolve() or destination == REPO.resolve() or REPO.resolve() in destination.parents:
        parser.error('use an immutable exported source root and an external derived destination')
    manifest = args.source_manifest.read_bytes()
    if sha(manifest) != args.manifest_sha256:
        parser.error('source manifest digest differs')
    entries = [line.split('  ', 1) for line in manifest.decode().splitlines()]
    if destination.exists():
        parser.error('destination must be new')
    records = []
    for digest, relative in entries:
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] not in ('sdk', 'experimental-capability-runtime', 'docs'):
            parser.error('unexpected source manifest path: ' + relative)
        original = source / path
        if original.is_symlink() or source not in original.resolve().parents:
            parser.error('input must be a regular source file: ' + relative)
        content = original.read_bytes()
        if sha(content) != digest:
            parser.error('source differs: ' + relative)
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        records.append({'path': relative, 'input_sha256': digest})

    changed = {}
    bridge = destination / 'experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime'

    def replace(file, before, after):
        path = bridge / file
        text = path.read_text()
        if text.count(before) != 1:
            raise RuntimeError('derived hook anchor changed or ambiguous: ' + file + ' / ' + before)
        path.write_text(text.replace(before, after))
        changed[str(path.relative_to(destination))] = sha(path.read_bytes())

    replace('Ownership.swift', 'await performSubmit(ticket)',
            'await ReviewBridgeControls.beforeWorker()\n                await performSubmit(ticket)')
    replace('Ownership.swift', 'ticket.state.withLock { $0.accepted = true }',
            'await ReviewBridgeControls.beforeAcceptancePublish()\n            ticket.state.withLock { $0.accepted = true }')
    replace('Ownership.swift', '        ticket.state.withLock { $0.expected = call }',
            '        ticket.state.withLock { $0.expected = call }\n        await ReviewBridgeControls.afterReservedID()')
    replace('Ownership.swift', '                        waiter.resume(returning: bytes)',
            '                        ReviewBridgeControls.beforeEnvelopeResume()\n                        waiter.resume(returning: bytes)')
    replace('Ownership.swift', '        for _ in 0..<8 {\n',
            '        ReviewBridgeControls.beforeTicketScan(self, cutoff: cutoff)\n        for _ in 0..<8 {\n')
    replace('Ownership.swift', 'control.withLock { $0.closeFinished = true }; signal()',
            'control.withLock { $0.closeFinished = true }; signal()\n            ReviewBridgeControls.afterCloseSignal()')
    replace('Ownership.swift', 'control.withLock { $0.hostCloseFinished = true }; signal()',
            'control.withLock { $0.hostCloseFinished = true }; signal()\n            ReviewBridgeControls.afterCloseSignal()')
    replace('Ownership.swift', 'deliver: { [self] in delivery($0, ticket: ticket) }, didExit: { [self] in exited(ticket) })',
            'deliver: { [self] in ReviewBridgeControls.hostDelivery($0, ticket: ticket, owner: self) }, didExit: { [self] in ReviewBridgeControls.hostExit(ticket, owner: self) })')
    replace('Native.swift', '        switch message.kind {',
            '        ReviewBridgeControls.transformTake(&message)\n        if message.kind == 1 { ReviewBridgeControls.afterNativeTake() }\n        switch message.kind {')
    replace('Native.swift', '        let status = mixer_vm_capability_session_wake_v1(handle, &flag, &report)',
            '        ReviewBridgeControls.beforeNativeWake()\n        let status = mixer_vm_capability_session_wake_v1(handle, &flag, &report)')
    replace('Native.swift', '        let status = mixer_vm_capability_limit_deadline_v1(handle, token, operation.rawValue, timeout, &result, &report)',
            '        ReviewBridgeControls.beforeNativeRemaining()\n        let status = mixer_vm_capability_limit_deadline_v1(handle, token, operation.rawValue, timeout, &result, &report)')
    replace('Native.swift', 'let status = module.withUnsafeBytes', 'var status = module.withUnsafeBytes')
    replace('Native.swift', '        do {\n            try Self.check(status, report)\n            guard output != 0',
            '        ReviewBridgeControls.transformCreate(&status, &output, &report)\n        do {\n            try Self.check(status, report)\n            guard output != 0')
    replace('Native.swift', 'var report = MixerVmReport(); let status = mixer_vm_capability_session_startup_v1(handle, &report)',
            'var report = MixerVmReport(); let status = mixer_vm_capability_session_startup_v1(handle, &report)\n        ReviewBridgeControls.transformStartup(&report)')
    replace('Session.swift', '    public var status: ExperimentalCapabilityStatus { owner.status }',
            '    public var status: ExperimentalCapabilityStatus { owner.status }\n    var reviewExitOwner: NativeExitOwner { owner }')
    controls = (HERE / 'InternalHarness/ReviewBridgeControls.swift').read_bytes()
    (bridge / 'ReviewBridgeControls.swift').write_bytes(controls)
    changed[str((bridge / 'ReviewBridgeControls.swift').relative_to(destination))] = sha(controls)
    # The independent harness is copied separately; package references then resolve
    # solely inside the derived source tree. No tests from another engine are used.
    review = destination / 'verification/capability-bridge-review'
    (review / 'InternalHarness/Tests/Fixtures').mkdir(parents=True)
    review_inputs = {}
    for relative in ['InternalHarness/Package.swift', 'InternalHarness/Tests/InternalBridgeReviewTests.swift']:
        target = review / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        content = (HERE / relative).read_bytes()
        target.write_bytes(content)
        review_inputs[relative] = sha(content)
    for path in (HERE / 'fixtures').iterdir():
        content = path.read_bytes()
        (review / 'InternalHarness/Tests/Fixtures' / path.name).write_bytes(content)
        review_inputs['fixtures/' + path.name] = sha(content)
    for digest, relative in entries:
        if sha((source / relative).read_bytes()) != digest:
            raise RuntimeError('source changed while deriving: ' + relative)
    for relative, digest in review_inputs.items():
        if sha((HERE / relative).read_bytes()) != digest:
            raise RuntimeError('review test input changed while deriving: ' + relative)
    receipt = {'scope': 'Review-only instrumented source copies; no build or qualification',
               'source_root': str(source), 'input_manifest_sha256': sha(manifest), 'input_files': records,
               'derived_source_sha256': changed, 'review_input_sha256': review_inputs,
               'script_sha256': sha(Path(__file__).read_bytes()),
               'production_source_unchanged': True, 'original_public_harness_not_instrumented': True}
    output = destination / 'derived-review.json'
    output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'derived_receipt': str(output), 'scope': receipt['scope']}))


if __name__ == '__main__':
    main()
