#!/usr/bin/env python3
"""Independent type-aware archive and exact source audit; no producer execution."""
import difflib, hashlib, io, json, pathlib, stat, tarfile
B=pathlib.Path(__file__).resolve().parent
ROOT=B.parents[1]
P=ROOT/'verification/apple-settings-fixed-chunk-implementation'
sha=lambda data:hashlib.sha256(data).hexdigest()
def save(name,value): (B/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def archive(path):
    result={}; kinds={}; links=[]
    with tarfile.open(path) as tf:
        for member in tf.getmembers():
            name=pathlib.PurePosixPath(member.name)
            assert not name.is_absolute() and '..' not in name.parts and member.name not in result, member.name
            assert member.isfile() or member.isdir() or member.issym(), member.name
            row={'kind':'file' if member.isfile() else 'directory' if member.isdir() else 'symlink','mode':member.mode}
            if member.isfile():
                raw=tf.extractfile(member).read(); row.update(bytes=len(raw),sha256=sha(raw))
            elif member.issym():
                # Record the lexical target only. Never extract or follow it.
                row['target']=member.linkname;links.append({'path':member.name,'target':member.linkname})
            result[member.name]=row;kinds[row['kind']]=kinds.get(row['kind'],0)+1
    return result,kinds,links
def main():
    expected='2d01866f3fa0f88b283ba8f2774f03092eb93d9616daeaa7d5d2875618cf6748'
    assert sha((P/'handoff.json').read_bytes())==expected
    handoff=json.loads((P/'handoff.json').read_bytes())
    for name,row in handoff['members'].items():
        path=ROOT/name; mode=path.lstat().st_mode
        assert stat.S_ISREG(mode) and row['kind']=='file',name
        raw=path.read_bytes(); assert len(raw)==row['bytes'] and sha(raw)==row['sha256'],name
    bindings=json.loads((P/'source-bindings.json').read_bytes())
    for name,digest in bindings['inputs'].items(): assert sha((ROOT/name).read_bytes())==digest
    frozen={}
    for item in bindings['archives']:
        copy=P/'inputs'/('selected-sources.tar.gz' if item['prefix']=='selected' else 'accepted-sources.tar.gz')
        assert sha(copy.read_bytes())==item['sha256']==sha((ROOT/item['path']).read_bytes())
        with tarfile.open(copy) as tf:
            rows=[m for m in tf.getmembers() if m.isfile()]; assert len(rows)==item['files']
            for m in rows:
                raw=tf.extractfile(m).read(); frozen[m.name]=raw
                assert bindings['frozenFiles'][m.name]=={'bytes':len(raw),'sha256':sha(raw)}
    package,package_kinds,links=archive(P/'review-source-package.tar.gz')
    manifest=json.loads((P/'source-package-manifest.json').read_bytes())
    assert package=={'package/'+name:row for name,row in manifest.items()}
    assert sha((P/'review-source-package.tar.gz').read_bytes())==handoff['sourceReviewArchiveSHA256']=='585f44532cb67ca626ae7c2c95bfa7030408bf2b4dc57f5bac0fdbd84cea66af'
    changed=[];diff=[]
    with tarfile.open(P/'review-source-package.tar.gz') as tf:
        for name,original in frozen.items():
            raw=tf.extractfile('package/sources/'+name).read()
            assert bindings['derivativeFiles'][name]=={'bytes':len(raw),'sha256':sha(raw)}
            assert (P/'sources'/name).read_bytes()==raw
            out=B/'sources'/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
            if raw!=original:
                changed.append(name)
                diff+=list(difflib.unified_diff(original.decode().splitlines(True),raw.decode().splitlines(True),'frozen/'+name,'reviewed/'+name))
        fixture=tf.extractfile('package/fixtures.py').read()
        (B/'fixtures.py').write_bytes(fixture)
        (B/'frozen-receiver.py').write_bytes(frozen['selected/inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py'])
    assert sorted(changed)==sorted(bindings['changedEndpoints']) and len(frozen)==72
    (B/'independent-endpoint-diff.patch').write_text(''.join(diff))
    synthetic,kinds,links=archive(P/'synthetic-evidence.tar.gz')
    assert synthetic==json.loads((P/'synthetic-evidence-manifest.json').read_bytes())
    native=json.loads((P/'inputs/native-result-receipt.json').read_bytes())
    assert native['officialSummary']=={'failed':1,'passed':0,'skipped':1} and native['xcodeExitCode']==65 and not native['nativeVerdictAccepted']
    save('audit.json',dict(passed=True,producerHandoffSHA256=expected,handoffMembers=len(handoff['members']),sourcePackageMembers=len(package),sourcePackageKinds=package_kinds,frozenSourceMembers=len(frozen),changedEndpoints=changed,unchangedSources=70,sourceBindingsSHA256=sha((P/'source-bindings.json').read_bytes()),sourceRevisionLabel=bindings['sourceRevision'],rootCurrentRevisionContext='be472ce6424a691de5673e3438d2768264827d23',syntheticMembers=len(synthetic),syntheticKinds=kinds,syntheticSymlinks=links,symlinksFollowed=False,originalSettingsFailed=True,dependentTabSkipped=True,xcodeExitCode=65,officialImporterAccepted=False))
    print(json.dumps({'passed':True,'producerMembers':len(handoff['members']),'sources':len(frozen),'changed':changed,'syntheticKinds':kinds}))
if __name__=='__main__':main()
