//! Independently authored controls against the actual imported codec module.
use super::*;

const PRINTABLE: &str = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~";
const HIGH: u64 = 0x0102_0304_0506_0700;
fn pair(base: u64, i: u64) -> SwiftReservationUsage {
    SwiftReservationUsage { current: usize::try_from(base+i).unwrap(), peak: usize::try_from(base+i+1).unwrap() }
}
fn observation(base: u64) -> SwiftRunUsage {
    SwiftRunUsage {
        reservations: SwiftReservations {
            retained_source: pair(base,0), retained_metadata: pair(base,2), cache: pair(base,4),
            state: pair(base,6), wasi: pair(base,8), shared: pair(base,10), construction: pair(base,12),
            combined: pair(base,14), live_tickets: usize::try_from(base+16).unwrap(), peak_tickets: usize::try_from(base+17).unwrap(),
        },
        live: SwiftLiveUsage { cache_entries: pair(base,18), active_pins: pair(base,20), frames: pair(base,22),
            values: pair(base,24), controls: pair(base,26), memory_pages: pair(base,28) },
        cache_work: base+30, execution_work: base+31, instruction_fuel: base+32,
        instructions: base+33, host_calls: base+34, cleanup_invariant: Some(SwiftCleanupInvariant::ConstructionBound),
        elapsed_micros: base+36, deadline_ms: base+37, deadline_origin: SwiftDeadlineOrigin::Wasi, deadline_overshoot_micros: base+39,
        validation: SwiftValidationUsage {
            input_visible_bytes: usize::try_from(base+40).unwrap(), source_bytes: usize::try_from(base+41).unwrap(),
            metadata_reserved: usize::try_from(base+42).unwrap(), scratch_reserved: usize::try_from(base+43).unwrap(),
            metadata_peak_reserved: usize::try_from(base+44).unwrap(), scratch_peak_reserved: usize::try_from(base+45).unwrap(),
            total_peak_reserved: usize::try_from(base+46).unwrap(), work_used: base+47, elapsed_micros: base+48, deadline_ms: base+49,
        },
        wasi: Some(WasiUsage { calls: base+51, work: base+52, transfer_bytes: base+53, random_bytes: base+54, log_bytes: base+55, failures: base+56,
            reservations: WasiReservations { fixed_state_bytes: base+57, staging_bytes: base+58, rollback_bytes: base+59,
                stdout_bytes: base+60, stderr_bytes: base+61, current_bytes: base+62, peak_bytes: base+63 } }),
    }
}
fn original() -> SwiftRunFailure {
    SwiftRunFailure { stage: SwiftRunStage::Cleanup, kind: SwiftRunFailureKind::Invariant, code: PRINTABLE,
        function: Some(u32::MAX), offset: Some(usize::MAX), resource: Some(SwiftRunResource::Reservation(SwiftReservationCategory::Shared)),
        attempted: 0xfedc_ba98_7654_3210, limit: 0x1122_3344_5566_7788, observed_capacity: Some(0),
        deadline_origin: SwiftDeadlineOrigin::Wasi, wasi_failure: Some(WasiFailure::Budget(Resource::Iovecs)), guest_exit: Some(u32::MAX),
        at_failure: observation(HIGH), after_cleanup: Some(observation(HIGH+1000)) }
}
fn put(raw: &mut [u8], i: usize, n: u64) { raw[i*8..i*8+8].copy_from_slice(&n.to_le_bytes()); }
fn get(raw: &[u8], i: usize) -> u64 { u64::from_le_bytes(raw[i*8..i*8+8].try_into().unwrap()) }
fn usage_oracle(base: u64) -> [u8;512] {
    let mut out=[0;512]; for i in 0..64 { put(&mut out,i,base+i as u64); }
    put(&mut out,35,4); put(&mut out,38,2); put(&mut out,50,1); out
}
fn scalar_oracle() -> [u8;256] {
    let mut out=[0;256];
    let expected=[6,21,63,95,u32::MAX as u64,usize::MAX as u64,1,6,0xfedc_ba98_7654_3210,0x1122_3344_5566_7788,0,2,5,5,u32::MAX as u64,0];
    for (i,n) in expected.into_iter().enumerate() { put(&mut out,i,n); }
    out[128..223].copy_from_slice(PRINTABLE.as_bytes()); out
}
fn references<'a>(d: &'a [u8;32]) -> UnverifiedResultReferencesV1<'a> {
    UnverifiedResultReferencesV1 { raw_original_bytes: 0, constructor_tag: 0, constructor_bytes: 0,
        raw_original_digest:d,constructor_digest:d,session_digest:d,typed_result_schema_digest:d,writer_digest:d }
}

