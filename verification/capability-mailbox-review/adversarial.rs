//! Independently authored behavioral review. No implementation tests imported.
use mixer_vm::experimental_capability::*;
use std::sync::{Arc, Barrier};
use std::time::{Duration, Instant};

fn mailbox(limits: Limits) -> Mailbox {
    let m = Mailbox::new(limits).unwrap();
    m.enable().unwrap();
    m
}
fn publish(m: &Mailbox, op: Operation, bytes: &[u8]) -> RequestId {
    let t = m.begin_turn().unwrap();
    let id = m.enqueue(t, op, bytes).unwrap();
    assert_eq!(m.finish_turn(t, TurnOutcome::Success), Ok(None));
    id
}
fn start(m: &Mailbox, id: RequestId, bytes: &[u8]) -> NativeLease {
    let mut output = vec![0xa5; bytes.len() + usize::from(bytes.len() < MAX_PAYLOAD_BYTES)];
    match m.take(&mut output).unwrap() {
        Take::Call {
            lease,
            length,
            remaining_milliseconds,
        } => {
            assert_eq!(lease.request(), id);
            assert_eq!(length, bytes.len());
            assert!((1..=30_000).contains(&remaining_milliseconds));
            assert_eq!(&output[..length], bytes);
            assert!(output[length..].iter().all(|b| *b == 0xa5));
            lease
        }
        other => panic!("expected dispatch, got {other:?}"),
    }
}

#[derive(Clone, Copy, Debug)]
enum Action {
    Post,
    Cancel,
    Exit,
    Deliver,
    Close,
}
#[derive(Clone, Copy, Debug)]
enum Terminal {
    Payload,
    Cancellation,
}
#[derive(Default)]
struct Reference {
    closed: bool,
    exited: bool,
    delivered: bool,
    released: bool,
    terminal: Option<Terminal>,
}
impl Reference {
    fn reconcile(&mut self) {
        self.released |= self.exited && (self.delivered || self.closed);
    }
    fn exercise(&mut self, action: Action, m: &Mailbox, id: RequestId, lease: NativeLease) {
        match action {
            Action::Post => {
                let expected = if self.closed {
                    Err(Error::SessionClosed)
                } else if self.released || self.delivered {
                    Err(Error::StaleRequest)
                } else if self.terminal.is_some() {
                    Err(Error::AlreadyTerminal)
                } else if self.exited {
                    Err(Error::AlreadyAcknowledged)
                } else {
                    self.terminal = Some(Terminal::Payload);
                    Ok(())
                };
                assert_eq!(m.post(&lease, b"YES"), expected);
            }
            Action::Cancel => {
                let expected = if self.closed {
                    Err(Error::SessionClosed)
                } else if self.released || self.delivered {
                    Err(Error::StaleRequest)
                } else if self.terminal.is_some() {
                    Err(Error::AlreadyTerminal)
                } else {
                    self.terminal = Some(Terminal::Cancellation);
                    Ok(())
                };
                assert_eq!(m.cancel(id), expected);
            }
            Action::Exit => {
                let expected = if self.released {
                    Err(Error::StaleRequest)
                } else if self.exited {
                    Err(Error::AlreadyAcknowledged)
                } else {
                    self.exited = true;
                    Ok(())
                };
                assert_eq!(m.ack_exit(&lease), expected);
            }
            Action::Deliver => {
                let mut output = [0x9d; 4];
                let expected = if self.closed {
                    Err(Error::SessionClosed)
                } else if self.released || self.delivered {
                    Err(Error::StaleRequest)
                } else {
                    match self.terminal.take() {
                        None => Ok(Poll::Pending),
                        Some(Terminal::Payload) => {
                            self.delivered = true;
                            Ok(Poll::Ready { length: 3 })
                        }
                        Some(Terminal::Cancellation) => {
                            self.delivered = true;
                            Ok(Poll::Failure(FailureCode::Cancelled))
                        }
                    }
                };
                assert_eq!(m.poll(id, &mut output), expected);
                if expected == Ok(Poll::Ready { length: 3 }) {
                    assert_eq!(output, [b'Y', b'E', b'S', 0x9d]);
                } else {
                    assert_eq!(output, [0x9d; 4]);
                }
            }
            Action::Close => {
                self.closed = true;
                self.delivered = true;
                self.terminal = None;
                let report = m.close().unwrap();
                let leases: Vec<_> = report.cancellations.into_iter().flatten().collect();
                assert_eq!(leases, if self.exited { vec![] } else { vec![lease] });
            }
        }
        self.reconcile();
        let u = m.usage().unwrap();
        assert_eq!(u.closed, self.closed);
        assert!(u.enabled && !u.turn_active);
        assert_eq!(u.outstanding_requests, usize::from(!self.released));
        assert_eq!(u.native_leases, usize::from(!self.released && !self.exited));
        assert_eq!(
            u.reserved_bytes,
            if self.released {
                0
            } else {
                MAX_PAYLOAD_BYTES + 4
            }
        );
        assert_eq!(u.argument_bytes, if self.released { 0 } else { 4 });
        assert_eq!(
            u.completion_bytes,
            if matches!(self.terminal, Some(Terminal::Payload)) {
                3
            } else {
                0
            }
        );
    }
}
#[test]
fn all_five_step_lifecycle_traces_obey_a_delivery_exit_product_model() {
    const ACTIONS: [Action; 5] = [
        Action::Post,
        Action::Cancel,
        Action::Exit,
        Action::Deliver,
        Action::Close,
    ];
    for script in 0..5usize.pow(5) {
        let m = mailbox(Limits::default());
        let id = publish(&m, Operation::Put, b"seed");
        let lease = start(&m, id, b"seed");
        let mut model = Reference::default();
        let mut encoded = script;
        for step in 0..5 {
            let action = ACTIONS[encoded % 5];
            encoded /= 5;
            let checked = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                model.exercise(action, &m, id, lease)
            }));
            assert!(
                checked.is_ok(),
                "script {script}, step {step}, action {action:?}"
            );
        }
        m.close().unwrap();
        if m.usage().unwrap().native_leases != 0 {
            m.ack_exit(&lease).unwrap();
        }
        assert_eq!(m.usage().unwrap().reserved_bytes, 0);
    }
    println!("independent lifecycle traces=3125 transitions=15625; delivery and native exit accounted separately");
}

