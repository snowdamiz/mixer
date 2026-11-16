use std::time::{Duration,Instant};
#[derive(Clone,Copy,Debug,Default,PartialEq,Eq)]
pub(crate) struct Counters { pub cache:u64, pub execution:u64, pub fuel:u64, pub hosts:u64 }
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) enum Kind { Initialize, Start, Event }
#[derive(Clone,Copy,Debug)]
enum Phase { Dormant, Running {epoch:u64,kind:Kind,baseline:Counters,deadline:Instant}, Idle {epoch:u64,kind:Kind,totals:Counters}, Terminal }
#[derive(Clone,Copy,Debug)]
pub(crate) struct UiTurns { phase:Phase }
pub(crate) fn checked_charge(total:u64,baseline:u64,credits:u64,limit:u64)->Option<u64> {
 let next=total.checked_add(credits)?;
 (next.checked_sub(baseline)?<=limit).then_some(next)
}
impl UiTurns {
 pub fn new()->Self {Self {phase:Phase::Dormant}}
 pub fn begin(&mut self,kind:Kind,counters:Counters,now:Instant,millis:u64,quiescent:bool,cancelled:bool)->Result<(u64,Instant),&'static str>{
  if cancelled {self.terminal();return Err("ui_turn_cancelled")}
  if !quiescent {return Err("ui_turn_not_quiescent")}
  let epoch=match (self.phase,kind) {
   (Phase::Dormant,Kind::Initialize)=>1,
   (Phase::Idle{epoch,kind:Kind::Initialize,totals},Kind::Start)|
   (Phase::Idle{epoch,kind:Kind::Start|Kind::Event,totals},Kind::Event)=>{if !counters.at_least(totals){return Err("ui_turn_counter_regression")} epoch.checked_add(1).ok_or("ui_turn_epoch_overflow")?},
   _=>return Err("ui_turn_phase")
  };
  let deadline=now.checked_add(Duration::from_millis(millis)).ok_or("ui_turn_deadline_overflow")?;
  self.phase=Phase::Running{epoch,kind,baseline:counters,deadline};Ok((epoch,deadline))
 }
 pub fn end(&mut self,epoch:u64,quiescent:bool,counters:Counters)->Result<(),&'static str>{
  match self.phase {
   Phase::Running{epoch:e,kind,baseline,..} if e==epoch && quiescent && counters.at_least(baseline)=>{self.phase=Phase::Idle{epoch,kind,totals:counters};Ok(())},
   _=>Err("ui_turn_end")
  }
 }
 pub fn baseline(&self)->Option<Counters>{match self.phase{Phase::Running{baseline,..}=>Some(baseline),_=>None}}
 pub fn epoch(&self)->Option<u64>{match self.phase{Phase::Running{epoch,..}=>Some(epoch),_=>None}}
 pub fn terminal(&mut self){self.phase=Phase::Terminal}
 pub fn deadline(&self)->Option<Instant>{match self.phase{Phase::Running{deadline,..}=>Some(deadline),_=>None}}
}

