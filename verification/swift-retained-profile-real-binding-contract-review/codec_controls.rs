// Independent data-only controls, appended to the frozen proposal by run_review.py.
// This reference envelope checker is a test oracle, never product admission.
#[cfg(test)]
mod independent_envelope_controls {
    use super::*;

    fn usage(marker: u64) -> SwiftRunUsage {
        SwiftRunUsage {
            reservations: SwiftReservations::default(), live: SwiftLiveUsage::default(),
            cache_work: marker, execution_work: marker + 1, instruction_fuel: marker + 2,
            instructions: marker + 3, host_calls: marker + 4, cleanup_invariant: None,
            elapsed_micros: marker + 5, deadline_ms: marker + 6,
            deadline_origin: SwiftDeadlineOrigin::Run, deadline_overshoot_micros: marker + 7,
            validation: SwiftValidationUsage::default(), wasi: None,
        }
    }
    fn failure() -> SwiftRunFailure {
        SwiftRunFailure {
            stage: SwiftRunStage::Cleanup, kind: SwiftRunFailureKind::Invariant,
            code: "unregistered_data_observation", function: Some(0), offset: Some(usize::MAX),
            resource: Some(SwiftRunResource::Reservation(SwiftReservationCategory::Construction)),
            attempted: u64::MAX, limit: 0, observed_capacity: Some(0),
            deadline_origin: SwiftDeadlineOrigin::Wasi,
            wasi_failure: Some(WasiFailure::Budget(Resource::Iovecs)), guest_exit: Some(u32::MAX),
            at_failure: usage(41), after_cleanup: Some(usage(73)),
        }
    }
    fn set_word(raw: &mut [u8], index: usize, value: u64) {
        raw[index * 8..index * 8 + 8].copy_from_slice(&value.to_le_bytes());
    }
    fn record(mask: u64, constructor: u64) -> [u8; 2048] {
        let mut r = [0; 2048]; r[..8].copy_from_slice(b"MIXRES01");
        for (i, value) in [(1,1),(2,2048),(3,1),(4,mask),(5,constructor),(6,17)] {
            set_word(&mut r, i, value);
        }
        // Required reference slots are byte observations, with no authority claim.
        r[64..96].fill(11); r[128..160].fill(13);
        r[160..192].fill(17); r[192..224].fill(19);
        if constructor != 0 { set_word(&mut r,7,65536); r[96..128].fill(23); }
        let f = failure();
        if mask & 1 != 0 {
            r[256..512].copy_from_slice(&encode_failure_meta(&f).unwrap());
            r[512..1024].copy_from_slice(&encode_usage(&f.at_failure).unwrap());
        }
        if mask & 2 != 0 { r[1024..1536].copy_from_slice(&encode_usage(&f.after_cleanup.unwrap()).unwrap()); }
        if mask & 4 != 0 { r[1536..2048].copy_from_slice(&encode_usage(&usage(109)).unwrap()); }
        r
    }
    fn check(raw: &[u8]) -> Result<(), Refusal> {
        if raw.len()!=2048 || &raw[..8]!=b"MIXRES01" { return Err("result extent/magic"); }
        let w=words::<32>(&raw[..256]);
        if (w[1],w[2],w[3])!=(1,2048,1) || w[28..].iter().any(|n|*n!=0) { return Err("result header"); }
        let mask=w[4];
        if mask>7 || mask&2!=0 && mask&1==0 { return Err("result presence"); }
        match w[5] {
            0 if w[7]==0 && raw[96..128].iter().all(|b|*b==0) => (),
            1..=8 if (1..=65536).contains(&w[7]) => (),
            _ => return Err("constructor reference"),
        }
        if mask&1!=0 {
            decode_failure_meta(raw[256..512].try_into().unwrap())?;
            decode_usage(raw[512..1024].try_into().unwrap())?;
        } else if raw[256..1024].iter().any(|b|*b!=0) { return Err("inactive failure"); }
        for (bit,start) in [(2,1024),(4,1536)] {
            if mask&bit!=0 { decode_usage(raw[start..start+512].try_into().unwrap())?; }
            else if raw[start..start+512].iter().any(|b|*b!=0) { return Err("inactive usage"); }
        }
        Ok(())
    }

