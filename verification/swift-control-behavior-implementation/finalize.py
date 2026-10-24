from pathlib import Path
import json,hashlib,gzip,tarfile,shutil,subprocess,re,collections,difflib,datetime
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];SCRATCH=Path('/tmp/mixer-swift-control-behavior-20261024');VM=SCRATCH/'vm';BASE=SCRATCH/'baseline-vm'
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def manifest(root):
 paths=[root/'Cargo.toml',root/'Cargo.lock']
 for name in ['src','tests','include']:paths+=sorted(p for p in (root/name).rglob('*') if p.is_file())
 return {str(p.relative_to(root)):sha(p) for p in paths}
base=json.loads((HERE/'baseline-manifest.json').read_text());candidate=json.loads((HERE/'starting-candidate-manifest.json').read_text());source=manifest(VM);tree=hashlib.sha256(enc(source)).hexdigest();assert tree=='241f7a6037100d29a4d277e1ec176fec55c0380b4283c17120bb8ace045318d5';assert len(source)==121;assert manifest(ROOT/'vm')==base
assert not (HERE/'seal.json').exists(),'sealed packet must not be overwritten'
(HERE/'source-manifest.json').write_bytes(enc(source))
for label,root,rows in [('baseline',BASE,base),('implementation',VM,source)]:
 assert manifest(root)==rows
 with tarfile.open(HERE/(label+'-source.tar.gz'),'w:gz') as archive:
  for name in rows:archive.add(root/name,arcname='vm/'+name,recursive=False)
shutil.copyfile(ROOT/'verification/swift-control-accounting-candidate-2/source.patch',HERE/'accepted-candidate-2.patch')
def patch(before_root,before,after_root,after,dest):
 output=[]
 for name in sorted(set(before)|set(after)):
  if before.get(name)==after.get(name):continue
  left=(before_root/name).read_text().splitlines(True) if name in before else []
  right=(after_root/name).read_text().splitlines(True) if name in after else []
  output.extend(difflib.unified_diff(left,right,fromfile='a/'+name if name in before else '/dev/null',tofile='b/'+name if name in after else '/dev/null'))
 dest.write_text(''.join(output))
patch(BASE,base,VM,source,HERE/'source.patch')
accepted=SCRATCH/'accepted-candidate-2-vm';accepted.mkdir()
for name in base:
 p=accepted/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(BASE/name,p)
apply=[]
for label,path in [('accepted-candidate',HERE/'accepted-candidate-2.patch')]:
 p=subprocess.run(['git','apply',str(path)],cwd=accepted,capture_output=True);apply.append(dict(name=label,argv=['git','apply',str(path)],cwd=str(accepted),exitCode=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode()));assert p.returncode==0
assert manifest(accepted)==candidate
patch(accepted,candidate,VM,source,HERE/'candidate-2-delta.patch')
p=subprocess.run(['git','apply',str(HERE/'candidate-2-delta.patch')],cwd=accepted,capture_output=True);apply.append(dict(name='candidate-to-implementation',argv=['git','apply',str(HERE/'candidate-2-delta.patch')],cwd=str(accepted),exitCode=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode()));assert p.returncode==0;assert manifest(accepted)==source
replay=SCRATCH/'baseline-patch-replay-vm';shutil.copytree(BASE,replay);p=subprocess.run(['git','apply',str(HERE/'source.patch')],cwd=replay,capture_output=True);apply.append(dict(name='baseline-to-implementation',argv=['git','apply',str(HERE/'source.patch')],cwd=str(replay),exitCode=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode()));assert p.returncode==0;assert manifest(replay)==source
(HERE/'patch-reproduction.json').write_bytes(enc(dict(commands=apply,exact=True)))
# Every qualifying command binds the identical frozen source.
latest={}
for receipt in sorted((HERE/'results').glob('*/receipt.json')):
 r=json.loads(receipt.read_text());r['receipt']=str(receipt.relative_to(HERE));latest[r['name']]=r
