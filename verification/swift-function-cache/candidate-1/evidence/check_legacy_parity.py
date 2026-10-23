#!/usr/bin/env python3
"""Replay exact current observation test against original Git legacy engine."""
import hashlib,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
ENV=dict(os.environ);ENV['PATH']='/opt/homebrew/opt/rustup/bin:'+ENV.get('PATH','')
def run(args,cwd=ROOT):
 p=subprocess.run(args,cwd=cwd,env=ENV,text=True,capture_output=True)
 return dict(argv=args,cwd=str(cwd),exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
revision='39199ae5475de5d03926807ce60add5dcb0741c2'
folder=Path(tempfile.mkdtemp(prefix='mixer-cache-baseline-'))
shutil.copytree(ROOT/'vm',folder/'vm',ignore=shutil.ignore_patterns('target','.DS_Store'))
manifest={}
current={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in list((ROOT/'vm/src').rglob('*.rs'))+[ROOT/'vm/Cargo.toml',ROOT/'vm/Cargo.lock']}
for path in ['vm/src/experimental/cache/mod.rs','vm/src/experimental/cache/decode.rs','vm/src/experimental_swift_reactor/mod.rs']:
 data=subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT)
 (folder/path).write_bytes(data);manifest[path]=hashlib.sha256(data).hexdigest()
tests=(ROOT/'vm/src/experimental/cache/tests.rs').read_text()
tests=tests[:tests.index('#[test]\nfn frozen_borrowed_transients_fit_existing_scratch')]
(folder/'vm/src/experimental/cache/tests.rs').write_text(tests)
decode=ROOT/'vm/src/experimental/cache/decode.rs'
helper=decode.read_text();helper=helper[helper.index('#[cfg(test)]\npub(super) fn frozen_offsets'):]
with (folder/'vm/src/experimental/cache/decode.rs').open('a')as f:f.write('\n'+helper)
# Private Swift cache is not selected in the original module, as in the baseline.
receipt={'scope':'original legacy cache engine replay; original synthetic fixtures only; no Swift execution','baseline_revision':revision,'baseline_engine_manifest':manifest,'baseline_directory':str(folder),'current_source_manifest':current,'current_source_manifest_sha256':hashlib.sha256(json.dumps(current,sort_keys=True).encode()).hexdigest(),'commands':[],'comparisons':[]}
pattern=re.compile(r'^(layout |offsets |scratch |new |miss |hit |release |invalid |cancel |allocation |precedence |eviction prefix )')
for mode in ['debug','release']:
 for features in ['experimental-function-cache','experimental-swift-reactor,experimental-span-execution']:
  args=['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--lib','--features',features]
  if mode=='release':args+=['--release']
  args+=['experimental::cache::tests::frozen_layout_and_trace_observation','--','--exact','--nocapture']
  old=run(args,folder);new=run(args);receipt['commands'] += [old,new]
  require(old['exit_code']==new['exit_code']==0,'legacy command failed')
  for item in [old,new]:require('1 passed; 0 failed' in item['stdout'],'zero-selection/failed observation')
  before=[line for line in old['stdout'].splitlines()if pattern.match(line)]
  after=[line for line in new['stdout'].splitlines()if pattern.match(line)]
  require(before==after,'legacy exact observation mismatch: '+mode+' '+features)
  receipt['comparisons'].append({'mode':mode,'features':features,'equal':True,'exact_observation_lines':len(before),'observation_sha256':hashlib.sha256('\n'.join(before).encode()).hexdigest()})
require(current=={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()for name in current},'source changed during legacy replay')
receipt['status']='pass'
(HERE/'legacy-parity-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt['comparisons'],indent=2))
