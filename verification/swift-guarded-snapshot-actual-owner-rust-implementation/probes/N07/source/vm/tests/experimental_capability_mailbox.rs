#![cfg(feature = "experimental-capability-mailbox")]
use mixer_vm::experimental_capability::*;
use std::sync::{Arc, Barrier};
use std::time::Duration;

fn open_mailbox() -> Mailbox {
    let mailbox = Mailbox::new(Limits::default()).unwrap();
    mailbox.enable().unwrap();
    mailbox
}
fn submit(mailbox: &Mailbox, operation: Operation, bytes: &[u8]) -> RequestId {
    let turn = mailbox.begin_turn().unwrap();
    let id = mailbox.enqueue(turn, operation, bytes).unwrap();
    assert_eq!(mailbox.finish_turn(turn, TurnOutcome::Success), Ok(None));
    id
}
fn dispatched(mailbox: &Mailbox, bytes: &[u8]) -> (RequestId, NativeLease) {
    let id = submit(mailbox, Operation::HttpRequest, bytes);
    let mut output = vec![0; bytes.len()];
    let Take::Call {
        lease,
        length,
        remaining_milliseconds,
    } = mailbox.take(&mut output).unwrap()
    else {
        panic!("missing call")
    };
    assert_eq!(
        (lease.request(), lease.operation(), length),
        (id, Operation::HttpRequest, bytes.len())
    );
    assert!((1..=MAX_TIMEOUT_MILLISECONDS).contains(&remaining_milliseconds));
    assert_eq!(output, bytes);
    (id, lease)
}

#[test]
fn unavailable_startup_and_one_way_enable_never_replay_old_requests() {
    let mailbox = Mailbox::new(Limits::default()).unwrap();
    let id = submit(&mailbox, Operation::Get, b"opaque-invalid-json");
    mailbox.enable().unwrap();
    mailbox.enable().unwrap();
    let mut untouched = [77; 32];
    assert_eq!(mailbox.take(&mut untouched), Ok(Take::None));
    assert_eq!(
        mailbox.poll(id, &mut untouched),
        Ok(Poll::Failure(FailureCode::Unavailable))
    );
    assert_eq!(untouched, [77; 32]);
    assert_eq!(mailbox.poll(id, &mut []), Err(Error::StaleRequest));
    assert_eq!(mailbox.usage().unwrap().reserved_bytes, 0);
    let (_, lease) = dispatched(&mailbox, b"new");
    mailbox
        .post(&lease, b"strict validation is outside this experiment")
        .unwrap();
}

#[test]
fn only_successful_turn_publishes_calls_and_stale_trap_cannot_kill_new_turn() {
    let mailbox = open_mailbox();
    let turn = mailbox.begin_turn().unwrap();
    assert_eq!(mailbox.begin_turn(), Err(Error::TurnActive));
    let id = mailbox.enqueue(turn, Operation::Put, b"owned").unwrap();
    let mut untouched = [55; 5];
    assert_eq!(mailbox.take(&mut untouched), Ok(Take::None));
    assert_eq!(untouched, [55; 5]);
    assert_eq!(mailbox.poll(id, &mut untouched), Ok(Poll::Pending));
    mailbox.finish_turn(turn, TurnOutcome::Success).unwrap();
    let next = mailbox.begin_turn().unwrap();
    assert_eq!(
        mailbox.finish_turn(turn, TurnOutcome::Trap),
        Err(Error::InvalidTurn)
    );
    assert_eq!(
        mailbox.enqueue(turn, Operation::Get, b"x"),
        Err(Error::InvalidTurn)
    );
    assert_eq!(mailbox.take(&mut untouched), Ok(Take::None));
    mailbox.finish_turn(next, TurnOutcome::Success).unwrap();
    assert!(matches!(
        mailbox.take(&mut untouched),
        Ok(Take::Call { .. })
    ));

    let trapped = open_mailbox();
    let turn = trapped.begin_turn().unwrap();
    let id = trapped
        .enqueue(turn, Operation::Delete, b"must never start")
        .unwrap();
    let report = trapped
        .finish_turn(turn, TurnOutcome::Trap)
        .unwrap()
        .unwrap();
    assert!(report.cancellations.iter().all(Option::is_none));
    assert_eq!(trapped.take(&mut untouched), Err(Error::SessionClosed));
    assert_eq!(trapped.poll(id, &mut untouched), Err(Error::SessionClosed));
    assert_eq!(trapped.usage().unwrap().reserved_bytes, 0);
}