#[test]
fn independent_golden_usage_scalar_and_three_snapshot_envelope() {
    assert_eq!(usize::BITS,64); assert_eq!(PRINTABLE.len(),95);
    let f=original(); let final_u=observation(HIGH+2000); let mut u=[0xa5;512];
    encode_usage_v1(&f.at_failure,&mut u).unwrap(); assert_eq!(u,usage_oracle(HIGH));
    assert_eq!(decode_usage_v1(&usage_oracle(HIGH)).unwrap(),f.at_failure);
    let mut s=[0xa5;256]; encode_failure_scalar_v1(&f,&mut s).unwrap(); assert_eq!(s,scalar_oracle());
    let decoded=decode_failure_scalar_v1(&s).unwrap();
    assert_eq!((decoded.stage,decoded.kind,decoded.code()),(SwiftRunStage::Cleanup,SwiftRunFailureKind::Invariant,PRINTABLE));
    assert_eq!((decoded.function,decoded.offset,decoded.resource),(f.function,f.offset,f.resource));
    assert_eq!((decoded.attempted,decoded.limit,decoded.observed_capacity),(f.attempted,f.limit,f.observed_capacity));
    assert_eq!((decoded.deadline_origin,decoded.wasi_failure,decoded.guest_exit),(f.deadline_origin,f.wasi_failure,f.guest_exit));
    let z=[0;32]; let mut wire=[0xa5;2048];
    encode_result_v1(ResultObservationV1{failure:Some(&f),final_consuming:Some(&final_u),references:references(&z)},&mut wire).unwrap();
    let mut expected=[0;2048]; expected[..8].copy_from_slice(b"MIXRES01");
    for (i,n) in [1,2048,1,7,0,0,0].into_iter().enumerate() { put(&mut expected,i+1,n); }
    expected[256..512].copy_from_slice(&scalar_oracle()); expected[512..1024].copy_from_slice(&usage_oracle(HIGH));
    expected[1024..1536].copy_from_slice(&usage_oracle(HIGH+1000)); expected[1536..].copy_from_slice(&usage_oracle(HIGH+2000));
    assert_eq!(wire,expected);
    let d=decode_result_v1(&expected).unwrap(); assert_eq!(d.at_failure(),Some(&f.at_failure));
    assert_eq!(d.after_cleanup(),f.after_cleanup.as_ref()); assert_eq!(d.final_consuming(),Some(&final_u));
    assert_eq!(d.failure_scalars().unwrap().code().as_ptr(),expected[384..].as_ptr());
}

#[test]
fn every_inactive_reserved_and_padding_byte_bit_refuses() {
    let z=[0;32]; let mut empty=[0;2048];
    encode_result_v1(ResultObservationV1{failure:None,final_consuming:None,references:references(&z)},&mut empty).unwrap();
    assert!(decode_result_v1(&empty).is_ok());
    for i in 224..2048 { for bit in 0..8 { let mut bad=empty; bad[i]=1<<bit; assert!(decode_result_v1(&bad).is_err(),"result byte {i} bit {bit}"); }}
    let mut scalar=scalar_oracle(); put(&mut scalar,2,0);
    for i in [4,5,6,7,10,12,13,14,15] { put(&mut scalar,i,0); }
    assert!(decode_failure_scalar_v1(&scalar).is_ok());
    for i in [4,5,6,7,10,12,13,14,15] { for byte in 0..8 { for bit in 0..8 {
        let mut bad=scalar; bad[i*8+byte]=1<<bit; assert!(decode_failure_scalar_v1(&bad).is_err());
    }}}
    for i in 223..256 { for bit in 0..8 { let mut bad=scalar; bad[i]=1<<bit; assert!(decode_failure_scalar_v1(&bad).is_err()); }}
    for bit in 6..64 { let mut bad=scalar; put(&mut bad,2,1u64<<bit); assert!(decode_failure_scalar_v1(&bad).is_err()); }
    let mut u=usage_oracle(HIGH); put(&mut u,50,0); u[408..].fill(0); assert!(decode_usage_v1(&u).is_ok());
    for i in 408..512 { for bit in 0..8 { let mut bad=u; bad[i]=1<<bit; assert!(decode_usage_v1(&bad).is_err()); }}
}

#[test]
fn every_code_octet_at_every_position_obeys_printable_range() {
    for i in 0..128 { for byte in 0..=255u8 {
        let mut s=scalar_oracle(); put(&mut s,3,128); s[128..].fill(b'x'); s[128+i]=byte;
        let d=decode_failure_scalar_v1(&s);
        assert_eq!(d.is_ok(),(32..=126).contains(&byte),"position {i} byte {byte}");
        if let Ok(d)=d { assert_eq!(d.code().as_bytes(),&s[128..]); assert_eq!(d.code().as_ptr(),s[128..].as_ptr()); }
    }}
    for len in (0..=256u64).chain([u64::MAX]) {
        let mut s=scalar_oracle(); put(&mut s,3,len); s[128..].fill(0);
        if len<=128 { s[128..128+len as usize].fill(b'~'); }
        assert_eq!(decode_failure_scalar_v1(&s).is_ok(),(1..=128).contains(&len));
    }
}

