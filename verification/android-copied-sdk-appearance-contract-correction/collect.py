#!/usr/bin/env python3
"""Read Git/frozen data and exercise data predicates only; no product imports/tools."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
ACCEPTED = '559858810e133640d52730972a6610e98442be6d'
ORIGINAL = ROOT / 'verification/android-copied-sdk-appearance-contract'
REVIEW = ROOT / 'verification/android-copied-sdk-appearance-contract-review'
COMMANDS = []


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def command(key, argv, output=None):
    started = time.monotonic()
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=20)
    stdout = output or (OUT / 'commands' / (key + '.stdout'))
    stderr = OUT / 'commands' / (key + '.stderr')
    stdout.parent.mkdir(parents=True, exist_ok=True)
    stderr.parent.mkdir(parents=True, exist_ok=True)
    stdout.write_bytes(p.stdout)
    stderr.write_bytes(p.stderr)
    COMMANDS.append({'key': key, 'argv': argv, 'cwd': str(ROOT), 'exit': p.returncode,
                     'seconds': time.monotonic() - started,
                     'stdout': {'path': str(stdout.relative_to(OUT)), **identity(p.stdout)},
                     'stderr': {'path': str(stderr.relative_to(OUT)), **identity(p.stderr)}})
    dump('commands.json', COMMANDS)
    if p.returncode:
        raise RuntimeError('Read/data command failed: ' + key)
    return p.stdout


def check_seal(packet, expected):
    raw = (packet / 'seal.json').read_bytes()
    assert identity(raw)['sha256'] == expected
    seal = json.loads(raw)
    for relative, value in seal['files'].items():
        assert identity((ROOT / relative).read_bytes()) == value, relative
    return {'packet': str(packet.relative_to(ROOT)), 'seal': identity(raw),
            'members': len(seal['files']), 'bytes': sum(v['bytes'] for v in seal['files'].values())}


before_seals = [check_seal(ORIGINAL, 'e08abcacc8421eb2415daa259cf0f9d67a9e2fafa7a879f0b95f574866f62ffb'),
                check_seal(REVIEW, '24d998719e2c5be67fd55a3426340bc8294b07aa78bbf0a8b9ac05bf0de287a9')]
revision = command('revision', ['git', 'rev-parse', 'HEAD']).decode().strip()
assert revision == ACCEPTED
python = command('python-version', [sys.executable, '--version']).decode().strip()
git = command('git-version', ['git', '--version']).decode().strip()
command('accepted-commit', ['git', 'show', '--no-patch', '--format=fuller', ACCEPTED])
old_manifest = json.loads((ORIGINAL / 'source-manifest.json').read_text())
profile = json.loads((ORIGINAL / 'proposed-profile-observation.json').read_text())
acceptance = json.loads((ROOT / 'verification/android-default-appearance-packaging-root-review/acceptance.json').read_text())
assert acceptance['status'] == 'accepted-scoped-default-appearance-packaging'
frozen_packaging = json.loads((ORIGINAL / 'source-inputs/verification/android-default-appearance-packaging/handoff.json').read_text())
paths = sorted(set(old_manifest['sdk_projection'] + old_manifest['adapter_projection'] + acceptance['product_files'] + [
    'cli/Sources/MixerBuild/Configuration.swift', 'cli/Sources/MixerBuild/ProjectGenerator.swift',
    'contracts/ui-v1.json']))
source_files = {}
for index, relative in enumerate(paths):
    data = command('git-source-' + str(index).zfill(2), ['git', 'show', ACCEPTED + ':' + relative], OUT / 'accepted-source' / relative)
    assert identity((ROOT / relative).read_bytes()) == identity(data), 'Live/Git drift: ' + relative
    if relative in old_manifest['sdk_projection'] + old_manifest['adapter_projection']:
        assert identity(data) == old_manifest['files'][relative], 'Original source-map drift: ' + relative
    if relative in acceptance['product_files']:
        assert identity(data) == frozen_packaging['owned_product_files'][relative], 'Frozen packaging product drift: ' + relative
    source_files[relative] = identity(data)
dump('source-manifest.json', {'accepted_git': ACCEPTED, 'files': source_files,
     'sha256': hashlib.sha256(json.dumps(source_files, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
     'sdk_projection': old_manifest['sdk_projection'], 'adapter_projection': old_manifest['adapter_projection']})
inputs = [
    'docs/android-copied-sdk-appearance-contract-review.md',
    'verification/android-copied-sdk-appearance-contract/proposed-profile-observation.json',
    'verification/android-copied-sdk-appearance-contract-review/probe-result.json',
    'verification/android-copied-sdk-appearance-contract-review/handoff.json',
    'verification/android-copied-sdk-appearance-contract-review/commands.json',
    'verification/android-copied-sdk-appearance-contract-review/receipt.json',
    'verification/android-copied-sdk-appearance-contract-review/host-probe/swift-version.stdout',
    'verification/android-copied-sdk-appearance-contract-review/host-probe/swift-version.stderr',
    'verification/android-copied-sdk-appearance-contract-review/host-probe/baseline-dump-package.stdout',
    'verification/android-copied-sdk-appearance-contract-review/host-probe/baseline-dump-package.stderr',
    'verification/android-copied-sdk-appearance-contract-review/host-probe/alternate-manifest-dump-package.stdout',
    'verification/android-copied-sdk-appearance-contract-review/host-probe/alternate-manifest-dump-package.stderr',
    'verification/android-copied-sdk-appearance-contract-review/host-probe/alternate-manifest/Package@swift-6.4.swift',
    'verification/android-copied-sdk-appearance-contract-review/host-probe/alternate-manifest/Sources/UnreviewedUI/Unreviewed.swift',
    'verification/android-default-appearance-packaging-root-review/acceptance.json']
input_files = {}
for relative in inputs:
    data = (ROOT / relative).read_bytes()
    target = OUT / 'inputs' / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    input_files[relative] = identity(data)
dump('input-manifest.json', {'files': input_files, 'seals_before': before_seals})
# The two failed exploratory lookups were observed before this collector. Retain
# exact failing argv and diagnostic text without rerunning either failed lookup.
dump('exploratory-lookup-failures.json', [
    {'argv': ['cat', 'verification/android-copied-sdk-appearance-contract-review/result.json'],
     'diagnostic': 'cat: verification/android-copied-sdk-appearance-contract-review/result.json: No such file or directory\n',
     'scope': 'Exploratory path lookup; actual file is probe-result.json; no source change or product command.'},
    {'argv': ['sed', '-n', '1,24p', 'verification/android-default-appearance-packaging-root-review/delivery.json'],
     'diagnostic': 'sed: verification/android-default-appearance-packaging-root-review/delivery.json: No such file or directory\n',
     'scope': 'Exploratory path lookup; bound accepted Git and acceptance.json instead; no source change or product command.'}])
probe = json.loads(command('data-probe', [sys.executable, '-B', str(OUT / 'data_probe.py')]))
after_seals = [check_seal(ORIGINAL, before_seals[0]['seal']['sha256']), check_seal(REVIEW, before_seals[1]['seal']['sha256'])]
assert after_seals == before_seals
assert all(identity((ROOT / path).read_bytes()) == value for path, value in source_files.items())
dump('receipt.json', {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
     'status': 'corrected-contract-only-awaiting-independent-review', 'accepted_git': ACCEPTED,
     'collector_command': ['python3', '-B', 'verification/android-copied-sdk-appearance-contract-correction/collect.py'],
     'tools': {'python': python, 'git': git}, 'source_files': len(source_files),
     'source_manifest': identity((OUT / 'source-manifest.json').read_bytes()),
     'source_live_equal_to_accepted_git_and_unchanged': True,
     'original_and_review_immutable': True, 'seals_before_and_after': after_seals,
     'commands': 'commands.json', 'data_probe': probe, 'exploratory_lookup_failures': 'exploratory-lookup-failures.json',
     'implementation_selected': False, 'implementation_accepted': False, 'GA_qualified': False,
     'native_runtime_or_capture_started': False, 'process_discovery': False,
     'product_or_original_harness_imported_or_executed': False, 'source_compiler_invoked': False,
     'whole_build_or_APK_created': False, 'committed_or_pushed': False,
     'cleanup': {'scratch_created': False, 'background_or_native_processes_started': []},
     'scope': 'Source identity at accepted Git, sealed review-data reuse and synthetic name/hex-data predicates only; no implemented admission or execution/ABI/distribution qualification.'})
print(json.dumps({'status': 'corrected-contract-only-awaiting-independent-review', 'source_files': len(source_files),
                  'original_and_review_seals_unchanged': True, 'probe': probe}, indent=2))
