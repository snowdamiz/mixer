#!/usr/bin/env python3
"""Independently verify and snapshot only the frozen first-party source closure."""
import hashlib
import io
import json
import pathlib
import subprocess
import tarfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent
PRODUCER = ROOT / 'verification/android-default-appearance-packaging'
EXPECTED = {'handoff.json': 'ddbaabec45eaac4fc8862bec0011f518167919a8032842cb19769e9cd5e76f1d',
            'seal.json': 'e7b005b12e6534db0c32ce213e52b2a20c5313ef744bae0411b6344b6a80941f'}
REVISION = '99d6384306ea17643b70c472f93b57418c674f86'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe(name):
    path = pathlib.PurePosixPath(name)
    assert not path.is_absolute() and '..' not in path.parts and name == path.as_posix(), name
    return path


def files_from_tar(data):
    result = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as archive:
        for member in archive:
            safe(member.name)
            if member.isdir():
                continue
            assert member.isfile() and not member.issym() and not member.islnk(), member.name
            assert member.name not in result and member.size <= 8 * 1024 * 1024, member.name
            assert member.name.startswith(('cli/', 'sdk/', 'updates/', 'native/android/')), member.name
            result[member.name] = archive.extractfile(member).read()
    return result


def main():
    for name, expected in EXPECTED.items():
        assert sha((PRODUCER / name).read_bytes()) == expected, name
    seal = json.loads((PRODUCER / 'seal.json').read_text())
    total = 0
    for name, record in seal['files'].items():
        safe(name)
        data = (PRODUCER / name).read_bytes()
        assert len(data) == record['bytes'] and sha(data) == record['sha256'], name
        total += len(data)
    for name, record in seal['external_owned_files'].items():
        safe(name)
        data = (ROOT / name).read_bytes()
        assert len(data) == record['bytes'] and sha(data) == record['sha256'], name
    for row in (BASE / 'baseline-seal.sha256').read_text().splitlines():
        expected, name = row.split('  ', 1)
        assert sha((ROOT / name).read_bytes()) == expected, name
    archive_data = (PRODUCER / 'product-inputs.tar.gz').read_bytes()
    frozen = files_from_tar(archive_data)
    accepted_command = ['git', 'archive', REVISION, 'cli', 'sdk', 'updates', 'native/android']
    accepted_result = subprocess.run(accepted_command, cwd=ROOT, capture_output=True, timeout=15, check=False)
    assert accepted_result.returncode == 0, accepted_result.stderr.decode()
    accepted = files_from_tar(accepted_result.stdout)
    changed = sorted(name for name in set(accepted) | set(frozen) if accepted.get(name) != frozen.get(name))
    selection = json.loads((BASE / 'implementation-selection.json').read_text())
    assert changed == sorted(selection['owned_product_files']), changed
    for name, record in seal['external_owned_files'].items():
        if name.startswith('cli/'):
            assert sha(frozen[name]) == record['sha256'], name
    target = BASE / 'frozen-source'
    assert not target.exists(), 'Refuse replacing a prior review source snapshot'
    for name, data in frozen.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (BASE / 'producer-handoff.json').write_bytes((PRODUCER / 'handoff.json').read_bytes())
    manifest = {name: {'bytes': len(data), 'sha256': sha(data)} for name, data in sorted(frozen.items())}
    digest = sha(''.join(name + '\0' + row['sha256'] + '\n' for name, row in manifest.items()).encode())
    output = {'schema_version': 1, 'status': 'frozen-handoff-and-scope-verified',
              'producer_handoff_sha256': EXPECTED['handoff.json'], 'producer_seal_sha256': EXPECTED['seal.json'],
              'producer_packet_files_verified': len(seal['files']), 'producer_packet_bytes_verified': total,
              'external_owned_files_verified': len(seal['external_owned_files']),
              'source_archive_sha256': sha(archive_data), 'source_archive_bytes': len(archive_data),
              'accepted_archive_command': accepted_command, 'accepted_archive_sha256': sha(accepted_result.stdout),
              'accepted_revision': REVISION, 'changed_paths': changed,
              'source_files': manifest, 'selected_source_sha256': digest,
              'original_preaccess_seal_verified': True,
              'source_scope': 'Only six selected CLI/test changes versus accepted Git; native/V1/runtime/SDK/updates/ProjectGenerator/ProcessRunner unchanged.',
              'producer_or_product_code_executed': False}
    (BASE / 'handoff-inspection.json').write_text(json.dumps(output, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key: output[key] for key in ['status', 'producer_packet_files_verified',
          'external_owned_files_verified', 'changed_paths', 'selected_source_sha256']}, sort_keys=True))


if __name__ == '__main__':
    main()
