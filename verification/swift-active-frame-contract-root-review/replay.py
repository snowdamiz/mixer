#!/usr/bin/env python3
"""Replay the sealed contract's retained host metadata; no frame/guest/native run."""
from pathlib import Path, PurePosixPath
import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/swift-active-frame-contract'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def members(path):
    with tarfile.open(path) as archive:
        result = {}
        for member in archive.getmembers():
            name = PurePosixPath(member.name)
            require(not name.is_absolute() and '..' not in name.parts, 'unsafe archive path')
            require(member.isdir() or member.isfile(), 'unsupported archive member')
            if member.isfile():
                require(member.name not in result, 'duplicate archive member')
                result[member.name] = archive.extractfile(member).read()
        return result


def main():
    require(len(sys.argv) == 2, 'pass the independently observed producer seal SHA256')
    seal_path = PRODUCER / 'seal.json'
    require(sha(seal_path) == sys.argv[1], 'producer seal changed')
    seal = json.loads(seal_path.read_text())
    bindings = dict(seal['bindings'])
    bindings[str(seal_path.relative_to(ROOT))] = sha(seal_path)
    bindings[str(Path(__file__).resolve().relative_to(ROOT))] = sha(Path(__file__))
    for name, expected in bindings.items():
        require(sha(ROOT / name) == expected, 'changed sealed input: ' + name)
    packet = PRODUCER / seal['results']
    receipt = json.loads((packet / 'receipt.json').read_text())
    for flag in ['implementationApplied', 'guestExecution', 'frameExecution',
                 'nativeRuntime', 'semanticAcceptance', 'accountingCompletenessAccepted']:
        require(receipt[flag] is False, 'unexpected producer scope: ' + flag)
    commands = {row['name']: row for row in receipt['commands']}
    require(len(commands) == len(receipt['commands']), 'duplicate command')
    source = json.loads((packet / 'source-manifest.json').read_text())
    archived_source = members(packet / 'source.tar.gz')
    require({name.removeprefix('vm/'): digest(data)
             for name, data in archived_source.items()} == source, 'source archive mismatch')
    require(digest(encoded(source)) == receipt['sourceTreeSHA256'], 'source tree mismatch')
    live_source = {name: sha(ROOT / 'vm' / name) for name in source}
    drift = [name for name in source if source[name] != live_source[name]]
    require(drift == ['tests/span_control_extraction.rs'], 'unexpected production/source drift')
    artifacts = json.loads((packet / 'qualifying-artifacts.json').read_text())
    artifact_path = packet / artifacts['archive']
    require(sha(artifact_path) == artifacts['archiveSHA256'], 'artifact archive changed')
    require(artifact_path.stat().st_size == artifacts['archiveBytes'], 'archive size changed')
    content = members(artifact_path)
    rows = artifacts['artifacts']
    require(len(rows) == 24 and len({row['id'] for row in rows}) == 24, 'artifact closure mismatch')
    require(set(content) == {row['archiveMember'] for row in rows}, 'unlisted/missing artifact')
    layouts = {row['label']: row for row in receipt['layouts']}
    abi = {row['label']: row for row in receipt['abi']}
    require(len(layouts) == 16 and len(abi) == 8, 'wrong compiler artifact matrix')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = HERE / 'results' / stamp
    output.mkdir(parents=True)
    (output / 'live-source-manifest.json').write_bytes(encoded(live_source))
    runs = []
    nm = shutil.which('nm')
    require(nm is not None, 'nm unavailable')
    tools = {'python': {'path': sys.executable, 'version': sys.version, 'sha256': sha(Path(sys.executable))},
             'nm': {'path': nm, 'sha256': sha(Path(nm))}}
    with tempfile.TemporaryDirectory(prefix='mixer-frame-contract-root-') as temp:
        for row in rows:
            data = content[row['archiveMember']]
            require(len(data) == row['bytes'] and digest(data) == row['sha256'], row['id'] + ' bytes changed')
            require(commands[row['buildCommand']]['sourceTreeSHA256'] == row['sourceTreeSHA256'], 'artifact source mismatch')
            binary = Path(temp) / Path(row['archiveMember']).name
            binary.write_bytes(data)
            binary.chmod(0o700)
            if row['kind'] == 'metadata':
                expected = layouts[row['id']]
                require(row['sha256'] == expected['binarySHA256'], 'metadata receipt mismatch')
                original = commands[row['runCommand']]
                arguments = original['argv'][1:]
                if '-unit-' in row['id']:
                    require(arguments == ['experimental_swift_reactor::execution::af_layout_only',
                                          '--exact', '--nocapture', '--test-threads=1'], 'not exact metadata-only test')
                else:
                    require(arguments == [], 'unexpected production metadata arguments')
                argv = [str(binary)] + arguments
            else:
                require(row['kind'] == 'abi-dylib', 'unexpected artifact kind')
                expected = abi[row['id']]
                require(row['sha256'] == expected['binarySHA256'], 'ABI receipt mismatch')
                argv = [nm, '-gU', '-j', str(binary)]
            process = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
            for stream in ['stdout', 'stderr']:
                (output / (row['id'] + '.' + stream)).write_text(getattr(process, stream))
            run = {'id': row['id'], 'argv': argv, 'sourceTreeSHA256': row['sourceTreeSHA256'],
                   'binarySHA256': row['sha256'], 'exitCode': process.returncode}
            for stream in ['stdout', 'stderr']:
                file = output / (row['id'] + '.' + stream)
                run[stream] = str(file.relative_to(ROOT))
                run[stream + 'SHA256'] = sha(file)
            runs.append(run)
            require(process.returncode == 0, row['id'] + ' replay failed')
            if row['kind'] == 'metadata':
                observed = [line[line.index('AF_'):] for line in process.stdout.splitlines() if 'AF_' in line]
                require(observed == expected['records'], row['id'] + ' metadata differs')
            else:
                observed = sorted(line for line in process.stdout.splitlines() if line.startswith('_mixer_'))
                require(observed == expected['exports'], row['id'] + ' exports differ')
    for name, expected in bindings.items():
        require(sha(ROOT / name) == expected, 'input changed during replay: ' + name)
    result = {'status': 'passed-retained-host-metadata-and-abi-replay',
              'scope': 'Contract declarations and metadata only. No active-frame algorithm, guest execution, native runtime or GA acceptance.',
              'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'producerSealSHA256': sys.argv[1], 'producerReceiptSHA256': sha(packet / 'receipt.json'),
              'sourceTreeSHA256': receipt['sourceTreeSHA256'], 'liveDrift': drift,
              'metadataExecutions': 16, 'abiInspections': 8, 'tools': tools, 'commands': runs,
              'bindings': bindings, 'temporaryExtractedArtifactsRemoved': True,
              'frameExecution': False, 'nativeRuntime': False, 'implementationAccepted': False}
    (output / 'receipt.json').write_bytes(encoded(result))
    print(output / 'receipt.json')


if __name__ == '__main__':
    main()
