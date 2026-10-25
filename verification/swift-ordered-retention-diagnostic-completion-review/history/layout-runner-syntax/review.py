"""Independent copied-source host review; no live engine or native work."""
from pathlib import Path
import datetime, hashlib, json, os, platform, selectors, shutil, subprocess, sys, tarfile, time

P=Path(__file__).resolve().parent
R=P.parents[1]
F=P.parent/'swift-ordered-retention-diagnostic-completion'
O=P.parent/'swift-ordered-retention-diagnostic-rust'
S=P/'.scratch'
T=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
BASE=json.loads((O/'baseline-source-manifest.json').read_bytes())
def sha(raw):return hashlib.sha256(raw).hexdigest()
def put(name,value):(P/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def tree(root):return {str(p.relative_to(root)):sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}
def live():return {n:sha((R/'vm'/n).read_bytes()) for n in BASE}
def check_seal(packet,expected):
    raw=(packet/'seal.json').read_bytes();assert sha(raw)==expected
    seal=json.loads(raw);total=0
    for entry in seal['members']:
        p=R/entry['path'];assert p.is_file() and not p.is_symlink()
        value=p.read_bytes();assert len(value)==entry['bytes'] and sha(value)==entry['sha256'];total+=len(value)
    return {'sha256':expected,'members':len(seal['members']),'bytes':total}
def prepare(expected):
    checks={'completion':check_seal(F,expected),'original':check_seal(O,'c19bd3fb06e2db11a5e6ecb5aad8de2ca6ee19a35e50a5ba691ecb598bde40bf'),'originalReview':check_seal(P.parent/'swift-ordered-retention-diagnostic-rust-review','b5436299c6f89fd8cdb89d870d4816ecc66080588ce5867085df44f1ad791e78')}
    assert len(BASE)==132 and live()==BASE
    (P/'inputs').mkdir(exist_ok=False)
    for name in ['seal.json','candidate-source.tar.gz','candidate-manifest.json','baseline-source.tar.gz','baseline-manifest.json','candidate.patch','completion_tests.rs','custody.py','test_custody.py']:
        shutil.copyfile(F/name,P/'inputs'/name)
    S.mkdir(exist_ok=False);owned={}
    for name in ['.','baseline','candidate','reverse','build-baseline','build-candidate','tmp','host']:
        d=S/name
        if name!='.':d.mkdir()
        st=d.stat();owned[name]={'dev':st.st_dev,'ino':st.st_ino}
    put('scratch-ownership.json',owned)
    for side in ['baseline','candidate']:
        manifest=json.loads((P/'inputs'/(side+'-manifest.json')).read_bytes())
        if side=='baseline':assert manifest==BASE
        with tarfile.open(P/'inputs'/(side+'-source.tar.gz'),'r:gz') as archive:
            assert len(archive.getmembers())==132 and sorted(archive.getnames())==sorted(manifest)
            for m in archive:
                assert m.isfile() and m.name in manifest and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
                b=archive.extractfile(m).read();assert sha(b)==manifest[m.name]
                for target in [S/side]+([S/'reverse'] if side=='candidate' else []):
                    p=target/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        assert tree(S/side)==manifest
    changed=[n for n in BASE if (S/'baseline'/n).read_bytes()!=(S/'candidate'/n).read_bytes()]
    assert changed==['src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/control.rs']
    original=json.loads((O/'candidate-manifest.json').read_bytes())
    candidate=tree(S/'candidate');assert [n for n in BASE if original[n]!=candidate[n]]==['src/experimental_swift_reactor/cache_tests.rs']
    assert run('reverse-patch',['/usr/bin/patch','-R','-p1','-i',str(P/'inputs/candidate.patch')],S/'reverse')['exitCode']==0
    assert tree(S/'reverse')==BASE
    bindings=[]
    for command in sorted((F/'commands').iterdir()):
        if not (command/'result.json').exists():continue
        result=json.loads((command/'result.json').read_bytes())
        for stream,binding in result['outputs'].items():
            b=(command/(stream+'.txt')).read_bytes();assert len(b)==binding['bytes'] and sha(b)==binding['sha256']
        bindings.append({'name':command.name,'status':result['status'],'exitCode':result['exitCode']})
    put('packet-audit.json',{'seals':checks,'archivesEach':132,'changedFromPristine':changed,'changedFromOriginal':['src/experimental_swift_reactor/cache_tests.rs'],'reverseAll132Restored':True,'live132Unchanged':True,'producerCommandBindings':bindings,'inputs':tree(P/'inputs')})
def run(name,argv,cwd,overrides=None,timeout=240):
    d=P/'commands'/name;d.mkdir(parents=True,exist_ok=False)
    env={'PATH':str(T)+':'+os.environ['PATH'],'RUSTC':str(T/'rustc'),'CARGO_BUILD_JOBS':'1','CARGO_NET_OFFLINE':'true','PYTHONDONTWRITEBYTECODE':'1'}
    env.update(overrides or {})
    before=tree(cwd) if cwd.name in ['baseline','candidate','reverse'] else None
    command={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'cwd':str(cwd),'environmentOverrides':env,'timeoutSeconds':timeout,'captureLimitPerStream':1048576,'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'sourceTree':before,'platform':platform.platform(),'tools':{n:{'path':str(T/n),'sha256':sha((T/n).read_bytes()),'version':subprocess.check_output([str(T/n),'--version'],text=True).strip()} for n in ['rustc','cargo']},'python':{'path':sys.executable,'version':sys.version,'sha256':sha(Path(sys.executable).read_bytes())},'runnerSHA256':sha(Path(__file__).read_bytes())}
    command['inputFiles']={arg:sha(Path(arg).read_bytes()) for arg in argv if Path(arg).is_absolute() and Path(arg).suffix in ['.py','.rs'] and Path(arg).is_file()}
    (d/'command.json').write_text(json.dumps(command,sort_keys=True,indent=2)+'\n')
    child=subprocess.Popen(argv,cwd=cwd,env={**os.environ,**env},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    sel=selectors.DefaultSelector();sel.register(child.stdout,selectors.EVENT_READ,'stdout');sel.register(child.stderr,selectors.EVENT_READ,'stderr')
    data={'stdout':bytearray(),'stderr':bytearray()};started=time.monotonic();status='exited'
    while sel.get_map():
        if time.monotonic()-started>timeout and child.poll() is None:status='timeout';child.kill()
        for key,_ in sel.select(.1):
            b=os.read(key.fileobj.fileno(),65536)
            if not b:sel.unregister(key.fileobj);continue
            out=data[key.data]
            if len(out)+len(b)>1048576:status='output-cap';child.kill();b=b[:1048576-len(out)]
            out.extend(b)
    code=child.wait(timeout=5);sel.close()
    for n,b in data.items():(d/(n+'.txt')).write_bytes(b)
    result={'status':status,'exitCode':code,'elapsedSeconds':time.monotonic()-started,'sourceUnchanged':before is None or tree(cwd)==before,'live132Unchanged':live()==BASE,'outputs':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in data.items()}}
    (d/'result.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(name,json.dumps(result),flush=True)
    return result
def cargo(name,side,args):
    tmp=S/'tmp'/name;tmp.mkdir(exist_ok=False)
    result=run(name,[str(T/'cargo'),'test','--offline','--release',*args],S/side,{'CARGO_TARGET_DIR':str(S/('build-'+side)),'TMPDIR':str(tmp)})
    assert result['exitCode']==0 and result['status']=='exited' and result['sourceUnchanged'] and result['live132Unchanged']
def cleanup():
    owned=json.loads((P/'scratch-ownership.json').read_bytes());removed=[]
    for name,identity in owned.items():
        if name=='.':continue
        d=S/name;st=d.stat();assert not d.is_symlink() and {'dev':st.st_dev,'ino':st.st_ino}==identity
        shutil.rmtree(d);removed.append({'name':name,**identity,'removed':not d.exists()})
    st=S.stat();assert {'dev':st.st_dev,'ino':st.st_ino}==owned['.'];S.rmdir()
    put('cleanup.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'removed':removed,'scratchRemoved':not S.exists(),'live132Unchanged':live()==BASE,'allSynchronousChildrenReaped':True,'nativeCaptureUIInstancesStarted':0,'processDiscovery':False})
if __name__=='__main__':
    action=sys.argv[1]
    if action=='prepare':prepare(sys.argv[2])
    elif action=='candidate':cargo('candidate-swift','candidate',['--features','experimental-swift-reactor','--lib','experimental_swift_reactor::','--','--test-threads=1','--nocapture'])
    elif action=='generic':
        for side in ['baseline','candidate']:
            cargo(side+'-generic-private',side,['--features','experimental-function-cache','--lib','experimental::cache::tests','--','--test-threads=1','--nocapture'])
            cargo(side+'-generic-integration',side,['--features','experimental-function-cache','--test','span_function_cache','--test','span_function_cache_allocations','--','--test-threads=1','--nocapture'])
    elif action=='host':
        for name in ['custody.py','test_custody.py']:shutil.copyfile(P/'inputs'/name,S/'host'/name)
        (S/'host/.scratch').mkdir()
        assert run('producer-custody',[sys.executable,'-B','-m','unittest','discover','-s',str(S/'host'),'-p','test_custody.py','-v'],S/'host')['exitCode']==0
        assert run('independent-controls',[sys.executable,'-B',str(P/'independent_controls.py')],P)['exitCode']==0
    elif action=='layout':
        suffix='-'+sys.argv[2] if len(sys.argv)>2 else ''
        assert run('layout-compile'+suffix,[str(T/'rustc'),'--edition=2021','-O',str(P/'layout-probe.rs'),'-o',str(S/'host/('layout-probe'+suffix))],S/'host')['exitCode']==0
        candidate=json.loads((P/'commands/candidate-swift/command.json').read_bytes())
        assert run('layout-probe'+suffix,[str(S/'host/('layout-probe'+suffix))],S/'host',{'TMPDIR':candidate['environmentOverrides']['TMPDIR']})['exitCode']==0
    elif action=='independent':
        assert run('independent-controls-'+sys.argv[2],[sys.executable,'-B',str(P/'independent_controls.py'),sys.argv[2]],P)['exitCode']==0
    elif action=='inventory':
        assert run('inventory-supplement',[sys.executable,'-B',str(P/'inventory_supplement.py')],P)['exitCode']==0
    elif action=='cleanup':cleanup()
