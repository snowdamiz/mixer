from pathlib import Path
import shutil,json,tarfile
from run import SCRATCH,HERE,b
import inventory
vm=SCRATCH/'import-failure-reconstruction';shutil.copytree(SCRATCH/'candidate/vm',vm)
p=vm/'src/experimental_swift_reactor/frame_operations_tests.rs';p.write_text(p.read_text().replace('Some(ACTIVE_BYTES + 119576 + control_operations::ACTIVE_BYTES + memory_operations::ACTIVE_BYTES)','Some(ACTIVE_BYTES + 119576 + control_operations::ACTIVE_BYTES)'))
p=vm/'src/experimental_swift_reactor/memory_operations_tests.rs';s=p.read_text();s=s.replace('#[test] fn mm14_frozen_parity()', '#[cfg(feature="experimental-span-execution")]\n#[path="../../tests/common/mod.rs"]\nmod frozen_fixture;\n#[test] fn mm14_frozen_parity()',1);a=s.index(' FIXTURES.with(|n|n.set(n.get()+1));\n // Original bounded Wasm');z=s.index('let limits=crate::Limits',a)
s=s[:a]+''' let mut spec=frozen_fixture::Spec::one(vec![],Some(Type::I32),vec![0x41,0,0x41,0x78,0x36,2,0,0x41,0,0x28,2,0,0x0b]);spec.memory=Some((1,1));
 let bytes=spec.bytes();'''+s[z:];p.write_text(s)
old_selected=inventory.selected
inventory.selected=lambda name:name!='experimental::execution::width'and old_selected(name)
rows=[];defs=[];closures={}
for config in ['production','unit']:
 r,d,c=inventory.canonical(HERE/('draft-'+config+'.mir.gz'),config);rows+=r;defs+=d;closures[config]=c
for env,source in [('active',inventory.AUTHORED),('permanent',inventory.PERMANENT)]:
 for window,bindings in source.items():
  for binding,ty in bindings:
   for pos in ['source','argument','returned','caller']:rows.append(dict(envelope=env,window=window,field=f'source_{window}_{binding}_{pos}',rustType=ty,binding=binding,sourceNames=[binding],position=pos,config='source',kind='authored'))
inventory.rows=lambda:(rows,defs,closures);inventory.HERE=SCRATCH/'import-failure-reconstruction-metadata';inventory.HERE.mkdir();inventory.render(vm)
expected=json.loads((HERE/'commands/changed-unit-mir/source-manifest.json').read_text());actual=b.manifest(vm);mismatch=[n for n in set(actual)|set(expected)if actual.get(n)!=expected.get(n)];print(mismatch)
if not mismatch:
 dest=HERE/'historical-failed-sources';dest.mkdir(exist_ok=True)
 with tarfile.open(dest/'changed-unit-mir-source.tar.gz','w:gz')as t:
  for n in actual:t.add(vm/n,arcname='vm/'+n,recursive=False)
results=json.loads((HERE/'historical-failed-source-reconstruction.json').read_text());results.append(dict(command='changed-unit-mir',exactSourceReconstructed=not mismatch,sourceClosure=b.digest(actual),expectedSourceClosure=b.digest(expected),mismatches=mismatch));(HERE/'historical-failed-source-reconstruction.json').write_bytes(b.enc(results))
