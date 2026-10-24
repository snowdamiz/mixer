#!/usr/bin/env python3
"""Remove only the successful original coordinator's archived generated scratch."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'verification/android-coordinator-join/candidate-2'
TARGET = BASE / '.build'
sha = lambda b: hashlib.sha256(b).hexdigest()
enc = lambda d: json.dumps(d, sort_keys=True, indent=2) + '\n'


def main():
    assert not (HERE / 'receipt.json').exists(), 'one-time cleanup'
    receipt = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'target': str(TARGET), 'status': 'preflight', 'nativeInstancesStarted': 0,
               'physicalDevicesQueried': False, 'otherProjectsModified': False,
               'failedCandidateOnePreserved': True}
    try:
        assert TARGET.is_dir() and not TARGET.is_symlink()
        stat = TARGET.stat(); receipt.update({'device': stat.st_dev, 'inode': stat.st_ino})
        tracked = subprocess.check_output(['git', 'ls-files', '--', str(TARGET)], cwd=ROOT)
        assert not tracked, 'never remove tracked evidence'
        all_paths = list(TARGET.rglob('*'))
        links = {str(p.relative_to(TARGET)): str(p.readlink()) for p in all_paths if p.is_symlink()}
        assert all((TARGET / p).resolve().is_relative_to(TARGET) for p in links), 'external symlink'
        receipt['internalGeneratedSymlinks'] = links
        files = [p for p in all_paths if p.is_file() and not p.is_symlink()]
        manifest = {str(p.relative_to(TARGET)): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in files}
        (HERE / 'removed-file-manifest.json').write_text(enc(manifest))
        archive = BASE / 'built-artifacts.tar.gz'
        assert sha(archive.read_bytes()) == '642962760271300298db98efd9f2018c159a2e9767843e4ef2bad84d9f824459'
        with tarfile.open(archive) as t:
            members = t.getmembers()
            assert len(members) == 177 and all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
            for m in members:
                assert m.name in manifest and sha(t.extractfile(m).read()) == manifest[m.name]['sha256']
        receipt.update({'archivedArtifactsVerified': 177, 'archiveSHA256': sha(archive.read_bytes()),
                        'files': len(files), 'bytes': sum(x['bytes'] for x in manifest.values()),
                        'unarchivedGeneratedIntermediates': len(files) - 177,
                        'preserved': 'All 177 qualified artifacts in bound archive; source snapshots, logs, receipts and failed candidate-1 scratch remain.'})
        result = subprocess.run(['lsof', '-nP', '+D', str(TARGET)], capture_output=True, timeout=60)
        (HERE / 'open-holders.log').write_bytes(result.stdout + result.stderr)
        receipt.update({'holderCommand': ['lsof', '-nP', '+D', str(TARGET)], 'holderExitCode': result.returncode,
                        'holderOutputEmpty': not result.stdout and not result.stderr})
        assert result.returncode == 1 and not result.stdout and not result.stderr
        assert TARGET.stat().st_dev == stat.st_dev and TARGET.stat().st_ino == stat.st_ino
        assert {str(p.relative_to(TARGET)): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in TARGET.rglob('*') if p.is_file() and not p.is_symlink()} == manifest
        assert {str(p.relative_to(TARGET)): str(p.readlink()) for p in TARGET.rglob('*') if p.is_symlink()} == links
        shutil.rmtree(TARGET)
        assert not TARGET.exists() and sha(archive.read_bytes()) == receipt['archiveSHA256']
        receipt.update({'status': 'owned-generated-scratch-removed-archived-evidence-preserved', 'removed': True})
    except BaseException as error:
        receipt.update({'status': 'failed-preflight-or-cleanup-retained', 'failure': repr(error), 'removed': not TARGET.exists()})
        raise
    finally:
        receipt['finishedUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        receipt['sourceRevision'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        receipt['bindings'] = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in HERE.iterdir() if p.is_file() and p.name != 'receipt.json'}
        (HERE / 'receipt.json').write_text(enc(receipt))
        print(enc(receipt))


if __name__ == '__main__':
    main()
