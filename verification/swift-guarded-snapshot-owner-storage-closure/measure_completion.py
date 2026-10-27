"""Measure the four actual new generic-completion tuple types in both contexts."""
import json,re,shutil
from probe import ROOT,INPUT,save,run
types=list(json.loads((ROOT/'unresolved-layouts.json').read_text()))
assert len(types)==4
def rust(t):return re.sub(r'(?<![\w:])(experimental|experimental_swift_reactor|experimental_wasi|execute)::',r'crate::\1::',t)
save(ROOT/'completion-layout-requests.json',types)
for unit in (False,True):
 label='completion-helper-tuples-'+('unit' if unit else 'production')
 symbol='MIXER_OWNER_COMPLETION_'+('UNIT' if unit else 'PRODUCTION')
 vm=ROOT/('owned-work/'+label+'/vm');assert not vm.exists();shutil.copytree(INPUT/'source/vm',vm)
 seam='\n// Owned source-occurrence tuple layout only; never invoked.\n#[no_mangle]\npub static '+symbol+':[usize;8]=[\n'
 for t in types:seam+='std::mem::size_of::<'+rust(t)+'>(),std::mem::align_of::<'+rust(t)+'>(),\n'
 seam+='];\n';(ROOT/(label+'-seam.rs')).write_text(seam)
 p=vm/'src/experimental_swift_reactor/cache/initial_profile_v1.rs';p.write_text(p.read_text()+seam)
 out=ROOT/('owned-work/'+label+'.ll')
 code=run(label,['--emit=llvm-ir','-Zmir-opt-level=0','-o',str(out)],vm=vm,unit=unit)
 if code:raise SystemExit(code)
 line=next(s for s in out.read_text().splitlines() if s.startswith('@'+symbol+' ='))
 (ROOT/(symbol+'.llvm')).write_text(line+'\n')
 raw=re.search(r'c"(.*?)"',line)[1];decoded=bytearray();i=0
 while i<len(raw):
  if raw[i]=='\\':decoded.append(int(raw[i+1:i+3],16));i+=3
  else:decoded.append(ord(raw[i]));i+=1
 values=[int.from_bytes(decoded[i:i+8],'little') for i in range(0,len(decoded),8)];assert len(values)==8
 rows=[{'compiler_type':t,'bytes':values[i*2],'alignment':values[i*2+1],'evidence':symbol+'.llvm'} for i,t in enumerate(types)]
 target=ROOT/('unit-type-layouts.json' if unit else 'extra-type-layouts.json')
 old=json.loads(target.read_text());assert not set(types)&{r['compiler_type'] for r in old}
 save(target,old+rows);shutil.rmtree(vm.parent)
 print(label,[(r['bytes'],r['alignment']) for r in rows])
