#!/usr/bin/env python3
"""Verify preserved macro proposal evidence; performs no product/native run."""
from pathlib import Path
import hashlib
import json
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = HERE / 'results/20261024T030635088702Z'
FINAL = HERE / 'results/20261024T030849261537Z'
METHODS = ['pop32', 'close_control', 'branch']


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def method(text, name):
    start = text.index('fn ' + name + '(')
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def check_commands(folder, commands):
    for command in commands:
        assert sha(folder / command['stdout']) == command['stdoutSHA256'], command['name']
        assert sha(folder / command['stderr']) == command['stderrSHA256'], command['name']
        if command['expectedError']:
            assert command['exitCode'] != 0
        else:
            assert command['exitCode'] == 0


def main():
    saved = json.loads((BASE / 'receipt.json').read_text())
    final = json.loads((FINAL / 'receipt.json').read_text())
    assert saved['status'] == 'failed-preflight'
    assert final['status'] == 'macro-proposal-expansion-layout-privacy-preflight-only'
    assert final['inheritedReceiptSHA256'] == sha(BASE / 'receipt.json')
    for receipt in [saved, final]:
        assert receipt['productVMUnchanged'] and receipt['priorRejectionUnchanged']
        assert receipt['implementationApplied'] is False
        assert receipt['guestExecution'] is False
        assert receipt['nativeRuntime'] is False
        assert receipt['semanticAcceptance'] is False
    check_commands(BASE, saved['commands'])
    check_commands(FINAL, final['commands'])
    assert sha(BASE / 'source.tar.gz') == saved['archiveSHA256']
    source = json.loads((BASE / 'source-manifest.json').read_text())
    assert len(source) == saved['sourceFiles'] == 116
    assert hashlib.sha256(encoded(source)).hexdigest() == saved['sourceTreeSHA256']
    with tarfile.open(BASE / 'source.tar.gz') as archive:
        original = {member.name.removeprefix('vm/'): archive.extractfile(member).read()
                    for member in archive.getmembers() if member.isfile()}
    assert {name: hashlib.sha256(data).hexdigest() for name, data in original.items()} == source
    for name, digest in source.items():
        assert sha(ROOT / 'vm' / name) == digest, name
    prior = json.loads((ROOT / 'verification/swift-control-extraction/seal.json').read_text())
    for name, digest in prior['bindings'].items():
        assert sha(ROOT / name) == digest, 'prior rejection changed: ' + name
    for name in ['frozen_control_methods.rs', 'layout_probe.rs']:
        assert (HERE / name).read_bytes() == (BASE / 'inputs' / name).read_bytes()
    proposed = dict(original)
    owner = proposed['src/experimental/execution/mod.rs'].decode()
    for name in METHODS:
        owner = owner.replace(method(owner, name), 'borrowed::frozen_control_methods!();' if name == 'pop32' else '', 1)
    proposed['src/experimental/execution/mod.rs'] = owner.encode()
    proposed['src/experimental/execution/borrowed.rs'] += b'\n' + (BASE / 'inputs/frozen_control_methods.rs').read_bytes()
    def digest_manifest(files):
        return {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    candidate = digest_manifest(proposed)
    baseline_layout = dict(original)
    candidate_layout = dict(proposed)
    for variant in [baseline_layout, candidate_layout]:
        variant['src/experimental/execution/mod.rs'] += b'\n' + (BASE / 'inputs/layout_probe.rs').read_bytes()
        variant['src/lib.rs'] += b'\n#[cfg(feature="experimental-span-execution")] pub fn control_macro_layout_probe(){experimental::execution::control_macro_layout_probe();}\n'
        variant['examples/control-macro-layout.rs'] = b'fn main(){mixer_vm::control_macro_layout_probe();}\n'
    expected_variants = {'baseline-expansion': source, 'candidate-expansion': candidate,
                         'candidate-check': candidate,
                         'baseline-layout': digest_manifest(baseline_layout),
                         'candidate-layout': digest_manifest(candidate_layout)}
    assert len(saved['variants']) == 5
    for variant in saved['variants']:
        actual = json.loads((BASE / variant['manifest']).read_text())
        assert actual == expected_variants[variant['name']], variant['name']
        assert hashlib.sha256(encoded(actual)).hexdigest() == variant['treeSHA256']
    expanded = {}
    assert len(saved['expansions']) == 8
    for expansion in saved['expansions']:
        command = next(c for c in saved['commands'] if c['name'] == expansion['label'])
        assert command['diagnosticBootstrap'] is True
        assert command['argv'][-1] == '-Zunpretty=expanded'
        output = (BASE / command['stdout']).read_text()
        owner = output[output.index('impl SpanInstance {'):]
        actual = {name: method(owner, name) for name in METHODS}
        assert actual == json.loads((BASE / expansion['methods']).read_text())
        assert {name: hashlib.sha256(text.encode()).hexdigest() for name, text in actual.items()} == expansion['methodHashes']
        expanded[expansion['label']] = actual
    for config in ['span', 'all']:
        for profile in ['debug', 'release']:
            suffix = config + '-' + profile + '-expansion'
            assert expanded['baseline-' + suffix] == expanded['candidate-' + suffix]
    checks = [c for c in saved['commands'] if c['name'].endswith('-check')]
    assert len(checks) == 8 and all(c['diagnosticBootstrap'] is False for c in checks)
    layouts = []
    assert len(saved['binaries']) == 16
    for binary in saved['binaries']:
        assert sha(Path(binary['path'])) == binary['sha256']
        output = (BASE / (binary['runCommand'] + '.stdout')).read_text()
        if binary['executedTest']:
            assert binary['executedTest'] + ': test' in (BASE / (binary['listCommand'] + '.stdout')).read_text().splitlines()
            assert 'test result: ok. 1 passed; 0 failed; 0 ignored;' in output
        rows = []
        for line in output.splitlines():
            for marker in ['control_macro_type ', 'control_macro_offset ', 'control_macro_reservation ']:
                at = line.find(marker)
                if at >= 0:
                    rows.append(line[at:])
                    break
        assert len(rows) == 66
        assert 'control_macro_reservation 2912' in rows
        layouts.append(dict(label=binary['label'], records=rows))
    assert all(item['records'] == layouts[0]['records'] for item in layouts)
    assert layouts == json.loads((FINAL / final['reconstructedLayouts']).read_text())
    assert sha(FINAL / final['reconstructedLayouts']) == final['reconstructedLayoutsSHA256']
    assert {n['expectedError'] for n in final['negatives']} == {'E0433', 'E0624'}
    for negative in final['negatives']:
        assert negative['expectedError'] in negative['actualCodes']
    sibling_folder = HERE / 'privacy-sibling'
    sibling = json.loads((sibling_folder / 'receipt.json').read_text())
    assert sibling['command']['exitCode'] != 0 and 'E0603' in sibling['command']['actualCodes']
    assert sha(sibling_folder / 'stdout.log') == sibling['command']['stdoutSHA256']
    assert sha(sibling_folder / 'stderr.log') == sibling['command']['stderrSHA256']
    sibling_expected = dict(proposed)
    sibling_expected['src/lib.rs'] += sibling['appendedLibSource'].encode()
    assert digest_manifest(sibling_expected) == json.loads((sibling_folder / 'source-manifest.json').read_text())
    delta = json.loads((HERE / 'named-transient-map.json').read_text())
    assert len(delta['bindingGroups']) == 26
    assert sum(delta['trySites'].values()) == 9
    assert delta['runtimeAddedObjects'] == delta['runtimeAddedBoundaries'] == delta['byteDeltaClaim'] == 0
    assert all(g['additionalPositions'] == g['additionalBytes'] == 0 for g in delta['bindingGroups'])
    for name, count in delta['trySites'].items():
        assert method(original['src/experimental/execution/mod.rs'].decode(), name).count('?') == count
    matrix = json.loads((HERE / 'later-implementation-matrix.json').read_text())
    assert matrix['status'] == 'pending-later-product-implementation'
    assert len(matrix['newTests']) == 6
    assert sha(ROOT / matrix['sourceMatrix']) == matrix['sourceMatrixSHA256']
    summary = dict(status='verified-macro-proposal-preflight-not-implementation-acceptance',
                   sourceFiles=116, compilerExpandedMethodsEqual=12, ordinaryFeatureProfileChecks=8,
                   metadataBinaries=16, layoutRecordsPerBinary=66, privacyRejections=3,
                   unchangedTransientGroups=26, unchangedTrySites=9, addedRuntimeObjects=0,
                   frozenReservationBytes=2912, pendingProductCases=6,
                   productVMUnchanged=True, priorRejectionUnchanged=True,
                   swiftExecution=False, semanticAcceptance=False, rootFreeze='pending')
    (HERE / 'verified-summary.json').write_bytes(encoded(summary))
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()
