#!/usr/bin/env python3
"""Independent integrity and exact baseline+patch reconstruction, before builds."""
import datetime, gzip, hashlib, json, pathlib, shutil, sys, tarfile, tempfile
sys.dont_write_bytecode = True
import collect as c
P = c.ROOT / 'verification/swift-cleanup-diagnostic'
sha = c.sha

def checked_packet(path):
    seal=json.loads((path/'seal.json').read_text())
    files=seal['files']
    actual={str(p.relative_to(path)) for p in path.rglob('*') if p.is_file() and p != path/'seal.json'}
    assert actual == set(files), (path, actual ^ set(files))
    for n,h in files.items(): assert sha((path/n).read_bytes()) == h, (path,n)
    for key in ['externalBindings','externalFiles']:
        for n,h in seal.get(key,{}).items(): assert sha((c.ROOT/n).read_bytes()) == h, n
    return dict(sealSHA256=sha((path/'seal.json').read_bytes()),files=len(files))

def unpack(path,manifest,destination):
    bodies={}
    with tarfile.open(path) as t:
        for e in t:
            assert e.isfile() and not pathlib.PurePosixPath(e.name).is_absolute() and '..' not in pathlib.PurePosixPath(e.name).parts
            assert e.name in manifest and e.name not in bodies
            b=t.extractfile(e).read(); assert sha(b)==manifest[e.name]
            bodies[e.name]=b
    assert set(bodies)==set(manifest)
    destination.mkdir()
    for n,b in bodies.items():
        p=destination/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)

def main():
    packets={}
    for n in ['swift-cleanup-diagnostic','swift-cleanup-diagnostic-contract','swift-host-operation-root-integration']:
        packets[n]=checked_packet(c.ROOT/'verification'/n)
    assert packets['swift-cleanup-diagnostic']['sealSHA256']=='19d9040a10275bfc7968966853adc6541fb2b9855201c4448e226d4eeb0488a1'
    inputs=json.loads((P/'input-bindings.json').read_text())
    for n,h in inputs.items(): assert sha((c.ROOT/n).read_bytes())==h,n
    accepted=c.ROOT/'verification/swift-host-operation-root-integration'
    baseline=json.loads((accepted/'integrated-source-manifest.json').read_text())
    candidate=json.loads((P/'candidate-source-manifest.json').read_text())
    assert len(baseline)==len(candidate)==128
    assert c.digest(baseline)=='7ee6194584a5029ff2bbbcb94f8286295411cb3441a04db30c8fd4036d851329'
    assert c.digest(candidate)=='1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c'
    assert baseline==json.loads((P/'baseline-source-manifest.json').read_text())
    scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-cleanup-independent-')).resolve();st=scratch.stat()
    c.save('session.json',dict(scratch=str(scratch),startedUTC=c.now(),scratchDevice=st.st_dev,scratchInode=st.st_ino,sourceRevisionContext=json.loads((accepted/'acceptance.json').read_text())['sourceRevision'],sourceBytesAreAuthority=True))
    unpack(accepted/'integrated-source.tar.gz',baseline,scratch/'baseline')
    shutil.copytree(scratch/'baseline',scratch/'candidate')
    c.command('patch-reconstruction',['patch','-p2','--batch','--fuzz=0','-i',str(P/'candidate.patch')],None,{'REVIEW_PATCH_WORKDIR':str(scratch/'candidate')}) if False else None
    # The patch mutates the owned candidate only, and is logged separately because
    # collect.command correctly rejects mutation of its source argument.
    c.command('patch-reconstruction',['patch','-d',str(scratch/'candidate'),'-p2','--batch','--fuzz=0','-i',str(P/'candidate.patch')])
    assert c.manifest(scratch/'candidate')==candidate
    unpack(P/'candidate-source.tar.gz',candidate,scratch/'producer-archive')
    assert c.manifest(scratch/'producer-archive')==candidate
    for label in ['baseline','candidate']: c.archive(label,scratch/label)
    shutil.rmtree(scratch/'producer-archive')
    copied={}
    for f in c.HERE.glob('*.py'):
        if (P/f.name).exists(): copied[f.name]=dict(producer=sha((P/f.name).read_bytes()),review=sha(f.read_bytes()))
    c.save('input-validation.json',dict(status='passed-before-source-rebuild',packets=packets,producerBindings=len(inputs),acceptedBaseline=c.digest(baseline),candidate=c.digest(candidate),exactPatchApplied=True,all128SourceHashesMatch=True,reusedMachinery=copied))
    c.command('producer-offline-replay',['python3','-B',str(P/'verify.py')],scratch/'candidate')
    c.command('contract-offline-replay',['python3','-B',str(c.ROOT/'verification/swift-cleanup-diagnostic-contract/verify.py')],scratch/'baseline')
    for name,argv in [('rustc',['rustc','-vV']),('cargo',['cargo','-V']),('clippy',['cargo','clippy','--version']),('rustfmt',['rustfmt','--version']),('python',['python3','--version']),('host',['uname','-a']),('patch',['patch','--version'])]:
        c.command('tool-'+name,argv,scratch/'candidate')
    print('PASS independent packet membership, accepted upstream and candidate reconstruction',flush=True)

if __name__=='__main__': main()