#[test]
fn queued_cancellation_suppresses_io_and_controls_are_bounded_coalesced_priority() {
    let mailbox = open_mailbox();
    let turn = mailbox.begin_turn().unwrap();
    let queued = mailbox.enqueue(turn, Operation::Get, b"queued").unwrap();
    mailbox.cancel(queued).unwrap();
    assert_eq!(mailbox.cancel(queued), Err(Error::AlreadyTerminal));
    mailbox.finish_turn(turn, TurnOutcome::Success).unwrap();
    assert_eq!(mailbox.take(&mut []), Ok(Take::None));
    assert_eq!(
        mailbox.poll(queued, &mut []),
        Ok(Poll::Failure(FailureCode::Cancelled))
    );

    let (id, lease) = dispatched(&mailbox, b"native");
    let turn = mailbox.begin_turn().unwrap();
    mailbox.enqueue(turn, Operation::Put, b"next").unwrap();
    mailbox.cancel(id).unwrap();
    for _ in 0..1_000 {
        assert_eq!(mailbox.cancel(id), Err(Error::AlreadyTerminal));
    }
    assert_eq!(mailbox.take(&mut []), Ok(Take::Cancel { lease }));
    assert_eq!(mailbox.take(&mut []), Ok(Take::None));
    assert_eq!(
        mailbox.poll(id, &mut []),
        Ok(Poll::Failure(FailureCode::Cancelled))
    );
    assert_eq!(mailbox.poll(id, &mut []), Err(Error::StaleRequest));
    assert_eq!(mailbox.usage().unwrap().native_leases, 1);
    mailbox.ack_exit(&lease).unwrap();
    mailbox.finish_turn(turn, TurnOutcome::Success).unwrap();
    assert!(matches!(mailbox.take(&mut [0; 4]), Ok(Take::Call { .. })));
}

#[test]
fn polling_and_take_backpressure_are_exact_atomic_and_copied() {
    let mailbox = open_mailbox();
    let mut args = b"owned snapshot".to_vec();
    let id = submit(&mailbox, Operation::Delete, &args);
    args.fill(0);
    let mut small = [33; 13];
    assert_eq!(
        mailbox.take(&mut []),
        Ok(Take::BufferTooSmall { required: 14 })
    );
    assert_eq!(
        mailbox.take(&mut small),
        Ok(Take::BufferTooSmall { required: 14 })
    );
    assert_eq!(small, [33; 13]);
    let mut output = [66; 15];
    let Take::Call { lease, length, .. } = mailbox.take(&mut output).unwrap() else {
        panic!()
    };
    assert_eq!(length, 14);
    assert_eq!(&output[..14], b"owned snapshot");
    assert_eq!(output[14], 66);
    assert_eq!(mailbox.take(&mut []), Ok(Take::None));
    assert_eq!(mailbox.poll(id, &mut small), Ok(Poll::Pending));
    assert_eq!(small, [33; 13]);
    let mut bytes = b"immutable response".to_vec();
    mailbox.post(&lease, &bytes).unwrap();
    bytes.fill(0);
    assert_eq!(
        mailbox.post(&lease, b"replace"),
        Err(Error::AlreadyTerminal)
    );
    assert_eq!(mailbox.cancel(id), Err(Error::AlreadyTerminal));
    assert_eq!(
        mailbox.poll(id, &mut []),
        Ok(Poll::BufferTooSmall { required: 18 })
    );
    assert_eq!(
        mailbox.poll(id, &mut small),
        Ok(Poll::BufferTooSmall { required: 18 })
    );
    assert_eq!(small, [33; 13]);
    let mut output = [44; 19];
    assert_eq!(
        mailbox.poll(id, &mut output),
        Ok(Poll::Ready { length: 18 })
    );
    assert_eq!(&output[..18], b"immutable response");
    assert_eq!(output[18], 44);
    assert_eq!(mailbox.poll(id, &mut output), Err(Error::StaleRequest));
    assert_eq!(mailbox.post(&lease, b"again"), Err(Error::StaleRequest));
    let usage = mailbox.usage().unwrap();
    assert_eq!(
        (
            usage.outstanding_requests,
            usage.native_leases,
            usage.completion_bytes
        ),
        (1, 1, 0)
    );
    mailbox.ack_exit(&lease).unwrap();
    assert_eq!(mailbox.ack_exit(&lease), Err(Error::StaleRequest));
    assert_eq!(mailbox.usage().unwrap().outstanding_requests, 0);
}

