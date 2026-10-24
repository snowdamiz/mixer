//! Original finite Frozen growth differential. No external runtime dependency.
use super::*;
use crate::experimental::{validate_spans,ValidationBudget,cache::CacheBudget};
use crate::experimental_swift_reactor::allocation_tests::measure_extended;
fn binary(encoded:u8)->Vec<u8>{let mut bytes=b"\0asm\x01\0\0\0".to_vec();bytes.extend_from_slice(&[1,5,1,0x60,0,1,0x7f,3,2,1,0,5,4,1,1,1,3,7,7,1,3,b'r',b'u',b'n',0,0,10,8,1,6,0,0x41,encoded,0x40,0,0x0b]);bytes}
#[test]fn frozen_growth_differential(){
 for(case,encoded,fault)in[("zero",0,0),("one",1,0),("two",2,0),("max_denial",3,0),("unsigned_denial",0x7f,0),("allocation",1,1),("state",1,2),("work_before",1,3),("work_after_pop",1,4),("cancelled",1,5)]{
  let cancel=Cancellation::default();let limits=crate::Limits{profile:crate::Profile::TableMemoryV3,..crate::Limits::default()};
  let bytes=binary(encoded);let spans=validate_spans(&bytes,limits,ValidationBudget::default(),&cancel).unwrap();let cache=FunctionCache::new(spans,CacheBudget::default(),&cancel).unwrap();let mut owner=SpanInstance::new(cache,ExecutionBudget::default(),cancel).unwrap();
  for(at,byte)in owner.memory.iter_mut().enumerate(){*byte=(at.wrapping_mul(37)^at/251)as u8;}
  let pin=owner.cache.pin(0,&owner.cancellation).unwrap();owner.cache.release(pin).unwrap();
  if fault==2{owner.budget.state_bytes=owner.usage.state_reserved+2*PAGE-1;}
  if fault==3{owner.budget.work_credits=owner.usage.work_used;}
  if fault==4{owner.budget.work_credits=owner.usage.work_used+6;}
  if fault==5{owner.cancellation.cancel();}
  let(result,allocation)=measure_extended(if fault==1{Some(0)}else{None},||owner.invoke("run",&[]));
  if fault==0{assert_eq!(result,Ok(Some(Value::I32(if encoded==3||encoded==0x7f{-1}else{1}))));}
  if fault!=0{assert!(result.is_err());}
  println!("FROZEN_GROWTH case={} result={:?} length={} digest={} usage={:?} cache={:?} allocation={:?}",case,result,owner.memory.len(),owner.memory.iter().fold(0u64,|hash,byte|hash.wrapping_mul(1099511628211).wrapping_add(*byte as u64)),owner.usage(),owner.cache_usage(),allocation);
 }
 println!("FROZEN_GROWTH_BOUND fixtures=10 maxGuestInstructions=3 maxFrames=1 maxPages=3 serial=true");
}
