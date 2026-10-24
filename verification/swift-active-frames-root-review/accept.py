#!/usr/bin/env python3
"""Record root source acceptance after manual review; hashes do not prove semantics."""
from pathlib import Path
import datetime, hashlib, json, subprocess, sys
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    audit = ROOT / sys.argv[1]
    data = json.loads(audit.read_text())
    assert data['status'] == 'passed-bounded-offline-resume-audit-root-acceptance-pending'
    assert not data['remainingBlockingFindings']
    assert data['source']['treeSHA256'] == '4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4'
    paths = {str(audit.relative_to(ROOT)), 'verification/swift-active-frames-root-review/accept.py'}
    for path, digest in data['inputFiles'].items():
        assert sha(ROOT / path) == digest, path
        paths.add(path)
    for cmd in data['commands']:
        assert cmd['exitCode'] == 0
        for stream in ['stdout', 'stderr']:
            path = audit.parent / cmd[stream]
            assert sha(path) == cmd[stream + 'SHA256']
            paths.add(str(path.relative_to(ROOT)))
    for folder, seal in [('swift-active-frames-implementation', 'seal.json'), ('swift-active-frames-implementation-review', 'review-seal.json'), ('swift-active-frames-resume-audit', 'seal.json')]:
        base = ROOT / 'verification' / folder
        paths.add(str((base / seal).relative_to(ROOT)))
        for rel, digest in json.loads((base / seal).read_text())['files'].items():
            path = base / rel
            assert sha(path) == digest, path
            paths.add(str(path.relative_to(ROOT)))
    manifest = json.loads((ROOT / 'verification/implementation-pause-2026-10-24/candidate-manifest.json').read_text())
    for path, digest in manifest.items():
        assert sha(ROOT / 'vm' / path) == digest, path
        paths.add('vm/' + path)
    source_diff = subprocess.check_output(['git', 'diff', '--', 'vm'], cwd=ROOT)
    (OUT / 'tracked-source.diff').write_bytes(source_diff)
    paths.add('verification/swift-active-frames-root-review/tracked-source.diff')
    receipt = dict(schema=1, decision='accepted-private-host-frame-entry-return-cleanup-slice', reviewer='root',
        observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        sourceRevision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        sourceTreeSHA256=data['source']['treeSHA256'], sourceFiles=len(manifest),
        command=[sys.executable, str(Path(__file__).resolve()), str(audit)], pythonVersion=sys.version,
        manualSourceReview=[
            'Reviewed frame_operations.rs production methods lines 1-1035, changed original-owner/construction/value/consuming-cleanup barriers and exact baseline diff.',
            'Fresh entry lengths are captured only after active agreement; rollback removes only acquired suffix/debits and retains sticky discrepancies.',
            'Original cache owns all pins; rejected release returns the same pin to the same indexed frame, separate from an unpublished guard; explicit cleanup reacquisition begins a new bounded pass.',
            'Cleanup uses no execution work/cancellation gate; original owner checks precede transition. Nested and outer reservation debt survive failed completion.',
            'Fixed caller storage and phase parts end before restoring construction bound; retained state blocks consuming cleanup and zero-frame value preparation.',
            'Accepted the independent actual-source/typed-field review and exact compiled field layout for logical ownership accounting, without inferring optimizer machine stack bounds.'
        ],
        evidenceSummary=dict(producerCandidateExecutions=904, independentCandidateUnitExecutions=682,
            independentAdversarialExecutions=40, producerCommands=229, importedCommands=204,
            freshCommands=25, producerLayouts=8, independentFreshLayouts=2, metadataReplays=8),
        rootExecutionScope='Manual source review and saved-evidence/hash audit. Root did not rerun compiler, retained test binaries or native runtimes at this acceptance; their original executions and command lineage are retained.',
        files={p:sha(ROOT/p) for p in sorted(paths)},
        limitations=[
            'Private nondefault host slice only; public invocation/instruction dispatch/Ready lifecycle remains absent.',
            'Broad Clippy retains 26 baseline diagnostics; not a clean broad-lint claim.',
            'AF15 capacity rejection is a derived defensive injection, not naturally reachable from valid state.',
            'Positive accounting increases construction/header/frame reservation; narrow budgets may reject construction without widening limits.',
            'Native simulator/emulator and computer use remain paused; phones disconnected; physical final matrix pending.',
            'No immutable published FieldLog, signing/store/customer/operational or GA acceptance.'
        ], gaGatePassed=False)
    (OUT / 'acceptance.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(dict(decision=receipt['decision'], bindings=len(paths), sourceTreeSHA256=receipt['sourceTreeSHA256'])))
if __name__ == '__main__': main()
