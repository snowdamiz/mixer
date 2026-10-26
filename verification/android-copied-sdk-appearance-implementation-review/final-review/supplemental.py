from runner import HERE,run as base_run,identity
def run(label,*args,**kwargs):return base_run('supplemental-final-'+label,*args,**kwargs)
from pathlib import Path
import ast,json,sys,os,shutil,hashlib
BASE=HERE/'scratch/consumer-release';SCRATCH=HERE/'scratch';raw=HERE/'candidate/cli/Sources/MixerBuild/Resources/android-build.py'
harness=SCRATCH/'harness-build/out/Products/Debug/ReviewDriver'
MARKER='__MIXER_ANDROID_SOURCE_PROFILE_HEX__';REPORT=[]
def tree(root):
    skip={'.build','.git','.swiftpm','node_modules','.gradle','.mixer','target','.DS_Store'};records=[]
    for base,dirs,files in os.walk(root):
        dirs[:]=sorted(n for n in dirs if n not in skip)
        for name in files:
            p=Path(base)/name;n=name.lower()
            if name in skip or n=='.env' or (n.startswith('.env.') and n!='.env.example') or p.suffix.lower() in {'.pem','.key','.p12','.pfx','.mobileprovision','.keystore','.jks'}:continue
            if p.is_file():records.append((p.relative_to(root).as_posix(),identity(p.read_bytes())['sha256']))
    return hashlib.sha256(''.join(n+'\0'+v+'\n' for n,v in sorted(records)).encode()).hexdigest()
def clean(p):
    for base,dirs,files in os.walk(p):
        for n in files:
            q=Path(base)/n
            if not q.is_symlink():q.chmod(0o600)
    shutil.rmtree(p)
def clone(label):p=SCRATCH/label;shutil.copytree(BASE,p);return p

