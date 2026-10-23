#!/usr/bin/env python3
"""Source-bound host-only regression collector; no target or device runner."""
import hashlib,json,os,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=HERE/'qualification'
OUT.mkdir(exist_ok=True)
ENV=dict(os.environ);ENV['PATH']='/opt/homebrew/opt/rustup/bin:'+ENV.get('PATH','');ENV['CARGO_TARGET_DIR']='/tmp/mixer-cache-regressions-final-target'
def command(args):
 start=time.monotonic();p=subprocess.run(args,cwd=ROOT,env=ENV,text=True,capture_output=True)
 return {'argv':args,'cwd':str(ROOT),'environment':{'PATH':ENV['PATH'],'CARGO_TARGET_DIR':ENV['CARGO_TARGET_DIR']},'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'seconds':time.monotonic()-start}
def manifest():
 paths=[]
 for tree in ['vm/src','vm/tests','vm/tools','vm/include']:
  paths += [p for p in (ROOT/tree).rglob('*')if p.is_file()and '__pycache__'not in p.parts]
 for name in ['vm/Cargo.toml','vm/Cargo.lock','docs/swift-cache-stage-contract.md','docs/swift-reactor-execution-stage-design.md','verification/swift-cache-stage-acceptance.json','verification/swift-cache-stage-contract/acceptance.json','verification/swift-cache-stage-contract/proposal-receipt.json','verification/swift-observation-accounting/acceptance.json']:
  paths.append(ROOT/name)
 return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(paths)}
source=manifest()
receipt={'schema':'mixer-private-swift-function-cache-regressions-v1','scope':'original small same-ABI cache fixtures and existing regression suites only; no instantiation of the 53777114-byte target, devices, release, executor or GA qualification','status':'running','revision':command(['git','rev-parse','HEAD']),'dirty_state':command(['git','status','--short']),'tools':[command(['rustc','-Vv']),command(['cargo','-V']),command(['python3','--version']),command(['node','--version'])],'source_manifest':source,'source_manifest_sha256':hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest(),'commands':[]}
def save(): (OUT/'regressions.json').write_text(json.dumps(receipt,indent=2)+'\n')
save()
features=[None,'experimental-stream-validation','experimental-function-cache','experimental-span-execution','experimental-swift-wasi','experimental-stream-validation,experimental-function-cache,experimental-span-execution,experimental-swift-wasi','experimental-swift-reactor','all']
commands=[]
for feature in features:
 for release in [False,True]:
  args=['cargo','test','--locked','--manifest-path','vm/Cargo.toml']
  if release:args+=['--release']
  if feature=='all':args+=['--all-features']
  elif feature:args+=['--features',feature]
  commands.append(args)
for release in [False,True]:
 args=['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--features','experimental-swift-reactor,experimental-span-execution']
 if release:args+=['--release']
 for test in ['differential','float_differential','experimental_oracle','span_execution_oracle']:args+=['--test',test]
 args+=['--','--ignored','--nocapture'];commands.append(args)
commands += [['cargo','clippy','--locked','--manifest-path','vm/Cargo.toml','--lib','--features','experimental-swift-reactor,experimental-span-execution','--','-D','warnings'],['cargo','clippy','--locked','--manifest-path','vm/Cargo.toml','--lib','--features','experimental-swift-reactor','--','-D','warnings'],['cargo','fmt','--manifest-path','vm/Cargo.toml','--','--check']]
for args in commands:
 if manifest()!=source:receipt['status']='source_changed';save();raise SystemExit(2)
 result=command(args)
 result['passed_counts']=[int(n)for n in re.findall(r'test result: ok\. (\d+) passed',result['stdout'])]
 result['total_passed']=sum(result['passed_counts'])
 if args[1]=='test'and result['total_passed']==0:result['zero_selection_failure']=True
 receipt['commands'].append(result)
 receipt['unchanged_source']=manifest()==source
 save()
 print(json.dumps({'argv':args,'exit':result['exit_code'],'passed':result['total_passed'],'seconds':round(result['seconds'],2)}),flush=True)
 if result['exit_code']or result.get('zero_selection_failure')or not receipt['unchanged_source']:
  receipt['status']='failed';save();raise SystemExit(1)
receipt['status']='pass';save()
