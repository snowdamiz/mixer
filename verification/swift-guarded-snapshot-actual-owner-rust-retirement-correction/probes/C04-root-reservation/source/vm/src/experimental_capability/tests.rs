use super::*;

fn open() -> Mailbox {
    let mailbox = Mailbox::new(Limits::default()).unwrap();
    mailbox.enable().unwrap();
    mailbox
}
fn request(mailbox: &Mailbox) -> RequestId {
    let turn = mailbox.begin_turn().unwrap();
    let id = mailbox
        .enqueue(turn, Operation::HttpRequest, b"args")
        .unwrap();
    mailbox.finish_turn(turn, TurnOutcome::Success).unwrap();
    id
}
fn take(mailbox: &Mailbox) -> NativeLease {
    match mailbox.take(&mut [0; 4]).unwrap() {
        Take::Call { lease, .. } => lease,
        other => panic!("expected call: {other:?}"),
    }
}
#[test]
fn generations_retire_without_wrap_and_invalid_id_forms_reject() {
    let mailbox = Mailbox::new(Limits {
        maximum_requests: 1,
        ..Limits::default()
    })
    .unwrap();
    mailbox.state.lock().unwrap().slots[0].generation = u32::MAX;
    let turn = mailbox.begin_turn().unwrap();
    let id = mailbox.enqueue(turn, Operation::Get, b"x").unwrap();
    assert_eq!(id.token_bits(), (u32::MAX as u64) << 32 | 1);
    for bits in [
        0,
        1,
        1u64 << 32,
        (u32::MAX as u64) << 32 | 9,
        1u64 << 32 | 1,
    ] {
        assert_eq!(
            mailbox.poll(
                RequestId {
                    owner: mailbox.owner,
                    bits
                },
                &mut []
            ),
            Err(Error::StaleRequest)
        );
    }
    assert_eq!(
        mailbox.poll(id, &mut []),
        Ok(Poll::Failure(FailureCode::Unavailable))
    );
    assert_eq!(mailbox.usage().unwrap().retired_slots, 1);
    assert_eq!(
        mailbox.enqueue(turn, Operation::Get, b"x"),
        Err(Error::QuotaExceeded)
    );
    assert_eq!(mailbox.cancel(id), Err(Error::StaleRequest));
}
#[test]
fn owner_and_turn_identifiers_exhaust_without_aliasing() {
    let counter = AtomicU64::new(u64::MAX - 1);
    assert_eq!(issue_owner(&counter), Ok(u64::MAX - 1));
    assert_eq!(issue_owner(&counter), Err(Error::IdentifierExhausted));
    assert_eq!(counter.load(Ordering::Relaxed), u64::MAX);
    let mailbox = open();
    mailbox.state.lock().unwrap().last_turn = u64::MAX - 1;
    let turn = mailbox.begin_turn().unwrap();
    assert_eq!(turn.sequence, u64::MAX);
    mailbox.finish_turn(turn, TurnOutcome::Success).unwrap();
    assert_eq!(mailbox.begin_turn(), Err(Error::IdentifierExhausted));
    assert_eq!(
        mailbox.enqueue(turn, Operation::Get, b"x"),
        Err(Error::InvalidTurn)
    );
}
#[test]
fn wrong_lease_operation_and_cross_owner_reject_without_native_release() {
    let a = open();
    let b = open();
    let id = request(&a);
    request(&b);
    let lease = take(&a);
    let wrong = NativeLease {
        operation: Operation::Delete,
        ..lease
    };
    let before = a.usage().unwrap();
    assert_eq!(b.post(&lease, b"done"), Err(Error::StaleRequest));
    assert_eq!(b.ack_exit(&lease), Err(Error::StaleRequest));
    assert_eq!(b.limit_deadline(&lease, 5), Err(Error::StaleRequest));
    assert_eq!(b.poll(id, &mut []), Err(Error::StaleRequest));
    assert_eq!(a.post(&wrong, b"done"), Err(Error::StaleRequest));
    assert_eq!(a.ack_exit(&wrong), Err(Error::StaleRequest));
    assert_eq!(a.usage().unwrap(), before);
}
#[test]
fn deadline_narrowing_is_relative_to_enqueue_and_late_success_cannot_win() {
    let mailbox = open();
    let id = request(&mailbox);
    let lease = take(&mailbox);
    // Private white-box setup is not a caller-supplied production clock.
    let enqueued = Instant::now() - Duration::from_millis(500);
    {
        let mut state = mailbox.state.lock().unwrap();
        let request = state.slots[0].request.as_mut().unwrap();
        request.enqueued = enqueued;
        request.deadline = enqueued + Duration::from_secs(30);
    }
    let first = mailbox.limit_deadline(&lease, 1_000).unwrap();
    assert!(first <= 500);
    let second = mailbox.limit_deadline(&lease, 30_000).unwrap();
    assert!(second <= first);
    assert_eq!(mailbox.limit_deadline(&lease, 100), Ok(0));
    assert_eq!(mailbox.post(&lease, b"late"), Err(Error::AlreadyTerminal));
    assert_eq!(
        mailbox.poll(id, &mut []),
        Ok(Poll::Failure(FailureCode::DeadlineExceeded))
    );
    assert!(matches!(mailbox.take(&mut []), Ok(Take::Cancel { .. })));
    mailbox.ack_exit(&lease).unwrap();
    assert_eq!(mailbox.usage().unwrap().outstanding_requests, 0);
}
#[test]
fn every_success_path_rechecks_private_clock_and_first_terminal_is_immutable() {
    for action in 0..5 {
        let mailbox = open();
        let id = request(&mailbox);
        let lease = if action == 0 {
            None
        } else {
            Some(take(&mailbox))
        };
        mailbox.state.lock().unwrap().slots[0]
            .request
            .as_mut()
            .unwrap()
            .deadline = Instant::now() - Duration::from_secs(1);
        match action {
            0 => assert_eq!(mailbox.take(&mut [99; 4]), Ok(Take::None)),
            1 => assert_eq!(
                mailbox.post(lease.as_ref().unwrap(), b"late"),
                Err(Error::AlreadyTerminal)
            ),
            2 => assert_eq!(mailbox.cancel(id), Err(Error::AlreadyTerminal)),
            3 => assert_eq!(
                mailbox.poll(id, &mut []),
                Ok(Poll::Failure(FailureCode::DeadlineExceeded))
            ),
            _ => mailbox.expire().unwrap(),
        }
        if action != 3 {
            assert_eq!(
                mailbox.poll(id, &mut []),
                Ok(Poll::Failure(FailureCode::DeadlineExceeded))
            );
        }
        if let Some(lease) = lease {
            mailbox.ack_exit(&lease).unwrap();
        }
        assert_eq!(mailbox.usage().unwrap().outstanding_requests, 0);
    }
    let mailbox = open();
    let id = request(&mailbox);
    let lease = take(&mailbox);
    mailbox.post(&lease, b"ok").unwrap();
    mailbox.state.lock().unwrap().slots[0]
        .request
        .as_mut()
        .unwrap()
        .deadline = Instant::now() - Duration::from_secs(1);
    mailbox.expire().unwrap();
    assert_eq!(mailbox.cancel(id), Err(Error::AlreadyTerminal));
    assert_eq!(mailbox.poll(id, &mut [0; 2]), Ok(Poll::Ready { length: 2 }));
    mailbox.ack_exit(&lease).unwrap();
}
#[test]
fn poisoned_mutex_rejects_reuse_instead_of_recovering_untrusted_state() {
    let mailbox = open();
    let trapped = std::panic::catch_unwind(|| {
        let _lock = mailbox.state.lock().unwrap();
        panic!("test mailbox poison");
    });
    assert!(trapped.is_err());
    assert_eq!(mailbox.begin_turn(), Err(Error::Poisoned));
    assert_eq!(mailbox.enable(), Err(Error::Poisoned));
    assert_eq!(mailbox.close(), Err(Error::Poisoned));
}
