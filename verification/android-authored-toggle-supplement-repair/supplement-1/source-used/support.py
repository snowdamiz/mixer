"""Isolated fixture repair support. Imports never dispatch native commands."""
import datetime,hashlib,importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/android-authored-toggle-input';RUNNER=ROOT/'verification/android-authored-toggle-input-runner'
BASE=ROOT/'verification/android-pointer-oracle-repair/candidate-5'
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home');SDK=Path('/opt/homebrew/share/android-commandlinetools');BT=SDK/'build-tools/37.0.0';JAR=SDK/'platforms/android-37.0/android.jar'
HELPER=ROOT/'verification/android-coordinator-runner-cleanup/owned_process.py'
PRODUCER_SEAL='3708eb10fff7634efcf07ba7548efd5301063b7297fa56670ee2ae9b85eff605'
RUNNER_SEAL='c76e70a6d2023aa09f3206b6fe8826983abb354bbad9417ee651f05037f052cc'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def data_bind(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def bind(p):return data_bind(Path(p).read_bytes())
def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate JSON key')
        result[key]=value
    return result
def read(p):return json.loads(Path(p).read_text(),object_pairs_hook=unique)
def read_bytes(data):return json.loads(data,object_pairs_hook=unique)
def save(p,v):Path(p).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
if sha(HELPER)!='209290a7b3638f7510bb1b88dfcdb272f657b89fffe96dcc2f2b631b8f244216':raise ValueError('owned helper drift')
owned=load('repair_owned_process',HELPER)
old=load('repair_frozen_support',RUNNER/'support.py')
def upstream():
    if sha(PRODUCER/'packet-seal.json')!=PRODUCER_SEAL or sha(RUNNER/'packet-seal.json')!=RUNNER_SEAL:raise ValueError('immutable upstream seal drift')
    expected=read(RUNNER/'packet-seal.json')['files']
    if old.files()!=expected or len(expected)!=247:raise ValueError('exact247 frozen runner closure required')
    metadata=old.frozen('supplement')
    return {'producerSeal':bind(PRODUCER/'packet-seal.json'),'frozenRunnerSeal':bind(RUNNER/'packet-seal.json'),'originalMetadata':metadata}
def seal(folder):
    excluded=folder/'artifact-seal.json';result={}
    for p in sorted(folder.rglob('*')):
        if p.is_symlink():raise ValueError('symlink refused '+str(p))
        if p.is_file() and p!=excluded:result[str(p.relative_to(folder))]=bind(p)
    return {'schema':1,'excludedExactPath':str(excluded.relative_to(ROOT)),'files':result}
def old_runner():
    before={n:sys.modules.get(n) for n in ('support','common','check_packet','oracle','run','bounded_output')}
    try:
        sys.modules['support']=old
        wrapper=load('repair_original_wrapper',RUNNER/'run.py')
        return wrapper.load_runner('supplement')
    finally:
        for name,module in before.items():
            if module is None:sys.modules.pop(name,None)
            else:sys.modules[name]=module
