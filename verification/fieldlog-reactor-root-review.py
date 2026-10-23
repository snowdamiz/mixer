#!/usr/bin/env python3
"""Independently audit retained model-reactor evidence; never authorize execution."""
import argparse
import gzip
import hashlib
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / 'compiler/experiments/fieldlog-reactor'
EVIDENCE = LANE / 'evidence/2026-10-23-qualified'
OWNER = EVIDENCE / 'receipt.json'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def closed_object(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, key
        result[key] = value
    return result


def parse(value):
    return json.loads(value, object_pairs_hook=closed_object)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    receipt = parse(OWNER.read_text())
    assert receipt['status'] == 'full-swift-fieldlog-reactor-model-parity-passed; owned-runtime-and-product-gates-open'
    assert receipt['fullSwiftSDK'] and not receipt['embeddedSwift']
    assert not any(receipt[key] for key in ('authorization', 'ownedVMExecution', 'deviceRun'))
    bindings = {}

    def verify(value):
        if isinstance(value, dict):
            if 'path' in value and 'sha256' in value:
                path = Path(value['path'])
                if not path.is_absolute():
                    path = EVIDENCE / path
                if str(path) not in bindings:
                    bindings[str(path)] = digest(path)
                assert bindings[str(path)] == value['sha256'], str(path)
                if 'bytes' in value:
                    assert path.stat().st_size == value['bytes'], str(path)
            for item in value.values():
                verify(item)
        elif isinstance(value, list):
            for item in value:
                verify(item)

    verify(receipt)
    snapshot = Path(receipt['retainedDiagnosticSourceDirectory'])
    for name, expected_hash in receipt['sourceManifest'].items():
        assert digest(ROOT / name) == digest(snapshot / name) == expected_hash, name
    canonical = json.dumps(receipt['sourceManifest'], sort_keys=True, separators=(',', ':')).encode()
    assert hashlib.sha256(canonical).hexdigest() == receipt['sourceManifestDigest']
    model = Path(receipt['inputs']['model']['path'])
    with tarfile.open(receipt['inputs']['archive']['path']) as archive:
        assert archive.extractfile('Sources/FieldLogModels/Workspace.swift').read() == model.read_bytes()
    assert receipt['fieldlogRevision'] == '1587d2d4f02ab2dad9914df97f878727dd622296'
    corpus = Path(receipt['inputs']['corpus']['path']).read_bytes()
    wrapper = Path(receipt['inputs']['wrapper']['path']).read_bytes()
    marker = b'let now = Date(timeIntervalSince1970: 1_792_627_200)\n'
    body = corpus[corpus.index(marker):]
    actual_body = wrapper.split(b'private func runFieldLogCorpus() throws {\n')[1].split(
        b'}\n\n// Swift errors must not cross a C-compatible boundary.')[0]
    declaration = corpus[corpus.index(b'struct Receipt:'):corpus.index(marker)].rstrip()
    actual_declaration = wrapper[wrapper.index(b'struct Receipt:'):wrapper.index(b'// The body between')].rstrip()
    assert body == actual_body and len(body) == 2675
    assert declaration == actual_declaration and len(declaration) == 361
    assert hashlib.sha256(body).hexdigest() == receipt['exactSourceMap']['bodySHA256']
    assert hashlib.sha256(declaration).hexdigest() == receipt['exactSourceMap']['receiptSHA256']
    commands = {command['name']: command for command in receipt['commands']}
    assert len(commands) == len(receipt['commands']) == 21
    for name, command in commands.items():
        assert command['exitCode'] == (2 if name.startswith('owned-') else 0), name
        assert not command['timedOut'] and not command['outputLimitExceeded'], name
    expected = dict(codableRoundTrip=True, committedEntries=1, completionBasisPoints=5000,
                    emptyTitleRejected=True, pendingChanges=1503, reordered=True,
                    repeatedCommitRejected=True, reportIncludesEntry=True,
                    status='passed', taskCount=1000, unicodePreserved=True)
    assert receipt['expectedObservation'] == expected
    observed = {}
    for name, count in [('native-command-run', 1), ('native-boundary-run', 2),
                        ('wasm-command-oracle', 1), ('wasm-reactor-oracle', 2)]:
        output = (EVIDENCE / commands[name]['stdout']['path']).read_text().splitlines()
        assert len(output) == count, name
        values = [parse(line) for line in output]
        for value in values:
            assert value == expected and all(type(value[k]) is type(v) for k, v in expected.items()), name
        observed[name] = count
    for mode in ('command', 'reactor'):
        lines = (EVIDENCE / commands[f'wasm-{mode}-oracle']['stderr']['path']).read_text().splitlines()
        assert len(lines) == 1 and lines[0].startswith('FIELDLOG_ORACLE ')
        assert parse(lines[0][len('FIELDLOG_ORACLE '):]) == receipt['parity'][mode]['control']
    control = receipt['parity']['reactor']['control']
    assert control['initializationCalls'] == 1 and control['invocationCalls'] == 2
    assert control['statuses'] == [0, 0]
    assert [sum(control['calls'][key].values()) for key in ('initialize', 'invoke-1', 'invoke-2')] == [7, 2522, 2513]
    assert [item['bytes'] for item in control['memory']] == [38273024, 38273024, 40960000, 41025536]
    descriptor = parse(Path(receipt['descriptors']['path']).read_text())
    exports = {row['name']: row for row in descriptor['exports']}
    assert set(exports) == {'memory', '_initialize', 'mixer_fieldlog_corpus_v1'}
    assert descriptor['startFunction'] is None
    assert exports['_initialize']['signature'] == dict(parameters=[], results=[])
    assert exports['mixer_fieldlog_corpus_v1']['signature'] == dict(parameters=[], results=['i32'])
    assert len(descriptor['imports']) == 34
    assert control['imports'] == [dict(module=row['module'], name=row['name'], kind='function') for row in descriptor['imports']]
    assert control['exports'] == [dict(name=row['name'], kind=row['kind']) for row in descriptor['exports']]
    artifact = receipt['guestBuild']['reactorArtifact']
    assert artifact['bytes'] == receipt['size']['rawBytes'] == 53777114
    assert artifact['sha256'] == '24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994'
    assert receipt['size']['gzip9Mtime0']['bytes'] == 18976211
    with gzip.open(receipt['size']['gzip9Mtime0']['path'], 'rb') as compressed:
        assert hashlib.file_digest(compressed, 'sha256').hexdigest() == artifact['sha256']
    assert not receipt['size']['completeArtifactBudgetPassed']
    assert receipt['size']['completeArtifactBudgetBytes'] == 3145728
    assert not receipt['ownedStrictRejection']['valid']
    assert receipt['ownedStrictRejection']['error']['message'] == 'module byte limit exceeded'
    assert not receipt['ownedDiagnosticInventory']['valid'] and receipt['ownedDiagnosticInventory']['inventory_complete']
    assert receipt['nesting']['maximum'] is None
    retained_evidence = {str(path.relative_to(ROOT)): digest(path) for path in sorted((LANE / 'evidence').rglob('*')) if path.is_file()}
    record = {
        'status': 'root source review and retained full Swift model-reactor evidence audit passed',
        'authorization': False,
        'owner_receipt': {'path': str(OWNER.relative_to(ROOT)), 'sha256': digest(OWNER)},
        'root_audit_sha256': digest(Path(__file__)),
        'reviewed_readme_sha256': digest(LANE / 'README.md'),
        'source_manifest_digest': receipt['sourceManifestDigest'],
        'verified_sources_and_retained_copies': len(receipt['sourceManifest']),
        'verified_distinct_path_bindings': len(bindings),
        'recorded_commands': len(commands),
        'complete_stdout_observations': observed,
        'retained_evidence_manifest': retained_evidence,
        'findings': [],
        'scope': [
            'No new compiled executable run in this root audit; original native and Node results and exact sources reviewed and matched.',
            'The unchanged immutable model and complete corpus body match all 11 typed observations; two reactor calls create fresh local Workspace values.',
            'One WASI initialization is observed; explicit test-boundary fflush repairs the preserved first buffered-output failure.',
            'Node remains a development oracle; strict owned rejection is retained and inventory is not full validation.',
            'Complete required-runtime artifact exceeds the 3MiB delivery budget; no runtime-base or delta exclusion earns credit.',
            'No persistent feature UI, owned full Swift execution, nesting, peak memory, physical RSS, device or product gate qualification.'
        ]
    }
    output = ROOT / 'verification/fieldlog-reactor-root-review.json'
    if args.check:
        assert parse(output.read_text()) == record
    else:
        output.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(dict(receipt_sha256=digest(output), path_bindings=len(bindings), retained_evidence=len(retained_evidence))))


if __name__ == '__main__':
    main()
