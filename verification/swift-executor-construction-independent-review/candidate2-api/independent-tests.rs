// Independent tests execute only in the derived snapshot. No public authority.
#[test]
fn independent_construction_review_signed_and_float_bit_matrix() {
    construction_hooks(ConstructionHooks::default());
    let mut owner = construct_owned(&mut construction_adopt(SwiftRunBudget::default())).unwrap();
    fn sleb(mut value: i64) -> Vec<u8> {
        let mut out = Vec::new();
        loop {
            let byte = (value as u8) & 127;
            value >>= 7;
            let done = (value == 0 && byte & 64 == 0) || (value == -1 && byte & 64 != 0);
            out.push(byte | if done { 0 } else { 128 });
            if done { return out; }
        }
    }
    let mut count = 0;
    for (ty, opcode, width) in [(Type::I32,0x41,32),(Type::I64,0x42,64)] {
        let mut values = vec![0, 1, -1, 63, 64, -64, -65, 127, 128, -127, -128];
        for bit in 1..width-1 { values.push(1i64 << bit); values.push(-(1i64 << bit)); }
        values.extend(if width==32 { [i32::MIN as i64,i32::MAX as i64] } else { [i64::MIN,i64::MAX] });
        for value in values {
            let encoded = sleb(value);
            for length in encoded.len()..=(width as usize).div_ceil(7) {
                let mut bytes = vec![opcode];
                bytes.extend_from_slice(&encoded);
                if length > encoded.len() {
                    *bytes.last_mut().unwrap() |= 128;
                    for _ in encoded.len()..length-1 { bytes.push(if value<0 { 255 } else { 128 }); }
                    bytes.push(if value<0 { 127 } else { 0 });
                }
                bytes.push(0x0b);
                let result = scalar_constant_probe(&bytes,1000,ty,owner.control.as_mut().unwrap(),owner.wasi.as_ref().unwrap()).unwrap();
                assert_eq!(result, if width==32 { Value::I32(value as i32) } else { Value::I64(value) });
                count += 1;
            }
        }
    }
    for bits in [0,0x80000000,0x7f800000,0xff800000,0x7fc01234,0x7f800001,u32::MAX] {
        let mut bytes=vec![0x43]; bytes.extend(bits.to_le_bytes()); bytes.push(0x0b);
        assert_eq!(scalar_constant_probe(&bytes,2000,Type::F32,owner.control.as_mut().unwrap(),owner.wasi.as_ref().unwrap()).unwrap(),Value::F32(bits));
        count += 1;
    }
    for bits in [0,0x8000000000000000,0x7ff0000000000000,0xfff0000000000000,0x7ff8000012345678,0x7ff0000000000001,u64::MAX] {
        let mut bytes=vec![0x44]; bytes.extend(bits.to_le_bytes()); bytes.push(0x0b);
        assert_eq!(scalar_constant_probe(&bytes,3000,Type::F64,owner.control.as_mut().unwrap(),owner.wasi.as_ref().unwrap()).unwrap(),Value::F64(bits));
        count += 1;
    }
    let usage=construction_finish(owner);
    assert_eq!(usage.instructions,0);
    println!("independent scalar accepted cases {count}");
}