matrix=json.loads((HERE/'matrix-summary.json').read_text());assert len(matrix)==17 and all(x['exitCode']==0 for x in matrix)
qualified=[];executables=[];(HERE/'executables').mkdir()
for task in matrix:
 r=latest[task['name']];assert r['exitCode']==0 and r['sourceTreeSHA256']==tree and r['liveVMUnchanged'];folder=HERE/Path(r['receipt']).parent;out=(folder/r['stdout']).read_text();err=(folder/r['stderr']).read_text();q=dict(name=r['name'],receipt=r['receipt'],sourceTreeSHA256=tree,exitCode=0,stdoutSHA256=sha(folder/r['stdout']),stderrSHA256=sha(folder/r['stderr']))
 if r['name'].endswith('control-frame-value-unit'):
  assert '46 passed; 0 failed;' in out;assert len(set(re.findall(r'::sc(\d\d)_',out)))==12;q['passedTests']=46;q['scGroups']=12
 elif r['name'].endswith('frozen-parity'):assert '6 passed; 0 failed;' in out;q['passedTests']=6
 if 'passedTests' in q:
  matches=re.findall(r'Running (?:unittests src/lib.rs|tests/span_control_extraction.rs) \(([^)]+)\)',err);assert len(matches)==1,(r['name'],err);binary=Path(matches[0]);assert binary.is_file();dest=HERE/'executables'/(r['name']+'.gz')
  with gzip.open(dest,'wb') as f:f.write(binary.read_bytes())
  executables.append(dict(name=r['name'],runtimeReceipt=r['receipt'],sourceTreeSHA256=tree,path=str(dest.relative_to(HERE)),uncompressedSHA256=sha(binary),uncompressedBytes=binary.stat().st_size))
 qualified.append(q)
(HERE/'executable-manifest.json').write_bytes(enc(executables))
meta=sorted((HERE/'metadata-results').glob('*/layouts.json'))[-1];layouts=json.loads(meta.read_text());assert len(layouts)==8;meta_commands=json.loads((meta.parent/'commands.json').read_text());assert all(x['exitCode']==0 for x in meta_commands)
meta_source=json.loads((meta.parent/'instrumented-manifest.json').read_text());assert manifest(SCRATCH/'metadata-vm')==meta_source
with tarfile.open(HERE/'metadata-source.tar.gz','w:gz') as archive:
 for name in meta_source:archive.add(SCRATCH/'metadata-vm'/name,arcname='vm/'+name,recursive=False)
check=sorted((HERE/'source-checks').glob('*/commands.json'))[-1].parent;cmds=json.loads((check/'commands.json').read_text());assert next(x for x in cmds if x['name']=='candidate-library-clippy')['exitCode']==0;assert all(x['identical'] and x['reservationBytes']==2912 for x in json.loads((check/'frozen-identity.json').read_text()).values())
diags={}
for label in ['baseline','candidate']:
 rows=[]
 for line in gzip.decompress((check/(label+'-broad-clippy.stdout.gz')).read_bytes()).decode().splitlines():
  try:r=json.loads(line)
  except ValueError:continue
  if r.get('reason')=='compiler-message' and r['message']['level']=='error':
   m=r['message'];s=next(s for s in m['spans'] if s['is_primary']);rows.append(dict(code=m.get('code',{}).get('code'),message=m['message'],path=s['file_name'],column=s['column_start'],line=s['line_start'],source=[x['text'] for x in s['text']]))
 diags[label]=rows
