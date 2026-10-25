from pathlib import Path
import datetime, difflib, hashlib, json, shutil, subprocess

ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
PACKET = ROOT / 'verification/swift-resident-index-grouped-reservation-review'
SELECTED = ROOT / 'verification/swift-resident-index-grouped-reservation'
DIAG = ROOT / 'verification/swift-index-ticket-storage-diagnosis'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n, v): (PACKET / n).write_text(json.dumps(v, indent=2, sort_keys=True)+'\n')
def manifest(p): return {str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file()}

expected = '3ffa1055e462be74c10ee9830bf891bbd196a896dfc7a66dc6befe2a6d9bb70f'
assert sha(SELECTED/'source-manifest.json') == expected
selected_manifest=json.loads((SELECTED/'source-manifest.json').read_text())
assert len(selected_manifest)==132
assert manifest(SELECTED/'source') == selected_manifest
assert sha(DIAG/'seal.json')=='44e3aeedcbca786326a565683929ffb1a4e30428898356b50633985ce9f1812d'
assert sha(DIAG/'receipt.json')=='9e2fff41f1b2099071fa394213d10d4d123777bff257a650b2e74fbab25742a9'
seal=json.loads((DIAG/'seal.json').read_text())
inputs=['input-source-manifest.json','implementation-production.patch','implementation-accounting-expectations.patch','clean-handoff.json','literal-frozen-trace.txt','frozen-comparison.json']
for name in inputs: assert sha(DIAG/name)==seal['files'][name]
assert sha(ROOT/'docs/swift-resident-index-grouped-reservation-contract.md')==json.loads((SELECTED/'selection.json').read_text())['contractSHA256']
write('selected-source-manifest.json',selected_manifest)
scratch=PACKET/'scratch'
assert not scratch.exists()
scratch.mkdir()
for variant in ['selected','baseline']:
 shutil.copytree(SELECTED/'source',scratch/variant)
baseline=scratch/'baseline'
p=baseline/'src/experimental_swift_reactor/cache.rs'
p.write_text(p.read_text().replace('let Some(header) = exclusive.checked_add(cleanup) else {\n        return None;\n    };','let Some(header) = exclusive.checked_add(cleanup) else { return None; };'))
patches=[]
for name in ['implementation-production.patch','implementation-accounting-expectations.patch']:
 argv=['/usr/bin/patch','--batch','--fuzz=0','-R','-p1','-i',str(DIAG/name)]
 result=subprocess.run(argv,cwd=baseline,capture_output=True)
 (PACKET/(name+'.reverse.stdout')).write_bytes(result.stdout)
 (PACKET/(name+'.reverse.stderr')).write_bytes(result.stderr)
 patches.append({'argv':argv,'cwd':str(baseline),'exitCode':result.returncode,'stdoutSHA256':hashlib.sha256(result.stdout).hexdigest(),'stderrSHA256':hashlib.sha256(result.stderr).hexdigest()})
 assert result.returncode==0
baseline_manifest=json.loads((DIAG/'input-source-manifest.json').read_text())
assert manifest(baseline)==baseline_manifest
assert sha(DIAG/'input-source-manifest.json')=='02fd25a32b05cf8c4b10e0f68df029d8851e14610ccecbec772be09af5073f8d'
write('baseline-source-manifest.json',baseline_manifest)
changes=[n for n in selected_manifest if selected_manifest[n]!=baseline_manifest[n]]
assert changes==['src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs']
diff=''.join(''.join(difflib.unified_diff((baseline/n).read_text().splitlines(True),(SELECTED/'source'/n).read_text().splitlines(True),fromfile='baseline/'+n,tofile='selected/'+n)) for n in changes)
(PACKET/'selected-delta.patch').write_text(diff)
write('preparation.json',{'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevision':'be472ce6424a691de5673e3438d2768264827d23','selectedManifestSHA256':expected,'selectedMembersVerified':132,'baselineMembersReconstructedAndVerified':132,'baselineManifestSHA256':sha(DIAG/'input-source-manifest.json'),'changedFiles':changes,'patchReverseCommands':patches,'diagnosisInputs':{n:sha(DIAG/n) for n in inputs},'excludedHostedSourcesRead':False,'liveSourceOrGitOperations':False})
print('Verified 132 selected source members; reconstructed and verified 132 clean baseline members; exactly two selected changes.')
