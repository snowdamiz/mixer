use super::*;
use crate::{Profile, Value};
mod fixture;
fn session() -> CapabilitySession {
    let limits = Limits {
        profile: Profile::TableMemoryV3,
        ..Limits::default()
    };
    let mut guest = CapabilityGuest::new(
        &fixture::wasm(),
        limits.clone(),
        mb::Limits::default(),
        crate::experimental_capability_guest::GuestLimits::default(),
        "start",
    )
    .unwrap();
    guest.startup().unwrap();
    guest.enable_effects().unwrap();
    CapabilitySession::new(guest, limits)
}
fn enqueue(s: &CapabilitySession) -> u64 {
    let mut g = s.guest().unwrap();
    assert_eq!(
        g.invoke("get", &[Value::I32(0), Value::I32(4), Value::I32(32)])
            .unwrap(),
        Some(Value::I32(0))
    );
    u64::from_le_bytes(g.memory()[32..40].try_into().unwrap())
}
fn take(s: &CapabilitySession) -> u64 {
    let transaction = s.take(&mut [0; 4]).unwrap();
    assert_eq!(transaction.message.kind, 1);
    let token = transaction.message.token;
    transaction.commit();
    token
}
fn poll(s: &CapabilitySession, token: u64) {
    let mut g = s.guest().unwrap();
    assert_eq!(
        g.invoke(
            "poll",
            &[
                Value::I64(token as i64),
                Value::I32(256),
                Value::I32(512),
                Value::I32(48)
            ]
        )
        .unwrap(),
        Some(Value::I32(0))
    );
}
#[test]
fn ledger_counts_only_call_and_first_successful_actual_exit() {
    let s = session();
    assert_eq!(s.take(&mut []).unwrap().message.kind, 0);
    assert_eq!(s.outstanding(), 0);
    let token = enqueue(&s);
    assert_eq!(s.take(&mut []).unwrap().message.kind, 3);
    assert_eq!(s.outstanding(), 0);
    assert_eq!(take(&s), token);
    assert_eq!(s.outstanding(), 1);
    assert_eq!(s.ack_exit(token, 2).unwrap().kind, 0);
    assert_eq!(s.outstanding(), 0);
    assert_eq!(s.ack_exit(token, 2).unwrap().kind, 2);
    assert_eq!(s.outstanding(), 0);
    assert_eq!(s.post(token, 2, b"opaque").unwrap_err().status, 3);
    assert_eq!(s.limit_deadline(token, 2, 30000).unwrap_err().status, 3);
    s.guest()
        .unwrap()
        .invoke("cancel", &[Value::I64(token as i64)])
        .unwrap();
    poll(&s, token);
    assert_eq!(s.ack_exit(token, 2).unwrap_err().status, 3);
    assert!(!s.quarantined());
}
#[test]
fn normal_stale_busy_and_bounds_errors_never_quarantine() {
    let s = session();
    assert_eq!(s.post(0, 2, b"x").unwrap_err().status, 3);
    let held = s.guest().unwrap();
    {
        let _guard = s.unwind_guard();
        assert!(matches!(s.guest(), Err(Failure { status: 3, .. })));
    }
    drop(held);
    assert!(!s.quarantined());
    assert!(s.ensure_live().is_ok());
    assert_eq!(s.ack_exit(0, 2).unwrap_err().status, 3);
    assert!(!s.quarantined());
}
#[test]
fn terminal_post_and_deadline_map_to_terminal_without_acknowledging() {
    let s = session();
    let token = enqueue(&s);
    take(&s);
    assert_eq!(s.post(token, 2, b"opaque").unwrap().kind, 0);
    assert_eq!(s.post(token, 2, b"again").unwrap().kind, 1);
    let result = s.limit_deadline(token, 2, 1).unwrap();
    assert_eq!(result.kind, 1);
    assert_eq!(result.remaining_milliseconds, 0);
    assert_eq!(s.outstanding(), 1);
    s.ack_exit(token, 2).unwrap();
    assert_eq!(s.post(token, 2, b"after ack").unwrap().kind, 1);
    let narrowed = s.limit_deadline(token, 2, 1).unwrap();
    assert_eq!((narrowed.kind, narrowed.remaining_milliseconds), (1, 0));
    poll(&s, token);
    assert_eq!(s.ack_exit(token, 2).unwrap_err().status, 3);
}
#[test]
fn acknowledged_old_entry_replaced_only_after_new_mailbox_generation() {
    let s = session();
    let first = enqueue(&s);
    take(&s);
    s.post(first, 2, b"done").unwrap();
    s.ack_exit(first, 2).unwrap();
    poll(&s, first);
    let second = enqueue(&s);
    assert_eq!(second, first + (1u64 << 32));
    assert_eq!(take(&s), second);
    assert_eq!(s.outstanding(), 1);
    assert_eq!(s.ack_exit(first, 2).unwrap_err().status, 3);
    assert_eq!(s.outstanding(), 1);
    s.close_native().unwrap();
    s.ack_exit(second, 2).unwrap();
    assert!(s.reclaim_ready());
}
#[test]
fn cancel_control_is_existing_ticket_and_no_new_obligation() {
    let s = session();
    let token = enqueue(&s);
    take(&s);
    s.guest()
        .unwrap()
        .invoke("cancel", &[Value::I64(token as i64)])
        .unwrap();
    let cancel = s.take(&mut []).unwrap();
    assert_eq!(
        (
            cancel.message.kind,
            cancel.message.token,
            cancel.message.operation
        ),
        (2, token, 2)
    );
    cancel.commit();
    assert_eq!(s.outstanding(), 1);
    s.close_native().unwrap();
    assert_eq!(s.ack_exit(token, 2).unwrap().kind, 0);
    assert!(s.reclaim_ready());
}
#[test]
fn uncommitted_take_and_unwind_latches_cannot_be_cleared_by_success() {
    let s = session();
    enqueue(&s);
    let transaction = s.take(&mut [0; 4]).unwrap();
    assert_eq!(s.outstanding(), 1);
    drop(transaction);
    assert!(s.quarantined());
    assert!(!s.reclaim_ready());
    assert_eq!(s.ack_exit(1u64 << 32 | 1, 2).unwrap_err().status, 4);
    let s = session();
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let _guard = s.unwind_guard();
        panic!("original native operation unwind");
    }));
    assert!(result.is_err());
    assert!(s.quarantined());
    let mut successful = s.unwind_guard();
    successful.disarm();
    drop(successful);
    assert!(s.quarantined());
}
#[test]
fn conflicting_unacknowledged_replacement_is_terminal_invariant() {
    let s = session();
    let first = enqueue(&s);
    take(&s);
    // Simulate a broken internal native ledger while retaining the real owner-
    // bound ticket: new Call must not silently overwrite an unresolved entry.
    {
        let mut ledger = s.ledger.lock().unwrap();
        ledger.entries[0]
            .as_mut()
            .unwrap()
            .lease
            .ack_exit()
            .unwrap();
    }
    s.guest()
        .unwrap()
        .invoke("cancel", &[Value::I64(first as i64)])
        .unwrap();
    poll(&s, first);
    enqueue(&s);
    assert_eq!(s.take(&mut [0; 4]).err().unwrap().status, 4);
    assert!(s.quarantined());
    assert!(!s.reclaim_ready());
}
#[test]
fn poisoned_ledger_pins_capacity_without_fabricated_ack() {
    let s = session();
    let token = enqueue(&s);
    take(&s);
    let _ = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let _held = s.ledger.lock().unwrap();
        panic!("native ledger poison fixture");
    }));
    assert_eq!(s.ack_exit(token, 2).unwrap_err().status, 4);
    assert!(s.quarantined());
    assert_eq!(s.outstanding(), 1);
}
#[test]
fn quarantined_unpoisoned_close_success_never_clears_reclamation_latch() {
    let s = session();
    let token = enqueue(&s);
    take(&s);
    s.quarantine();
    assert!(s.close_native().is_ok());
    assert!(s.quarantined());
    assert!(!s.reclaim_ready());
    assert_eq!(s.outstanding(), 1);
    assert_eq!(s.ensure_live().unwrap_err().status, 4);
    assert_eq!(s.ack_exit(token, 2).unwrap_err().status, 4);
    assert!(!s.reclaim_ready());
}
