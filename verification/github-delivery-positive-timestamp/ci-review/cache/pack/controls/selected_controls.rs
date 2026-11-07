//! Independent finite checks of the exact selected implementation, private only.
use super::*;
#[derive(Clone,Copy,Debug)]
struct Row { function:u64, bytes:u64, pins:u64, time:u64, generation:u64 }
fn word(b:&mut[u8],offset:usize,value:u64){b[offset..offset+8].copy_from_slice(&value.to_le_bytes());}
fn row(bytes:u64,pins:u64,time:u64)->Option<Row>{Some(Row{function:77,bytes,pins,time,generation:u64::MAX})}
// This oracle consumes complete resident descriptions. It selects the shortest
// stable prefix that creates a destination and makes the requested bytes fit.
// u128 computes capacity arithmetic independently of production's u64 prefix.
fn expected(rows:&[Option<Row>],base:u64,capacity:u64,request:u64)->(u64,u64,bool,Vec<usize>){
 let mut used:u128=rows.iter().flatten().map(|r|r.bytes as u128).sum();
 let mut destination=rows.iter().position(Option::is_none);
 let mut eligible:Vec<_>=rows.iter().enumerate().filter_map(|(i,r)|r.filter(|r|r.pins==0).map(|r|(r.time,i))).collect();
 eligible.sort();let ordered:Vec<_>=eligible.iter().map(|(_,i)|*i).collect();
 let mut victims=0;
 for (_,index) in eligible {
  if destination.is_some() && used+base as u128+request as u128<=capacity as u128 {break;}
  used-=rows[index].unwrap().bytes as u128;victims|=1u64<<index;destination=Some(index);
 }
 let fits=destination.is_some()&&used+base as u128+request as u128<=capacity as u128;
 (victims,if fits {destination.unwrap()as u64}else{u64::MAX},fits,ordered)
}
fn fixture(rows:&[Option<Row>],pin_backrefs:&[usize],base:u64,capacity:u64,request:u64)->(Vec<u8>,Progress,Fixture,[u64;16]){
 let mut arena=vec![0;ARENA_BYTES];
 for (i,resident) in rows.iter().enumerate(){
  let at=RESIDENT.base+i*64;
  match resident{
   Some(r)=>{for (j,value) in [1,r.function,r.bytes,r.pins,r.time,r.generation,0,0].into_iter().enumerate(){word(&mut arena,at+j*8,value);}}
   None=>word(&mut arena,at+8,u64::MAX)
  }
 }
 for i in 0..64{
  let entry=pin_backrefs.get(i).map(|s|*s as u64).unwrap_or(u64::MAX);
  word(&mut arena,PIN.base+i*48,entry);
  if entry!=u64::MAX{word(&mut arena,PIN.base+i*48+8,i as u64+1);}
 }
 // Requested function1 has no resident. Nonrequested identities may duplicate.
 arena[FUNCTION.base+96+20..FUNCTION.base+96+24].copy_from_slice(&1u32.to_le_bytes());
 for (j,value)in[1,32,4,1,0].into_iter().enumerate(){word(&mut arena,PLAN.base+40+j*8,value);}
 let total:u128=rows.iter().flatten().map(|r|r.bytes as u128).sum();
 let mut q=[0;16];q[3]=5;q[4]=9;q[5]=1;q[6]=rows.iter().flatten().count()as u64;q[7]=total as u64;q[8]=rows.iter().flatten().map(|r|r.pins).sum();q[9]=65;
 let progress=Progress{calls:0,latch:0,q};
 let config=Fixture{cap:1,mask:33,extent:u64::MAX,types:2,slots:rows.len()as u64,pins:64,base,capacity,entry:u64::MAX};
 let record=[1,5,0,9,10,1,1,32,4,1,u64::MAX,u64::MAX,0,request,base,capacity];
 (arena,progress,config,record)
}
fn observe(rows:&[Option<Row>],backrefs:&[usize],base:u64,capacity:u64,request:u64){
 let oracle=expected(rows,base,capacity,request);
 let(mut arena,progress,config,record)=fixture(rows,backrefs,base,capacity,request);
 let before_resident=arena[RESIDENT.base..RESIDENT.base+4096].to_vec();let before_pin=arena[PIN.base..PIN.base+3072].to_vec();
 let mut candidate=[0;2048];let decoded=FixtureDecodedRecordV1{words:&record};let loan=Loan{record:&decoded,config:&config};
 let mut budget=StepBudget{remaining:7680,spent:0};
 let reply=semantic(&mut arena,&mut candidate,&loan,&progress,&mut budget);
 assert_eq!((reply.status,reply.reason,reply.debit),(1,0,7680));assert_eq!((budget.remaining,budget.spent),(0,7680));
 assert_eq!((cq(&candidate,10),cq(&candidate,14),cq(&candidate,15)),(oracle.0,oracle.1,u64::from(oracle.2)));
 for(position,slot)in oracle.3.iter().enumerate(){assert_eq!(candidate[512+position],*slot as u8);}
 for position in oracle.3.len()..64{assert_eq!(candidate[512+position],255);}
 assert_eq!(&arena[RESIDENT.base..RESIDENT.base+4096],before_resident);assert_eq!(&arena[PIN.base..PIN.base+3072],before_pin);
}
#[test]
fn g5_capacity_boundaries_empty_full_sparse_and_u64_totals(){
 let mut checks=0;
 for slots in [1usize,2,3,16,64]{
  for distribution in 0..4{
   let rows:Vec<_>=(0..slots).map(|i|match distribution{0=>None,1=>row((i%5+1)as u64,0,u64::MAX),2=>if i%3==0{None}else{row((i%7+1)as u64,0,(slots-i)as u64)},_=>row((i%3+1)as u64,0,(i%4)as u64)}).collect();
   let total:u64=rows.iter().flatten().map(|r|r.bytes).sum();
   for capacity in [1,total.max(1),total+1,total+5]{observe(&rows,&[],0,capacity,1);checks+=1;}
  }
 }
 observe(&[row(u64::MAX-1,0,u64::MAX),None],&[],0,u64::MAX,1);checks+=1;
 observe(&[row(u64::MAX-1,0,u64::MAX),row(1,0,0)],&[],0,u64::MAX,1);checks+=1;
 observe(&[row(1,0,1),None],&[],u64::MAX-1,u64::MAX,1);checks+=1;
 println!("PRIVATE_ACTUAL_G5_CAPACITY_CASES={checks} PUBLIC_REACHABILITY_CREDIT=0");
}
#[test]
fn g2_admitted_duplicate_nonrequested_identities_and_unbalanced_pin_backrefs(){
 // Two resident pin counts are1 each; both live tokens reference only slot0.
 // G2 admits this state. Eviction may use only the two unpinned rows2/3.
 let rows=[row(7,1,0),row(9,1,u64::MAX),row(11,0,u64::MAX),row(13,0,u64::MAX)];
 for capacity in [5,16,23,28,40,45]{observe(&rows,&[0,0],0,capacity,5);}
 println!("PRIVATE_ACTUAL_G2_ADMITTED_MALFORMED_CASES=6 PUBLIC_REACHABILITY_CREDIT=0");
}
#[test]
fn refused_pre_g5_states_keep_arena_and_never_reach_ordinary_subtraction(){
 let rows=[row(7,0,0),row(9,0,u64::MAX),None];let mut checks=0;
 for damage in 0..5{
  let(mut arena,mut progress,mut config,mut record)=fixture(&rows,&[],0,10,5);
  let reason=match damage{
   0=>{progress.q[7]+=1;13},
   1=>{word(&mut arena,RESIDENT.base+8,1);word(&mut arena,RESIDENT.base+64+8,1);7},
   2=>{progress.q[8]=1;13},
   3=>{config.base=u64::MAX;record[14]=u64::MAX;10},
   _=>{word(&mut arena,RESIDENT.base+16,u64::MAX);word(&mut arena,RESIDENT.base+64+16,1);10},
  };
  let before=arena.clone();let mut candidate=[0;2048];let decoded=FixtureDecodedRecordV1{words:&record};let loan=Loan{record:&decoded,config:&config};let mut budget=StepBudget{remaining:7680,spent:0};
  let reply=semantic(&mut arena,&mut candidate,&loan,&progress,&mut budget);
  assert_eq!((reply.status,reply.reason,reply.debit),(2,reason,7680));assert_eq!(arena,before);checks+=1;
 }
 println!("PRIVATE_ACTUAL_PRE_G5_REFUSALS={checks} PUBLIC_REACHABILITY_CREDIT=0");
}