    #[test]
    fn all_six_presence_masks_and_nine_constructor_states() {
        for mask in [0,1,3,4,5,7] { for tag in 0..=8 {
            assert!(check(&record(mask,tag)).is_ok(), "mask={mask} tag={tag}");
        }}
    }
    #[test]
    fn malformed_present_scalar_payloads_refuse_inside_envelope() {
        let good=record(7,8);
        for (i,value) in [(0,0),(0,7),(1,0),(1,22),(2,64),(3,0),(3,129),
            (4,u32::MAX as u64+1),(6,18),(7,8),(11,0),(12,9),(13,6),
            (14,u32::MAX as u64+1),(15,1)] {
            let mut r=good; set_word(&mut r[256..512],i,value);
            assert!(check(&r).is_err(), "scalar word {i}={value}");
        }
        for offset in [384,511] {
            let mut r=good; r[offset]=255; assert!(check(&r).is_err());
        }
        let mut r=good;
        let mask=words::<16>(&r[256..384])[2]&!1;
        set_word(&mut r[256..512],2,mask); set_word(&mut r[256..512],4,1);
        assert!(check(&r).is_err(),"hidden optional function");
    }
    #[test]
    fn every_present_usage_is_decoded_not_merely_sliced() {
        for start in [512,1024,1536] {
            for (i,value) in [(35,6),(38,0),(38,3),(50,2),(51,1)] {
                let mut r=record(7,8); set_word(&mut r[start..start+512],i,value);
                assert!(check(&r).is_err(),"snapshot {start} word {i}");
            }
        }
    }
    #[test]
    fn hidden_payloads_masks_extents_and_reserved_bytes_refuse() {
        for mask in [2,6,8,u64::MAX] {
            let mut r=record(0,0); set_word(&mut r,4,mask); assert!(check(&r).is_err());
        }
        for start in [256,512,1024,1536] {
            let mut r=record(0,0); r[start]=1; assert!(check(&r).is_err());
        }
        for offset in 224..256 {
            let mut r=record(7,8); r[offset]=1; assert!(check(&r).is_err());
        }
        let r=record(7,8);
        for n in [0,1,255,256,2047] { assert!(check(&r[..n]).is_err()); }
        assert!(check(&[0u8;2049]).is_err());
    }
    #[test]
    fn constructor_receipt_presence_and_exact_cap_refuse_malformed_joins() {
        for tag in 1..=8 {
            for len in [0,65537,u64::MAX] {
                let mut r=record(7,tag); set_word(&mut r,7,len); assert!(check(&r).is_err());
            }
            for len in [1,65536] {
                let mut r=record(7,tag); set_word(&mut r,7,len); assert!(check(&r).is_ok());
            }
        }
        let mut r=record(0,0); set_word(&mut r,7,1); assert!(check(&r).is_err());
        let mut r=record(0,0); r[96]=1; assert!(check(&r).is_err());
        let mut r=record(0,0); set_word(&mut r,5,9); assert!(check(&r).is_err());
    }
    #[test]
    fn final_observation_is_independent_and_all_fifteen_ledgers_survive() {
        let original=record(7,8);
        let final_start=1536;
        for (slot,wire_word) in [0,2,4,6,8,10,12,14,16,18,20,22,24,26,28].iter().enumerate() {
            let mut r=original; set_word(&mut r[final_start..],*wire_word,slot as u64+1);
            assert!(check(&r).is_ok());
            assert_eq!(&r[256..1536],&original[256..1536]);
            let final_u=decode_usage(r[1536..].try_into().unwrap()).unwrap();
            assert_eq!(ledger(&final_u)[slot],slot as u64+1);
        }
        let mut r=record(4,0);
        set_word(&mut r[1536..],12,331496); set_word(&mut r[1536..],14,331496);
        set_word(&mut r[1536..],16,1); set_word(&mut r[1536..],35,4);
        assert!(check(&r).is_ok());
        let final_u=decode_usage(r[1536..].try_into().unwrap()).unwrap();
        assert_eq!((final_u.reservations.construction.current,final_u.reservations.live_tickets),(331496,1));
        assert_eq!(final_u.cleanup_invariant,Some(SwiftCleanupInvariant::ConstructionBound));
    }
    #[test]
    fn unknown_code_and_anomalous_observations_are_data_without_semantic_admission() {
        let r=record(7,8); let f=decode_failure_meta(r[256..512].try_into().unwrap()).unwrap();
        assert_eq!(f.code,"unregistered_data_observation");
        assert_eq!(f.guest_exit,Some(u32::MAX));
        let mut u=usage(1); u.reservations.cache.current=99; u.reservations.cache.peak=1;
        assert_eq!(decode_usage(&encode_usage(&u).unwrap()).unwrap(),u);
    }
}
