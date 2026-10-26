"""Actual CLI optional canonical-only negatives and copied-tree prohibition."""
import importlib.util,json,os,pathlib,shutil,subprocess,sys,tempfile
HERE=pathlib.Path(__file__).resolve().parent;SOURCE=HERE/'source';CLI=SOURCE/'.build/out/Products/Debug/mixer';BASE=HERE/'consumers/PairFiveConsumer';ROWS=[]
NAMES=['AppearanceDescriptorV1.java','AppearanceResolutionV1.java','AdapterInstrumentation.java']
def call(args,code,env):
    p=subprocess.run(list(map(str,args)),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
    ROWS.append({'command':list(map(str,args)),'returncode':p.returncode,'output':p.stdout,'expected':code})
    assert p.returncode==1 and code in p.stdout,ROWS[-1]
with tempfile.TemporaryDirectory(prefix='mixer-optional-actual-',dir=HERE) as temporary:
    base=pathlib.Path(temporary);tools=base/'tools';tools.mkdir();sentinel=base/'TOOL-REACHED'
    for name in ['swift','python3']:
        tool=tools/name;tool.write_text('#!/bin/sh\n/bin/echo invoked >> "'+str(sentinel)+'"\nexit 92\n');tool.chmod(0o755)
    env=os.environ.copy();env['PATH']=str(tools)+os.pathsep+env.get('PATH','');env['MIXER_SWIFT']=str(tools/'swift')
    for name in NAMES:
        for change in ['same-size','append','rename','case','symlink','fifo','directory','extra','zero','short','oversized']:
            adapter=base/'Adapter';shutil.copytree(SOURCE/'native/android',adapter)
            path=adapter/'app/src/dev/mixer/android'/name;raw=path.read_bytes();path.unlink()
            if change=='same-size':path.write_bytes(b'x'*len(raw))
            elif change=='append':path.write_bytes(raw+b' ')
            elif change=='rename':path.with_suffix('.renamed').write_bytes(raw)
            elif change=='case':path.with_name(path.name.lower()).write_bytes(raw)
            elif change=='symlink':path.symlink_to(base/'missing')
            elif change=='fifo':os.mkfifo(path)
            elif change=='directory':path.mkdir()
            elif change=='extra':path.write_bytes(raw);path.with_name('unknown.txt').write_bytes(b'')
            elif change=='zero':path.write_bytes(b'')
            elif change=='short':path.write_bytes(raw[:-1])
            else:path.write_bytes(b'x'*2_000_000)
            target=base/'Created'
            call([CLI,'create','Created','--directory',target,'--platform','android','--sdk-path',SOURCE/'sdk','--android-adapter-path',adapter],'create.android-sdk-compatibility',env)
            assert not target.exists() and not sentinel.exists();shutil.rmtree(adapter)
    for subset in [[n] for n in NAMES]+[NAMES]:
        root=base/'App';shutil.copytree(BASE,root,ignore=shutil.ignore_patterns('.mixer','.build','.swiftpm'));adapter=root/'Generated/MixerAndroid'
        spec=importlib.util.spec_from_file_location('copied_optional',adapter/'android-build.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        for name in subset:shutil.copyfile(SOURCE/'native/android/app/src/dev/mixer/android'/name,adapter/'app/src/dev/mixer/android'/name)
        lock=json.loads((root/'mixer.lock').read_text());lock['android']['adapterDigest']=module.source_tree(adapter);(root/'mixer.lock').write_text(json.dumps(lock))
        (root/'Generated/MixerSDK/GenericHasherSentinel').symlink_to(base/'missing')
        for platform in ['host','ios','android']:call([CLI,'build','--directory',root,'--platform',platform],'android.sdk-compatibility',env)
        call([CLI,'export',base/'Export','--directory',root],'android.sdk-compatibility',env)
        call([sys.executable,'-B',adapter/'android-build.py','build',root],'source compatibility rejected',env)
        assert not sentinel.exists() and not (root/'.mixer').exists() and not (base/'Export').exists();shutil.rmtree(root)
    assert not any(p.name.startswith('.mixer-create-') for p in base.iterdir())
(HERE/'evidence/optional-external-details.json').write_text(json.dumps({'schema':1,'actual_commands':len(ROWS),'tool_sentinel_unreached':True,'owned_temporary_cleanup':True,'rows':ROWS},indent=2)+'\n')
print('Optional input33 + generated-extra20 actual CLI/direct commands pass; no tools/output/staging.')
