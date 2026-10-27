"""Build layout constants for actual MIR-requested storage types; no engine call."""
from pathlib import Path
import json,re,shutil,hashlib
from probe import ROOT,INPUT,run,verify
TYPES=json.loads((ROOT/'type-requests.json').read_text())
GENERIC=['crate::experimental::metadata::Signature','crate::Type','crate::experimental::metadata::Import','crate::experimental::metadata::Function','crate::experimental::metadata::Global','crate::experimental::metadata::Export','crate::experimental::metadata::Segment']
def normalize(t):
 t=t.replace("'_","'static")
 for old,new in [('descriptor::WasiFunction','crate::experimental_wasi::WasiFunction'),('initial_profile_v1::','crate::experimental_swift_reactor::cache::initial_profile_v1::'),('control::','crate::experimental_swift_reactor::control::'),('accounted::','crate::experimental_wasi::accounted::')]:
  t=re.sub(r'(?<![\w:])'+re.escape(old),new,t)
 t=re.sub(r'(?<![\w:])(experimental|experimental_swift_reactor|experimental_wasi)::',r'crate::\1::',t)
 t=t.replace('crate::experimental_wasi::descriptor::WasiFunction','crate::experimental_wasi::WasiFunction')
 aliases={
 'SnapshotEncodeErrorV2':'crate::experimental::swift::snapshot_encoder_v2::SnapshotEncodeErrorV2',
 'SnapshotViewV2':'crate::experimental::swift::snapshot_encoder_v2::SnapshotViewV2',
 'SnapshotCursorV2':'crate::experimental::swift::snapshot_encoder_v2::SnapshotCursorV2',
 'SnapshotBlockV2':'crate::experimental::swift::snapshot_encoder_v2::SnapshotBlockV2',
 'SpanCheckV2':'crate::experimental::swift::snapshot_encoder_v2::SpanCheckV2',
 'Type':'crate::Type','TryFromIntError':'std::num::TryFromIntError',
 'FileIdentityV1':'crate::experimental_swift_reactor::retained_profile_loader_v1::FileIdentityV1',
 'AdoptionBodyV1':'crate::experimental_swift_reactor::retained_profile_loader_v1::AdoptionBodyV1',
 'LoaderProvenanceV1':'crate::experimental_swift_reactor::retained_profile_loader_v1::LoaderProvenanceV1',
 'WasiContext':'crate::experimental_wasi::WasiContext'}
 for a,b in aliases.items():t=re.sub(r'(?<![\w:])'+a+r'\b',b,t)
 return t
if __name__=='__main__':
 verify();vm=ROOT/'owned-work/layout-source/vm';
 if vm.exists():shutil.rmtree(vm)
 shutil.copytree(INPUT/'source/vm',vm)
 groups={'encoder':[],'loader':[],'initial':[]};requests=[]
 for i,t in enumerate(TYPES):
  if '{closure@' in t:continue
  if re.search(r'\bT\b',t):actual=[re.sub(r'\bT\b',x,normalize(t)) for x in GENERIC]
  else:actual=[normalize(t)]
  for j,a in enumerate(actual):
   group='initial' if 'initial_profile_v1::' in a else 'loader' if any(x in a for x in ['retained_profile_loader_v1::','experimental_swift_reactor::cache::']) else 'encoder'
   key=f't{i}-{j}';groups[group].append((key,a));requests.append({'key':key,'compiler_type':t,'actual_type':a,'group':group})
 for group,rows in groups.items():
  code='\n// Owned metadata-only exact type-layout request seam. No behavior calls.\n#[used]\nstatic MIXER_ENCODER_STORAGE_'+group.upper()+': [usize;'+str(len(rows)*2)+'] = [\n'
  code+=''.join(' std::mem::size_of::<'+t+'>(),std::mem::align_of::<'+t+'>(), // '+key+'\n' for key,t in rows)+'];\n'
  (ROOT/(group+'-layout-seam.rs')).write_text(code)
  path=vm/({'encoder':'src/experimental/swift.rs','loader':'src/experimental_swift_reactor/retained_profile_loader_v1.rs','initial':'src/experimental_swift_reactor/cache/initial_profile_v1.rs'}[group])
  s=path.read_text()
  if group=='encoder':
   marker='\n}\n\n\n// Fixed O(1) actual Buffer lengths';assert s.count(marker)==1;s=s.replace(marker,code+marker)
  else:s+=code
  path.write_text(s)
 lib=vm/'src/lib.rs';lib.write_text('#![feature(never_type)]\n'+lib.read_text())
 (ROOT/'layout-requests.json').write_text(json.dumps(requests,indent=2)+'\n')
 result=run('actual-type-layouts-exact-private-contexts',['--emit=llvm-ir','-o',str(ROOT/'owned-work/type-layouts.ll')],source_vm=vm)
 if result:raise SystemExit(result)
 text=(ROOT/'owned-work/type-layouts.ll').read_text();results=[]
 for group,rows in groups.items():
  symbol='MIXER_ENCODER_STORAGE_'+group.upper();lines=[l for l in text.splitlines() if l.startswith('@') and symbol in l and 'constant' in l and 'c"' in l];assert len(lines)==1,(symbol,len(lines))
  (ROOT/(symbol+'.llvm')).write_text(lines[0]+'\n');raw=re.search(r'c"(.*?)"',lines[0]).group(1);data=bytearray();i=0
  while i<len(raw):
   if raw[i]=='\\':data.append(int(raw[i+1:i+3],16));i+=3
   else:data.append(ord(raw[i]));i+=1
  values=[int.from_bytes(data[i:i+8],'little') for i in range(0,len(data),8)];assert len(values)==2*len(rows)
  for (key,t),(size,align) in zip(rows,zip(values[::2],values[1::2])):results.append({'key':key,'actual_type':t,'bytes':size,'alignment':align})
 (ROOT/'actual-type-layouts.json').write_text(json.dumps(results,indent=2)+'\n');print('measured',len(results),'actual type instantiations')
