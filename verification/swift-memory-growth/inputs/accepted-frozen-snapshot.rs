//! Original finite fixtures executing the original Frozen interpreter and owners.
use super::*;
use crate::experimental::{validate_spans,ValidationBudget,cache::CacheBudget};
use crate::experimental_swift_reactor::allocation_tests::measure_extended;
fn fixture(result:u8, code:&[u8])->Vec<u8>{
 let mut bytes=b"\0asm\x01\0\0\0".to_vec();
 for (id,payload) in [(1,vec![1,0x60,0,1,result]),(3,vec![1,0]),(5,vec![1,1,1,2]),(7,vec![1,3,b'r',b'u',b'n',0,0])]{bytes.extend([id,payload.len()as u8]);bytes.extend(payload);}
 let mut body=vec![0];body.extend(code);let mut payload=vec![1,body.len()as u8];payload.extend(body);bytes.extend([10,payload.len()as u8]);bytes.extend(payload);bytes
}
fn run_case(name:&str,result:u8,code:&[u8],allocates:bool){
 let bytes=fixture(result,code);let cancel=Cancellation::default();let limits=crate::Limits{profile:crate::Profile::TableMemoryV3,..crate::Limits::default()};
 let spans=validate_spans(&bytes,limits,ValidationBudget::default(),&cancel).unwrap();let cache=FunctionCache::new(spans,CacheBudget::default(),&cancel).unwrap();let mut owner=SpanInstance::new(cache,ExecutionBudget::default(),cancel).unwrap();
 owner.memory[3..11].copy_from_slice(&0xfedcba98f654b381u64.to_le_bytes());
 let pin=owner.cache.pin(0,&owner.cancellation).unwrap();owner.cache.release(pin).unwrap();
 for(i,byte)in owner.memory[..24576].iter_mut().enumerate(){*byte=(i.wrapping_mul(37)^i/251)as u8;}
 let (result,allocation)=measure_extended(if allocates{None}else{Some(0)},||owner.invoke("run",&[]));
 if !allocates{assert_eq!(allocation.attempts,0);}
 println!("FROZEN_SNAPSHOT {} result={:?} memory={:?} digest={} length={} usage={:?} cache={:?} allocation={:?}",name,result,&owner.memory[..12],owner.memory.iter().fold(0u64,|h,b|h.wrapping_mul(1099511628211).wrapping_add(*b as u64)),owner.memory.len(),owner.usage(),owner.cache_usage(),allocation);
}
#[test]
fn frozen_bulk_behavior_snapshot(){
 for (src,dst,len) in [(0,1,0),(0,1,1),(0,1,64),(0,1,65),(0,1,4096),(0,1,4097),(1,0,8193),(3,3,8193),(100,12000,8193)] {
  let mut code=Vec::new();for value in [dst,src,len]{code.push(0x41);code.extend(signed(value));}code.extend([0xfc,10,0,0,0x41,0,0x28,0,0,0x0b]);run_case(&format!("copy_{src}_{dst}_{len}"),0x7f,&code,false);
 }
 for value in [0,255,256,-1,0x1234] {for len in [0,1,4097]{let mut code=Vec::new();for n in [3,value,len]{code.push(0x41);code.extend(signed(n));}code.extend([0xfc,11,0,0x41,3,0x28,0,0,0x0b]);run_case(&format!("fill_{value}_{len}"),0x7f,&code,false);}}
 for (dst,src,len)in[(65536,65536,0),(65537,0,0),(65536,0,1),(0,-1,0),(0,0,-1)] {let mut code=Vec::new();for n in[dst,src,len]{code.push(0x41);code.extend(signed(n));}code.extend([0xfc,10,0,0,0x41,0,0x0b]);run_case(&format!("copy_bounds_{dst}_{src}_{len}"),0x7f,&code,false);}
 run_case("size",0x7f,&[0x3f,0,0x0b],false);
 run_case("fill_oob",0x7f,&[0x41,0x7f,0x41,1,0x41,1,0xfc,11,0,0x41,0,0x0b],false);
 run_case("grow_excluded_regression",0x7f,&[0x41,1,0x40,0,0x0b],true);
 println!("FROZEN_BOUNDS fixtures=32 maxGuestSteps=16 maxFrames=1 maxMemoryPages=2 serial=true");
}
fn signed(mut n:i32)->Vec<u8>{let mut bytes=Vec::new();loop{let byte=(n&127)as u8;n>>=7;let done=(n==0&&byte&64==0)||(n==-1&&byte&64!=0);bytes.push(if done{byte}else{byte|128});if done{return bytes;}}}
