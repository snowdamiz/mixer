// Derived-only metadata probe for the root-owned pending foundation correction.
// These are actual std/toolchain shapes, not a new product boundary allowance.
pub fn boundary_shapes() {
    type Tickets = [Option<ReservationTicket>; 3];
    type IntoTickets = std::array::IntoIter<Option<ReservationTicket>, 3>;
    type FlatTickets = std::iter::Flatten<IntoTickets>;
    macro_rules! row { ($t:ty) => { println!("layout {} {} {}",stringify!($t),size_of::<$t>(),align_of::<$t>()); }; }
    row!(&'static mut Option<SwiftRunFailure>);
    row!(&'static mut Option<SwiftRunUsage>);
    row!(&'static mut RuntimeControl);
    row!(&'static RuntimeControl);
    row!(&'static mut SwiftReservations);
    row!(&'static SwiftReservations);
    row!(&'static mut SwiftReservationUsage);
    row!(Option<&'static mut SwiftRunFailure>);
    row!(SwiftCleanupInvariant);
    row!(SwiftReservationCategory);
    row!(&'static str);
    row!(usize); row!(u64); row!(u128);
    row!(Option<usize>);
    row!(std::time::Instant);
    row!(std::time::Duration);
    row!(Result<u64, std::num::TryFromIntError>);
    row!(Tickets); row!(IntoTickets); row!(FlatTickets);
    row!(Option<Option<ReservationTicket>>);
    row!(Result<usize,SwiftRunFailure>);
    row!(SwiftMode); row!(FrozenMode); row!(FrozenOperation<'static>);
    row!(ExecutionParts<'static,FrozenMode>); row!(LayoutTerm);
    // Selected disjoint proposal: every field below is additional to the
    // foundation's four diagnostic/six ticket/six observation classes. This
    // probe measures the proposal; it does not admit it in RuntimeControl.
    #[allow(dead_code)]
    struct RefundSupplement {
        outcome: &'static mut Option<SwiftRunFailure>,
        usage: &'static mut Option<SwiftRunUsage>,
        drop_receiver: &'static mut RuntimeControl,
        refund_receiver: &'static mut RuntimeControl,
        cleanup_fault_receiver: &'static mut RuntimeControl,
        fail_receiver: &'static mut RuntimeControl,
        usage_receiver: &'static RuntimeControl,
        invariant: SwiftCleanupInvariant,
        code: &'static str,
        cursor: Cursor,
        fault: Fault,
        usage_now: std::time::Instant,
        micros_duration: std::time::Duration,
        checked_category: Option<usize>,
        checked_combined: Option<usize>,
        checked_count: Option<usize>,
    }
    #[allow(dead_code)]
    struct FinishSupplement {
        outcome: &'static mut Option<SwiftRunFailure>,
        usage: &'static mut Option<SwiftRunUsage>,
        started: std::time::Instant,
        deadline: std::time::Instant,
        tickets: FlatTickets,
        checked_category: Option<usize>,
        checked_combined: Option<usize>,
        checked_count: Option<usize>,
        category: usize,
        combined: usize,
        count: usize,
        reservation_receiver: &'static mut SwiftReservations,
        reservation_return: &'static mut SwiftReservationUsage,
        category_parameter: SwiftReservationCategory,
    }
    row!(RefundSupplement); row!(FinishSupplement);
    macro_rules! fields { ($t:ty; $($f:ident),+) => {$({ println!("offset {} {} {}",stringify!($t),stringify!($f),offset_of!($t,$f)); })+}; }
    fields!(RefundSupplement;outcome,usage,drop_receiver,refund_receiver,cleanup_fault_receiver,fail_receiver,usage_receiver,invariant,code,cursor,fault,usage_now,micros_duration,checked_category,checked_combined,checked_count);
    fields!(FinishSupplement;outcome,usage,started,deadline,tickets,checked_category,checked_combined,checked_count,category,combined,count,reservation_receiver,reservation_return,category_parameter);
    fields!(FrozenOperation<'static>;budget,cancellation,usage,failure,function,offset);
    fields!(ExecutionParts<'static,FrozenMode>;cache,memory,table,globals,values,controls,frames);
    fields!(LayoutTerm;phase,binding,shape,count,bytes);
}
