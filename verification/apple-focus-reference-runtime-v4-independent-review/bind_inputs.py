"""Independent data-only binding and scratch-copy of the explicitly frozen closure."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tarfile
import tempfile

OWNED = Path(__file__).resolve().parent
ROOT = OWNED.parents[1]
V4 = ROOT / 'verification/apple-focus-reference-runtime-v4'
EXPECTED = {
    'handoff.json': '79a8a2d5070b1f9466831089be0f2f89d1e67d3785c707879414ea2edac9ca07',
    'packet.json': '4622a27a5e4c9dc9651b3eee6022e850dab1f55db3b48ac8f0daa4921b80e77a',
    'host-attempt-2/receipt.json': '771d70983473916cc8004d2c3a4893b2ce82bfc0e0a992ce657cd853fa5e35c3',
}
sha = lambda raw: hashlib.sha256(raw).hexdigest()
stable = lambda data: (json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()

def safe(name):
    assert not any(word in name.lower() for word in ('hosted','catalog','authority-driver','worker-transport')), name
    path = Path(name)
    assert '..' not in path.parts, name
    return path if path.is_absolute() else ROOT / path

def row(path):
    canonical = path.resolve()
    assert canonical == path or str(path).endswith('/SDKSettings.json'), path
    info = canonical.lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1, path
    raw = canonical.read_bytes()
    return {'kind':'file','mode':stat.S_IMODE(info.st_mode),'bytes':len(raw),'sha256':sha(raw)}

def bind():
    for name, expected in EXPECTED.items():
        assert row(V4 / name)['sha256'] == expected, name
    handoff = json.loads((V4 / 'handoff.json').read_bytes())
    packet = json.loads((V4 / 'packet.json').read_bytes())
    receipt = json.loads((V4 / 'host-attempt-2/receipt.json').read_bytes())
    members = handoff['members']; deps = json.loads((V4 / 'derivation-inputs.json').read_bytes())
    assert len(members) == 535 and len(deps) == 621
    assert sha(stable(members)) == handoff['memberTreeSHA256'] == '1026b48423fc2b98beb46a5d21144de6cd8960881658c7c8ba73847a9add3c0d'
    assert sha(stable(deps)) == receipt['inputTreeSHA256'] == '30e511b5622426f8288595da7613e829e50eba34046d8351186a7d415067cca4'
    assert receipt['inputBindings'] == deps == json.loads((V4 / 'input-lock.json').read_bytes())
    bindings = dict(deps)
    for name, expected in members.items():
        assert name not in bindings or bindings[name] == expected, name
        bindings[name] = expected
    bindings[str((V4/'handoff.json').relative_to(ROOT))] = row(V4/'handoff.json')
    for name, expected in bindings.items():
        assert row(safe(name)) == expected, name
    assert sha(stable(packet['ownedSources'])) == packet['ownedSourceTreeSHA256'] == receipt['ownedSourceTreeSHA256']
    for name, expected in packet['ownedSources'].items(): assert row(V4/name) == expected, name
    assert sha(stable(receipt['outputs'])) == receipt['outputTreeSHA256']
    for name, expected in receipt['outputs'].items(): assert row(V4/'host-attempt-2'/name) == expected, name
    assert handoff['sourceTreeSHA256'] == packet['sourceTreeSHA256'] == receipt['sourceTreeSHA256'] == '696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a'
    assert handoff['productArchiveSHA256'] == packet['productArchiveSHA256'] == receipt['productArchiveSHA256'] == '0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8'
    return bindings, handoff, packet, receipt

def copy_closure(bindings, scratch):
    for name, expected in bindings.items():
        dst = scratch / ('external' if name.startswith('/') else 'repo') / name.lstrip('/')
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(safe(name).read_bytes()); dst.chmod(expected['mode'])
        assert row(dst) == expected, name
    return scratch / 'repo'

def archive_rows(path, expected, prefix=''):
    found={}
    with tarfile.open(path,'r:gz') as archive:
        for member in archive.getmembers():
            assert not member.name.startswith('/') and '..' not in Path(member.name).parts
            if member.isdir(): continue
            assert member.isfile() and member.name.startswith(prefix), member.name
            name=member.name[len(prefix):];assert name not in found, name
            raw=archive.extractfile(member).read()
            found[name]={'kind':'file','mode':member.mode,'bytes':len(raw),'sha256':sha(raw)}
    assert found == expected, path
    return {'members':len(found),'treeSHA256':sha(stable(found)),'archiveSHA256':sha(path.read_bytes())}

def main():
    bindings, handoff, packet, receipt=bind()
    scratch=Path(tempfile.mkdtemp(prefix='.scratch-',dir=OWNED))
    try:
        repo=copy_closure(bindings,scratch)
        base=repo/'verification/apple-focus-reference-runtime-v4'
        manifest=json.loads((base/'runtime-source-manifest.json').read_bytes())
        source=archive_rows(base/'runtime-sources.tar.gz',manifest['files'],'selected/')
        prior=repo/'verification/apple-focus-reference-diagnostic-v1'
        prepared=json.loads((prior/'prepared.json').read_bytes())
        accepted=archive_rows(prior/'accepted-sources.tar.gz',prepared['derivativeSources'],'accepted/')
        products=json.loads((prior/'compile-attempt-1/product-manifest.json').read_bytes())
        product=archive_rows(prior/'compile-attempt-1/products.tar.gz',products['products'])
        assert accepted['members']==39 and accepted['treeSHA256']==packet['sourceTreeSHA256']
        assert product['members']==55 and product['treeSHA256']==packet['productTreeSHA256']
        assert product['archiveSHA256']==packet['productArchiveSHA256']
        commands={r['programSHA256']:r['argv'][3] for r in receipt['hostPythonSubprocesses']}
        output=OWNED/'inspected-programs';output.mkdir(exist_ok=True)
        for digest,program in commands.items():
            assert sha(program.encode())==digest
            (output/(digest+'.py')).write_text(program)
        result={'schema':'mixer.apple-focus-reference-runtime-v4-independent-input-bindings.1',
                'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'command':[sys.executable,'-B',str(Path(__file__).resolve())],
                'python':sys.version,'pythonExecutable':str(Path(sys.executable).resolve()),'hostUname':list(os.uname()),
                'expected':EXPECTED,'handoffMembers':535,'frozenDependencies':621,'bindings':bindings,
                'bindingTreeSHA256':sha(stable(bindings)),'archives':{'runtime':source,'acceptedSource':accepted,'products':product},
                'sourceRevisionLabel':receipt['sourceRevisionLabel'],'sourceRevisionMeaning':'Inherited label only; hashes define source; no Git query',
                'scratch':str(scratch),'scratchRepo':str(repo),'copiedBeforeReplay':True,'nativeExecuted':False,
                'excludedHostedLanesReadImportedExecuted':False}
        (OWNED/'input-bindings.json').write_bytes(stable(result))
        print(json.dumps({k:v for k,v in result.items() if k not in ('bindings','hostUname','python')},sort_keys=True))
    except BaseException:
        shutil.rmtree(scratch)
        raise

if __name__=='__main__': main()
