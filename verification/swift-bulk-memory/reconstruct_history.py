from pathlib import Path
import json,hashlib,tarfile,io
from build_overlay import enc,digest
HERE=Path(__file__).resolve().parent;SCRATCH=Path(json.loads((HERE/'session.json').read_text())['scratch'])
pool={}
def add(value):
 data=value.encode()if isinstance(value,str)else value
 pool[hashlib.sha256(data).hexdigest()]=data
for label in SCRATCH.iterdir():
 if not label.is_dir()or label.name.startswith('target-'):continue
 vm=label/'vm'if(label/'vm/Cargo.toml').exists()else label
 if not(vm/'Cargo.toml').exists():continue
 for directory in ['src','tests','include']:
  for p in(vm/directory).rglob('*'):
   if p.is_file():add(p.read_bytes())
 for name in['Cargo.toml','Cargo.lock']:add((vm/name).read_bytes())
for archive in(HERE/'sources').glob('*.tar.gz'):
 with tarfile.open(archive,'r:gz')as tar:
  for m in tar.getmembers():
   if m.isfile():add(tar.extractfile(m).read())
add((HERE/'proposal.rs').read_text().split('// ACCOUNTING_START')[0]+'''// ACCOUNTING_START
struct PermanentPositions { placeholder: u8 }
struct ActivePositions { placeholder: u8 }
pub(in crate::experimental_swift_reactor::execution) const PERMANENT_BYTES:usize=size_of::<PermanentPositions>();
pub(super) const ACTIVE_BYTES:usize=size_of::<ActivePositions>();
''')
# Draft executable used the equivalent modulo expression before the Clippy repair.
for data in list(pool.values()):
 if b'swift_bulk_memory_page_agreement'in data:
  add(data.decode().replace('!self.phase.parts.memory.len().is_multiple_of(PAGE)','self.phase.parts.memory.len() % PAGE != 0'))
# Exact source versions before the first Frozen-feature expansion parse repair.
s=(SCRATCH/'candidate/vm/src/experimental/execution/borrowed.rs').read_text()
add(s.replace('($($rangevis:tt)*)','($rangevis:vis)').replace('$($rangevis)* fn $range(', '$rangevis fn $range('))
add(s.replace('($($rangevis:tt)*)','$rangevis:vis').replace('$($rangevis)* fn $range(', '$rangevis fn $range('))
s=(SCRATCH/'candidate/vm/src/experimental/execution/mod.rs').read_text();add(s.replace('(), range, load, store, ());','(), range, load, store,);'))
s=(SCRATCH/'candidate/vm/src/experimental_swift_reactor/memory_operations.rs').read_text();add(s.replace('memory_load, memory_store, (pub(super))','memory_load, memory_store, pub(super)'))
# Recover the immutable pre-refinement fixture from a frozen command archive.
initial=None
for archive in(HERE/'sources').glob('*.tar.gz'):
 with tarfile.open(archive,'r:gz')as tar:
  try:data=tar.extractfile('src/experimental_swift_reactor/bulk_memory_operations_tests.rs').read().decode()
  except KeyError:continue
  if 'for len in[0usize,1,63'not in data and 'let mut foreign=owner();install_foreign'in data:initial=data;break
assert initial is not None
s=initial.replace(', install_foreign, restore_foreign','').replace('FIXTURES.with(|n|n.set(n.get()+2));let mut foreign=owner();install_foreign(&mut foreign);let mut own=owner();','FIXTURES.with(|n|n.set(n.get()+1));let mut own=owner();').replace('restore_foreign(&mut foreign);retire(foreign);retire(own);}','retire(own);}')
add(s)
s=s.replace('if !p.cleanup.live_unreconciled{assert_eq!(observed(p).live.values.current,p.phase.parts.values.len());}slot.unwrap()', 'assert_eq!(observed(p).live.values.current,p.phase.parts.values.len());slot.unwrap()').replace('let original=(f.base,f.operands,f.controls);match fault','let original=(f.base,f.operands,f.controls);let pages=observed(p).live.memory_pages.current;match fault').replace('7=>{p.phase.parts.memory.truncate(583*PAGE);},','7=>p.phase.operation.control.remove_live(Live::MemoryPages,1).unwrap(),').replace('if fault==7{p.phase.parts.memory.resize(584*PAGE,0);}','if fault==7{p.phase.operation.control.add_live(Live::MemoryPages,pages-observed(p).live.memory_pages.current,cursor()).unwrap();}')
add(s);add(s.replace('pub(super) fn check_checkpoint(', 'fn check_checkpoint(').replace('retire, pin_ids};','retire, pin_ids, install_foreign, restore_foreign};'));add('use super::*;\n')
reconstructed=[]
for path in sorted((HERE/'commands').glob('*/source-manifest.json')):
 if not(path.parent/'receipt.json').exists():continue
 m=json.loads(path.read_text());archive=HERE/'sources'/(digest(m)+'.tar.gz')
 if archive.exists():continue
 missing=[(name,sha)for name,sha in m.items()if sha not in pool]
 if missing:print(path.parent.name,missing);continue
 with tarfile.open(archive,'w:gz')as tar:
  for name,sha in m.items():
   data=pool[sha];entry=tarfile.TarInfo(name);entry.size=len(data);entry.mtime=0;tar.addfile(entry,io.BytesIO(data))
 reconstructed.append(dict(command=path.parent.name,sourceTreeSHA256=digest(m),exactManifestReproduced=True))
(HERE/'historical-source-reconstruction.json').write_bytes(enc(reconstructed))
print('reconstructed',len(reconstructed),'byte-exact historical source archives')