#[test]
fn owner_turn_and_generation_boundaries_survive_cross_product_replays() {
    let boxes: Vec<_> = (0..8)
        .map(|_| Mailbox::new(Limits::default()).unwrap())
        .collect();
    let mut obsolete = vec![];
    let mut stale_turns = vec![];
    for m in &boxes {
        let t = m.begin_turn().unwrap();
        let id = m.enqueue(t, Operation::Delete, b"before enable").unwrap();
        m.enable().unwrap();
        assert_eq!(m.take(&mut [0; 20]), Ok(Take::None));
        m.finish_turn(t, TurnOutcome::Success).unwrap();
        assert_eq!(
            m.poll(id, &mut []),
            Ok(Poll::Failure(FailureCode::Unavailable))
        );
        stale_turns.push(t);
        obsolete.push(id);
    }
    let mut turns = vec![];
    let mut ids = vec![];
    for m in &boxes {
        let t = m.begin_turn().unwrap();
        let id = m.enqueue(t, Operation::Get, b"after enable").unwrap();
        turns.push(t);
        ids.push(id);
    }
    assert!(ids.iter().all(|id| id.token_bits() == (2u64 << 32 | 1)));
    for (owner, m) in boxes.iter().enumerate() {
        let before = m.usage().unwrap();
        for i in 0..boxes.len() {
            assert_eq!(
                m.finish_turn(stale_turns[i], TurnOutcome::Trap),
                Err(Error::InvalidTurn)
            );
            assert_eq!(
                m.finish_turn(stale_turns[i], TurnOutcome::Success),
                Err(Error::InvalidTurn)
            );
            assert_eq!(m.cancel(obsolete[i]), Err(Error::StaleRequest));
            if owner != i {
                assert_eq!(
                    m.enqueue(turns[i], Operation::Put, b"foreign"),
                    Err(Error::InvalidTurn)
                );
                assert_eq!(
                    m.finish_turn(turns[i], TurnOutcome::Trap),
                    Err(Error::InvalidTurn)
                );
                let mut output = [0x7b; 20];
                assert_eq!(m.poll(ids[i], &mut output), Err(Error::StaleRequest));
                assert_eq!(output, [0x7b; 20]);
            }
        }
        assert_eq!(m.usage().unwrap(), before);
        assert_eq!(m.take(&mut [0; 20]), Ok(Take::None));
    }
    for (i, m) in boxes.iter().enumerate() {
        m.finish_turn(turns[i], TurnOutcome::Success).unwrap();
    }
    let leases: Vec<_> = boxes
        .iter()
        .enumerate()
        .map(|(i, m)| start(m, ids[i], b"after enable"))
        .collect();
    for (owner, m) in boxes.iter().enumerate() {
        let before = m.usage().unwrap();
        for (i, lease) in leases.iter().enumerate() {
            if i != owner {
                assert_eq!(m.post(lease, b"alien"), Err(Error::StaleRequest));
                assert_eq!(m.limit_deadline(lease, 1), Err(Error::StaleRequest));
                assert_eq!(m.ack_exit(lease), Err(Error::StaleRequest));
            }
        }
        assert_eq!(m.usage().unwrap(), before);
        m.close().unwrap();
        m.ack_exit(&leases[owner]).unwrap();
    }
}

