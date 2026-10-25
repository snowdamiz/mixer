#!/usr/bin/env python3
"""One offline finite actual-cache fixture. No full reactor build or execution."""
from pathlib import Path
import datetime,difflib,gzip,hashlib,json,os,platform,shutil,signal,subprocess,sys,tarfile,time
H=Path(__file__).resolve().parent;R=H.parent.parent
S=H/'owned-source';B=H/'owned-target';T=H/'owned-tmp'
CLOSURE='16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v): (H/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def manifest(p):
    paths=[p/'Cargo.toml',p/'Cargo.lock']+[x for top in ('src','include','tests') for x in (p/top).rglob('*') if x.is_file()]
    return {str(x.relative_to(p)):sha(x) for x in sorted(paths)}
def replace(s,old,new):
    assert s.count(old)==1,(old[:80],s.count(old));return s.replace(old,new)
def group(g):
    out=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,comm='],text=True,timeout=10)
    return [x.strip() for x in out.splitlines() if len(x.split())>=2 and int(x.split()[1])==g]
def holders(path):
    argv=['/usr/sbin/lsof','-nP','+D',str(path)]
    q=subprocess.run(argv,capture_output=True,text=True,timeout=20)
    return {'argv':argv,'exitCode':q.returncode,'stdout':q.stdout,'stderr':q.stderr}
assert not (H/'command.json').exists(),'one finite fixture already recorded'
assert not any(p.exists() for p in (S,B,T))
baseline=R/'verification/swift-decode-plan-root-integration/live-source-manifest.json'
assert sha(baseline)==CLOSURE
bound=json.loads(baseline.read_text());assert len(bound)==132 and manifest(R/'vm')==bound
save('baseline-manifest.json',bound);save('live-source-before.json',manifest(R/'vm'))
refs=['AGENTS.md','PLAN.md','STATUS.md','mixer-product-plan.md',
      'docs/swift-decode-plan-integration.md','docs/swift-cache-remaining-work-diagnosis.md','docs/swift-cache-work-attribution-result.md',
      'verification/swift-decode-plan-root-integration/acceptance.json',
      'verification/swift-exact-reactor-after-plan-reuse/result-seal.json',
      'verification/swift-exact-reactor-after-plan-reuse/target-once-events.json',
      'verification/swift-exact-reactor-after-plan-reuse/target-once-result.json',
      'verification/swift-exact-reactor-after-plan-reuse/phase-counters.json',
      'verification/swift-exact-reactor-after-plan-reuse/consuming-cleanup-audit.json',
      'verification/swift-exact-reactor-after-plan-reuse/target-once-classification.json']
assert sha(R/refs[8])=='8f04098c444d63e9d638c32e22297eccdad346222241529ef710c524473e7526'
save('input-bindings.json',{n:sha(R/n) for n in refs})
for n in bound:
    p=S/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/'vm'/n,p)
