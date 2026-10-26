from runner import HERE,run,identity
from pathlib import Path
import os,sys,shutil,json,stat

BASE=HERE/'scratch/consumer-debug';SCRATCH=HERE/'scratch'
SENT=SCRATCH/'sentinels';SENT.mkdir(exist_ok=True)
HIT=SCRATCH/'tool-hit'
for name in ['swift','python3','javac','java','xcodebuild']:
    p=SENT/name;p.write_text('#!/bin/sh\nprintf "%s\\n" "$0 $*" >> '+str(HIT)+'\nexit 97\n');p.chmod(0o755)
ENV={'PATH':str(SENT)+os.pathsep+os.environ.get('PATH',''),'MIXER_SWIFT':str(SENT/'swift'),'PYTHONDONTWRITEBYTECODE':'1'}
SKIP={'.build','.git','.swiftpm','node_modules','.gradle','.mixer','target','.DS_Store'}
EXT={'.pem','.key','.p12','.pfx','.mobileprovision','.keystore','.jks'}
REPORT=[]
def digest_tree(root):
    import hashlib
    records=[]
    for base,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=sorted(n for n in dirs if n not in SKIP)
        for name in files:
            p=Path(base)/name;lower=name.lower()
            if name in SKIP or lower=='.env' or (lower.startswith('.env.') and lower!='.env.example') or p.suffix.lower() in EXT:continue
            typ=p.lstat().st_mode
            if stat.S_ISLNK(typ):raise ValueError('independent whole lock refuses symlink')
            if stat.S_ISREG(typ):records.append((p.relative_to(root).as_posix(),identity(p.read_bytes())['sha256']))
        if any((Path(base)/n).is_symlink() for n in dirs):raise ValueError('independent whole lock refuses symlink')
    return hashlib.sha256(''.join(n+'\0'+h+'\n' for n,h in sorted(records)).encode()).hexdigest()
def relock(root):
    lock=json.loads((root/'mixer.lock').read_text());done=True
    try:
        lock['sdkDigest']=digest_tree(root/'Generated/MixerSDK')
        if lock.get('android'):lock['android']['adapterDigest']=digest_tree(root/'Generated/MixerAndroid')
    except ValueError:done=False
    (root/'mixer.lock').write_text(json.dumps(lock,indent=2)+'\n');return done
def fixture(label):
    p=SCRATCH/('fixture-'+label);shutil.copytree(BASE,p);return p
def cleanup(p):
    for base,dirs,files in os.walk(p):
        for n in files:
            q=Path(base)/n
            if not q.is_symlink():q.chmod(0o600)
    shutil.rmtree(p)
def harness(mode):
    root=SCRATCH/'harness-build'
    choices=[root/mode/'ReviewDriver',root/'out/Products'/mode.capitalize()/'ReviewDriver']
    return next(p for p in choices if p.is_file())
