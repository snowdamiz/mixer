#![allow(dead_code)]
include!("source-types.rs");
use SnapshotAdmissionErrorV1 as AError;
#[path = "../../swift-guarded-snapshot-emission-bound-implementation/overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs"]
mod candidate;

#[cfg(test)]
mod independent {
    use super::*;
    use candidate::checked_snapshot_emission_bound_v1 as candidate;
    const CAPS:[usize;9]=[67_108_864,512,8192,34,79_966,8192,4096,4096,4096];
    fn raw(e:u64,b:u64)->SnapshotShapeV1 {SnapshotShapeV1 {counts:[0;9],extent:e,blocks:b,records:0,words:0}}
    fn oracle(e:u64,b:u64)->Result<u64,AError> {
        let encoder_call=26u128+68*515+39*9*515+139*513+4096;
        let sum=14224u128+1217+4096+u128::from(b)*(encoder_call+4259+122*32)+u128::from(e)*32;
        sum.try_into().map_err(|_|AError::Arithmetic)
    }
    #[test]
    fn exact_components_and_geometry_endpoints() {
        assert_eq!(candidate(&raw(0,0)),Ok(14224+1217+4096));
        assert_eq!(candidate(&raw(0,1)),Ok(318914));
        let zero=snapshot_shape_v1([0;9]).unwrap();
        assert_eq!((zero.extent,zero.blocks),(2560,1));
        assert_eq!(candidate(&zero),Ok(400834));
        let cap=snapshot_shape_v1(CAPS).unwrap();
        assert_eq!((cap.extent,cap.blocks),(69765152,17033));
        assert_eq!(candidate(&cap),Ok(7331792842));
        assert!(candidate(&cap).unwrap()>1_000_000_000);
    }
    #[test]
    fn checked_order_edges_and_adjacent_successes() {
        let m=u64::MAX;
        let last_block=m/299377;
        assert_eq!(candidate(&raw(0,last_block)),oracle(0,last_block));
        assert_eq!(candidate(&raw(0,last_block+1)),Err(AError::Arithmetic));
        assert_eq!(candidate(&raw(m/32+1,0)),Err(AError::Arithmetic));
        let last_extent=(m-19537)/32;
        assert_eq!(candidate(&raw(last_extent,0)),oracle(last_extent,0));
        assert_eq!(candidate(&raw(last_extent+1,0)),Err(AError::Arithmetic));
        // Both products and the fixed+transfer partial result fit; final sum fails.
        let last_combined=(u128::from(m)-u128::from(last_block)*299377-19537)/32;
        let e=u64::try_from(last_combined).unwrap();
        assert_eq!(candidate(&raw(e,last_block)),oracle(e,last_block));
        assert_eq!(candidate(&raw(e+1,last_block)),Err(AError::Arithmetic));
        // All failure stages report the actual admission error variant.
        assert!(matches!(candidate(&raw(m,m)),Err(SnapshotAdmissionErrorV1::Arithmetic)));
    }
    #[test]
    fn independent_wide_integer_oracle_grid() {
        let es=[0,1,2559,2560,4095,4096,4097,69765152,(u64::MAX-19537)/32,u64::MAX/32,u64::MAX/32+1,u64::MAX];
        let bs=[0,1,2,17033,u64::MAX/299377-1,u64::MAX/299377,u64::MAX/299377+1,u64::MAX];
        for e in es {for b in bs {assert_eq!(candidate(&raw(e,b)),oracle(e,b),"E={e}, B={b}");}}
        let mut rng=0x533a_16c8_1c31_789du64;
        for i in 0..4096 {
            rng=rng.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let e=if i%2==0 {rng%(u64::MAX/64)}else{rng};
            rng=rng.rotate_left(17).wrapping_add(0x9e3779b97f4a7c15);
            let b=if i%3==0 {rng%(u64::MAX/600000)}else{rng};
            assert_eq!(candidate(&raw(e,b)),oracle(e,b),"case={i}, E={e}, B={b}");
        }
    }
    #[test]
    fn actual_geometry_mixed_counts_and_cap_refusals() {
        let mut rng=773u64;
        for _ in 0..2048 {
            let counts=std::array::from_fn(|i|{
                rng=rng.wrapping_mul(2862933555777941757).wrapping_add(3037000493);
                (rng%(CAPS[i] as u64+1)) as usize
            });
            let shape=snapshot_shape_v1(counts).unwrap();
            let expected_words=counts.iter().zip([0usize,3,1,5,3,4,4,4,4]).map(|(n,w)|n*w).sum::<usize>() as u64;
            assert_eq!(shape.extent,2560+counts[0] as u64+8*expected_words);
            assert_eq!(shape.blocks,(shape.extent+4095)/4096);
            assert_eq!(candidate(&shape),oracle(shape.extent,shape.blocks));
        }
        for i in 0..9 {let mut c=[0;9];c[i]=CAPS[i]+1;assert!(matches!(snapshot_shape_v1(c),Err(AError::Layout)));}
    }
    #[test]
    fn block_step_residues_and_original_budget_cutoff() {
        for block in [1u64,2,7,31,511,16383] {
            let mut previous=None;
            for e in block*4096-1..=block*4096+4097 {
                let mut c=[0;9];c[0]=(e-2560) as usize;
                let shape=snapshot_shape_v1(c).unwrap();
                let work=candidate(&shape).unwrap();
                assert_eq!(Some(work),oracle(e,(e+4095)/4096).ok());
                if let Some(old)=previous {assert_eq!(work-old,32+if (e-1)%4096==0 {299377}else{0});}
                previous=Some(work);
            }
        }
        let work=|e:u64|{let mut c=[0;9];c[0]=(e-2560) as usize;candidate(&snapshot_shape_v1(c).unwrap()).unwrap()};
        let(mut lo,mut hi)=(2560,67111424);
        while lo+1<hi {let mid=lo+(hi-lo)/2;if work(mid)<=1_000_000_000 {lo=mid;}else{hi=mid;}}
        assert!(work(lo)<=1_000_000_000 && work(hi)>1_000_000_000);
        println!("UNCHANGED_BUDGET_CUTOFF extent={lo} debit={} next_extent={hi} next_debit={}",work(lo),work(hi));
    }
    #[test]
    fn host_layout_observation_is_not_storage_selection() {
        use std::mem::{size_of,align_of};
        println!("HOST_LAYOUT AError={}/{} Result={}/{} Option={}/{} shape={}/{} reference={}/{}",
            size_of::<AError>(),align_of::<AError>(),size_of::<Result<u64,AError>>(),align_of::<Result<u64,AError>>(),
            size_of::<Option<u64>>(),align_of::<Option<u64>>(),size_of::<SnapshotShapeV1>(),align_of::<SnapshotShapeV1>(),
            size_of::<&SnapshotShapeV1>(),align_of::<&SnapshotShapeV1>());
        assert!(size_of::<AError>()>=size_of::<SwiftRunFailure>());
    }
}
