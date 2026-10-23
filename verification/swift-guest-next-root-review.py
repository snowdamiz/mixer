#!/usr/bin/env python3
"""Audit retained compiler diagnostics without rerunning or widening the VM."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / 'compiler/experiments/swift-guest-next'
PATH = LANE / 'evidence/2026-10-23-callsites/receipt.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    receipt = json.loads(PATH.read_text())
    assert receipt['status'] == 'passed-diagnostic-only'
    assert not receipt['authorization'] and not receipt['ownedVMExecution'] and not receipt['deviceRun']
    for name, digest in receipt['sourceManifest'].items():
        assert sha(LANE / name) == digest, name
    canonical = json.dumps(receipt['sourceManifest'], sort_keys=True, separators=(',', ':')).encode()
    assert hashlib.sha256(canonical).hexdigest() == receipt['sourceManifestDigest']
    bindings = {}

    def verify(value):
        if isinstance(value, dict):
            if 'path' in value and 'sha256' in value:
                path = Path(value['path'])
                assert sha(path) == value['sha256'], str(path)
                if 'bytes' in value:
                    assert path.stat().st_size == value['bytes']
                bindings[str(path)] = value['sha256']
            for item in value.values():
                verify(item)
        elif isinstance(value, list):
            for item in value:
                verify(item)

    verify(receipt)
    for command in receipt['commands']:
        expected = 2 if command['name'] == 'reactor-owned-inventory' else 0
        assert command['exitCode'] == expected
    trace = json.loads(Path(receipt['trace']['path']).read_text())
    expected = dict(codableRoundTrip=True, committedEntries=1, completionBasisPoints=5000,
                    emptyTitleRejected=True, pendingChanges=1503, reordered=True,
                    repeatedCommitRejected=True, reportIncludesEntry=True,
                    status='passed', taskCount=1000, unicodePreserved=True)
    assert receipt['observations'] == expected
    command = next(c for c in receipt['commands'] if c['name'] == 'retained-corpus-trace')
    assert json.loads(Path(command['stdout']['path']).read_text()) == expected
    assert trace['totalCalls'] == sum(x['calls'] for x in trace['imports'].values()) == 2531
    assert len(trace['invokedImports']) == 9 and len(trace['uninvokedImports']) == 25
    random = trace['imports']['random_get']
    assert random['calls'] == 2510 and random['totalRequestedBytes'] == 40132
    assert random['maximumRequestedBytes'] == 16
    assert trace['memory']['icuExtent']['changedBytes'] == 0
    assert trace['memory']['initialExtent']['changed64KiBPages'] == 15
    assert not trace['memory']['peakMeasured']
    assert receipt['reactorProbe']['artifact']['bytes'] == 5508625
    assert receipt['reactorProbe']['gzip9Bytes'] == 1589092
    assert not receipt['reactorProbe']['ownedInventory']['valid']
    assert receipt['reactorProbe']['maximumNesting'] is None
    record = {
        'status': 'root source review and exact retained diagnostic evidence audit passed',
        'owner_receipt': {'path': str(PATH.relative_to(ROOT)), 'sha256': sha(PATH)},
        'root_audit_sha256': sha(Path(__file__)),
        'reviewed_design_sha256': sha(LANE / 'README.md'),
        'source_manifest_digest': receipt['sourceManifestDigest'],
        'verified_sources': len(receipt['sourceManifest']),
        'verified_distinct_path_bindings': len(bindings),
        'recorded_commands': len(receipt['commands']),
        'reviewed_vm_meter': {'path': 'vm/src/execute.rs', 'sha256': sha(ROOT / 'vm/src/execute.rs')},
        'reviewed_corpus': {'path': 'compiler/Fixtures/FieldLogCorpus/main.swift', 'sha256': sha(ROOT / 'compiler/Fixtures/FieldLogCorpus/main.swift')},
        'findings': [],
        'scope': [
            'No new executable test or tool run in this root audit; inspected original diagnostic source and verified retained outputs.',
            'Node is a development oracle only. Both original observation equality and scalar reactor calls are preserved evidence, not owned Swift execution.',
            'Host-call meter resets per invocation. 2531 is prospective single-command corpus demand, not a whole-app impossibility or ordinary reducer-turn measurement.',
            'Ten sampled stacks identify UUID/outbox callsites; no complete dynamic call coverage or randomness substitution.',
            'Final byte equality does not establish immutable ICU, temporary-write behavior, peak allocation or physical RSS.',
            'Complete compressed artifact including required guest runtime must meet 3MiB; base reuse or delta transfer earns no budget credit.',
            'A real unchanged FieldLog model reactor is the next artifact; span/cache execution and exact WASI/resource profile remain unimplemented.'
        ]
    }
    output = ROOT / 'verification/swift-guest-next-root-review.json'
    if args.check:
        assert json.loads(output.read_text()) == record
    else:
        output.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'receipt_sha256': sha(output), 'bindings': len(bindings), 'commands': len(receipt['commands'])}))


if __name__ == '__main__':
    main()
