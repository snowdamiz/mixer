"""Independent bounded offline review. Owns only this directory and its scratch."""
from pathlib import Path
import datetime, hashlib, json, os, platform, selectors, shutil, subprocess, sys, tarfile, time
R=Path(__file__).resolve().parents[2]; P=Path(__file__).resolve().parent
F=R/'verification/swift-ordered-retention-diagnostic-rust'; S=P/'.scratch'
T=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
def sha(b): return hashlib.sha256(b).hexdigest()
def put(name,value): (P/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def tree(root): return {str(p.relative_to(root)):sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}
def live(): return {n:sha((R/'vm'/n).read_bytes()) for n in BASE}
BASE=json.loads((F/'baseline-source-manifest.json').read_bytes())
def audit():
    sealraw=(F/'seal.json').read_bytes(); assert sha(sealraw)=='c19bd3fb06e2db11a5e6ecb5aad8de2ca6ee19a35e50a5ba691ecb598bde40bf'
    seal=json.loads(sealraw); total=0
    for e in seal['members']:
        path=R/e['path']; assert path.is_file() and not path.is_symlink()
        b=path.read_bytes(); assert len(b)==e['bytes'] and sha(b)==e['sha256']; total+=len(b)
    assert len(seal['members'])==186 and total==20248850
    assert live()==BASE and len(BASE)==132
    assert not S.exists(); S.mkdir()
    ownership={}
    for name in ['baseline','candidate','reverse','build-baseline','build-candidate','tmp','writer']:
        d=S/name;d.mkdir();s=d.stat();ownership[name]={'dev':s.st_dev,'ino':s.st_ino}
    put('scratch-ownership.json',ownership)
    for label in ['baseline','candidate']:
        manifest=json.loads((F/(label+'-manifest.json')).read_bytes())
        with tarfile.open(F/(label+'-source.tar.gz'),'r:gz') as archive:
            assert len(archive.getmembers())==132 and sorted(archive.getnames())==sorted(manifest)
            for m in archive:
                assert m.isfile() and m.name in manifest and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
                b=archive.extractfile(m).read();assert sha(b)==manifest[m.name]
                for target in [S/label]+([S/'reverse'] if label=='candidate' else []):
                    d=target/m.name;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(b)
        assert tree(S/label)==manifest
    changed=[n for n in BASE if (S/'baseline'/n).read_bytes()!=(S/'candidate'/n).read_bytes()]
    assert changed==['src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/control.rs']
    assert (S/'baseline/Cargo.toml').read_bytes()==(S/'candidate/Cargo.toml').read_bytes()
    assert (S/'baseline/Cargo.lock').read_bytes()==(S/'candidate/Cargo.lock').read_bytes()
    result=run('reverse-patch',['/usr/bin/patch','-R','-p1','-i',str(F/'candidate.patch')],S/'reverse')
    assert result['exitCode']==0 and tree(S/'reverse')==BASE
    checks=[]
    for command in sorted((F/'commands').iterdir()):
        if not (command/'result.json').exists():continue
        result=json.loads((command/'result.json').read_bytes())
        for stream,binding in result['outputs'].items():
            b=(command/(stream+'.txt')).read_bytes();assert len(b)==binding['bytes'] and sha(b)==binding['sha256']
        checks.append({'name':command.name,'status':result['status'],'exitCode':result['exitCode']})
    put('packet-audit.json',{'producerSealSHA256':sha(sealraw),'members':len(seal['members']),'bytes':total,'archivesEach':132,'changedCopiedFiles':changed,'reversePatchAll132Restored':True,'live132Unchanged':True,'commandOutputBindingsVerified':checks})
def run(name,argv,cwd,env=None,timeout=240):
    d=P/'commands'/name;d.mkdir(parents=True,exist_ok=False)
    overrides={'RUSTC':str(T/'rustc'),'PATH':str(T)+':'+os.environ['PATH'],'CARGO_NET_OFFLINE':'true','CARGO_BUILD_JOBS':'1'}
    if env:overrides.update(env)
    before=tree(cwd) if cwd.name in ['baseline','candidate','reverse'] else None
    command={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'cwd':str(cwd),'environmentOverrides':overrides,'timeoutSeconds':timeout,'captureLimitPerStream':1048576,'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'sourceTree':before,'tools':{n:{'path':str(T/n),'sha256':sha((T/n).read_bytes()),'version':subprocess.check_output([str(T/n),'--version'],text=True).strip()} for n in ['cargo','rustc']},'runnerSHA256':sha(Path(__file__).read_bytes())}
    (d/'command.json').write_text(json.dumps(command,indent=2,sort_keys=True)+'\n')
    child=subprocess.Popen(argv,cwd=cwd,env={**os.environ,**overrides},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    selector=selectors.DefaultSelector();selector.register(child.stdout,selectors.EVENT_READ,'stdout');selector.register(child.stderr,selectors.EVENT_READ,'stderr')
    data={'stdout':bytearray(),'stderr':bytearray()};status='exited';start=time.monotonic()
    while selector.get_map():
        if time.monotonic()-start>timeout and child.poll() is None:status='timeout';child.kill()
        for key,_ in selector.select(.1):
            b=os.read(key.fileobj.fileno(),65536)
            if not b:selector.unregister(key.fileobj);continue
            output=data[key.data]
            if len(output)+len(b)>1048576:
                status='output-cap';child.kill();b=b[:1048576-len(output)]
            output.extend(b)
    code=child.wait(timeout=5);selector.close()
    for n,b in data.items():(d/(n+'.txt')).write_bytes(b)
    result={'status':status,'exitCode':code,'elapsedSeconds':time.monotonic()-start,'outputs':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in data.items()},'sourceUnchanged':before is None or tree(cwd)==before,'live132Unchanged':live()==BASE}
    (d/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(name,json.dumps(result),flush=True)
    return result
def cargo(name,side,args):
    tmp=S/'tmp'/name;tmp.mkdir(exist_ok=False)
    return run(name,[str(T/'cargo'),'test','--offline','--release',*args],S/side,{'CARGO_TARGET_DIR':str(S/('build-'+side)),'TMPDIR':str(tmp)})
def cleanup():
    owned=json.loads((P/'scratch-ownership.json').read_bytes());removed=[]
    for n,identity in owned.items():
        d=S/n;s=d.stat();assert s.st_dev==identity['dev'] and s.st_ino==identity['ino'] and not d.is_symlink()
        shutil.rmtree(d);removed.append({'name':n,**identity,'removed':not d.exists()})
    S.rmdir();put('cleanup.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'directories':removed,'scratchRemoved':not S.exists(),'live132Unchanged':live()==BASE,'noProcessDiscovery':True,'allSynchronousChildrenReaped':True,'nativeCaptureUIInstancesStarted':0})
if __name__=='__main__':
    action=sys.argv[1]
    if action=='prepare':audit()
    elif action=='originals':
        for side in ['baseline','candidate']:
            assert cargo(side+'-swift-attempt2',side,['--features','experimental-swift-reactor','--lib','experimental_swift_reactor::','--','--test-threads=1','--nocapture'])['exitCode']==0
            assert cargo(side+'-generic-private',side,['--features','experimental-function-cache','--lib','experimental::cache::tests','--','--test-threads=1','--nocapture'])['exitCode']==0
            assert cargo(side+'-generic-integration',side,['--features','experimental-function-cache','--test','span_function_cache','--test','span_function_cache_allocations','--','--test-threads=1','--nocapture'])['exitCode']==0
    elif action=='independent':
        f=S/'candidate/src/experimental_swift_reactor/cache_tests.rs';s=f.read_text();assert s.endswith('\n}\n');s=s[:-3]+(P/'independent-hooks.rs').read_text()+'\n}\n';f.write_text(s)
        put('independent-source-manifest.json',tree(S/'candidate'))
        assert cargo('independent-hooks','candidate',['--features','experimental-swift-reactor','--lib','independent_review_','--','--test-threads=1','--nocapture'])['exitCode']==0
    elif action=='writer':
        (S/'writer/writer.rs').write_bytes((F/'writer.rs').read_bytes())
        (S/'writer/main.rs').write_bytes((P/'independent-writer.rs').read_bytes())
        assert run('independent-writer-compile',[str(T/'rustc'),'--edition=2021','--test','-O',str(S/'writer/main.rs'),'-o',str(S/'writer/tests')],S/'writer')['exitCode']==0
        assert run('independent-writer',[str(S/'writer/tests'),'--test-threads=1','--nocapture'],S/'writer')['exitCode']==0
    elif action=='custody':
        assert run('independent-custody-attempt2',[sys.executable,str(P/'custody_adversity.py')],P)['exitCode']==0
    elif action=='custody-inventory':
        assert run('independent-custody-inventory',[sys.executable,str(P/'custody_inventory.py')],P)['exitCode']==0
    elif action=='cleanup':cleanup()