def mutate(root,kind):
    sdk=root/'Generated/MixerSDK';adapter=root/'Generated/MixerAndroid';src=sdk/'Sources/MixerUI/AppearanceDefaultV2.swift';asset=adapter/'app/assets/MixerAppearanceV2/descriptor.json'
    if kind.startswith('root:'):(sdk/kind.split(':',1)[1]).write_bytes(b'inert manifest-namespace fixture\n')
    elif kind=='kelvin-base':(sdk/'Package.swift').rename(sdk/'Pac\u212aage.swift')
    elif kind=='unicode-directory':(sdk/'caf\u00e9').mkdir()
    elif kind=='reserved-directory':(sdk/'Package.resolved').mkdir()
    elif kind=='reserved-fifo':os.mkfifo(sdk/'Package@swift-6.4.swift')
    elif kind=='reserved-symlink':(sdk/'Package@swift-6.4.swift').symlink_to('Package.swift')
    elif kind=='manifest-case':(sdk/'Package.swift').rename(sdk/'package.swift')
    elif kind=='source-case':src.rename(src.with_name('appearancedefaultv2.swift'))
    elif kind=='ancestor-case':(sdk/'Sources').rename(sdk/'sources')
    elif kind=='extra-empty':(sdk/'Sources/MixerCore/empty').mkdir()
    elif kind.startswith('extra:'):(sdk/'Sources/MixerCore'/kind.split(':',1)[1]).write_bytes(b'inert extra')
    elif kind=='source-short':src.write_bytes(src.read_bytes()[:-1])
    elif kind=='source-long':src.write_bytes(src.read_bytes()+b' ')
    elif kind=='source-same-length':src.write_bytes(b' '+src.read_bytes()[1:])
    elif kind=='source-missing':src.unlink()
    elif kind=='source-directory':src.unlink();src.mkdir()
    elif kind=='source-fifo':src.unlink();os.mkfifo(src)
    elif kind=='source-symlink':src.unlink();src.symlink_to('AppearanceDefaultV1.swift')
    elif kind=='adapter-empty':(adapter/'Sources/MixerAndroidRuntime/empty').mkdir()
    elif kind=='adapter-drift':p=adapter/'bridge/jni.c';p.write_bytes(p.read_bytes()+b' ')
    elif kind=='asset-drift':asset.write_bytes(b' '+asset.read_bytes()[1:])
    elif kind=='asset-oversize':asset.write_bytes(b' '*65537)
    elif kind=='asset-extra':(asset.parent/'extra.json').write_text('{}')
    elif kind=='asset-case':asset.rename(asset.with_name('Descriptor.json'))
    elif kind=='asset-symlink':asset.unlink();asset.symlink_to('../../../../Package.swift')
    elif kind=='generated-case':(root/'Generated').rename(root/'generated')
    elif kind in ['missing-android','legacy','unknown','mismatch','lock-only','missing-lock','ios-only-request']:
        lock=json.loads((root/'mixer.lock').read_text());config=json.loads((root/'mixer.yml').read_text())
        if kind in ['missing-android','ios-only-request']:lock.pop('android')
        elif kind=='legacy':lock['android'].pop('profile')
        elif kind=='unknown':lock['android']['profile']['id']='unreviewed'
        elif kind=='mismatch':lock['android']['profile']['default_descriptor']['bytes']+=1
        if kind in ['lock-only','ios-only-request']:config['targets']=['ios']
        if kind=='lock-only':asset.write_bytes(b' '+asset.read_bytes()[1:])
        (root/'mixer.lock').write_text(json.dumps(lock));(root/'mixer.yml').write_text(json.dumps(config))
        if kind=='missing-lock':(root/'mixer.lock').unlink()
    else:raise ValueError(kind)

def negative(label,kind,mode,action,driver=False,read_sentinel=False):
    root=fixture(label);HIT.unlink(missing_ok=True);lock_recomputed=False
    try:
        mutate(root,kind)
        if (root/'mixer.lock').is_file():lock_recomputed=relock(root)
        if read_sentinel:
            sentinel=root/'Generated/MixerSDK/ReadOrderingSentinel.txt';sentinel.write_text('generic source reader must fail here if reached')
            lock_recomputed=relock(root);sentinel.chmod(0)
        output=SCRATCH/('export-'+label)
        if driver:argv=[sys.executable,'-B',root/'Generated/MixerAndroid/android-build.py','build',root]
        else:argv=[harness(mode),action,root]+([output] if action=='export' else ['android','build'] if action=='run' else [])
        text=run(label,argv,env=ENV,timeout=20,allowed=(1,23,24))
        assert ('sdk-' in text or 'source compatibility rejected' in text or 'Android SDK source profile' in text or kind=='missing-lock' and 'mixer.lock' in text),text
        assert not HIT.exists(),label+' tool reached'
        assert not output.exists(),label+' export output'
        assert not (root/'.mixer').exists(),label+' build output'
        REPORT.append({'label':label,'kind':kind,'mode':mode,'action':action,'driver':driver,'local_lock_recomputed':lock_recomputed,'read_sentinel':read_sentinel,'tool_sentinel_hit':False,'output_absent':True})
    finally:cleanup(root)

