"""Read-only predecessor binding and private candidate helpers; no target discovery."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/'verification/android-coordinator-apk-packaging/candidate-1'
PARENT=ROOT/'verification/android-coordinator-apk-packaging/run.py'
PARENT_SHA='a1f360bdd1815a76198b3853bc3b1384ff0751e5dd6fc3781bb8d3d85177299e'
EXPECTED_APK='78af8c5df197fb6f163f3010825648a1b1a50427c9ab963b1c5aeca1e513b3ba'
EXPECTED_CLOSURE='00c269c70199ffb376b39394db1c2367f8e9053d92ce6a863741d2a154359c04'
ROOT_REVISION='d4909e275df7e757a5218cc0a88112f4fc3f088b'
OVERLAYS={name:'verification/android-coordinator-join/'+name for name in ('CoordinatorJoinActivity.java','CoordinatorJoinInstrumentation.java','operations.json')}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def accepted():
    if sha(PARENT)!=PARENT_SHA:raise ValueError('accepted packaging wrapper drift')
    adapter=load('pointer_accepted_packaging',PARENT);runner,source,_=adapter.load_runner();receipt=runner.bind_candidate(BASE)
    if receipt['apkSHA256']!=EXPECTED_APK or receipt['sourceClosureSHA256']!=EXPECTED_CLOSURE:raise ValueError('predecessor identity drift')
    acceptance=ROOT/'verification/android-native-input-root-review/contract-acceptance.json'
    contract=json.loads(acceptance.read_text())
    if contract['status']!='accepted-bounded-pointer-contract-for-isolated-fixture-implementation' or contract['nativeRunAuthorizedByThisReceipt'] or contract['productionMutationAuthorized'] or contract['gestureActions']!=20 or contract['maxInjectedMotionEvents']!=320:raise ValueError('root input contract changed')
    for name,value in contract['bindings'].items():
        if sha(ROOT/name)!=value:raise ValueError('root accepted pointer contract binding drift '+name)
    return adapter,runner,source,receipt

def exact_seal(directory,name='artifact-seal.json'):
    directory=Path(directory);exclude=directory/name
    if any(p.is_symlink() for p in directory.rglob('*')):raise ValueError('seal refuses symlink')
    return {str(p.relative_to(directory)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(directory.rglob('*')) if p.is_file() and p!=exclude}

def validate_seal(directory,name='artifact-seal.json'):
    expected=json.loads((Path(directory)/name).read_text())
    if exact_seal(directory,name)!=expected:raise ValueError('exact recursive seal mismatch '+str(directory))

def candidate(built,guard):
    validate_seal(built)
    receipt=json.loads((built/'receipt.json').read_text());locked=json.loads((built/'source-lock.json').read_text())['files']
    if len(locked)!=105 or receipt['sourceClosureSHA256']!=hashlib.sha256(json.dumps(locked,sort_keys=True,separators=(',',':')).encode()).hexdigest():raise ValueError('pointer source closure mismatch')
    for name,value in locked.items():
        if sha(built/'inputs'/name)!=value:raise ValueError('pointer frozen input mismatch '+name)
    artifacts=json.loads((built/'built-artifacts.json').read_text())
    with tarfile.open(built/'built-artifacts.tar.gz','r:gz') as archive:
        members=archive.getmembers();names=[m.name for m in members]
        if len(names)!=len(set(names)) or set(names)!=set(artifacts):raise ValueError('pointer archive membership mismatch')
        for member in members:
            if not member.isfile() or Path(member.name).is_absolute() or '..' in Path(member.name).parts:raise ValueError('unsafe pointer archive member')
        data=archive.extractfile('coordinator-join.apk').read()
    if hashlib.sha256(data).hexdigest()!=receipt['apkSHA256']:raise ValueError('pointer APK mismatch')
    receipt['packagingPreDispatch']=guard.validate(data)
    if receipt['packagingPreDispatch']['nativeLibraries']!=18:raise ValueError('exact eighteen native libraries required')
    return receipt
