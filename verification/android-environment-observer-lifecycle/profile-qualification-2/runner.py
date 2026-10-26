#!/usr/bin/env python3
"""Actual CLI creation/export and rendered-driver admission in owned host outputs."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from unittest import mock

ROOT=Path(__file__).resolve().parents[2]
PACKET=Path(__file__).resolve().parent
OUT=PACKET/'profile-qualification-2'
SWIFT=Path('/usr/bin/swift')
ANDROID_SWIFT=Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
PROPOSAL='80eed4b279283d073f745061eb071aff7daa7b4369cbabd9e4b97fab6ff98b8a'

def identity(data): return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def save(path,value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def module(path):
    spec=importlib.util.spec_from_file_location('actual_rendered_observer_driver',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def main():
    assert identity((PACKET/'candidate-proposal.json').read_bytes())['sha256']==PROPOSAL
    admission=json.loads((ROOT/'verification/android-environment-observer-root-review/profile-candidate-admission.json').read_text())
    assert admission['candidate_proposal_sha256']==PROPOSAL and admission['actual_profile_qualification_authorized']
    candidate=json.loads((PACKET/'candidate-proposal.json').read_text())
    for relative,expected in candidate['files'].items(): assert identity((ROOT/relative).read_bytes())==expected,relative
    OUT.mkdir(exist_ok=False)
    (OUT/'runner.py').write_bytes(Path(__file__).read_bytes())
    source=OUT/'source';source.mkdir()
    files=set(candidate['files'])
    for directory in ['cli/Sources','cli/Tests','sdk/Sources','sdk/Tests','updates/Sources']:
        files.update(p.relative_to(ROOT).as_posix() for p in (ROOT/directory).rglob('*') if p.is_file())
    files.update(['cli/Package.swift','cli/Package.resolved','sdk/Package.swift','updates/Package.swift',
        'verification/android-default-appearance-packaging/run-2/created-descriptor.json'])
    bindings={}
    for relative in sorted(files):
        data=(ROOT/relative).read_bytes();target=source/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);bindings[relative]=identity(data)
    save(OUT/'source-freeze.json',{'schema':1,'files':bindings,'projection_sha256':hashlib.sha256(''.join(p+'\0'+bindings[p]['sha256']+'\n' for p in sorted(bindings)).encode()).hexdigest()})
    env=dict(os.environ)
    for name in ('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS','JDK_JAVAC_OPTIONS','CLASSPATH','JAVA_OPTS'):env.pop(name,None)
    env['PATH']=str(SWIFT.parent)+os.pathsep+env['PATH']
    env['MIXER_SWIFT']=str(ANDROID_SWIFT)
    commands=[];cases=[];status='failed';scratch=[]
    def run(label,argv,expected=0,timeout=300):
        argv=[str(p) for p in argv];start=time.time()
        p=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed=False
        try:out,err=p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate()
        (OUT/(label+'.stdout')).write_bytes(out);(OUT/(label+'.stderr')).write_bytes(err)
        commands.append({'label':label,'argv':argv,'cwd':str(ROOT),'exit':p.returncode,'expected_exit':expected,'timed_out':timed,'child_reaped':True,'elapsed_seconds':time.time()-start,'stdout':identity(out),'stderr':identity(err)})
        save(OUT/'commands.json',commands)
        print(label, p.returncode,flush=True)
        if p.returncode!=expected or timed:raise RuntimeError(label+' failed; see retained streams')
        return out,err
    receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python_version':sys.version,
        'argv':[sys.executable,*sys.argv],'candidate_proposal_sha256':PROPOSAL,'admission':identity((ROOT/'verification/android-environment-observer-root-review/profile-candidate-admission.json').read_bytes()),
        'scope':'Actual compiled Swift CLI and its actual rendered driver; host tests only; no native runtime',
        'native_runtime_capture_or_process_discovery':False,'new_dependencies':[],'cases':cases}
    try:
        run('swift-version',[SWIFT,'--version']);run('python-version',[sys.executable,'--version']);run('revision',['git','rev-parse','HEAD'])
        build=OUT/'swift-cli';scratch.append(build)
        run('swift-compatibility-tests',[SWIFT,'test','--package-path',source/'cli','--scratch-path',build,'--disable-automatic-resolution','--filter','androidCompatibility'])
        run('python-compatibility-tests',[sys.executable,'-B',source/'cli/build-tests/test_android_sdk_compatibility.py'])
        cli=build/'debug/mixer';receipt['compiled_cli']=identity(cli.read_bytes())
        app=OUT/'ObserverConsumer'
        run('cli-create',[cli,'create','ObserverConsumer','--directory',app,'--application','dev.mixer.observerconsumer','--platform','android','--sdk-path',source/'sdk','--android-adapter-path',source/'native/android'])
        driver=app/'Generated/MixerAndroid/android-build.py';m=module(driver);profile=m.source_profile()
        assert profile['id']=='mixer.android-source-pair.2'
        assert m.profile_lock(profile)==json.loads((app/'mixer.lock').read_text())['android']['profile']
        assert profile==json.loads((PACKET/'candidate-profile-2.json').read_text())
        assert identity(m.admit_source_pair(app,profile))==profile['default_descriptor']
        cases.append('actual-cli-created-profile2-with-exact42-source-map-and-descriptor')
        exported=OUT/'CopiedConsumer'
        run('cli-export',[cli,'export',exported,'--directory',app])
        assert m.admit_source_pair(exported,profile)==m.admit_source_pair(app,profile)
        cases.append('actual-cli-copied-export-admits-identical-profile2')
        for label,package in [('app-shared-tests',app),('app-owned-session-tests',app/'Platforms/Android')]:
            scratchdir=OUT/(label+'-build');scratch.append(scratchdir)
            run(label,[SWIFT,'test','--package-path',package,'--scratch-path',scratchdir])
        cases.append('ordinary-app-owned-factory-reducer-and-staged-session-host-controls')
        original_lock=json.loads((app/'mixer.lock').read_text())
        old_policy=json.loads((ROOT/'verification/android-owner-effect-contract/inputs/cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').read_text().split('Data(#"""\n',1)[1].split('\n        """#.utf8)',1)[0])
        for name in ['old-profile1','edited-observer','recomputed-locks']:
            rejected=OUT/name;shutil.copytree(exported,rejected)
            lock=json.loads((rejected/'mixer.lock').read_text())
            if name=='old-profile1':
                lock['android']['profile']=m.profile_lock(old_policy)
                shutil.rmtree(rejected/'Generated')
                expected='android.sdk-profile-mismatch'
            else:
                observer=rejected/'Generated/MixerAndroid/app/src/dev/mixer/android/NativeEnvironmentV2.java'
                data=observer.read_bytes();observer.write_bytes(data.replace(b'private long generation = 1;',b'private long generation = 2;'))
                assert len(observer.read_bytes())==len(data)
                if name=='recomputed-locks':
                    lock['sdkDigest']=m.source_tree(rejected/'Generated/MixerSDK')
                    lock['android']['adapterDigest']=m.source_tree(rejected/'Generated/MixerAndroid')
                expected='android.sdk-compatibility'
            (rejected/'mixer.lock').write_text(json.dumps(lock))
            with mock.patch.object(m,'source_tree',side_effect=AssertionError('generic hashing before admission')),mock.patch.object(m,'inspect',side_effect=AssertionError('tools before admission')),mock.patch.object(m,'checked_output',side_effect=AssertionError('output before admission')):
                try:m.build(rejected)
                except RuntimeError as failure:
                    assert ('profile-mismatch' if name=='old-profile1' else 'source compatibility rejected') in str(failure)
                else:raise AssertionError('edited/old source accepted')
            out,err=run(name+'-cli',[cli,'build','--platform','android','--directory',rejected],expected=1)
            assert json.loads(out)['code']==expected,(out,err)
            out,err=run(name+'-driver',[sys.executable,'-B',driver,'build',rejected],expected=1)
            assert ('profile-mismatch' if name=='old-profile1' else 'source compatibility rejected') in err.decode()
            assert not (rejected/'.mixer').exists()
            cases.append(name+'-actual-cli-and-rendered-driver-reject-before-generic-hashing-tools-output')
        with mock.patch.object(m,'SOURCE_PROFILE_HEX',json.dumps(old_policy).encode().hex()),mock.patch.object(m,'read_json',side_effect=AssertionError('lock read before profile rejection')):
            try:m.build(OUT/'absent-root')
            except RuntimeError as failure:assert 'not rendered or supported' in str(failure)
            else:raise AssertionError('profile1 policy accepted by profile2 driver')
        cases.append('profile1-rendered-policy-refused-before-lock-read')
        receipt['project_sources']={}
        for project in [app,exported]:
            receipt['project_sources'][project.name]={'lock':identity((project/'mixer.lock').read_bytes()),'generic_tree_sha256':m.source_tree(project),'driver':identity((project/'Generated/MixerAndroid/android-build.py').read_bytes())}
        save(OUT/'toolchain.json',original_lock['android']['toolchain'])
        save(OUT/'project-source-manifest.json',{p.relative_to(app).as_posix():identity(p.read_bytes()) for p in sorted(app.rglob('*')) if p.is_file() and '.build' not in p.parts and '.swiftpm' not in p.parts})
        for relative,expected in candidate['files'].items():assert identity((ROOT/relative).read_bytes())==expected,'candidate drift '+relative
        status='passed-host-profile2-qualification'
    except BaseException as failure:
        receipt['failure']={'type':type(failure).__name__,'message':str(failure)};raise
    finally:
        removed=[]
        for directory in scratch:
            if directory.exists():shutil.rmtree(directory);removed.append(str(directory))
        receipt.update(status=status,commands='commands.json',cleanup={'owned_build_directories_removed':removed,'owned_children_reaped':all(c['child_reaped'] for c in commands),'native_or_capture_instances_created':False},pending=['Native Android runtime','Public V2/effect-runner integration','Final physical-phone matrix','Immutable published FieldLog packages','Signing/store/operational/GA qualification'])
        save(OUT/'receipt.json',receipt)

if __name__=='__main__':main()