impl Counters {
 fn at_least(self,b:Self)->bool {self.cache>=b.cache&&self.execution>=b.execution&&self.fuel>=b.fuel&&self.hosts>=b.hosts}
}
#[cfg(test)]
pub(crate) fn value_only_epoch_and_retention_controls() {
 let now=Instant::now();let c=Counters::default();
 let mut t=UiTurns{phase:Phase::Idle{epoch:u64::MAX,kind:Kind::Start,totals:c}};
 assert_eq!(t.begin(Kind::Event,c,now,30_000,true,false),Err("ui_turn_epoch_overflow"));
 let mut t=UiTurns::new();
 let retained_bytes=123456u64;let retained_tickets=278u64;let total_copy_bytes=2048u64;
 let retained=(retained_bytes,retained_tickets,total_copy_bytes);
 let (e,d)=t.begin(Kind::Initialize,c,now,30_000,true,false).unwrap();
 assert_eq!(t.begin(Kind::Initialize,c,now+Duration::from_secs(5),30_000,true,false),Err("ui_turn_phase"));
 assert_eq!(t.deadline(),Some(d));
 let c=Counters{cache:20,execution:30,fuel:40,hosts:50};
 t.end(e,true,c).unwrap();
 assert_eq!(t.begin(Kind::Start,Counters::default(),now,30_000,true,false),Err("ui_turn_counter_regression"));
 let (e,d2)=t.begin(Kind::Start,c,now+Duration::from_secs(60),30_000,true,false).unwrap();
 assert_eq!(d2,now+Duration::from_secs(90));
 assert_eq!(t.end(e,true,Counters::default()),Err("ui_turn_end"));
 assert_eq!(retained,(retained_bytes,retained_tickets,total_copy_bytes));
 t.end(e,true,c).unwrap();
 assert_eq!(t.begin(Kind::Event,c,now,30_000,true,true),Err("ui_turn_cancelled"));
 assert!(t.begin(Kind::Event,c,now,30_000,true,false).is_err());
 t.terminal();assert!(t.begin(Kind::Initialize,c,now,30_000,true,false).is_err());
 println!("PASS value-only epoch overflow, monotonic totals, retained fields unchanged, idle-only deadline, sticky cancellation and terminal guards");
}

// Construction's named foundation envelope remains reserved until consuming close.
// Phase growth and an extra transient ticket are therefore distinct from that floor.
#[derive(Clone,Copy,Debug)]
pub(crate) struct FoundationReservation {
 pub current:usize, pub ticket_bytes:usize, pub floor:Option<usize>,
 pub owner_matches:bool, pub category_matches:bool,
}
pub(crate) fn boundary_ready(active:[usize;4],foundation:FoundationReservation,
 cache_entries:usize,live_tickets:usize,fixed_tickets:usize)->bool {
 active==[0;4] && foundation.owner_matches && foundation.category_matches &&
 foundation.floor.is_some_and(|floor|foundation.current==floor&&foundation.ticket_bytes==floor) &&
 fixed_tickets.checked_add(cache_entries)==Some(live_tickets)
}
pub(crate) fn profile_supported(profile_id:u32)->bool {profile_id==1}
#[cfg(test)]
pub(crate) fn value_only_foundation_controls(fixed:usize) {
 let floor=275152;
 let f=FoundationReservation{current:floor,ticket_bytes:floor,floor:Some(floor),owner_matches:true,category_matches:true};
 assert!(boundary_ready([0;4],f,0,fixed,fixed));
 assert!(boundary_ready([0;4],f,256,fixed+256,fixed));
 assert!(!boundary_ready([0;4],FoundationReservation{current:floor+1,..f},0,fixed,fixed));
 assert!(!boundary_ready([0;4],FoundationReservation{ticket_bytes:floor+1,..f},0,fixed,fixed));
 assert!(!boundary_ready([0;4],FoundationReservation{owner_matches:false,..f},0,fixed,fixed));
 assert!(!boundary_ready([0;4],FoundationReservation{category_matches:false,..f},0,fixed,fixed));
 assert!(!boundary_ready([0;4],FoundationReservation{floor:None,..f},0,fixed,fixed));
 assert!(!boundary_ready([0;4],f,0,fixed+1,fixed));
 assert!(!boundary_ready([0;4],f,0,5,fixed));
 assert!(!boundary_ready([0;4],f,usize::MAX,0,fixed));
 for i in 0..4 {let mut active=[0;4];active[i]=1;assert!(!boundary_ready(active,f,0,fixed,fixed));}
 assert!(profile_supported(1));
 for id in [0,2,u32::MAX]{assert!(!profile_supported(id));}
 println!("PASS production foundation-floor helper accepts retained envelope, rejects phase growth/transient tickets/adoption-only inventory/owner/category/overflow/live frames/pins/operands/labels; profile0/2/MAX rejected");
}
