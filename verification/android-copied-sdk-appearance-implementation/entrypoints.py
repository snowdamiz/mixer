"""Actual CLI and actual rendered executable admission with tool/output sentinels."""
import hashlib, json, os, pathlib, shutil, sys, tempfile
from run import BASE, run

REPO = BASE.parents[1]
CONSUMER = pathlib.Path('/tmp/mixer-source-pair-consumer-20261026')
REPORT = []
def whole(root):
    # Independent lock recomputation for these ordinary projected fixtures.
    values = []
    skip={'.build','.git','.swiftpm','node_modules','.gradle','.mixer','target','.DS_Store'}
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [x for x in dirs if x not in skip]
        for name in names:
            path=pathlib.Path(directory)/name
            if name in skip or name=='.env' or (name.startswith('.env.') and name!='.env.example') or path.suffix.lower() in {'.pem','.key','.p12','.pfx','.mobileprovision','.keystore','.jks'}: continue
            if path.is_symlink(): continue
            values.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(''.join(p+'\0'+h+'\n' for p,h in sorted(values)).encode()).hexdigest()

def command(label, argv, expected, env):
    code, folder=run(label, argv, 20, env=env)
    output=(folder/'output.txt').read_text()
    assert code != 0 and expected in output, (label, code, output)
    REPORT.append({'label':label,'command_result':str(folder.relative_to(BASE)),'expected':expected,'passed':True})

with tempfile.TemporaryDirectory(prefix='mixer-entrypoints-',dir='/tmp') as tmp:
    base=pathlib.Path(tmp); tools=base/'tools';tools.mkdir()
    sentinel=base/'TOOL-INVOKED'
    for name in ['swift','python3']:
        script=tools/name
        script.write_text('#!/bin/sh\n/usr/bin/touch "'+str(sentinel)+'"\necho TOOL-ORDER-SENTINEL\nexit 99\n');script.chmod(0o755)
    env=os.environ.copy();env['PATH']=str(tools)+os.pathsep+env['PATH'];env['MIXER_SWIFT']=str(tools/'swift')
    for configuration in ['debug','release']:
        cli=REPO/'cli/.build'/configuration/'mixer'
        root=base/configuration;root.mkdir()
        shutil.copytree(CONSUMER/'Generated',root/'Generated')
        shutil.copyfile(CONSUMER/'mixer.yml',root/'mixer.yml')
        (root/'Resources').mkdir()
        baseline=json.loads((CONSUMER/'mixer.lock').read_text())
        def lock():
            value=json.loads(json.dumps(baseline))
            value['sdkDigest']=whole(root/'Generated/MixerSDK');value['android']['adapterDigest']=whole(root/'Generated/MixerAndroid')
            (root/'mixer.lock').write_text(json.dumps(value))
        lock()
        # Matching actual CLI-generated driver must reach the deliberate tool
        # sentinel, after its profile and both recomputed full source locks.
        command(configuration+'-generated-baseline-tool-sentinel',[sys.executable,'-B',str(root/'Generated/MixerAndroid/android-build.py'),'build',str(root)],'exit status 99',env)
        assert sentinel.exists();sentinel.unlink()
        assert (root/'.mixer/android-build/build-input.json').is_file();shutil.rmtree(root/'.mixer')
        names=['Package@swift-6.4.swift','Pac\u212aage.swift','Pac\u212aage@swift-6.4.swift','unrelated-東京']
        for index,name in enumerate(names):
            sdk=root/'Generated/MixerSDK';manifest=(sdk/'Package.swift').read_bytes()
            if name=='Pac\u212aage.swift': (sdk/'Package.swift').unlink()
            item=sdk/name;item.write_bytes(b'unadmitted selector');lock()
            for platform in ['android','host','ios']:
                command(configuration+f'-{index}-run-'+platform,[str(cli),'build','--directory',str(root),'--platform',platform],'android.sdk-compatibility',env)
            output=base/('export-'+configuration+str(index))
            command(configuration+f'-{index}-export',[str(cli),'export',str(output),'--directory',str(root)],'android.sdk-compatibility',env)
            assert not output.exists()
            created=base/('created-'+configuration+str(index))
            command(configuration+f'-{index}-create',[str(cli),'create','Created','--directory',str(created),'--platform','android','--sdk-path',str(sdk),'--android-adapter-path',str(REPO/'native/android')],'create.android-sdk-compatibility',env)
            assert not created.exists()
            command(configuration+f'-{index}-rendered-build',[sys.executable,'-B',str(root/'Generated/MixerAndroid/android-build.py'),'build',str(root)],'source compatibility rejected',env)
            assert not sentinel.exists() and not (root/'.mixer').exists()
            assert not list(base.glob('.mixer-create-*'))
            item.unlink();(sdk/'Package.swift').write_bytes(manifest)
        lock()
        value=json.loads((root/'mixer.lock').read_text());value.pop('android');(root/'mixer.lock').write_text(json.dumps(value))
        command(configuration+'-android-config-missing-lock',[str(cli),'build','--directory',str(root),'--platform','host'],'android.sdk-profile-required',env)
        assert not sentinel.exists()
(BASE/'actual-entrypoint-report.json').write_text(json.dumps({'checks':REPORT,'owned_process_groups_reaped':True,'scratch_removed_after_commands':True},indent=2)+'\n')
print('Actual entrypoint checks:',len(REPORT))