#[test]
fn exact_capacity_counts_opposite_halves_of_native_and_delivery_obligations() {
    let m = mailbox(Limits::default());
    let payload = vec![0x68; MAX_PAYLOAD_BYTES];
    let mut output = vec![0x32; MAX_PAYLOAD_BYTES];
    let t = m.begin_turn().unwrap();
    let ids: Vec<_> = (0..8)
        .map(|_| m.enqueue(t, Operation::HttpRequest, &payload).unwrap())
        .collect();
    assert_eq!(m.usage().unwrap().reserved_bytes, 8 * 1024 * 1024);
    let before = m.usage().unwrap();
    assert_eq!(
        m.enqueue(t, Operation::Get, b"ninth"),
        Err(Error::QuotaExceeded)
    );
    assert_eq!(m.usage().unwrap(), before);
    m.finish_turn(t, TurnOutcome::Success).unwrap();
    let mut leases = vec![];
    for id in &ids {
        let lease = start(&m, *id, &payload);
        m.post(&lease, &payload).unwrap();
        leases.push(lease);
    }
    let full = m.usage().unwrap();
    assert_eq!(
        full.argument_bytes + full.completion_bytes,
        MAX_RESERVATION_BYTES
    );
    // The first half has actual exit but undelivered completion. The second half
    // has delivered completion but ongoing native work. Every slot must remain.
    for lease in &leases[..4] {
        m.ack_exit(lease).unwrap();
    }
    for id in &ids[4..] {
        assert_eq!(
            m.poll(*id, &mut output),
            Ok(Poll::Ready {
                length: MAX_PAYLOAD_BYTES
            })
        );
        assert!(output.iter().all(|b| *b == 0x68));
    }
    let split = m.usage().unwrap();
    assert_eq!(
        (
            split.outstanding_requests,
            split.native_leases,
            split.reserved_bytes
        ),
        (8, 4, MAX_RESERVATION_BYTES)
    );
    let t = m.begin_turn().unwrap();
    assert_eq!(
        m.enqueue(t, Operation::Delete, b"still ninth"),
        Err(Error::QuotaExceeded)
    );
    m.finish_turn(t, TurnOutcome::Success).unwrap();
    let report = m.close().unwrap();
    let survivors: Vec<_> = report.cancellations.into_iter().flatten().collect();
    assert_eq!(survivors, leases[4..]);
    assert_eq!(m.close(), Ok(report));
    let closing = m.usage().unwrap();
    assert_eq!(
        (
            closing.outstanding_requests,
            closing.native_leases,
            closing.argument_bytes,
            closing.completion_bytes,
            closing.reserved_bytes
        ),
        (4, 4, 4 * MAX_PAYLOAD_BYTES, 0, 4 * 2 * MAX_PAYLOAD_BYTES)
    );
    for lease in survivors {
        m.ack_exit(&lease).unwrap();
    }
    assert_eq!(m.usage().unwrap().reserved_bytes, 0);
}

