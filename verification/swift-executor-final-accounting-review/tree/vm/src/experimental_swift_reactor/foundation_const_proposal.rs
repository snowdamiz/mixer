use super::*;
// Candidate proposal only, for root adaptation and separate source acceptance.
// These inventory types are never instantiated. Each field is an explicit
// source role in source-roles.json; whole group max changes only between ended
// refund, record and finish helper calls. This changes no stored owner type.
#[allow(dead_code)]
struct FoundationFinalFinalOutputBorrows {
    outcome: &'static mut Option<SwiftRunFailure>,
    usage: &'static mut Option<SwiftRunUsage>,
}
#[allow(dead_code)]
struct FoundationFinalClockLeaf {
    usage_receiver: &'static RuntimeControl,
    usage_now: Instant,
    elapsed_receiver: &'static Instant,
    elapsed_earlier: Instant,
    elapsed_duration: Duration,
    overshoot_receiver: &'static Instant,
    overshoot_earlier: Instant,
    overshoot_duration: Duration,
    micros_duration: Duration,
    as_micros_receiver: &'static Duration,
    micros_u128: u128,
    try_from_input: u128,
    try_from_output: Result<u64, std::num::TryFromIntError>,
    unwrap_input: Result<u64, std::num::TryFromIntError>,
    unwrap_default: u64,
    micros_return: u64,
    elapsed_return: u64,
    overshoot_return: u64,
}
#[allow(dead_code)]
struct FoundationFinalFaultLeaf {
    cleanup_receiver: &'static mut RuntimeControl,
    invariant: SwiftCleanupInvariant,
    code: &'static str,
    insert_receiver: &'static mut Option<SwiftCleanupInvariant>,
    insert_argument: SwiftCleanupInvariant,
    insert_result: &'static mut SwiftCleanupInvariant,
    cursor_source: Cursor,
    fault_kind: SwiftRunFailureKind,
    fault_code: &'static str,
    fault_source: Fault,
    fail_receiver: &'static mut RuntimeControl,
    cursor_transfer: Cursor,
    fault_transfer: Fault,
}
#[allow(dead_code)]
struct FoundationFinalCategoryLeaves {
    category_receiver: &'static SwiftReservations,
    category_argument: SwiftReservationCategory,
    category_return: &'static SwiftReservationUsage,
    category_mut_receiver: &'static mut SwiftReservations,
    category_mut_argument: SwiftReservationCategory,
    category_mut_return: &'static mut SwiftReservationUsage,
}
#[allow(dead_code)]
struct FoundationFinalRefundParent {
    outputs: FoundationFinalFinalOutputBorrows,
    header_take_receiver: &'static mut Option<ReservationTicket>,
    drop_receiver: &'static mut RuntimeControl,
    refund_receiver: &'static mut RuntimeControl,
    category: Option<usize>,
    combined: Option<usize>,
    count: Option<usize>,
    option_match: (Option<usize>, Option<usize>, Option<usize>),
    category_pattern: usize,
    combined_pattern: usize,
    count_pattern: usize,
    categories: FoundationFinalCategoryLeaves,
    fault: FoundationFinalFaultLeaf,
    clock: FoundationFinalClockLeaf,
}
#[allow(dead_code)]
struct FoundationFinalRecordParent {
    outputs: FoundationFinalFinalOutputBorrows,
    record_receiver: &'static mut RuntimeControl,
    failure_option_receiver: &'static mut Option<SwiftRunFailure>,
    failure_pattern: &'static mut SwiftRunFailure,
    clock: FoundationFinalClockLeaf,
}
#[allow(dead_code)]
struct FoundationFinalFinishConstFormulaParent {
    outputs: FoundationFinalFinalOutputBorrows,
    started: Instant,
    deadline: Instant,
    control_take_receiver: &'static mut Option<ReservationTicket>,
    cancel_take_receiver: &'static mut Option<ReservationTicket>,
    construction_take_receiver: &'static mut Option<ReservationTicket>,
    array: [Option<ReservationTicket>;3],
    into_tickets: std::array::IntoIter<Option<ReservationTicket>,3>,
    flatten_tickets: std::iter::Flatten<std::array::IntoIter<Option<ReservationTicket>,3>>,
    flatten_receiver: &'static mut std::iter::Flatten<std::array::IntoIter<Option<ReservationTicket>,3>>,
    iterator_next: Option<ReservationTicket>,
    category: Option<usize>,
    combined: Option<usize>,
    count: Option<usize>,
    option_match: (Option<usize>,Option<usize>,Option<usize>),
    category_pattern: usize,
    combined_pattern: usize,
    count_pattern: usize,
    categories: FoundationFinalCategoryLeaves,
    ticket_bytes_some: Option<usize>,
    formula_return: Option<usize>,
    insert_receiver: &'static mut Option<SwiftCleanupInvariant>,
    insert_argument: SwiftCleanupInvariant,
    insert_return: &'static mut SwiftCleanupInvariant,
    clock: FoundationFinalClockLeaf,
    now: Instant,
}

const FOUNDATION_FINAL_BOUNDARY_BYTES: usize = {
    let refund = size_of::<FoundationFinalRefundParent>();
    let record = size_of::<FoundationFinalRecordParent>();
    let finish = size_of::<FoundationFinalFinishConstFormulaParent>();
    let first = if refund > record { refund } else { record };
    if first > finish { first } else { finish }
};

// All array/loop/closure metadata computation occurs in this const initializer.
// The public spelling remains a function that copies the precomputed Option.
// No runtime temporary array, IntoIter or try_fold exists in this proposal.
const FOUNDATION_CONSTRUCTION_BYTES: Option<usize> = {
    let terms: [(usize, usize); 8] = [
        (3, size_of::<ValidatedSwiftReactor>()),
        (3, size_of::<RuntimeControl>()),
        (3, size_of::<AdoptedProof>()),
        (4, size_of::<SwiftRunFailure>()),
        (4, size_of::<SwiftRunUsage>()),
        (6, size_of::<ReservationTicket>()),
        (6, size_of::<Option<WasiUsage>>()),
        (1, FOUNDATION_FINAL_BOUNDARY_BYTES),
    ];
    let mut sum = Some(0usize);
    let mut index = 0usize;
    while index < terms.len() {
        sum = match (sum, terms[index].0.checked_mul(terms[index].1)) {
            (Some(accumulated), Some(term)) => accumulated.checked_add(term),
            _ => None,
        };
        index += 1;
    }
    sum
};

// Root replaces the original function with this spelling when adapting.
pub(crate) fn proposed_foundation_construction_bytes() -> Option<usize> {
    FOUNDATION_CONSTRUCTION_BYTES
}

#[test]
fn independent_proposed_final_foundation_const_formula() {
    assert_eq!(foundation_construction_bytes(), Some(16504));
    assert_eq!(FOUNDATION_FINAL_BOUNDARY_BYTES, 864);
    assert_eq!(proposed_foundation_construction_bytes(), Some(17368));
}
