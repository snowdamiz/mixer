// Independently authored finite diagnostic writer; never product authority.
use std::io::{self, Write};
pub const ABSENT:u64=u64::MAX;
pub const MAX_RECORDS:u64=4_194_304;
pub const CAP:u32=1; pub const IO:u32=2; pub const CONTEXT:u32=4;
pub const BORROW:u32=8; pub const RANGE:u32=16; pub const OVERFLOW:u32=32;
pub const LIFECYCLE:u32=64; pub const CODE:u32=128; pub const GATE:u32=256;
pub const HEADER_MAGIC:u64=0x315244524f58494d;
pub const FOOTER_MAGIC:u64=0x31444e454f58494d;
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub struct Record(pub [u64;16]);
impl Record {
    pub fn new(kind:u64,phase:u64,operation:u64,function:u64)->Self {
        Self([0,kind,phase,operation,0,0,function,ABSENT,ABSENT,ABSENT,ABSENT,ABSENT,0,0,0,0])
    }
    pub fn encode(&self,out:&mut [u8;128]) {
        for (i,n) in self.0.iter().enumerate(){out[8*i..8*i+8].copy_from_slice(&n.to_le_bytes());}
    }
    pub fn decode(raw:&[u8;128])->Self {
        let mut words=[0;16];for (i,n) in words.iter_mut().enumerate(){*n=u64::from_le_bytes(raw[8*i..8*i+8].try_into().unwrap());}Self(words)
    }
    pub fn valid(&self,code_count:u64)->bool {
        let w=&self.0;
        if !(1..=14).contains(&w[1])||w[2]>5||w[0]==0{return false;}
        let full=w[6]<80000&&w[7]!=ABSENT&&w[8]!=ABSENT&&w[9]!=ABSENT&&w[7].checked_add(w[8]).is_some();
        let absent_body=w[7..10]==[ABSENT;3];
        let no_slots=w[10]==ABSENT&&w[11]==ABSENT&&w[12]==0;
        match w[1] {
            1=>w[3]>0&&w[6]<80000&&absent_body&&no_slots&&w[13..16]==[0;3],
            2=>w[3]>0&&full&&w[11]==ABSENT&&w[12]==0&&w[13]<=1&&w[14]==0&&w[15]==0&&if w[13]==0{w[10]==ABSENT}else{w[10]<64},
            3=>w[3]>0&&full&&no_slots&&w[13]==0&&w[14]==0&&w[15]==w[6]&511,
            4=>w[3]>0&&full&&no_slots&&w[13]<=2&&(if w[13]==1{w[14]<80000&&w[14]!=w[6]}else{w[14]==ABSENT})&&w[15]==w[6]&511,
            5=>w[3]>0&&full&&no_slots&&w[13]>0&&w[14].checked_add(w[13]).is_some_and(|n|n<=w[15]),
            6..=8=>w[3]>0&&full&&w[10]<64&&w[11]==ABSENT&&w[12]==0&&w[13]>0&&w[14..16]==[0;2],
            9|10=>w[3]>0&&full&&no_slots&&w[13]>0&&w[14..16]==[0;2],
            11=>w[3]>0&&full&&w[10]<64&&w[11]<64&&w[12]>0&&w[13]<=1&&w[14]>0&&(1..=64).contains(&w[15]),
            12=>w[3]==0&&w[6]<80000&&w[7]!=ABSENT&&w[8]==ABSENT&&w[9]!=ABSENT&&w[10]<64&&w[11]<64&&w[12]>0&&w[13]>0&&w[14]==0&&w[15]<64,
            13=>w[3]==0&&w[6]==ABSENT&&absent_body&&no_slots&&w[13]==w[2]&&w[14..16]==[0;2],
            14=>absent_body&&(w[6]==ABSENT||w[6]<80000)&&no_slots&&(1..=21).contains(&w[13])&&(1..=code_count).contains(&w[14])&&(1..=6).contains(&w[15]),
            _=>false,
        }
    }
}
pub fn encode_frame(words:&[u64;64])->[u8;512] {
    let mut bytes=[0;512];for (i,n) in words.iter().enumerate(){bytes[i*8..i*8+8].copy_from_slice(&n.to_le_bytes());}bytes
}
pub fn header(cap:u64,mask:u64,digests:[[u8;32];4])->Option<[u8;512]> {
    if cap==0||cap>MAX_RECORDS||mask==0||mask>=64||mask&33!=33{return None;}
    let mut w=[0;64]; w[..10].copy_from_slice(&[HEADER_MAGIC,1,512,128,512,cap,80000,64,512,mask]);
    let mut out=encode_frame(&w);for(i,d)in digests.iter().enumerate(){out[128+32*i..160+32*i].copy_from_slice(d);}Some(out)
}
pub fn valid_header(raw:&[u8;512])->bool {
    let word=|i:usize|u64::from_le_bytes(raw[i*8..i*8+8].try_into().unwrap());
    word(0)==HEADER_MAGIC&&word(1)==1&&word(2)==512&&word(3)==128&&word(4)==512&&
    (1..=MAX_RECORDS).contains(&word(5))&&word(6)==80000&&word(7)==64&&word(8)==512&&
    word(9)<64&&word(9)&33==33&&raw[80..128].iter().all(|b|*b==0)&&raw[256..].iter().all(|b|*b==0)
}
#[derive(Debug)]
#[repr(C)]
pub struct Writer<W:Write> {
    pub buffer:[u8;4096],pub record:[u8;128],pub stored:u64,pub attempted:u64,pub dropped:u64,
    pub used:usize,pub cap:u64,pub last_work:u64,pub last_instructions:u64,pub operation:u64,
    pub phase:u64,pub observed_mask:u64,pub expected_mask:u64,pub attempts:u64,pub code_count:u64,
    pub bindings:[u64;8],pub pin_failed:bool,pub terminal_failed:bool,pub ended:bool,pub flags:u32,pub sink:W,
}
// Every loop body executes at most 32 times, including Interrupted/short writes.
pub fn bounded_write<W:Write>(sink:&mut W,bytes:&[u8],attempts:&mut u64)->bool {
    let mut offset=0usize;
    for _ in 0..32 {
        let Some(n)=attempts.checked_add(1)else{return false;};*attempts=n;
        let result:io::Result<usize>=sink.write(&bytes[offset..]);
        match result {Ok(0)=>return false,Ok(n)=>{if n>bytes.len()-offset{return false;}offset+=n;if offset==bytes.len(){return true;}},Err(e)=>{if e.kind()!=io::ErrorKind::Interrupted{return false;}}}
    }false
}
impl<W:Write> Writer<W> {
    pub fn new(sink:W,cap:u64,mask:u64,code_count:u64,head:&[u8;512])->Option<Self> {
        if !valid_header(head)||u64::from_le_bytes(head[40..48].try_into().unwrap())!=cap||u64::from_le_bytes(head[72..80].try_into().unwrap())!=mask||code_count!=24{return None;}
        let mut out=Self {buffer:[0;4096],record:[0;128],stored:0,attempted:0,dropped:0,used:0,cap,last_work:0,last_instructions:0,operation:0,phase:0,observed_mask:1,expected_mask:mask,attempts:0,code_count,bindings:[0;8],pin_failed:false,terminal_failed:false,ended:false,flags:0,sink};
        for (i,n) in out.bindings.iter_mut().enumerate(){*n=u64::from_le_bytes(head[128+8*i..136+8*i].try_into().unwrap());}
        if !bounded_write(&mut out.sink,head,&mut out.attempts){out.flags|=IO;}Some(out)
    }
    pub fn freeze(&mut self,flags:u32){self.flags|=flags;}
    pub fn push(&mut self,mut event:Record) {
        if self.ended {return;}
        match self.attempted.checked_add(1){Some(n)=>self.attempted=n,None=>{self.flags|=OVERFLOW;return;}}
        // Actual lifecycle scalars continue after truncation; no missing Phase
        // record is invented and stored-stream coordinates stay unchanged.
        if event.0[1]==13 {
            if event.0[2]>5||event.0[13]!=event.0[2]||event.0[2]<=self.phase{self.flags|=LIFECYCLE;}
            else {self.phase=event.0[2];self.observed_mask|=1<<self.phase;}
        }
        if self.flags!=0||self.stored==self.cap {
            if self.stored==self.cap {self.flags|=CAP;}
            match self.dropped.checked_add(1){Some(n)=>self.dropped=n,None=>self.flags|=OVERFLOW};return;
        }
        event.0[0]=self.stored+1;
        let w=&event.0;
        if !event.valid(self.code_count){self.flags|=RANGE;self.dropped+=1;return;}
        if w[4]<self.last_work||w[5]<self.last_instructions||w[2]<self.phase {
            self.flags|=LIFECYCLE;self.dropped+=1;return;
        }
        if w[2]!=self.phase {self.flags|=LIFECYCLE;self.dropped+=1;return;}
        if w[1]==1 {if self.pin_failed||self.terminal_failed||w[3]!=self.operation+1 {self.flags|=LIFECYCLE;self.dropped+=1;return;}self.operation=w[3];}
        else if w[1]!=12&&w[1]!=13&&w[1]!=14&&w[3]!=self.operation {self.flags|=LIFECYCLE;self.dropped+=1;return;}
        if w[1]==14 {if w[3]==0{if self.terminal_failed{self.flags|=LIFECYCLE;self.dropped+=1;return;}self.terminal_failed=true;}else {if w[3]!=self.operation||self.pin_failed{self.flags|=LIFECYCLE;self.dropped+=1;return;}self.pin_failed=true;}}
        event.encode(&mut self.record);
        self.buffer[self.used..self.used+128].copy_from_slice(&self.record);self.used+=128;
        self.stored+=1;self.last_work=w[4];self.last_instructions=w[5];
        if self.used==4096 {self.flush_records();}
    }
    pub fn flush_records(&mut self) {
        if self.used==0||self.flags&!CAP!=0{return;}
        if !bounded_write(&mut self.sink,&self.buffer[..self.used],&mut self.attempts){self.flags|=IO;}
        self.used=0;
    }
    // Caller supplies original terminal and final-consuming ledger words only.
    pub fn finish(&mut self,mut footer:[u64;64])->[u64;64] {
        if self.ended {footer[9]|=LIFECYCLE as u64;return footer;}
        self.ended=true;self.flush_records();
        footer[0]=FOOTER_MAGIC;footer[1]=1;footer[2]=self.stored;footer[3]=self.attempted;footer[4]=self.dropped;
        footer[5]=self.stored;footer[6]=self.last_work;footer[7]=self.last_instructions;footer[8]=self.operation;
        footer[9]|=self.flags as u64;footer[15]=self.observed_mask;footer[33]=self.phase;footer[35]=self.cap;
        // attempts includes the actual terminal block after the write; wire word
        // stores the attempts before that block (closed finite bound definition).
        footer[34]=self.attempts;footer[36..44].copy_from_slice(&self.bindings);
        let bytes=encode_frame(&footer);
        if !bounded_write(&mut self.sink,&bytes,&mut self.attempts){self.flags|=IO;}
        footer
    }
}
pub fn valid_footer_fields(head:&[u8;512],raw:&[u8;512],file_bytes:u64)->bool{
    if !valid_header(head){return false;}
    let word=|i:usize|u64::from_le_bytes(raw[i*8..i*8+8].try_into().unwrap());
    let cap=u64::from_le_bytes(head[40..48].try_into().unwrap());
    let expected=u64::from_le_bytes(head[72..80].try_into().unwrap());
    let flags=word(9);
    if word(0)!=FOOTER_MAGIC||word(1)!=1||word(2)>cap||word(5)!=word(2)||word(3).checked_sub(word(2))!=Some(word(4))||flags>=512||word(35)!=cap||word(34)>4_194_336||word(10)<word(6)||word(11)<word(7)||word(15)>=64||word(33)>5||word(31)>5||word(32)>1||raw[352..].iter().any(|b|*b!=0)||raw[288..352]!=head[128..192]{return false;}
    if word(2).checked_mul(128).and_then(|n|n.checked_add(1024))!=Some(file_bytes){return false;}
    if word(12)==0 {if word(13)!=0||word(14)!=ABSENT||word(32)!=0{return false;}}
    else if word(12)>21||word(13)>24||(word(13)==0&&flags&CODE as u64==0)||!(1..=6).contains(&word(14))||word(32)!=1{return false;}
    if flags==0 {if word(4)!=0||word(15)!=expected||word(33)!=5{return false;}}
    if flags==CAP as u64&&(word(2)!=cap||word(3)<=word(2)||word(4)==0||word(15)!=expected||word(33)!=5){return false;}
    true
}
#[cfg(test)] mod tests {
    use super::*;
    #[derive(Debug)] struct Sink{bytes:[u8;16384],used:usize,quantum:usize,interrupts:usize,zero:bool,error:bool,calls:usize}
    impl Sink{fn new()->Self{Self{bytes:[0;16384],used:0,quantum:usize::MAX,interrupts:0,zero:false,error:false,calls:0}}}
    impl Write for Sink{fn write(&mut self,b:&[u8])->io::Result<usize>{self.calls+=1;if self.interrupts>0{self.interrupts-=1;return Err(io::ErrorKind::Interrupted.into());}if self.zero{return Ok(0);}if self.error{return Err(io::ErrorKind::BrokenPipe.into());}let n=b.len().min(self.quantum);self.bytes[self.used..self.used+n].copy_from_slice(&b[..n]);self.used+=n;Ok(n)}fn flush(&mut self)->io::Result<()>{Ok(())}}
    fn writer(cap:u64)->Writer<Sink>{let h=header(cap,33,[[7;32];4]).unwrap();Writer::new(Sink::new(),cap,33,24,&h).unwrap()}
    fn event()->Record{Record::new(1,0,1,40)}
    #[test]fn wire_roundtrip_closed_fields(){let mut r=event();r.0[0]=1;assert!(r.valid(24));let mut b=[0;128];r.encode(&mut b);assert_eq!(Record::decode(&b),r);for i in 7..10{let mut x=r;x.0[i]=0;assert!(!x.valid(24));}let mut x=r;x.0[15]=1;assert!(!x.valid(24));}
    #[test]fn header_closed_mutations(){let h=header(32,33,[[7;32];4]).unwrap();assert!(valid_header(&h));for i in [80,127,256,511]{let mut x=h;x[i]=1;assert!(!valid_header(&x));}for cap in [0,MAX_RECORDS+1]{assert!(header(cap,33,[[0;32];4]).is_none());}}
    #[test]fn bounded_short_write_interrupted_zero_error(){let mut s=Sink::new();s.quantum=4;s.interrupts=2;let mut a=0;assert!(bounded_write(&mut s,&[1;120],&mut a));assert_eq!(a,32);assert_eq!(s.used,120);let mut s=Sink::new();s.interrupts=33;let mut a=0;assert!(!bounded_write(&mut s,&[1;1],&mut a));assert_eq!(a,32);for zero in [false,true]{let mut s=Sink::new();s.zero=zero;s.error=!zero;let mut a=0;assert!(!bounded_write(&mut s,&[1;1],&mut a));assert_eq!(a,1);}}
    #[test]fn cap_prefix_tiny_positions(){for cap in 1..=32{let mut w=writer(cap);for n in 1..=cap+4{let mut r=event();r.0[3]=n;w.push(r);}let f=w.finish([0;64]);assert_eq!(f[2],cap);assert_eq!(f[3],cap+4);assert_eq!(f[4],4);assert_eq!(f[9],CAP as u64);assert_eq!(w.sink.used,1024+128*cap as usize);assert_eq!(w.attempts,3);}}
    #[test]fn sticky_io_never_resumes(){let mut w=writer(64);w.sink.zero=true;for n in 1..=33{let mut r=event();r.0[3]=n;w.push(r);}assert_eq!(w.flags,IO);let used=w.sink.used;w.sink.zero=false;let mut r=event();r.0[3]=34;w.push(r);assert_eq!(w.stored,32);assert_eq!(w.dropped,2);assert_eq!(w.sink.used,used);}
    #[test]fn range_lifecycle_and_overflow_sticky(){let mut w=writer(32);let mut r=event();r.0[6]=80000;w.push(r);assert_eq!(w.flags,RANGE);assert_eq!(w.attempted,w.stored+w.dropped);let mut w=writer(32);let mut r=event();r.0[3]=2;w.push(r);assert_eq!(w.flags,LIFECYCLE);let mut w=writer(32);w.attempted=u64::MAX;w.push(event());assert_eq!(w.flags,OVERFLOW);}
    #[test]fn duplicate_finish_no_second_frame(){let mut w=writer(32);w.push(event());w.finish([0;64]);let used=w.sink.used;let f=w.finish([0;64]);assert_ne!(f[9]&LIFECYCLE as u64,0);assert_eq!(w.sink.used,used);}
    #[test]fn footer_closed_fields_and_cap_lifecycle(){
        let mut w=writer(1);w.push(event());let mut p=Record::new(13,5,0,ABSENT);p.0[13]=5;w.push(p);
        let mut original=[0;64];original[14]=ABSENT;let f=w.finish(original);let h=header(1,33,[[7;32];4]).unwrap();let raw=encode_frame(&f);assert_eq!(f[9],CAP as u64);assert!(valid_footer_fields(&h,&raw,w.sink.used as u64));
        for i in [0,8,352,511]{let mut x=raw;x[i]^=1;assert!(!valid_footer_fields(&h,&x,w.sink.used as u64));}
        let mut x=f;x[2]=0;x[5]=0;assert!(!valid_footer_fields(&h,&encode_frame(&x),1024));
        let mut x=f;x[13]=1;assert!(!valid_footer_fields(&h,&encode_frame(&x),w.sink.used as u64));
    }

}
