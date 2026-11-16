pub const BUCKETS: usize = 512;
pub const LINKS: usize = 256;
pub const CELLS: usize = BUCKETS + LINKS;
pub const BYTES: usize = CELLS * 2 + 32;
#[derive(Debug)] pub enum Error<E> { Meter(E), Corrupt(&'static str) }
#[derive(Clone,Copy,Debug,PartialEq,Eq)] pub struct Found { pub slot:usize, pub link:usize, pub next:u16 }
pub fn bucket(key:u32)->usize {(key.wrapping_mul(0x9e3779b9)>>23) as usize}
pub fn get(a:&[u8],i:usize)->u16 {u16::from_le_bytes([a[i*2],a[i*2+1]])}
pub fn put(a:&mut[u8],i:usize,v:u16) {a[i*2..i*2+2].copy_from_slice(&v.to_le_bytes());}
pub fn find<E>(a:&[u8],len:usize,key:u32,keys:impl Fn(usize)->Option<u32>,mut work:impl FnMut(u64)->Result<(),E>)->Result<Option<Found>,Error<E>> {
 if a.len()!=BYTES || len==0 || len>LINKS {return Err(Error::Corrupt("wide_layout"))}
 work(2).map_err(Error::Meter)?;
 let b=bucket(key); let mut link=b; let mut node=get(a,link); let mut seen=[0u64;4]; let mut hit=None;
 for _ in 0..LINKS {
  if node==0{return Ok(hit)}
  work(6).map_err(Error::Meter)?;
  let slot=usize::from(node-1);
  if slot>=len{return Err(Error::Corrupt("wide_slot"))}
  let bit=1u64<<(slot%64);
  if seen[slot/64]&bit!=0{return Err(Error::Corrupt("wide_cycle"))}
  seen[slot/64]|=bit;
  let actual=keys(slot).ok_or(Error::Corrupt("wide_empty"))?;
  if bucket(actual)!=b{return Err(Error::Corrupt("wide_bucket"))}
  let next=get(a,BUCKETS+slot);
  if actual==key {
   if hit.is_some(){return Err(Error::Corrupt("wide_duplicate"))}
   hit=Some(Found{slot,link,next});
  }
  link=BUCKETS+slot;node=next;
 }
 if node==0 {Ok(hit)} else {Err(Error::Corrupt("wide_cycle"))}
}
pub fn insert<E>(a:&mut[u8],len:usize,key:u32,slot:usize,keys:impl Fn(usize)->Option<u32>,mut work:impl FnMut(u64)->Result<(),E>)->Result<(),Error<E>>{
 if find(a,len,key,&keys,&mut work)?.is_some(){return Err(Error::Corrupt("wide_duplicate"))}
 work(4).map_err(Error::Meter)?;
 if slot>=len || keys(slot).is_some() || get(a,BUCKETS+slot)!=0 {return Err(Error::Corrupt("wide_insert"))}
 let b=bucket(key);let next=get(a,b);
 work(4).map_err(Error::Meter)?;
 put(a,BUCKETS+slot,next);put(a,b,(slot+1) as u16);Ok(())
}
pub fn remove<E>(a:&mut[u8],len:usize,key:u32,slot:usize,keys:impl Fn(usize)->Option<u32>,mut work:impl FnMut(u64)->Result<(),E>)->Result<(),Error<E>>{
 let hit=find(a,len,key,keys,&mut work)?.filter(|f|f.slot==slot).ok_or(Error::Corrupt("wide_victim"))?;
 work(4).map_err(Error::Meter)?;
 put(a,hit.link,hit.next);put(a,BUCKETS+slot,0);Ok(())
}
pub fn mask(a:&[u8],word:usize)->u64 {let i=CELLS*2+word*8;u64::from_le_bytes(a[i..i+8].try_into().unwrap())}
pub fn setmask(a:&mut[u8],word:usize,v:u64){let i=CELLS*2+word*8;a[i..i+8].copy_from_slice(&v.to_le_bytes())}
fn pin_mask(len:usize,word:usize)->u64 {
 let remaining=len.saturating_sub(word*64);
 if remaining>=64 {u64::MAX} else {(1u64<<remaining)-1}
}
pub fn init_pins(a:&mut[u8],len:usize)->Option<()> {
 if a.len()!=BYTES || len==0 || len>LINKS {return None}
 for w in 0..4 {setmask(a,w,pin_mask(len,w))} Some(())
}
pub fn free_pin<E>(a:&[u8],len:usize,active:usize,unused:impl Fn(usize)->bool,mut work:impl FnMut(u64)->Result<(),E>)->Result<usize,Error<E>>{
 if a.len()!=BYTES || len==0 || len>LINKS{return Err(Error::Corrupt("wide_pin_layout"))}
 work(16).map_err(Error::Meter)?;
 let mut free=0usize;let mut selected=None;
 for w in 0..4 {
  let m=mask(a,w);
  if m & !pin_mask(len,w)!=0 {return Err(Error::Corrupt("wide_pin_layout"))}
  free+=m.count_ones() as usize;
  if selected.is_none()&&m!=0 {selected=Some(w*64+m.trailing_zeros() as usize)}
 }
 if active>len || free!=len-active{return Err(Error::Corrupt("wide_pin_count"))}
 let slot=selected.ok_or(Error::Corrupt("pin_slots_exhausted"))?;
 if !unused(slot){return Err(Error::Corrupt("wide_pin_occupied"))}
 // Includes the later infallible publication of this word under exclusive borrow.
 work(8).map_err(Error::Meter)?;Ok(slot)
}
pub fn publish_pin(a:&mut[u8],slot:usize){setmask(a,slot/64,mask(a,slot/64)&!(1u64<<(slot%64)))}
pub fn release_pin(a:&mut[u8],slot:usize){setmask(a,slot/64,mask(a,slot/64)|(1u64<<(slot%64)))}
pub fn release_valid(a:&[u8],slot:usize)->bool {a.len()==BYTES&&slot<LINKS&&mask(a,slot/64)&(1u64<<(slot%64))==0}
// Conservative disjoint scalar, borrow, iterator, return, and closure environments.
// Three copies cover lookup/insert/remove nesting; no helper allocates.
pub struct Inventory {
 pub scalars:[usize;48], pub seen:[u64;4], pub found:[Option<Found>;4],
 pub borrows:[&'static [u8];8], pub outcomes:[Option<Found>;4],
}

#[cfg(test)]
mod r3554_pure {
    use super::*;
    #[test]
    fn exact_wide_lookup_work_and_rejection() {
        let mut a=[0u8;BYTES]; let mut charged=0u64;
        let miss=find(&a,256,7, |_|None, |n|{charged+=n;Ok::<_,()>(())}).unwrap();
        assert!(miss.is_none());assert_eq!(charged,2);
        put(&mut a,bucket(7),1);charged=0;
        let hit=find(&a,256,7,|i|if i==0{Some(7)}else{None},|n|{charged+=n;Ok::<_,()>(())}).unwrap();
        assert_eq!(hit.unwrap().slot,0);assert_eq!(charged,2+6);
        put(&mut a,BUCKETS,1);charged=0;
        assert!(matches!(find(&a,256,7,|_|Some(7),|n|{charged+=n;Ok::<_,()>(())}),Err(Error::Corrupt("wide_cycle"))));
        assert_eq!(charged,2+6+6);
        // A refused work charge stops before reading the head or calling keys.
        let key_reads=std::cell::Cell::new(0usize);
        assert!(matches!(find(&a,256,7,|_|{key_reads.set(key_reads.get()+1);Some(7)},|_|Err::<(),_>(9u8)),Err(Error::Meter(9))));
        assert_eq!(key_reads.get(),0);
    }
}

#[cfg(test)]
mod r3672_tests {
 use super::*;
 use crate::experimental::cache::storage::SwiftResourcePlan;
 #[test]
 fn r3672_admitted_lengths_exhaustion_hole_reuse_and_refusal() {
  assert_eq!(SwiftResourcePlan::checked(64,64,64,true).unwrap().ticket_limit(),86);
  assert_eq!(SwiftResourcePlan::ui_profile_1().ticket_limit(),278);
  for len in [65,128,255,257,usize::MAX] {
   assert!(SwiftResourcePlan::checked(len,len,len,true).is_none());
  }
  for len in [1usize,63,64,65,128,255,256] {
   let mut a=[0u8;BYTES]; assert_eq!(init_pins(&mut a,len),Some(()));
   let mut records=[0u64;LINKS];
   for active in 0..len {
    let before=a;let mut work=0;
    let slot=free_pin(&a,len,active,|i|records[i]==0,|n|{work+=n;Ok::<(),()>(())}).unwrap();
    assert_eq!(slot,active);assert_eq!(work,24);assert_eq!(a,before);
    records[slot]=(slot+1) as u64;publish_pin(&mut a,slot);
   }
   let full=a;let mut touched=0;
   assert!(matches!(free_pin(&a,len,len,|_|{panic!("exhaustion must not read a selected record")},|n|{touched+=n;Ok::<(),()>(())}),Err(Error::Corrupt("pin_slots_exhausted"))));
   assert_eq!(touched,16);assert_eq!(a,full);
   let hole=len/2;assert!(release_valid(&a,hole));let old=records[hole];
   records[hole]=0;release_pin(&mut a,hole);assert!(!release_valid(&a,hole));
   let available=a;
   let slot=free_pin(&a,len,len-1,|i|records[i]==0,|_|Ok::<(),()>(())).unwrap();
   assert_eq!(slot,hole);assert_eq!(a,available);records[slot]=old+1024;publish_pin(&mut a,slot);
   for (i,id) in records[..len].iter().enumerate(){assert_eq!(*id,if i==hole{old+1024}else{(i+1)as u64});}
   for slot in 0..len{assert!(release_valid(&a,slot));release_pin(&mut a,slot);}
   assert_eq!(free_pin(&a,len,0,|_|true,|_|Ok::<(),()>(())).unwrap(),0);
   println!("R3672_PURE len={len} exhausted=true stable_other_records=true reused={hole} work=24 unpinned_all=true");
  }
  for len in [0usize,257,usize::MAX] {
   let mut a=[0x5au8;BYTES];let before=a;
   assert_eq!(init_pins(&mut a,len),None);assert_eq!(a,before);
   assert!(matches!(free_pin::<()>(&a,len,0,|_|panic!("layout must precede record access"),|_|panic!("layout must precede work")),Err(Error::Corrupt("wide_pin_layout"))));
   assert_eq!(a,before);
  }
  for bytes in [0usize,BYTES-1,BYTES+1] {
   let mut a=vec![0x5a;bytes];let before=a.clone();
   assert_eq!(init_pins(&mut a,64),None);assert_eq!(a,before);
   assert!(matches!(free_pin(&a,64,0,|_|true,|_|Ok::<(),()>(())) ,Err(Error::Corrupt("wide_pin_layout"))));assert_eq!(a,before);
  }
 }
 #[test]
 fn r3672_malformed_bits_counts_and_meter_refuse_before_mutation() {
  for len in [1usize,63,64,65,128,255] {
   let mut a=[0u8;BYTES];init_pins(&mut a,len).unwrap();
   let corrupt=mask(&a,len/64)|(1u64<<(len%64));setmask(&mut a,len/64,corrupt);
   let bad=a;
   assert!(matches!(free_pin(&a,len,0,|_|panic!("out of range free bit"),|_|Ok::<(),()>(())),Err(Error::Corrupt("wide_pin_layout"))));assert_eq!(a,bad);
  }
  let mut a=[0u8;BYTES];init_pins(&mut a,64).unwrap();let before=a;
  for active in [1usize,65,usize::MAX] {
   assert!(matches!(free_pin(&a,64,active,|_|true,|_|Ok::<(),()>(())),Err(Error::Corrupt("wide_pin_count"))));assert_eq!(a,before);
  }
  assert!(matches!(free_pin(&a,64,0,|_|false,|_|Ok::<(),()>(())),Err(Error::Corrupt("wide_pin_occupied"))));assert_eq!(a,before);
  for fail_at in [0usize,1] {
   let mut calls=0;let reads=std::cell::Cell::new(0usize);
   assert!(matches!(free_pin(&a,64,0,|_|{reads.set(reads.get()+1);true},|_|{let n=calls;calls+=1;if n==fail_at{Err(7u8)}else{Ok(())}}),Err(Error::Meter(7))));
   assert_eq!(reads.get(),fail_at);assert_eq!(a,before);
  }
  println!("R3672_PURE malformed length/bits/count/occupied and both meter refusals preserve storage");
 }
}
