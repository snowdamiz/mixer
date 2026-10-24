// Independently authored supplemental logical whole-object inventory.
// Conservative sum of complete authored preflight call frames; no old slot is reclaimed.
#[allow(dead_code)]
struct PreflightSupplementConstructorPrelude {
    object_0: std::result::Result<crate::experimental_swift_reactor::execution::SwiftReactorInstance, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut Option<(super::control::RuntimeControl, super::control::AdoptedProof)>,
    object_2: WasiGrants,
    object_3: WasiBudget,
    object_4: Instant,
    object_5: super::control::Cursor,
    object_6: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_7: &'static mut crate::experimental_swift_reactor::control::AdoptedProof,
    object_8: &'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof),
    object_9: std::option::Option<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>,
    object_10: &'static str,
    object_11: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_12: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_13: &'static crate::experimental_swift_reactor::control::AdoptedProof,
    object_14: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_15: isize,
    object_16: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_17: usize,
    object_18: crate::experimental_swift_reactor::control::SwiftRunUsage,
    object_19: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    object_20: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_21: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    object_22: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_23: std::option::Option<usize>,
    object_24: std::option::Option<usize>,
    object_25: (&'static usize,),
    object_26: &'static usize,
    object_27: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor),
    object_28: &'static crate::experimental_swift_reactor::control::Cursor,
    object_29: isize,
    object_30: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_31: usize,
    object_32: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_33: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_34: isize,
    object_35: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
}
#[allow(dead_code)]
struct PreflightSupplementConstructorPreludeCallback0 {
    object_0: std::option::Option<usize>,
    object_1: (&'static usize,),
    object_2: usize,
    object_3: usize,
    object_4: &'static usize,
}
#[allow(dead_code)]
struct PreflightSupplementConstructorPreludeCallback1 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: crate::experimental_swift_reactor::control::Fault,
    object_4: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_5: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_6: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_7: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct PreflightSupplementStatePrepare {
    object_0: std::result::Result<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: &'static SwiftFunctionCache,
    object_3: &'static AccountedWasi,
    object_4: super::control::Cursor,
    object_5: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>,
    object_6: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_7: isize,
    object_8: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_9: crate::experimental_wasi::WasiUsage,
    object_10: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_11: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_12: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    object_13: isize,
    object_14: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_15: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_16: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_17: isize,
    object_18: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_19: bool,
    object_20: usize,
    object_21: crate::experimental_swift_reactor::cache::SwiftCacheUsage,
    object_22: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_23: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_24: usize,
    object_25: crate::experimental_swift_reactor::control::SwiftRunUsage,
    object_26: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    object_27: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_28: crate::experimental_wasi::WasiUsage,
    object_29: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    object_30: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_31: std::option::Option<usize>,
    object_32: std::option::Option<usize>,
    object_33: (&'static usize,),
    object_34: &'static usize,
    object_35: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_36: &'static crate::experimental_swift_reactor::control::Cursor,
    object_37: isize,
    object_38: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_39: usize,
    object_40: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_41: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_42: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_43: crate::experimental_wasi::WasiUsage,
    object_44: isize,
    object_45: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_46: crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>,
}
#[allow(dead_code)]
struct PreflightSupplementStatePrepareCallback0 {
    object_0: std::option::Option<usize>,
    object_1: (&'static usize,),
    object_2: usize,
    object_3: usize,
    object_4: &'static usize,
}
#[allow(dead_code)]
struct PreflightSupplementStatePrepareCallback1 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_4: &'static crate::experimental_wasi::accounted::AccountedWasi,
    object_5: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct PreflightSupplementConstructionBytes {
    object_0: std::option::Option<usize>,
}
#[allow(dead_code)]
struct PreflightSupplementChecked {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: &'static AccountedWasi,
    object_3: super::control::Cursor,
    object_4: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_5: crate::experimental_wasi::WasiUsage,
}
#[allow(dead_code)]
struct PreflightSupplementConstructionFailure {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: &'static AccountedWasi,
    object_3: super::control::Cursor,
    object_4: super::control::SwiftRunFailureKind,
    object_5: &'static str,
    object_6: crate::experimental_swift_reactor::control::Fault,
    object_7: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_8: crate::experimental_wasi::WasiUsage,
}
#[allow(dead_code)]
struct PreflightSupplementLayoutFailure {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: &'static AccountedWasi,
    object_3: super::control::Cursor,
    object_4: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
}
#[allow(dead_code)]
struct PreflightSupplementCacheOwner {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static SwiftFunctionCache,
    object_2: &'static mut super::control::RuntimeControl,
    object_3: Option<&'static AccountedWasi>,
    object_4: super::control::Cursor,
    object_5: &'static mut crate::experimental_swift_reactor::cache::CacheControl<'static>,
    object_6: crate::experimental_swift_reactor::cache::CacheControl<'static>,
}
#[allow(dead_code)]
struct PreflightSupplementCacheHeader {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut CacheControl<'static>,
    object_2: &'static SwiftFunctionCache,
    object_3: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::option::Option<crate::experimental_wasi::WasiUsage>>,
    object_4: std::result::Result<std::option::Option<crate::experimental_wasi::WasiUsage>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_5: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
    object_6: crate::experimental_swift_reactor::control::Cursor,
    object_7: isize,
    object_8: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_9: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_10: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_11: crate::experimental::cache::CacheFailureKind,
    object_12: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    object_13: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    object_14: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_15: isize,
    object_16: crate::experimental_swift_reactor::control::Cursor,
    object_17: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_18: &'static crate::experimental_swift_reactor::cache::CacheControl<'static>,
    object_19: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_20: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
}
#[allow(dead_code)]
struct PreflightSupplementCachePairing {
    object_0: std::result::Result<std::option::Option<crate::experimental_wasi::WasiUsage>, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: Option<&'static AccountedWasi>,
    object_3: super::control::Cursor,
    object_4: std::option::Option<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_5: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor),
    object_6: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct PreflightSupplementCachePairingCallback0 {
    object_0: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor),
    object_2: &'static AccountedWasi,
    object_3: crate::experimental_swift_reactor::control::Cursor,
    object_4: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_5: &'static crate::experimental_swift_reactor::control::Cursor,
}
#[allow(dead_code)]
struct PreflightSupplementCacheError {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: &'static mut CacheControl<'static>,
    object_2: crate::experimental::cache::CacheFailureKind,
    object_3: &'static str,
    object_4: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_5: isize,
    object_6: crate::experimental_swift_reactor::control::Cursor,
    object_7: crate::experimental_swift_reactor::control::Fault,
    object_8: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_9: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_10: &'static crate::experimental_swift_reactor::cache::CacheControl<'static>,
    object_11: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
}
#[allow(dead_code)]
struct PreflightSupplementCacheObservation {
    object_0: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_1: &'static CacheControl<'static>,
    object_2: std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>,
}
#[allow(dead_code)]
struct PreflightSupplementCacheUsage {
    object_0: crate::experimental_swift_reactor::cache::SwiftCacheUsage,
    object_1: &'static SwiftFunctionCache,
}
#[allow(dead_code)]
struct PreflightSupplementWasiCheckedUsage {
    object_0: std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static AccountedWasi,
    object_2: &'static mut super::control::RuntimeControl,
    object_3: super::control::Cursor,
    object_4: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_5: crate::experimental_swift_reactor::control::Fault,
    object_6: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_7: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_8: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    object_9: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    object_10: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_11: isize,
    object_12: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_13: bool,
    object_14: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    object_15: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    object_16: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_17: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_18: isize,
    object_19: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_20: crate::experimental_wasi::WasiUsage,
    object_21: &'static crate::experimental_wasi::WasiContext,
}
#[allow(dead_code)]
struct PreflightSupplementWasiCheckedUsageCallback0 {
    object_0: crate::experimental_wasi::WasiUsage,
    object_1: (&'static crate::experimental_wasi::accounted::AccountedWasi,),
    object_2: &'static crate::experimental_wasi::WasiContext,
    object_3: &'static crate::experimental_wasi::accounted::AccountedWasi,
}
#[allow(dead_code)]
struct PreflightSupplementWasiUsage {
    object_0: crate::experimental_wasi::WasiUsage,
    object_1: &'static AccountedWasi,
    object_2: &'static crate::experimental_wasi::WasiContext,
}
#[allow(dead_code)]
struct PreflightSupplementContextUsage {
    object_0: crate::experimental_wasi::WasiUsage,
    object_1: &'static crate::experimental_wasi::WasiContext,
}
#[allow(dead_code)]
struct PreflightSupplementAdoptedOwner {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: &'static super::control::AdoptedProof,
    object_3: super::control::Cursor,
    object_4: Option<WasiUsage>,
    object_5: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_6: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_7: &'static crate::experimental_swift_reactor::control::ReservationTicket,
    object_8: isize,
    object_9: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_10: &'static crate::experimental_swift_reactor::control::ReservationTicket,
}
#[allow(dead_code)]
struct PreflightSupplementReservationMatches {
    object_0: bool,
    object_1: &'static super::control::RuntimeControl,
    object_2: &'static super::control::ReservationTicket,
    object_3: bool,
    object_4: u64,
    object_5: u64,
    object_6: u64,
}
#[allow(dead_code)]
struct PreflightSupplementReservationOwner {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: &'static super::control::ReservationTicket,
    object_3: super::control::Cursor,
    object_4: Option<WasiUsage>,
    object_5: std::option::Option<(crate::experimental_swift_reactor::control::SwiftCleanupInvariant, &'static str)>,
    object_6: bool,
    object_7: u64,
    object_8: u64,
    object_9: bool,
    object_10: u64,
    object_11: (crate::experimental_swift_reactor::control::SwiftCleanupInvariant, &'static str),
    object_12: crate::experimental_swift_reactor::control::SwiftCleanupInvariant,
    object_13: bool,
    object_14: usize,
    object_15: bool,
    object_16: usize,
    object_17: &'static crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_18: &'static crate::experimental_swift_reactor::control::SwiftReservations,
    object_19: crate::experimental_swift_reactor::control::SwiftReservationCategory,
    object_20: usize,
    object_21: bool,
    object_22: usize,
    object_23: usize,
    object_24: (crate::experimental_swift_reactor::control::SwiftCleanupInvariant, &'static str),
    object_25: crate::experimental_swift_reactor::control::SwiftCleanupInvariant,
    object_26: isize,
    object_27: crate::experimental_swift_reactor::control::SwiftCleanupInvariant,
    object_28: &'static str,
    object_29: &'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant,
    object_30: &'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>,
    object_31: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_32: crate::experimental_swift_reactor::control::Fault,
    object_33: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
}
#[allow(dead_code)]
struct PreflightSupplementEnlargePlain {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: usize,
    object_3: super::control::Cursor,
    object_4: std::option::Option<crate::experimental_wasi::WasiUsage>,
}
#[allow(dead_code)]
struct PreflightSupplementEnlargeObserved {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: usize,
    object_3: super::control::Cursor,
    object_4: Option<WasiUsage>,
    object_5: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>,
    object_6: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_7: isize,
    object_8: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_9: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>,
    object_10: std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_11: std::option::Option<usize>,
    object_12: std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>,
    object_13: &'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
    object_14: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor,&'static std::option::Option<crate::experimental_wasi::WasiUsage>),
    object_15: &'static crate::experimental_swift_reactor::control::Cursor,
    object_16: &'static std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_17: isize,
    object_18: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_19: usize,
    object_20: bool,
    object_21: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_22: crate::experimental_swift_reactor::control::Fault,
    object_23: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_24: usize,
    object_25: usize,
    object_26: std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, (usize, usize)>,
    object_27: std::result::Result<(usize, usize), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_28: crate::experimental_swift_reactor::control::SwiftReservationCategory,
    object_29: usize,
    object_30: (usize, bool),
    object_31: isize,
    object_32: std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_33: (usize, usize),
    object_34: (),
    object_35: crate::experimental_swift_reactor::control::SwiftReservationCategory,
    object_36: &'static mut crate::experimental_swift_reactor::control::ReservationTicket,
    object_37: std::option::Option<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>,
    object_38: &'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>,
}
#[allow(dead_code)]
struct PreflightSupplementEnlargeObservedCallback0 {
    object_0: usize,
    object_1: (),
    object_2: &'static super::control::ReservationTicket,
}
#[allow(dead_code)]
struct PreflightSupplementEnlargeObservedCallback1 {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: (&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor,&'static std::option::Option<crate::experimental_wasi::WasiUsage>),
    object_2: crate::experimental_swift_reactor::control::Cursor,
    object_3: crate::experimental_swift_reactor::control::Fault,
    object_4: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_5: std::option::Option<crate::experimental_wasi::WasiUsage>,
    object_6: &'static mut crate::experimental_swift_reactor::control::RuntimeControl,
    object_7: &'static crate::experimental_swift_reactor::control::Cursor,
    object_8: &'static std::option::Option<crate::experimental_wasi::WasiUsage>,
}
#[allow(dead_code)]
struct PreflightSupplementControlCheck {
    object_0: std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: super::control::Cursor,
    object_3: Option<WasiUsage>,
    object_4: isize,
    object_5: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_6: bool,
    object_7: &'static crate::execute::Cancellation,
    object_8: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_9: crate::experimental_swift_reactor::control::Fault,
    object_10: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_11: bool,
    object_12: &'static std::time::Instant,
    object_13: std::time::Instant,
    object_14: &'static std::time::Instant,
    object_15: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_16: crate::experimental_swift_reactor::control::Fault,
    object_17: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
}
#[allow(dead_code)]
struct PreflightSupplementControlUsage {
    object_0: crate::experimental_swift_reactor::control::SwiftRunUsage,
    object_1: &'static super::control::RuntimeControl,
    object_2: Option<WasiUsage>,
    object_3: std::time::Instant,
    object_4: crate::experimental_swift_reactor::control::SwiftReservations,
    object_5: crate::experimental_swift_reactor::control::SwiftLiveUsage,
    object_6: u64,
    object_7: u64,
    object_8: u64,
    object_9: u64,
    object_10: u64,
    object_11: std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>,
    object_12: u64,
    object_13: std::time::Duration,
    object_14: &'static std::time::Instant,
    object_15: std::time::Instant,
    object_16: u64,
    object_17: crate::experimental_swift_reactor::control::SwiftDeadlineOrigin,
    object_18: u64,
    object_19: std::time::Duration,
    object_20: &'static std::time::Instant,
    object_21: std::time::Instant,
    object_22: crate::experimental::swift::SwiftValidationUsage,
}
#[allow(dead_code)]
struct PreflightSupplementControlFail {
    object_0: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: super::control::Cursor,
    object_3: super::control::Fault,
    object_4: Option<WasiUsage>,
    object_5: isize,
    object_6: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_7: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_8: crate::experimental_swift_reactor::control::SwiftRunStage,
    object_9: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_10: &'static str,
    object_11: std::option::Option<u32>,
    object_12: std::option::Option<usize>,
    object_13: std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>,
    object_14: u64,
    object_15: u64,
    object_16: std::option::Option<usize>,
    object_17: crate::experimental_swift_reactor::control::SwiftDeadlineOrigin,
    object_18: std::option::Option<crate::experimental_wasi::WasiFailure>,
    object_19: std::option::Option<u32>,
    object_20: crate::experimental_swift_reactor::control::SwiftRunUsage,
    object_21: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    object_22: std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>,
    object_23: std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>,
}
#[allow(dead_code)]
struct PreflightSupplementBytesPreflight {
    object_0: std::result::Result<(usize, usize), crate::experimental_swift_reactor::control::SwiftRunFailure>,
    object_1: &'static mut super::control::RuntimeControl,
    object_2: super::control::SwiftReservationCategory,
    object_3: usize,
    object_4: super::control::Cursor,
    object_5: Option<WasiUsage>,
    object_6: std::option::Option<usize>,
    object_7: usize,
    object_8: &'static crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_9: &'static crate::experimental_swift_reactor::control::SwiftReservations,
    object_10: usize,
    object_11: &'static crate::experimental_swift_reactor::control::RuntimeControl,
    object_12: bool,
    object_13: (&'static usize,),
    object_14: &'static usize,
    object_15: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_16: bool,
    object_17: isize,
    object_18: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_19: crate::experimental_swift_reactor::control::Fault,
    object_20: crate::experimental_swift_reactor::control::Fault,
    object_21: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_22: crate::experimental_swift_reactor::control::SwiftRunResource,
    object_23: u64,
    object_24: u64,
    object_25: std::option::Option<usize>,
    object_26: usize,
    object_27: bool,
    object_28: (&'static usize,),
    object_29: &'static usize,
    object_30: crate::experimental_swift_reactor::control::SwiftRunFailure,
    object_31: crate::experimental_swift_reactor::control::Fault,
    object_32: crate::experimental_swift_reactor::control::Fault,
    object_33: crate::experimental_swift_reactor::control::SwiftRunFailureKind,
    object_34: crate::experimental_swift_reactor::control::SwiftRunResource,
    object_35: u64,
    object_36: u64,
    object_37: usize,
    object_38: (usize, usize),
    object_39: usize,
    object_40: usize,
}
#[allow(dead_code)]
struct PreflightSupplementBytesPreflightCallback0 {
    object_0: bool,
    object_1: (&'static usize,),
    object_2: usize,
    object_3: usize,
    object_4: &'static usize,
}
#[allow(dead_code)]
struct PreflightSupplementBytesPreflightCallback1 {
    object_0: u64,
    object_1: (),
    object_2: usize,
}
#[allow(dead_code)]
struct PreflightSupplementBytesPreflightCallback2 {
    object_0: bool,
    object_1: (&'static usize,),
    object_2: usize,
    object_3: usize,
    object_4: &'static usize,
}
#[allow(dead_code)]
struct PreflightSupplementBytesPreflightCallback3 {
    object_0: u64,
    object_1: (),
    object_2: usize,
}
#[allow(dead_code)]
struct PreflightSupplementBytesCommit {
    object_0: (),
    object_1: &'static mut super::control::RuntimeControl,
    object_2: super::control::SwiftReservationCategory,
    object_3: usize,
    object_4: usize,
    object_5: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_6: &'static mut crate::experimental_swift_reactor::control::SwiftReservations,
    object_7: usize,
    object_8: usize,
    object_9: usize,
    object_10: usize,
}
#[allow(dead_code)]
struct PreflightSupplementCategoryLimit {
    object_0: usize,
    object_1: &'static super::control::RuntimeControl,
    object_2: super::control::SwiftReservationCategory,
    object_3: isize,
}
#[allow(dead_code)]
struct PreflightSupplementCategoryRef {
    object_0: &'static crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_1: &'static super::control::SwiftReservations,
    object_2: super::control::SwiftReservationCategory,
    object_3: &'static crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_4: isize,
    object_5: &'static crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_6: &'static crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_7: &'static crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_8: &'static crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_9: &'static crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_10: &'static crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_11: &'static crate::experimental_swift_reactor::control::SwiftReservationUsage,
}
#[allow(dead_code)]
struct PreflightSupplementCategoryMut {
    object_0: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_1: &'static mut super::control::SwiftReservations,
    object_2: super::control::SwiftReservationCategory,
    object_3: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_4: isize,
    object_5: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_6: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_7: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_8: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_9: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_10: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
    object_11: &'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage,
}
#[allow(dead_code)]
struct PreflightSupplementFaultNew {
    object_0: crate::experimental_swift_reactor::control::Fault,
    object_1: super::control::SwiftRunFailureKind,
    object_2: &'static str,
    object_3: std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>,
    object_4: std::option::Option<usize>,
    object_5: std::option::Option<crate::experimental_wasi::WasiFailure>,
    object_6: std::option::Option<u32>,
}
#[allow(dead_code)]
struct PreflightSupplementFaultLimit {
    object_0: crate::experimental_swift_reactor::control::Fault,
    object_1: super::control::Fault,
    object_2: super::control::SwiftRunResource,
    object_3: u64,
    object_4: u64,
    object_5: std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>,
}
#[allow(dead_code)]
struct PreflightSupplementMicros {
    object_0: u64,
    object_1: std::time::Duration,
    object_2: std::result::Result<u64, std::num::TryFromIntError>,
    object_3: u128,
    object_4: &'static std::time::Duration,
}
#[allow(dead_code)]
struct PreflightSupplementCancelled {
    object_0: bool,
    object_1: &'static crate::execute::Cancellation,
    object_2: &'static std::sync::atomic::AtomicBool,
    object_3: &'static std::sync::Arc<std::sync::atomic::AtomicBool>,
    object_4: std::sync::atomic::Ordering,
}
#[allow(dead_code)]
pub(super) struct ConstructionPreflightSupplement {
    constructor_prelude: PreflightSupplementConstructorPrelude,
    constructor_prelude_callback_0: PreflightSupplementConstructorPreludeCallback0,
    constructor_prelude_callback_1: PreflightSupplementConstructorPreludeCallback1,
    state_prepare: PreflightSupplementStatePrepare,
    state_prepare_callback_0: PreflightSupplementStatePrepareCallback0,
    state_prepare_callback_1: PreflightSupplementStatePrepareCallback1,
    construction_bytes: PreflightSupplementConstructionBytes,
    checked: PreflightSupplementChecked,
    construction_failure: PreflightSupplementConstructionFailure,
    layout_failure: PreflightSupplementLayoutFailure,
    cache_owner: PreflightSupplementCacheOwner,
    cache_header: PreflightSupplementCacheHeader,
    cache_pairing: PreflightSupplementCachePairing,
    cache_pairing_callback_0: PreflightSupplementCachePairingCallback0,
    cache_error: PreflightSupplementCacheError,
    cache_observation: PreflightSupplementCacheObservation,
    cache_usage: PreflightSupplementCacheUsage,
    wasi_checked_usage: PreflightSupplementWasiCheckedUsage,
    wasi_checked_usage_callback_0: PreflightSupplementWasiCheckedUsageCallback0,
    wasi_usage: PreflightSupplementWasiUsage,
    context_usage: PreflightSupplementContextUsage,
    adopted_owner: PreflightSupplementAdoptedOwner,
    reservation_matches: PreflightSupplementReservationMatches,
    reservation_owner: PreflightSupplementReservationOwner,
    enlarge_plain: PreflightSupplementEnlargePlain,
    enlarge_observed: PreflightSupplementEnlargeObserved,
    enlarge_observed_callback_0: PreflightSupplementEnlargeObservedCallback0,
    enlarge_observed_callback_1: PreflightSupplementEnlargeObservedCallback1,
    control_check: PreflightSupplementControlCheck,
    control_usage: PreflightSupplementControlUsage,
    control_fail: PreflightSupplementControlFail,
    bytes_preflight: PreflightSupplementBytesPreflight,
    bytes_preflight_callback_0: PreflightSupplementBytesPreflightCallback0,
    bytes_preflight_callback_1: PreflightSupplementBytesPreflightCallback1,
    bytes_preflight_callback_2: PreflightSupplementBytesPreflightCallback2,
    bytes_preflight_callback_3: PreflightSupplementBytesPreflightCallback3,
    bytes_commit: PreflightSupplementBytesCommit,
    category_limit: PreflightSupplementCategoryLimit,
    category_ref: PreflightSupplementCategoryRef,
    category_mut: PreflightSupplementCategoryMut,
    fault_new: PreflightSupplementFaultNew,
    fault_limit: PreflightSupplementFaultLimit,
    micros: PreflightSupplementMicros,
    cancelled: PreflightSupplementCancelled,
}
pub(super) const CONSTRUCTION_PREFLIGHT_SUPPLEMENT_BYTES: usize = std::mem::size_of::<ConstructionPreflightSupplement>();
pub(crate) fn independent_preflight_supplement_probe(){
 use std::mem::{size_of,align_of,offset_of};
println!("isupplement|constructor_prelude|{}|{}",size_of::<PreflightSupplementConstructorPrelude>(),align_of::<PreflightSupplementConstructorPrelude>());
println!("isupplementfield|constructor_prelude|object_0|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_0),size_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftReactorInstance, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::execution::SwiftReactorInstance, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|constructor_prelude|object_1|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_1),size_of::<&'static mut Option<(super::control::RuntimeControl, super::control::AdoptedProof)>>(),align_of::<&'static mut Option<(super::control::RuntimeControl, super::control::AdoptedProof)>>());
println!("isupplementfield|constructor_prelude|object_2|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_2),size_of::<WasiGrants>(),align_of::<WasiGrants>());
println!("isupplementfield|constructor_prelude|object_3|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_3),size_of::<WasiBudget>(),align_of::<WasiBudget>());
println!("isupplementfield|constructor_prelude|object_4|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_4),size_of::<Instant>(),align_of::<Instant>());
println!("isupplementfield|constructor_prelude|object_5|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_5),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("isupplementfield|constructor_prelude|object_6|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_6),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("isupplementfield|constructor_prelude|object_7|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_7),size_of::<&'static mut crate::experimental_swift_reactor::control::AdoptedProof>(),align_of::<&'static mut crate::experimental_swift_reactor::control::AdoptedProof>());
println!("isupplementfield|constructor_prelude|object_8|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_8),size_of::<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>(),align_of::<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>());
println!("isupplementfield|constructor_prelude|object_9|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_9),size_of::<std::option::Option<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>>(),align_of::<std::option::Option<&'static mut (crate::experimental_swift_reactor::control::RuntimeControl, crate::experimental_swift_reactor::control::AdoptedProof)>>());
println!("isupplementfield|constructor_prelude|object_10|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_10),size_of::<&'static str>(),align_of::<&'static str>());
println!("isupplementfield|constructor_prelude|object_11|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_11),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("isupplementfield|constructor_prelude|object_12|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_12),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|constructor_prelude|object_13|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_13),size_of::<&'static crate::experimental_swift_reactor::control::AdoptedProof>(),align_of::<&'static crate::experimental_swift_reactor::control::AdoptedProof>());
println!("isupplementfield|constructor_prelude|object_14|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_14),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|constructor_prelude|object_15|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_15),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|constructor_prelude|object_16|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_16),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|constructor_prelude|object_17|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_17),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|constructor_prelude|object_18|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_18),size_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>());
println!("isupplementfield|constructor_prelude|object_19|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_19),size_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>());
println!("isupplementfield|constructor_prelude|object_20|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_20),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|constructor_prelude|object_21|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_21),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>());
println!("isupplementfield|constructor_prelude|object_22|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_22),size_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|constructor_prelude|object_23|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_23),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("isupplementfield|constructor_prelude|object_24|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_24),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("isupplementfield|constructor_prelude|object_25|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_25),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("isupplementfield|constructor_prelude|object_26|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_26),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("isupplementfield|constructor_prelude|object_27|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_27),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("isupplementfield|constructor_prelude|object_28|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_28),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("isupplementfield|constructor_prelude|object_29|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_29),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|constructor_prelude|object_30|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_30),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|constructor_prelude|object_31|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_31),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|constructor_prelude|object_32|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_32),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("isupplementfield|constructor_prelude|object_33|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_33),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|constructor_prelude|object_34|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_34),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|constructor_prelude|object_35|{}|{}|{}",offset_of!(PreflightSupplementConstructorPrelude,object_35),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplement|constructor_prelude_callback_0|{}|{}",size_of::<PreflightSupplementConstructorPreludeCallback0>(),align_of::<PreflightSupplementConstructorPreludeCallback0>());
println!("isupplementfield|constructor_prelude_callback_0|object_0|{}|{}|{}",offset_of!(PreflightSupplementConstructorPreludeCallback0,object_0),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("isupplementfield|constructor_prelude_callback_0|object_1|{}|{}|{}",offset_of!(PreflightSupplementConstructorPreludeCallback0,object_1),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("isupplementfield|constructor_prelude_callback_0|object_2|{}|{}|{}",offset_of!(PreflightSupplementConstructorPreludeCallback0,object_2),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|constructor_prelude_callback_0|object_3|{}|{}|{}",offset_of!(PreflightSupplementConstructorPreludeCallback0,object_3),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|constructor_prelude_callback_0|object_4|{}|{}|{}",offset_of!(PreflightSupplementConstructorPreludeCallback0,object_4),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("isupplement|constructor_prelude_callback_1|{}|{}",size_of::<PreflightSupplementConstructorPreludeCallback1>(),align_of::<PreflightSupplementConstructorPreludeCallback1>());
println!("isupplementfield|constructor_prelude_callback_1|object_0|{}|{}|{}",offset_of!(PreflightSupplementConstructorPreludeCallback1,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|constructor_prelude_callback_1|object_1|{}|{}|{}",offset_of!(PreflightSupplementConstructorPreludeCallback1,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("isupplementfield|constructor_prelude_callback_1|object_2|{}|{}|{}",offset_of!(PreflightSupplementConstructorPreludeCallback1,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("isupplementfield|constructor_prelude_callback_1|object_3|{}|{}|{}",offset_of!(PreflightSupplementConstructorPreludeCallback1,object_3),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("isupplementfield|constructor_prelude_callback_1|object_4|{}|{}|{}",offset_of!(PreflightSupplementConstructorPreludeCallback1,object_4),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("isupplementfield|constructor_prelude_callback_1|object_5|{}|{}|{}",offset_of!(PreflightSupplementConstructorPreludeCallback1,object_5),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|constructor_prelude_callback_1|object_6|{}|{}|{}",offset_of!(PreflightSupplementConstructorPreludeCallback1,object_6),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("isupplementfield|constructor_prelude_callback_1|object_7|{}|{}|{}",offset_of!(PreflightSupplementConstructorPreludeCallback1,object_7),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("isupplement|state_prepare|{}|{}",size_of::<PreflightSupplementStatePrepare>(),align_of::<PreflightSupplementStatePrepare>());
println!("isupplementfield|state_prepare|object_0|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_0),size_of::<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|state_prepare|object_1|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("isupplementfield|state_prepare|object_2|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_2),size_of::<&'static SwiftFunctionCache>(),align_of::<&'static SwiftFunctionCache>());
println!("isupplementfield|state_prepare|object_3|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_3),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("isupplementfield|state_prepare|object_4|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_4),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("isupplementfield|state_prepare|object_5|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_5),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|state_prepare|object_6|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_6),size_of::<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|state_prepare|object_7|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_7),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|state_prepare|object_8|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_8),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|state_prepare|object_9|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_9),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("isupplementfield|state_prepare|object_10|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_10),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("isupplementfield|state_prepare|object_11|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_11),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|state_prepare|object_12|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_12),size_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>());
println!("isupplementfield|state_prepare|object_13|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_13),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|state_prepare|object_14|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_14),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|state_prepare|object_15|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_15),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("isupplementfield|state_prepare|object_16|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_16),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|state_prepare|object_17|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_17),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|state_prepare|object_18|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_18),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|state_prepare|object_19|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_19),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|state_prepare|object_20|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_20),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|state_prepare|object_21|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_21),size_of::<crate::experimental_swift_reactor::cache::SwiftCacheUsage>(),align_of::<crate::experimental_swift_reactor::cache::SwiftCacheUsage>());
println!("isupplementfield|state_prepare|object_22|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_22),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|state_prepare|object_23|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_23),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("isupplementfield|state_prepare|object_24|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_24),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|state_prepare|object_25|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_25),size_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>());
println!("isupplementfield|state_prepare|object_26|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_26),size_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>());
println!("isupplementfield|state_prepare|object_27|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_27),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|state_prepare|object_28|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_28),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("isupplementfield|state_prepare|object_29|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_29),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>());
println!("isupplementfield|state_prepare|object_30|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_30),size_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|state_prepare|object_31|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_31),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("isupplementfield|state_prepare|object_32|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_32),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("isupplementfield|state_prepare|object_33|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_33),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("isupplementfield|state_prepare|object_34|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_34),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("isupplementfield|state_prepare|object_35|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_35),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("isupplementfield|state_prepare|object_36|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_36),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("isupplementfield|state_prepare|object_37|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_37),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|state_prepare|object_38|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_38),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|state_prepare|object_39|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_39),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|state_prepare|object_40|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_40),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("isupplementfield|state_prepare|object_41|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_41),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|state_prepare|object_42|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_42),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|state_prepare|object_43|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_43),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("isupplementfield|state_prepare|object_44|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_44),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|state_prepare|object_45|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_45),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|state_prepare|object_46|{}|{}|{}",offset_of!(PreflightSupplementStatePrepare,object_46),size_of::<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>(),align_of::<crate::experimental_swift_reactor::execution::ExecutionConstructionPhase<'static>>());
println!("isupplement|state_prepare_callback_0|{}|{}",size_of::<PreflightSupplementStatePrepareCallback0>(),align_of::<PreflightSupplementStatePrepareCallback0>());
println!("isupplementfield|state_prepare_callback_0|object_0|{}|{}|{}",offset_of!(PreflightSupplementStatePrepareCallback0,object_0),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("isupplementfield|state_prepare_callback_0|object_1|{}|{}|{}",offset_of!(PreflightSupplementStatePrepareCallback0,object_1),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("isupplementfield|state_prepare_callback_0|object_2|{}|{}|{}",offset_of!(PreflightSupplementStatePrepareCallback0,object_2),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|state_prepare_callback_0|object_3|{}|{}|{}",offset_of!(PreflightSupplementStatePrepareCallback0,object_3),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|state_prepare_callback_0|object_4|{}|{}|{}",offset_of!(PreflightSupplementStatePrepareCallback0,object_4),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("isupplement|state_prepare_callback_1|{}|{}",size_of::<PreflightSupplementStatePrepareCallback1>(),align_of::<PreflightSupplementStatePrepareCallback1>());
println!("isupplementfield|state_prepare_callback_1|object_0|{}|{}|{}",offset_of!(PreflightSupplementStatePrepareCallback1,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|state_prepare_callback_1|object_1|{}|{}|{}",offset_of!(PreflightSupplementStatePrepareCallback1,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_wasi::accounted::AccountedWasi,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("isupplementfield|state_prepare_callback_1|object_2|{}|{}|{}",offset_of!(PreflightSupplementStatePrepareCallback1,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("isupplementfield|state_prepare_callback_1|object_3|{}|{}|{}",offset_of!(PreflightSupplementStatePrepareCallback1,object_3),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("isupplementfield|state_prepare_callback_1|object_4|{}|{}|{}",offset_of!(PreflightSupplementStatePrepareCallback1,object_4),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("isupplementfield|state_prepare_callback_1|object_5|{}|{}|{}",offset_of!(PreflightSupplementStatePrepareCallback1,object_5),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("isupplement|construction_bytes|{}|{}",size_of::<PreflightSupplementConstructionBytes>(),align_of::<PreflightSupplementConstructionBytes>());
println!("isupplementfield|construction_bytes|object_0|{}|{}|{}",offset_of!(PreflightSupplementConstructionBytes,object_0),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("isupplement|checked|{}|{}",size_of::<PreflightSupplementChecked>(),align_of::<PreflightSupplementChecked>());
println!("isupplementfield|checked|object_0|{}|{}|{}",offset_of!(PreflightSupplementChecked,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|checked|object_1|{}|{}|{}",offset_of!(PreflightSupplementChecked,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("isupplementfield|checked|object_2|{}|{}|{}",offset_of!(PreflightSupplementChecked,object_2),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("isupplementfield|checked|object_3|{}|{}|{}",offset_of!(PreflightSupplementChecked,object_3),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("isupplementfield|checked|object_4|{}|{}|{}",offset_of!(PreflightSupplementChecked,object_4),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|checked|object_5|{}|{}|{}",offset_of!(PreflightSupplementChecked,object_5),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("isupplement|construction_failure|{}|{}",size_of::<PreflightSupplementConstructionFailure>(),align_of::<PreflightSupplementConstructionFailure>());
println!("isupplementfield|construction_failure|object_0|{}|{}|{}",offset_of!(PreflightSupplementConstructionFailure,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|construction_failure|object_1|{}|{}|{}",offset_of!(PreflightSupplementConstructionFailure,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("isupplementfield|construction_failure|object_2|{}|{}|{}",offset_of!(PreflightSupplementConstructionFailure,object_2),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("isupplementfield|construction_failure|object_3|{}|{}|{}",offset_of!(PreflightSupplementConstructionFailure,object_3),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("isupplementfield|construction_failure|object_4|{}|{}|{}",offset_of!(PreflightSupplementConstructionFailure,object_4),size_of::<super::control::SwiftRunFailureKind>(),align_of::<super::control::SwiftRunFailureKind>());
println!("isupplementfield|construction_failure|object_5|{}|{}|{}",offset_of!(PreflightSupplementConstructionFailure,object_5),size_of::<&'static str>(),align_of::<&'static str>());
println!("isupplementfield|construction_failure|object_6|{}|{}|{}",offset_of!(PreflightSupplementConstructionFailure,object_6),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("isupplementfield|construction_failure|object_7|{}|{}|{}",offset_of!(PreflightSupplementConstructionFailure,object_7),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|construction_failure|object_8|{}|{}|{}",offset_of!(PreflightSupplementConstructionFailure,object_8),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("isupplement|layout_failure|{}|{}",size_of::<PreflightSupplementLayoutFailure>(),align_of::<PreflightSupplementLayoutFailure>());
println!("isupplementfield|layout_failure|object_0|{}|{}|{}",offset_of!(PreflightSupplementLayoutFailure,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|layout_failure|object_1|{}|{}|{}",offset_of!(PreflightSupplementLayoutFailure,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("isupplementfield|layout_failure|object_2|{}|{}|{}",offset_of!(PreflightSupplementLayoutFailure,object_2),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("isupplementfield|layout_failure|object_3|{}|{}|{}",offset_of!(PreflightSupplementLayoutFailure,object_3),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("isupplementfield|layout_failure|object_4|{}|{}|{}",offset_of!(PreflightSupplementLayoutFailure,object_4),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("isupplement|cache_owner|{}|{}",size_of::<PreflightSupplementCacheOwner>(),align_of::<PreflightSupplementCacheOwner>());
println!("isupplementfield|cache_owner|object_0|{}|{}|{}",offset_of!(PreflightSupplementCacheOwner,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|cache_owner|object_1|{}|{}|{}",offset_of!(PreflightSupplementCacheOwner,object_1),size_of::<&'static SwiftFunctionCache>(),align_of::<&'static SwiftFunctionCache>());
println!("isupplementfield|cache_owner|object_2|{}|{}|{}",offset_of!(PreflightSupplementCacheOwner,object_2),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("isupplementfield|cache_owner|object_3|{}|{}|{}",offset_of!(PreflightSupplementCacheOwner,object_3),size_of::<Option<&'static AccountedWasi>>(),align_of::<Option<&'static AccountedWasi>>());
println!("isupplementfield|cache_owner|object_4|{}|{}|{}",offset_of!(PreflightSupplementCacheOwner,object_4),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("isupplementfield|cache_owner|object_5|{}|{}|{}",offset_of!(PreflightSupplementCacheOwner,object_5),size_of::<&'static mut crate::experimental_swift_reactor::cache::CacheControl<'static>>(),align_of::<&'static mut crate::experimental_swift_reactor::cache::CacheControl<'static>>());
println!("isupplementfield|cache_owner|object_6|{}|{}|{}",offset_of!(PreflightSupplementCacheOwner,object_6),size_of::<crate::experimental_swift_reactor::cache::CacheControl<'static>>(),align_of::<crate::experimental_swift_reactor::cache::CacheControl<'static>>());
println!("isupplement|cache_header|{}|{}",size_of::<PreflightSupplementCacheHeader>(),align_of::<PreflightSupplementCacheHeader>());
println!("isupplementfield|cache_header|object_0|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|cache_header|object_1|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_1),size_of::<&'static mut CacheControl<'static>>(),align_of::<&'static mut CacheControl<'static>>());
println!("isupplementfield|cache_header|object_2|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_2),size_of::<&'static SwiftFunctionCache>(),align_of::<&'static SwiftFunctionCache>());
println!("isupplementfield|cache_header|object_3|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_3),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::option::Option<crate::experimental_wasi::WasiUsage>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, std::option::Option<crate::experimental_wasi::WasiUsage>>>());
println!("isupplementfield|cache_header|object_4|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_4),size_of::<std::result::Result<std::option::Option<crate::experimental_wasi::WasiUsage>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::option::Option<crate::experimental_wasi::WasiUsage>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|cache_header|object_5|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_5),size_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>());
println!("isupplementfield|cache_header|object_6|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_6),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("isupplementfield|cache_header|object_7|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_7),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|cache_header|object_8|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_8),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|cache_header|object_9|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_9),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|cache_header|object_10|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_10),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|cache_header|object_11|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_11),size_of::<crate::experimental::cache::CacheFailureKind>(),align_of::<crate::experimental::cache::CacheFailureKind>());
println!("isupplementfield|cache_header|object_12|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_12),size_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>());
println!("isupplementfield|cache_header|object_13|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_13),size_of::<std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("isupplementfield|cache_header|object_14|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_14),size_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("isupplementfield|cache_header|object_15|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_15),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|cache_header|object_16|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_16),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("isupplementfield|cache_header|object_17|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_17),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|cache_header|object_18|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_18),size_of::<&'static crate::experimental_swift_reactor::cache::CacheControl<'static>>(),align_of::<&'static crate::experimental_swift_reactor::cache::CacheControl<'static>>());
println!("isupplementfield|cache_header|object_19|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_19),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("isupplementfield|cache_header|object_20|{}|{}|{}",offset_of!(PreflightSupplementCacheHeader,object_20),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("isupplement|cache_pairing|{}|{}",size_of::<PreflightSupplementCachePairing>(),align_of::<PreflightSupplementCachePairing>());
println!("isupplementfield|cache_pairing|object_0|{}|{}|{}",offset_of!(PreflightSupplementCachePairing,object_0),size_of::<std::result::Result<std::option::Option<crate::experimental_wasi::WasiUsage>, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::option::Option<crate::experimental_wasi::WasiUsage>, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|cache_pairing|object_1|{}|{}|{}",offset_of!(PreflightSupplementCachePairing,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("isupplementfield|cache_pairing|object_2|{}|{}|{}",offset_of!(PreflightSupplementCachePairing,object_2),size_of::<Option<&'static AccountedWasi>>(),align_of::<Option<&'static AccountedWasi>>());
println!("isupplementfield|cache_pairing|object_3|{}|{}|{}",offset_of!(PreflightSupplementCachePairing,object_3),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("isupplementfield|cache_pairing|object_4|{}|{}|{}",offset_of!(PreflightSupplementCachePairing,object_4),size_of::<std::option::Option<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::option::Option<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("isupplementfield|cache_pairing|object_5|{}|{}|{}",offset_of!(PreflightSupplementCachePairing,object_5),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("isupplementfield|cache_pairing|object_6|{}|{}|{}",offset_of!(PreflightSupplementCachePairing,object_6),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("isupplement|cache_pairing_callback_0|{}|{}",size_of::<PreflightSupplementCachePairingCallback0>(),align_of::<PreflightSupplementCachePairingCallback0>());
println!("isupplementfield|cache_pairing_callback_0|object_0|{}|{}|{}",offset_of!(PreflightSupplementCachePairingCallback0,object_0),size_of::<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|cache_pairing_callback_0|object_1|{}|{}|{}",offset_of!(PreflightSupplementCachePairingCallback0,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor)>());
println!("isupplementfield|cache_pairing_callback_0|object_2|{}|{}|{}",offset_of!(PreflightSupplementCachePairingCallback0,object_2),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("isupplementfield|cache_pairing_callback_0|object_3|{}|{}|{}",offset_of!(PreflightSupplementCachePairingCallback0,object_3),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("isupplementfield|cache_pairing_callback_0|object_4|{}|{}|{}",offset_of!(PreflightSupplementCachePairingCallback0,object_4),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("isupplementfield|cache_pairing_callback_0|object_5|{}|{}|{}",offset_of!(PreflightSupplementCachePairingCallback0,object_5),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("isupplement|cache_error|{}|{}",size_of::<PreflightSupplementCacheError>(),align_of::<PreflightSupplementCacheError>());
println!("isupplementfield|cache_error|object_0|{}|{}|{}",offset_of!(PreflightSupplementCacheError,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|cache_error|object_1|{}|{}|{}",offset_of!(PreflightSupplementCacheError,object_1),size_of::<&'static mut CacheControl<'static>>(),align_of::<&'static mut CacheControl<'static>>());
println!("isupplementfield|cache_error|object_2|{}|{}|{}",offset_of!(PreflightSupplementCacheError,object_2),size_of::<crate::experimental::cache::CacheFailureKind>(),align_of::<crate::experimental::cache::CacheFailureKind>());
println!("isupplementfield|cache_error|object_3|{}|{}|{}",offset_of!(PreflightSupplementCacheError,object_3),size_of::<&'static str>(),align_of::<&'static str>());
println!("isupplementfield|cache_error|object_4|{}|{}|{}",offset_of!(PreflightSupplementCacheError,object_4),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("isupplementfield|cache_error|object_5|{}|{}|{}",offset_of!(PreflightSupplementCacheError,object_5),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|cache_error|object_6|{}|{}|{}",offset_of!(PreflightSupplementCacheError,object_6),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("isupplementfield|cache_error|object_7|{}|{}|{}",offset_of!(PreflightSupplementCacheError,object_7),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("isupplementfield|cache_error|object_8|{}|{}|{}",offset_of!(PreflightSupplementCacheError,object_8),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("isupplementfield|cache_error|object_9|{}|{}|{}",offset_of!(PreflightSupplementCacheError,object_9),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|cache_error|object_10|{}|{}|{}",offset_of!(PreflightSupplementCacheError,object_10),size_of::<&'static crate::experimental_swift_reactor::cache::CacheControl<'static>>(),align_of::<&'static crate::experimental_swift_reactor::cache::CacheControl<'static>>());
println!("isupplementfield|cache_error|object_11|{}|{}|{}",offset_of!(PreflightSupplementCacheError,object_11),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("isupplement|cache_observation|{}|{}",size_of::<PreflightSupplementCacheObservation>(),align_of::<PreflightSupplementCacheObservation>());
println!("isupplementfield|cache_observation|object_0|{}|{}|{}",offset_of!(PreflightSupplementCacheObservation,object_0),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|cache_observation|object_1|{}|{}|{}",offset_of!(PreflightSupplementCacheObservation,object_1),size_of::<&'static CacheControl<'static>>(),align_of::<&'static CacheControl<'static>>());
println!("isupplementfield|cache_observation|object_2|{}|{}|{}",offset_of!(PreflightSupplementCacheObservation,object_2),size_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>(),align_of::<std::option::Option<&'static crate::experimental_wasi::accounted::AccountedWasi>>());
println!("isupplement|cache_usage|{}|{}",size_of::<PreflightSupplementCacheUsage>(),align_of::<PreflightSupplementCacheUsage>());
println!("isupplementfield|cache_usage|object_0|{}|{}|{}",offset_of!(PreflightSupplementCacheUsage,object_0),size_of::<crate::experimental_swift_reactor::cache::SwiftCacheUsage>(),align_of::<crate::experimental_swift_reactor::cache::SwiftCacheUsage>());
println!("isupplementfield|cache_usage|object_1|{}|{}|{}",offset_of!(PreflightSupplementCacheUsage,object_1),size_of::<&'static SwiftFunctionCache>(),align_of::<&'static SwiftFunctionCache>());
println!("isupplement|wasi_checked_usage|{}|{}",size_of::<PreflightSupplementWasiCheckedUsage>(),align_of::<PreflightSupplementWasiCheckedUsage>());
println!("isupplementfield|wasi_checked_usage|object_0|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_0),size_of::<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<crate::experimental_wasi::WasiUsage, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|wasi_checked_usage|object_1|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_1),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("isupplementfield|wasi_checked_usage|object_2|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_2),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("isupplementfield|wasi_checked_usage|object_3|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_3),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("isupplementfield|wasi_checked_usage|object_4|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_4),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|wasi_checked_usage|object_5|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_5),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("isupplementfield|wasi_checked_usage|object_6|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_6),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("isupplementfield|wasi_checked_usage|object_7|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_7),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|wasi_checked_usage|object_8|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_8),size_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>());
println!("isupplementfield|wasi_checked_usage|object_9|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_9),size_of::<std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("isupplementfield|wasi_checked_usage|object_10|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_10),size_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("isupplementfield|wasi_checked_usage|object_11|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_11),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|wasi_checked_usage|object_12|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_12),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|wasi_checked_usage|object_13|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_13),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|wasi_checked_usage|object_14|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_14),size_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>());
println!("isupplementfield|wasi_checked_usage|object_15|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_15),size_of::<(&'static crate::experimental_wasi::accounted::AccountedWasi,)>(),align_of::<(&'static crate::experimental_wasi::accounted::AccountedWasi,)>());
println!("isupplementfield|wasi_checked_usage|object_16|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_16),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("isupplementfield|wasi_checked_usage|object_17|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_17),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|wasi_checked_usage|object_18|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_18),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|wasi_checked_usage|object_19|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_19),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|wasi_checked_usage|object_20|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_20),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("isupplementfield|wasi_checked_usage|object_21|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsage,object_21),size_of::<&'static crate::experimental_wasi::WasiContext>(),align_of::<&'static crate::experimental_wasi::WasiContext>());
println!("isupplement|wasi_checked_usage_callback_0|{}|{}",size_of::<PreflightSupplementWasiCheckedUsageCallback0>(),align_of::<PreflightSupplementWasiCheckedUsageCallback0>());
println!("isupplementfield|wasi_checked_usage_callback_0|object_0|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsageCallback0,object_0),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("isupplementfield|wasi_checked_usage_callback_0|object_1|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsageCallback0,object_1),size_of::<(&'static crate::experimental_wasi::accounted::AccountedWasi,)>(),align_of::<(&'static crate::experimental_wasi::accounted::AccountedWasi,)>());
println!("isupplementfield|wasi_checked_usage_callback_0|object_2|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsageCallback0,object_2),size_of::<&'static crate::experimental_wasi::WasiContext>(),align_of::<&'static crate::experimental_wasi::WasiContext>());
println!("isupplementfield|wasi_checked_usage_callback_0|object_3|{}|{}|{}",offset_of!(PreflightSupplementWasiCheckedUsageCallback0,object_3),size_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>(),align_of::<&'static crate::experimental_wasi::accounted::AccountedWasi>());
println!("isupplement|wasi_usage|{}|{}",size_of::<PreflightSupplementWasiUsage>(),align_of::<PreflightSupplementWasiUsage>());
println!("isupplementfield|wasi_usage|object_0|{}|{}|{}",offset_of!(PreflightSupplementWasiUsage,object_0),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("isupplementfield|wasi_usage|object_1|{}|{}|{}",offset_of!(PreflightSupplementWasiUsage,object_1),size_of::<&'static AccountedWasi>(),align_of::<&'static AccountedWasi>());
println!("isupplementfield|wasi_usage|object_2|{}|{}|{}",offset_of!(PreflightSupplementWasiUsage,object_2),size_of::<&'static crate::experimental_wasi::WasiContext>(),align_of::<&'static crate::experimental_wasi::WasiContext>());
println!("isupplement|context_usage|{}|{}",size_of::<PreflightSupplementContextUsage>(),align_of::<PreflightSupplementContextUsage>());
println!("isupplementfield|context_usage|object_0|{}|{}|{}",offset_of!(PreflightSupplementContextUsage,object_0),size_of::<crate::experimental_wasi::WasiUsage>(),align_of::<crate::experimental_wasi::WasiUsage>());
println!("isupplementfield|context_usage|object_1|{}|{}|{}",offset_of!(PreflightSupplementContextUsage,object_1),size_of::<&'static crate::experimental_wasi::WasiContext>(),align_of::<&'static crate::experimental_wasi::WasiContext>());
println!("isupplement|adopted_owner|{}|{}",size_of::<PreflightSupplementAdoptedOwner>(),align_of::<PreflightSupplementAdoptedOwner>());
println!("isupplementfield|adopted_owner|object_0|{}|{}|{}",offset_of!(PreflightSupplementAdoptedOwner,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|adopted_owner|object_1|{}|{}|{}",offset_of!(PreflightSupplementAdoptedOwner,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("isupplementfield|adopted_owner|object_2|{}|{}|{}",offset_of!(PreflightSupplementAdoptedOwner,object_2),size_of::<&'static super::control::AdoptedProof>(),align_of::<&'static super::control::AdoptedProof>());
println!("isupplementfield|adopted_owner|object_3|{}|{}|{}",offset_of!(PreflightSupplementAdoptedOwner,object_3),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("isupplementfield|adopted_owner|object_4|{}|{}|{}",offset_of!(PreflightSupplementAdoptedOwner,object_4),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("isupplementfield|adopted_owner|object_5|{}|{}|{}",offset_of!(PreflightSupplementAdoptedOwner,object_5),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("isupplementfield|adopted_owner|object_6|{}|{}|{}",offset_of!(PreflightSupplementAdoptedOwner,object_6),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|adopted_owner|object_7|{}|{}|{}",offset_of!(PreflightSupplementAdoptedOwner,object_7),size_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>());
println!("isupplementfield|adopted_owner|object_8|{}|{}|{}",offset_of!(PreflightSupplementAdoptedOwner,object_8),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|adopted_owner|object_9|{}|{}|{}",offset_of!(PreflightSupplementAdoptedOwner,object_9),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|adopted_owner|object_10|{}|{}|{}",offset_of!(PreflightSupplementAdoptedOwner,object_10),size_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<&'static crate::experimental_swift_reactor::control::ReservationTicket>());
println!("isupplement|reservation_matches|{}|{}",size_of::<PreflightSupplementReservationMatches>(),align_of::<PreflightSupplementReservationMatches>());
println!("isupplementfield|reservation_matches|object_0|{}|{}|{}",offset_of!(PreflightSupplementReservationMatches,object_0),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|reservation_matches|object_1|{}|{}|{}",offset_of!(PreflightSupplementReservationMatches,object_1),size_of::<&'static super::control::RuntimeControl>(),align_of::<&'static super::control::RuntimeControl>());
println!("isupplementfield|reservation_matches|object_2|{}|{}|{}",offset_of!(PreflightSupplementReservationMatches,object_2),size_of::<&'static super::control::ReservationTicket>(),align_of::<&'static super::control::ReservationTicket>());
println!("isupplementfield|reservation_matches|object_3|{}|{}|{}",offset_of!(PreflightSupplementReservationMatches,object_3),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|reservation_matches|object_4|{}|{}|{}",offset_of!(PreflightSupplementReservationMatches,object_4),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|reservation_matches|object_5|{}|{}|{}",offset_of!(PreflightSupplementReservationMatches,object_5),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|reservation_matches|object_6|{}|{}|{}",offset_of!(PreflightSupplementReservationMatches,object_6),size_of::<u64>(),align_of::<u64>());
println!("isupplement|reservation_owner|{}|{}",size_of::<PreflightSupplementReservationOwner>(),align_of::<PreflightSupplementReservationOwner>());
println!("isupplementfield|reservation_owner|object_0|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|reservation_owner|object_1|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("isupplementfield|reservation_owner|object_2|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_2),size_of::<&'static super::control::ReservationTicket>(),align_of::<&'static super::control::ReservationTicket>());
println!("isupplementfield|reservation_owner|object_3|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_3),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("isupplementfield|reservation_owner|object_4|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_4),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("isupplementfield|reservation_owner|object_5|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_5),size_of::<std::option::Option<(crate::experimental_swift_reactor::control::SwiftCleanupInvariant, &'static str)>>(),align_of::<std::option::Option<(crate::experimental_swift_reactor::control::SwiftCleanupInvariant, &'static str)>>());
println!("isupplementfield|reservation_owner|object_6|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_6),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|reservation_owner|object_7|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_7),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|reservation_owner|object_8|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_8),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|reservation_owner|object_9|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_9),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|reservation_owner|object_10|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_10),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|reservation_owner|object_11|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_11),size_of::<(crate::experimental_swift_reactor::control::SwiftCleanupInvariant, &'static str)>(),align_of::<(crate::experimental_swift_reactor::control::SwiftCleanupInvariant, &'static str)>());
println!("isupplementfield|reservation_owner|object_12|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_12),size_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>(),align_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>());
println!("isupplementfield|reservation_owner|object_13|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_13),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|reservation_owner|object_14|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_14),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|reservation_owner|object_15|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_15),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|reservation_owner|object_16|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_16),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|reservation_owner|object_17|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_17),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|reservation_owner|object_18|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_18),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservations>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservations>());
println!("isupplementfield|reservation_owner|object_19|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_19),size_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("isupplementfield|reservation_owner|object_20|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_20),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|reservation_owner|object_21|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_21),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|reservation_owner|object_22|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_22),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|reservation_owner|object_23|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_23),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|reservation_owner|object_24|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_24),size_of::<(crate::experimental_swift_reactor::control::SwiftCleanupInvariant, &'static str)>(),align_of::<(crate::experimental_swift_reactor::control::SwiftCleanupInvariant, &'static str)>());
println!("isupplementfield|reservation_owner|object_25|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_25),size_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>(),align_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>());
println!("isupplementfield|reservation_owner|object_26|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_26),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|reservation_owner|object_27|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_27),size_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>(),align_of::<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>());
println!("isupplementfield|reservation_owner|object_28|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_28),size_of::<&'static str>(),align_of::<&'static str>());
println!("isupplementfield|reservation_owner|object_29|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_29),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftCleanupInvariant>());
println!("isupplementfield|reservation_owner|object_30|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_30),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>>());
println!("isupplementfield|reservation_owner|object_31|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_31),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|reservation_owner|object_32|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_32),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("isupplementfield|reservation_owner|object_33|{}|{}|{}",offset_of!(PreflightSupplementReservationOwner,object_33),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("isupplement|enlarge_plain|{}|{}",size_of::<PreflightSupplementEnlargePlain>(),align_of::<PreflightSupplementEnlargePlain>());
println!("isupplementfield|enlarge_plain|object_0|{}|{}|{}",offset_of!(PreflightSupplementEnlargePlain,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|enlarge_plain|object_1|{}|{}|{}",offset_of!(PreflightSupplementEnlargePlain,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("isupplementfield|enlarge_plain|object_2|{}|{}|{}",offset_of!(PreflightSupplementEnlargePlain,object_2),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|enlarge_plain|object_3|{}|{}|{}",offset_of!(PreflightSupplementEnlargePlain,object_3),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("isupplementfield|enlarge_plain|object_4|{}|{}|{}",offset_of!(PreflightSupplementEnlargePlain,object_4),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplement|enlarge_observed|{}|{}",size_of::<PreflightSupplementEnlargeObserved>(),align_of::<PreflightSupplementEnlargeObserved>());
println!("isupplementfield|enlarge_observed|object_0|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|enlarge_observed|object_1|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("isupplementfield|enlarge_observed|object_2|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_2),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|enlarge_observed|object_3|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_3),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("isupplementfield|enlarge_observed|object_4|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_4),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("isupplementfield|enlarge_observed|object_5|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_5),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>>());
println!("isupplementfield|enlarge_observed|object_6|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_6),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|enlarge_observed|object_7|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_7),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|enlarge_observed|object_8|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_8),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|enlarge_observed|object_9|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_9),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, usize>>());
println!("isupplementfield|enlarge_observed|object_10|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_10),size_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<usize, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|enlarge_observed|object_11|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_11),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("isupplementfield|enlarge_observed|object_12|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_12),size_of::<std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<&'static crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("isupplementfield|enlarge_observed|object_13|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_13),size_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("isupplementfield|enlarge_observed|object_14|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_14),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor,&'static std::option::Option<crate::experimental_wasi::WasiUsage>)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor,&'static std::option::Option<crate::experimental_wasi::WasiUsage>)>());
println!("isupplementfield|enlarge_observed|object_15|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_15),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("isupplementfield|enlarge_observed|object_16|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_16),size_of::<&'static std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<&'static std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|enlarge_observed|object_17|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_17),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|enlarge_observed|object_18|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_18),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|enlarge_observed|object_19|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_19),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|enlarge_observed|object_20|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_20),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|enlarge_observed|object_21|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_21),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|enlarge_observed|object_22|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_22),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("isupplementfield|enlarge_observed|object_23|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_23),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("isupplementfield|enlarge_observed|object_24|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_24),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|enlarge_observed|object_25|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_25),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|enlarge_observed|object_26|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_26),size_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, (usize, usize)>>(),align_of::<std::ops::ControlFlow<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>, (usize, usize)>>());
println!("isupplementfield|enlarge_observed|object_27|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_27),size_of::<std::result::Result<(usize, usize), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(usize, usize), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|enlarge_observed|object_28|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_28),size_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("isupplementfield|enlarge_observed|object_29|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_29),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|enlarge_observed|object_30|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_30),size_of::<(usize, bool)>(),align_of::<(usize, bool)>());
println!("isupplementfield|enlarge_observed|object_31|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_31),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|enlarge_observed|object_32|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_32),size_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<std::convert::Infallible, crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|enlarge_observed|object_33|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_33),size_of::<(usize, usize)>(),align_of::<(usize, usize)>());
println!("isupplementfield|enlarge_observed|object_34|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_34),size_of::<()>(),align_of::<()>());
println!("isupplementfield|enlarge_observed|object_35|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_35),size_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservationCategory>());
println!("isupplementfield|enlarge_observed|object_36|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_36),size_of::<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>(),align_of::<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>());
println!("isupplementfield|enlarge_observed|object_37|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_37),size_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<std::option::Option<&'static mut crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("isupplementfield|enlarge_observed|object_38|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObserved,object_38),size_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>(),align_of::<&'static mut std::option::Option<crate::experimental_swift_reactor::control::ReservationTicket>>());
println!("isupplement|enlarge_observed_callback_0|{}|{}",size_of::<PreflightSupplementEnlargeObservedCallback0>(),align_of::<PreflightSupplementEnlargeObservedCallback0>());
println!("isupplementfield|enlarge_observed_callback_0|object_0|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObservedCallback0,object_0),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|enlarge_observed_callback_0|object_1|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObservedCallback0,object_1),size_of::<()>(),align_of::<()>());
println!("isupplementfield|enlarge_observed_callback_0|object_2|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObservedCallback0,object_2),size_of::<&'static super::control::ReservationTicket>(),align_of::<&'static super::control::ReservationTicket>());
println!("isupplement|enlarge_observed_callback_1|{}|{}",size_of::<PreflightSupplementEnlargeObservedCallback1>(),align_of::<PreflightSupplementEnlargeObservedCallback1>());
println!("isupplementfield|enlarge_observed_callback_1|object_0|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObservedCallback1,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|enlarge_observed_callback_1|object_1|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObservedCallback1,object_1),size_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor,&'static std::option::Option<crate::experimental_wasi::WasiUsage>)>(),align_of::<(&'static mut crate::experimental_swift_reactor::control::RuntimeControl,&'static crate::experimental_swift_reactor::control::Cursor,&'static std::option::Option<crate::experimental_wasi::WasiUsage>)>());
println!("isupplementfield|enlarge_observed_callback_1|object_2|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObservedCallback1,object_2),size_of::<crate::experimental_swift_reactor::control::Cursor>(),align_of::<crate::experimental_swift_reactor::control::Cursor>());
println!("isupplementfield|enlarge_observed_callback_1|object_3|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObservedCallback1,object_3),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("isupplementfield|enlarge_observed_callback_1|object_4|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObservedCallback1,object_4),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("isupplementfield|enlarge_observed_callback_1|object_5|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObservedCallback1,object_5),size_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplementfield|enlarge_observed_callback_1|object_6|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObservedCallback1,object_6),size_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static mut crate::experimental_swift_reactor::control::RuntimeControl>());
println!("isupplementfield|enlarge_observed_callback_1|object_7|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObservedCallback1,object_7),size_of::<&'static crate::experimental_swift_reactor::control::Cursor>(),align_of::<&'static crate::experimental_swift_reactor::control::Cursor>());
println!("isupplementfield|enlarge_observed_callback_1|object_8|{}|{}|{}",offset_of!(PreflightSupplementEnlargeObservedCallback1,object_8),size_of::<&'static std::option::Option<crate::experimental_wasi::WasiUsage>>(),align_of::<&'static std::option::Option<crate::experimental_wasi::WasiUsage>>());
println!("isupplement|control_check|{}|{}",size_of::<PreflightSupplementControlCheck>(),align_of::<PreflightSupplementControlCheck>());
println!("isupplementfield|control_check|object_0|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_0),size_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|control_check|object_1|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("isupplementfield|control_check|object_2|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_2),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("isupplementfield|control_check|object_3|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_3),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("isupplementfield|control_check|object_4|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_4),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|control_check|object_5|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_5),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|control_check|object_6|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_6),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|control_check|object_7|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_7),size_of::<&'static crate::execute::Cancellation>(),align_of::<&'static crate::execute::Cancellation>());
println!("isupplementfield|control_check|object_8|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_8),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|control_check|object_9|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_9),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("isupplementfield|control_check|object_10|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_10),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("isupplementfield|control_check|object_11|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_11),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|control_check|object_12|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_12),size_of::<&'static std::time::Instant>(),align_of::<&'static std::time::Instant>());
println!("isupplementfield|control_check|object_13|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_13),size_of::<std::time::Instant>(),align_of::<std::time::Instant>());
println!("isupplementfield|control_check|object_14|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_14),size_of::<&'static std::time::Instant>(),align_of::<&'static std::time::Instant>());
println!("isupplementfield|control_check|object_15|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_15),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|control_check|object_16|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_16),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("isupplementfield|control_check|object_17|{}|{}|{}",offset_of!(PreflightSupplementControlCheck,object_17),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("isupplement|control_usage|{}|{}",size_of::<PreflightSupplementControlUsage>(),align_of::<PreflightSupplementControlUsage>());
println!("isupplementfield|control_usage|object_0|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>());
println!("isupplementfield|control_usage|object_1|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_1),size_of::<&'static super::control::RuntimeControl>(),align_of::<&'static super::control::RuntimeControl>());
println!("isupplementfield|control_usage|object_2|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_2),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("isupplementfield|control_usage|object_3|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_3),size_of::<std::time::Instant>(),align_of::<std::time::Instant>());
println!("isupplementfield|control_usage|object_4|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_4),size_of::<crate::experimental_swift_reactor::control::SwiftReservations>(),align_of::<crate::experimental_swift_reactor::control::SwiftReservations>());
println!("isupplementfield|control_usage|object_5|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_5),size_of::<crate::experimental_swift_reactor::control::SwiftLiveUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftLiveUsage>());
println!("isupplementfield|control_usage|object_6|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_6),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|control_usage|object_7|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_7),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|control_usage|object_8|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_8),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|control_usage|object_9|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_9),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|control_usage|object_10|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_10),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|control_usage|object_11|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_11),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftCleanupInvariant>>());
println!("isupplementfield|control_usage|object_12|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_12),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|control_usage|object_13|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_13),size_of::<std::time::Duration>(),align_of::<std::time::Duration>());
println!("isupplementfield|control_usage|object_14|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_14),size_of::<&'static std::time::Instant>(),align_of::<&'static std::time::Instant>());
println!("isupplementfield|control_usage|object_15|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_15),size_of::<std::time::Instant>(),align_of::<std::time::Instant>());
println!("isupplementfield|control_usage|object_16|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_16),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|control_usage|object_17|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_17),size_of::<crate::experimental_swift_reactor::control::SwiftDeadlineOrigin>(),align_of::<crate::experimental_swift_reactor::control::SwiftDeadlineOrigin>());
println!("isupplementfield|control_usage|object_18|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_18),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|control_usage|object_19|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_19),size_of::<std::time::Duration>(),align_of::<std::time::Duration>());
println!("isupplementfield|control_usage|object_20|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_20),size_of::<&'static std::time::Instant>(),align_of::<&'static std::time::Instant>());
println!("isupplementfield|control_usage|object_21|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_21),size_of::<std::time::Instant>(),align_of::<std::time::Instant>());
println!("isupplementfield|control_usage|object_22|{}|{}|{}",offset_of!(PreflightSupplementControlUsage,object_22),size_of::<crate::experimental::swift::SwiftValidationUsage>(),align_of::<crate::experimental::swift::SwiftValidationUsage>());
println!("isupplement|control_fail|{}|{}",size_of::<PreflightSupplementControlFail>(),align_of::<PreflightSupplementControlFail>());
println!("isupplementfield|control_fail|object_0|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_0),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|control_fail|object_1|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("isupplementfield|control_fail|object_2|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_2),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("isupplementfield|control_fail|object_3|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_3),size_of::<super::control::Fault>(),align_of::<super::control::Fault>());
println!("isupplementfield|control_fail|object_4|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_4),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("isupplementfield|control_fail|object_5|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_5),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|control_fail|object_6|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_6),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|control_fail|object_7|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_7),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|control_fail|object_8|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_8),size_of::<crate::experimental_swift_reactor::control::SwiftRunStage>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunStage>());
println!("isupplementfield|control_fail|object_9|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_9),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("isupplementfield|control_fail|object_10|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_10),size_of::<&'static str>(),align_of::<&'static str>());
println!("isupplementfield|control_fail|object_11|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_11),size_of::<std::option::Option<u32>>(),align_of::<std::option::Option<u32>>());
println!("isupplementfield|control_fail|object_12|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_12),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("isupplementfield|control_fail|object_13|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_13),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>>());
println!("isupplementfield|control_fail|object_14|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_14),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|control_fail|object_15|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_15),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|control_fail|object_16|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_16),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("isupplementfield|control_fail|object_17|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_17),size_of::<crate::experimental_swift_reactor::control::SwiftDeadlineOrigin>(),align_of::<crate::experimental_swift_reactor::control::SwiftDeadlineOrigin>());
println!("isupplementfield|control_fail|object_18|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_18),size_of::<std::option::Option<crate::experimental_wasi::WasiFailure>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiFailure>>());
println!("isupplementfield|control_fail|object_19|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_19),size_of::<std::option::Option<u32>>(),align_of::<std::option::Option<u32>>());
println!("isupplementfield|control_fail|object_20|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_20),size_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunUsage>());
println!("isupplementfield|control_fail|object_21|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_21),size_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>());
println!("isupplementfield|control_fail|object_22|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_22),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunUsage>>());
println!("isupplementfield|control_fail|object_23|{}|{}|{}",offset_of!(PreflightSupplementControlFail,object_23),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplement|bytes_preflight|{}|{}",size_of::<PreflightSupplementBytesPreflight>(),align_of::<PreflightSupplementBytesPreflight>());
println!("isupplementfield|bytes_preflight|object_0|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_0),size_of::<std::result::Result<(usize, usize), crate::experimental_swift_reactor::control::SwiftRunFailure>>(),align_of::<std::result::Result<(usize, usize), crate::experimental_swift_reactor::control::SwiftRunFailure>>());
println!("isupplementfield|bytes_preflight|object_1|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("isupplementfield|bytes_preflight|object_2|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_2),size_of::<super::control::SwiftReservationCategory>(),align_of::<super::control::SwiftReservationCategory>());
println!("isupplementfield|bytes_preflight|object_3|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_3),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|bytes_preflight|object_4|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_4),size_of::<super::control::Cursor>(),align_of::<super::control::Cursor>());
println!("isupplementfield|bytes_preflight|object_5|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_5),size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("isupplementfield|bytes_preflight|object_6|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_6),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("isupplementfield|bytes_preflight|object_7|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_7),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|bytes_preflight|object_8|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_8),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|bytes_preflight|object_9|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_9),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservations>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservations>());
println!("isupplementfield|bytes_preflight|object_10|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_10),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|bytes_preflight|object_11|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_11),size_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>(),align_of::<&'static crate::experimental_swift_reactor::control::RuntimeControl>());
println!("isupplementfield|bytes_preflight|object_12|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_12),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|bytes_preflight|object_13|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_13),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("isupplementfield|bytes_preflight|object_14|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_14),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("isupplementfield|bytes_preflight|object_15|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_15),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("isupplementfield|bytes_preflight|object_16|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_16),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|bytes_preflight|object_17|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_17),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|bytes_preflight|object_18|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_18),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|bytes_preflight|object_19|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_19),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("isupplementfield|bytes_preflight|object_20|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_20),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("isupplementfield|bytes_preflight|object_21|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_21),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("isupplementfield|bytes_preflight|object_22|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_22),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("isupplementfield|bytes_preflight|object_23|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_23),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|bytes_preflight|object_24|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_24),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|bytes_preflight|object_25|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_25),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("isupplementfield|bytes_preflight|object_26|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_26),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|bytes_preflight|object_27|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_27),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|bytes_preflight|object_28|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_28),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("isupplementfield|bytes_preflight|object_29|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_29),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("isupplementfield|bytes_preflight|object_30|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_30),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailure>());
println!("isupplementfield|bytes_preflight|object_31|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_31),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("isupplementfield|bytes_preflight|object_32|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_32),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("isupplementfield|bytes_preflight|object_33|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_33),size_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunFailureKind>());
println!("isupplementfield|bytes_preflight|object_34|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_34),size_of::<crate::experimental_swift_reactor::control::SwiftRunResource>(),align_of::<crate::experimental_swift_reactor::control::SwiftRunResource>());
println!("isupplementfield|bytes_preflight|object_35|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_35),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|bytes_preflight|object_36|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_36),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|bytes_preflight|object_37|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_37),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|bytes_preflight|object_38|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_38),size_of::<(usize, usize)>(),align_of::<(usize, usize)>());
println!("isupplementfield|bytes_preflight|object_39|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_39),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|bytes_preflight|object_40|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflight,object_40),size_of::<usize>(),align_of::<usize>());
println!("isupplement|bytes_preflight_callback_0|{}|{}",size_of::<PreflightSupplementBytesPreflightCallback0>(),align_of::<PreflightSupplementBytesPreflightCallback0>());
println!("isupplementfield|bytes_preflight_callback_0|object_0|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback0,object_0),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|bytes_preflight_callback_0|object_1|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback0,object_1),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("isupplementfield|bytes_preflight_callback_0|object_2|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback0,object_2),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|bytes_preflight_callback_0|object_3|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback0,object_3),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|bytes_preflight_callback_0|object_4|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback0,object_4),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("isupplement|bytes_preflight_callback_1|{}|{}",size_of::<PreflightSupplementBytesPreflightCallback1>(),align_of::<PreflightSupplementBytesPreflightCallback1>());
println!("isupplementfield|bytes_preflight_callback_1|object_0|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback1,object_0),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|bytes_preflight_callback_1|object_1|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback1,object_1),size_of::<()>(),align_of::<()>());
println!("isupplementfield|bytes_preflight_callback_1|object_2|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback1,object_2),size_of::<usize>(),align_of::<usize>());
println!("isupplement|bytes_preflight_callback_2|{}|{}",size_of::<PreflightSupplementBytesPreflightCallback2>(),align_of::<PreflightSupplementBytesPreflightCallback2>());
println!("isupplementfield|bytes_preflight_callback_2|object_0|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback2,object_0),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|bytes_preflight_callback_2|object_1|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback2,object_1),size_of::<(&'static usize,)>(),align_of::<(&'static usize,)>());
println!("isupplementfield|bytes_preflight_callback_2|object_2|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback2,object_2),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|bytes_preflight_callback_2|object_3|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback2,object_3),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|bytes_preflight_callback_2|object_4|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback2,object_4),size_of::<&'static usize>(),align_of::<&'static usize>());
println!("isupplement|bytes_preflight_callback_3|{}|{}",size_of::<PreflightSupplementBytesPreflightCallback3>(),align_of::<PreflightSupplementBytesPreflightCallback3>());
println!("isupplementfield|bytes_preflight_callback_3|object_0|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback3,object_0),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|bytes_preflight_callback_3|object_1|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback3,object_1),size_of::<()>(),align_of::<()>());
println!("isupplementfield|bytes_preflight_callback_3|object_2|{}|{}|{}",offset_of!(PreflightSupplementBytesPreflightCallback3,object_2),size_of::<usize>(),align_of::<usize>());
println!("isupplement|bytes_commit|{}|{}",size_of::<PreflightSupplementBytesCommit>(),align_of::<PreflightSupplementBytesCommit>());
println!("isupplementfield|bytes_commit|object_0|{}|{}|{}",offset_of!(PreflightSupplementBytesCommit,object_0),size_of::<()>(),align_of::<()>());
println!("isupplementfield|bytes_commit|object_1|{}|{}|{}",offset_of!(PreflightSupplementBytesCommit,object_1),size_of::<&'static mut super::control::RuntimeControl>(),align_of::<&'static mut super::control::RuntimeControl>());
println!("isupplementfield|bytes_commit|object_2|{}|{}|{}",offset_of!(PreflightSupplementBytesCommit,object_2),size_of::<super::control::SwiftReservationCategory>(),align_of::<super::control::SwiftReservationCategory>());
println!("isupplementfield|bytes_commit|object_3|{}|{}|{}",offset_of!(PreflightSupplementBytesCommit,object_3),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|bytes_commit|object_4|{}|{}|{}",offset_of!(PreflightSupplementBytesCommit,object_4),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|bytes_commit|object_5|{}|{}|{}",offset_of!(PreflightSupplementBytesCommit,object_5),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|bytes_commit|object_6|{}|{}|{}",offset_of!(PreflightSupplementBytesCommit,object_6),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservations>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservations>());
println!("isupplementfield|bytes_commit|object_7|{}|{}|{}",offset_of!(PreflightSupplementBytesCommit,object_7),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|bytes_commit|object_8|{}|{}|{}",offset_of!(PreflightSupplementBytesCommit,object_8),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|bytes_commit|object_9|{}|{}|{}",offset_of!(PreflightSupplementBytesCommit,object_9),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|bytes_commit|object_10|{}|{}|{}",offset_of!(PreflightSupplementBytesCommit,object_10),size_of::<usize>(),align_of::<usize>());
println!("isupplement|category_limit|{}|{}",size_of::<PreflightSupplementCategoryLimit>(),align_of::<PreflightSupplementCategoryLimit>());
println!("isupplementfield|category_limit|object_0|{}|{}|{}",offset_of!(PreflightSupplementCategoryLimit,object_0),size_of::<usize>(),align_of::<usize>());
println!("isupplementfield|category_limit|object_1|{}|{}|{}",offset_of!(PreflightSupplementCategoryLimit,object_1),size_of::<&'static super::control::RuntimeControl>(),align_of::<&'static super::control::RuntimeControl>());
println!("isupplementfield|category_limit|object_2|{}|{}|{}",offset_of!(PreflightSupplementCategoryLimit,object_2),size_of::<super::control::SwiftReservationCategory>(),align_of::<super::control::SwiftReservationCategory>());
println!("isupplementfield|category_limit|object_3|{}|{}|{}",offset_of!(PreflightSupplementCategoryLimit,object_3),size_of::<isize>(),align_of::<isize>());
println!("isupplement|category_ref|{}|{}",size_of::<PreflightSupplementCategoryRef>(),align_of::<PreflightSupplementCategoryRef>());
println!("isupplementfield|category_ref|object_0|{}|{}|{}",offset_of!(PreflightSupplementCategoryRef,object_0),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_ref|object_1|{}|{}|{}",offset_of!(PreflightSupplementCategoryRef,object_1),size_of::<&'static super::control::SwiftReservations>(),align_of::<&'static super::control::SwiftReservations>());
println!("isupplementfield|category_ref|object_2|{}|{}|{}",offset_of!(PreflightSupplementCategoryRef,object_2),size_of::<super::control::SwiftReservationCategory>(),align_of::<super::control::SwiftReservationCategory>());
println!("isupplementfield|category_ref|object_3|{}|{}|{}",offset_of!(PreflightSupplementCategoryRef,object_3),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_ref|object_4|{}|{}|{}",offset_of!(PreflightSupplementCategoryRef,object_4),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|category_ref|object_5|{}|{}|{}",offset_of!(PreflightSupplementCategoryRef,object_5),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_ref|object_6|{}|{}|{}",offset_of!(PreflightSupplementCategoryRef,object_6),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_ref|object_7|{}|{}|{}",offset_of!(PreflightSupplementCategoryRef,object_7),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_ref|object_8|{}|{}|{}",offset_of!(PreflightSupplementCategoryRef,object_8),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_ref|object_9|{}|{}|{}",offset_of!(PreflightSupplementCategoryRef,object_9),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_ref|object_10|{}|{}|{}",offset_of!(PreflightSupplementCategoryRef,object_10),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_ref|object_11|{}|{}|{}",offset_of!(PreflightSupplementCategoryRef,object_11),size_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplement|category_mut|{}|{}",size_of::<PreflightSupplementCategoryMut>(),align_of::<PreflightSupplementCategoryMut>());
println!("isupplementfield|category_mut|object_0|{}|{}|{}",offset_of!(PreflightSupplementCategoryMut,object_0),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_mut|object_1|{}|{}|{}",offset_of!(PreflightSupplementCategoryMut,object_1),size_of::<&'static mut super::control::SwiftReservations>(),align_of::<&'static mut super::control::SwiftReservations>());
println!("isupplementfield|category_mut|object_2|{}|{}|{}",offset_of!(PreflightSupplementCategoryMut,object_2),size_of::<super::control::SwiftReservationCategory>(),align_of::<super::control::SwiftReservationCategory>());
println!("isupplementfield|category_mut|object_3|{}|{}|{}",offset_of!(PreflightSupplementCategoryMut,object_3),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_mut|object_4|{}|{}|{}",offset_of!(PreflightSupplementCategoryMut,object_4),size_of::<isize>(),align_of::<isize>());
println!("isupplementfield|category_mut|object_5|{}|{}|{}",offset_of!(PreflightSupplementCategoryMut,object_5),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_mut|object_6|{}|{}|{}",offset_of!(PreflightSupplementCategoryMut,object_6),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_mut|object_7|{}|{}|{}",offset_of!(PreflightSupplementCategoryMut,object_7),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_mut|object_8|{}|{}|{}",offset_of!(PreflightSupplementCategoryMut,object_8),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_mut|object_9|{}|{}|{}",offset_of!(PreflightSupplementCategoryMut,object_9),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_mut|object_10|{}|{}|{}",offset_of!(PreflightSupplementCategoryMut,object_10),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplementfield|category_mut|object_11|{}|{}|{}",offset_of!(PreflightSupplementCategoryMut,object_11),size_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>(),align_of::<&'static mut crate::experimental_swift_reactor::control::SwiftReservationUsage>());
println!("isupplement|fault_new|{}|{}",size_of::<PreflightSupplementFaultNew>(),align_of::<PreflightSupplementFaultNew>());
println!("isupplementfield|fault_new|object_0|{}|{}|{}",offset_of!(PreflightSupplementFaultNew,object_0),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("isupplementfield|fault_new|object_1|{}|{}|{}",offset_of!(PreflightSupplementFaultNew,object_1),size_of::<super::control::SwiftRunFailureKind>(),align_of::<super::control::SwiftRunFailureKind>());
println!("isupplementfield|fault_new|object_2|{}|{}|{}",offset_of!(PreflightSupplementFaultNew,object_2),size_of::<&'static str>(),align_of::<&'static str>());
println!("isupplementfield|fault_new|object_3|{}|{}|{}",offset_of!(PreflightSupplementFaultNew,object_3),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>>());
println!("isupplementfield|fault_new|object_4|{}|{}|{}",offset_of!(PreflightSupplementFaultNew,object_4),size_of::<std::option::Option<usize>>(),align_of::<std::option::Option<usize>>());
println!("isupplementfield|fault_new|object_5|{}|{}|{}",offset_of!(PreflightSupplementFaultNew,object_5),size_of::<std::option::Option<crate::experimental_wasi::WasiFailure>>(),align_of::<std::option::Option<crate::experimental_wasi::WasiFailure>>());
println!("isupplementfield|fault_new|object_6|{}|{}|{}",offset_of!(PreflightSupplementFaultNew,object_6),size_of::<std::option::Option<u32>>(),align_of::<std::option::Option<u32>>());
println!("isupplement|fault_limit|{}|{}",size_of::<PreflightSupplementFaultLimit>(),align_of::<PreflightSupplementFaultLimit>());
println!("isupplementfield|fault_limit|object_0|{}|{}|{}",offset_of!(PreflightSupplementFaultLimit,object_0),size_of::<crate::experimental_swift_reactor::control::Fault>(),align_of::<crate::experimental_swift_reactor::control::Fault>());
println!("isupplementfield|fault_limit|object_1|{}|{}|{}",offset_of!(PreflightSupplementFaultLimit,object_1),size_of::<super::control::Fault>(),align_of::<super::control::Fault>());
println!("isupplementfield|fault_limit|object_2|{}|{}|{}",offset_of!(PreflightSupplementFaultLimit,object_2),size_of::<super::control::SwiftRunResource>(),align_of::<super::control::SwiftRunResource>());
println!("isupplementfield|fault_limit|object_3|{}|{}|{}",offset_of!(PreflightSupplementFaultLimit,object_3),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|fault_limit|object_4|{}|{}|{}",offset_of!(PreflightSupplementFaultLimit,object_4),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|fault_limit|object_5|{}|{}|{}",offset_of!(PreflightSupplementFaultLimit,object_5),size_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>>(),align_of::<std::option::Option<crate::experimental_swift_reactor::control::SwiftRunResource>>());
println!("isupplement|micros|{}|{}",size_of::<PreflightSupplementMicros>(),align_of::<PreflightSupplementMicros>());
println!("isupplementfield|micros|object_0|{}|{}|{}",offset_of!(PreflightSupplementMicros,object_0),size_of::<u64>(),align_of::<u64>());
println!("isupplementfield|micros|object_1|{}|{}|{}",offset_of!(PreflightSupplementMicros,object_1),size_of::<std::time::Duration>(),align_of::<std::time::Duration>());
println!("isupplementfield|micros|object_2|{}|{}|{}",offset_of!(PreflightSupplementMicros,object_2),size_of::<std::result::Result<u64, std::num::TryFromIntError>>(),align_of::<std::result::Result<u64, std::num::TryFromIntError>>());
println!("isupplementfield|micros|object_3|{}|{}|{}",offset_of!(PreflightSupplementMicros,object_3),size_of::<u128>(),align_of::<u128>());
println!("isupplementfield|micros|object_4|{}|{}|{}",offset_of!(PreflightSupplementMicros,object_4),size_of::<&'static std::time::Duration>(),align_of::<&'static std::time::Duration>());
println!("isupplement|cancelled|{}|{}",size_of::<PreflightSupplementCancelled>(),align_of::<PreflightSupplementCancelled>());
println!("isupplementfield|cancelled|object_0|{}|{}|{}",offset_of!(PreflightSupplementCancelled,object_0),size_of::<bool>(),align_of::<bool>());
println!("isupplementfield|cancelled|object_1|{}|{}|{}",offset_of!(PreflightSupplementCancelled,object_1),size_of::<&'static crate::execute::Cancellation>(),align_of::<&'static crate::execute::Cancellation>());
println!("isupplementfield|cancelled|object_2|{}|{}|{}",offset_of!(PreflightSupplementCancelled,object_2),size_of::<&'static std::sync::atomic::AtomicBool>(),align_of::<&'static std::sync::atomic::AtomicBool>());
println!("isupplementfield|cancelled|object_3|{}|{}|{}",offset_of!(PreflightSupplementCancelled,object_3),size_of::<&'static std::sync::Arc<std::sync::atomic::AtomicBool>>(),align_of::<&'static std::sync::Arc<std::sync::atomic::AtomicBool>>());
println!("isupplementfield|cancelled|object_4|{}|{}|{}",offset_of!(PreflightSupplementCancelled,object_4),size_of::<std::sync::atomic::Ordering>(),align_of::<std::sync::atomic::Ordering>());
println!("isupplementtotal|{}|{}",size_of::<ConstructionPreflightSupplement>(),align_of::<ConstructionPreflightSupplement>());
}