#[test]
fn invalid_buffers_cannot_consume_controls_failures_or_payloads() {
    let m = mailbox(Limits::default());
    let id = publish(&m, Operation::Get, b"seven77");
    let mut oversized = vec![0x79; MAX_PAYLOAD_BYTES + 1];
    let before = m.usage().unwrap();
    assert_eq!(m.take(&mut oversized), Err(Error::InvalidArguments));
    assert_eq!(m.usage().unwrap(), before);
    let mut small = [0x41; 6];
    for _ in 0..3 {
        assert_eq!(m.take(&mut small), Ok(Take::BufferTooSmall { required: 7 }));
        assert_eq!(small, [0x41; 6]);
    }
    let lease = start(&m, id, b"seven77");
    for bytes in [&[][..], &oversized[..]] {
        assert_eq!(m.post(&lease, bytes), Err(Error::InvalidArguments));
    }
    assert_eq!(m.poll(id, &mut oversized), Err(Error::InvalidArguments));
    m.cancel(id).unwrap();
    let cancelled = m.usage().unwrap();
    assert_eq!(m.take(&mut oversized), Err(Error::InvalidArguments));
    assert_eq!(m.poll(id, &mut oversized), Err(Error::InvalidArguments));
    assert_eq!(m.usage().unwrap(), cancelled);
    assert!(oversized.iter().all(|b| *b == 0x79));
    assert_eq!(m.take(&mut []), Ok(Take::Cancel { lease }));
    assert_eq!(m.take(&mut []), Ok(Take::None));
    assert_eq!(
        m.poll(id, &mut small),
        Ok(Poll::Failure(FailureCode::Cancelled))
    );
    assert_eq!(small, [0x41; 6]);
    m.ack_exit(&lease).unwrap();
    // Completion backpressure never exposes a partial prefix or consumes data.
    let id = publish(&m, Operation::Put, b"new");
    let lease = start(&m, id, b"new");
    let mut native = b"snapshot\0bytes".to_vec();
    m.post(&lease, &native).unwrap();
    native.fill(0xcc);
    assert_eq!(
        m.poll(id, &mut small),
        Ok(Poll::BufferTooSmall { required: 14 })
    );
    assert_eq!(small, [0x41; 6]);
    let mut out = [0x55; 15];
    assert_eq!(m.poll(id, &mut out), Ok(Poll::Ready { length: 14 }));
    assert_eq!(&out[..14], b"snapshot\0bytes");
    assert_eq!(out[14], 0x55);
    m.ack_exit(&lease).unwrap();
}

#[test]
fn narrowed_budget_refuses_before_snapshot_and_caller_mutation_cannot_change_arguments() {
    for bad in [
        Limits {
            maximum_requests: 0,
            ..Limits::default()
        },
        Limits {
            maximum_requests: 9,
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
            timeout_milliseconds: 30_001,
            ..Limits::default()
        },
    ] {
        assert!(matches!(Mailbox::new(bad), Err(Error::InvalidLimits)));
    }
    let m = mailbox(Limits {
        reservation_bytes: MAX_PAYLOAD_BYTES + 3,
        ..Limits::default()
    });
    let t = m.begin_turn().unwrap();
    let before = m.usage().unwrap();
    let oversized = vec![0x99; MAX_PAYLOAD_BYTES + 1];
    for bytes in [&[][..], &oversized[..]] {
        assert_eq!(
            m.enqueue(t, Operation::Put, bytes),
            Err(Error::InvalidArguments)
        );
    }
    assert_eq!(
        m.enqueue(t, Operation::Put, b"four"),
        Err(Error::QuotaExceeded)
    );
    assert_eq!(m.usage().unwrap(), before);
    let mut caller = b"abc".to_vec();
    let id = m.enqueue(t, Operation::Put, &caller).unwrap();
    caller.fill(0xee);
    assert_eq!(m.usage().unwrap().reserved_bytes, MAX_PAYLOAD_BYTES + 3);
    m.finish_turn(t, TurnOutcome::Success).unwrap();
    let lease = start(&m, id, b"abc");
    let before = m.usage().unwrap();
    assert_eq!(m.limit_deadline(&lease, 0), Err(Error::InvalidArguments));
    assert_eq!(
        m.limit_deadline(&lease, 30_001),
        Err(Error::InvalidArguments)
    );
    assert_eq!(m.usage().unwrap(), before);
    m.close().unwrap();
    m.ack_exit(&lease).unwrap();
    assert_eq!(m.usage().unwrap().reserved_bytes, 0);
}

#[test]
fn successful_turns_gate_calls_while_controls_and_trap_cleanup_remain_live() {
    let m = mailbox(Limits::default());
    let running = publish(&m, Operation::Delete, b"running");
    let lease = start(&m, running, b"running");
    let queued = publish(&m, Operation::Get, b"already successful");
    let turn = m.begin_turn().unwrap();
    let trapped = m.enqueue(turn, Operation::Put, b"trap candidate").unwrap();
    m.cancel(running).unwrap();
    assert_eq!(m.take(&mut []), Ok(Take::Cancel { lease }));
    assert_eq!(m.take(&mut [0; 64]), Ok(Take::None));
    let report = m.finish_turn(turn, TurnOutcome::Trap).unwrap().unwrap();
    assert_eq!(
        report
            .cancellations
            .into_iter()
            .flatten()
            .collect::<Vec<_>>(),
        vec![lease]
    );
    assert_eq!(m.usage().unwrap().argument_bytes, 7);
    for id in [running, queued, trapped] {
        assert_eq!(m.poll(id, &mut []), Err(Error::SessionClosed));
    }
    m.ack_exit(&lease).unwrap();
    assert_eq!(m.usage().unwrap().outstanding_requests, 0);
}

