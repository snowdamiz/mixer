//! Data-only proposal tests against exact released source declarations.
//! No source proof, selection, load, release, owner or replay authority exists here.
#![forbid(unsafe_code)]
#[path = "actual_data_records.rs"] mod actual;
use actual::*;

type Refusal = &'static str;
macro_rules! closed_enum {
    ($encode:ident, $decode:ident, $ty:ident, {$($name:ident = $id:literal),+ $(,)?}) => {
        fn $encode(value:$ty)->u64 {match value {$($ty::$name=>$id),+}}
        fn $decode(value:u64)->Result<$ty,Refusal> {match value {$($id=>Ok($ty::$name)),+, _=>Err("unknown enum")}}
    }
}
closed_enum!(category_word, word_category, SwiftReservationCategory, {
    RetainedSource=1,RetainedMetadata=2,Cache=3,State=4,Wasi=5,Shared=6,Construction=7
});
closed_enum!(stage_word, word_stage, SwiftRunStage, {
    Adoption=1,Cache=2,Initialization=3,Invocation=4,Wasi=5,Cleanup=6
});
closed_enum!(kind_word, word_kind, SwiftRunFailureKind, {
    InvalidBudget=1,Cancelled=2,Deadline=3,Allocation=4,Adoption=5,
    CategoryExhausted=6,CombinedExhausted=7,ResourceExhausted=8,FuelExhausted=9,
    WorkExhausted=10,HostCallLimit=11,PinLimit=12,FrameLimit=13,ValueLimit=14,
    ControlLimit=15,DecoderMismatch=16,UnsupportedEnvironment=17,GuestTrap=18,
    GuestExit=19,Wasi=20,Invariant=21
});
closed_enum!(cleanup_word, word_cleanup, SwiftCleanupInvariant, {
    ReservationOwner=1,ReservationUnderflow=2,MissingConstruction=3,ConstructionBound=4,LiveUnderflow=5
});
closed_enum!(origin_word, word_origin, SwiftDeadlineOrigin, {Run=1,Wasi=2});
closed_enum!(wasi_resource_word, word_wasi_resource, Resource, {
    Calls=1,Transfer=2,TransferSize=3,Work=4,Iovecs=5
});
fn resource_words(value:SwiftRunResource)->(u64,u64) {
    match value {
        SwiftRunResource::Reservation(c)=>(1,category_word(c)),
        SwiftRunResource::Combined=>(2,0),SwiftRunResource::CacheEntryBytes=>(3,0),
        SwiftRunResource::CacheEntries=>(4,0),SwiftRunResource::ActivePins=>(5,0),
        SwiftRunResource::Frames=>(6,0),SwiftRunResource::Values=>(7,0),
        SwiftRunResource::Controls=>(8,0),SwiftRunResource::MemoryPages=>(9,0),
        SwiftRunResource::CacheWork=>(10,0),SwiftRunResource::ExecutionWork=>(11,0),
        SwiftRunResource::InstructionFuel=>(12,0),SwiftRunResource::HostCalls=>(13,0),
        SwiftRunResource::Deadline=>(14,0),SwiftRunResource::TicketInventory=>(15,0),
        SwiftRunResource::OwnerIdentity=>(16,0),SwiftRunResource::ExactCapacity=>(17,0),
    }
}
fn words_resource(tag:u64,payload:u64)->Result<SwiftRunResource,Refusal> {
    use SwiftRunResource::*;
    if tag==1 {return Ok(Reservation(word_category(payload)?));}
    if payload!=0 {return Err("inactive reservation payload");}
    Ok(match tag {2=>Combined,3=>CacheEntryBytes,4=>CacheEntries,5=>ActivePins,
        6=>Frames,7=>Values,8=>Controls,9=>MemoryPages,10=>CacheWork,11=>ExecutionWork,
        12=>InstructionFuel,13=>HostCalls,14=>Deadline,15=>TicketInventory,
        16=>OwnerIdentity,17=>ExactCapacity,_=>return Err("unknown resource")})
}
fn wasi_words(value:WasiFailure)->(u64,u64) {
    match value {
        WasiFailure::InvalidBudget=>(1,0),WasiFailure::Allocation=>(2,0),
        WasiFailure::InvalidArguments=>(3,0),WasiFailure::InvalidMemory=>(4,0),
        WasiFailure::Budget(r)=>(5,wasi_resource_word(r)),WasiFailure::Cancelled=>(6,0),
        WasiFailure::Deadline=>(7,0),WasiFailure::Invariant=>(8,0),
    }
}
fn words_wasi(tag:u64,payload:u64)->Result<WasiFailure,Refusal> {
    if tag==5 {return Ok(WasiFailure::Budget(word_wasi_resource(payload)?));}
    if payload!=0 {return Err("inactive WASI payload");}
    Ok(match tag {1=>WasiFailure::InvalidBudget,2=>WasiFailure::Allocation,
        3=>WasiFailure::InvalidArguments,4=>WasiFailure::InvalidMemory,
        6=>WasiFailure::Cancelled,7=>WasiFailure::Deadline,8=>WasiFailure::Invariant,
        _=>return Err("unknown WASI failure")})
}
fn words<const N:usize>(bytes:&[u8])->[u64;N] {
    std::array::from_fn(|i|u64::from_le_bytes(bytes[i*8..i*8+8].try_into().unwrap()))
}
fn bytes<const N:usize>(words:&[u64])->[u8;N] {
    let mut out=[0;N];for (i,w) in words.iter().enumerate(){out[i*8..i*8+8].copy_from_slice(&w.to_le_bytes());}out
}
fn widen(n:usize)->Result<u64,Refusal>{u64::try_from(n).map_err(|_|"usize exceeds wire")}
fn narrow(n:u64)->Result<usize,Refusal>{usize::try_from(n).map_err(|_|"wire exceeds usize")}

