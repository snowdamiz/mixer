from pathlib import Path
import os,sys,hashlib,json,re,tarfile,gzip,shutil,datetime,subprocess,platform
P=Path(__file__).resolve().parent;R=P.parents[1];S=P/'.scratch'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
base=json.loads((P/'baseline-source-manifest.json').read_text());candidate=json.loads((P/'candidate-manifest.json').read_text())
assert len(base)==len(candidate)==132
assert {n:sha(R/'vm'/n)for n in base}==base
assert {n:sha(S/'baseline'/n)for n in base}==base
assert {n:sha(S/'candidate'/n)for n in base}==candidate
changed=[n for n in base if base[n]!=candidate[n]];assert sorted(changed)==sorted(['src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/control.rs'])
commands={}
for d in sorted((P/'commands').iterdir()):
 if not(d/'result.json').exists():continue
 result=json.loads((d/'result.json').read_text());assert result['status']=='exited' and result['sourceUnchanged'] and result['live132Unchanged']
 commands[d.name]=result
for n in ['baseline-original-swift','candidate-final-swift','candidate-final-finite','baseline-generic-private','candidate-generic-private','baseline-generic-integration','candidate-generic-integration']:assert commands[n]['exitCode']==0
names=lambda path:set(re.findall(r'^test (\S+) \.\.\.',path.read_text(),re.M))
original=names(P/'commands/baseline-original-swift/stdout.txt');actual=names(P/'commands/candidate-final-swift/stdout.txt');assert len(original)==340 and len(actual)==356 and original<=actual and all('::ordered_'in n for n in actual-original)
for group in ['generic-private','generic-integration']:assert sha(P/f'commands/baseline-{group}/stdout.txt')==sha(P/f'commands/candidate-{group}/stdout.txt')
# Preserve exactly the synchronous executed binary names reported by Cargo.
bin_dir=P/'binaries';bin_dir.mkdir(exist_ok=False);binary_receipts=[];seen=set()
for d in sorted((P/'commands').iterdir()):
 if not(d/'stderr.txt').exists():continue
 for value in re.findall(r'Running [^\n]* \((/[^)]+)\)',(d/'stderr.txt').read_text()):
  path=Path(value)
  if path in seen or not path.exists():continue
  assert path.is_relative_to(S);seen.add(path);h=sha(path)
  with path.open('rb')as a,gzip.open(bin_dir/(h+'.gz'),'wb')as b:shutil.copyfileobj(a,b)
  binary_receipts.append({'path':str(path),'sha256':h,'bytes':path.stat().st_size,'archive':str((bin_dir/(h+'.gz')).relative_to(R)),'scope':'final available executable at named path; not retrospective identity of superseded binaries'})
for path in [P/'writer-tests',S/'tmp-candidate/writer-layout']:
 if path.exists():
  h=sha(path)
  with path.open('rb')as a,gzip.open(bin_dir/(h+'.gz'),'wb')as b:shutil.copyfileobj(a,b)
  binary_receipts.append({'path':str(path),'sha256':h,'bytes':path.stat().st_size,'archive':str((bin_dir/(h+'.gz')).relative_to(R))})
save(P/'binary-manifest.json',binary_receipts)
# Raw fixtures include invalid/unfinished streams and original-result receipts.
fixtures=[]
with tarfile.open(P/'raw-fixtures.tar.gz','w:gz')as t:
 for d in sorted((S/'tmp-candidate').iterdir()):
  if not d.is_dir() or d.name=='reversal':continue
  for f in sorted(d.iterdir()):
   if not f.is_file()or not f.name.startswith('ordered-'):continue
   assert f.stat().st_size<=536871936
   st=f.stat();fixtures.append({'path':str(f.relative_to(S)),'sha256':sha(f),'bytes':st.st_size,'dev':st.st_dev,'ino':st.st_ino});t.add(f,arcname=str(f.relative_to(S)),recursive=False)
save(P/'raw-fixture-manifest.json',fixtures)
# Bind the finite custody producer separately from target-driver acceptance.
py=Path(sys.executable).resolve()
save(P/'capture-provenance.json',{'argv':[str(py),'-B',str(P/'capture_finite.py'),'candidate-final-finite'],'python':sys.version,'pythonExecutableSHA256':sha(py),'sourceSHA256':sha(P/'capture_finite.py'),'receiptSHA256':sha(P/'candidate-final-finite-capture.json'),'scope':'one successful finite copy attempt per newly produced source; adversarial custody protocol remains pending'})
# Preserve control-source prefix and Cargo bytes; source reversal was actual.
assert (S/'candidate/src/experimental_swift_reactor/control.rs').read_bytes().startswith((S/'baseline/src/experimental_swift_reactor/control.rs').read_bytes())
for name in ['Cargo.toml','Cargo.lock']:assert (S/'candidate'/name).read_bytes()==(S/'baseline'/name).read_bytes()
tool=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin')
record={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'provisional finite feasibility, independent review and specified qualification gaps pending','revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'platform':platform.platform(),'changedCopiedFiles':changed,'live132Unchanged':True,'counts':{'originalSwift':340,'candidateSwift':356,'newFinite':16,'genericPrivateEach':5,'genericIntegrationEach':10},'peaks':{'callback':12282,'footer':13394,'retirement':15578,'ceiling':16384,'allPhaseUnion':19554},'cargoUnchanged':True,'controlOriginalPrefixUnchanged':True,'noTargetNativeCaptureOrProcessDiscovery':True,'commands':commands,'python':{'path':str(py),'sha256':sha(py),'version':sys.version},'tools':{n:{'path':str(tool/n),'sha256':sha(tool/n),'version':subprocess.check_output([str(tool/n),'--version'],text=True).strip()}for n in ['cargo','rustc']},'patchTool':{'path':'/usr/bin/patch','sha256':sha(Path('/usr/bin/patch')),'versionOutput':subprocess.run(['/usr/bin/patch','-v'],capture_output=True,text=True).stdout}}
save(P/'result.json',record)
# All runner-owned synchronous children returned before any deletion; no
# process discovery is used during the explicit user pause. Each initial child
# directory must still have the exact recorded device/inode, no symlink.
ownership=json.loads((P/'scratch-ownership.json').read_text());cleanup=[]
for name,identity in ownership.items():
 d=S/name;st=d.lstat();assert not d.is_symlink()and {'dev':st.st_dev,'ino':st.st_ino}==identity
 cleanup.append({'path':str(d),'dev':st.st_dev,'ino':st.st_ino,'removed':True});shutil.rmtree(d)
assert not list(S.iterdir());rootstat=S.stat();S.rmdir()
loose=P/'writer-tests'
if loose.exists():st=loose.lstat();assert not loose.is_symlink();loose.unlink();cleanup.append({'path':str(loose),'dev':st.st_dev,'ino':st.st_ino,'removed':True})
assert {n:sha(R/'vm'/n)for n in base}==base
save(P/'cleanup.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'directories':cleanup,'scratchRoot':{'dev':rootstat.st_dev,'ino':rootstat.st_ino,'removed':True},'allOwnedCommandsExited':True,'noOtherProjectPathsTouched':True,'live132UnchangedAfterCleanup':True,'nativeOrCaptureInstancesStarted':0,'cleanupMethod':'exact owned device/inode validation, synchronous child exit receipts; no process discovery/signals'})
print('final receipt, exact available binaries/raw fixtures archived; all owned scratch removed; live132 unchanged')
