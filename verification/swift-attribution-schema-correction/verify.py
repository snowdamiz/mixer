#!/usr/bin/env python3
"""Read-only correction audit. No restoration, scratch, target selection or dispatch."""
from pathlib import Path
import ast
import copy
import gzip
import hashlib
import importlib.util
import io
import json
import sys
import tarfile
import unittest

sys.dont_write_bytecode = True
H = Path(__file__).resolve().parent
R = H.parent.parent
P = H.parent / 'swift-current-attribution-full-preparation'
Q = H.parent / 'swift-current-attribution-preparation-review'
C = H.parent / 'swift-cache-current-attribution-observer'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_bytes())


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def functions(path):
    source = Path(path).read_text()
    return {n.name: ast.get_source_segment(source, n) for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}


def normalized(body):
    for name in ('harness.rs', 'adapter.rs', 'adapter-controls.rs', 'baseline-manifest.json',
                 'copied-build-manifest.json', 'binding.json', 'binary.json', 'output-contract.json'):
        for slash in (' / ', '/'):
            for quote in ('"', "'"):
                body = body.replace('ASSETS' + slash + quote + name + quote,
                                    'HERE' + slash + quote + name + quote)
    body = body.replace('    assert Path(telemetry.__file__).resolve() == _classifier_path\n', '')
    body = body.replace('        assert selection["originalPreparedSealSHA256"] == sha(ASSETS / "prepared-seal.json") == "c40ab937f218baa54b45e5a5846e4dd12d05edcfb2c3786a75d27f026f70a7f1"\n', '')
    body = body.replace('choices=("control", "host-controls", "adapter-controls", "target")',
        'choices=("prepare", "build", "control", "host-controls", "adapter-controls", "propose", "target", "cleanup")')
    return body


def enum_variants(source, name):
    body = source.split('pub enum ' + name + ' {', 1)[1].split('}', 1)[0]
    return tuple(line.strip().removesuffix(',') for line in body.splitlines() if line.strip())