#[test]
fn private_monotonic_deadlines_narrow_from_origin_and_preserve_first_terminal() {
    let m = mailbox(Limits::default());
    let id = publish(&m, Operation::Get, b"origin");
    let lease = start(&m, id, b"origin");
    std::thread::sleep(Duration::from_millis(80));
    assert_eq!(m.limit_deadline(&lease, 50), Ok(0));
    assert_eq!(
        m.limit_deadline(&lease, 30_000),
        Err(Error::AlreadyTerminal)
    );
    assert_eq!(m.post(&lease, b"late"), Err(Error::AlreadyTerminal));
    assert_eq!(
        m.poll(id, &mut []),
        Ok(Poll::Failure(FailureCode::DeadlineExceeded))
    );
    m.ack_exit(&lease).unwrap();
    // An early exit is not a completion or release, but deadline consumption is.
    let m = mailbox(Limits {
        timeout_milliseconds: 100,
        ..Limits::default()
    });
    let id = publish(&m, Operation::Get, b"no result");
    let lease = start(&m, id, b"no result");
    m.ack_exit(&lease).unwrap();
    assert_eq!(m.poll(id, &mut []), Ok(Poll::Pending));
    assert_eq!(m.usage().unwrap().reserved_bytes, MAX_PAYLOAD_BYTES + 9);
    std::thread::sleep(Duration::from_millis(130));
    assert_eq!(
        m.poll(id, &mut []),
        Ok(Poll::Failure(FailureCode::DeadlineExceeded))
    );
    assert_eq!(m.usage().unwrap().reserved_bytes, 0);
    // A successful result already accepted stays immutable after its deadline.
    let m = mailbox(Limits {
        timeout_milliseconds: 100,
        ..Limits::default()
    });
    let id = publish(&m, Operation::Put, b"committed");
    let lease = start(&m, id, b"committed");
    m.post(&lease, b"first").unwrap();
    std::thread::sleep(Duration::from_millis(130));
    m.expire().unwrap();
    assert_eq!(m.cancel(id), Err(Error::AlreadyTerminal));
    let mut bytes = [0; 5];
    assert_eq!(m.poll(id, &mut bytes), Ok(Poll::Ready { length: 5 }));
    assert_eq!(&bytes, b"first");
    m.ack_exit(&lease).unwrap();
}

