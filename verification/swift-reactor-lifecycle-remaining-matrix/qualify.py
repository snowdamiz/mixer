#!/usr/bin/env python3
"""Select exact lifecycle identities; retain binaries before target cleanup."""
import gzip,hashlib,json,re,subprocess,sys,shutil
from pathlib import Path
from run import HERE,CANDIDATE,TARGET,save,sha,manifest

def run(label,argv,expected=0):
 subprocess.run([sys.executable,'-B',str(HERE/'run.py'),label,*map(str,argv)],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 row=json.loads((HERE/'commands'/(label+'.json')).read_text())
 assert row['exitCode']==expected and not row['timedOut'] and row['sourceUnchanged'] and not row['remainingProcessGroup'],label
 return row

def matrix():
 expected=sorted(re.findall(r'^fn (swift_lifecycle_\w+)\(', (CANDIDATE/'src/experimental_swift_reactor/lifecycle_tests.rs').read_text(),re.M))
 prior=json.loads((HERE.parents[1]/'verification/swift-reactor-lifecycle-v3-integration/exact-tests.json').read_text())
 save(HERE/'prior-test-inventory.json',prior)
 result=[]
 for config,flags in [('swift-debug',['--features','experimental-swift-reactor']),('all-debug',['--all-features']),('swift-release',['--features','experimental-swift-reactor','--release']),('all-release',['--all-features','--release'])]:
  label='final-'+config
  build=['cargo','test','--lib','--locked','--offline','--no-default-features',*flags,'--no-run','--message-format=json-render-diagnostics']
  run(label+'-build',build)
  artifacts=[json.loads(line) for line in (HERE/'commands'/(label+'-build.stdout')).read_text().splitlines() if line.startswith('{')]
  artifact=[x for x in artifacts if x.get('reason')=='compiler-artifact' and x.get('executable')][0]
  executable=Path(artifact['executable']); bindir=HERE/'binaries';bindir.mkdir(exist_ok=True)
  binary=executable.read_bytes();archive=bindir/(config+'.gz');archive.write_bytes(gzip.compress(binary,mtime=0))
  run(label+'-list',[executable,'swift_lifecycle_','--list','--format','terse'])
  listed=[line.removesuffix(': test') for line in (HERE/'commands'/(label+'-list.stdout')).read_text().splitlines() if line.endswith(': test')]
  assert sorted(x.rsplit('::',1)[-1] for x in listed)==expected,(config,'inventory')
  run(label+'-execute',[executable,'swift_lifecycle_','--test-threads=1'])
  output=(HERE/'commands'/(label+'-execute.stdout')).read_text()
  passed=re.findall(r'^test (\S+) \.\.\. ok$',output,re.M)
  assert sorted(passed)==sorted(listed),(config,'execution identity mismatch')
  assert f'test result: ok. {len(expected)} passed; 0 failed; 0 ignored;' in output
  result.append({'configuration':config,'commands':[label+'-'+x for x in ['build','list','execute']],'listed':listed,'passed':passed,'ignored':[],'executablePath':str(executable),'executableSHA256':hashlib.sha256(binary).hexdigest(),'archive':str(archive.relative_to(HERE)),'archiveSHA256':sha(archive),'artifact':artifact})
  save(HERE/'configuration-results.json',result)
  print(config,len(passed),'passed',flush=True)
 save(HERE/'candidate-manifest.json',manifest())
 print('FINAL_MATRIX_OK',len(expected),len(expected)*len(result),flush=True)

def negative():
 fixtures=HERE/'negative';fixtures.mkdir(exist_ok=True)
 cases={
 'external-construction':('use mixer_vm::experimental_swift_reactor::execution::SwiftReactorInstance;\nfn main() {}\n','E0603'),
 'external-forged-request':('use mixer_vm::experimental_swift_reactor::execution::frame_operations::memory_growth_operations::lifecycle::{Request,Reply};\nfn main() {}\n','E0603'),
 'external-pin-escape':('use mixer_vm::experimental_swift_reactor::cache::SwiftFunctionPin;\nfn main() {}\n','E0603'),
 'external-arbitrary-invocation':('fn main() { mixer_vm::experimental_swift_reactor::invoke_function(35); }\n','E0425')}
 base=['rustc','--edition=2021','--crate-name','mixer_vm','src/lib.rs','--cfg','feature="experimental-stream-validation"','--cfg','feature="experimental-swift-wasi"','--cfg','feature="experimental-swift-reactor"']
 metadata=TARGET/'libmixer_vm_negative.rmeta'
 run('negative2-metadata-build',[*base,'--crate-type','rlib','--emit=metadata','-o',metadata])
 results=[]
 for name,(source,code) in cases.items():
  file=fixtures/(name.replace('-','_')+'.rs');file.write_text(source)
  label='negative2-'+name
  run(label,['rustc','--edition=2021','--emit=metadata','--error-format=json','--extern','mixer_vm='+str(metadata),file,'-o',TARGET/(name+'.rmeta')],1)
  diagnostics=[json.loads(line) for line in (HERE/'commands'/(label+'.stderr')).read_text().splitlines() if line.startswith('{')]
  matches=[d for d in diagnostics if d.get('code',{} ) and d['code'].get('code')==code and any(s['is_primary'] and Path(s['file_name'])==file for s in d['spans'])]
  assert matches,(name,code)
  results.append({'case':name,'command':label,'expectedCode':code,'expectedSource':str(file),'matchedDiagnostics':matches,'fixtureSHA256':sha(file)})
 negative_copy=HERE/'compiler-negative-candidate'
 shutil.copytree(CANDIDATE,negative_copy)
 for name,feature in [('whole-owner','whole_owner'),('retained-owner','retained_owner')]:
  label='negative2-'+name
  fixture=fixtures/(feature+'.rs')
  injected=negative_copy/'src/experimental_swift_reactor/lifecycle_tests.rs'
  injected.write_bytes((CANDIDATE/'src/experimental_swift_reactor/lifecycle_tests.rs').read_bytes()+b'\n'+fixture.read_bytes())
  negative_base=[str(negative_copy/'src/lib.rs') if x=='src/lib.rs' else x for x in base]
  run(label,['env','CARGO_MANIFEST_DIR='+str(negative_copy),*negative_base,'--test','--emit=metadata','--error-format=json','-o',TARGET/(name+'.rmeta')],1)
  (fixtures/(feature+'-injected-lifecycle_tests.rs')).write_bytes(injected.read_bytes())
  diagnostics=[json.loads(line) for line in (HERE/'commands'/(label+'.stderr')).read_text().splitlines() if line.startswith('{')]
  matches=[d for d in diagnostics if d.get('code',{}) and d['code'].get('code')=='E0506' and any(s['is_primary'] and Path(s['file_name'])==injected and s['text'][0]['text'].strip()=='owner.lifecycle = Lifecycle::Ready;' for s in d['spans'])]
  assert matches,(name,'E0506 actual source assignment')
  results.append({'case':name,'command':label,'expectedCode':'E0506','matchedDiagnostics':matches})
 save(HERE/'negative-results.json',results)
 print('NEGATIVE_OK',len(results),flush=True)

if __name__=='__main__': {'matrix':matrix,'negative':negative}[sys.argv[1]]()
