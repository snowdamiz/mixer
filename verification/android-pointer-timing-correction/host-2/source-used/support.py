"""Host-only immutable predecessor binding and contained fresh-output policy."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIOR = ROOT / 'verification/android-pointer-oracle-repair'
REVIEW = ROOT / 'verification/android-pointer-oracle-repair-review'
SELECTION = ROOT / 'verification/android-pointer-oracle-root-review/correction-selection.json'
REVIEW_SEAL = 'de633fb09dc23c98e43ef0b125b87754554e4d6089a61ec60067c68529f2cd70'
PRIOR_SEAL = '275e733bbc31262c12bf65402fc12e110a43c9f5d14cb41ad157be7a5d755fd5'
APK = '57e82e4e98cdc61581c0639603ec6efa500a66d8d2754f6b47ece89c8165d714'
ARCHIVE = '847de52459dbe90b8fd5abbe186aaf2f936cce38981cbc28ce86b36bcdc9249b'
CLOSURE = '9082e2de1327bd0784d752db5dfbe4484751d565b3410e01e78664321467f5ce'
CONCRETE = 'bd7cd16883a831aac29fa13d162eabf6fae78c88c6b523919e4d9b38c0103b31'
RUNTIME_POLICY = 'Only verification/android-pointer-timing-correction/runtime/runtime-N is mutable runtime evidence; root dispatch after independent correction acceptance; fresh contained path, no symlinks anywhere; recursive runtime seal keeps nested receipts.'
_PRIOR_MODULES = None

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def bind(path): return {'bytes': Path(path).stat().st_size, 'sha256': sha(path)}
def save(path, value): Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

def prior_modules():
    global _PRIOR_MODULES
    if _PRIOR_MODULES is not None: return _PRIOR_MODULES
    # The reviewed wrapper uses these exact module names. Retain its imports and
    # paths; the correction never rewrites or re-executes transformed source.
    sys.path.insert(0, str(PRIOR)) if str(PRIOR) not in sys.path else None
    common = load('timing_prior_common', PRIOR / 'common.py')
    sys.modules['common'] = common
    old_run = load('timing_prior_run', PRIOR / 'run.py')
    old_check = load('timing_prior_packet', PRIOR / 'check_packet.py')
    sys.modules['check_packet'] = old_check
    _PRIOR_MODULES = (common, old_run, old_check)
    return _PRIOR_MODULES

def upstream():
    if sha(PRIOR / 'packet-seal.json') != PRIOR_SEAL or sha(REVIEW / 'artifact-seal.json') != REVIEW_SEAL:
        raise ValueError('designated immutable predecessor/review seal drift')
    _, _, check = prior_modules()
    producer = check.check()
    reviewed = load('timing_prior_review', REVIEW / 'check_review.py').check()
    if producer['hostFiles'] != 284 or producer['upstream']['candidate4Files'] != 507 or producer['upstream']['reviewFiles'] != 42 or reviewed['files'] != 835:
        raise ValueError('exact prior packet counts required')
    selection = json.loads(SELECTION.read_text())
    if selection['acceptedFindings'] != ['F06', 'F07'] or selection['nativeRuntimeAttempted'] or selection['nativeAccepted'] or len(selection['bindings']) != 1121:
        raise ValueError('root correction selection differs')
    for name, digest in selection['bindings'].items():
        path = ROOT / name
        if path.is_symlink() or not path.is_relative_to(ROOT) or sha(path) != digest:
            raise ValueError('root selection binding drift ' + name)
    return {'producer': producer, 'independentReview': reviewed, 'rootSelection': bind(SELECTION), 'rootSelectionBindings': 1121}

def runtime_directory(attempt):
    if not re.fullmatch(r'runtime-[1-9][0-9]*', attempt): raise ValueError('fresh runtime-N required')
    runtime = HERE / 'runtime'
    if HERE.is_symlink() or runtime.is_symlink() or runtime.resolve() != HERE.resolve() / 'runtime':
        raise ValueError('runtime root symlink or path escape')
    for path in HERE.rglob('*'):
        if path.is_symlink(): raise ValueError('host/runtime symlink refused')
    destination = runtime / attempt
    if destination.exists() or destination.is_symlink() or destination.resolve().parent != runtime.resolve():
        raise ValueError('fresh contained runtime directory required')
    return destination

def files():
    runtime = HERE / 'runtime'
    if HERE.is_symlink() or runtime.is_symlink() or runtime.resolve() != HERE.resolve() / 'runtime':
        raise ValueError('host/runtime path escape or symlink')
    result = []
    for path in sorted(HERE.rglob('*')):
        if path.is_symlink(): raise ValueError('host/runtime symlink refused')
        if path == runtime or path.is_relative_to(runtime): continue
        if path.is_dir() and path.name in ('.build', '.scratch', '__pycache__'):
            raise ValueError('owned scratch remains in host packet')
        if path.is_file() and path != HERE / 'packet-seal.json': result.append(path)
    doc = ROOT / 'docs/android-pointer-timing-correction.md'
    if doc.is_symlink(): raise ValueError('document symlink refused')
    result.append(doc)
    return {str(path.relative_to(ROOT)): bind(path) for path in sorted(result)}