#[test]
fn independent_construction_review_malformed_cursor_matrix() {
    let cases: Vec<(Vec<u8>,Type,&str,usize)> = vec![
        (vec![],Type::I32,"swift_execution_scalar_eof",0),
        (vec![0x41],Type::I32,"swift_execution_scalar_eof",1),
        (vec![0x42,0x80],Type::I64,"swift_execution_scalar_eof",2),
        (vec![0x41,0xff,0xff,0xff,0xff,0x07,0x0b],Type::I64,"swift_execution_scalar_type",0),
        (vec![0x41,0x80,0x80,0x80,0x80,0x80,0,0x0b],Type::I32,"swift_execution_scalar_signed",5),
        (vec![0x41,0xff,0xff,0xff,0xff,0x77,0x0b],Type::I32,"swift_execution_scalar_signed",5),
        (vec![0x42,0x80,0x80,0x80,0x80,0x80,0x80,0x80,0x80,0x80,0x01,0x0b],Type::I64,"swift_execution_scalar_signed",10),
        (vec![0x42,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0x7e,0x0b],Type::I64,"swift_execution_scalar_signed",10),
        (vec![0x43,0,0,0,0],Type::F32,"swift_execution_scalar_eof",5),
        (vec![0x44,0,0,0,0,0,0,0,0,0x0a],Type::F64,"swift_execution_scalar_end",9),
        (vec![0x41,0,0x0b,0xff],Type::I32,"swift_execution_scalar_trailing",3),
    ];
    for (bytes,ty,code,offset) in &cases {
        construction_hooks(ConstructionHooks::default());
        let mut owner=construct_owned(&mut construction_adopt(SwiftRunBudget::default())).unwrap();
        let (failure,stats)=measure(||scalar_constant_probe(bytes,8181,*ty,owner.control.as_mut().unwrap(),owner.wasi.as_ref().unwrap()).err().unwrap());
        assert_eq!((failure.code,failure.offset),(*code,Some(8181+offset)));
        assert_eq!(stats.allocations+stats.reallocations,0);
        construction_finish(owner);
    }
    println!("independent malformed cursor cases {}",cases.len());
}

#[test]
fn independent_construction_review_natural_deadline_after_take_drains_cache() {
    use std::time::Duration;
    construction_hooks(ConstructionHooks::default());
    let mut pair=construction_adopt(SwiftRunBudget::default());
    let started=Instant::now()-Duration::from_secs(31);
    let (failure,stats)=measure(|| { let mut retained_pair=pair; let result=SwiftReactorInstance::construct(&mut retained_pair,WasiGrants::default(),construction_wasi_budget(),started,construction_cursor()); assert!(retained_pair.is_none()); independent_complete_failed_construct(retained_pair,result) });
    assert_eq!(failure.kind,SwiftRunFailureKind::Deadline);
    let after=failure.after_cleanup.unwrap();
    assert_eq!(after.reservations.combined.current,0);
    assert_eq!(after.reservations.live_tickets,0);
    assert_eq!(stats.allocations,3); // Cache fixed arrays; WASI deadline rejects before buffer construction.
    assert_eq!(stats.deallocations,13); // Adopted/foundation backing plus cache payloads.
    println!("independent natural WASI deadline allocations {} deallocations {}",stats.allocations,stats.deallocations);
}

#[test]
fn independent_construction_review_foreign_adopted_pair_preserves_exact_slot() {
    construction_hooks(ConstructionHooks::default());
    let mut first=construction_adopt(SwiftRunBudget::default());
    let mut second=construction_adopt(SwiftRunBudget::default());
    let before=first.as_ref().unwrap().0.usage(None).reservations;
    let source_first=first.as_ref().unwrap().1.proof().source().as_ptr();
    let source_second=second.as_ref().unwrap().1.proof().source().as_ptr();
    std::mem::swap(&mut first.as_mut().unwrap().1,&mut second.as_mut().unwrap().1);
    let (failure,stats)=measure(||match construct_owned(&mut first){Err(ConstructionFailure::Rejected(failure))=>failure,_=>panic!("expected intact rejection")});
    assert_eq!(failure.code,"swift_run_reservation_owner");
    assert!(first.is_some());
    assert_eq!(first.as_ref().unwrap().1.proof().source().as_ptr(),source_second);
    assert_eq!(first.as_ref().unwrap().0.usage(None).reservations,before);
    assert_eq!(stats.allocations+stats.reallocations+stats.deallocations,0);
    std::mem::swap(&mut first.as_mut().unwrap().1,&mut second.as_mut().unwrap().1);
    assert_eq!(first.as_ref().unwrap().1.proof().source().as_ptr(),source_first);
    for pair in [first,second] { let (mut control,proof)=pair.unwrap(); control.drop_proof(proof).unwrap(); assert_eq!(control.finish_owned_cleanup(None).reservations.combined.current,0); }
}