#[test]
fn exact_payload_request_reservation_and_plus_one_bounds() {
    for limits in [
        Limits {
            maximum_requests: 0,
            ..Limits::default()
        },
        Limits {
            maximum_requests: MAX_REQUESTS + 1,
            ..Limits::default()
        },
        Limits {
            reservation_bytes: 0,
            ..Limits::default()
        },
        Limits {
            reservation_bytes: MAX_RESERVATION_BYTES + 1,
            ..Limits::default()
        },
        Limits {
            timeout_milliseconds: 0,
            ..Limits::default()
        },
        Limits {
            timeout_milliseconds: MAX_TIMEOUT_MILLISECONDS + 1,
            ..Limits::default()
        },
    ] {
        assert!(matches!(Mailbox::new(limits), Err(Error::InvalidLimits)));
    }
    let mailbox = open_mailbox();
    let turn = mailbox.begin_turn().unwrap();
    let bytes = vec![1; MAX_PAYLOAD_BYTES];
    let mut oversized = vec![2; MAX_PAYLOAD_BYTES + 1];
    assert_eq!(
        mailbox.enqueue(turn, Operation::Get, &[]),
        Err(Error::InvalidArguments)
    );
    assert_eq!(
        mailbox.enqueue(turn, Operation::Get, &oversized),
        Err(Error::InvalidArguments)
    );
    let mut ids = Vec::new();
    for operation in [
        Operation::HttpRequest,
        Operation::Get,
        Operation::Put,
        Operation::Delete,
    ]
    .into_iter()
    .cycle()
    .take(MAX_REQUESTS)
    {
        ids.push(mailbox.enqueue(turn, operation, &bytes).unwrap());
    }
    let usage = mailbox.usage().unwrap();
    assert_eq!(usage.reserved_bytes, MAX_RESERVATION_BYTES);
    assert_eq!(usage.argument_bytes, MAX_REQUESTS * MAX_PAYLOAD_BYTES);
    assert_eq!(
        mailbox.enqueue(turn, Operation::Get, b"+1 request"),
        Err(Error::QuotaExceeded)
    );
    mailbox.finish_turn(turn, TurnOutcome::Success).unwrap();
    assert_eq!(mailbox.take(&mut oversized), Err(Error::InvalidArguments));
    assert!(oversized.iter().all(|&v| v == 2));
    let mut output = vec![0; MAX_PAYLOAD_BYTES];
    let Take::Call { lease, .. } = mailbox.take(&mut output).unwrap() else {
        panic!()
    };
    assert_eq!(mailbox.post(&lease, &[]), Err(Error::InvalidArguments));
    assert_eq!(
        mailbox.post(&lease, &oversized),
        Err(Error::InvalidArguments)
    );
    assert_eq!(
        mailbox.poll(ids[0], &mut oversized),
        Err(Error::InvalidArguments)
    );
    assert_eq!(
        mailbox.limit_deadline(&lease, 0),
        Err(Error::InvalidArguments)
    );
    assert_eq!(
        mailbox.limit_deadline(&lease, 30_001),
        Err(Error::InvalidArguments)
    );
    mailbox.post(&lease, &bytes).unwrap();
    assert_eq!(mailbox.usage().unwrap().completion_bytes, MAX_PAYLOAD_BYTES);
    assert_eq!(
        mailbox.poll(ids[0], &mut output),
        Ok(Poll::Ready {
            length: MAX_PAYLOAD_BYTES
        })
    );
    mailbox.ack_exit(&lease).unwrap();
    let turn = mailbox.begin_turn().unwrap();
    let next = mailbox.enqueue(turn, Operation::Get, &bytes).unwrap();
    assert_ne!(next.token_bits(), ids[0].token_bits());
    assert_eq!(next.token_bits() >> 32, 2);
    assert_eq!(mailbox.cancel(ids[0]), Err(Error::StaleRequest));

    let narrow = Mailbox::new(Limits {
        reservation_bytes: MAX_PAYLOAD_BYTES + 3,
        ..Limits::default()
    })
    .unwrap();
    let turn = narrow.begin_turn().unwrap();
    assert_eq!(
        narrow.enqueue(turn, Operation::Get, b"four"),
        Err(Error::QuotaExceeded)
    );
    assert_eq!(narrow.usage().unwrap().outstanding_requests, 0);
    narrow.enqueue(turn, Operation::Get, b"123").unwrap();
    assert_eq!(
        narrow.usage().unwrap().reserved_bytes,
        MAX_PAYLOAD_BYTES + 3
    );
}

