// Const-only conditional additive recipe; no runtime admission or arrays.
pub const BASE_C:u64=77144;
pub const BASE_S:u64=941467;
pub const BASE_A:u64=430175;
pub const BASE_H:u64=81327;
pub const OLD_REFUSAL:u64=1096;
pub const WRAPPER_FORWARD:u64=8;
pub const HELPER_ALL_PLACES:u64=0u64
 // delta::checked_snapshot_emission_bound_v1::_0
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_1
 .checked_add(8).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_2
 .checked_add(8).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_3
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_4
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_5
 .checked_add(16).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_6
 .checked_add(8).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_7
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_8
 .checked_add(8).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_9
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_10
 .checked_add(0).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_11
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_12
 .checked_add(8).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_13
 .checked_add(8).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_14
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_15
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_16
 .checked_add(16).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_17
 .checked_add(8).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_18
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_19
 .checked_add(8).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_20
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_21
 .checked_add(0).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_22
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_23
 .checked_add(8).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_24
 .checked_add(8).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_25
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_26
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_27
 .checked_add(16).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_28
 .checked_add(8).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_29
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_30
 .checked_add(8).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_31
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_32
 .checked_add(0).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_33
 .checked_add(1096).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_34
 .checked_add(8).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_35
 .checked_add(16).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_36
 .checked_add(8).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_37
 .checked_add(8).expect("helper source occurrence sum")
 // delta::checked_snapshot_emission_bound_v1::_38
 .checked_add(1096).expect("helper source occurrence sum")
;
pub const HELPER_PLUS_FORWARD:u64=HELPER_ALL_PLACES.checked_add(WRAPPER_FORWARD).expect("helper and wrapper");
pub const BASE_S_LESS_REFUSAL:u64=BASE_S.checked_sub(OLD_REFUSAL).expect("baseline identity subtraction");
pub const CANDIDATE_S:u64=BASE_S_LESS_REFUSAL.checked_add(HELPER_PLUS_FORWARD).expect("S addition");
pub const NET_DELTA:u64=HELPER_PLUS_FORWARD.checked_sub(OLD_REFUSAL).expect("positive delta");
pub const SELECTED_FROM_LEGACY:u64=BASE_C.checked_add(CANDIDATE_S).expect("selected sum");
pub const PHASE_FROM_LEGACY:u64=SELECTED_FROM_LEGACY.checked_add(BASE_A).expect("phase sum");
pub const HOST_PHASE_FROM_LEGACY:u64=PHASE_FROM_LEGACY.checked_add(BASE_H).expect("host sum");
const _:()=assert!(HELPER_ALL_PLACES==18816 && NET_DELTA==17728 && CANDIDATE_S==959195);
