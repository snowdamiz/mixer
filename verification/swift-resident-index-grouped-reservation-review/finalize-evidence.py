from pathlib import Path
import datetime,difflib,hashlib,json,os,shutil,subprocess,sys,tarfile
P=Path(__file__).resolve().parent
ROOT=P.parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(P/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def manifest(s):return {str(f.relative_to(s)):sha(f) for f in sorted(s.rglob('*')) if f.is_file()}
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

traces={}
for variant in ['baseline','selected']:
 out=(P/'commands'/(variant+'-frozen')/'stdout').read_bytes()
 start=out.index(b'layout FunctionCache ')
 end=out.index(b'\n',out.index(b'allocation release ',start))+1
 traces[variant]=out[start:end]
 (P/(variant+'-frozen-trace.txt')).write_bytes(traces[variant])
assert traces['baseline']==traces['selected']
assert traces['selected']==(ROOT/'verification/swift-index-ticket-storage-diagnosis/literal-frozen-trace.txt').read_bytes()
write('frozen-comparison.json',{'equal':True,'alsoEqualsSealedDiagnosisLiteral':True,'bytes':len(traces['selected']),'sha256':hashlib.sha256(traces['selected']).hexdigest(),'extraction':'layout FunctionCache through final allocation release newline; excludes libtest framing','commands':['commands/baseline-frozen','commands/selected-frozen']})

summaries={}
for d in sorted((P/'commands').iterdir()):
 r=json.loads((d/'receipt.json').read_text())
 assert r['sourceUnchanged'] and r['stdoutEOF'] and r['stderrEOF'] and r['processGroupGone']
 assert not r['timedOut'] and r['signal'] is None
 assert r['executableBeforeSHA256']==r['executableAfterSHA256']
 out=(d/'stdout').read_text()
 result=[line for line in out.splitlines() if line.startswith('test result:')]
 summaries[d.name]={'exitCode':r['exitCode'],'testResult':result,'receiptSHA256':sha(d/'receipt.json'),'executableSHA256':r['executableBeforeSHA256'],'sourceManifestSHA256':r['sourceManifestSHA256']}
 assert r['exitCode']==(101 if d.name=='selected-independent' else 0)
write('command-summary.json',summaries)

source=ROOT/'verification/swift-resident-index-grouped-reservation/source'
for variant in ['baseline','selected']:
 s=P/'scratch'/variant
 expected=json.loads((P/(variant+'-overlay-source-manifest.json')).read_text())
 assert manifest(s)==expected
 if variant=='selected':
  clean=source
  changes=[n for n in expected if expected[n]!=json.loads((P/'selected-source-manifest.json').read_text())[n]]
  delta=''.join(''.join(difflib.unified_diff((clean/n).read_text().splitlines(True),(s/n).read_text().splitlines(True),fromfile='clean-selected/'+n,tofile='selected-review/'+n)) for n in changes)
 else:
  f='src/experimental_swift_reactor/cache_tests.rs'
  original=(s/f).read_text().split('// Independently authored review control, appended to the actual cache tests.')[0]
  # overlay.py appends exactly one newline before the review source.
  original=original[:-1]
  assert hashlib.sha256(original.encode()).hexdigest()==json.loads((P/'baseline-source-manifest.json').read_text())[f]
  delta=''.join(difflib.unified_diff(original.splitlines(True),(s/f).read_text().splitlines(True),fromfile='clean-baseline/'+f,tofile='baseline-review/'+f))
 (P/(variant+'-review-overlay.patch')).write_text(delta)

archive=P/'review-sources.tar.gz'
with tarfile.open(archive,'w:gz') as a:
 for variant in ['baseline','selected']:
  s=P/'scratch'/variant
  for f in sorted(s.rglob('*')):
   if f.is_file():a.add(f,arcname=str(Path(variant)/f.relative_to(s)),recursive=False)
with tarfile.open(archive) as a:
 files=a.getmembers();assert len(files)==264
 for member in files:
  variant,relative=member.name.split('/',1)
  expected=json.loads((P/(variant+'-overlay-source-manifest.json')).read_text())[relative]
  assert hashlib.sha256(a.extractfile(member).read()).hexdigest()==expected

tools=json.loads((P/'tools.json').read_text())
for name,argv in [('python',[sys.executable,'--version']),('patch',['/usr/bin/patch','--version'])]:
 result=subprocess.run(argv,capture_output=True)
 tools[name]={'path':argv[0],'sha256':sha(Path(argv[0])),'argv':argv,'exitCode':result.returncode,'stdout':result.stdout.decode(),'stderr':result.stderr.decode()}
write('tools.json',tools)

# Preserve rather than reinterpret the diagnosis packet's two failed test runs.
diag=ROOT/'verification/swift-index-ticket-storage-diagnosis'
seal=json.loads((diag/'seal.json').read_text())
retained={}
for command in ['grouped-cache','grouped-cache-final']:
 for name in ['receipt.json','stdout','stderr']:
  relative='commands/'+command+'/'+name
  assert sha(diag/relative)==seal['files'][relative]
  dest=P/'diagnosis-initial-failures'/command/name
  dest.parent.mkdir(parents=True,exist_ok=True)
  shutil.copy2(diag/relative,dest)
  retained[relative]=sha(dest)
write('diagnosis-initial-failures.json',{'diagnosisSealSHA256':sha(diag/'seal.json'),'files':retained,'interpretation':'Old ticket literal74 versus actual73, and the old header+patch+index capacity boundary. These failures remain failures; only accounting expectations were corrected by the selected source.'})

scratch=P/'scratch'
paths=[scratch/n for n in ['baseline','selected','baseline-target','selected-target']]
assert set(scratch.iterdir())==set(paths)
holders=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(scratch)],capture_output=True,timeout=30)
(P/'cleanup-holders.stdout').write_bytes(holders.stdout)
(P/'cleanup-holders.stderr').write_bytes(holders.stderr)
assert holders.returncode==1 and not holders.stdout,holders.stdout.decode()
file_count=sum(1 for f in scratch.rglob('*') if f.is_file())
bytes_removed=sum(f.stat().st_size for f in scratch.rglob('*') if f.is_file())
shutil.rmtree(scratch)
write('cleanup.json',{'observedUTC':now(),'scope':'Only this review packet owned scratch copied source and target directories','removedPaths':[str(x) for x in paths],'removedRegularFiles':file_count,'removedLogicalBytes':bytes_removed,'sourceArchiveSHA256':sha(archive),'archiveMembersVerified':264,'lsofArgv':['/usr/sbin/lsof','-nP','+D',str(scratch)],'lsofExitCode':holders.returncode,'lsofSHA256':sha(Path('/usr/sbin/lsof')),'lsofStdoutSHA256':sha(P/'cleanup-holders.stdout'),'lsofStderrSHA256':sha(P/'cleanup-holders.stderr'),'scratchAbsent':not scratch.exists(),'allCommandGroupsGone':True,'nativeSimulatorEmulatorOrOtherProjectProcessesTouched':False})
assert manifest(source)==json.loads((P/'selected-source-manifest.json').read_text())
print('Frozen trace identical:',len(traces['selected']),'bytes; archived 264 verified source members; owned scratch removed:',bytes_removed,'bytes.')
