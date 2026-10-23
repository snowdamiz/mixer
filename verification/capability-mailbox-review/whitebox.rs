//! Review-only injection of otherwise unreachable private exhaustion states.
use super::*;
use std::sync::Arc;

#[test]
fn concurrent_owner_counter_boundary_never_issues_zero_or_wraps_or_duplicates() {
    const ISSUED: u64 = 4095;
    let counter = Arc::new(AtomicU64::new(u64::MAX - ISSUED));
    let mut all = std::thread::scope(|scope| {
        let mut handles = vec![];
        for _ in 0..16 {
            let counter = Arc::clone(&counter);
            handles.push(scope.spawn(move || {
                let mut issued = vec![];
                loop {
                    match issue_owner(&counter) {
                        Ok(id) => issued.push(id),
                        Err(Error::IdentifierExhausted) => break,
                        other => panic!("unexpected owner result {other:?}"),
                    }
                }
                issued
            }));
        }
        handles
            .into_iter()
            .flat_map(|h| h.join().unwrap())
            .collect::<Vec<_>>()
    });
    all.sort_unstable();
    assert_eq!(all.len(), ISSUED as usize);
    assert_eq!(all, ((u64::MAX - ISSUED)..u64::MAX).collect::<Vec<_>>());
    assert_eq!(counter.load(Ordering::Relaxed), u64::MAX);
    assert_eq!(issue_owner(&counter), Err(Error::IdentifierExhausted));
    println!("independent owner exhaustion race: 16 contenders issued all 4095 remaining identities exactly once");
}

#[test]
fn every_slot_reaches_retirement_without_replay_or_capacity_reappearing() {
    let m = Mailbox::new(Limits::default()).unwrap();
    {
        let mut s = m.state.lock().unwrap();
        for slot in &mut s.slots {
            slot.generation = u32::MAX - 1;
        }
        s.last_turn = u64::MAX - 1;
    }
    let t = m.begin_turn().unwrap();
    let mut obsolete = vec![];
    for slot in 1..=8u64 {
        for generation in [u32::MAX - 1, u32::MAX] {
            let id = m.enqueue(t, Operation::Get, b"retire").unwrap();
            assert_eq!(id.token_bits(), ((generation as u64) << 32) | slot);
            obsolete.push(id);
            assert_eq!(
                m.poll(id, &mut []),
                Ok(Poll::Failure(FailureCode::Unavailable))
            );
            for old in &obsolete {
                assert_eq!(m.cancel(*old), Err(Error::StaleRequest));
            }
        }
        let u = m.usage().unwrap();
        assert_eq!(u.retired_slots, slot as usize);
        assert_eq!((u.outstanding_requests, u.reserved_bytes), (0, 0));
    }
    assert_eq!(
        m.enqueue(t, Operation::Get, b"no wrap"),
        Err(Error::QuotaExceeded)
    );
    m.finish_turn(t, TurnOutcome::Success).unwrap();
    assert_eq!(m.begin_turn(), Err(Error::IdentifierExhausted));
    assert_eq!(m.finish_turn(t, TurnOutcome::Trap), Err(Error::InvalidTurn));
    assert!(!m.usage().unwrap().closed);
    println!("independent combined boundary: all eight slots retired after 16 final generations; final turn exhausted; stale trap cannot close owner");
}

#[test]
fn all_malformed_token_shapes_and_wrong_operation_leases_leave_storage_unchanged() {
    let m = Mailbox::new(Limits::default()).unwrap();
    m.enable().unwrap();
    let t = m.begin_turn().unwrap();
    let id = m.enqueue(t, Operation::Put, b"protected").unwrap();
    m.finish_turn(t, TurnOutcome::Success).unwrap();
    let Take::Call { lease, .. } = m.take(&mut [0; 9]).unwrap() else {
        panic!()
    };
    let before = m.usage().unwrap();
    for generation in [0, 1, 2, u32::MAX] {
        for slot in [0, 1, 8, 9, u32::MAX] {
            let bits = ((generation as u64) << 32) | slot as u64;
            if bits == id.bits {
                continue;
            }
            let forged = RequestId {
                owner: m.owner,
                bits,
            };
            let mut output = [0x71; 16];
            assert_eq!(m.poll(forged, &mut output), Err(Error::StaleRequest));
            assert_eq!(output, [0x71; 16]);
            assert_eq!(m.cancel(forged), Err(Error::StaleRequest));
        }
    }
    for operation in [Operation::HttpRequest, Operation::Get, Operation::Delete] {
        let altered = NativeLease { operation, ..lease };
        assert_eq!(m.post(&altered, b"alien"), Err(Error::StaleRequest));
        assert_eq!(m.ack_exit(&altered), Err(Error::StaleRequest));
        assert_eq!(m.limit_deadline(&altered, 1), Err(Error::StaleRequest));
    }
    assert_eq!(m.usage().unwrap(), before);
    m.close().unwrap();
    m.ack_exit(&lease).unwrap();
}