norm=lambda rows:collections.Counter(json.dumps({k:v for k,v in r.items() if k!='line'},sort_keys=True) for r in rows)
assert len(diags['baseline'])==len(diags['candidate'])==26 and norm(diags['baseline'])==norm(diags['candidate']);(check/'clippy-comparison.json').write_bytes(enc(dict(status='same-26-prior-diagnostic-identities-no-new-diagnostics',**diags)))
# Bind the exact original source producer diagnostic to the clarification.
(HERE/'original-diagnostic-binding.json').write_bytes(enc(dict(path='vm/src/experimental_swift_reactor/control.rs',sha256=base['src/experimental_swift_reactor/control.rs'],range='1599-1648',originalUnderflow=dict(stage='Cleanup',function=None,offset=None,resource=None,code='swift_run_live_underflow'),rootClarification='authorizations.json')))
revision=gzip.decompress((check/'tool-revision.stdout.gz').read_bytes()).decode().strip()
receipt=dict(schema=1,status='producer-complete-private-control-behavior-pending-independent-review',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceRevision=revision,baselineVMClosure=hashlib.sha256(enc(base)).hexdigest(),acceptedCandidate2Closure=hashlib.sha256(enc(candidate)).hexdigest(),implementationVMClosure=tree,sourceFiles=len(source),overlayFiles=sorted(str(p.relative_to(HERE/'overlay')) for p in (HERE/'overlay').rglob('*') if p.is_file()),qualifyingCommands=qualified,metadataDirectory=str(meta.parent.relative_to(HERE)),sourceChecksDirectory=str(check.relative_to(HERE)),canonicalAccountingAudit='canonical-accounting-audit.json',hookAudit='unit-hook-final-audit.json',positiveHookFields=400,production=dict(header=1514504,frame=2211968,controlPermanent=105280,controlActive=1162520),unit=dict(header=2409184,frame=3950128,controlPermanent=122456,controlActive=2325256,hookPermanent=17144,hookActive=224),frozenReservation=2912,retainedExecutables='executable-manifest.json',sourcePatch='source.patch',candidateDelta='candidate-2-delta.patch',liveVMUnchanged=True,nativeRuntime=False,physicalRuntime=False,phonesDisconnected=True,implementationAccepted=False,gaAcceptance=False,limitations=['Logical authored/canonical ownership reservation, not physical stack, optimizer temporary or RSS bound.','Original removal-underflow failure is Cleanup/None/None/resource None, with actual WASI, as root clarified; G08 remains open.','Initial three direct authoring attempts retained stdout/stderr but predate exact source-manifest collector; they are excluded from qualifying source-bound evidence.','Full dispatcher/Ready/public invoke, separate-repository immutable FieldLog release, native/final physical, signing/store/customer/operational/GA remain open.'])
(HERE/'receipt.json').write_bytes(enc(receipt))
# Retain setup/failure provenance without upgrading it to qualifying evidence.
(HERE/'initial-authoring-attempts.json').write_bytes(enc(dict(scope='non-qualifying authoring attempts, source tree not archived',attempts=[dict(name='initial-test',argv=['/opt/homebrew/opt/rustup/bin/cargo','test','--manifest-path',str(VM/'Cargo.toml'),'--lib','--features','experimental-swift-reactor','sc0','--','--nocapture','--test-threads=1'],cwd=str(ROOT),exitCode=101,reason='Rust not on inherited PATH',stdout='initial-test.stdout',stderr='initial-test.stderr'),dict(name='attempt2',argv=['cargo','test','--manifest-path',str(VM/'Cargo.toml'),'--lib','--features','experimental-swift-reactor','sc0','--','--nocapture','--test-threads=1'],cwd=str(ROOT),environment=dict(PATHPrefix='/opt/homebrew/opt/rustup/bin',CARGO_TARGET_DIR=str(SCRATCH/'target')),exitCode=0,stdout='attempt2.stdout',stderr='attempt2.stderr'),dict(name='attempt3',argv=['cargo','test','--manifest-path',str(VM/'Cargo.toml'),'--lib','--features','experimental-swift-reactor','sc0','--','--nocapture','--test-threads=1'],cwd=str(ROOT),environment=dict(PATHPrefix='/opt/homebrew/opt/rustup/bin',CARGO_TARGET_DIR=str(SCRATCH/'target')),exitCode=0,stdout='attempt3.stdout',stderr='attempt3.stderr')])))
size=subprocess.run(['du','-sk',str(SCRATCH)],capture_output=True);assert size.returncode==0;used_kib=int(size.stdout.split()[0]);shutil.rmtree(SCRATCH)
(HERE/'cleanup.json').write_bytes(enc(dict(ownedScratch=str(SCRATCH),removed=not SCRATCH.exists(),observedDiskKiB=used_kib,inventoryCommand=dict(argv=['du','-sk',str(SCRATCH)],exitCode=size.returncode,stdout=size.stdout.decode(),stderr=size.stderr.decode()),nativeInstancesStarted=0,physicalRuns=0,otherProjectProcessesTouched=False,liveVMUnchanged=manifest(ROOT/'vm')==base)))
print('frozen',tree,'121 files; 4 x46 SC/frame/value and 4 x6 Frozen tests; 8 layouts; exact accounting; scratch removed',flush=True)
