#[path="writer.rs"] mod candidate;
use candidate::*;
use std::io::{self,Write};
#[derive(Default)]struct Sink{bytes:Vec<u8>,calls:u64,mode:u8}
impl Write for Sink {
    fn write(&mut self,b:&[u8])->io::Result<usize>{self.calls+=1;match self.mode{1=>Ok(b.len()+1),2=>Err(io::ErrorKind::Interrupted.into()),3=>{self.bytes.extend_from_slice(&b[..b.len().min(1)]);Ok(b.len().min(1))},_=>{self.bytes.extend_from_slice(b);Ok(b.len())}}}
    fn flush(&mut self)->io::Result<()>{Ok(())}
}
fn writer(cap:u64)->Writer<Sink>{let h=header(cap,33,[[2;32];4]).unwrap();Writer::new(Sink::default(),cap,33,24,&h).unwrap()}
#[test]fn independent_write_adversity(){
    let mut over=Sink{mode:1,..Sink::default()};let mut a=0;assert!(!bounded_write(&mut over,&[1;2],&mut a));assert_eq!(a,1);
    let mut short=Sink{mode:3,..Sink::default()};let mut a=0;assert!(!bounded_write(&mut short,&[1;33],&mut a));assert_eq!(a,32);assert_eq!(short.bytes.len(),32);
    let mut s=Sink::default();let mut a=u64::MAX;assert!(!bounded_write(&mut s,&[1],&mut a));assert_eq!(s.calls,0);
}
#[test]fn independent_code_bounds_and_release_sentinels(){
    let mut f=Record::new(14,0,0,ABSENT);f.0[0]=1;f.0[13..16].copy_from_slice(&[21,24,6]);assert!(f.valid(24));
    for (i,bad) in [(13,0),(13,22),(14,0),(14,25),(15,0),(15,7),(10,0),(11,0),(12,1)] {let mut r=f;r.0[i]=bad;assert!(!r.valid(24),"field {i}");}
    let mut r=Record::new(12,4,0,34);r.0[0]=1;r.0[7]=100;r.0[9]=3;r.0[10]=0;r.0[11]=0;r.0[12]=1;r.0[13]=64;assert!(r.valid(24));r.0[8]=2;assert!(!r.valid(24));
}
#[test]fn independent_header_bounds_and_unknown_flags(){
    for mask in [0,1,32,64,65,u64::MAX] {assert!(header(1,mask,[[0;32];4]).is_none());}
    let h=header(MAX_RECORDS,63,[[0;32];4]).unwrap();assert!(valid_header(&h));
    let mut w=writer(1);w.push(Record::new(1,0,1,34));let mut p=Record::new(13,5,0,ABSENT);p.0[13]=5;w.push(p);
    let mut original=[0;64];original[14]=ABSENT;let f=w.finish(original);let h=header(1,33,[[2;32];4]).unwrap();
    assert!(valid_footer_fields(&h,&encode_frame(&f),1152));let mut bad=f;bad[9]|=512;assert!(!valid_footer_fields(&h,&encode_frame(&bad),1152));
}
#[test]fn independent_cap_exact_prefix_and_footer_failure_outer_result(){
    let mut w=writer(1);w.push(Record::new(1,0,1,34));w.push(Record::new(1,0,2,34));let mut p=Record::new(13,5,0,ABSENT);p.0[13]=5;w.push(p);
    let mut f=[0;64];f[14]=ABSENT;let f=w.finish(f);assert_eq!(f[2..5],[1,3,2]);assert_eq!(w.sink.bytes.len(),1152);assert_eq!(f[34],2);assert_eq!(w.attempts,3);
    let h=header(1,33,[[2;32];4]).unwrap();for (field,bad) in [(2,0),(3,1),(4,0),(15,1),(33,4)]{let mut x=f;x[field]=bad;assert!(!valid_footer_fields(&h,&encode_frame(&x),1152));}
    let mut w=writer(1);w.sink.mode=2;let f=w.finish([0;64]);assert_eq!(f[9],0);assert_eq!(w.flags,IO);assert_eq!(w.attempts,33);assert_eq!(w.sink.bytes.len(),512);
    println!("INDEPENDENT footer returned frame precedes footer IO; actual writer IO and attempt count must bind outer receipt");
}
#[test]fn independent_state_freeze_after_work_regression(){
    let mut w=writer(16);let mut a=Record::new(1,0,1,34);a.0[4]=10;w.push(a);let mut b=Record::new(1,0,2,34);b.0[4]=9;w.push(b);assert_eq!(w.flags,LIFECYCLE);let mut c=Record::new(1,0,3,34);c.0[4]=20;w.push(c);assert_eq!((w.stored,w.attempted,w.dropped),(1,3,2));
}