#[test]
fn required_digest_each_octet_remains_opaque_with_empty_raw_reference() {
    let z=[0;32]; let mut wire=[0;2048];
    encode_result_v1(ResultObservationV1{failure:None,final_consuming:None,references:references(&z)},&mut wire).unwrap();
    for start in [64,128,160,192] { for pos in 0..32 { for byte in 0..=255u8 {
        let mut varied=wire; varied[start+pos]=byte;
        let d=decode_result_v1(&varied).unwrap(); assert_eq!(d.references().raw_original_bytes,0);
        assert_eq!(&d.encoded()[start..start+32],&varied[start..start+32]);
        assert_eq!(d.references().raw_original_digest.as_ptr(),varied[64..].as_ptr());
        assert_eq!(d.references().session_digest.as_ptr(),varied[128..].as_ptr());
        assert_eq!(d.references().typed_result_schema_digest.as_ptr(),varied[160..].as_ptr());
        assert_eq!(d.references().writer_digest.as_ptr(),varied[192..].as_ptr());
    }}}
    for tag in 1..=8 { for len in [1,65536] { for byte in 0..=255u8 {
        let digest=std::array::from_fn(|i| byte.wrapping_add(i as u8)); let mut refs=references(&z);
        refs.constructor_tag=tag; refs.constructor_bytes=len; refs.constructor_digest=&digest; refs.raw_original_bytes=u64::MAX;
        let mut encoded=[0xa5;2048]; encode_result_v1(ResultObservationV1{failure:None,final_consuming:None,references:refs},&mut encoded).unwrap();
        assert_eq!(decode_result_v1(&encoded).unwrap().references(),&refs);
    }}}
}

#[test]
fn extent_precedes_bad_content_and_all_writes_stay_inside_caller_slice() {
    let z=[0;32]; let mut f=original(); f.code=""; let mut refs=references(&z); refs.constructor_tag=9;
    for n in 0..=2049 {
        let mut backing=[0xa5;2065]; let old=backing;
        let result=encode_result_v1(ResultObservationV1{failure:Some(&f),final_consuming:None,references:refs},&mut backing[8..8+n]);
        if n!=2048 { assert_eq!(result,Err(CodecRefusalV1::Extent)); } else { assert!(result.is_err()); }
        assert_eq!(backing,old);
        let result=encode_failure_scalar_v1(&f,&mut backing[8..8+n]);
        if n!=256 { assert_eq!(result,Err(CodecRefusalV1::Extent)); } else { assert!(result.is_err()); }
        assert_eq!(backing,old);
    }
    let f=original(); let u=observation(HIGH+2000);
    let mut b=[0xa5;2064]; encode_result_v1(ResultObservationV1{failure:Some(&f),final_consuming:Some(&u),references:references(&z)},&mut b[8..2056]).unwrap();
    assert_eq!(&b[..8],&[0xa5;8]); assert_eq!(&b[2056..],&[0xa5;8]); assert!(decode_result_v1(&b[8..2056]).is_ok());
    let mut b=[0xa5;272]; encode_failure_scalar_v1(&f,&mut b[8..264]).unwrap(); assert_eq!(&b[..8],&[0xa5;8]); assert_eq!(&b[264..],&[0xa5;8]); assert_eq!(&b[8..264],&scalar_oracle());
    let mut b=[0xa5;528]; encode_usage_v1(&u,&mut b[8..520]).unwrap(); assert_eq!(&b[..8],&[0xa5;8]); assert_eq!(&b[520..],&[0xa5;8]); assert_eq!(&b[8..520],&usage_oracle(HIGH+2000));
}

#[test]
fn every_upper_u32_bit_refuses_and_presence_zero_is_retained() {
    for word in [4,14] { for bit in 32..64 { let mut s=scalar_oracle(); put(&mut s,word,1u64<<bit); assert!(decode_failure_scalar_v1(&s).is_err()); }}
    let mut s=scalar_oracle(); for i in [4,5,10,14] { put(&mut s,i,0); }
    let d=decode_failure_scalar_v1(&s).unwrap(); assert_eq!((d.function,d.offset,d.observed_capacity,d.guest_exit),(Some(0),Some(0),Some(0),Some(0)));
    for (word,allowed) in [(0,6),(1,21),(11,2)] { for value in [0,allowed+1,u64::MAX] { let mut s=scalar_oracle(); put(&mut s,word,value); assert!(decode_failure_scalar_v1(&s).is_err()); }}
}

