#!/usr/bin/env python3
"""Read saved contract evidence; no compiler, guest, extraction or native tools."""
import datetime
import gzip
import hashlib
import json
import platform
import tarfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PACKET = ROOT / 'verification/swift-host-dispatch-contract'
def sha(data): return hashlib.sha256(data).hexdigest()
def read(path): return json.loads(path.read_text())
def encoded(value): return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
def main():
    receipt = read(PACKET / 'receipt.json')
    bindings = {}
    for name, expected in receipt['bindings'].items():
        assert sha((ROOT / name).read_bytes()) == expected, name
        bindings[name] = expected
    archives = {}
    for label, row in receipt['sourceArchives'].items():
        archive = PACKET / (label + '-source.tar.gz')
        assert sha(archive.read_bytes()) == row['archiveSHA256']
        with tarfile.open(archive) as tar:
            members = tar.getmembers()
            assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
            content = {m.name: tar.extractfile(m).read() for m in members}
            assert len(content) == len(members) == row['files']
        manifest = {name: sha(data) for name, data in content.items()}
        assert manifest == read(PACKET / (label + '-source-manifest.json'))
        assert sha(encoded(manifest)) == row['sourceTreeSHA256']
        archives[row['sourceTreeSHA256']] = content
    commands = {}
    for path in sorted((PACKET / 'commands').glob('*/receipt.json')):
        command = read(path); name = path.parent.name
        source = command['sourceTreeSHA256']
        if source:
            assert command['sourceUnchanged'] is True
            manifest = read(path.parent / 'source-manifest.json')
            assert sha(encoded(manifest)) == source
            assert manifest == {key: sha(data) for key, data in archives[source].items()}
        for stream in ['stdout', 'stderr']:
            assert sha(gzip.decompress((path.parent / (stream + '.gz')).read_bytes())) == command[stream + 'SHA256']
        commands[name] = command
        bindings[str(path.relative_to(ROOT))] = sha(path.read_bytes())
    for name in receipt['qualifyingCommands']:
        assert commands[name]['exitCode'] == (101 if name.startswith('negative-final-') else 0)
        if name.startswith('layout-'):
            label = name.split('-')[1]
            assert commands[name]['sourceTreeSHA256'] == receipt['sourceArchives']['metadata-' + label]['sourceTreeSHA256']
    baseline = archives[receipt['baselineSourceClosure']]
    candidate = archives[receipt['candidateSourceClosure']]
    assert set(baseline) == set(candidate)
    changed = [name for name in baseline if baseline[name] != candidate[name]]
    assert changed == ['src/experimental_swift_reactor/frame_operations.rs']
    assert candidate[changed[0]].startswith(baseline[changed[0]])
    assert all((ROOT / 'vm' / name).read_bytes() == data for name, data in baseline.items())
    assert not receipt['hostOperationExecuted'] and not receipt['runtimeAccepted'] and not receipt['gaAcceptance']
    assert receipt['cleanup']['ownedScratchRemoved'] and not Path(receipt['cleanup']['scratch']).exists()
    for path in [PACKET / 'receipt.json', Path(__file__)]:
        bindings[str(path.relative_to(ROOT))] = sha(path.read_bytes())
    result = dict(schema=1, observedUTC=datetime.datetime.now(datetime.UTC).isoformat(),
        status='source-and-saved-compiler-preflight-passed-layout-acceptance-pending',
        command=['python3', '-B', str(Path(__file__).relative_to(ROOT))], pythonVersion=platform.python_version(),
        sourceRevision=receipt['baselineGitRevision'], baselineSourceClosure=receipt['baselineSourceClosure'],
        candidateSourceClosure=receipt['candidateSourceClosure'], producerBindings=len(receipt['bindings']),
        verifiedSourceArchives=len(archives), verifiedCommandReceipts=len(commands), totalRootBindings=len(bindings),
        priorLayoutReceipts=16, priorLayoutsAccepted=False,
        reason='Earlier metadata contexts reused Cargo targets across corrected source variants without exact executable hashes or full unit lists. Fresh source-digest/config/context-isolated replay is required. Producer source manifests match, but that alone cannot prove executable provenance.',
        receiptBindingCorrection='Original seal omitted every receipt.json basename. Root now independently validates and binds every per-command receipt as well as the producer receipt.',
        scope='Uncalled compiler feasibility and original source identity only. H01-H16 runtime, accounting integration, full dispatcher/Swift, Ready/public/native/physical/FieldLog/GA remain pending. Rebase and remeasure after accepted growth before runtime implementation.',
        bindings=bindings)
    (HERE / 'contract-preflight.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ['status','producerBindings','verifiedSourceArchives','verifiedCommandReceipts','totalRootBindings']}))
if __name__ == '__main__': main()