// Exact 64-word logical encoding; no Rust memory representation is copied.
fn encode_usage(u:&SwiftRunUsage)->Result<[u8;512],Refusal> {
    let mut w=[0u64;64];let r=&u.reservations;
    for (i,v) in [r.retained_source,r.retained_metadata,r.cache,r.state,r.wasi,r.shared,r.construction,r.combined].iter().enumerate(){w[i*2]=widen(v.current)?;w[i*2+1]=widen(v.peak)?;}
    w[16]=widen(r.live_tickets)?;w[17]=widen(r.peak_tickets)?;
    let l=&u.live;
    for (i,v) in [l.cache_entries,l.active_pins,l.frames,l.values,l.controls,l.memory_pages].iter().enumerate(){w[18+i*2]=widen(v.current)?;w[19+i*2]=widen(v.peak)?;}
    w[30..35].copy_from_slice(&[u.cache_work,u.execution_work,u.instruction_fuel,u.instructions,u.host_calls]);
    w[35]=u.cleanup_invariant.map_or(0,cleanup_word);
    w[36..40].copy_from_slice(&[u.elapsed_micros,u.deadline_ms,origin_word(u.deadline_origin),u.deadline_overshoot_micros]);
    let v=&u.validation;
    w[40..50].copy_from_slice(&[widen(v.input_visible_bytes)?,widen(v.source_bytes)?,widen(v.metadata_reserved)?,widen(v.scratch_reserved)?,widen(v.metadata_peak_reserved)?,widen(v.scratch_peak_reserved)?,widen(v.total_peak_reserved)?,v.work_used,v.elapsed_micros,v.deadline_ms]);
    if let Some(v)=u.wasi {let r=v.reservations;w[50]=1;w[51..64].copy_from_slice(&[v.calls,v.work,v.transfer_bytes,v.random_bytes,v.log_bytes,v.failures,r.fixed_state_bytes,r.staging_bytes,r.rollback_bytes,r.stdout_bytes,r.stderr_bytes,r.current_bytes,r.peak_bytes]);}
    Ok(bytes(&w))
}
fn decode_usage(raw:&[u8;512])->Result<SwiftRunUsage,Refusal> {
    let w=words::<64>(raw);
    let pair=|i|->Result<SwiftReservationUsage,Refusal>{Ok(SwiftReservationUsage{current:narrow(w[i])?,peak:narrow(w[i+1])?})};
    let v=SwiftValidationUsage{input_visible_bytes:narrow(w[40])?,source_bytes:narrow(w[41])?,metadata_reserved:narrow(w[42])?,scratch_reserved:narrow(w[43])?,metadata_peak_reserved:narrow(w[44])?,scratch_peak_reserved:narrow(w[45])?,total_peak_reserved:narrow(w[46])?,work_used:w[47],elapsed_micros:w[48],deadline_ms:w[49]};
    let wasi=match w[50] {
        0=>{if w[51..64].iter().any(|n|*n!=0){return Err("absent WASI bytes");}None},
        1=>Some(WasiUsage{calls:w[51],work:w[52],transfer_bytes:w[53],random_bytes:w[54],log_bytes:w[55],failures:w[56],reservations:WasiReservations{fixed_state_bytes:w[57],staging_bytes:w[58],rollback_bytes:w[59],stdout_bytes:w[60],stderr_bytes:w[61],current_bytes:w[62],peak_bytes:w[63]}}),
        _=>return Err("WASI presence"),
    };
    Ok(SwiftRunUsage{reservations:SwiftReservations{retained_source:pair(0)?,retained_metadata:pair(2)?,cache:pair(4)?,state:pair(6)?,wasi:pair(8)?,shared:pair(10)?,construction:pair(12)?,combined:pair(14)?,live_tickets:narrow(w[16])?,peak_tickets:narrow(w[17])?},live:SwiftLiveUsage{cache_entries:pair(18)?,active_pins:pair(20)?,frames:pair(22)?,values:pair(24)?,controls:pair(26)?,memory_pages:pair(28)?},cache_work:w[30],execution_work:w[31],instruction_fuel:w[32],instructions:w[33],host_calls:w[34],cleanup_invariant:if w[35]==0{None}else{Some(word_cleanup(w[35])?)},elapsed_micros:w[36],deadline_ms:w[37],deadline_origin:word_origin(w[38])?,deadline_overshoot_micros:w[39],validation:v,wasi})
}