# No generic algorithm changes: cfg(test) default-no-op site/completion callbacks.
p=S/'src/experimental/cache/borrowed.rs';s=p.read_text()
s=replace(s,'    fn step(&mut self, _: CacheStep) {}','    fn step(&mut self, _: CacheStep) {}\n    #[cfg(test)] fn diagnostic_site(&mut self, _: u8) {}\n    #[cfg(test)] fn diagnostic_completed(&mut self) {}')
for old,new in [
 ('    meter.step(CacheStep::Lookup);\n    meter.work(1)?;','    meter.step(CacheStep::Lookup);\n    #[cfg(test)] meter.diagnostic_site(1);\n    meter.work(1)?;'),
 ('    let mut pin_slot = None;','    #[cfg(test)] meter.diagnostic_site(2);\n    let mut pin_slot = None;'),
 ('    let hit = M::resident_lookup','    #[cfg(test)] meter.diagnostic_site(3);\n    let hit = M::resident_lookup'),
 ('        meter.work(parts.slots.len() as u64)?;','        #[cfg(test)] meter.diagnostic_site(8);\n        meter.work(parts.slots.len() as u64)?;'),
 ('        while empty.is_none() || base + remaining + bytes > capacity {','        #[cfg(test)] meter.diagnostic_site(9);\n        while empty.is_none() || base + remaining + bytes > capacity {'),
 ('        meter.work(MAX_ENTRIES as u64)?;','        #[cfg(test)] meter.diagnostic_site(10);\n        meter.work(MAX_ENTRIES as u64)?;'),
 ('                M::resident_remove(parts.slots','                #[cfg(test)] meter.diagnostic_site(11);\n                M::resident_remove(parts.slots'),
 ('        if let Err(error) =\n            M::resident_insert','        #[cfg(test)] meter.diagnostic_site(14);\n        if let Err(error) =\n            M::resident_insert'),
 ('        meter.usage_mut().decoded(next_decodes, bytes);','        meter.usage_mut().decoded(next_decodes, bytes);\n        #[cfg(test)] meter.diagnostic_completed();'),
 ('        meter.step(CacheStep::Publication);','        meter.step(CacheStep::Publication);\n        #[cfg(test)] meter.diagnostic_site(15);'),
]:s=replace(s,old,new)
p.write_text(s)
p=S/'src/experimental_swift_reactor/cache.rs';s=p.read_text()
s=replace(s,'        self.control\n            .work_with_wasi(Work::Cache, n, self.cursor, self.observation())','        let result = self.control\n            .work_with_wasi(Work::Cache, n, self.cursor, self.observation());\n        #[cfg(test)] super::cache_tests::remaining_plan_work(n, result.is_ok());\n        result')
s=replace(s,'    fn step(&mut self, step: CacheStep) {','    #[cfg(test)] fn diagnostic_site(&mut self, site: u8) { super::cache_tests::remaining_plan_site(site); }\n    #[cfg(test)] fn diagnostic_completed(&mut self) { super::cache_tests::remaining_plan_completed(); }\n    fn step(&mut self, step: CacheStep) {')
# Only scan and build_payload call this exact policy statement.
old='        let policy = policy(snapshot, body, meter)?;';assert s.count(old)==2
position=s.index(old);s=s[:position]+s[position:].replace(old,'        #[cfg(test)] meter.diagnostic_site(4);\n'+old,1)
position=s.rindex(old);s=s[:position]+s[position:].replace(old,'        #[cfg(test)] meter.diagnostic_site(12);\n'+old,1)
for old,new in [
 ('        meter.work(1)?; // requested identity hash,','        #[cfg(test)] meter.diagnostic_site(5);\n        meter.work(1)?; // requested identity hash,'),
 ('                return Ok(plan.counts);','                #[cfg(test)] super::cache_tests::remaining_plan_event(2);\n                return Ok(plan.counts);'),
 ('        meter.step(CacheStep::ScanReset);','        #[cfg(test)] super::cache_tests::remaining_plan_event(if scratch.plans[index].is_some() {1} else {0});\n        meter.step(CacheStep::ScanReset);'),
 ('        meter.step(CacheStep::Scan);','        meter.step(CacheStep::Scan);\n        #[cfg(test)] meter.diagnostic_site(6);'),
 ('        meter.work(PLAN_CELL_CREDITS + 3)?;','        #[cfg(test)] meter.diagnostic_site(7);\n        meter.work(PLAN_CELL_CREDITS + 3)?;\n        #[cfg(test)] super::cache_tests::remaining_plan_event(3);'),
 ('        meter.step(CacheStep::Build);','        meter.step(CacheStep::Build);\n        #[cfg(test)] meter.diagnostic_site(13);'),
]:s=replace(s,old,new)
p.write_text(s)
p=S/'src/experimental_swift_reactor/cache_tests.rs';p.write_bytes(p.read_bytes()+b'\n'+(H/'finite-hook.rs').read_bytes())
modified=manifest(S);changed=[n for n in bound if bound[n]!=modified[n]]
assert changed==['src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs']
save('copied-source-manifest.json',modified)
(H/'instrumentation.patch').write_text(''.join(''.join(difflib.unified_diff((R/'vm'/n).read_text().splitlines(True),(S/n).read_text().splitlines(True),fromfile='vm/'+n,tofile='isolated/'+n)) for n in changed))
T.mkdir();identities={str(p):{'device':p.stat().st_dev,'inode':p.stat().st_ino} for p in (S,T)}
toolchain=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
env={k:os.environ[k] for k in ('HOME','USER','LOGNAME') if k in os.environ}
env.update(PATH=str(toolchain)+':/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',CARGO_TARGET_DIR=str(B),CARGO_BUILD_JOBS='2',CARGO_NET_OFFLINE='true',CARGO_INCREMENTAL='0',RUST_TEST_THREADS='1',TMPDIR=str(T))
versions={'python':{'path':sys.executable,'sha256':sha(Path(sys.executable).resolve()),'version':sys.version},'platform':platform.platform()}
for n,flags in [('rustc',['-vV']),('cargo',['-V'])]:
    q=subprocess.run([str(toolchain/n),*flags],capture_output=True,text=True,env=env,check=True,timeout=10)
    versions[n]={'path':str(toolchain/n),'sha256':sha(toolchain/n),'stdout':q.stdout,'stderr':q.stderr}
