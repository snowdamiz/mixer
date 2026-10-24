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

def candidate():
    return HERE/read(HERE/'runner-contract.json')['candidate']
def frozen(variant='supplement'):
    prior=upstream()['originalMetadata'];folder=candidate();receipt=read(folder/'receipt.json')
    if read(folder/'artifact-seal.json')!=seal(folder):raise ValueError('repair candidate seal drift')
    inputs={p.name:bind(p) for p in sorted((folder/'source-used').iterdir()) if p.is_file()}
    lock=read(folder/'source-lock.json')
    closure=hashlib.sha256(json.dumps({'productionClosure':prior['productionSourceClosureSHA256'],'supplementInputs':inputs},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if inputs!=lock['supplementInputs'] or closure!=receipt['sourceClosureSHA256'] or closure!=lock['sourceClosureSHA256']:raise ValueError('repair closure drift')
    if receipt['unchangedProductionClasses']!=159 or receipt['unchangedLibraries']!=18 or receipt['supplementClasses']!=5 or not receipt['cleanup']['absent']:raise ValueError('repair composition/cleanup drift')
    for path,binding in receipt['tools'].items():
        if bind(path)!={k:binding[k] for k in ('bytes','sha256')} or str(Path(path).resolve())!=binding['realPath']:raise ValueError('build tool drift '+path)
    import gzip
    with gzip.open(folder/'authored-toggle-supplement.apk.gz','rb') as stream:
        digest=hashlib.sha256();size=0
        while block:=stream.read(1048576):digest.update(block);size+=len(block)
    if {'bytes':size,'sha256':digest.hexdigest()}!=receipt['apk']:raise ValueError('repair executable drift')
    return dict(prior,sourceClosureSHA256=closure,apkSHA256=receipt['apk']['sha256'],debugCertificateSHA256=receipt['debugCertificateSHA256'],packagingPreDispatch=read(folder/'predispatch-packaging.json'),variant='isolated-supplement-repair',privatePackage='dev.mixer.android.authoredtogglerepair',repairSourceTree=closure,repairCandidateSeal=bind(folder/'artifact-seal.json'),sourceUnchanged=False)
def inventory(variant='supplement'):
    result={n:v for n,v in old.inventory('supplement').items() if n.startswith('apk/lib/')}
    result.update(read(candidate()/'built-artifacts.json'));result['coordinator-join.apk']=read(candidate()/'receipt.json')['apk']
    if len(result)!=184:raise ValueError('exact184 repaired payload required')
    return result
def extract(work,variant='supplement'):
    import gzip
    expected=inventory();original=old.inventory('supplement')
    base=read(BASE/'built-artifacts.json');changed={n:v for n,v in read(old.CANDIDATE/'built-artifacts.json').items() if base.get(n)!=v and n!='coordinator-join.apk'}
    values={n:data for n,data in old.verified_archive(BASE/'built-artifacts.tar.gz',base) if n.startswith(('production-classes/','apk/lib/')) and n not in changed}
    values.update({n:data for n,data in old.verified_archive(old.CANDIDATE/'changed-artifacts.tar.gz',changed) if n.startswith('production-classes/')})
    private={n:v for n,v in read(candidate()/'built-artifacts.json').items() if not n.startswith('production-classes/')}
    values.update(dict(old.verified_archive(candidate()/'supplement-class-dex.tar.gz',private)))
    with gzip.open(candidate()/'authored-toggle-supplement.apk.gz','rb') as stream:values['coordinator-join.apk']=stream.read(expected['coordinator-join.apk']['bytes']+1)
    if {n:data_bind(data) for n,data in values.items()}!=expected:raise ValueError('repair exact payload mismatch')
    for name,data in values.items():
        path=work/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(data)
    return expected
def runtime_directory(attempt):
    import re
    if not re.fullmatch(r'runtime-[1-9][0-9]*',attempt):raise ValueError('fresh runtime-N required')
    root=HERE/'runtime'
    for path in (HERE,root):
        if path.is_symlink():raise ValueError('runtime symlink')
    for path in HERE.rglob('*'):
        if path.is_symlink():raise ValueError('packet symlink')
    destination=root/attempt
    if destination.exists() or destination.is_symlink() or destination.resolve().parent!=root.resolve():raise ValueError('fresh contained runtime required')
    return destination
def copy_metadata(out):
    for folder,prefix in ((old.CANDIDATE,'production-build-'),(candidate(),'component-repair-build-')):
        for name in ('receipt.json','source-lock.json','built-artifacts.json'):(out/(prefix+name)).write_bytes((folder/name).read_bytes())
def packet_files():
    result={}
    for path in sorted(HERE.rglob('*')):
        if path.is_symlink():raise ValueError('packet symlink')
        if path.is_relative_to(HERE/'runtime'):continue
        if path.is_dir() and path.name in ('.build','.scratch','__pycache__'):raise ValueError('owned scratch remains')
        if path.is_file() and path!=HERE/'packet-seal.json':result[str(path.relative_to(ROOT))]=bind(path)
    document=ROOT/'docs/android-authored-toggle-supplement-repair.md';result[str(document.relative_to(ROOT))]=bind(document)
    return result
def check_packet():
    packet=read(HERE/'packet-seal.json')
    if packet_files()!=packet['files']:raise ValueError('repair packet seal drift')
    return packet
