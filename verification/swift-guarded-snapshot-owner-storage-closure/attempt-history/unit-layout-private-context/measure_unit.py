"""Measure all nameable charged types in the exact cfg(test) host layout context."""
import json,re,shutil
from probe import ROOT,INPUT,save,run
from layouts import normalize,instantiate
data=json.loads((ROOT/'raw-inventory.json').read_text())
types=list(json.loads((ROOT/'resolved-layouts.json').read_text()))
types += [instantiate(r['compiler_type'],'selected') for r in data['host_caller']['roles'] if r['funding_class']=='host-caller']
types=list(dict.fromkeys(t for t in types if '{closure@' not in t and not re.search(r'\{.*\}$',t)))
groups={'initial':[],'control':[]}
for t in types:
 group='control' if any('control::'+x in t for x in ['OriginalAdoptionV1','SnapshotAdoptionV1']) else 'initial'
 groups[group].append(t)
vm=ROOT/'owned-work/unit-layout-source/vm';assert not vm.exists();shutil.copytree(INPUT/'source/vm',vm)
def rust(t):return re.sub(r'(?<![\w:])(experimental|experimental_swift_reactor|experimental_wasi|execute)::',r'crate::\1::',t).replace("'_","'static")
for group,ts in groups.items():
 if not ts:continue
 code='\n// Owned exact unit-context type measurement; no engine call.\n#[no_mangle]\npub static MIXER_OWNER_UNIT_'+group.upper()+':[usize;'+str(len(ts)*2)+']=[\n'
 for t in ts:code+='std::mem::size_of::<'+rust(t)+'>(),std::mem::align_of::<'+rust(t)+'>(),\n'
 code+='];\n';(ROOT/('unit-'+group+'-layout-seam.rs')).write_text(code)
 p=vm/('src/experimental_swift_reactor/cache/initial_profile_v1.rs' if group=='initial' else 'src/experimental_swift_reactor/control.rs');p.write_text(p.read_text()+code)
p=vm/'src/lib.rs';p.write_text('#![feature(never_type)]\n'+p.read_text())
save(ROOT/'unit-layout-requests.json',groups)
code=run('exact-unit-layouts',['--emit=llvm-ir','-Zmir-opt-level=0','-o',str(ROOT/'owned-work/unit-layouts.ll')],vm=vm,unit=True)
if code:raise SystemExit(code)
ir=(ROOT/'owned-work/unit-layouts.ll').read_text();out=[]
for group,ts in groups.items():
 if not ts:continue
 symbol='MIXER_OWNER_UNIT_'+group.upper();lines=[s for s in ir.splitlines() if s.startswith('@'+symbol+' =')];assert len(lines)==1,(group,len(lines))
 (ROOT/(symbol+'.llvm')).write_text(lines[0]+'\n')
 raw=re.search(r'c"(.*?)"',lines[0])[1];decoded=bytearray();i=0
 while i<len(raw):
  if raw[i]=='\\':decoded.append(int(raw[i+1:i+3],16));i+=3
  else:decoded.append(ord(raw[i]));i+=1
 values=[int.from_bytes(decoded[i:i+8],'little') for i in range(0,len(decoded),8)];assert len(values)==2*len(ts)
 out += [{'compiler_type':t,'bytes':values[i*2],'alignment':values[i*2+1],'evidence':symbol+'.llvm'} for i,t in enumerate(ts)]
save(ROOT/'unit-type-layouts.json',out);shutil.rmtree(vm.parent);print('unit exact layouts',len(out))