// The source's &'static code is encoded exactly. Decoder borrows bytes and never
// constructs a fake &'static string or a source-authoritative failure owner.
fn encode_failure_meta(f:&SwiftRunFailure)->Result<[u8;256],Refusal> {
    if f.code.is_empty()||f.code.len()>128||!f.code.bytes().all(|c|(32..=126).contains(&c)){return Err("code extent/ASCII");}
    let mut w=[0u64;16];w[0]=stage_word(f.stage);w[1]=kind_word(f.kind);w[3]=f.code.len() as u64;
    if let Some(n)=f.function{w[2]|=1;w[4]=u64::from(n);}
    if let Some(n)=f.offset{w[2]|=2;w[5]=widen(n)?;}
    if let Some(r)=f.resource{w[2]|=4;(w[6],w[7])=resource_words(r);}
    w[8]=f.attempted;w[9]=f.limit;
    if let Some(n)=f.observed_capacity{w[2]|=8;w[10]=widen(n)?;}
    w[11]=origin_word(f.deadline_origin);
    if let Some(v)=f.wasi_failure{w[2]|=16;(w[12],w[13])=wasi_words(v);}
    if let Some(n)=f.guest_exit{w[2]|=32;w[14]=u64::from(n);}
    let mut out=[0;256];out[..128].copy_from_slice(&bytes::<128>(&w));out[128..128+f.code.len()].copy_from_slice(f.code.as_bytes());Ok(out)
}
#[derive(Debug)]
struct DecodedFailure<'a> {stage:SwiftRunStage,kind:SwiftRunFailureKind,code:&'a str,function:Option<u32>,offset:Option<usize>,resource:Option<SwiftRunResource>,attempted:u64,limit:u64,observed_capacity:Option<usize>,deadline_origin:SwiftDeadlineOrigin,wasi_failure:Option<WasiFailure>,guest_exit:Option<u32>}
fn decode_failure_meta(raw:&[u8;256])->Result<DecodedFailure<'_>,Refusal> {
    let w=words::<16>(&raw[..128]);
    if w[2]>63||w[3]==0||w[3]>128||w[15]!=0{return Err("failure framing");}
    let len=w[3] as usize;
    if !raw[128..128+len].iter().all(|c|(32..=126).contains(c))||raw[128+len..].iter().any(|c|*c!=0){return Err("code padding/ASCII");}
    for (bit,indices) in [(1,&[4][..]),(2,&[5][..]),(4,&[6,7][..]),(8,&[10][..]),(16,&[12,13][..]),(32,&[14][..])]{if w[2]&bit==0&&indices.iter().any(|i|w[*i]!=0){return Err("inactive optional payload");}}
    Ok(DecodedFailure{stage:word_stage(w[0])?,kind:word_kind(w[1])?,code:std::str::from_utf8(&raw[128..128+len]).map_err(|_|"code utf8")?,function:if w[2]&1==0{None}else{Some(u32::try_from(w[4]).map_err(|_|"function width")?)},offset:if w[2]&2==0{None}else{Some(narrow(w[5])?)},resource:if w[2]&4==0{None}else{Some(words_resource(w[6],w[7])?)},attempted:w[8],limit:w[9],observed_capacity:if w[2]&8==0{None}else{Some(narrow(w[10])?)},deadline_origin:word_origin(w[11])?,wasi_failure:if w[2]&16==0{None}else{Some(words_wasi(w[12],w[13])?)},guest_exit:if w[2]&32==0{None}else{Some(u32::try_from(w[14]).map_err(|_|"guest exit width")?)}})
}
fn ledger(u:&SwiftRunUsage)->[u64;15] {
    let r=&u.reservations;let l=&u.live;
    [r.retained_source.current as u64,r.retained_metadata.current as u64,r.cache.current as u64,r.state.current as u64,r.wasi.current as u64,r.shared.current as u64,r.construction.current as u64,r.combined.current as u64,r.live_tickets as u64,l.cache_entries.current as u64,l.active_pins.current as u64,l.frames.current as u64,l.values.current as u64,l.controls.current as u64,l.memory_pages.current as u64]
}