#[test]
fn actual_named_stage_kind_resource_and_wasi_discriminants_match_selected_wire() {
    let stages=[SwiftRunStage::Adoption,SwiftRunStage::Cache,SwiftRunStage::Initialization,SwiftRunStage::Invocation,SwiftRunStage::Wasi,SwiftRunStage::Cleanup];
    let kinds=[SwiftRunFailureKind::InvalidBudget,SwiftRunFailureKind::Cancelled,SwiftRunFailureKind::Deadline,SwiftRunFailureKind::Allocation,SwiftRunFailureKind::Adoption,
        SwiftRunFailureKind::CategoryExhausted,SwiftRunFailureKind::CombinedExhausted,SwiftRunFailureKind::ResourceExhausted,SwiftRunFailureKind::FuelExhausted,
        SwiftRunFailureKind::WorkExhausted,SwiftRunFailureKind::HostCallLimit,SwiftRunFailureKind::PinLimit,SwiftRunFailureKind::FrameLimit,SwiftRunFailureKind::ValueLimit,
        SwiftRunFailureKind::ControlLimit,SwiftRunFailureKind::DecoderMismatch,SwiftRunFailureKind::UnsupportedEnvironment,SwiftRunFailureKind::GuestTrap,
        SwiftRunFailureKind::GuestExit,SwiftRunFailureKind::Wasi,SwiftRunFailureKind::Invariant];
    for (i,value) in stages.into_iter().enumerate() { let mut f=original();f.stage=value;let mut s=[0;256];encode_failure_scalar_v1(&f,&mut s).unwrap();assert_eq!(get(&s,0),i as u64+1);assert_eq!(decode_failure_scalar_v1(&s).unwrap().stage,value); }
    for (i,value) in kinds.into_iter().enumerate() { let mut f=original();f.kind=value;let mut s=[0;256];encode_failure_scalar_v1(&f,&mut s).unwrap();assert_eq!(get(&s,1),i as u64+1);assert_eq!(decode_failure_scalar_v1(&s).unwrap().kind,value); }
    let categories=[SwiftReservationCategory::RetainedSource,SwiftReservationCategory::RetainedMetadata,SwiftReservationCategory::Cache,SwiftReservationCategory::State,SwiftReservationCategory::Wasi,SwiftReservationCategory::Shared,SwiftReservationCategory::Construction];
    for (i,value) in categories.into_iter().enumerate() { let mut f=original();f.resource=Some(SwiftRunResource::Reservation(value));let mut s=[0;256];encode_failure_scalar_v1(&f,&mut s).unwrap();assert_eq!((get(&s,6),get(&s,7)),(1,i as u64+1));assert_eq!(decode_failure_scalar_v1(&s).unwrap().resource,f.resource); }
    let resources=[SwiftRunResource::Combined,SwiftRunResource::CacheEntryBytes,SwiftRunResource::CacheEntries,SwiftRunResource::ActivePins,SwiftRunResource::Frames,SwiftRunResource::Values,SwiftRunResource::Controls,SwiftRunResource::MemoryPages,SwiftRunResource::CacheWork,SwiftRunResource::ExecutionWork,SwiftRunResource::InstructionFuel,SwiftRunResource::HostCalls,SwiftRunResource::Deadline,SwiftRunResource::TicketInventory,SwiftRunResource::OwnerIdentity,SwiftRunResource::ExactCapacity];
    for (i,value) in resources.into_iter().enumerate() { let mut f=original();f.resource=Some(value);let mut s=[0;256];encode_failure_scalar_v1(&f,&mut s).unwrap();assert_eq!((get(&s,6),get(&s,7)),(i as u64+2,0));assert_eq!(decode_failure_scalar_v1(&s).unwrap().resource,f.resource); }
    let wasi=[WasiFailure::InvalidBudget,WasiFailure::Allocation,WasiFailure::InvalidArguments,WasiFailure::InvalidMemory,WasiFailure::Budget(Resource::Calls),WasiFailure::Cancelled,WasiFailure::Deadline,WasiFailure::Invariant];
    for (i,value) in wasi.into_iter().enumerate() { let mut f=original();f.wasi_failure=Some(value);let mut s=[0;256];encode_failure_scalar_v1(&f,&mut s).unwrap();assert_eq!(get(&s,12),i as u64+1);assert_eq!(get(&s,13),if i==4{1}else{0});assert_eq!(decode_failure_scalar_v1(&s).unwrap().wasi_failure,f.wasi_failure); }
    for (i,value) in [Resource::Calls,Resource::Transfer,Resource::TransferSize,Resource::Work,Resource::Iovecs].into_iter().enumerate() { let mut f=original();f.wasi_failure=Some(WasiFailure::Budget(value));let mut s=[0;256];encode_failure_scalar_v1(&f,&mut s).unwrap();assert_eq!((get(&s,12),get(&s,13)),(5,i as u64+1)); }
}