def main():
    seal = load(H / 'seal.json')
    names = {str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name != 'seal.json'}
    assert names == set(seal['files'])
    for name, digest in seal['files'].items(): assert sha(H / name) == digest, name
    for name, digest in seal['externalFiles'].items(): assert sha(R / name) == digest, name
    for directory, name, digest, count in ((P, 'prepared-seal.json', 'c40ab937f218baa54b45e5a5846e4dd12d05edcfb2c3786a75d27f026f70a7f1', 104),
                                         (Q, 'seal.json', 'd4eff30cc7c48accf8c93621e0810ec94a68ee282699fed9a1aaf772071ac3b6', 69)):
        assert sha(directory / name) == digest
        original_seal = load(directory / name); assert len(original_seal['files']) == count
        for n, d in original_seal['files'].items(): assert sha(directory / n) == d, n
        for n, d in original_seal['externalFiles'].items(): assert sha(R / n) == d, n
    original_functions = functions(P / 'diagnostic.py')
    corrected_functions = functions(H / 'diagnostic.py')
    assert original_functions.keys() == corrected_functions.keys()
    assert all(normalized(corrected_functions[n]) == body for n, body in original_functions.items())
    assert sha(H / 'test_driver.py') == sha(P / 'test_driver.py')
    driver = module('verified_corrected_driver', H / 'diagnostic.py')
    telemetry = driver.telemetry
    assert Path(telemetry.__file__).resolve() == (H / 'telemetry.py').resolve()
    assert driver.ASSETS == P and driver.SOURCE == P / 'owned-scratch/vm' and driver.BINARY == P / 'bin/exact-tests'
    assert {n: hashlib.sha256(b).hexdigest() for n, b in driver.reconstructed_source().items()} == load(P / 'copied-build-manifest.json')
    with tarfile.open(C / 'isolated-source.tar.gz', 'r:gz') as archive:
        control = archive.extractfile('src/experimental_swift_reactor/control.rs').read()
    assert hashlib.sha256(control).hexdigest() == load(C / 'copied-source-manifest.json')['src/experimental_swift_reactor/control.rs']
    control = control.decode()
    assert frozenset(enum_variants(control, 'SwiftRunFailureKind')) == telemetry.KINDS
    variants = enum_variants(control, 'SwiftRunResource')
    assert variants[0] == 'Reservation(SwiftReservationCategory)'
    assert tuple(variants[1:]) == telemetry.RESOURCE_VARIANTS
    assert enum_variants(control, 'SwiftReservationCategory') == telemetry.RESERVATIONS
    binding = load(P / 'binding.json')
    assert 'host: aarch64-apple-darwin' in binding['compilerTools']['rustc']['version']
    assert binding['compilerTools']['machine'] == 'arm64' and telemetry.USIZE == telemetry.U64
    contract = load(P / 'output-contract.json')
    assert telemetry.ENVELOPE == contract['maxEnvelopeBytesIncludingPrefixNewline'] == 4608
    assert telemetry.LIFETIME == contract['maxLifetimeBytes'] == 27648
    assert tuple(contract['labels']) == telemetry.LABELS
    digest = hashlib.sha256()
    with gzip.open(P / 'bin/exact-tests.gz', 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): digest.update(block)
    assert digest.hexdigest() == load(P / 'binary.json')['retained']['sha256'] == 'fc27c22f8f771e7f148bcb73781b09a974a2bcebce7be7466b951ff85d9fafaf'
    classifications = load(H / 'classifications.json')
    original = load(Q / 'parser-original-events.json')
    for case in classifications['sixReproductions']:
        before = copy.deepcopy(original)
        result = telemetry.classify(R / case['path'], original)
        assert result['status'] == 'invalid_or_missing' and result['issues'] == case['correctedIssues']
        assert original == before and not result['originalResultReplaced'] and not result['cleanupTruthInferredFromTelemetry']
    schema = module('read_only_schema_controls', H / 'test_schema.py')
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(unittest.defaultTestLoader.loadTestsFromTestCase(schema.TypedSchemaControls))
    assert result.wasSuccessful() and result.testsRun == 16, output.getvalue()
    commands = {}
    for path in sorted((H / 'commands').glob('*/receipt.json')):
        command = load(path); commands[path.parent.name] = command
        assert command['stdoutSHA256'] == sha(path.parent / 'stdout') and command['stderrSHA256'] == sha(path.parent / 'stderr')
        assert command['processGroupEmpty'] and command['scratchCleaned'] and command['inputsUnchanged'] and not command['signalsSent']
        assert command['fullTargetAttempts'] == command['realTargetValidations'] == command['realTargetInitializeCalls'] == command['realTargetCorpusCalls'] == command['nativeOrDeviceRuns'] == 0
        for name, digest in command['codeSHA256'].items():
            matching = [p for p in [H / name, *sorted((H / 'commands').glob('*/' + name))] if p.is_file() and sha(p) == digest]
            assert matching, (path.parent.name, name)
        for name, digest in command['externalInputsSHA256'].items(): assert sha(R / name) == digest, name
    assert set(commands) == {'host-001', 'host-002', 'host-003'}
    assert not commands['host-001']['passed'] and commands['host-001']['exitCode'] == 1
    assert 'FAILED (failures=2)' in (H / 'commands/host-001/stderr').read_text()
    assert commands['host-002']['passed'] and commands['host-003']['passed']
    assert 'Ran 38 tests' in (H / 'commands/host-003/stderr').read_text() and (H / 'commands/host-003/stderr').read_text().endswith('OK\n')
    template = load(H / 'root-selection-template.json')
    assert template['exactCommandSelected'] is False
    assert template['originalPreparedSealSHA256'] == sha(P / 'prepared-seal.json')
    assert template['driverSHA256'] == sha(H / 'diagnostic.py') and template['telemetryClassifierSHA256'] == sha(H / 'telemetry.py')
    assert template['outerCommand'] == ['python3', '-B', str((H / 'diagnostic.py').relative_to(R)), 'target']
    for name, digest in template['boundEvidence'].items(): assert sha(H / name) == digest, name
    for name in ('root-selection.json', 'target-attempt-started.json', 'owned-scratch', 'owned-tmp', '__pycache__'):
        assert not (H / name).exists(), name
    receipt = load(H / 'receipt.json')
    assert receipt['hostMethodsPassed'] == 38 and receipt['sixReviewReproductionsRejected'] == 6
    assert receipt['fullTargetAttempts'] == 0 and not receipt['gaAccepted'] and not receipt['rootSelectionCreated']
    print(json.dumps({'correctionIntegrityVerified': True, 'sealedMembers': len(names),
        'sixReviewReproductionsRejected': 6, 'retainedProducerOutputsStillValid': 2,
        'hostMethodsPassed': 38, 'inMemorySchemaMethodsReplayed': 16,
        'originalFunctionsPreservedWithExplicitChangesOnly': len(original_functions),
        'fullTargetAttempts': 0, 'rootSelectionCreated': False, 'gaAccepted': False}, sort_keys=True))


if __name__ == '__main__': main()
