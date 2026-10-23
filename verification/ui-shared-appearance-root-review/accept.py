#!/usr/bin/env python3
"""Accept only the concrete appearance foundation design and default bytes."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DESIGN = ROOT / 'verification/ui-shared-appearance-contract/v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise RuntimeError(message)


receipt = json.loads((DESIGN / 'receipt.json').read_text())
require(receipt['passed'] is True, 'design collector')
checks = 0
for item in receipt['source_inputs']:
    path = DESIGN / item['snapshot']
    require(path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], 'archived source ' + item['path'])
    checks += 1
for item in receipt['artifacts']:
    path = ROOT / item['path']
    require(path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], 'artifact ' + item['path'])
    checks += 1
commands = []
for name, argv in [
    ('python-version', ['python3', '--version']),
    ('swift-version', ['swift', '--version']),
    ('tests-normal', ['python3', '-m', 'unittest', 'discover', '-s', str(DESIGN), '-p', 'test_descriptor.py']),
    ('tests-optimized', ['python3', '-O', '-m', 'unittest', 'discover', '-s', str(DESIGN), '-p', 'test_descriptor.py']),
    ('declarations', ['swiftc', '-swift-version', '6', '-warnings-as-errors', '-typecheck', str(DESIGN / 'AppearanceV1Declarations.swift')]),
]:
    result = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    log = HERE / (name + '.log')
    log.write_bytes(result.stdout)
    require(result.returncode == 0, name)
    if name.startswith('tests-'):
        require(b'Ran 50 tests' in result.stdout and result.stdout.rstrip().endswith(b'OK'), name + ' count')
    commands.append({'argv': argv, 'cwd': str(ROOT), 'exit_code': result.returncode,
                     'log': str(log.relative_to(ROOT)), 'log_sha256': sha(log)})
default = DESIGN / 'mixer-default-appearance-v1.json'
require(default.stat().st_size == 1906 and sha(default) == 'e94f6988744bde16b83001db8e5047aeac4f15f6b045f99a4660445e7e2062d2', 'single canonical default')
files = {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), DESIGN / 'receipt.json',
    DESIGN / 'foundation-seam.md', DESIGN / 'AppearanceV1Declarations.swift',
    DESIGN / 'descriptor-schema.json', default, ROOT / 'docs/ui-shared-appearance-contract.md']}
acceptance = {
    'observed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'reviewer': 'root integrator', 'accepted': 'pure appearance values, closed canonical codec, integer metric math and exact default data only',
    'source_artifact_bindings': checks, 'files': files, 'commands': commands,
    'implementation_owner_paths': ['sdk/Sources/MixerUI/AppearanceValuesV1.swift',
        'sdk/Sources/MixerUI/AppearanceDescriptorV1.swift', 'sdk/Sources/MixerUI/AppearanceMetricMathV1.swift',
        'sdk/Sources/MixerUI/AppearanceDefaultV1.swift', 'sdk/Tests/MixerUITests/AppearanceV1Tests.swift',
        'verification/ui-appearance-foundation/**'],
    'default_storage': 'Single embedded canonical ASCII byte source in AppearanceDefaultV1.swift; no parallel maintained default tables or Package.swift resource changes. Public mixerDefaultV1 decodes and validates those exact1906 bytes. Later packaging must capture those same emitted bytes.',
    'clarifications': ['Raw constructors do not validate or establish native provenance; every public codec entry validates the complete graph before use.',
        'Canonical and preflight resource bounds apply before allocation/growth, including programmatically oversized arrays/strings. No full oversized serialization before checking the65,536-byte limit.',
        'No production font assets are copied or redistributed. systemSans is the accepted initial data default with platform shaping/parity qualification still pending.',
        'Original17of19 recovered inputs and2hash-only transient status observations are historical; v2 exact36archived inputs are the design basis.'],
    'pending': ['Native style resolver and ten-kind adapter support', 'Apple reference capture before style changes',
        'Android native styling and actual widget consumption', 'Canonical app resource packaging/extraction and real linked index',
        'Private signed installed capture and factory integration', 'Physical parity/accessibility/performance and all GA/dogfood gates'],
    'native_or_release_authority': False,
}
(HERE / 'acceptance.json').write_text(json.dumps(acceptance, indent=2) + '\n')
print(json.dumps({'accepted': acceptance['accepted'], 'bindings': checks, 'commands': len(commands)}))
