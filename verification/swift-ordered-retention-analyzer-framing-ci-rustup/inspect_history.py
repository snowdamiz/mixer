"""Read historical source bindings and the first CI failure as immutable data."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
OLD = ROOT / 'verification/swift-ordered-retention-analyzer-framing-ci'
REVISION = '2e4ca9a347f9fe3ff8684b96672723886a7b9fad'
SEAL = '2175ba4d989c42261ae18352305e267c7dd3d7538fb5c8fdb844ea5a6f484ed6'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    require(sha(OLD / 'seal.json') == SEAL, 'Original handoff seal changed')
    rows = json.loads((OLD / 'seal.json').read_text())['members']
    source_snapshots = {
        'scripts/ci/check-analyzer-framing.py': 'check-analyzer-framing.py',
        'scripts/ci/tests/test_analyzer_framing_runner.py': 'test_analyzer_framing_runner.py',
        '.github/workflows/verify.yml': 'verify.yml',
        'docs/swift-ordered-retention-analyzer-framing-ci.md': 'swift-ordered-retention-analyzer-framing-ci.md',
    }
    retained = OWN / 'historical-sources'
    retained.mkdir()
    git_commands, historical_sources = [], {}
    for row in rows:
        if row['path'] in source_snapshots:
            argv = ['git', 'show', REVISION + ':' + row['path']]
            result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=15)
            require(result.returncode == 0, 'Historical Git source unavailable')
            digest = hashlib.sha256(result.stdout).hexdigest()
            require(len(result.stdout) == row['bytes'] and digest == row['sha256'], 'Historical Git source differs')
            snapshot = OLD / 'sources' / source_snapshots[row['path']]
            require(sha(snapshot) == digest, 'Historical retained source differs')
            shutil.copyfile(snapshot, retained / snapshot.name)
            historical_sources[row['path']] = {'revision': REVISION, 'sha256': digest,
                                                'snapshot': str((retained / snapshot.name).relative_to(ROOT))}
            git_commands.append({'argv': argv, 'exit': result.returncode,
                                 'stdout_sha256': digest, 'stderr_sha256': hashlib.sha256(result.stderr).hexdigest()})
        else:
            source = ROOT / row['path']
            require(source.stat().st_size == row['bytes'] and sha(source) == row['sha256'],
                    'Original sealed packet member changed: ' + row['path'])
    require(len(rows) == 108 and len(historical_sources) == 4, 'Original handoff inventory differs')
    for name in ['seal.json', 'seal.sha256']:
        shutil.copyfile(OLD / name, retained / name)
    delivery = ROOT / 'verification/github-delivery-analyzer-contract-ci/remote-framing-1'
    download = json.loads((delivery / 'download-receipt.json').read_text())
    archive = delivery / 'artifact.zip'
    require(sha(archive) == download['archive_sha256'] == '165c0071c73c1fa5c9607a8d7995eabf1833578f3924f005c988806884fc82d3',
            'First CI artifact digest differs')
    first_ci = OWN / 'first-ci'
    first_ci.mkdir()
    shutil.copyfile(archive, first_ci / 'artifact.zip')
    shutil.copyfile(delivery / 'download-receipt.json', first_ci / 'download-receipt.json')
    with zipfile.ZipFile(archive) as compressed:
        names = compressed.namelist()
        require(len(names) == len(set(names)) == 57, 'First CI artifact inventory differs')
        for name in names:
            path = PurePosixPath(name)
            require(not path.is_absolute() and '..' not in path.parts, 'Unsafe archive member')
        receipt = json.loads(compressed.read('receipt.json'))
        require(receipt['result'] == 'failed' and receipt['revision_before'] == REVISION,
                'Unexpected first CI result')
        require(receipt['cleanup']['removed'] and receipt['cleanup']['children_returned_before_cleanup'],
                'First CI cleanup did not complete')
        commands = receipt['commands']
        require(not any(row['name'] in ('test-compile', 'test-execute') for row in commands),
                'First CI ran unexpected test commands')
        require(receipt['rustc_launcher']['resolved_path'] == '/opt/homebrew/Cellar/rustup/1.29.0/bin/rustup-init',
                'Unexpected first CI dispatch target')
        require(receipt['rustc']['version_verbose'].startswith('rustup-init 1.29.0'),
                'Unexpected first CI version identity')
        compile_row = next(row for row in commands if row['name'] == 'library-compile')
        require(compile_row['exit'] == 1, 'Unexpected first CI compile status')
        for name in ['receipt.json', 'commands/rust-version.stdout', 'commands/rust-version.stderr',
                     'commands/rust-version.json', 'commands/library-compile.stdout',
                     'commands/library-compile.stderr', 'commands/library-compile.json']:
            target = first_ci / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(compressed.read(name))
        collector = compressed.read('source/collector.py')
        require(hashlib.sha256(collector).hexdigest() == historical_sources['scripts/ci/check-analyzer-framing.py']['sha256'],
                'First CI executed collector differs from delivered source')
    observed = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
                'python': platform.python_version(), 'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'original_handoff_seal_sha256': SEAL, 'original_handoff_members': len(rows),
                'original_root_sources_verified_through_git_revision': REVISION,
                'historical_source_bindings': historical_sources, 'git_commands': git_commands,
                'first_ci_artifact': {'path': str(archive.relative_to(ROOT)), 'sha256': sha(archive),
                                      'members': len(names), 'executed_as_code': False,
                                      'run': 40244180264, 'result': 'failed-before-Rust-compilation',
                                      'rust_methods_executed': 0, 'cleanup_removed': True,
                                      'download_receipt_sha256': sha(delivery / 'download-receipt.json')},
                'historical_packet_modified': False, 'old_sources_executed': False}
    (OWN / 'history-preflight.json').write_text(json.dumps(observed, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'historical_members_verified': len(rows), 'old_sources_bound_to_git': REVISION,
                      'first_ci': observed['first_ci_artifact']}))


if __name__ == '__main__':
    main()
