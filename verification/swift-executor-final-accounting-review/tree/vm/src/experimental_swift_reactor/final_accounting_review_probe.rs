#![allow(dead_code)]
use super::*;
use std::mem::{size_of,align_of,offset_of};
struct FinalOutputBorrows {
    outcome: &'static mut Option<SwiftRunFailure>,
    usage: &'static mut Option<SwiftRunUsage>,
}
struct ClockLeaf {
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
struct FaultLeaf {
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
struct CategoryLeaves {
    category_receiver: &'static SwiftReservations,
    category_argument: SwiftReservationCategory,
    category_return: &'static SwiftReservationUsage,
    category_mut_receiver: &'static mut SwiftReservations,
    category_mut_argument: SwiftReservationCategory,
    category_mut_return: &'static mut SwiftReservationUsage,
}
struct RefundParent {
    outputs: FinalOutputBorrows,
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
    categories: CategoryLeaves,
    fault: FaultLeaf,
    clock: ClockLeaf,
}
struct RecordParent {
    outputs: FinalOutputBorrows,
    record_receiver: &'static mut RuntimeControl,
    failure_option_receiver: &'static mut Option<SwiftRunFailure>,
    failure_pattern: &'static mut SwiftRunFailure,
    clock: ClockLeaf,
}
struct FoundationFormulaRuntime {
    items: [(usize,usize);7],
    iterator: std::array::IntoIter<(usize,usize),7>,
    try_fold_receiver: &'static mut std::array::IntoIter<(usize,usize),7>,
    sum: usize,
    pair: (usize,usize),
    count: usize,
    bytes: usize,
    product: Option<usize>,
    product_value: usize,
    next: Option<usize>,
    returned: Option<usize>,
}
struct FinishParent {
    outputs: FinalOutputBorrows,
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
    categories: CategoryLeaves,
    ticket_bytes_some: Option<usize>,
    formula_return: Option<usize>,
    insert_receiver: &'static mut Option<SwiftCleanupInvariant>,
    insert_argument: SwiftCleanupInvariant,
    insert_return: &'static mut SwiftCleanupInvariant,
    clock: ClockLeaf,
    now: Instant,
    formula: FoundationFormulaRuntime,
}
struct FinishConstFormulaParent {
    outputs: FinalOutputBorrows,
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
    categories: CategoryLeaves,
    ticket_bytes_some: Option<usize>,
    formula_return: Option<usize>,
    insert_receiver: &'static mut Option<SwiftCleanupInvariant>,
    insert_argument: SwiftCleanupInvariant,
    insert_return: &'static mut SwiftCleanupInvariant,
    clock: ClockLeaf,
    now: Instant,
}
#[test]
fn independent_final_accounting_shapes(){
println!("layout FinalOutputBorrows {} {}",size_of::<FinalOutputBorrows>(),align_of::<FinalOutputBorrows>());
println!("field FinalOutputBorrows outcome {} {} {}",size_of::<&'static mut Option<SwiftRunFailure>>(),align_of::<&'static mut Option<SwiftRunFailure>>(),offset_of!(FinalOutputBorrows,outcome));
println!("field FinalOutputBorrows usage {} {} {}",size_of::<&'static mut Option<SwiftRunUsage>>(),align_of::<&'static mut Option<SwiftRunUsage>>(),offset_of!(FinalOutputBorrows,usage));
println!("layout ClockLeaf {} {}",size_of::<ClockLeaf>(),align_of::<ClockLeaf>());
println!("field ClockLeaf usage_receiver {} {} {}",size_of::<&'static RuntimeControl>(),align_of::<&'static RuntimeControl>(),offset_of!(ClockLeaf,usage_receiver));
println!("field ClockLeaf usage_now {} {} {}",size_of::<Instant>(),align_of::<Instant>(),offset_of!(ClockLeaf,usage_now));
println!("field ClockLeaf elapsed_receiver {} {} {}",size_of::<&'static Instant>(),align_of::<&'static Instant>(),offset_of!(ClockLeaf,elapsed_receiver));
println!("field ClockLeaf elapsed_earlier {} {} {}",size_of::<Instant>(),align_of::<Instant>(),offset_of!(ClockLeaf,elapsed_earlier));
println!("field ClockLeaf elapsed_duration {} {} {}",size_of::<Duration>(),align_of::<Duration>(),offset_of!(ClockLeaf,elapsed_duration));
println!("field ClockLeaf overshoot_receiver {} {} {}",size_of::<&'static Instant>(),align_of::<&'static Instant>(),offset_of!(ClockLeaf,overshoot_receiver));
println!("field ClockLeaf overshoot_earlier {} {} {}",size_of::<Instant>(),align_of::<Instant>(),offset_of!(ClockLeaf,overshoot_earlier));
println!("field ClockLeaf overshoot_duration {} {} {}",size_of::<Duration>(),align_of::<Duration>(),offset_of!(ClockLeaf,overshoot_duration));
println!("field ClockLeaf micros_duration {} {} {}",size_of::<Duration>(),align_of::<Duration>(),offset_of!(ClockLeaf,micros_duration));
println!("field ClockLeaf as_micros_receiver {} {} {}",size_of::<&'static Duration>(),align_of::<&'static Duration>(),offset_of!(ClockLeaf,as_micros_receiver));
println!("field ClockLeaf micros_u128 {} {} {}",size_of::<u128>(),align_of::<u128>(),offset_of!(ClockLeaf,micros_u128));
println!("field ClockLeaf try_from_input {} {} {}",size_of::<u128>(),align_of::<u128>(),offset_of!(ClockLeaf,try_from_input));
println!("field ClockLeaf try_from_output {} {} {}",size_of::<Result<u64, std::num::TryFromIntError>>(),align_of::<Result<u64, std::num::TryFromIntError>>(),offset_of!(ClockLeaf,try_from_output));
println!("field ClockLeaf unwrap_input {} {} {}",size_of::<Result<u64, std::num::TryFromIntError>>(),align_of::<Result<u64, std::num::TryFromIntError>>(),offset_of!(ClockLeaf,unwrap_input));
println!("field ClockLeaf unwrap_default {} {} {}",size_of::<u64>(),align_of::<u64>(),offset_of!(ClockLeaf,unwrap_default));
println!("field ClockLeaf micros_return {} {} {}",size_of::<u64>(),align_of::<u64>(),offset_of!(ClockLeaf,micros_return));
println!("field ClockLeaf elapsed_return {} {} {}",size_of::<u64>(),align_of::<u64>(),offset_of!(ClockLeaf,elapsed_return));
println!("field ClockLeaf overshoot_return {} {} {}",size_of::<u64>(),align_of::<u64>(),offset_of!(ClockLeaf,overshoot_return));
println!("layout FaultLeaf {} {}",size_of::<FaultLeaf>(),align_of::<FaultLeaf>());
println!("field FaultLeaf cleanup_receiver {} {} {}",size_of::<&'static mut RuntimeControl>(),align_of::<&'static mut RuntimeControl>(),offset_of!(FaultLeaf,cleanup_receiver));
println!("field FaultLeaf invariant {} {} {}",size_of::<SwiftCleanupInvariant>(),align_of::<SwiftCleanupInvariant>(),offset_of!(FaultLeaf,invariant));
println!("field FaultLeaf code {} {} {}",size_of::<&'static str>(),align_of::<&'static str>(),offset_of!(FaultLeaf,code));
println!("field FaultLeaf insert_receiver {} {} {}",size_of::<&'static mut Option<SwiftCleanupInvariant>>(),align_of::<&'static mut Option<SwiftCleanupInvariant>>(),offset_of!(FaultLeaf,insert_receiver));
println!("field FaultLeaf insert_argument {} {} {}",size_of::<SwiftCleanupInvariant>(),align_of::<SwiftCleanupInvariant>(),offset_of!(FaultLeaf,insert_argument));
println!("field FaultLeaf insert_result {} {} {}",size_of::<&'static mut SwiftCleanupInvariant>(),align_of::<&'static mut SwiftCleanupInvariant>(),offset_of!(FaultLeaf,insert_result));
println!("field FaultLeaf cursor_source {} {} {}",size_of::<Cursor>(),align_of::<Cursor>(),offset_of!(FaultLeaf,cursor_source));
println!("field FaultLeaf fault_kind {} {} {}",size_of::<SwiftRunFailureKind>(),align_of::<SwiftRunFailureKind>(),offset_of!(FaultLeaf,fault_kind));
println!("field FaultLeaf fault_code {} {} {}",size_of::<&'static str>(),align_of::<&'static str>(),offset_of!(FaultLeaf,fault_code));
println!("field FaultLeaf fault_source {} {} {}",size_of::<Fault>(),align_of::<Fault>(),offset_of!(FaultLeaf,fault_source));
println!("field FaultLeaf fail_receiver {} {} {}",size_of::<&'static mut RuntimeControl>(),align_of::<&'static mut RuntimeControl>(),offset_of!(FaultLeaf,fail_receiver));
println!("field FaultLeaf cursor_transfer {} {} {}",size_of::<Cursor>(),align_of::<Cursor>(),offset_of!(FaultLeaf,cursor_transfer));
println!("field FaultLeaf fault_transfer {} {} {}",size_of::<Fault>(),align_of::<Fault>(),offset_of!(FaultLeaf,fault_transfer));
println!("layout CategoryLeaves {} {}",size_of::<CategoryLeaves>(),align_of::<CategoryLeaves>());
println!("field CategoryLeaves category_receiver {} {} {}",size_of::<&'static SwiftReservations>(),align_of::<&'static SwiftReservations>(),offset_of!(CategoryLeaves,category_receiver));
println!("field CategoryLeaves category_argument {} {} {}",size_of::<SwiftReservationCategory>(),align_of::<SwiftReservationCategory>(),offset_of!(CategoryLeaves,category_argument));
println!("field CategoryLeaves category_return {} {} {}",size_of::<&'static SwiftReservationUsage>(),align_of::<&'static SwiftReservationUsage>(),offset_of!(CategoryLeaves,category_return));
println!("field CategoryLeaves category_mut_receiver {} {} {}",size_of::<&'static mut SwiftReservations>(),align_of::<&'static mut SwiftReservations>(),offset_of!(CategoryLeaves,category_mut_receiver));
println!("field CategoryLeaves category_mut_argument {} {} {}",size_of::<SwiftReservationCategory>(),align_of::<SwiftReservationCategory>(),offset_of!(CategoryLeaves,category_mut_argument));
println!("field CategoryLeaves category_mut_return {} {} {}",size_of::<&'static mut SwiftReservationUsage>(),align_of::<&'static mut SwiftReservationUsage>(),offset_of!(CategoryLeaves,category_mut_return));
println!("layout RefundParent {} {}",size_of::<RefundParent>(),align_of::<RefundParent>());
println!("field RefundParent outputs {} {} {}",size_of::<FinalOutputBorrows>(),align_of::<FinalOutputBorrows>(),offset_of!(RefundParent,outputs));
println!("field RefundParent header_take_receiver {} {} {}",size_of::<&'static mut Option<ReservationTicket>>(),align_of::<&'static mut Option<ReservationTicket>>(),offset_of!(RefundParent,header_take_receiver));
println!("field RefundParent drop_receiver {} {} {}",size_of::<&'static mut RuntimeControl>(),align_of::<&'static mut RuntimeControl>(),offset_of!(RefundParent,drop_receiver));
println!("field RefundParent refund_receiver {} {} {}",size_of::<&'static mut RuntimeControl>(),align_of::<&'static mut RuntimeControl>(),offset_of!(RefundParent,refund_receiver));
println!("field RefundParent category {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(RefundParent,category));
println!("field RefundParent combined {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(RefundParent,combined));
println!("field RefundParent count {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(RefundParent,count));
println!("field RefundParent option_match {} {} {}",size_of::<(Option<usize>, Option<usize>, Option<usize>)>(),align_of::<(Option<usize>, Option<usize>, Option<usize>)>(),offset_of!(RefundParent,option_match));
println!("field RefundParent category_pattern {} {} {}",size_of::<usize>(),align_of::<usize>(),offset_of!(RefundParent,category_pattern));
println!("field RefundParent combined_pattern {} {} {}",size_of::<usize>(),align_of::<usize>(),offset_of!(RefundParent,combined_pattern));
println!("field RefundParent count_pattern {} {} {}",size_of::<usize>(),align_of::<usize>(),offset_of!(RefundParent,count_pattern));
println!("field RefundParent categories {} {} {}",size_of::<CategoryLeaves>(),align_of::<CategoryLeaves>(),offset_of!(RefundParent,categories));
println!("field RefundParent fault {} {} {}",size_of::<FaultLeaf>(),align_of::<FaultLeaf>(),offset_of!(RefundParent,fault));
println!("field RefundParent clock {} {} {}",size_of::<ClockLeaf>(),align_of::<ClockLeaf>(),offset_of!(RefundParent,clock));
println!("layout RecordParent {} {}",size_of::<RecordParent>(),align_of::<RecordParent>());
println!("field RecordParent outputs {} {} {}",size_of::<FinalOutputBorrows>(),align_of::<FinalOutputBorrows>(),offset_of!(RecordParent,outputs));
println!("field RecordParent record_receiver {} {} {}",size_of::<&'static mut RuntimeControl>(),align_of::<&'static mut RuntimeControl>(),offset_of!(RecordParent,record_receiver));
println!("field RecordParent failure_option_receiver {} {} {}",size_of::<&'static mut Option<SwiftRunFailure>>(),align_of::<&'static mut Option<SwiftRunFailure>>(),offset_of!(RecordParent,failure_option_receiver));
println!("field RecordParent failure_pattern {} {} {}",size_of::<&'static mut SwiftRunFailure>(),align_of::<&'static mut SwiftRunFailure>(),offset_of!(RecordParent,failure_pattern));
println!("field RecordParent clock {} {} {}",size_of::<ClockLeaf>(),align_of::<ClockLeaf>(),offset_of!(RecordParent,clock));
println!("layout FoundationFormulaRuntime {} {}",size_of::<FoundationFormulaRuntime>(),align_of::<FoundationFormulaRuntime>());
println!("field FoundationFormulaRuntime items {} {} {}",size_of::<[(usize,usize);7]>(),align_of::<[(usize,usize);7]>(),offset_of!(FoundationFormulaRuntime,items));
println!("field FoundationFormulaRuntime iterator {} {} {}",size_of::<std::array::IntoIter<(usize,usize),7>>(),align_of::<std::array::IntoIter<(usize,usize),7>>(),offset_of!(FoundationFormulaRuntime,iterator));
println!("field FoundationFormulaRuntime try_fold_receiver {} {} {}",size_of::<&'static mut std::array::IntoIter<(usize,usize),7>>(),align_of::<&'static mut std::array::IntoIter<(usize,usize),7>>(),offset_of!(FoundationFormulaRuntime,try_fold_receiver));
println!("field FoundationFormulaRuntime sum {} {} {}",size_of::<usize>(),align_of::<usize>(),offset_of!(FoundationFormulaRuntime,sum));
println!("field FoundationFormulaRuntime pair {} {} {}",size_of::<(usize,usize)>(),align_of::<(usize,usize)>(),offset_of!(FoundationFormulaRuntime,pair));
println!("field FoundationFormulaRuntime count {} {} {}",size_of::<usize>(),align_of::<usize>(),offset_of!(FoundationFormulaRuntime,count));
println!("field FoundationFormulaRuntime bytes {} {} {}",size_of::<usize>(),align_of::<usize>(),offset_of!(FoundationFormulaRuntime,bytes));
println!("field FoundationFormulaRuntime product {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(FoundationFormulaRuntime,product));
println!("field FoundationFormulaRuntime product_value {} {} {}",size_of::<usize>(),align_of::<usize>(),offset_of!(FoundationFormulaRuntime,product_value));
println!("field FoundationFormulaRuntime next {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(FoundationFormulaRuntime,next));
println!("field FoundationFormulaRuntime returned {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(FoundationFormulaRuntime,returned));
println!("layout FinishParent {} {}",size_of::<FinishParent>(),align_of::<FinishParent>());
println!("field FinishParent outputs {} {} {}",size_of::<FinalOutputBorrows>(),align_of::<FinalOutputBorrows>(),offset_of!(FinishParent,outputs));
println!("field FinishParent started {} {} {}",size_of::<Instant>(),align_of::<Instant>(),offset_of!(FinishParent,started));
println!("field FinishParent deadline {} {} {}",size_of::<Instant>(),align_of::<Instant>(),offset_of!(FinishParent,deadline));
println!("field FinishParent control_take_receiver {} {} {}",size_of::<&'static mut Option<ReservationTicket>>(),align_of::<&'static mut Option<ReservationTicket>>(),offset_of!(FinishParent,control_take_receiver));
println!("field FinishParent cancel_take_receiver {} {} {}",size_of::<&'static mut Option<ReservationTicket>>(),align_of::<&'static mut Option<ReservationTicket>>(),offset_of!(FinishParent,cancel_take_receiver));
println!("field FinishParent construction_take_receiver {} {} {}",size_of::<&'static mut Option<ReservationTicket>>(),align_of::<&'static mut Option<ReservationTicket>>(),offset_of!(FinishParent,construction_take_receiver));
println!("field FinishParent array {} {} {}",size_of::<[Option<ReservationTicket>;3]>(),align_of::<[Option<ReservationTicket>;3]>(),offset_of!(FinishParent,array));
println!("field FinishParent into_tickets {} {} {}",size_of::<std::array::IntoIter<Option<ReservationTicket>,3>>(),align_of::<std::array::IntoIter<Option<ReservationTicket>,3>>(),offset_of!(FinishParent,into_tickets));
println!("field FinishParent flatten_tickets {} {} {}",size_of::<std::iter::Flatten<std::array::IntoIter<Option<ReservationTicket>,3>>>(),align_of::<std::iter::Flatten<std::array::IntoIter<Option<ReservationTicket>,3>>>(),offset_of!(FinishParent,flatten_tickets));
println!("field FinishParent flatten_receiver {} {} {}",size_of::<&'static mut std::iter::Flatten<std::array::IntoIter<Option<ReservationTicket>,3>>>(),align_of::<&'static mut std::iter::Flatten<std::array::IntoIter<Option<ReservationTicket>,3>>>(),offset_of!(FinishParent,flatten_receiver));
println!("field FinishParent iterator_next {} {} {}",size_of::<Option<ReservationTicket>>(),align_of::<Option<ReservationTicket>>(),offset_of!(FinishParent,iterator_next));
println!("field FinishParent category {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(FinishParent,category));
println!("field FinishParent combined {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(FinishParent,combined));
println!("field FinishParent count {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(FinishParent,count));
println!("field FinishParent option_match {} {} {}",size_of::<(Option<usize>,Option<usize>,Option<usize>)>(),align_of::<(Option<usize>,Option<usize>,Option<usize>)>(),offset_of!(FinishParent,option_match));
println!("field FinishParent category_pattern {} {} {}",size_of::<usize>(),align_of::<usize>(),offset_of!(FinishParent,category_pattern));
println!("field FinishParent combined_pattern {} {} {}",size_of::<usize>(),align_of::<usize>(),offset_of!(FinishParent,combined_pattern));
println!("field FinishParent count_pattern {} {} {}",size_of::<usize>(),align_of::<usize>(),offset_of!(FinishParent,count_pattern));
println!("field FinishParent categories {} {} {}",size_of::<CategoryLeaves>(),align_of::<CategoryLeaves>(),offset_of!(FinishParent,categories));
println!("field FinishParent ticket_bytes_some {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(FinishParent,ticket_bytes_some));
println!("field FinishParent formula_return {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(FinishParent,formula_return));
println!("field FinishParent insert_receiver {} {} {}",size_of::<&'static mut Option<SwiftCleanupInvariant>>(),align_of::<&'static mut Option<SwiftCleanupInvariant>>(),offset_of!(FinishParent,insert_receiver));
println!("field FinishParent insert_argument {} {} {}",size_of::<SwiftCleanupInvariant>(),align_of::<SwiftCleanupInvariant>(),offset_of!(FinishParent,insert_argument));
println!("field FinishParent insert_return {} {} {}",size_of::<&'static mut SwiftCleanupInvariant>(),align_of::<&'static mut SwiftCleanupInvariant>(),offset_of!(FinishParent,insert_return));
println!("field FinishParent clock {} {} {}",size_of::<ClockLeaf>(),align_of::<ClockLeaf>(),offset_of!(FinishParent,clock));
println!("field FinishParent now {} {} {}",size_of::<Instant>(),align_of::<Instant>(),offset_of!(FinishParent,now));
println!("field FinishParent formula {} {} {}",size_of::<FoundationFormulaRuntime>(),align_of::<FoundationFormulaRuntime>(),offset_of!(FinishParent,formula));
println!("layout FinishConstFormulaParent {} {}",size_of::<FinishConstFormulaParent>(),align_of::<FinishConstFormulaParent>());
println!("field FinishConstFormulaParent outputs {} {} {}",size_of::<FinalOutputBorrows>(),align_of::<FinalOutputBorrows>(),offset_of!(FinishConstFormulaParent,outputs));
println!("field FinishConstFormulaParent started {} {} {}",size_of::<Instant>(),align_of::<Instant>(),offset_of!(FinishConstFormulaParent,started));
println!("field FinishConstFormulaParent deadline {} {} {}",size_of::<Instant>(),align_of::<Instant>(),offset_of!(FinishConstFormulaParent,deadline));
println!("field FinishConstFormulaParent control_take_receiver {} {} {}",size_of::<&'static mut Option<ReservationTicket>>(),align_of::<&'static mut Option<ReservationTicket>>(),offset_of!(FinishConstFormulaParent,control_take_receiver));
println!("field FinishConstFormulaParent cancel_take_receiver {} {} {}",size_of::<&'static mut Option<ReservationTicket>>(),align_of::<&'static mut Option<ReservationTicket>>(),offset_of!(FinishConstFormulaParent,cancel_take_receiver));
println!("field FinishConstFormulaParent construction_take_receiver {} {} {}",size_of::<&'static mut Option<ReservationTicket>>(),align_of::<&'static mut Option<ReservationTicket>>(),offset_of!(FinishConstFormulaParent,construction_take_receiver));
println!("field FinishConstFormulaParent array {} {} {}",size_of::<[Option<ReservationTicket>;3]>(),align_of::<[Option<ReservationTicket>;3]>(),offset_of!(FinishConstFormulaParent,array));
println!("field FinishConstFormulaParent into_tickets {} {} {}",size_of::<std::array::IntoIter<Option<ReservationTicket>,3>>(),align_of::<std::array::IntoIter<Option<ReservationTicket>,3>>(),offset_of!(FinishConstFormulaParent,into_tickets));
println!("field FinishConstFormulaParent flatten_tickets {} {} {}",size_of::<std::iter::Flatten<std::array::IntoIter<Option<ReservationTicket>,3>>>(),align_of::<std::iter::Flatten<std::array::IntoIter<Option<ReservationTicket>,3>>>(),offset_of!(FinishConstFormulaParent,flatten_tickets));
println!("field FinishConstFormulaParent flatten_receiver {} {} {}",size_of::<&'static mut std::iter::Flatten<std::array::IntoIter<Option<ReservationTicket>,3>>>(),align_of::<&'static mut std::iter::Flatten<std::array::IntoIter<Option<ReservationTicket>,3>>>(),offset_of!(FinishConstFormulaParent,flatten_receiver));
println!("field FinishConstFormulaParent iterator_next {} {} {}",size_of::<Option<ReservationTicket>>(),align_of::<Option<ReservationTicket>>(),offset_of!(FinishConstFormulaParent,iterator_next));
println!("field FinishConstFormulaParent category {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(FinishConstFormulaParent,category));
println!("field FinishConstFormulaParent combined {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(FinishConstFormulaParent,combined));
println!("field FinishConstFormulaParent count {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(FinishConstFormulaParent,count));
println!("field FinishConstFormulaParent option_match {} {} {}",size_of::<(Option<usize>,Option<usize>,Option<usize>)>(),align_of::<(Option<usize>,Option<usize>,Option<usize>)>(),offset_of!(FinishConstFormulaParent,option_match));
println!("field FinishConstFormulaParent category_pattern {} {} {}",size_of::<usize>(),align_of::<usize>(),offset_of!(FinishConstFormulaParent,category_pattern));
println!("field FinishConstFormulaParent combined_pattern {} {} {}",size_of::<usize>(),align_of::<usize>(),offset_of!(FinishConstFormulaParent,combined_pattern));
println!("field FinishConstFormulaParent count_pattern {} {} {}",size_of::<usize>(),align_of::<usize>(),offset_of!(FinishConstFormulaParent,count_pattern));
println!("field FinishConstFormulaParent categories {} {} {}",size_of::<CategoryLeaves>(),align_of::<CategoryLeaves>(),offset_of!(FinishConstFormulaParent,categories));
println!("field FinishConstFormulaParent ticket_bytes_some {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(FinishConstFormulaParent,ticket_bytes_some));
println!("field FinishConstFormulaParent formula_return {} {} {}",size_of::<Option<usize>>(),align_of::<Option<usize>>(),offset_of!(FinishConstFormulaParent,formula_return));
println!("field FinishConstFormulaParent insert_receiver {} {} {}",size_of::<&'static mut Option<SwiftCleanupInvariant>>(),align_of::<&'static mut Option<SwiftCleanupInvariant>>(),offset_of!(FinishConstFormulaParent,insert_receiver));
println!("field FinishConstFormulaParent insert_argument {} {} {}",size_of::<SwiftCleanupInvariant>(),align_of::<SwiftCleanupInvariant>(),offset_of!(FinishConstFormulaParent,insert_argument));
println!("field FinishConstFormulaParent insert_return {} {} {}",size_of::<&'static mut SwiftCleanupInvariant>(),align_of::<&'static mut SwiftCleanupInvariant>(),offset_of!(FinishConstFormulaParent,insert_return));
println!("field FinishConstFormulaParent clock {} {} {}",size_of::<ClockLeaf>(),align_of::<ClockLeaf>(),offset_of!(FinishConstFormulaParent,clock));
println!("field FinishConstFormulaParent now {} {} {}",size_of::<Instant>(),align_of::<Instant>(),offset_of!(FinishConstFormulaParent,now));
println!("shape SwiftRunFailure {} {}",size_of::<SwiftRunFailure>(),align_of::<SwiftRunFailure>());
println!("shape Option<SwiftRunFailure> {} {}",size_of::<Option<SwiftRunFailure>>(),align_of::<Option<SwiftRunFailure>>());
println!("shape Result<(),SwiftRunFailure> {} {}",size_of::<Result<(),SwiftRunFailure>>(),align_of::<Result<(),SwiftRunFailure>>());
println!("shape SwiftRunUsage {} {}",size_of::<SwiftRunUsage>(),align_of::<SwiftRunUsage>());
println!("shape Option<SwiftRunUsage> {} {}",size_of::<Option<SwiftRunUsage>>(),align_of::<Option<SwiftRunUsage>>());
println!("shape ReservationTicket {} {}",size_of::<ReservationTicket>(),align_of::<ReservationTicket>());
println!("shape Option<ReservationTicket> {} {}",size_of::<Option<ReservationTicket>>(),align_of::<Option<ReservationTicket>>());
println!("shape Option<Option<ReservationTicket>> {} {}",size_of::<Option<Option<ReservationTicket>>>(),align_of::<Option<Option<ReservationTicket>>>());
println!("shape Option<WasiUsage> {} {}",size_of::<Option<WasiUsage>>(),align_of::<Option<WasiUsage>>());
println!("shape RuntimeControl {} {}",size_of::<RuntimeControl>(),align_of::<RuntimeControl>());
assert_eq!(size_of::<SwiftRunFailure>(),size_of::<Option<SwiftRunFailure>>());
assert_eq!(size_of::<SwiftRunUsage>(),size_of::<Option<SwiftRunUsage>>());
assert_eq!(size_of::<ReservationTicket>(),size_of::<Option<ReservationTicket>>());
}
