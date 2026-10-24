#!/usr/bin/env python3
"""Root audit and bounded host replay of the frozen literal extraction."""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import subprocess
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/swift-control-macro-implementation'
INDEPENDENT = ROOT / 'verification/swift-control-macro-independent-review'
FINAL = PRODUCER / 'results/20261024T032530904964Z'
PRIOR = PRODUCER / 'results/20261024T032202022153Z'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    bindings, commands = {}, []

    def bind(path, expected=None):
        digest = sha(path)
        if expected is not None:
            assert digest == expected, str(path)
        bindings[str(path.relative_to(ROOT))] = digest

    def run(name, argv):
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        process = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
        for suffix, value in [('stdout', process.stdout), ('stderr', process.stderr)]:
            file = HERE / (name + '.' + suffix)
            file.write_text(value)
            bind(file)
        commands.append({'name': name, 'argv': argv, 'startedUTC': started,
                         'finishedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         'exitCode': process.returncode})
        assert process.returncode == 0, (name, process.stderr[-1000:])
        return process.stdout

    for directory in [PRODUCER, INDEPENDENT]:
        seal = directory / 'seal.json'
        bind(seal)
        for name, expected in json.loads(seal.read_text())['bindings'].items():
            bind(ROOT / name, expected)
    run('producer-offline', ['python3', '-B', str(PRODUCER / 'verify.py')])
    review_receipt = INDEPENDENT / 'results/20261024T032720299561Z/receipt.json'
    run('independent-offline', ['python3', '-B', str(INDEPENDENT / 'verify_saved.py'), str(review_receipt)])
    summary = json.loads((INDEPENDENT / 'summary.json').read_text())
    assert summary['blockingFindings'] == []
    assert summary['runtimeAddedObjects'] == summary['runtimeAddedCallBoundaries'] == 0
    assert summary['frozenReservationBytes'] == 2912
    binary_manifest = HERE / 'qualifying-binaries.json'
    binary_archive = HERE / 'qualifying-binaries.tar.gz'
    bind(binary_manifest)
    bind(binary_archive)
    retained = json.loads(binary_manifest.read_text())
    assert len(retained) == 44
    with tarfile.open(binary_archive) as archive:
        files = {item.name: item for item in archive.getmembers()}
        assert set(files) == {item['archiveMember'] for item in retained}
        for item in retained:
            data = archive.extractfile(files[item['archiveMember']]).read()
            assert hashlib.sha256(data).hexdigest() == item['sha256']
    for folder, label, private in [(FINAL, 'candidate-all-release', False),
                                   (PRIOR, 'candidate-all-release-probe', True)]:
        receipt = json.loads((folder / 'receipt.json').read_text())
        binary = next(b for b in receipt['binaries'] if b['label'] == label and
                      b['name'] == ('mixer_vm' if private else 'span_control_extraction'))
        item = next(item for item in retained if item['receipt'] == str((folder / 'receipt.json').relative_to(ROOT))
                    and item['label'] == binary['label'] and item['name'] == binary['name'])
        assert item['sha256'] == binary['sha256']
        with tempfile.TemporaryDirectory(prefix='mixer-root-control-replay-') as temporary:
            path = Path(temporary) / binary['name']
            with tarfile.open(binary_archive) as archive:
                path.write_bytes(archive.extractfile(item['archiveMember']).read())
            path.chmod(0o700)
            assert sha(path) == binary['sha256']
            arguments = [str(path)] + (['experimental::execution::control_probes::'] if private else [])
            output = run('host-private' if private else 'host-public', arguments + ['--nocapture', '--test-threads=1'])
        assert f"test result: ok. {len(binary['executedTests'])} passed; 0 failed; 0 ignored;" in output
        markers = ['control_probe '] if private else ['control_trace ', 'control_warm ', 'control_validation_ceiling ']

        def rows(text):
            return [line[line.index(marker):] for line in text.splitlines()
                    for marker in markers if marker in line]

        expected = rows((folder / (binary['runCommand'] + '.stdout')).read_text())
        assert rows(output) == expected
        assert len(expected) == (17 if private else 795)
        commands[-1].update(binarySHA256=binary['sha256'], tests=len(binary['executedTests']), traceRows=len(expected))
    bind(Path(__file__))
    acceptance = {
        'status': 'accepted-private-literal-control-extraction-host-scope',
        'reviewer': 'root integrator',
        'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'candidateTreeSHA256': summary['candidateTreeSHA256'],
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'pythonVersion': platform.python_version(),
        'decision': 'Accept exact private two-file method extraction and new executable regression tests. Original owner, method bodies, failure/effect order, layout, visibility and reservation remain unchanged.',
        'bindings': bindings, 'commands': commands,
        'publicTestsPerConfiguration': 6, 'controlRowsPerConfiguration': 795,
        'producerConfigurations': 4, 'independentQualifyingBinaries': 44,
        'retainedQualifyingBinaries': len(retained),
        'rootFreshHostTests': 8, 'fixedReservationBytes': 2912,
        'scope': 'Literal frozen SpanInstance extraction only. Swift invocation and active frames remain separate implementation.',
        'fullHistoricalMemoryProof': False, 'swiftExecution': False,
        'nativeRuntime': False, 'physicalRuntime': False, 'gaAcceptance': False
    }
    (HERE / 'acceptance.json').write_text(json.dumps(acceptance, indent=2) + '\n')
    print(json.dumps({k: v for k, v in acceptance.items() if k not in ['bindings', 'commands']}))


if __name__ == '__main__':
    main()
