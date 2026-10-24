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
 let (result,allocation)=measure_extended(if allocates{None}else{Some(0)},||owner.invoke("run",&[]));
 if !allocates{assert_eq!(allocation.attempts,0);}
 println!("FROZEN_SNAPSHOT {} result={:?} memory={:?} length={} usage={:?} cache={:?} allocation={:?}",name,result,&owner.memory[..12],owner.memory.len(),owner.usage(),owner.cache_usage(),allocation);
}
#[test]
fn frozen_memory_behavior_snapshot(){
 for opcode in 0x28..=0x35{let result=match opcode{0x28|0x2c..=0x2f=>0x7f,0x2a=>0x7d,0x2b=>0x7c,_=>0x7e};run_case(&format!("load_{opcode:02x}"),result,&[0x41,3,opcode,0,0,0x0b],false);}
 for opcode in 0x36..=0x3e{let(result,load,constant)=match opcode{0x37|0x3c..=0x3e=>(0x7e,0x29,vec![0x42,0x7f]),0x38=>(0x7d,0x2a,vec![0x43,0x45,0x23,0xc1,0x7f]),0x39=>(0x7c,0x2b,vec![0x44,0xbc,0x9a,0x78,0x56,0x34,0x12,0xf0,0x7f]),_=>(0x7f,0x28,vec![0x41,0x7f])};let mut code=vec![0x41,3];code.extend(constant);code.extend([opcode,0,0,0x41,3,load,0,0,0x0b]);run_case(&format!("store_{opcode:02x}"),result,&code,false);}
 run_case("load_oob",0x7f,&[0x41,0x7f,0x28,0,0,0x0b],false);
 run_case("store_oob",0x7f,&[0x41,0x7f,0x41,1,0x36,0,0,0x41,0,0x0b],false);
 run_case("copy",0x7f,&[0x41,0,0x41,3,0x41,8,0xfc,10,0,0,0x41,0,0x28,0,0,0x0b],false);
 run_case("fill",0x7f,&[0x41,0,0x41,0x55,0x41,8,0xfc,11,0,0x41,0,0x28,0,0,0x0b],false);
 run_case("grow",0x7f,&[0x41,1,0x40,0,0x0b],true);
 println!("FROZEN_BOUNDS fixtures=28 maxGuestSteps=8 maxFrames=1 maxMemoryPages=2 serial=true");
}