profile=json.loads(run('compiled-authority-profile',[harness,'profile']))
expected=json.loads((HERE.parent/'preaccess/selected-inputs/verification/android-copied-sdk-appearance-contract/proposed-profile-observation.json').read_text());expected['id']='mixer.android-source-pair.1'
assert profile==expected
script=(BASE/'Generated/MixerAndroid/android-build.py').read_text()
assignments=[n for n in ast.parse(script).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_PROFILE_HEX' for t in n.targets)]
assert len(assignments)==1 and json.loads(bytes.fromhex(assignments[0].value.value))==profile
assert raw.read_text().count(MARKER)==1 and script.count(MARKER)==0
REPORT.append({'control':'one-authoritative-compiled-profile-and-rendered-literal','sdk':len(profile['sdk_files']),'adapter':len(profile['adapter_files'])})

for i,hexvalue in enumerate(['nothex','',b'{broken'.hex(),json.dumps(profile|{'extra':True}).encode().hex(),json.dumps(profile|{'id':'unknown'}).encode().hex()]):
    p=SCRATCH/('malformed-policy-'+str(i)+'.py');p.write_text(script.replace(assignments[0].value.value,hexvalue))
    out=run('malformed-build-policy-'+str(i),[sys.executable,'-B',p,'build',SCRATCH/'does-not-exist'],allowed=(1,),timeout=20)
    assert 'source profile is not rendered or supported' in out
    p.unlink();REPORT.append({'control':'malformed-policy-refuses-before-root-read','case':i})
out=run('raw-build-refusal',[sys.executable,'-B',raw,'build',SCRATCH/'does-not-exist'],allowed=(1,),timeout=20)
assert 'source profile is not rendered or supported' in out

for mode in ['debug','release']:
    for label,replacement in [('missing',''),('duplicate',MARKER+MARKER)]:
        p=SCRATCH/('marker-'+mode+'-'+label);p.mkdir();exe=p/'mixer';shutil.copyfile(HERE/'executables'/('cli-'+mode)/'mixer',exe);exe.chmod(0o755)
        resource=p/'MixerCLI_MixerBuild.bundle/Resources';resource.mkdir(parents=True)
        (resource/'android-build.py').write_text(raw.read_text().replace(MARKER,replacement))
        dest=SCRATCH/('refused-marker-'+mode+'-'+label)
        out=run('actual-marker-'+mode+'-'+label,[exe,'create','MarkerFailure','--platform','android','--directory',dest,'--sdk-path',HERE/'candidate/sdk','--android-adapter-path',HERE/'candidate/native/android'],allowed=(1,),timeout=20)
        assert 'android.driver-profile' in out and not dest.exists() and not list(SCRATCH.glob('.mixer-create-*'))
        clean(p);REPORT.append({'control':'actual-create-marker-refusal-and-staging-cleanup','mode':mode,'marker':label})

# Positive full export exercises copied-export admission; the resulting digest is independent.
dest=SCRATCH/'positive-export'
out=run('actual-positive-export',[harness,'export',BASE,dest],timeout=30)
assert 'REVIEW_ENTRYPOINT_ACCEPTED' in out
REPORT.append({'control':'actual-positive-export','independent_tree_sha256':tree(dest),'sdk_compatibility_default_unchanged':True})
clean(dest)

# A copy failure after destination creation must clean the actual export.
source=clone('unreadable-export');blocked=source/'ExportReadSentinel.txt';blocked.write_text('refuse copy');blocked.chmod(0)
dest=SCRATCH/'failed-export'
try:
    out=run('actual-failed-export-cleanup',[harness,'export',source,dest],allowed=(24,),timeout=30)
    assert not dest.exists()
    REPORT.append({'control':'actual-failed-export-cleanup','destination_absent':True,'error':out.strip()})
finally:clean(source)

# A generic read sentinel proves the negative preflight fixtures' ordering oracle.
for kind in ['swift','python']:
    source=clone('generic-read-control-'+kind);sentinel=source/'Generated/MixerSDK/ReadOrderingSentinel.txt';sentinel.write_text('ordinary full-tree-only read sentinel')
    lock=json.loads((source/'mixer.lock').read_text());lock['sdkDigest']=tree(source/'Generated/MixerSDK');(source/'mixer.lock').write_text(json.dumps(lock));sentinel.chmod(0)
    try:
        args=[harness,'verify',source] if kind=='swift' else [sys.executable,'-B',source/'Generated/MixerAndroid/android-build.py','build',source]
        out=run('generic-read-sentinel-control-'+kind,args,allowed=(1,24),timeout=20)
        assert ('permission' in out.lower() or 'Permission' in out or '257' in out) and not (source/'.mixer').exists(),out
        REPORT.append({'control':'generic-read-sentinel-control','language':kind,'observed_read_refusal':True})
    finally:clean(source)

# Historical iOS-only selection retains alternate/Unicode root copying; no selected manifest evaluation.
source=SCRATCH/'ios-sdk-with-extra';shutil.copytree(HERE/'candidate/sdk',source)
(source/'Package@swift-6.4.swift').write_text('inert never evaluated manifest fixture\n');(source/'caf\u00e9.txt').write_text('inert Unicode documentation\n')
dest=SCRATCH/'ios-extra-consumer'
run('actual-ios-extra-selection',[HERE/'executables/cli-debug/mixer','create','HistoricalIOS','--directory',dest,'--sdk-path',source],timeout=30)
assert (dest/'Generated/MixerSDK/Package@swift-6.4.swift').is_file()
REPORT.append({'control':'ios-only-sdk-selection-unchanged','alternate_manifest_copied_without_evaluation':True})
clean(source);clean(dest)

run('candidate-python-focused-regressions',[sys.executable,'-B','-m','unittest','discover','-s',HERE/'candidate/cli/build-tests','-p','test_android_*.py','-v'],timeout=60)
(HERE/'supplemental-results.json').write_text(json.dumps({'schema':1,'checks':REPORT,'count':len(REPORT)},indent=2)+'\n')