# Self-check read sentinel on the actual host, separate from product assertions.
permission=SCRATCH/'permission-control';permission.write_text('test');permission.chmod(0)
try:
    try:permission.read_bytes();READ_SENTINEL=False
    except PermissionError:READ_SENTINEL=True
finally:permission.chmod(0o600);permission.unlink()
(HERE/'ordering-permission-control.json').write_text(json.dumps({'ordinary_unreadable_file_refuses_read':READ_SENTINEL})+'\n')

for mode in ['debug','release']:
    run('common-positive-'+mode,[harness(mode),'verify',BASE],timeout=20)
    kinds=['root:Package@swift-6.4.swift','root:Pac\u212aage@swift-6.4.swift','kelvin-base','root:caf\u00e9.txt','unicode-directory','manifest-case','ancestor-case','extra-empty','source-long','source-fifo','asset-oversize','missing-android','legacy','unknown','lock-only','missing-lock','ios-only-request']
    for i,kind in enumerate(kinds):
        action=['verify','direct','run','export'][i%4]
        if kind=='ios-only-request':action='required'
        negative(f'swift-{mode}-{i:02}',kind,mode,action,read_sentinel=READ_SENTINEL and kind in ['source-long','asset-oversize'])

kinds=['root:Package@swift-6.4.swift','root:Pac\u212aage@swift-6.4.swift','kelvin-base','root:caf\u00e9.txt','unicode-directory','reserved-directory','reserved-fifo','reserved-symlink','source-case','ancestor-case','extra-empty','extra:.build','extra:.env','extra:key.pem','extra:unknown.txt','source-short','source-long','source-same-length','source-missing','source-directory','source-fifo','source-symlink','adapter-empty','adapter-drift','asset-drift','asset-oversize','asset-extra','asset-case','asset-symlink','generated-case','missing-android','legacy','unknown','mismatch','missing-lock']
for i,kind in enumerate(kinds):negative(f'python-{i:02}',kind,'python','build',driver=True,read_sentinel=READ_SENTINEL and kind in ['source-long','asset-oversize'])

# Matching driver may create output, then must reach only the tool sentinel.
root=fixture('driver-positive');HIT.unlink(missing_ok=True)
try:
    text=run('driver-positive-tool-boundary',[sys.executable,'-B',root/'Generated/MixerAndroid/android-build.py','build',root],env=ENV,timeout=20,allowed=(1,))
    assert HIT.exists() and (root/'.mixer/android-build/build-input.json').is_file()
    REPORT.append({'label':'driver-positive-tool-boundary','tool_sentinel_hit':True,'native_compile_started':False,'output_created_after_admission':True})
finally:cleanup(root)

# Actual CLI creation controls: fixtures never evaluate the unadmitted manifests.
for mode in ['debug','release']:
    for i,kind in enumerate(['root:Package@swift-6.4.swift','root:Pac\u212aage@swift-6.4.swift','kelvin-base','root:caf\u00e9.txt','unicode-directory','extra-empty','source-long']):
        root=fixture('create-'+mode+str(i));dest=SCRATCH/('refused-create-'+mode+str(i));HIT.unlink(missing_ok=True)
        try:
            mutate(root,kind)
            text=run('create-refusal-'+mode+str(i),[HERE/'executables'/('cli-'+mode)/'mixer','create','Rejected','--platform','android','--directory',dest,'--sdk-path',root/'Generated/MixerSDK','--android-adapter-path',HERE/'candidate/native/android'],env=ENV,timeout=20,allowed=(1,))
            assert 'create.android-sdk-compatibility' in text and not dest.exists() and not HIT.exists()
            assert not list(SCRATCH.glob('.mixer-create-*'))
            REPORT.append({'label':'create-refusal-'+mode+str(i),'kind':kind,'mode':mode,'destination_absent':True,'owned_staging_absent':True,'tool_sentinel_hit':False})
        finally:cleanup(root)

(HERE/'independent-entrypoint-results.json').write_text(json.dumps({'schema':1,'checks':REPORT,'count':len(REPORT),'read_sentinel_available':READ_SENTINEL},indent=2)+'\n')
