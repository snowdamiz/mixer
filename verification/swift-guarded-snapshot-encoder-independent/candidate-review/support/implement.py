#!/usr/bin/env python3
"""Construct a new isolated144-member source variant; never mutate inputs."""
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent
OUT=HERE.parent
BASE=OUT.parent/'swift-guarded-snapshot-export-preparation/inputs/accepted-source/vm'
SOURCE=OUT/'source/vm'
def replace(path,before,after):
 p=SOURCE/path;s=p.read_text();assert s.count(before)==1,(path,before);p.write_text(s.replace(before,after))
def append(path,text):
 p=SOURCE/path;p.write_text(p.read_text()+text)
def main():
 assert not SOURCE.exists(),'variant already exists; preserve prior attempt'
 shutil.copytree(BASE,SOURCE)
 replace('src/experimental_swift_reactor/cache/initial_profile_v1.rs',"struct InitialProfileBorrowV1<'a> {","pub(crate) struct InitialProfileBorrowV1<'a> {")
 append('src/experimental_swift_reactor/cache.rs','\npub(crate) use initial_profile_v1::InitialProfileBorrowV1;\n')
 append('src/experimental_swift_reactor/mod.rs','\npub(crate) use cache::InitialProfileBorrowV1;\npub(crate) use retained_profile_loader_v1::LoaderProvenanceV1;\n')
 append('src/experimental/account.rs','''
impl<T:Copy> Buffer<T> {
 pub(super) fn snapshot_inventory_v2(&self)->(usize,usize,usize,usize,Resource){
  (self.values.len(),self.values.capacity(),std::mem::size_of::<T>(),self.charged,self.category)
 }
}
''')
 replace('src/experimental_swift_reactor/retained_profile_loader_v1.rs','pub(super) struct LoaderProvenanceV1 {','pub(crate) struct LoaderProvenanceV1 {')
 append('src/experimental_swift_reactor/retained_profile_loader_v1.rs','''
impl LoaderProvenanceV1 {
 pub(crate) fn snapshot_encode_v2(&self,out:&mut[u8;576])->Result<(),()> {
  out.fill(0);out[..8].copy_from_slice(b"MIXLPR01");
  let limits=&self.validation_budget;
  let values=[1,576,self.source_extent,u64::try_from(limits.source_bytes).map_err(|_|())?,
   u64::try_from(limits.metadata_bytes).map_err(|_|())?,u64::try_from(limits.scratch_bytes).map_err(|_|())?,
   limits.work_credits,limits.deadline_ms];
  for (i,n) in values.iter().enumerate(){out[8+i*8..16+i*8].copy_from_slice(&n.to_le_bytes());}
  for (i,value) in [&self.source,&self.manifest,&self.build,&self.session,&self.executable,&self.nonce].iter().enumerate(){
   out[72+i*32..104+i*32].copy_from_slice(*value);
  }
  for (i,identity) in self.identities.iter().enumerate(){out[264+i*64..328+i*64].copy_from_slice(&identity.encode());}
  Ok(())
 }
}
''')
 append('src/experimental_wasi/mod.rs','''
impl WasiContext {pub(crate) fn snapshot_configuration_v2(&self)->(WasiBudget,WasiGrants){(self.budget,self.grants)}}
''')
 append('src/experimental_wasi/accounted.rs','''
impl AccountedWasi {pub(crate) fn snapshot_configuration_v2(&self)->(WasiBudget,WasiGrants){self.context.snapshot_configuration_v2()}}
''')
 append('src/experimental_swift_reactor/cache/initial_profile_v1.rs','''
impl InitialProfileBorrowV1<'_> {
 pub(crate) fn snapshot_proof_v2(&self)->&ValidatedSwiftReactor{self.cache.proof()}
 pub(crate) fn snapshot_selected_v2(&self)->Option<&super::super::retained_profile_loader_v1::LoaderProvenanceV1>{self.cache.adopted.selected_provenance()}
 pub(crate) fn snapshot_runtime_v2(&self,out:&mut[u8;512])->Result<(),()> {
  out.fill(0);out[..8].copy_from_slice(b"MIXRTB01");let b=self.control.budget();
  let s=&self.scalars;let wasi=self.wasi.map(AccountedWasi::snapshot_configuration_v2);
  let convert=|n:usize|u64::try_from(n).map_err(|_|());
  let limits=[convert(b.source_bytes)?,convert(b.metadata_bytes)?,convert(b.cache_bytes)?,convert(b.cache_entry_bytes)?,
   convert(b.cache_entries)?,convert(b.active_pins)?,b.cache_work,convert(b.frames)?,convert(b.values)?,convert(b.controls)?,
   u64::from(b.memory_pages),convert(b.state_bytes)?,convert(b.combined_bytes)?,b.instruction_fuel,b.execution_work,b.host_calls,b.deadline_ms];
  for(i,n)in [1,512,u64::from(wasi.is_some()),self.cache.owner].iter().enumerate(){out[8+i*8..16+i*8].copy_from_slice(&n.to_le_bytes());}
  for(i,n)in limits.iter().enumerate(){out[40+i*8..48+i*8].copy_from_slice(&n.to_le_bytes());}
  if let Some((w,g))=wasi{
   for(i,n)in [w.calls,w.transfer_bytes,w.work,u64::from(w.one_transfer_bytes),u64::from(w.iovecs),u64::from(w.log_bytes),w.deadline_ms,
    u64::from(g.secure_random),u64::from(g.realtime),u64::from(g.monotonic),u64::from(g.stdout),u64::from(g.stderr)].iter().enumerate(){out[176+i*8..184+i*8].copy_from_slice(&n.to_le_bytes());}
  }
  for(i,n)in [s.source_extent,s.type_count,s.slot_limit,s.pin_limit,s.initial_nonce,s.cache_base,s.cache_capacity,s.entry_limit].iter().enumerate(){out[272+i*8..280+i*8].copy_from_slice(&n.to_le_bytes());}
  Ok(())
 }
}
#[cfg(any(test,mixer_snapshot_encoder_host))]use tests::snapshot_encoder_host;
''')
 replace('src/experimental_swift_reactor/cache/initial_profile_v1.rs','#[cfg(any(test,mixer_initial_profile_component_host))] mod tests;','#[cfg(any(test,mixer_initial_profile_component_host,mixer_snapshot_encoder_host))] mod tests;')
 replace('src/experimental_swift_reactor/cache/initial_profile_v1.rs','let initial=InitialProfileBorrowV1 { cache,control,wasi,scalars };','let initial=InitialProfileBorrowV1 { cache,control,wasi,scalars };\n    #[cfg(any(test,mixer_snapshot_encoder_host))]\n    snapshot_encoder_host::observe_v2(&initial);')
 append('src/experimental/swift.rs','\n#[allow(dead_code)]\npub(crate) mod snapshot_encoder_v2 {\n'+(HERE/'encoder.rs').read_text()+'\n}\n')
 append('src/experimental_swift_reactor/cache/initial_profile_v1/tests.rs','\n#[cfg(any(test,mixer_snapshot_encoder_host))]\npub(super) mod snapshot_encoder_host {\n'+(HERE/'host.rs').read_text()+'\n}\n')
 append('src/lib.rs','''
#[cfg(all(mixer_snapshot_encoder_host,not(test)))]
fn main(){unsafe{extern "C"{fn mixer_snapshot_encoder_host_v2();}mixer_snapshot_encoder_host_v2();}}
''')
if __name__=='__main__':main()