#[test]
fn many_posters_pollers_cancellation_and_exit_have_exactly_one_complete_delivery() {
    const N: usize = 8;
    const BYTES: usize = 32_768;
    for round in 0..64 {
        let m = Arc::new(mailbox(Limits::default()));
        let id = publish(&m, Operation::HttpRequest, b"race");
        let lease = start(&m, id, b"race");
        let barrier = Arc::new(Barrier::new(N + 4 + 2 + 1));
        std::thread::scope(|scope| {
            let mut posts = vec![];
            for tag in 1..=N {
                let (m, b) = (Arc::clone(&m), Arc::clone(&barrier));
                posts.push(scope.spawn(move || {
                    let bytes = vec![tag as u8; BYTES];
                    b.wait();
                    (tag as u8, m.post(&lease, &bytes))
                }));
            }
            let mut consumers = vec![];
            for _ in 0..4 {
                let (m, b) = (Arc::clone(&m), Arc::clone(&barrier));
                consumers.push(scope.spawn(move || {
                    let mut bytes = vec![0xd7; BYTES + 1];
                    b.wait();
                    let bound = Instant::now() + Duration::from_secs(5);
                    loop {
                        match m.poll(id, &mut bytes) {
                            Ok(Poll::Pending) if Instant::now() < bound => std::thread::yield_now(),
                            Ok(Poll::Ready { length }) => {
                                assert_eq!(length, BYTES);
                                let tag = bytes[0];
                                assert!((1..=N as u8).contains(&tag));
                                assert!(bytes[..length].iter().all(|v| *v == tag));
                                assert_eq!(bytes[length], 0xd7);
                                return Some(Some(tag));
                            }
                            Ok(Poll::Failure(FailureCode::Cancelled)) => {
                                assert!(bytes.iter().all(|v| *v == 0xd7));
                                return Some(None);
                            }
                            Err(Error::StaleRequest) => {
                                assert!(bytes.iter().all(|v| *v == 0xd7));
                                return None;
                            }
                            other => panic!("round {round}, unexpected delivery {other:?}"),
                        }
                    }
                }));
            }
            let (cm, cb) = (Arc::clone(&m), Arc::clone(&barrier));
            let cancelled = scope.spawn(move || {
                cb.wait();
                cm.cancel(id)
            });
            let (am, ab) = (Arc::clone(&m), Arc::clone(&barrier));
            let exited = scope.spawn(move || {
                ab.wait();
                am.ack_exit(&lease)
            });
            barrier.wait();
            let posts: Vec<_> = posts.into_iter().map(|h| h.join().unwrap()).collect();
            let deliveries: Vec<_> = consumers
                .into_iter()
                .filter_map(|h| h.join().unwrap())
                .collect();
            let cancellation = cancelled.join().unwrap();
            assert_eq!(exited.join().unwrap(), Ok(()));
            assert_eq!(deliveries.len(), 1, "round {round}");
            match deliveries[0] {
                Some(tag) => {
                    assert_eq!(posts.iter().filter(|p| p.1.is_ok()).count(), 1);
                    assert!(posts.contains(&(tag, Ok(()))));
                    assert!(matches!(
                        cancellation,
                        Err(Error::AlreadyTerminal | Error::StaleRequest)
                    ));
                }
                None => {
                    assert_eq!(cancellation, Ok(()));
                    assert!(posts.iter().all(|p| p.1.is_err()));
                }
            }
            assert!(posts.iter().all(|p| matches!(
                p.1,
                Ok(())
                    | Err(Error::AlreadyTerminal
                        | Error::StaleRequest
                        | Error::AlreadyAcknowledged)
            )));
        });
        assert_eq!(m.usage().unwrap().reserved_bytes, 0);
        assert_eq!(m.ack_exit(&lease), Err(Error::StaleRequest));
    }
    println!("concurrent completion/cancel/exit/delivery rounds=64; actors_per_round=14; one intact delivery per round");
}

#[test]
fn concurrent_close_reports_keep_all_and_only_unacknowledged_leases() {
    for _ in 0..32 {
        let m = Arc::new(mailbox(Limits::default()));
        let mut ids = vec![];
        let mut leases = vec![];
        for _ in 0..8 {
            let id = publish(&m, Operation::Get, b"retained");
            leases.push(start(&m, id, b"retained"));
            ids.push(id);
        }
        for lease in &leases {
            m.post(lease, b"discard on close").unwrap();
        }
        let barrier = Barrier::new(4);
        std::thread::scope(|scope| {
            let closing = scope.spawn(|| {
                barrier.wait();
                m.close().unwrap()
            });
            let exit_half = scope.spawn(|| {
                barrier.wait();
                for l in &leases[..4] {
                    m.ack_exit(l).unwrap();
                }
            });
            let delivery = scope.spawn(|| {
                barrier.wait();
                for id in &ids {
                    assert!(matches!(
                        m.poll(*id, &mut [0; 32]),
                        Ok(Poll::Ready { length: 16 }) | Err(Error::SessionClosed)
                    ));
                }
            });
            barrier.wait();
            let report = closing.join().unwrap();
            exit_half.join().unwrap();
            delivery.join().unwrap();
            for lease in &leases[4..] {
                assert!(report.cancellations.contains(&Some(*lease)));
            }
        });
        let stable = m.close().unwrap();
        assert_eq!(m.close(), Ok(stable));
        assert_eq!(
            stable
                .cancellations
                .into_iter()
                .flatten()
                .collect::<Vec<_>>(),
            leases[4..]
        );
        let u = m.usage().unwrap();
        assert_eq!(
            (
                u.native_leases,
                u.outstanding_requests,
                u.argument_bytes,
                u.completion_bytes
            ),
            (4, 4, 32, 0)
        );
        for l in &leases[4..] {
            m.ack_exit(l).unwrap();
        }
        assert_eq!(m.usage().unwrap().reserved_bytes, 0);
    }
    println!("concurrent close/delivery/partial-exit rounds=32; stable reports retain exactly four outstanding native identities");
}