#[test]
fn early_exit_ack_retains_pending_delivery_then_deadline_releases_it() {
    let mailbox = open_mailbox();
    let (id, lease) = dispatched(&mailbox, b"args");
    mailbox.ack_exit(&lease).unwrap();
    assert_eq!(mailbox.ack_exit(&lease), Err(Error::AlreadyAcknowledged));
    assert_eq!(
        mailbox.post(&lease, b"too late"),
        Err(Error::AlreadyAcknowledged)
    );
    assert_eq!(mailbox.poll(id, &mut []), Ok(Poll::Pending));
    assert_eq!(mailbox.usage().unwrap().outstanding_requests, 1);
    mailbox.cancel(id).unwrap();
    assert_eq!(mailbox.take(&mut []), Ok(Take::None));
    assert_eq!(
        mailbox.poll(id, &mut []),
        Ok(Poll::Failure(FailureCode::Cancelled))
    );
    assert_eq!(mailbox.usage().unwrap().reserved_bytes, 0);

    let timed = Mailbox::new(Limits {
        timeout_milliseconds: 100,
        ..Limits::default()
    })
    .unwrap();
    timed.enable().unwrap();
    let (id, lease) = dispatched(&timed, b"early exit");
    timed.ack_exit(&lease).unwrap();
    std::thread::sleep(Duration::from_millis(120));
    assert_eq!(
        timed.poll(id, &mut []),
        Ok(Poll::Failure(FailureCode::DeadlineExceeded))
    );
    assert_eq!(timed.usage().unwrap().outstanding_requests, 0);
}

#[test]
fn late_post_without_watchdog_expires_and_keeps_lease_until_actual_exit() {
    let mailbox = Mailbox::new(Limits {
        timeout_milliseconds: 100,
        ..Limits::default()
    })
    .unwrap();
    mailbox.enable().unwrap();
    let (id, lease) = dispatched(&mailbox, b"args");
    std::thread::sleep(Duration::from_millis(120));
    assert_eq!(
        mailbox.post(&lease, b"late success"),
        Err(Error::AlreadyTerminal)
    );
    assert_eq!(
        mailbox.poll(id, &mut []),
        Ok(Poll::Failure(FailureCode::DeadlineExceeded))
    );
    assert_eq!(mailbox.usage().unwrap().native_leases, 1);
    mailbox.ack_exit(&lease).unwrap();
    assert_eq!(mailbox.usage().unwrap().reserved_bytes, 0);
}