#[test]
fn independent_construction_review_intact_foreign_cache_and_state_preflight() {
    for component in ["cache","state"] {
        construction_hooks(ConstructionHooks::default());
        let mut first=Some(construct_owned(&mut construction_adopt(SwiftRunBudget::default())).unwrap());
        let mut second=Some(construct_owned(&mut construction_adopt(SwiftRunBudget::default())).unwrap());
        match component {
            "cache"=>std::mem::swap(&mut first.as_mut().unwrap().cache,&mut second.as_mut().unwrap().cache),
            _=>std::mem::swap(&mut first.as_mut().unwrap().state,&mut second.as_mut().unwrap().state),
        }
        let before=first.as_ref().unwrap().control.as_ref().unwrap().usage(None).reservations;
        let (failure,stats)=measure(||SwiftReactorInstance::cleanup_owned(&mut first).err().unwrap());
        assert_eq!(failure.code,"swift_run_reservation_owner");
        assert!(first.is_some());
        assert_eq!(first.as_ref().unwrap().control.as_ref().unwrap().usage(None).reservations,before);
        assert_eq!(stats.allocations+stats.reallocations+stats.deallocations,0);
        match component {
            "cache"=>std::mem::swap(&mut first.as_mut().unwrap().cache,&mut second.as_mut().unwrap().cache),
            _=>std::mem::swap(&mut first.as_mut().unwrap().state,&mut second.as_mut().unwrap().state),
        }
        independent_finish_after_owner_rejection(first.take().unwrap()); construction_finish(second.take().unwrap());
    }
}

fn independent_finish_after_owner_rejection(owner:SwiftReactorInstance)->SwiftRunUsage {
    let mut owned=Some(owner);
    let mut returned=Some(SwiftReactorInstance::cleanup_owned(&mut owned));
    let tail=returned.take().unwrap().unwrap_or_else(|e|panic!("unexpected {}",e.code));
    let mut outcome=None;let mut usage=None;
    tail.complete((owned,returned),&mut outcome,&mut usage);
    let usage=usage.unwrap();
    assert_eq!(usage.reservations.combined.current,0);
    assert_eq!(usage.reservations.live_tickets,0);
    assert_eq!(usage.cleanup_invariant,Some(SwiftCleanupInvariant::ReservationOwner));
    usage
}

fn independent_uint(mut value:u32,out:&mut Vec<u8>){loop{let byte=(value&127)as u8;value>>=7;out.push(byte|if value!=0{128}else{0});if value==0{return;}}}
fn independent_section_replace(bytes:&[u8],wanted:u8,payload:&[u8])->Vec<u8>{
    fn uint_at(bytes:&[u8],at:&mut usize)->usize{let mut out=0;let mut shift=0;loop{let b=bytes[*at];*at+=1;out|=((b&127)as usize)<<shift;if b&128==0{return out;}shift+=7;}}
    let mut out=bytes[..8].to_vec();let mut at=8;let mut replaced=false;
    while at<bytes.len(){let start=at;let id=bytes[at];at+=1;let len=uint_at(bytes,&mut at);at+=len;if id==wanted{out.push(id);independent_uint(payload.len()as u32,&mut out);out.extend_from_slice(payload);replaced=true;}else{out.extend_from_slice(&bytes[start..at]);}}
    assert!(replaced);out
}
#[test]
fn independent_construction_review_invalid_ranges_fail_before_adoption() {
    for kind in ["data","element"] {
        construction_hooks(ConstructionHooks::default());
        let bytes=if kind=="data" {
            // First data payload is valid; later empty range is one past memory.
            let mut payload=vec![2,0,0x41,0,0x0b,3,b'a',b'b',b'c',0,0x41];
            independent_uint(584*65536+1,&mut payload);payload.extend([0x0b,0]);
            independent_section_replace(&construction_fixture(),11,&payload)
        }else{
            // Data would write successfully, but a table range is out of bounds.
            let mut payload=vec![1,0,0x41];independent_uint(46713,&mut payload);payload.extend([0x0b,1,34]);
            independent_section_replace(&construction_fixture(),9,&payload)
        };
        let failure=validate_swift_reactor(&bytes,SwiftValidationBudget::default(),&Cancellation::default()).err().expect("complete validator rejects impossible retained range");
        assert_eq!(failure.code,if kind=="data"{"swift_data_segment_fit"}else{"swift_element_segment_fit"});
        println!("independent validator {kind} rejection {} absolute offset {:?}",failure.code,failure.offset);
    }
}

