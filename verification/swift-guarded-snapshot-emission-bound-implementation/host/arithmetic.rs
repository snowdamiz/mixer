#![allow(dead_code)]
// Exact source declarations/arithmetic are extracted and bound by prepare.py.
include!("source-types.rs");
use SnapshotAdmissionErrorV1 as AError;
#[path = "../overlay/vm/src/experimental_swift_reactor/cache/initial_profile_v1/emission_bound_v1.rs"]
mod emission_bound_v1;

#[cfg(test)]
mod tests {
    use super::*;
    use super::emission_bound_v1::checked_snapshot_emission_bound_v1 as bound;
    const CAPS: [usize;9] = [67108864,512,8192,34,79966,8192,4096,4096,4096];

    // Deliberately raw only for integer boundary tests. These literals grant
    // no runtime shape/owner authority and are not input to a VM or writer.
    fn raw(extent:u64,blocks:u64)->SnapshotShapeV1 {
        SnapshotShapeV1 {counts:[0;9],extent,blocks,records:0,words:0}
    }
    fn oracle(extent:u64,blocks:u64)->Result<u64,AError> {
        let independent = 14_224u128+1_217+4_096
            +u128::from(blocks)*(26+68*515+39*(9*515)+139*513+4096+4259+32*122)
            +32*u128::from(extent);
        u64::try_from(independent).map_err(|_|AError::Arithmetic)
    }
    fn source_shape(extent:u64)->SnapshotShapeV1 {
        let mut counts=[0;9];counts[0]=usize::try_from(extent-2560).unwrap();
        snapshot_shape_v1(counts).unwrap()
    }

    #[test]
    fn exact_floor_and_valid_minimum() {
        assert_eq!(bound(&raw(0,0)),Ok(19_537));
        let minimum=snapshot_shape_v1([0;9]).unwrap();
        assert_eq!((minimum.extent,minimum.blocks),(2560,1));
        assert_eq!(bound(&minimum),Ok(400_834));
    }
    #[test]
    fn every_cap_corner_matches_independent_u128() {
        for mask in 0..512usize {
            let counts=std::array::from_fn(|i|if mask&(1<<i)!=0 {CAPS[i]} else {0});
            let shape=snapshot_shape_v1(counts).unwrap();
            assert_eq!(bound(&shape),oracle(shape.extent,shape.blocks),"mask {mask}");
        }
    }
    #[test]
    fn every_single_cap_overrun_refuses_shape() {
        for i in 0..9 {
            let mut counts=[0;9];counts[i]=CAPS[i]+1;
            assert!(matches!(snapshot_shape_v1(counts),Err(AError::Layout)));
        }
    }
    #[test]
    fn maximum_geometry_exceeds_unchanged_original_budget() {
        let shape=snapshot_shape_v1(CAPS).unwrap();
        assert_eq!((shape.extent,shape.blocks),(69_765_152,17_033));
        let work=bound(&shape).unwrap();
        assert_eq!(work,7_331_792_842);
        assert!(work>1_000_000_000);
        // This arithmetic comparison is not an executed runtime debit.
    }
    #[test]
    fn geometry_residues_and_monotone_boundary_steps() {
        for block_base in [0u64,1,2,3,16,255] {
            for residue in 0..4096u64 {
                let extent=block_base*4096+residue;
                if extent<2560 {continue;}
                let shape=source_shape(extent);
                assert_eq!(shape.blocks,(extent+4095)/4096);
                assert_eq!(bound(&shape),oracle(extent,shape.blocks));
            }
        }
        let mut previous=bound(&source_shape(2560)).unwrap();
        for extent in 2561..=68_096u64 {
            let next=bound(&source_shape(extent)).unwrap();
            let expected_step=32+if (extent-1)%4096==0 {299_377} else {0};
            assert_eq!(next-previous,expected_step,"extent {extent}");
            previous=next;
        }
    }
    #[test]
    fn all_four_checked_operation_failure_edges() {
        let max=u64::MAX;
        assert_eq!(bound(&raw(0,max/299_377+1)),Err(AError::Arithmetic));
        assert_eq!(bound(&raw(max/32+1,0)),Err(AError::Arithmetic));
        assert_eq!(bound(&raw(max/32,0)),Err(AError::Arithmetic));
        let blocks=max/299_377;
        let product=u128::from(blocks)*299_377;
        let remaining=u128::from(max)-product-19_537;
        let extent=u64::try_from(remaining/32+1).unwrap();
        assert!(19_537+32*u128::from(extent)<=u128::from(max));
        assert_eq!(bound(&raw(extent,blocks)),Err(AError::Arithmetic));
        assert_eq!(bound(&raw(extent-1,blocks)),oracle(extent-1,blocks));
    }
    #[test]
    fn checked_boundary_grid_matches_u128_oracle() {
        let extents=[0,1,2560,69_765_152,u64::MAX/32-1,u64::MAX/32,u64::MAX/32+1,u64::MAX];
        let blocks=[0,1,17_033,u64::MAX/299_377-1,u64::MAX/299_377,u64::MAX/299_377+1,u64::MAX];
        for extent in extents {for count in blocks {
            assert_eq!(bound(&raw(extent,count)),oracle(extent,count),"E={extent} B={count}");
        }}
    }
    #[test]
    fn one_billion_boundary_refuses_without_budget_increase() {
        let mut low=2560u64;let mut high=67_108_864+2560;
        while low<high {
            let mid=low+(high-low+1)/2;
            if bound(&source_shape(mid)).unwrap()<=1_000_000_000 {low=mid;}else{high=mid-1;}
        }
        assert!(bound(&source_shape(low)).unwrap()<=1_000_000_000);
        assert!(bound(&source_shape(low+1)).unwrap()>1_000_000_000);
    }
    #[test]
    fn actual_helper_related_type_layouts_are_host_observations_only() {
        use std::mem::{size_of,align_of};
        println!("MIXER_EMISSION_HELPER_TYPE_LAYOUTS_V1={{\"u64\":[{},{}],\"shape_ref\":[{},{}],\"Option_u64\":[{},{}],\"AError\":[{},{}],\"Result_u64_AError\":[{},{}],\"SnapshotShapeV1\":[{},{}]}}",
            size_of::<u64>(),align_of::<u64>(),
            size_of::<&SnapshotShapeV1>(),align_of::<&SnapshotShapeV1>(),
            size_of::<Option<u64>>(),align_of::<Option<u64>>(),
            size_of::<AError>(),align_of::<AError>(),
            size_of::<Result<u64,AError>>(),align_of::<Result<u64,AError>>(),
            size_of::<SnapshotShapeV1>(),align_of::<SnapshotShapeV1>());
    }
}
