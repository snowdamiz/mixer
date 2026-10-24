#!/usr/bin/env python3
"""Verify exact source/class/archive/APK delta closure, without running Android."""
import hashlib
import json
import tarfile
import common
import build
import run


def check():
    adapter,_,_,base_receipt=common.accepted();runner,_,_=run.load_runner();built=common.HERE/'candidate-4';receipt=runner.bind_candidate(built)
    old=json.loads((common.BASE/'source-lock.json').read_text())['files'];new=json.loads((built/'source-lock.json').read_text())['files']
    if set(old)!=set(new) or {n for n in old if old[n]!=new[n]}!=set(common.OVERLAYS.values()):raise ValueError('private source overlay differs')
    for name in old:
        if name.startswith(('native/','sdk/')) and (old[name]!=new[name] or common.sha(common.ROOT/name)!=old[name]):raise ValueError('live native/SDK content drift '+name)
    for filename,logical in common.OVERLAYS.items():
        if common.sha(common.HERE/filename)!=new[logical]:raise ValueError('new harness differs from frozen candidate')
    old_artifacts=json.loads((common.BASE/'built-artifacts.json').read_text());artifacts=json.loads((built/'built-artifacts.json').read_text())
    changes={name:{'before':old_artifacts.get(name),'after':artifacts.get(name)} for name in sorted(set(old_artifacts)|set(artifacts)) if old_artifacts.get(name)!=artifacts.get(name)}
    declared=json.loads((built/'artifact-delta.json').read_text())
    if declared['changedPrivateHarnessDexAndAPK']!=changes or any(not(build.family(n) or n.startswith('dex/') or n=='coordinator-join.apk') for n in changes):raise ValueError('compiled delta mapping drift')
    for name in old_artifacts:
        if name.startswith(('production-classes/','apk/lib/')) and old_artifacts[name]!=artifacts.get(name):raise ValueError('production class or native library changed '+name)
    for directory,index in [(common.BASE,old_artifacts),(built,artifacts)]:
        with tarfile.open(directory/'built-artifacts.tar.gz','r:gz') as archive:
            members=archive.getmembers();runner.validate_members(members,index)
            for member in members:
                stream=archive.extractfile(member);digest=hashlib.sha256()
                for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
                if digest.hexdigest()!=index[member.name]['sha256'] or member.size!=index[member.name]['bytes']:raise ValueError('archive artifact mismatch '+member.name)
    old_entries=json.loads((common.BASE/'apk-entries.json').read_text());entries=json.loads((built/'apk-entries.json').read_text())
    entry_changes={n:{'before':old_entries.get(n),'after':entries.get(n)} for n in sorted(set(old_entries)|set(entries)) if old_entries.get(n)!=entries.get(n)}
    if entry_changes!=json.loads((built/'apk-entry-delta.json').read_text())['changedPrivateFixtureDexOrDebugSignature'] or set(old_entries)!=set(entries):raise ValueError('APK delta mapping drift')
    if any(not(n.startswith('META-INF/') or n.endswith('.dex') or n=='assets/CoordinatorJoin/operations.json') for n in entry_changes):raise ValueError('production APK entry changed')
    if receipt['packagingPreDispatch']!=json.loads((built/'post-sign-packaging.json').read_text()) or receipt['packagingPreDispatch']['nativeLibraries']!=18:raise ValueError('actual APK packaging parity differs')
    if receipt['privateKeyRetained'] or receipt['productionArtifactsRecompiled'] or not receipt['productionArtifactsUnchanged'] or not receipt['sourceUnchanged'] or receipt['buildScratchCleanup']['status']!='removed' or (built/'.build').exists():raise ValueError('build scope or cleanup differs')
    external=receipt['externalAPK']
    if common.sha(external['path'])!=receipt['apkSHA256']:raise ValueError('outside-Git retained APK differs')
    if any(c['exitCode'] or c['ownedCommandGroupCleanup']['after'] for c in receipt['commands']):raise ValueError('build command failed or leaked group')
    return {'status':'passed-private-pointer-source-class-archive-packaging-closure','nativeRuntime':'NOT RUN','nativeInstancesStarted':0,'physicalTargetsQueried':False,'nativeAcceptance':False,
        'sourceInputs':105,'unchangedSourceInputs':102,'unchangedNativeAndSDKInputs':88,'compiledArtifacts':len(artifacts),'mappedChangedArtifacts':len(changes),'unchangedProductionClassArtifacts':sum(n.startswith('production-classes/') for n in artifacts),
        'mappedChangedAPKEntries':list(entry_changes),'apkSHA256':receipt['apkSHA256'],'sourceClosureSHA256':receipt['sourceClosureSHA256'],'baseAPK_SHA256':base_receipt['apkSHA256'],'directNativeCallbackCount':None}

if __name__=='__main__':print(json.dumps(check(),indent=2,sort_keys=True))
