#!/usr/bin/env python3
from pathlib import Path
import hashlib,io,json,os,re,subprocess,tarfile,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];TREE=HERE/'tree';BASE='39199ae5475de5d03926807ce60add5dcb0741c2'
def sha(b):return hashlib.sha256(b).hexdigest()
def manifest():return {str(p.relative_to(TREE)):sha(p.read_bytes()) for p in sorted((TREE/'vm').rglob('*')) if p.is_file()}
map_measure=json.loads((HERE.parent/'candidate2-final-map/measurement-receipt.json').read_text())
source=map_measure['source_before_test_overlay']
assert not TREE.exists();TREE.mkdir();(HERE/'tmp').mkdir()
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','archive',BASE,'vm'],cwd=ROOT))) as archive:archive.extractall(TREE,filter='data')
for name,digest in source.items():
 data=(ROOT/name).read_bytes();assert sha(data)==digest,name
 p=TREE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
before=manifest();assert len(before)==420
(HERE/'full-input-manifest.json').write_text(json.dumps(before,indent=2)+'\n')
env=os.environ|{'PATH':'/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],'CARGO_TARGET_DIR':str(HERE/'build'),'TMPDIR':str(HERE/'tmp')}
commands=[]
def run(argv,label):
 start=time.monotonic();p=subprocess.run(argv,cwd=TREE,env=env,capture_output=True,text=True);out=p.stdout+p.stderr
 log=label+'.log';(HERE/log).write_text(out)
 one=bool(re.search(r'test result: ok\. 1 passed; 0 failed;',out))
 commands.append({'argv':argv,'cwd':str(TREE),'environment':{k:env[k] for k in ['PATH','CARGO_TARGET_DIR','TMPDIR']},'exit_code':p.returncode,'seconds':time.monotonic()-start,'output':log,'output_sha256':sha(out.encode()),'exact_one_passed':one})
 (HERE/'runs.json').write_text(json.dumps({'scope':'independent immutable candidate2 exact named assertions and original-engine replay','baseline_revision':BASE,'source_before_test_overlay':source,'full_input_manifest_sha256':sha(json.dumps(before,sort_keys=True).encode()),'commands':commands,'source_unchanged':manifest()==before},indent=2)+'\n')
 print(f'{label}: exit={p.returncode} exact_one={one}',flush=True)
 assert p.returncode==0 and one,out[-6000:]
 return p.stdout
cases=json.loads((ROOT/'verification/swift-function-cache/coverage-map.json').read_text())['tests'];assert len(cases)==18
for mode in ['debug','release']:
 flags=['--release'] if mode=='release' else []
 for case in cases:
  run(['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--all-features','--lib']+flags+['experimental_swift_reactor::cache_tests::'+case['name'],'--','--exact','--nocapture','--test-threads=1'],'named-'+mode+'-'+case['name'])
comparisons=[]
pattern=re.compile(r'^(layout |offsets |scratch |new |miss |hit |release |invalid |cancel |allocation |precedence |eviction prefix )')
for mode in ['debug','release']:
 for features,label,count,digest in [('experimental-function-cache','frozen',122,'57454094eba1b79333bf8f389c67f4531dcd9f224bc826a2a506aa4ae6c41bf8'),('experimental-swift-reactor,experimental-span-execution','swift-span',126,'fff986f56ec3eee1296059220f96107b4f6035fd4b45e3ce822bf5bd9fcc3b5f')]:
  out=run(['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--features',features,'--lib']+(['--release'] if mode=='release' else [])+['experimental::cache::tests::frozen_layout_and_trace_observation','--','--exact','--nocapture','--test-threads=1'],'legacy-'+mode+'-'+label)
  lines=[re.sub(r'^test experimental::cache::tests::frozen_layout_and_trace_observation \.\.\. ','',line) for line in out.splitlines()]
  lines=[line for line in lines if pattern.match(line)]
  observed=sha('\n'.join(lines).encode());assert len(lines)==count and observed==digest,(mode,label,len(lines),observed)
  comparisons.append({'mode':mode,'features':features,'exact_lines':count,'observed_sha256':observed,'equals_independent_original_engine_replay':True})
  (HERE/'legacy-comparisons.json').write_text(json.dumps({'comparisons':comparisons,'original_evidence_receipt':'verification/swift-function-cache-review/candidate-1-review-receipt.json','original_evidence_receipt_sha256':'835172d9a8bf3dd99b114a73b3c8735531e0b5f1ef383499e78f7c5598dc2a5d'},indent=2)+'\n')
assert manifest()==before
