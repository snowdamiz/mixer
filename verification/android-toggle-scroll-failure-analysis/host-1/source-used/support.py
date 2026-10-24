"""Content-bound private diagnostic support. Imports do not dispatch native tools."""
import datetime,gzip,hashlib,importlib.util,json,re,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
REPAIR=ROOT/'verification/android-authored-toggle-supplement-repair'
PACKAGE='dev.mixer.android.authoredtogglescrolldiagnostic'
REPAIR_SEAL='7588daf1c2163657a4d1fe743ccdded8ce1f5a15b023c5413f9da1f049ce7532'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
repair=load('scroll_frozen_repair_support',REPAIR/'support.py')
for _name in ('PRODUCER','RUNNER','BASE','JDK','SDK','BT','JAR','HELPER','owned','sha','data_bind','bind','read','read_bytes','save','now','seal'):
    globals()[_name]=getattr(repair,_name)
def upstream():
    if sha(REPAIR/'packet-seal.json')!=REPAIR_SEAL:raise ValueError('frozen repair seal drift')
    repair.check_packet();parent=repair.frozen()
    return {'repairSeal':bind(REPAIR/'packet-seal.json'),'originalMetadata':parent,'unchangedDependencies':bind(ROOT/'THIRD_PARTY.yml')}
def repair_runner():
    before=sys.modules.get('support')
    try:
        sys.modules['support']=repair;wrapper=load('scroll_frozen_repair_run',REPAIR/'run.py');return wrapper.load_runner()
    finally:
        if before is None:sys.modules.pop('support',None)
        else:sys.modules['support']=before
def candidate():return HERE/read(HERE/'runner-contract.json')['candidate']
def frozen(variant='supplement'):
    prior=upstream()['originalMetadata'];folder=candidate();receipt=read(folder/'receipt.json')
    if read(folder/'artifact-seal.json')!=seal(folder):raise ValueError('scroll diagnostic artifact seal drift')
    inputs={p.name:bind(p) for p in sorted((folder/'source-used').iterdir()) if p.is_file()}
    closure=hashlib.sha256(json.dumps({'productionClosure':prior['productionSourceClosureSHA256'],'supplementInputs':inputs},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    lock=read(folder/'source-lock.json')
    if inputs!=lock['supplementInputs'] or closure!=receipt['sourceClosureSHA256'] or closure!=lock['sourceClosureSHA256']:raise ValueError('scroll source closure drift')
    if receipt['unchangedProductionClasses']!=159 or receipt['unchangedLibraries']!=18 or not receipt['cleanup']['absent']:raise ValueError('composition/cleanup drift')
    for path,binding in receipt['tools'].items():
        if bind(path)!={k:binding[k] for k in ('bytes','sha256')} or str(Path(path).resolve())!=binding['realPath']:raise ValueError('build tool drift '+path)
    with gzip.open(folder/'authored-toggle-supplement.apk.gz','rb') as stream:
        digest=hashlib.sha256();size=0
        while block:=stream.read(1048576):digest.update(block);size+=len(block)
    if {'bytes':size,'sha256':digest.hexdigest()}!=receipt['apk']:raise ValueError('diagnostic APK drift')
    return dict(prior,sourceClosureSHA256=closure,apkSHA256=receipt['apk']['sha256'],debugCertificateSHA256=receipt['debugCertificateSHA256'],packagingPreDispatch=read(folder/'predispatch-packaging.json'),variant='original-protocol-scroll-diagnostic',privatePackage=PACKAGE,repairSourceTree=closure,repairCandidateSeal=bind(folder/'artifact-seal.json'),sourceUnchanged=False)
def inventory(variant='supplement'):
    result={n:v for n,v in repair.inventory().items() if n.startswith('apk/lib/')}
    result.update(read(candidate()/'built-artifacts.json'));result['coordinator-join.apk']=read(candidate()/'receipt.json')['apk']
    return result
def extract(work,variant='supplement'):
    expected=inventory();old=repair.old;base=read(BASE/'built-artifacts.json')
    changed={n:v for n,v in read(old.CANDIDATE/'built-artifacts.json').items() if base.get(n)!=v and n!='coordinator-join.apk'}
    values={n:data for n,data in old.verified_archive(BASE/'built-artifacts.tar.gz',base) if n.startswith(('production-classes/','apk/lib/')) and n not in changed}
    values.update({n:data for n,data in old.verified_archive(old.CANDIDATE/'changed-artifacts.tar.gz',changed) if n.startswith('production-classes/')})
    private={n:v for n,v in read(candidate()/'built-artifacts.json').items() if not n.startswith('production-classes/')}
    values.update(dict(old.verified_archive(candidate()/'supplement-class-dex.tar.gz',private)))
    with gzip.open(candidate()/'authored-toggle-supplement.apk.gz','rb') as stream:values['coordinator-join.apk']=stream.read(expected['coordinator-join.apk']['bytes']+1)
    if {n:data_bind(data) for n,data in values.items()}!=expected:raise ValueError('diagnostic exact payload mismatch')
    for name,data in values.items():
        path=work/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(data)
    return expected
def runtime_directory(attempt):
    if not re.fullmatch(r'runtime-[1-9][0-9]*',attempt):raise ValueError('fresh runtime-N required')
    root=HERE/'runtime';destination=root/attempt
    if HERE.is_symlink() or root.is_symlink():raise ValueError('runtime symlink')
    for path in HERE.rglob('*'):
        if path.is_symlink():raise ValueError('packet symlink')
    if destination.exists() or destination.is_symlink() or destination.resolve().parent!=root.resolve():raise ValueError('fresh contained runtime required')
    return destination
def copy_metadata(out):
    for folder,prefix in ((repair.old.CANDIDATE,'production-build-'),(candidate(),'component-scroll-diagnostic-build-')):
        for name in ('receipt.json','source-lock.json','built-artifacts.json'):(out/(prefix+name)).write_bytes((folder/name).read_bytes())
def packet_files():
    result={}
    for path in sorted(HERE.rglob('*')):
        if path.is_symlink():raise ValueError('packet symlink')
        if path.is_relative_to(HERE/'runtime'):continue
        if path.is_dir() and path.name in ('.build','.scratch','__pycache__'):raise ValueError('owned scratch remains')
        if path.is_file() and path!=HERE/'packet-seal.json':result[str(path.relative_to(ROOT))]=bind(path)
    doc=ROOT/'docs/android-toggle-scroll-failure-analysis.md';result[str(doc.relative_to(ROOT))]=bind(doc);return result
def check_packet():
    packet=read(HERE/'packet-seal.json')
    if packet_files()!=packet['files']:raise ValueError('scroll diagnostic packet seal drift')
    return packet
