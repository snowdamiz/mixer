#!/usr/bin/env python3
"""Offline verification of saved independent source, command and binary evidence."""
from pathlib import Path
import argparse, hashlib, json, re, tarfile

encoded = lambda obj: (json.dumps(obj, sort_keys=True, indent=2) + '\n').encode()
sha = lambda data: hashlib.sha256(data).hexdigest()


def archive_files(path):
    with tarfile.open(path) as archive:
        return {m.name: archive.extractfile(m).read() for m in archive if m.isfile()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('result', type=Path)
    args = parser.parse_args()
    out = args.result.resolve()
    receipt = json.loads((out/'receipt.json').read_text())
    assert receipt['status'] == 'passed-host-original-owner-review-matrix'
    for path, expected in receipt['inputs'].items():
        assert sha((out/path).read_bytes()) == expected, path
    for command in receipt['commands']:
        for stream in ['stdout','stderr']:
            assert sha((out/command[stream]).read_bytes()) == command[stream+'SHA256'], command['name']
        if command.get('expectedError'):
            assert command['exitCode'] != 0
            assert command['expectedError'] in (out/command['stderr']).read_text()
        else:
            assert command['exitCode'] == 0
    sources = {}
    for label in ['baseline','candidate']:
        files = archive_files(out/'inputs'/(label+'-source.tar.gz'))
        sources[label] = {name.removeprefix('vm/'): data for name,data in files.items()}
        manifest = {name: sha(data) for name,data in sorted(sources[label].items())}
        assert manifest == json.loads((out/'inputs'/(label+'-manifest.json')).read_text())
        assert sha(encoded(manifest)) == receipt['sourceTreeSHA256'][label]
    independent = {name.removeprefix('vm/'): data for name,data in archive_files(out/'independent-source.tar.gz').items()}
    expected = dict(sources['candidate'])
    frame = 'src/experimental_swift_reactor/frame_operations.rs'
    tests = 'src/experimental_swift_reactor/frame_operations_tests.rs'
    expected[frame] += b'\n#[cfg(test)]\n#[path="independent_active_frame_review_tests.rs"]\nmod independent_review_tests;\n'
    expected[tests] += b'\n#[path="independent_active_frame_fault_review_tests.rs"]\nmod independent_fault_review_tests;\n'
    expected['src/experimental_swift_reactor/independent_active_frame_review_tests.rs'] = (out/'inputs/independent-probes.rs').read_bytes()
    expected['src/experimental_swift_reactor/independent_active_frame_fault_review_tests.rs'] = (out/'inputs/independent-fault-probes.rs').read_bytes()
    assert independent == expected, 'derived harness changed product bytes'
    manifest = {name:sha(data) for name,data in sorted(independent.items())}
    assert manifest == json.loads((out/'independent-manifest.json').read_text())
    assert sha(encoded(manifest)) == receipt['sourceTreeSHA256']['independent']
    private = {name.removeprefix('vm/'): data for name,data in archive_files(out/'private-parent-source.tar.gz').items()}
    expected_private = dict(sources['candidate'])
    execution = 'src/experimental_swift_reactor/execution.rs'
    expected_private[execution] += b'\nfn independent_forbidden_inherited_value_access(phase: &mut frame_operations::FrameOperationPhase<\'_>) { let _ = &mut phase.phase; }\n'
    assert private == expected_private
    manifest = {name:sha(data) for name,data in sorted(private.items())}
    assert manifest == json.loads((out/'private-parent-manifest.json').read_text())
    assert sha(encoded(manifest)) == receipt['sourceTreeSHA256']['private-parent']
    assert sha((out/'qualifying-artifacts.tar.gz').read_bytes()) == receipt['qualifyingArchiveSHA256']
    artifacts = archive_files(out/'qualifying-artifacts.tar.gz')
    assert set(artifacts) == {binary['member'] for binary in receipt['binaries']}
    for binary in receipt['binaries']:
        assert sha(artifacts[binary['member']]) == binary['sha256']
        if binary['kind'] == 'unit-executable':
            command = next(c for c in receipt['commands'] if c['name'] == binary['runCommand'])
            output = (out/command['stdout']).read_text()
            summary = re.findall(r'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;', output)
            assert summary == [('ok',str(binary['passed']),'0','0')]
            assert binary['passed'] == len(binary['tests'])
    for comparison in receipt['comparisons']:
        assert comparison['publicMixerCExportsEqual']
        assert comparison['candidateTests'] >= comparison['baselineTests']
    parity = json.loads((out/'literal-frozen-parity.json').read_text())
    assert parity['everyOriginalByteUnchanged']
    common = 'src/experimental/execution/mod.rs'
    candidate = sources['candidate'][common]
    start = candidate.index(b'impl Control {\n')
    end = candidate.index(b'#[cfg_attr(not(feature = "experimental-span-execution"), allow(dead_code))]\npub(crate) struct Frame', start)
    assert candidate[:start] + candidate[end:] == sources['baseline'][common]
    shared = 'src/experimental/execution/borrowed.rs'
    assert sources['baseline'][shared] == sources['candidate'][shared]
    units = [binary for binary in receipt['binaries'] if binary['kind']=='unit-executable']
    product = [binary for binary in units if binary['configuration'].startswith('candidate-')]
    probes = [binary for binary in units if binary['configuration'].startswith('independent-')]
    assert len(product) == len(probes) == 4
    assert all(len(binary['tests']) == 10 for binary in probes)
    print(json.dumps(dict(status='verified-saved-host-evidence',commands=len(receipt['commands']),portableArtifacts=len(artifacts),
        unmodifiedCandidateUnitExecutions=sum(binary['passed'] for binary in product),
        independentProbeExecutions=sum(binary['passed'] for binary in probes),
        sourceTreeSHA256=receipt['sourceTreeSHA256']['candidate'],
        productBodiesLiteralInIndependentHarness=True,
        nativeRuntimeAccepted=False,gaGatePassed=False),sort_keys=True,indent=2))


if __name__ == '__main__':
    main()