#[test]
fn close_retains_running_storage_and_only_matching_ack_can_release_it() {
    let mailbox = open_mailbox();
    let (id, lease) = dispatched(&mailbox, b"retained arguments");
    mailbox.post(&lease, b"undelivered response").unwrap();
    let queued = submit(&mailbox, Operation::Delete, b"queued never dispatched");
    let expected_reservation = MAX_PAYLOAD_BYTES + b"retained arguments".len();
    let report = mailbox.close().unwrap();
    assert_eq!(
        report
            .cancellations
            .iter()
            .flatten()
            .copied()
            .collect::<Vec<_>>(),
        vec![lease]
    );
    assert_eq!(mailbox.close(), Ok(report));
    let usage = mailbox.usage().unwrap();
    assert_eq!(
        (
            usage.outstanding_requests,
            usage.native_leases,
            usage.reserved_bytes,
            usage.argument_bytes,
            usage.completion_bytes
        ),
        (1, 1, expected_reservation, b"retained arguments".len(), 0)
    );
    let mut untouched = [33; 16];
    assert_eq!(mailbox.poll(id, &mut untouched), Err(Error::SessionClosed));
    assert_eq!(mailbox.cancel(queued), Err(Error::SessionClosed));
    assert_eq!(mailbox.post(&lease, b"late"), Err(Error::SessionClosed));
    assert_eq!(mailbox.take(&mut untouched), Err(Error::SessionClosed));
    assert_eq!(mailbox.limit_deadline(&lease, 1), Err(Error::SessionClosed));
    assert_eq!(mailbox.enable(), Err(Error::SessionClosed));
    assert_eq!(mailbox.begin_turn(), Err(Error::SessionClosed));
    assert_eq!(mailbox.expire(), Err(Error::SessionClosed));
    assert_eq!(untouched, [33; 16]);
    let other = open_mailbox();
    assert_eq!(other.ack_exit(&lease), Err(Error::StaleRequest));
    mailbox.ack_exit(&lease).unwrap();
    assert_eq!(mailbox.ack_exit(&lease), Err(Error::StaleRequest));
    assert_eq!(mailbox.usage().unwrap().reserved_bytes, 0);
    assert!(mailbox
        .close()
        .unwrap()
        .cancellations
        .iter()
        .all(Option::is_none));
}

#[test]
fn cross_owner_ids_and_turns_cannot_alias_equal_numeric_tokens() {
    let a = open_mailbox();
    let b = open_mailbox();
    let aid = submit(&a, Operation::Get, b"a");
    let bid = submit(&b, Operation::Get, b"b");
    assert_eq!(aid.token_bits(), bid.token_bits());
    assert_ne!(aid, bid);
    assert_eq!(a.poll(bid, &mut [0; 1]), Err(Error::StaleRequest));
    assert_eq!(b.cancel(aid), Err(Error::StaleRequest));
    let aturn = a.begin_turn().unwrap();
    let bturn = b.begin_turn().unwrap();
    assert_eq!(
        a.finish_turn(bturn, TurnOutcome::Trap),
        Err(Error::InvalidTurn)
    );
    assert_eq!(
        b.enqueue(aturn, Operation::Get, b"x"),
        Err(Error::InvalidTurn)
    );
    a.finish_turn(aturn, TurnOutcome::Success).unwrap();
    b.finish_turn(bturn, TurnOutcome::Success).unwrap();
}

#[test]
fn cancel_completion_and_close_races_have_one_terminal_and_no_capacity_escape() {
    for _ in 0..100 {
        let mailbox = Arc::new(open_mailbox());
        let (id, lease) = dispatched(&mailbox, b"race");
        let barrier = Arc::new(Barrier::new(3));
        std::thread::scope(|scope| {
            let posted = scope.spawn(|| {
                barrier.wait();
                mailbox.post(&lease, b"ok")
            });
            let cancelled = scope.spawn(|| {
                barrier.wait();
                mailbox.cancel(id)
            });
            barrier.wait();
            let post = posted.join().unwrap();
            let cancel = cancelled.join().unwrap();
            assert!(matches!(
                (post, cancel),
                (Ok(()), Err(Error::AlreadyTerminal)) | (Err(Error::AlreadyTerminal), Ok(()))
            ));
        });
        let mut bytes = [0; 2];
        assert!(matches!(
            mailbox.poll(id, &mut bytes),
            Ok(Poll::Ready { length: 2 }) | Ok(Poll::Failure(FailureCode::Cancelled))
        ));
        assert_eq!(mailbox.usage().unwrap().native_leases, 1);
        mailbox.ack_exit(&lease).unwrap();
        assert_eq!(mailbox.usage().unwrap().outstanding_requests, 0);

        let (id, lease) = dispatched(&mailbox, b"close race");
        let barrier = Barrier::new(3);
        std::thread::scope(|scope| {
            let posted = scope.spawn(|| {
                barrier.wait();
                mailbox.post(&lease, b"ok")
            });
            let closed = scope.spawn(|| {
                barrier.wait();
                mailbox.close()
            });
            barrier.wait();
            assert!(matches!(
                posted.join().unwrap(),
                Ok(()) | Err(Error::SessionClosed)
            ));
            assert!(closed
                .join()
                .unwrap()
                .unwrap()
                .cancellations
                .contains(&Some(lease)));
        });
        assert_eq!(mailbox.poll(id, &mut bytes), Err(Error::SessionClosed));
        assert_eq!(mailbox.usage().unwrap().native_leases, 1);
        mailbox.ack_exit(&lease).unwrap();
        assert_eq!(mailbox.usage().unwrap().reserved_bytes, 0);
    }
}

