"""Exact remaining tuples/base types in their private declaring context."""
from pathlib import Path
import json,re,shutil
from probe import ROOT,INPUT,run,save,sha
types=list(json.loads((ROOT/'unresolved-layouts.json').read_text()))
types+=['()','!','bool','u8','u16','u32','u64','u128','i8','i16','i32','i64','i128','usize','isize','&u8','&mut u8','&[u8]','&mut [u8]','&str','*const u8','*mut u8','*const [u8]','fn()->()']
types=list(dict.fromkeys(types))
vm=ROOT/'owned-work/extra-layout-source/vm';assert not vm.exists();shutil.copytree(INPUT/'source/vm',vm)
def rust(t):return re.sub(r'(?<![\w:])(experimental|experimental_swift_reactor|experimental_wasi|execute)::',r'crate::\1::',t).replace("'_","'static")
code='\n// Owned exact MIR tuple/base type measurement only. Never invoked.\n#[no_mangle]\npub static MIXER_OWNER_EXTRA_LAYOUTS_V1:[usize;'+str(len(types)*2)+']=[\n'
for t in types:code+='std::mem::size_of::<'+rust(t)+'>(),std::mem::align_of::<'+rust(t)+'>(),\n'
code+='];\n'
(ROOT/'extra-layout-seam.rs').write_text(code)
p=vm/'src/experimental_swift_reactor/cache/initial_profile_v1.rs';p.write_text(p.read_text()+code)
p=vm/'src/lib.rs';p.write_text('#![feature(never_type)]\n'+p.read_text())
save(ROOT/'extra-layout-requests.json',[{'key':i,'compiler_type':t,'rust_type':rust(t)} for i,t in enumerate(types)])
code=run('exact-extra-layouts',['--emit=llvm-ir','-Zmir-opt-level=0','-o',str(ROOT/'owned-work/extra-layouts.ll')],vm=vm)
if code:raise SystemExit(code)
data=(ROOT/'owned-work/extra-layouts.ll').read_text();lines=[s for s in data.splitlines() if s.startswith('@MIXER_OWNER_EXTRA_LAYOUTS_V1 =')];assert len(lines)==1
(ROOT/'MIXER_OWNER_EXTRA_LAYOUTS_V1.llvm').write_text(lines[0]+'\n')
raw=re.search(r'c"(.*?)"',lines[0])[1];decoded=bytearray();i=0
while i<len(raw):
 if raw[i]=='\\':decoded.append(int(raw[i+1:i+3],16));i+=3
 else:decoded.append(ord(raw[i]));i+=1
values=[int.from_bytes(decoded[i:i+8],'little') for i in range(0,len(decoded),8)];assert len(values)==len(types)*2
save(ROOT/'extra-type-layouts.json',[{'compiler_type':t,'bytes':values[i*2],'alignment':values[i*2+1],'evidence':'MIXER_OWNER_EXTRA_LAYOUTS_V1.llvm'} for i,t in enumerate(types)])
shutil.rmtree(vm.parent)
print('measured',len(types),'exact extra/base identities')
