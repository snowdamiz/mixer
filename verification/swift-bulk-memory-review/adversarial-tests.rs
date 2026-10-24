// Independent review-only tests appended to the original fixture module.
#[test]
fn review01_copy_byte_oracle_and_owner_identity() {
    let _b = Bounds::new();
    for (src, dst) in [(5usize,6usize),(6,5),(17,17)] {
        for len in [0usize,1,4095,4096,4097,8193] {
            fixture(true,None,|p| {
                seed(p);
                let before_bytes=p.phase.parts.memory[..4*CHUNK].to_vec();
                let mut expected=before_bytes.clone();
                for i in 0..len { expected[dst+i]=before_bytes[src+i]; }
                push(p,&[Value::I32(dst as i32),Value::I32(src as i32),Value::I32(len as i32)]);
                let before=observed(p);
                let ptr=p.phase.parts.memory.as_ptr();let cap=p.phase.parts.memory.capacity();let pins=pin_ids(p);
                let (result,stats)=measure_extended(Some(0),||op(p,COPY));
                assert_eq!(stats.attempts,0);result.unwrap();
                assert_eq!(&p.phase.parts.memory[..4*CHUNK],expected.as_slice());
                assert_eq!(p.phase.parts.memory.as_ptr(),ptr);assert_eq!(p.phase.parts.memory.capacity(),cap);
                assert_eq!(pin_ids(p),pins);assert_eq!(observed(p).reservations,before.reservations);
                assert_eq!(observed(p).instruction_fuel-before.instruction_fuel,len.div_ceil(64)as u64);
                assert_eq!(observed(p).execution_work-before.execution_work,3+len as u64);
            });
        }
    }
}
#[test]
fn review02_actual_pinned_zero_and_size_denial_no_alloc() {
    let _b=Bounds::new();
    for (operation,body)in[(COPY,BODY),(FILL,&[0x41,0,0x41,3,0x41,8,0xfc,11,0,0x0b][..])] {
        fixture(true,Some(body),|p| {
            let end=p.phase.parts.memory.len()as i32;
            push(p,&[Value::I32(end),Value::I32(if matches!(operation,Operation::MemoryCopy){end}else{i32::MIN}),Value::I32(0)]);
            p.phase.parts.frames[0].pc=3;
            let before=observed(p);let pins=pin_ids(p);let ptr=p.phase.parts.memory.as_ptr();let cap=p.phase.parts.memory.capacity();let mut s=storage();
            let (outer,stats)=measure_extended(Some(0),||pinned(p,&mut s));
            outer.unwrap();assert_eq!(stats.attempts,0);assert_eq!(s.entry.take(),Some(Ok(())));
            assert_eq!(observed(p).instruction_fuel-before.instruction_fuel,1);assert_eq!(observed(p).instructions-before.instructions,1);
            assert_eq!(observed(p).execution_work-before.execution_work,4);assert_eq!(p.phase.parts.frames[0].pc,4);
            assert_eq!(p.phase.parts.memory.as_ptr(),ptr);assert_eq!(p.phase.parts.memory.capacity(),cap);assert_eq!(pin_ids(p),pins);assert_eq!(observed(p).reservations,before.reservations);
            assert_eq!(CHECKS.with(Cell::get),0);assert!(p.phase.parts.values.is_empty());
        });
    }
    fixture(true,Some(&[0x3f,0,0x1a,0x0b]),|p| {
        let before=observed(p);let old=p.phase.operation.control.test_replace_execution_work_limit(before.execution_work+1);let mut s=storage();
        let (outer,stats)=measure_extended(Some(0),||pinned(p,&mut s));outer.unwrap();assert_eq!(stats.attempts,0);
        let stored=s.entry.unwrap().unwrap_err();assert_eq!(stored.kind,SwiftRunFailureKind::WorkExhausted);
        assert_eq!(observed(p).instructions-before.instructions,1);assert_eq!(observed(p).instruction_fuel-before.instruction_fuel,1);
        assert_eq!(observed(p).execution_work-before.execution_work,1);assert_eq!(p.phase.parts.frames[0].pc,1);assert!(p.phase.parts.values.is_empty());
        assert!(matches!(p.lifecycle,Lifecycle::Terminal));assert!(matches!(p.cleanup.disposition,FrameDisposition::Draining));
        p.phase.operation.control.test_replace_execution_work_limit(old);
    });
}
#[test]
fn review03_end_aligned_chunk_cancellation_byte_oracle() {
    let _b=Bounds::new();
    for operation in[COPY,FILL] {
        for allowed in 0usize..=3 {
            fixture(true,None,|p| {
                let end=p.phase.parts.memory.len();let start=end-4*CHUNK;
                for(i,b)in p.phase.parts.memory[start..].iter_mut().enumerate(){*b=(i.wrapping_mul(19)^i/127)as u8;}
                let len=2*CHUNK+9;let dst=end-len;let src=dst-1;
                let old=p.phase.parts.memory[start..].to_vec();let mut expected=old.clone();
                if matches!(operation,Operation::MemoryCopy) {
                    let complete=len.min(allowed*CHUNK);
                    for i in len-complete..len {expected[dst-start+i]=old[src-start+i];}
                }else {
                    for i in 0..len.min(allowed*CHUNK) {expected[dst-start+i]=0xa5;}
                }
                push(p,&[Value::I32(dst as i32),Value::I32(if matches!(operation,Operation::MemoryCopy){src as i32}else{0x7fa5}),Value::I32(len as i32)]);
                CHECK_CANCEL.with(|v|v.set(Some(allowed)));let before=observed(p);let result=op(p,operation);
                assert_eq!(result.is_ok(),allowed==3);if let Err(f)=result {assert_eq!(f.kind,SwiftRunFailureKind::Cancelled);}
                assert_eq!(&p.phase.parts.memory[start..],expected.as_slice());
                assert_eq!(observed(p).execution_work-before.execution_work,3+len as u64);assert_eq!(observed(p).instruction_fuel-before.instruction_fuel,len.div_ceil(64)as u64);
                assert_eq!(CHECKS.with(Cell::get),allowed.min(2)+1);assert!(p.phase.parts.values.is_empty());
            });
        }
    }
}
