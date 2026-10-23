// Independent supplemental corrupted-ledger branches; no guest executor route.
#[test]
fn independent_root_finish_checks_combined_and_ticket_underflow() {
    for broken_count in [false, true] {
        let (mut control, adopted) = adopt(SwiftRunBudget::default());
        control.drop_proof(adopted).unwrap();
        let before = control.usage(None);
        assert_eq!(before.reservations.live_tickets, 3);
        if broken_count {
            control.reservations.live_tickets = 0;
        } else {
            control.reservations.combined.current = 0;
        }
        let (after, stats) = super::super::allocation_tests::measure(|| {
            control.finish_owned_cleanup(None)
        });
        no_allocations(stats);
        assert_eq!(after.cleanup_invariant, Some(SwiftCleanupInvariant::ReservationUnderflow));
        // Every attempted refund rejects. Intact category charges are retained;
        // damaged counters are never fabricated into an apparently valid pass.
        assert_eq!(after.reservations.construction.current, before.reservations.construction.current);
        assert_eq!(after.reservations.shared.current, before.reservations.shared.current);
        if broken_count {
            assert_eq!(after.reservations.combined.current, before.reservations.combined.current);
            assert_eq!(after.reservations.live_tickets, 0);
        } else {
            assert_eq!(after.reservations.combined.current, 0);
            assert_eq!(after.reservations.live_tickets, 3);
        }
        println!("independent finish checked-counter branch broken_count={broken_count} allocations={}",stats.allocations);
    }
}
