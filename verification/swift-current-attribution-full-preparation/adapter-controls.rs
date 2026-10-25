// Finite controls only. Assertions here are test oracles, never the full driver.
struct FullTestSink { bytes:[u8;FULL_LIFETIME_OUTPUT],len:usize,fail:bool }
impl FullTestSink {fn new()->Self {Self{bytes:[0;FULL_LIFETIME_OUTPUT],len:0,fail:false}} fn text(&self)->&str {std::str::from_utf8(&self.bytes[..self.len]).unwrap()}}
impl std::io::Write for FullTestSink {
    fn write(&mut self,b:&[u8])->std::io::Result<usize>{
        if self.fail || self.len+b.len()>self.bytes.len(){return Err(std::io::Error::other("finite sink rejected"));}
        self.bytes[self.len..self.len+b.len()].copy_from_slice(b);self.len+=b.len();Ok(b.len())
    }
    fn flush(&mut self)->std::io::Result<()> {if self.fail {Err(std::io::Error::other("finite flush rejected"))}else{Ok(())}}
}
fn full_test_end(cache:SwiftFunctionCache,mut c:RuntimeControl,sink:&mut FullTestSink) {
    let decodes=cache.usage().decodes;let before=c.usage(None).cache_work;
    let _=cleanup(cache,&mut c,None);let u=c.finish_owned_cleanup(None);
    assert_eq!(u.cache_work,before);assert_eq!(u.cleanup_invariant,None);
    assert_eq!((u.reservations.combined.current,u.reservations.live_tickets),(0,0));
    assert!(full_snapshot_to(FullAttributionPhase::FinalCleanup,u.cache_work,decodes,true,ATTR_OUTPUT,sink));
}
#[test]
fn full_attribution_adapter_lifecycle_and_bounds() {
    hooks(Hooks::default());full_attribution_begin();
    let bytes=fixture(0,&[0,0x0b],600);let (mut c,mut cache)=new(&bytes,SwiftRunBudget::default());let mut sink=FullTestSink::new();
    for (phase,index) in [(FullAttributionPhase::Constructed,None),(FullAttributionPhase::Initialize,Some(34)),(FullAttributionPhase::Corpus1,Some(35)),(FullAttributionPhase::Corpus2,Some(34)),(FullAttributionPhase::BeforeCleanup,None)] {
        if let Some(f)=index {attr_one(&mut cache,&mut c,f);}
        assert!(full_snapshot_to(phase,c.usage(None).cache_work,cache.usage().decodes,false,ATTR_OUTPUT,&mut sink));
    }
    let t=attr_totals();full_test_end(cache,c,&mut sink);
    assert_eq!(sink.text().lines().count(),6);assert!(sink.len<=FULL_LIFETIME_OUTPUT);
    assert!(sink.text().lines().all(|l|l.len()+1<=FULL_ENVELOPE && l.contains("\"valid\":true")));
    FULL_ATTRIBUTION_LIFETIME.with(|s|{let m=s.borrow();assert_eq!((m.reset_count,m.seen,m.emissions,m.invalid),(1,63,6,0));assert!(!m.active);});
    assert_eq!(attr_totals(),t);
    println!("FULL_ADAPTER lifecycle=6 reset=1 cumulative_bitmap=true final_original_usage_and_preconsumption_decodes=true max_envelope={} max_lifetime={} observed_bytes={} guest_instructions=0 cleanup_zero=true",FULL_ENVELOPE,FULL_LIFETIME_OUTPUT,sink.len);
}
#[test]
fn full_attribution_adapter_invalid_does_not_replace_failure() {
    let bytes=fixture(0,&[0,0x0b],600);let mut original=None;
    for mode in 0..4 {
        hooks(Hooks::default());full_attribution_begin();
        let (mut c,mut cache)=new(&bytes,SwiftRunBudget{cache_work:5078,..SwiftRunBudget::default()});
        let failure=pin(&mut cache,&mut c,34,None).unwrap_err();
        if let Some(old)=original {let old:SwiftRunFailure=old;assert_eq!((old.stage,old.kind,old.code,old.function,old.offset,old.resource,old.attempted,old.limit),(failure.stage,failure.kind,failure.code,failure.function,failure.offset,failure.resource,failure.attempted,failure.limit));}else{original=Some(failure);}
        if mode==1 {CURRENT_ATTRIBUTION.with(|s|s.borrow_mut().site(255));}
        if mode==2 {CURRENT_ATTRIBUTION.with(|s|s.borrow_mut().totals.credits[1]=u64::MAX);}
        let mut sink=FullTestSink::new();let work=c.usage(None).cache_work;
        assert!(full_snapshot_to(FullAttributionPhase::Constructed,work,cache.usage().decodes,false,if mode==3{64}else{ATTR_OUTPUT},&mut sink));
        if mode==0 {assert!(sink.text().contains("\"valid\":true"));}
        else {assert!(sink.text().contains("\"valid\":false") && sink.text().contains("\"payload\":null"));}
        if mode==3 {assert!(sink.text().contains("\"formatted\":false,\"observer_invalid\":8"));assert!(!sink.text().contains("\"credits\""));CURRENT_ATTRIBUTION.with(|s|assert_eq!(s.borrow().invalid,8));}
        let retry=pin(&mut cache,&mut c,35,None).unwrap_err();
        assert_eq!((failure.stage,failure.kind,failure.code,failure.function,failure.offset,failure.resource,failure.attempted,failure.limit),(retry.stage,retry.kind,retry.code,retry.function,retry.offset,retry.resource,retry.attempted,retry.limit));
        assert_eq!(c.usage(None).cache_work,work);full_test_end(cache,c,&mut sink);
        println!("FULL_ADAPTER_INVALID mode={mode} original=WorkExhausted attempted=5079 limit=5078 partial_payload_discarded=true sticky_failure_preserved=true cleanup_zero=true");
    }
}
#[test]
fn full_attribution_adapter_order_reset_and_write_failure() {
    hooks(Hooks::default());full_attribution_begin();
    let bytes=fixture(0,&[0,0x0b],600);let (c,cache)=new(&bytes,SwiftRunBudget::default());let mut sink=FullTestSink::new();
    let t=attr_totals();full_attribution_begin();assert_eq!(attr_totals(),t); // second begin cannot reset this lifetime.
    assert!(full_snapshot_to(FullAttributionPhase::Corpus1,c.usage(None).cache_work,0,false,ATTR_OUTPUT,&mut sink));
    assert!(full_snapshot_to(FullAttributionPhase::Corpus1,c.usage(None).cache_work,0,false,ATTR_OUTPUT,&mut sink));
    assert!(full_snapshot_to(FullAttributionPhase::Initialize,c.usage(None).cache_work,0,false,ATTR_OUTPUT,&mut sink));
    FULL_ATTRIBUTION_LIFETIME.with(|s|{let m=s.borrow();assert_eq!(m.invalid&7,7);assert_eq!(m.reset_count,1);});
    let mut failed=FullTestSink::new();failed.fail=true;
    assert!(!full_snapshot_to(FullAttributionPhase::BeforeCleanup,c.usage(None).cache_work,0,false,ATTR_OUTPUT,&mut failed));assert_eq!(failed.len,0);
    full_test_end(cache,c,&mut sink);assert!(sink.text().contains("\"prior_write_failed\":true"));
    assert!(full_snapshot_to(FullAttributionPhase::FinalCleanup,0,0,true,ATTR_OUTPUT,&mut sink));let before=sink.len;
    assert!(!full_snapshot_to(FullAttributionPhase::FinalCleanup,0,0,true,ATTR_OUTPUT,&mut sink));assert_eq!(sink.len,before);
    FULL_ATTRIBUTION_LIFETIME.with(|s|assert_eq!(s.borrow().emissions,6));
    println!("FULL_ADAPTER_META duplicate=true order=true second_reset_refused=true write_failure_separate=true seventh_output_suppressed=true guest_instructions=0 cleanup_zero=true");
}