fn independent_complete_failed_construct(pair:Option<(RuntimeControl,AdoptedProof)>,result:Result<SwiftReactorInstance,ConstructionFailure>)->SwiftRunFailure {
    let mut returned=Some(result);
    let tail=match returned.take().unwrap(){Err(ConstructionFailure::Cleanup(tail))=>tail,_=>panic!("post-take completion required")};
    let mut outcome=None;let mut usage=None;
    tail.complete((pair,returned),&mut outcome,&mut usage);
    let mut failure=outcome.expect("same control retained first failure");failure.after_cleanup=usage;failure
}
#[test]
fn independent_construction_review_failure_tail_retains_full_cause_and_large_storage() {
    for (budget,hook,header,code) in [
        (SwiftRunBudget{state_bytes:0,..SwiftRunBudget::default()},false,false,"swift_run_category_capacity"),
        (SwiftRunBudget{memory_pages:583,..SwiftRunBudget::default()},false,false,"swift_execution_memory_minimum"),
        (SwiftRunBudget{execution_work:0,..SwiftRunBudget::default()},false,false,"swift_run_work"),
        (SwiftRunBudget::default(),true,true,"swift_run_construction_phase_bound"),
    ] {
        construction_hooks(ConstructionHooks{bad_restore:hook,..ConstructionHooks::default()});
        let mut pair=construction_adopt(budget);let before_floor=pair.as_ref().unwrap().0.usage(None).reservations.construction.current;
        let mut returned=Some(construct_owned(&mut pair));
        assert!(pair.is_none());
        let mut tail=match returned.take().unwrap(){Err(ConstructionFailure::Cleanup(tail))=>tail,_=>panic!("completion authority required")};
        assert_eq!(tail.tail.header.is_some(),header);
        let live=tail.tail.control.usage(tail.tail.final_wasi);
        assert!(live.reservations.construction.current>before_floor);
        assert_eq!(live.reservations.cache.current+live.reservations.wasi.current+live.reservations.retained_source.current+live.reservations.retained_metadata.current,0);
        assert_eq!(live.live.memory_pages.current,0);
        let mut copied=tail.tail.failure.expect("tail has copied first failure");
        let mut latched=tail.tail.control.check_with_wasi(construction_cursor(),tail.tail.final_wasi).err().unwrap();
        assert_eq!(copied.code,code);
        copied.after_cleanup=None;latched.after_cleanup=None;assert_eq!(copied,latched);
        let mut outcome=None;let mut usage=None;
        let (_,stats)=measure(||tail.complete((pair,returned),&mut outcome,&mut usage));
        assert_eq!(stats.allocations+stats.reallocations,0);
        let mut after=outcome.unwrap();after.after_cleanup=None;assert_eq!(after,copied);
        let usage=usage.unwrap();
        if hook {assert!(usage.reservations.combined.current>0);assert_eq!(usage.reservations.live_tickets,1);}else{assert_eq!(usage.reservations.combined.current,0);assert_eq!(usage.reservations.live_tickets,0);}
        println!("independent completion retained same cause {code}, header={header}, rejected_restore={hook}");
    }
    construction_hooks(ConstructionHooks::default());
}
