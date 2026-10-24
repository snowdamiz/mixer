"""Content-bound candidate adaptation. Imports and host checks never dispatch native commands."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import stat
import sys
import tarfile
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/android-authored-toggle-input'
CANDIDATE = PRODUCER / 'candidate-3'
SUPPLEMENT = PRODUCER / 'supplement-3'
BASE = ROOT / 'verification/android-pointer-oracle-repair/candidate-5'
TIMING = ROOT / 'verification/android-pointer-timing-correction'
HELPER = ROOT / 'verification/android-coordinator-runner-cleanup/owned_process.py'
HELPER_SHA = '209290a7b3638f7510bb1b88dfcdb272f657b89fffe96dcc2f2b631b8f244216'
CONCRETE = 'bd7cd16883a831aac29fa13d162eabf6fae78c88c6b523919e4d9b38c0103b31'
PRODUCER_SEAL = '3708eb10fff7634efcf07ba7548efd5301063b7297fa56670ee2ae9b85eff605'
CLOSURE = '509ef6a00bbaf034ebbe9dd6d8d3b8716fe96d9600e7fe8fa92fac41ebca3f99'
SUPPLEMENT_CLOSURE = '12fc0156b7689bcf0718c404b80471e707633d93ba44196184fd68b358c5306f'
APK = '24d75ecc19d08f44adc95e2db123936687929ca5a9fcd71f19189865240f6d18'
SUPPLEMENT_APK = '96e9e790e89d8fcc0681499ba7baf4d40af20a432384e720ab43b3d7fbc1189b'
SOURCE_PREFIX = 'native/android/app/src/dev/mixer/android/'
CHANGED = {SOURCE_PREFIX + n + '.java' for n in ('NativeAppearanceViewsV2', 'NativeRenderer')}
ADDED = SOURCE_PREFIX + 'AuthoredToggleInputV2.java'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def data_bind(data): return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
def bind(p): return data_bind(Path(p).read_bytes())
def read(p): return json.loads(Path(p).read_text(), object_pairs_hook=unique)
def read_bytes(data): return json.loads(data, object_pairs_hook=unique)
def save(p, value): Path(p).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result: raise ValueError('duplicate JSON key')
        result[k] = v
    return result

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def exact_seal(folder, name='artifact-seal.json'):
    folder = Path(folder)
    if folder.is_symlink(): raise ValueError('seal root symlink')
    files = {}
    for p in sorted(folder.rglob('*')):
        if p.is_symlink(): raise ValueError('seal symlink')
        if p.is_file() and p != folder / name: files[str(p.relative_to(folder))] = bind(p)
    expected = read(folder / name)
    if 'files' in expected: expected = expected['files']
    if files != expected: raise ValueError('exact recursive seal drift ' + str(folder))
    return {'files': len(files), 'seal': bind(folder / name)}

def prior():
    old_support = load('authored_timing_support', TIMING / 'support.py')
    sys.modules['support'] = old_support
    try: old = load('authored_timing_run', TIMING / 'run.py')
    finally: sys.modules['support'] = sys.modules[__name__]
    runner, source, _ = old.load_runner()
    if hashlib.sha256(source.encode()).hexdigest() != CONCRETE: raise ValueError('prior concrete drift')
    return runner, source

def runtime_directory(attempt):
    if not re.fullmatch(r'runtime-[1-9][0-9]*', attempt): raise ValueError('fresh runtime-N required')
    root = HERE / 'runtime'
    if HERE.is_symlink() or root.is_symlink() or root.resolve() != HERE.resolve() / 'runtime': raise ValueError('runtime escape')
    for p in HERE.rglob('*'):
        if p.is_symlink(): raise ValueError('runtime symlink')
    destination = root / attempt
    if destination.exists() or destination.is_symlink() or destination.resolve().parent != root.resolve(): raise ValueError('fresh contained output required')
    return destination

def source_identity(variant):
    lock = read(CANDIDATE / 'source-lock.json')
    files = {str(p.relative_to(CANDIDATE / 'inputs')): sha(p) for p in sorted((CANDIDATE / 'inputs').rglob('*')) if p.is_file()}
    digest = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if files != lock['files'] or len(files) != 106 or digest != CLOSURE: raise ValueError('106-input candidate closure drift')
    baseline = read(BASE / 'source-lock.json')['files']
    native = {n: v for n, v in baseline.items() if n.startswith(('native/', 'sdk/'))}
    if len(native) != 88: raise ValueError('baseline live count')
    for n, value in native.items():
        p = ROOT / n
        if p.is_symlink() or sha(p) != value: raise ValueError('live baseline changed ' + n)
    if set(files) != set(baseline) | {ADDED}: raise ValueError('unexpected source membership')
    if {n for n in baseline if files[n] != baseline[n]} != CHANGED: raise ValueError('unexpected changed source authority')
    for name in ('CoordinatorJoinActivity.java', 'CoordinatorJoinInstrumentation.java', 'AndroidManifest.xml'):
        a = CANDIDATE / 'inputs/verification/android-coordinator-join' / name
        b = ROOT / 'verification/android-pointer-oracle-repair' / name
        if a.read_bytes() != b.read_bytes(): raise ValueError('baseline fixture changed')
    supplemental = read(SUPPLEMENT / 'source-lock.json')
    inputs = {p.name: bind(p) for p in sorted((SUPPLEMENT / 'source-used').iterdir()) if p.is_file()}
    closure = hashlib.sha256(json.dumps({'productionClosure': CLOSURE, 'supplementInputs': inputs}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if inputs != supplemental['supplementInputs'] or closure != SUPPLEMENT_CLOSURE: raise ValueError('supplement source closure drift')
    return {'sourceInputsRechecked': 106, 'liveBaselineNativeAndSDKInputsRechecked': 88,
            'sourceRevision': read(HERE / 'runner-contract.json')['sourceRevisionContext'],
            'sourceRevisionAuthority': 'contextual root-supplied Git revision; exact source bytes authorized only by sourceTree/sourceClosureSHA256',
            'sourceTree': CLOSURE, 'sourceTreeAlgorithm': 'sha256 canonical 106-input manifest, not a Git tree',
            'sourceClosureSHA256': CLOSURE if variant == 'baseline' else SUPPLEMENT_CLOSURE,
            'productionSourceClosureSHA256': CLOSURE, 'changedProductionInputs': sorted(CHANGED), 'addedProductionInput': ADDED,
            'candidateEqualsLiveProductSource': False,
            'scope': 'three frozen changed/added production inputs; separate unchanged live baseline88 check; unchanged fixture; component supplement has no engine authority' if variant == 'supplement' else 'three frozen changed/added production inputs; separate unchanged live baseline88 check; unchanged20action fixture'}

def frozen(variant='baseline'):
    if sha(PRODUCER / 'packet-seal.json') != PRODUCER_SEAL: raise ValueError('frozen producer top seal drift')
    expected_files = read(PRODUCER / 'packet-seal.json')['files']
    actual_files = {str(p.relative_to(ROOT)): bind(p) for p in PRODUCER.rglob('*') if p.is_file() and p != PRODUCER / 'packet-seal.json'}
    doc = ROOT / 'docs/android-authored-toggle-input-implementation.md'
    actual_files[str(doc.relative_to(ROOT))] = bind(doc)
    if any(p.is_symlink() for p in PRODUCER.rglob('*')) or actual_files != expected_files or len(actual_files) != 555: raise ValueError('exact555 producer files required')
    identity = source_identity(variant)
    folder = CANDIDATE if variant == 'baseline' else SUPPLEMENT
    r = read(folder / 'receipt.json')
    expected = APK if variant == 'baseline' else SUPPLEMENT_APK
    if r['apk']['sha256'] != expected: raise ValueError('selected APK receipt drift')
    if variant == 'baseline':
        if bind(folder / 'coordinator-join.apk') != {k:r['apk'][k] for k in ('bytes','sha256')}: raise ValueError('candidate APK drift')
    else:
        retained = folder / 'authored-toggle-supplement.apk.gz'
        if sha(retained) != '433cd47805a66ac51f194c7507acf6467f36c452f7b8b06f9f771eaeac89127c': raise ValueError('supplement gzip drift')
        with gzip.open(retained, 'rb') as stream:
            h = hashlib.sha256(); size = 0
            while block := stream.read(1048576): h.update(block); size += len(block)
        if {'bytes':size, 'sha256':h.hexdigest()} != r['apk']: raise ValueError('supplement uncompressed drift')
    if sha(HELPER) != HELPER_SHA: raise ValueError('owned helper drift')
    return dict(identity, status='authored-frozen-candidate-ready-runtime-NOT-RUN', sourceUnchanged=False,
                apkSHA256=expected, debugCertificateSHA256=r['debugCertificateSHA256'],
                fixtureSHA256=read(BASE / 'receipt.json')['fixtureSHA256'],
                descriptorSHA256=read(BASE / 'receipt.json')['descriptorSHA256'],
                packagingPreDispatch=read(folder / 'predispatch-packaging.json'),
                producerSeal=bind(PRODUCER / 'packet-seal.json'), variant=variant)

def verified_archive(path, expected):
    with tarfile.open(path, 'r:gz') as archive:
        members = archive.getmembers(); names = [m.name for m in members]
        if len(names) != len(set(names)) or set(names) != set(expected): raise ValueError('exact archive membership required')
        for m in members:
            if not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts: raise ValueError('unsafe archive member')
            if m.size != expected[m.name]['bytes']: raise ValueError('archive size drift')
            data = archive.extractfile(m).read()
            if data_bind(data) != expected[m.name]: raise ValueError('archive content drift')
            yield m.name, data

def inventory(variant):
    candidate = read(CANDIDATE / 'built-artifacts.json')
    if variant == 'baseline': return candidate
    expected = {n:v for n,v in candidate.items() if n.startswith('apk/lib/')}
    expected.update(read(SUPPLEMENT / 'built-artifacts.json'))
    expected['coordinator-join.apk'] = read(SUPPLEMENT / 'receipt.json')['apk']
    if len(expected) != 183: raise ValueError('exact183 component inventory')
    return expected

def extract(work, variant):
    """Assemble exact183 artifacts without mutating producer or duplicating retained APK."""
    base = read(BASE / 'built-artifacts.json'); candidate = read(CANDIDATE / 'built-artifacts.json')
    if len(base) != 179 or len(candidate) != 183: raise ValueError('baseline/candidate archive count drift')
    changed = {n: v for n, v in candidate.items() if base.get(n) != v and n != 'coordinator-join.apk'}
    values = {n: data for n, data in verified_archive(BASE / 'built-artifacts.tar.gz', base) if n in candidate and n not in changed and n != 'coordinator-join.apk'}
    values.update(dict(verified_archive(CANDIDATE / 'changed-artifacts.tar.gz', changed)))
    expected = candidate
    if variant == 'baseline': values['coordinator-join.apk'] = (CANDIDATE / 'coordinator-join.apk').read_bytes()
    else:
        supplement = read(SUPPLEMENT / 'built-artifacts.json')
        private = {n:v for n,v in supplement.items() if not n.startswith('production-classes/')}
        values = {n:v for n,v in values.items() if n.startswith(('production-classes/', 'apk/lib/'))}
        values.update(dict(verified_archive(SUPPLEMENT / 'supplement-class-dex.tar.gz', private)))
        with gzip.open(SUPPLEMENT / 'authored-toggle-supplement.apk.gz', 'rb') as stream: values['coordinator-join.apk'] = stream.read(86206458)
        expected = {n:v for n,v in candidate.items() if n.startswith('apk/lib/')}
        expected.update(supplement); expected['coordinator-join.apk'] = read(SUPPLEMENT / 'receipt.json')['apk']
    if len(values) != 183 or {n:data_bind(d) for n,d in values.items()} != expected: raise ValueError('exact183 artifact payload mismatch')
    for n, data in values.items():
        p = work / n; p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('xb') as stream: stream.write(data)
    return expected

def files():
    runtime = HERE / 'runtime'; result = {}
    for p in sorted(HERE.rglob('*')):
        if p.is_symlink(): raise ValueError('packet symlink')
        if p == runtime or p.is_relative_to(runtime): continue
        if p.is_dir() and p.name in ('.build', '.scratch', '__pycache__'): raise ValueError('owned scratch remains')
        if p.is_file() and p != HERE / 'packet-seal.json': result[str(p.relative_to(ROOT))] = bind(p)
    doc = ROOT / 'docs/android-authored-toggle-input-runner.md'
    if doc.is_symlink(): raise ValueError('document symlink')
    result[str(doc.relative_to(ROOT))] = bind(doc)
    return result


def copy_component_metadata(out):
    for folder, prefix in ((CANDIDATE,'production-build-'),(SUPPLEMENT,'component-build-')):
        for name in ('receipt.json','source-lock.json','built-artifacts.json'):
            (out/(prefix+name)).write_bytes((folder/name).read_bytes())
