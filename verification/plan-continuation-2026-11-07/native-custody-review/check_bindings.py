"""Read-only identities and ZIP contents; no tool or native executable runs."""
from pathlib import Path
import hashlib
import importlib.util
import json
import signal
import sys
import time
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CANDIDATE = HERE.parent / 'native-custody-premise'
START = time.monotonic()
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(RuntimeError('120s binding deadline')))
signal.alarm(120)

def identity(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return {'sha256': digest.hexdigest(), 'bytes': path.stat().st_size}

def require(value, label):
    if not value:
        raise RuntimeError(label)

def read(name):
    return json.loads((CANDIDATE / name).read_text())

checked = {}
for name, expected in read('final-tested-hashes.json').items():
    actual = identity(expected['path'])
    require(actual == {k: expected[k] for k in ('sha256', 'bytes')}, name)
    checked[name] = actual
packet = read('packet.json')
for key, expected in packet['verification'].items():
    if isinstance(expected, dict) and 'path' in expected and 'sha256' in expected:
        require(identity(expected['path']) == {k: expected[k] for k in ('sha256', 'bytes')}, key)

binding = read('prepared-source-binding.json')
for relative, expected in {**binding['canonicalInputs'], **binding['implementationFiles']}.items():
    require(identity(ROOT / relative) == expected, relative)
spec = importlib.util.spec_from_file_location('binding_checker', ROOT / 'scripts/ci/check-android-generated-java.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
profile = checker.load_profile(ROOT)
inputs = checker.source_inputs(profile)
require(len(inputs) == 101 and inputs == binding['canonicalInputs'], 'source101')
require(checker.source_digest(inputs) == binding['canonicalDigest'], 'canonical digest')
for kind, count in [('sdk', 22), ('adapter', 24)]:
    require(len(profile[kind+'_files']) == count and profile[kind+'_files'] == binding['projections'][kind]['files'], kind)

reuse = read('prepared-native-reuse.json')
for path, expected in reuse['currentToolsEqualOriginalBuildTools'].items():
    require(identity(path) == {k: expected[k] for k in ('sha256', 'bytes')} and str(Path(path).resolve()) == expected['realPath'], path)
for relative, expected in reuse['nativeSourceFiles'].items():
    require(identity(ROOT / relative) == expected, relative)
apk = reuse['retainedAPK']
require(identity(apk['path']) == {k: apk[k] for k in ('sha256', 'bytes')}, 'retained APK')
with zipfile.ZipFile(apk['path']) as archive:
    require({name for name in archive.namelist() if name.startswith('lib/')} == set(reuse['nativeLibraries']), 'native ZIP closure')
    for name, expected in reuse['nativeLibraries'].items():
        data = archive.read(name)
        require({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == expected, name)

host = read('host-controls-optimized.json')
fresh = read('fresh-host-experiments.json')
require(host['status'] == 'passed' and host['tests'] == 26 and host['mode'] == 'optimized', 'host profile')
require(all(row['allTerminalCustody'] and row['scratchRemoved'] and row['hold'] is None for row in host['cleanup']), 'host cleanup')
require(fresh['status'] == 'passed' and len(fresh['experiments']) == 2, 'fresh host')
facts = ('direct_child_reaped', 'stdout_eof', 'stderr_eof', 'owned_group_absent', 'terminal_custody')
for experiment in fresh['experiments']:
    require(experiment['cleanup']['allTerminalCustody'] and experiment['cleanup']['scratchRemoved'] and experiment['cleanup']['hold'] is None, 'fresh cleanup')
    require(all(all(record[fact] for fact in facts) for record in experiment['records']), 'fresh custody facts')
for receipt in (host, fresh):
    require(receipt['controllerSHA256'] == checked['run_native_probe.py']['sha256'], 'controller receipt')
    require(receipt['lifecycleSHA256'] == checked['cleanup_control.py']['sha256'], 'cleanup receipt')
require(not (CANDIDATE / 'runtime-attempt').exists(), 'one-attempt output already exists')
result = {'status': 'passed', 'command': [sys.executable, '-B', str(Path(__file__).resolve())],
          'python': sys.version, 'elapsedSeconds': time.monotonic()-START,
          'sourceCount': len(inputs), 'sourceDigest': checker.source_digest(inputs),
          'sdkCount': 22, 'adapterCount': 24, 'toolIdentities': len(reuse['currentToolsEqualOriginalBuildTools']),
          'nativeSourceIdentities': len(reuse['nativeSourceFiles']), 'nativeLibraryIdentities': len(reuse['nativeLibraries']),
          'instrumentation': identity(ROOT / 'native/android/tests/NativeCoordinatorV2IntegrationInstrumentation.java'),
          'files': checked, 'hostAdmission': identity(CANDIDATE / 'host-controls-optimized.json'),
          'freshHostAdmission': identity(CANDIDATE / 'fresh-host-experiments.json'),
          'scope': 'Read-only hashes and ZIP reads. No tool execution, native test, held process operation or held scratch read.'}
(HERE / 'binding-check.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k: v for k, v in result.items() if k not in ('files','command','python')}))
