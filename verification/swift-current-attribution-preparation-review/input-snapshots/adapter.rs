// Test-only bridge appended after the accepted observer, never production code.
// No cache operation runs with an observer/adapter RefCell borrow retained.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum FullAttributionPhase { Constructed, Initialize, Corpus1, Corpus2, BeforeCleanup, FinalCleanup }
impl FullAttributionPhase {
    fn rank(self) -> u8 { match self { Self::Constructed=>0,Self::Initialize=>1,Self::Corpus1=>2,Self::Corpus2=>3,Self::BeforeCleanup=>4,Self::FinalCleanup=>5 } }
    fn label(self) -> &'static str { match self { Self::Constructed=>"constructed",Self::Initialize=>"initialize",Self::Corpus1=>"corpus_1",Self::Corpus2=>"corpus_2",Self::BeforeCleanup=>"before_cleanup",Self::FinalCleanup=>"final_cleanup" } }
}
const FULL_ENVELOPE: usize = 4_608;
const FULL_LIFETIME_OUTPUT: usize = 6 * FULL_ENVELOPE;
#[derive(Default)]
struct FullAttributionLifetime { active:bool, reset_count:u8, seen:u8, last:Option<u8>, emissions:u8, invalid:u32, write_failed:bool }
thread_local! { static FULL_ATTRIBUTION_LIFETIME: RefCell<FullAttributionLifetime> = RefCell::new(FullAttributionLifetime::default()); }
pub(super) fn full_attribution_begin() {
    let begin=FULL_ATTRIBUTION_LIFETIME.with(|s| {
        let Ok(mut m)=s.try_borrow_mut() else { return false; };
        if m.active {m.invalid|=4;return false;}
        *m=FullAttributionLifetime{active:true,reset_count:1,..FullAttributionLifetime::default()};true
    });
    if begin {attr_reset();}
}
struct FullCapture { text:AttributionText, formatted:bool, invalid:u32, invariant_mask:u32 }
fn full_capture(work:u64,decodes:u64,limit:usize)->Option<FullCapture> {
    CURRENT_ATTRIBUTION.with(|s| {
        let Ok(mut x)=s.try_borrow_mut() else {return None;};
        let t=x.totals;let sum=|v:&[u64]|v.iter().map(|v|u128::from(*v)).sum::<u128>();
        let mut mask=0;
        if sum(&t.credits)!=u128::from(work) {mask|=1;}
        if sum(&t.scan_credits)!=u128::from(t.credits[6]) || sum(&t.scan_calls)!=u128::from(t.calls[6]) {mask|=2;}
        if sum(&t.build_credits)!=u128::from(t.credits[13]) || sum(&t.build_calls)!=u128::from(t.calls[13]) {mask|=4;}
        if sum(&t.scan_published)!=u128::from(t.plans[3]) {mask|=8;}
        if u128::from(t.distinct)+u128::from(t.repeated)!=u128::from(t.completed) || t.completed!=decodes {mask|=16;}
        if x.seen.iter().map(|w|u64::from(w.count_ones())).sum::<u64>()!=t.distinct {mask|=32;}
        let mut text=AttributionText::new(limit);
        let formatted=attr_format(&mut x,&mut text);
        if !formatted {text.bytes.fill(0);text.len=0;} // Discard ALL partial bytes, including stale invalid=0.
        Some(FullCapture{text,formatted,invalid:x.invalid,invariant_mask:mask})
    })
}
struct FullEnvelope {bytes:[u8;FULL_ENVELOPE],len:usize}
impl FullEnvelope {fn new()->Self {Self{bytes:[0;FULL_ENVELOPE],len:0}}}
impl std::fmt::Write for FullEnvelope {
    fn write_str(&mut self,s:&str)->std::fmt::Result {
        let Some(end)=self.len.checked_add(s.len()).filter(|n|*n<=FULL_ENVELOPE) else {return Err(std::fmt::Error);};
        self.bytes[self.len..end].copy_from_slice(s.as_bytes());self.len=end;Ok(())
    }
}
fn full_snapshot_to<W:std::io::Write>(phase:FullAttributionPhase,work:u64,decodes:u64,preconsumption:bool,limit:usize,sink:&mut W)->bool {
    let metadata=FULL_ATTRIBUTION_LIFETIME.with(|s| {
        let Ok(mut m)=s.try_borrow_mut() else {return None;};
        if m.emissions>=6 {m.invalid|=32;return None;}
        let rank=phase.rank();let bit=1u8<<rank;
        if !m.active {m.invalid|=8;}
        if m.seen & bit != 0 {m.invalid|=1;}
        if m.last.is_some_and(|last|rank<=last) {m.invalid|=2;}
        if phase==FullAttributionPhase::FinalCleanup && !preconsumption {m.invalid|=16;}
        m.seen|=bit;m.last=Some(rank);m.emissions+=1;
        if phase==FullAttributionPhase::FinalCleanup {m.active=false;}
        Some((m.reset_count,m.emissions,m.invalid,m.write_failed))
    });
    let Some((resets,sequence,adapter_invalid,write_failed))=metadata else {return false;};
    let capture=full_capture(work,decodes,limit);
    let (formatted,invalid,invariants,payload)=match &capture {
        Some(c)=>{
            let text=if c.formatted && c.invalid==0 && c.invariant_mask==0 {std::str::from_utf8(&c.text.bytes[..c.text.len]).ok()}else{None};
            (c.formatted,c.invalid,c.invariant_mask,text)
        }
        None=>(false,0,64,None),
    };
    let valid=formatted && invalid==0 && invariants==0 && adapter_invalid==0 && !write_failed && payload.is_some();
    let payload=if valid {payload.unwrap_or("null")}else{"null"}; // Option fallback only; no Result replacement/panic.
    let mut envelope=FullEnvelope::new();
    let result=write!(&mut envelope,"MIXER_ATTRIBUTION {{\"lifecycle\":\"{}\",\"sequence\":{},\"reset_count\":{},\"formatted\":{},\"observer_invalid\":{},\"invariant_mask\":{},\"adapter_invalid\":{},\"prior_write_failed\":{},\"valid\":{},\"cache_work\":{},\"cache_decodes\":{},\"decodes_bound_before_consumption\":{},\"payload\":{}}}\n",phase.label(),sequence,resets,formatted,invalid,invariants,adapter_invalid,write_failed,valid,work,decodes,preconsumption,payload);
    let wrote=result.is_ok() && sink.write_all(&envelope.bytes[..envelope.len]).is_ok() && sink.flush().is_ok();
    if !wrote {FULL_ATTRIBUTION_LIFETIME.with(|s|{if let Ok(mut m)=s.try_borrow_mut(){m.write_failed=true;}});}
    wrote
}
pub(super) fn full_attribution_snapshot(phase:FullAttributionPhase,work:u64,decodes:u64,preconsumption:bool) {
    let stdout=std::io::stdout();let mut sink=stdout.lock();
    let _=full_snapshot_to(phase,work,decodes,preconsumption,ATTR_OUTPUT,&mut sink);
}
