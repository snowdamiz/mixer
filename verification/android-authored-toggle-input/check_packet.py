#!/usr/bin/env python3
"""Read-only exact candidate replay. No Git, Android commands, native dispatch, or writes."""
import argparse,gzip,hashlib,json,re,tarfile,zipfile
from pathlib import Path
import build as common

def check(candidate):
    if not re.fullmatch(r'candidate-[1-9][0-9]*',candidate):raise ValueError('contained candidate required')
    folder=common.HERE/candidate
    if common.seal(folder)!=json.loads((folder/'artifact-seal.json').read_text()):raise ValueError('exact attempt seal mismatch')
    r=json.loads((folder/'receipt.json').read_text());lock=json.loads((folder/'source-lock.json').read_text())
    files={str(p.relative_to(folder/'inputs')):common.sha(p) for p in sorted((folder/'inputs').rglob('*')) if p.is_file()}
    closure=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if files!=lock['files'] or closure!=lock['sourceClosureSHA256'] or closure!=r['sourceClosureSHA256']:raise ValueError('source closure mismatch')
    for name,source in common.FIXTURES.items():
        if (folder/'inputs'/source).read_bytes()!=(common.ROOT/'verification/android-pointer-oracle-repair'/name).read_bytes():raise ValueError('frozen original fixture changed')
    old=json.loads((common.BASE/'built-artifacts.json').read_text());new=json.loads((folder/'built-artifacts.json').read_text())
    delta={n for n in set(old)|set(new) if old.get(n)!=new.get(n)}
    if any(not(common.family(n) or n.startswith('dex/') or n=='coordinator-join.apk') for n in delta):raise ValueError('unassigned binary family changed')
    with tarfile.open(folder/'changed-artifacts.tar.gz','r:gz') as archive:
        members=archive.getmembers();expected=delta-{'coordinator-join.apk'}
        if {m.name for m in members}!=expected or len(members)!=len(expected):raise ValueError('exact changed byte inventory mismatch')
        for member in members:
            if not member.isfile() or Path(member.name).is_absolute() or '..' in Path(member.name).parts:raise ValueError('unsafe changed archive')
            data=archive.extractfile(member).read()
            if {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}!=new[member.name]:raise ValueError('changed artifact mismatch')
    apk=Path(r['apk']['path'])
    if common.bind(apk)!={k:r['apk'][k] for k in ('bytes','sha256')}:raise ValueError('retained APK mismatch')
    with zipfile.ZipFile(apk) as archive:
        entries={i.filename:{'bytes':i.file_size,'sha256':hashlib.sha256(archive.read(i.filename)).hexdigest()} for i in archive.infolist()}
    if entries!=json.loads((folder/'apk-entries.json').read_text()):raise ValueError('APK inventory mismatch')
    base_entries=json.loads((common.BASE/'apk-entries.json').read_text())
    if set(entries)!=set(base_entries) or any(not(n.startswith('META-INF/') or n.endswith('.dex')) and entries[n]!=base_entries[n] for n in entries):raise ValueError('baseline fixture/manifest/assets/resource/library changed')
    libraries={n:v for n,v in entries.items() if n.endswith('.so')}
    if len(libraries)!=18:raise ValueError('exact eighteen libraries required')
    guard=common.load('authored_check_packaging',common.ROOT/'verification/android-coordinator-apk-packaging/apk_packaging.py');packaging=guard.validate(apk)
    if packaging!=json.loads((folder/'predispatch-packaging.json').read_text()):raise ValueError('packaging replay mismatch')
    if not r['cleanup']['absent'] or (folder/'.build').exists() or any(c['ownedCommandGroupCleanup']['after'] for c in r['commands']):raise ValueError('cleanup incomplete')
    return {'schema':1,'status':'passed-read-only-production-policy-source-class-APK-replay','candidate':candidate,'sourceInputs':len(files),'sourceClosureSHA256':closure,'apkSHA256':r['apk']['sha256'],'productionPolicyTests':r['productionPolicyTests']['tests'],'changedArtifacts':len(delta),'unchangedNativeSwiftLibraries':18,'nativeRuntime':'NOT RUN','nativeDispatchAuthorized':False,'nativeRunner':'pending root-selected derived wrapper; original timing runner pins candidate-5 and must remain unchanged'}

def supplement(name):
    if not re.fullmatch(r'supplement-[1-9][0-9]*',name):raise ValueError('contained supplement required')
    folder=common.HERE/name
    if common.seal(folder)!=json.loads((folder/'artifact-seal.json').read_text()):raise ValueError('supplement seal mismatch')
    r=json.loads((folder/'receipt.json').read_text());p=Path(r['retainedExecutable']['path'])
    if common.bind(p)!={k:r['retainedExecutable'][k] for k in ('bytes','sha256')}:raise ValueError('compressed supplement drift')
    with gzip.open(p,'rb') as f:data=f.read()
    if {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}!=r['apk']:raise ValueError('exact executable replay mismatch')
    guard=common.load('authored_supplement_check_packaging',common.ROOT/'verification/android-coordinator-apk-packaging/apk_packaging.py')
    if guard.validate(data)!=json.loads((folder/'predispatch-packaging.json').read_text()):raise ValueError('supplement packaging drift')
    return {'status':'passed-read-only-separate-component-APK-replay','apkSHA256':r['apk']['sha256'],'sourceClosureSHA256':r['sourceClosureSHA256'],'nativeRuntime':'NOT RUN','nativeDispatchAuthorized':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--supplement');a=p.parse_args();result=check(a.candidate)
    if a.supplement:result['supplement']=supplement(a.supplement)
    print(json.dumps(result,sort_keys=True,indent=2))
if __name__=='__main__':main()
