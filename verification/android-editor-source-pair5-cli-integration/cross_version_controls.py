"""Cross-generation actual-entrypoint controls and stale-driver regression witness."""
import hashlib, importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile, time
HERE=pathlib.Path(__file__).resolve().parent; SOURCE=HERE/'source'; BASE=HERE/'consumers/PairFiveConsumer'
NEW=SOURCE/'.build/out/Products/Debug/mixer'; OLD=HERE/'scratch/old-cli/out/Products/Debug/mixer'; PRE=HERE/'artifacts/pre-driver-guard/mixer'
P4=json.loads((HERE/'inputs/profile4.json').read_text());ROWS=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mod(path):
    spec=importlib.util.spec_from_file_location('crossversion',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def call(args,expected,env,label):
    result=subprocess.run(list(map(str,args)),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
    ROWS.append({'label':label,'command':list(map(str,args)),'returncode':result.returncode,'output':result.stdout,'expected':expected})
    assert result.returncode==1 and expected in result.stdout,ROWS[-1]

def copied(args,root,code,env,label):
    for platform in ['host','ios','android']:
        call([args,'build','--directory',root,'--platform',platform],code,env,label+'-'+platform)
    export=root.parent/'Export';call([args,'export',export,'--directory',root],code,env,label+'-export');assert not export.exists()
    if label != 'old-cli-new-copy':
        call([sys.executable,'-B',root/'Generated/MixerAndroid/android-build.py','build',root], 'source compatibility rejected' if code=='android.sdk-compatibility' else code,env,label+'-direct')
    assert not (root/'.mixer').exists()

with tempfile.TemporaryDirectory(prefix='mixer-cross-version-',dir=HERE) as tmp:
    base=pathlib.Path(tmp);tools=base/'tools';tools.mkdir();sentinel=base/'TOOL-REACHED'
    for name in ['swift','python3']:
        p=tools/name;p.write_text('#!/bin/sh\n/bin/echo '+name+' >> "'+str(sentinel)+'"\nexit 92\n');p.chmod(0o755)
    env=os.environ.copy();env['PATH']=str(tools)+os.pathsep+env.get('PATH','');env['MIXER_SWIFT']=str(tools/'swift')
    old_adapter=base/'OldAdapter'
    for relative,identity in P4['adapter_files'].items():
        actual='engine/'+relative if relative.startswith('Sources/') else relative
        src=HERE/'inputs/old-adapter'/actual
        assert src.stat().st_size==identity['bytes'] and sha(src)==identity['sha256']
        dst=old_adapter/actual;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
    for cli,adapter,label in [(OLD,SOURCE/'native/android','old-cli-new-input'),(NEW,old_adapter,'new-cli-old-input')]:
        target=base/'Created';call([cli,'create','Created','--directory',target,'--platform','android','--sdk-path',SOURCE/'sdk','--android-adapter-path',adapter],'create.android-sdk-compatibility',env,label);assert not target.exists()
    for case in ['old-cli-new-copy','old4-lock','old4-source','unaccepted-views','unaccepted-renderer','missing-editor','stale-driver']:
        root=base/'App';shutil.copytree(BASE,root,ignore=shutil.ignore_patterns('.mixer','.build','.swiftpm'))
        adapter=root/'Generated/MixerAndroid';lock=json.loads((root/'mixer.lock').read_text());module=mod(adapter/'android-build.py')
        code='android.sdk-compatibility';cli=NEW
        if case=='old-cli-new-copy': cli=OLD;code='android.sdk-profile-mismatch'
        elif case=='old4-lock':lock['android']['profile']=module.profile_lock(P4);code='android.sdk-profile-mismatch'
        elif case=='old4-source':
            for name in ['NativeAppearanceViewsV2.java','NativeRenderer.java','NativeCoordinatorV2.java']:
                shutil.copyfile(old_adapter/'app/src/dev/mixer/android'/name,adapter/'app/src/dev/mixer/android'/name)
            (adapter/'app/src/dev/mixer/android/NativeEditorConnectionV2.java').unlink()
        elif case.startswith('unaccepted-'):
            name='NativeAppearanceViewsV2.java' if case.endswith('views') else 'NativeRenderer.java'
            shutil.copyfile(HERE/'inputs'/('unaccepted-'+name),adapter/'app/src/dev/mixer/android'/name)
        elif case=='missing-editor':(adapter/'app/src/dev/mixer/android/NativeEditorConnectionV2.java').unlink()
        elif case=='stale-driver':
            raw=(HERE/'inputs/old4-android-build.py').read_text();(adapter/'android-build.py').write_text(raw.replace('__MIXER_ANDROID_SOURCE_PROFILE_HEX__',json.dumps(P4).encode().hex()))
        lock['android']['adapterDigest']=module.source_tree(adapter);(root/'mixer.lock').write_text(json.dumps(lock))
        if case=='stale-driver':
            # Retained pre-correction exact executable reaches compiler discovery:
            # failure is a required ordering witness, not a source-policy pass.
            call([PRE,'export',base/'PreGuardExport','--directory',root],'lock.toolchain-drift',env,'retained-stale-driver-ordering-failure')
            assert sentinel.exists();trace=sentinel.read_text();sentinel.unlink()
            ROWS[-1]['required_failure_witness']=True;ROWS[-1]['tool_sentinel_trace']=trace;ROWS[-1]['executable_sha256']=sha(PRE)
            # Current CLI must refuse stale bytes before any tool or generic hash.
            for platform in ['host','ios','android']:
                call([NEW,'build','--directory',root,'--platform',platform],code,env,'corrected-stale-driver-'+platform)
            call([NEW,'export',base/'Export','--directory',root],code,env,'corrected-stale-driver-export')
            call([sys.executable,'-B',adapter/'android-build.py','build',root],'android.sdk-profile-mismatch',env,'stale-driver-direct')
        else:copied(cli,root,code,env,case)
        assert not sentinel.exists() and not (root/'.mixer').exists()
        shutil.rmtree(root)
    assert not any(p.name.startswith('.mixer-create-') for p in base.iterdir())
summary={'schema':1,'actual_commands':len(ROWS),'old_cli_sha256':sha(OLD),'new_cli_sha256':sha(NEW),'pre_driver_guard_cli_sha256':sha(PRE),'rows':ROWS,'owned_temporary_cleanup':True,'tool_sentinels_unreached_except_retained_failure':True}
(HERE/'evidence/cross-version-details.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='rows'}))
