#!/usr/bin/env python3
"""Owned finite Rust copies, selected commands, immutable receipts and cleanup."""
import datetime, hashlib, json, os, pathlib, shutil, subprocess, sys, tarfile, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
SCRATCH = OUT / '.scratch'
TOOLCHAIN = pathlib.Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
EXPECTED = '16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
MANIFEST = ROOT/'verification/swift-cost-retention-candidate/live-baseline-source-manifest.json'
def sha(data): return hashlib.sha256(data).hexdigest()
def encoded(obj): return (json.dumps(obj,indent=2,sort_keys=True)+'\n').encode()
def write(path,obj): path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(encoded(obj))
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def closure(base):
    return {p:sha((base/p).read_bytes()) for p in json.loads(MANIFEST.read_bytes())}
def live():
    m=closure(ROOT/'vm'); assert len(m)==132 and sha(encoded(m))==EXPECTED
    return m
def inputs():
    paths=['AGENTS.md','PLAN.md','mixer-product-plan.md','docs/swift-retention-next-design.md',
       'docs/swift-retention-next-design-review.md','verification/swift-retention-next-design-review/root-acceptance.json',
       'verification/swift-retention-next-design/seal.json','verification/swift-retention-next-design-review/seal.json',
       'verification/swift-retention-next-design/contract.json','verification/swift-retention-next-design/synthetic-traces.json',
       'verification/swift-cost-retention-candidate/common-tests.rs',str(MANIFEST.relative_to(ROOT))]
    return {p:sha((ROOT/p).read_bytes()) for p in paths}
def verify_seals():
    result=[]
    for p in ['verification/swift-retention-next-design/seal.json','verification/swift-retention-next-design-review/seal.json']:
        packet=json.loads((ROOT/p).read_bytes())
        for m in packet['members']:
            b=(ROOT/m['path']).read_bytes(); assert len(b)==m['bytes'] and sha(b)==m['sha256'],m['path']
        result.append({'seal':p,'sha256':sha((ROOT/p).read_bytes()),'members':len(packet['members'])})
    return result
def archive(mode):
    with tarfile.open(OUT/(mode+'-source.tar.gz'),'w:gz') as t:
        for p in sorted(closure(SCRATCH/mode)): t.add(SCRATCH/mode/p,arcname=p,recursive=False)
    write(OUT/(mode+'-source-manifest.json'),closure(SCRATCH/mode))
def prepare():
    m=live(); assert not SCRATCH.exists()
    seals=verify_seals(); SCRATCH.mkdir()
    st=SCRATCH.stat(); write(OUT/'ownership.json',{'path':str(SCRATCH),'device':st.st_dev,'inode':st.st_ino,'created':now()})
    for mode in ['baseline','candidate']:
        for p in m:
            dst=SCRATCH/mode/p;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'vm'/p,dst)
        (SCRATCH/('build-'+mode)).mkdir();(SCRATCH/('tmp-'+mode)).mkdir()
    write(OUT/'inputs.json',{'at':now(),'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
       'metadata':inputs(),'liveClosure':EXPECTED,'liveFileCount':132,'seals':seals,
       'limits':{'cacheBytes':16777216,'entryBytes':8388608,'entries':64,'pins':64,'tickets':86,'cacheWork':64000000,'combinedBytes':268435456},
       'scope':'isolated finite Rust host candidate only; no live integration, full target, native/UI/capture or process discovery'})
    archive('baseline');print('Exact live closure copied twice:',EXPECTED)
def run(name,mode,args):
    dest=OUT/'commands'/name;assert not dest.exists();dest.mkdir(parents=True)
    before=live(); source=closure(SCRATCH/mode);write(dest/'source-manifest.json',source)
    environment={'CARGO_BUILD_JOBS':'1','CARGO_NET_OFFLINE':'true','CARGO_TARGET_DIR':str(SCRATCH/('build-'+mode)),
       'RUSTC':str(TOOLCHAIN/'rustc'),'TMPDIR':str(SCRATCH/('tmp-'+mode)), 'PATH':str(TOOLCHAIN)+':'+os.environ['PATH']}
    argv=[str(TOOLCHAIN/'cargo')]+args
    tools={p:{'version':subprocess.check_output([str(TOOLCHAIN/p),'--version'],text=True).strip(),'sha256':sha((TOOLCHAIN/p).read_bytes())} for p in ['rustc','cargo']}
    context=inputs();write(dest/'command.json',{'at':now(),'argv':argv,'cwd':str(SCRATCH/mode),'environmentOverrides':environment,
       'timeoutSeconds':240,'tools':tools,'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
       'sourceManifestSHA256':sha(encoded(source)),'liveClosureBefore':sha(encoded(before)),'inputsBefore':context})
    start=time.monotonic();code=None;error=None
    try:
        p=subprocess.run(argv,cwd=SCRATCH/mode,env=os.environ|environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=240)
        stdout,stderr,code=p.stdout,p.stderr,p.returncode
    except subprocess.TimeoutExpired as e:
        stdout,stderr=e.stdout or b'',e.stderr or b'';error='timeout (synchronous child terminated)'
    (dest/'stdout').write_bytes(stdout);(dest/'stderr').write_bytes(stderr)
    after=live();assert before==after;assert source==closure(SCRATCH/mode)
    after_context=inputs(); changes={p:{'before':h,'after':after_context[p]} for p,h in context.items() if h!=after_context[p]}
    assert all(p in ['PLAN.md'] for p in changes),changes
    write(dest/'result.json',{'at':now(),'exitCode':code,'error':error,'seconds':round(time.monotonic()-start,3),
      'liveClosureAfter':sha(encoded(after)),'sourceUnchanged':True,'metadataOnlyChanges':changes,
      'stdoutSHA256':sha(stdout),'stderrSHA256':sha(stderr),'stdoutBytes':len(stdout),'stderrBytes':len(stderr)})
    print(name,'exit',code,'seconds',round(time.monotonic()-start,3));print(stdout.decode(errors='replace')[-2000:]);print(stderr.decode(errors='replace')[-2000:])
    if code!=0:sys.exit(code or 124)
def cleanup():
    owner=json.loads((OUT/'ownership.json').read_bytes());st=SCRATCH.stat()
    assert [st.st_dev,st.st_ino]==[owner['device'],owner['inode']]
    write(OUT/'cleanup-preflight.json',{'at':now(),'ownership':owner,'matchingIdentity':True,'liveClosure':sha(encoded(live())),
       'ownedTreeBytes':sum(p.stat().st_size for p in SCRATCH.rglob('*') if p.is_file()),'synchronousChildrenOnly':True})
    shutil.rmtree(SCRATCH);write(OUT/'cleanup.json',{'at':now(),'ownership':owner,'removed':not SCRATCH.exists(),
       'scope':'only the exact owned scratch tree, containing copied sources and compiler/temp products; no unrelated processes or files'})
    print('Owned scratch removed')
if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':run(sys.argv[2],sys.argv[3],sys.argv[4:])
    elif sys.argv[1]=='archive':archive(sys.argv[2])
    elif sys.argv[1]=='cleanup':cleanup()
    else:raise SystemExit('unknown action')
