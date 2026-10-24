#!/usr/bin/env python3
"""Compile only two private harness sources over the accepted frozen APK; never query a native target."""
import argparse
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import sys
import tarfile
import zipfile
import common

HERE,ROOT,BASE=common.HERE,common.ROOT,common.BASE
SDK=Path('/opt/homebrew/share/android-commandlinetools')
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
BT=SDK/'build-tools/37.0.0';JAR=SDK/'platforms/android-37.0/android.jar'
PREFIXES=('test-classes/dev/mixer/android/CoordinatorJoinActivity','test-classes/dev/mixer/android/CoordinatorJoinInstrumentation')
EXTERNAL=HERE/'retained-apk'

def family(name):return any(name.startswith(p) and (name[len(p):]=='.class' or name[len(p):].startswith('$')) for p in PREFIXES)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--attempt',required=True);args=parser.parse_args()
    if not re.fullmatch(r'candidate-[1-9][0-9]*',args.attempt):parser.error('fresh candidate-N required')
    adapter,runner,_,original=common.accepted()
    guard=common.load('pointer_packaging_guard',ROOT/'verification/android-coordinator-apk-packaging/apk_packaging.py')
    out=HERE/args.attempt;out.mkdir();work=out/'.build';work.mkdir();identity=work.stat();ownership=(identity.st_dev,identity.st_ino)
    commands=[];env=dict(os.environ,JAVA_HOME=str(JDK),PATH=str(JDK/'bin')+os.pathsep+os.environ['PATH'])
    receipt={'schema':1,'status':'building-private-pointer-candidate','commands':commands,'startedUTC':now(),
        'nativeRuntime':'NOT RUN','nativeAcceptance':False,'gaAcceptance':False,'physicalTargetsQueried':False,'nativeInstancesStarted':0,
        'privateKeyRetained':False,'hostLeavesPackaged':False,'compiledMinAPI':36,'sourceSDKTargetTripleAPI':28,'actuallyQualifiedRuntimeAPI':None,
        'immutablePredecessorBindingsRechecked':common.preserved_inputs(),'builderSHA256':common.sha(__file__),'commonSHA256':common.sha(HERE/'common.py'),'packagingValidatorSHA256':common.sha(ROOT/'verification/android-coordinator-apk-packaging/apk_packaging.py'),
        'rootContractAcceptanceSHA256':common.sha(ROOT/'verification/android-native-input-root-review/contract-acceptance.json'),
        'limitations':['host build only; exact pointer native acceptance pending root source/runner/APK review and explicit dispatch','internal callbacks unobserved/null','physical phones disconnected/deferred; native IME/accessibility/public/signed OTA/FieldLog/store/operational/GA pending']}
    def command(name,argv,allowed=(0,)):
        argv=list(map(str,argv));start=now();result=runner.execute(argv,cwd=ROOT,env=env,timeout=180)
        log=out/(name+'.log');log.write_bytes(result.stdout)
        commands.append({'name':name,'argv':argv,'cwd':str(ROOT),'startedUTC':start,'finishedUTC':now(),'exitCode':result.returncode,'output':log.name,'sha256':common.sha(log),'ownedCommandGroupCleanup':result.groupCleanup})
        print(name+': exit '+str(result.returncode),flush=True)
        if result.returncode not in allowed:raise RuntimeError(name+' failed; full output retained')
        return result.stdout.decode(errors='replace').strip()
    try:
        receipt['sourceRevision']=command('source-revision',['git','rev-parse','HEAD'])
        receipt['rootCoordinatedBaselineRevision']=common.ROOT_REVISION
        receipt['sourceTree']=command('source-tree',['git','rev-parse','HEAD^{tree}']);command('source-status',['git','status','--short'])
        base=json.loads((BASE/'source-lock.json').read_text())['files'];locked={}
        for relative,digest in base.items():
            source=BASE/'inputs'/relative
            if common.sha(source)!=digest:raise ValueError('accepted frozen source changed '+relative)
            target=out/'inputs'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
        for filename,relative in common.OVERLAYS.items():
            before=(out/'inputs'/relative).read_text();after=(HERE/filename).read_text();(out/'inputs'/relative).write_text(after)
            (out/(filename+'.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='accepted-packaging/'+relative,tofile='private-pointer/'+relative)))
        locked={name:common.sha(out/'inputs'/name) for name in base};changed=[name for name in base if base[name]!=locked[name]]
        if set(changed)!=set(common.OVERLAYS.values()):raise ValueError('only exact private activity/instrumentation/operation inputs may change')
        for name in base:
            if name.startswith(('native/','sdk/')) and (locked[name]!=base[name] or common.sha(ROOT/name)!=base[name]):raise ValueError('native/SDK input changed '+name)
        closure=hashlib.sha256(json.dumps(locked,sort_keys=True,separators=(',',':')).encode()).hexdigest();receipt['sourceClosureSHA256']=closure
        common.save(out/'source-lock.json',{'sourceRevision':receipt['sourceRevision'],'sourceClosureSHA256':closure,'files':locked})
        common.save(out/'source-delta.json',{'baseCandidate':str(BASE.relative_to(ROOT)),'baseAPK_SHA256':original['apkSHA256'],'baseSourceClosureSHA256':original['sourceClosureSHA256'],'baseInputs':len(base),'changedPrivateInputs':{n:{'before':base[n],'after':locked[n]} for n in changed},'unchangedNativeAndSDKInputs':sum(n.startswith(('native/','sdk/')) for n in base),'unchangedInputs':len(base)-len(changed)})
        prior=json.loads((common.PRIOR/'candidate-4/source-lock.json').read_text())['files']
        delta={n:{'before':prior[n],'after':locked[n]} for n in prior if prior[n]!=locked[n]}
        if set(delta)!={common.OVERLAYS['CoordinatorJoinInstrumentation.java']}:raise ValueError('candidate4-to5 source delta must be private instrumentation timestamps only')
        common.save(out/'candidate4-source-delta.json',{'predecessorSealSHA256':common.PRIOR_SEAL,'predecessorSourceClosureSHA256':'93a7796153dfd94904c28169ab13f66516ad87d6e2341b93e89d51f6eb91efd4','changedInputs':delta,'unchangedInputs':104})
        receipt['fixtureSHA256']=locked[common.OVERLAYS['operations.json']]
        receipt['versions']={name:command(name+'-version',argv) for name,argv in [('python',[sys.executable,'--version']),('java',[JDK/'bin/java','--version']),('javac',[JDK/'bin/javac','--version']),('d8',[BT/'d8','--version']),('apksigner',[BT/'apksigner','version'])]}
        tools=[JDK/'bin/java',JDK/'bin/javac',JDK/'bin/keytool',BT/'d8',BT/'lib/d8.jar',BT/'zipalign',BT/'apksigner',BT/'lib/apksigner.jar',BT/'source.properties',JAR]
        receipt['tools']={str(p):{'sha256':common.sha(p),'bytes':p.stat().st_size,'realPath':str(p.resolve())} for p in tools}
        old=json.loads((BASE/'built-artifacts.json').read_text());old_entries=json.loads((BASE/'apk-entries.json').read_text())
        with tarfile.open(BASE/'built-artifacts.tar.gz','r:gz') as archive:
            members=archive.getmembers();runner.validate_members(members,old);archive.extractall(work,members=members,filter='data')
        for name,value in old.items():
            if common.sha(work/name)!=value['sha256']:raise ValueError('accepted artifact changed '+name)
        apk=work/'coordinator-join.apk'
        if common.sha(apk)!=common.EXPECTED_APK:raise ValueError('accepted APK hash mismatch')
        common.save(out/'base-packaging.json',guard.validate(apk))
        with zipfile.ZipFile(apk) as archive:
            infos=archive.infolist();payloads={i.filename:archive.read(i.filename) for i in infos}
        if set(payloads)!=set(old_entries) or any(hashlib.sha256(data).hexdigest()!=old_entries[name]['sha256'] for name,data in payloads.items()):raise ValueError('accepted APK entries drift')
        removed=[n for n in old if family(n)]
        for name in removed:(work/name).unlink()
        production,tests,dex=(work/name for name in ('production-classes','test-classes','dex'));empty=work/'empty-sourcepath';empty.mkdir()
        command('pointer-private-harness-java17-sdk37',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',os.pathsep.join(map(str,[production,tests,JAR])),'-d',tests,*[out/'inputs'/common.OVERLAYS[n] for n in ('CoordinatorJoinActivity.java','CoordinatorJoinInstrumentation.java')]])
        for path in dex.glob('*.dex'):path.unlink()
        command('joined-dex-min36',[BT/'d8','--min-api','36','--lib',JAR,'--output',dex,*sorted(production.rglob('*.class')),*sorted(tests.rglob('*.class'))])
        unsigned=work/'unsigned.apk'
        with zipfile.ZipFile(unsigned,'w') as archive:
            for info in infos:
                if info.filename.startswith('META-INF/') or info.filename.endswith('.dex'):continue
                info.compress_type=zipfile.ZIP_STORED if info.filename=='resources.arsc' or info.filename.endswith('.so') else info.compress_type
                data=(HERE/'operations.json').read_bytes() if info.filename=='assets/CoordinatorJoin/operations.json' else payloads[info.filename]
                archive.writestr(info,data)
            for path in sorted(dex.glob('*.dex')):archive.write(path,path.name,compress_type=zipfile.ZIP_DEFLATED)
        aligned=work/'aligned.apk';command('private-apk-align-16k',[BT/'zipalign','-f','-P','16','4',unsigned,aligned])
        common.save(out/'pre-sign-packaging.json',guard.validate(aligned));command('pre-sign-official-zipalign',[BT/'zipalign','-c','-P','16','-v','4',aligned])
        key=work/'disposable-debug.keystore'
        try:
            env['MIXER_POINTER_DEBUG_PASS']=secrets.token_urlsafe(32)
            command('disposable-debug-key',[JDK/'bin/keytool','-genkeypair','-keystore',key,'-storepass:env','MIXER_POINTER_DEBUG_PASS','-keypass:env','MIXER_POINTER_DEBUG_PASS','-alias','debug','-keyalg','RSA','-keysize','2048','-validity','30','-dname','CN=Mixer Disposable Actual Pointer Fixture'])
            command('private-debug-apk-sign',[BT/'apksigner','sign','--ks',key,'--ks-pass','env:MIXER_POINTER_DEBUG_PASS','--key-pass','env:MIXER_POINTER_DEBUG_PASS','--out',apk,aligned])
        finally:key.unlink(missing_ok=True);env.pop('MIXER_POINTER_DEBUG_PASS',None)
        cert=command('private-debug-signature-cert',[BT/'apksigner','verify','--verbose','--print-certs',apk]);certs=re.findall(r'certificate SHA-256 digest: ([0-9a-f]{64})',cert)
        if len(certs)!=1:raise ValueError('one disposable debug certificate required')
        common.save(out/'post-sign-packaging.json',guard.validate(apk));command('post-sign-official-zipalign',[BT/'zipalign','-c','-P','16','-v','4',apk])
        artifacts={str(p.relative_to(work)):{'bytes':p.stat().st_size,'sha256':common.sha(p)} for folder in [production,tests,dex,work/'apk/lib/arm64-v8a'] for p in sorted(folder.rglob('*')) if p.is_file()};artifacts['coordinator-join.apk']={'bytes':apk.stat().st_size,'sha256':common.sha(apk)}
        changes={name:{'before':old.get(name),'after':artifacts.get(name)} for name in sorted(set(old)|set(artifacts)) if old.get(name)!=artifacts.get(name)}
        if any(not(family(name) or name.startswith('dex/') or name=='coordinator-join.apk') for name in changes):raise ValueError('production artifact changed')
        with zipfile.ZipFile(apk) as archive:entries={i.filename:{'bytes':i.file_size,'sha256':hashlib.sha256(archive.read(i.filename)).hexdigest()} for i in archive.infolist()}
        entry_changes={name:{'before':old_entries.get(name),'after':entries.get(name)} for name in sorted(set(old_entries)|set(entries)) if old_entries.get(name)!=entries.get(name)}
        if set(entries)!=set(old_entries) or any(not(name.startswith('META-INF/') or name.endswith('.dex') or name=='assets/CoordinatorJoin/operations.json') for name in entry_changes):raise ValueError('unexpected APK entry changes')
        common.save(out/'artifact-delta.json',{'changedPrivateHarnessDexAndAPK':changes,'removedPrivateClassFamilies':removed,'compiledPrivateClassFamilies':[n for n in artifacts if family(n)],'unchangedArtifacts':{n:v for n,v in artifacts.items() if old.get(n)==v}})
        common.save(out/'apk-entry-delta.json',{'changedPrivateFixtureDexOrDebugSignature':entry_changes,'unchangedProductEntries':{n:v for n,v in entries.items() if old_entries.get(n)==v}})
        common.save(out/'apk-entries.json',entries);common.save(out/'built-artifacts.json',artifacts)
        with tarfile.open(out/'built-artifacts.tar.gz','w:gz') as archive:
            for name in sorted(artifacts):archive.add(work/name,arcname=name,recursive=False)
        external=EXTERNAL/(args.attempt+'-'+common.sha(apk));external.mkdir(parents=True);external_apk=external/'coordinator-join.apk';shutil.copyfile(apk,external_apk)
        receipt.update({'apkSHA256':common.sha(apk),'builtArchiveSHA256':common.sha(out/'built-artifacts.tar.gz'),'artifactCount':len(artifacts),'descriptorSHA256':original['descriptorSHA256'],'debugCertificateSHA256':certs[0],
            'coordinatorClassSHA256':original['coordinatorClassSHA256'],'compiledProductionSources':original['compiledProductionSources'],'productionArtifactsRecompiled':0,'productionArtifactsUnchanged':True,
            'changedArtifacts':list(changes),'changedAPKEntries':list(entry_changes),'externalAPK':{'path':str(external_apk),'bytes':external_apk.stat().st_size,'sha256':common.sha(external_apk)},
            'sourceUnchanged':all(common.sha(out/'inputs'/n)==v for n,v in locked.items())})
        common.accepted();receipt['status']='actual-private-apk-built-runtime-NOT-RUN'
    except BaseException as failure:
        receipt.update({'status':'failed-private-pointer-build-retained','failure':repr(failure)});raise
    finally:
        (work/'disposable-debug.keystore').unlink(missing_ok=True)
        empty=work/'empty-sourcepath'
        if empty.is_dir() and not empty.is_symlink() and not list(empty.iterdir()):empty.rmdir()
        expected={str(p.relative_to(work)):{} for p in work.rglob('*') if p.is_file()}
        try:receipt['buildScratchCleanup']=runner.remove_owned_extraction(work,out,expected,ownership)
        except BaseException as failure:receipt.update({'status':'failed-build-scratch-cleanup','buildScratchCleanup':repr(failure)});raise
        finally:receipt['finishedUTC']=now();common.save(out/'receipt.json',receipt);common.save(out/'artifact-seal.json',common.exact_seal(out))

if __name__=='__main__':main()