#[test]
fn trap_discards_new_calls_and_reports_prior_native_leases_for_exit() {
    let mailbox = open_mailbox();
    let (id, lease) = dispatched(&mailbox, b"prior effect");
    let turn = mailbox.begin_turn().unwrap();
    mailbox
        .enqueue(turn, Operation::Put, b"trapped effect")
        .unwrap();
    let report = mailbox
        .finish_turn(turn, TurnOutcome::Trap)
        .unwrap()
        .unwrap();
    assert_eq!(
        report
            .cancellations
            .iter()
            .flatten()
            .copied()
            .collect::<Vec<_>>(),
        vec![lease]
    );
    assert_eq!(mailbox.usage().unwrap().outstanding_requests, 1);
    assert_eq!(mailbox.poll(id, &mut []), Err(Error::SessionClosed));
    mailbox.ack_exit(&lease).unwrap();
    assert_eq!(mailbox.usage().unwrap().reserved_bytes, 0);
}

#[test]
fn concurrent_close_and_early_exit_release_exactly_once() {
    for _ in 0..50 {
        let mailbox = open_mailbox();
        let (_, lease) = dispatched(&mailbox, b"native exit");
        let barrier = Barrier::new(3);
        std::thread::scope(|scope| {
            let exit = scope.spawn(|| {
                barrier.wait();
                mailbox.ack_exit(&lease)
            });
            let close = scope.spawn(|| {
                barrier.wait();
                mailbox.close()
            });
            barrier.wait();
            assert_eq!(exit.join().unwrap(), Ok(()));
            close.join().unwrap().unwrap();
        });
        assert_eq!(mailbox.usage().unwrap().outstanding_requests, 0);
        assert_eq!(mailbox.ack_exit(&lease), Err(Error::StaleRequest));
    }
}

#[test]
fn native_exit_after_post_retains_unconsumed_terminal_and_slot_until_poll() {
    let mailbox = Mailbox::new(Limits {
        maximum_requests: 1,
        ..Limits::default()
    })
    .unwrap();
    mailbox.enable().unwrap();
    let (id, lease) = dispatched(&mailbox, b"args");
    mailbox.post(&lease, b"ok").unwrap();
    mailbox.ack_exit(&lease).unwrap();
    let usage = mailbox.usage().unwrap();
    assert_eq!(
        (
            usage.outstanding_requests,
            usage.native_leases,
            usage.completion_bytes
        ),
        (1, 0, 2)
    );
    let turn = mailbox.begin_turn().unwrap();
    assert_eq!(
        mailbox.enqueue(turn, Operation::Get, b"blocked"),
        Err(Error::QuotaExceeded)
    );
    assert_eq!(mailbox.ack_exit(&lease), Err(Error::AlreadyAcknowledged));
    assert_eq!(
        mailbox.poll(id, &mut []),
        Ok(Poll::BufferTooSmall { required: 2 })
    );
    assert_eq!(mailbox.poll(id, &mut [0; 2]), Ok(Poll::Ready { length: 2 }));
    assert_eq!(mailbox.usage().unwrap().reserved_bytes, 0);
    let next = mailbox.enqueue(turn, Operation::Get, b"next").unwrap();
    assert_eq!(next.token_bits() >> 32, 2);
    assert_eq!(mailbox.ack_exit(&lease), Err(Error::StaleRequest));
    assert_eq!(mailbox.usage().unwrap().outstanding_requests, 1);
}
