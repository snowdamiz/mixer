#!/usr/bin/env python3
"""Independent byte inventories and exact historical replay; no native commands."""
import hashlib
import importlib.util
import json
import pathlib
import stat
import tarfile
import sys

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
P=ROOT/'verification/apple-toggle-keyboard-focus-v7-preparation'
V6=P.parent/'apple-toggle-keyboard-focus-v6-preparation'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':')).encode()
read=lambda p:json.loads(p.read_bytes())


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def main():
    inputs=read(HERE/'review-inputs.json')
    for name,digest in inputs.items():
        path=pathlib.Path(name) if name.startswith('/') else ROOT/name
        assert path.is_file() and not path.is_symlink() and sha(path)==digest,name
    for binding in read(HERE/'tool-link-bindings.json'):
        path=pathlib.Path(binding['path'])
        assert path.is_symlink() and path.readlink().as_posix()==binding['linkText'] and str(path.resolve())==binding['resolved'] and sha(path)==binding['sha256']
    manifest=read(P/'build-products-manifest.json');base=P/'build/Build/Products'
    tree={}
    for path in sorted(base.rglob('*')):
        assert not path.is_symlink()
        mode=format(stat.S_IMODE(path.stat().st_mode),'04o')
        tree[str(path.relative_to(base))]=dict(kind='directory',mode=mode) if path.is_dir() else dict(kind='file',mode=mode,bytes=path.stat().st_size,sha256=sha(path))
    assert tree==manifest['products']
    assert hashlib.sha256(canonical(tree)).hexdigest()==manifest['productTreeSHA256']
    archive=P/'test-runner-products.tar.gz'
    assert sha(archive)==manifest['productArchiveSHA256']
    archive_tree={}
    with tarfile.open(archive,'r:gz') as tar:
        for member in tar.getmembers():
            assert member.name not in archive_tree and not member.name.startswith('/') and '..' not in pathlib.PurePosixPath(member.name).parts
            if member.isdir(): value=dict(kind='directory',mode=format(member.mode,'04o'))
            else:
                assert member.isfile()
                data=tar.extractfile(member).read()
                value=dict(kind='file',mode=format(member.mode,'04o'),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
            archive_tree[member.name]=value
    assert archive_tree==tree
    assert all(sha(ROOT/name)==digest for name,digest in manifest['sourceFiles'].items())
    assert hashlib.sha256(canonical(manifest['sourceFiles'])).hexdigest()==manifest['sourceTreeSHA256']
    assert all(sha(pathlib.Path(name))==digest for name,digest in manifest['toolFiles'].items())
    app=read(P/'built-app-manifest.json');lock=read(P/'source-lock.json')
    sources={str(path.relative_to(P/'source')):sha(path) for path in sorted((P/'source').rglob('*')) if path.is_file()}
    assert sources==lock['sha256']
    assert hashlib.sha256(canonical(sources)).hexdigest()==lock['sourceClosureSHA256']=='f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46'
    assert sha(P/'built-app.tar.gz')==app['archiveSHA256']==sha(V6/'built-app.tar.gz')=='b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393'
    reuse=read(P/'immutable-reuse.json')
    assert all(sha(ROOT/name)==sha(ROOT/source)==reuse['copiedFiles'][name] for name,source in reuse['exactCopySources'].items())
    assert sha(P/'keyboard_oracle.py')==sha(V6/'keyboard_oracle.py')
    assert sha(P/'harness/UITests/DiagnosticTransport.swift')==sha(V6/'harness/UITests/DiagnosticTransport.swift')
    headers=read(P/'official/manifest.json')['installedOfficialHeaders']
    assert all(sha(pathlib.Path(v['source']))==sha(P/'official'/v['snapshot'])==v['sha256'] for v in headers)
    build=read(P/'runner-build-attempt-1.json')
    official=[c for c in build if c['argv'][1:2]==['build-for-testing']]
    assert len(official)==1 and official[0]['exitCode']==0 and '** TEST BUILD SUCCEEDED **' in official[0]['stdout']
    assert 'generic/platform=iOS Simulator' in official[0]['argv'] and 'CODE_SIGNING_ALLOWED=NO' in official[0]['argv'] and 'ARCHS=arm64' in official[0]['argv']
    assert 'PublicSwitchSelection.swift' in official[0]['stdout']
    sys.path.insert(0,str(V6))
    legacy=load('independent_legacy_session',V6/'settings_telemetry.py')
    legacy_replay=load('independent_legacy_replay',V6/'replay.py');legacy_replay.t=legacy
    journal=V6/'runtime/captures';paths=sorted(journal.glob('0000-settings-*.json'));assert len(paths)==275
    before={str(path):sha(path) for path in paths}
    actual=legacy_replay.replay(journal)
    assert actual==read(V6/'runtime/runtime-verdict.json')['settingsDiagnostic']
    current=load('independent_v7_route_predicate',P/'settings_telemetry.py')
    legacy.route_target=current.route_target
    corrected=legacy_replay.replay(journal)
    assert actual['routeTaps']==[0,1] and corrected['routeTaps']==[0,1,2]
    assert corrected['settingsReportedEnabled'] is False and corrected['setupObservationSatisfied'] is False
    assert before=={str(path):sha(path) for path in paths}
    (HERE/'frozen-v6-replay.json').write_text(json.dumps(dict(records=275,original=actual,correctedRoutePredicateOnly=corrected,filesUnchanged=True,syntheticNativeClaims=False),indent=2,sort_keys=True)+'\n')
    result=dict(inputFilesVerified=len(inputs),producerSealFiles=90,runnerProductEntries=len(tree),runnerProductTreeSHA256=manifest['productTreeSHA256'],runnerArchiveSHA256=manifest['productArchiveSHA256'],runnerSourceSHA256=manifest['sourceTreeSHA256'],sourceRevisionContext=manifest['sourceRevisionContext'],
                appArchiveSHA256=app['archiveSHA256'],appSourceClosureSHA256=lock['sourceClosureSHA256'],exactImmutableCopies=len(reuse['exactCopySources']),officialHeadersVerified=len(headers),toolFilesVerified=len(manifest['toolFiles']),
                officialBuildForTestingVerified=True,frozenV6RecordsReplayed=275,frozenV6StillFailed=True,correctedRoutePredicateCreditsAllThreeOnly=True,nativeExecuted=False,nativeInstancesQueried=False,gaAccepted=False)
    (HERE/'provenance-and-legacy.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
