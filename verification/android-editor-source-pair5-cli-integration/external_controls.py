"""Actual CLI and direct rendered-driver negative controls, under owned scratch."""
import hashlib, importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile, time
HERE=pathlib.Path(__file__).resolve().parent
SOURCE=HERE/'source'; CONSUMER=HERE/'consumers/PairFiveConsumer'
CLI=SOURCE/'.build/out/Products/Debug/mixer'
name=sys.argv[1]
rows=[]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,code,env):
    stamp=time.monotonic()
    result=subprocess.run(list(map(str,args)),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
    rows.append({'command':list(map(str,args)),'returncode':result.returncode,'output':result.stdout,'elapsed_seconds':time.monotonic()-stamp,'expected_diagnostic':code})
    assert result.returncode==1 and code in result.stdout,(args,result.stdout)

def load(path):
    spec=importlib.util.spec_from_file_location('direct_negative',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def mutate(path,change):
    data=path.read_bytes();path.unlink()
    if change=='same-size': path.write_bytes(b'x'*len(data))
    elif change=='append': path.write_bytes(data+b' ')
    elif change=='rename': path.with_suffix('.renamed').write_bytes(data)
    elif change=='case': path.with_name(path.name.lower()).write_bytes(data)
    elif change=='symlink': path.symlink_to(path.parent/'missing')
    elif change=='fifo': os.mkfifo(path)
    elif change=='directory':path.mkdir()
    elif change=='extra':path.write_bytes(data);path.with_name('unknown.txt').write_bytes(b'')
    elif change=='oversized':path.write_bytes(b'x'*2_000_000)

with tempfile.TemporaryDirectory(prefix='mixer-actual-',dir=HERE) as scratch:
    base=pathlib.Path(scratch);tools=base/'tools';tools.mkdir(); sentinel=base/'TOOL-REACHED'
    script='#!/bin/sh\n/bin/echo invoked >> "'+str(sentinel)+'"\nexit 92\n'
    for command in ['swift','python3']:
        tool=tools/command;tool.write_text(script);tool.chmod(0o755)
    env=os.environ.copy();env['PATH']=str(tools)+os.pathsep+env.get('PATH','');env['MIXER_SWIFT']=str(tools/'swift')
    for change in ['same-size','append','remove','rename','case','symlink','fifo','directory','extra','oversized']:
        root=base/'App';adapter=base/'Adapter';target=base/'Created';export=base/'Export'
        shutil.copytree(CONSUMER,root,ignore=shutil.ignore_patterns('.mixer','.build','.swiftpm'))
        shutil.copytree(SOURCE/'native/android',adapter)
        driver=load(root/'Generated/MixerAndroid/android-build.py')
        relative='app/src/dev/mixer/android/'+name
        mutate(root/'Generated/MixerAndroid'/relative,change);mutate(adapter/relative,change)
        lock=json.loads((root/'mixer.lock').read_text())
        if change not in ['symlink','fifo','directory']:
            lock['android']['adapterDigest']=driver.source_tree(root/'Generated/MixerAndroid')
            (root/'mixer.lock').write_text(json.dumps(lock))
        # A generic source hasher would hit the excluded root symlink; a source
        # profile error establishes that source admission came first.
        (root/'Generated/MixerSDK/GenericHasherSentinel').symlink_to(base/'missing')
        for platform in ['host','ios','android']:
            run([CLI,'build','--directory',root,'--platform',platform],'android.sdk-compatibility',env)
        run([CLI,'export',export,'--directory',root],'android.sdk-compatibility',env)
        run([CLI,'create','Created','--directory',target,'--application','dev.example.created','--platform','android','--sdk-path',SOURCE/'sdk','--android-adapter-path',adapter],'create.android-sdk-compatibility',env)
        run([sys.executable,'-B',root/'Generated/MixerAndroid/android-build.py','build',root],'source compatibility rejected',env)
        assert not target.exists() and not export.exists() and not (root/'.mixer').exists() and not sentinel.exists()
        assert not any(p.name.startswith('.mixer-create-') for p in base.iterdir())
        shutil.rmtree(root);shutil.rmtree(adapter)
    summary={'schema':1,'source':name,'cases':10,'actual_commands':len(rows),'cli_sha256':sha(CLI),'rows':rows,'tool_sentinel_unreached':not sentinel.exists(),'generic_hasher_sentinel':'excluded SDK root symlink would raise files.symlink after admission','owned_temporary_cleanup':'TemporaryDirectory exits below'}
(HERE/'evidence'/('external-'+name+'-'+sha(CLI)[:12]+'.json')).write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='rows'}))