save('tools.json',versions)
argv=[str(toolchain/'cargo'),'test','--lib','--locked','--offline','--no-default-features','--features','experimental-swift-reactor','--release','experimental_swift_reactor::cache_tests::remaining_plan_actual_cache_finite','--','--exact','--nocapture','--test-threads=1']
start=time.monotonic();began=datetime.datetime.now(datetime.timezone.utc).isoformat();signals=[]
with (H/'finite.stdout').open('wb') as out,(H/'finite.stderr').open('wb') as err:
    q=subprocess.Popen(argv,cwd=S,env=env,stdout=out,stderr=err,start_new_session=True)
    save('started.json',{'argv':argv,'cwd':str(S),'environment':env,'pid':q.pid,'processGroup':q.pid,'beganUTC':began,'timeoutSeconds':120})
    try: code=q.wait(timeout=120);timed_out=False
    except subprocess.TimeoutExpired:
        timed_out=True;assert group(q.pid);os.killpg(q.pid,signal.SIGTERM);signals.append('SIGTERM')
        try:code=q.wait(timeout=3)
        except subprocess.TimeoutExpired:os.killpg(q.pid,signal.SIGKILL);signals.append('SIGKILL');code=q.wait(timeout=3)
record={'argv':argv,'cwd':str(S),'environment':env,'beganUTC':began,'elapsedSeconds':time.monotonic()-start,'exitCode':code,'timedOut':timed_out,'pid':q.pid,'processGroup':q.pid,'signalsSent':signals,'timeoutSeconds':120,'sourceManifestSHA256':sha(H/'copied-source-manifest.json'),'stdoutSHA256':sha(H/'finite.stdout'),'stderrSHA256':sha(H/'finite.stderr')}
save('command.json',record)
if B.exists():identities[str(B)]={'device':B.stat().st_dev,'inode':B.stat().st_ino}
save('cleanup-identities.json',identities)
rows=[]
for line in (H/'finite.stdout').read_text().splitlines():
    if 'PLAN_REMAINING ' in line:
        # Rust Debug Option uses Some/None; normalize the single fixed field.
        value=line.split('PLAN_REMAINING ',1)[1].replace('None','null').replace('Some([','[').replace(']),','],')
        rows.append(json.loads(value))
save('finite-observations.json',{'observations':rows})
members=group(q.pid);checks={str(p):holders(p) for p in (S,B,T) if p.exists()}
save('cleanup-preflight.json',{'groupMembers':members,'holders':checks,'identities':identities})
assert not members
assert all(x['exitCode']==1 and not x['stdout'] and not x['stderr'] for x in checks.values())
assert manifest(S)==modified and manifest(R/'vm')==bound
# Retain exact isolated source bytes; no compiled executable or guest payload needed.
with tarfile.open(H/'isolated-source.tar.gz','w:gz') as archive:
    for n in modified:archive.add(S/n,arcname=n,recursive=False)
logical=sum(p.stat().st_size for d in (S,B,T) for p in d.rglob('*') if p.is_file())
for p in (S,B,T):
    if p.exists():assert identities[str(p)]=={'device':p.stat().st_dev,'inode':p.stat().st_ino};shutil.rmtree(p)
save('live-source-after.json',manifest(R/'vm'))
save('cleanup.json',{'processGroupMembers':members,'signalsSent':signals,'removedLogicalBytes':logical,'ownedPathsAbsent':all(not p.exists() for p in (S,B,T)),'liveSourceUnchanged':manifest(R/'vm')==bound,'otherProjectsTouched':False,'nativeInstancesUsed':False})
print(json.dumps({'exitCode':code,'observations':len(rows),'elapsedSeconds':record['elapsedSeconds'],'cleanupComplete':True}))
raise SystemExit(code)