#[cfg(test)] mod tests {
    use super::*;
    fn usage()->SwiftRunUsage {
        let mut w=std::array::from_fn::<_,64,_>(|i|100+i as u64);
        w[35]=5;w[38]=2;w[50]=1;decode_usage(&bytes(&w)).unwrap()
    }
    fn failure()->SwiftRunFailure {SwiftRunFailure{stage:SwiftRunStage::Adoption,kind:SwiftRunFailureKind::InvalidBudget,code:"swift_run_fixture",function:None,offset:None,resource:None,attempted:u64::MAX,limit:0,observed_capacity:None,deadline_origin:SwiftDeadlineOrigin::Run,wasi_failure:None,guest_exit:None,at_failure:usage(),after_cleanup:Some(usage())}}
    fn compare(f:&SwiftRunFailure){let raw=encode_failure_meta(f).unwrap();let d=decode_failure_meta(&raw).unwrap();assert_eq!((d.stage,d.kind,d.code),(f.stage,f.kind,f.code));assert_eq!((d.function,d.offset,d.resource),(f.function,f.offset,f.resource));assert_eq!((d.attempted,d.limit,d.observed_capacity),(f.attempted,f.limit,f.observed_capacity));assert_eq!((d.deadline_origin,d.wasi_failure,d.guest_exit),(f.deadline_origin,f.wasi_failure,f.guest_exit));}
    #[test]fn all_usage_fields_roundtrip(){let u=usage();assert_eq!(decode_usage(&encode_usage(&u).unwrap()).unwrap(),u);let w=words::<64>(&encode_usage(&u).unwrap());for i in 0..64{if ![35,38,50].contains(&i){assert_eq!(w[i],100+i as u64);}}}
    #[test]fn all_stage_kind_cleanup_origin_variants(){for s in 1..=6{for k in 1..=21{let mut f=failure();f.stage=word_stage(s).unwrap();f.kind=word_kind(k).unwrap();compare(&f);}}for c in 0..=5{for d in 1..=2{let mut u=usage();u.cleanup_invariant=if c==0{None}else{Some(word_cleanup(c).unwrap())};u.deadline_origin=word_origin(d).unwrap();assert_eq!(decode_usage(&encode_usage(&u).unwrap()).unwrap(),u);}}}
    #[test]fn all_resource_payloads(){for tag in 1..=17{for p in if tag==1{1..=7}else{0..=0}{let mut f=failure();f.resource=Some(words_resource(tag,p).unwrap());compare(&f);}}}
    #[test]fn all_wasi_failure_payloads(){for tag in 1..=8{for p in if tag==5{1..=5}else{0..=0}{let mut f=failure();f.wasi_failure=Some(words_wasi(tag,p).unwrap());compare(&f);}}}
    #[test]fn optional_fields_none_zero_and_max(){for mask in 0..64{let mut f=failure();if mask&1!=0{f.function=Some(0);}if mask&2!=0{f.offset=Some(0);}if mask&4!=0{f.resource=Some(SwiftRunResource::Reservation(SwiftReservationCategory::Construction));}if mask&8!=0{f.observed_capacity=Some(0);}if mask&16!=0{f.wasi_failure=Some(WasiFailure::InvalidMemory);}if mask&32!=0{f.guest_exit=Some(0);}compare(&f);}let mut f=failure();f.function=Some(u32::MAX);f.offset=Some(usize::MAX);f.observed_capacity=Some(usize::MAX);f.guest_exit=Some(u32::MAX);compare(&f);}
    #[test]fn wasi_none_is_distinct_from_some_zero(){let mut u=usage();u.wasi=None;let a=encode_usage(&u).unwrap();assert_eq!(decode_usage(&a).unwrap(),u);u.wasi=Some(WasiUsage::default());let b=encode_usage(&u).unwrap();assert_ne!(a,b);assert_eq!(decode_usage(&b).unwrap(),u);}
    #[test]fn source_width_boundaries(){let mut u=usage();u.reservations.retained_source.current=usize::MAX;u.validation.source_bytes=usize::MAX;u.cache_work=u64::MAX;assert_eq!(decode_usage(&encode_usage(&u).unwrap()).unwrap(),u);assert!(usize::BITS<=64);}
    #[test]fn unknown_and_inactive_enums_refuse(){assert!(word_stage(0).is_err());assert!(word_stage(7).is_err());assert!(word_kind(0).is_err());assert!(word_kind(22).is_err());assert!(word_cleanup(6).is_err());assert!(word_origin(0).is_err());assert!(word_category(8).is_err());assert!(word_wasi_resource(6).is_err());assert!(words_resource(18,0).is_err());assert!(words_resource(2,1).is_err());assert!(words_resource(1,0).is_err());assert!(words_wasi(9,0).is_err());assert!(words_wasi(1,1).is_err());assert!(words_wasi(5,0).is_err());}
    #[test]fn optional_and_reserved_bytes_refuse(){let f=failure();let original=encode_failure_meta(&f).unwrap();for i in [4,5,6,7,10,12,13,14,15]{let mut b=original;b[i*8]=1;assert!(decode_failure_meta(&b).is_err(),"word {i}");}for value in [64,128,u64::MAX]{let mut b=original;b[16..24].copy_from_slice(&value.to_le_bytes());assert!(decode_failure_meta(&b).is_err());}let mut b=original;b[255]=1;assert!(decode_failure_meta(&b).is_err());}
    #[test]fn u32_overflow_refuses_without_truncation(){let mut f=failure();f.function=Some(0);f.guest_exit=Some(0);let raw=encode_failure_meta(&f).unwrap();for i in [4,14]{let mut b=raw;b[i*8..i*8+8].copy_from_slice(&(u32::MAX as u64+1).to_le_bytes());assert!(decode_failure_meta(&b).is_err());}}
    #[test]fn exact_code_bytes_and_overflow_refusal(){let mut f=failure();f.code=" ";compare(&f);f.code="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";compare(&f);f.code="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";assert!(encode_failure_meta(&f).is_err());f.code="";assert!(encode_failure_meta(&f).is_err());f.code="not\ncanonical";assert!(encode_failure_meta(&f).is_err());f.code="é";assert!(encode_failure_meta(&f).is_err());}
    #[test]fn all_fifteen_ledger_words_are_independent(){let u=usage();let base=ledger(&u);let raw=encode_usage(&u).unwrap();for (slot,wire_word) in [0,2,4,6,8,10,12,14,16,18,20,22,24,26,28].iter().enumerate(){let mut w=words::<64>(&raw);w[*wire_word]+=1;let next=ledger(&decode_usage(&bytes(&w)).unwrap());for i in 0..15{assert_eq!(next[i],base[i]+u64::from(i==slot));}}}
    #[test]fn original_snapshots_and_final_consumption_stay_distinct(){let f=failure();let a=encode_usage(&f.at_failure).unwrap();let mut after=f.after_cleanup.unwrap();after.reservations.construction.current=331496;after.reservations.live_tickets=1;let b=encode_usage(&after).unwrap();let mut final_u=after;final_u.elapsed_micros+=1;final_u.reservations.construction.current=0;final_u.reservations.live_tickets=0;let c=encode_usage(&final_u).unwrap();let mut slot=[0;2048];slot[256..512].copy_from_slice(&encode_failure_meta(&f).unwrap());slot[512..1024].copy_from_slice(&a);slot[1024..1536].copy_from_slice(&b);slot[1536..2048].copy_from_slice(&c);assert_eq!(decode_usage(slot[512..1024].try_into().unwrap()).unwrap(),f.at_failure);assert_eq!(decode_usage(slot[1024..1536].try_into().unwrap()).unwrap(),after);assert_eq!(decode_usage(slot[1536..2048].try_into().unwrap()).unwrap(),final_u);assert_ne!(ledger(&after),ledger(&final_u));}
    #[test]fn absent_wasi_tail_and_presence_refuse(){let mut u=usage();u.wasi=None;let raw=encode_usage(&u).unwrap();for i in 51..64{let mut b=raw;b[i*8]=1;assert!(decode_usage(&b).is_err());}let mut b=raw;b[400]=2;assert!(decode_usage(&b).is_err());}
}
