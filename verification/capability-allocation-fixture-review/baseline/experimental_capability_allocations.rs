#![cfg(feature = "experimental-capability-mailbox")]
//! One test in its own process: deterministic allocator refusal and measurements.
use mixer_vm::experimental_capability::*;
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering::SeqCst};
use std::time::{Duration, Instant};

struct Probe;
static TRACKING: AtomicBool = AtomicBool::new(false);
static CALLS: AtomicUsize = AtomicUsize::new(0);
static LIVE: AtomicUsize = AtomicUsize::new(0);
static PEAK: AtomicUsize = AtomicUsize::new(0);
static FAIL_AT: AtomicUsize = AtomicUsize::new(0);
static PAUSE: AtomicBool = AtomicBool::new(false);
static ENTERED: AtomicBool = AtomicBool::new(false);
static RELEASE: AtomicBool = AtomicBool::new(false);
fn permit() -> bool {
    if !TRACKING.load(SeqCst) {
        return true;
    }
    let ordinal = CALLS.fetch_add(1, SeqCst) + 1;
    if PAUSE.load(SeqCst) && ordinal == 1 {
        ENTERED.store(true, SeqCst);
        while !RELEASE.load(SeqCst) {
            std::hint::spin_loop();
        }
    }
    ordinal != FAIL_AT.load(SeqCst)
}
fn allocated(bytes: usize) {
    let live = LIVE.fetch_add(bytes, SeqCst) + bytes;
    if TRACKING.load(SeqCst) {
        PEAK.fetch_max(live, SeqCst);
    }
}
unsafe impl GlobalAlloc for Probe {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if !permit() {
            return std::ptr::null_mut();
        }
        let ptr = unsafe { System.alloc(layout) };
        if !ptr.is_null() {
            allocated(layout.size());
        }
        ptr
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        if !permit() {
            return std::ptr::null_mut();
        }
        let ptr = unsafe { System.alloc_zeroed(layout) };
        if !ptr.is_null() {
            allocated(layout.size());
        }
        ptr
    }
    unsafe fn realloc(&self, ptr: *mut u8, layout: Layout, size: usize) -> *mut u8 {
        if !permit() {
            return std::ptr::null_mut();
        }
        let updated = unsafe { System.realloc(ptr, layout, size) };
        if !updated.is_null() {
            LIVE.fetch_sub(layout.size(), SeqCst);
            allocated(size);
        }
        updated
    }
    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        unsafe { System.dealloc(ptr, layout) };
        LIVE.fetch_sub(layout.size(), SeqCst);
    }
}
#[global_allocator]
static ALLOCATOR: Probe = Probe;
fn track(fail: usize) -> usize {
    CALLS.store(0, SeqCst);
    FAIL_AT.store(fail, SeqCst);
    let baseline = LIVE.load(SeqCst);
    PEAK.store(baseline, SeqCst);
    TRACKING.store(true, SeqCst);
    baseline
}
fn stop(baseline: usize) -> (usize, usize, usize) {
    TRACKING.store(false, SeqCst);
    (
        CALLS.load(SeqCst),
        LIVE.load(SeqCst).saturating_sub(baseline),
        PEAK.load(SeqCst).saturating_sub(baseline),
    )
}
fn take(mailbox: &Mailbox, output: &mut [u8]) -> NativeLease {
    match mailbox.take(output).unwrap() {
        Take::Call { lease, .. } => lease,
        other => panic!("{other:?}"),
    }
}
#[test]
fn allocations_fail_atomically_and_all_auxiliary_state_is_fixed() {
    if std::env::var_os("MIXER_CAPABILITY_MUTEX_OOM_PROBE").is_some() {
        let mailbox = Mailbox::new(Limits::default()).unwrap();
        track(1);
        let _ = mailbox.enable(); // standard-library first-lock allocation may abort
        TRACKING.store(false, SeqCst);
        return;
    }
    // Warm the platform clock before the observed intervals.
    let _ = Instant::now();
    let baseline = track(1);
    let mailbox = Mailbox::new(Limits::default()).unwrap();
    let construction = stop(baseline);
    assert_eq!(construction, (0, 0, 0));
    let baseline = track(0);
    mailbox.enable().unwrap();
    let first_lock = stop(baseline);
    // Platform standard-library synchronization overhead is outside payload
    // reservation. Its allocator behavior is observed, not universally promised.
    assert!(first_lock.0 <= 1 && first_lock.1 <= 256);
    if first_lock.0 != 0 {
        let child = std::process::Command::new(std::env::current_exe().unwrap())
            .arg("--exact")
            .arg("allocations_fail_atomically_and_all_auxiliary_state_is_fixed")
            .arg("--nocapture")
            .env("MIXER_CAPABILITY_MUTEX_OOM_PROBE", "1")
            .output()
            .unwrap();
        assert!(
            !child.status.success(),
            "lazy std mutex allocation unexpectedly survived refusal"
        );
        println!(
            "known standard-library first-lock OOM failure: status={}; stderr={}",
            child.status,
            String::from_utf8_lossy(&child.stderr).trim()
        );
    }
    let turn = mailbox.begin_turn().unwrap();
    let before = mailbox.usage().unwrap();
    let baseline = track(1);
    let failure = mailbox.enqueue(turn, Operation::Put, b"argument snapshot");
    let failed_enqueue = stop(baseline);
    assert_eq!(failure, Err(Error::AllocationFailure));
    assert_eq!(failed_enqueue, (1, 0, 0));
    assert_eq!(mailbox.usage().unwrap(), before);
    let baseline = track(0);
    let id = mailbox
        .enqueue(turn, Operation::Put, b"argument snapshot")
        .unwrap();
    let admitted = stop(baseline);
    assert_eq!(admitted, (1, 17, 17));
    assert_eq!(id.token_bits(), 1u64 << 32 | 1);
    mailbox.finish_turn(turn, TurnOutcome::Success).unwrap();
    let baseline = track(1);
    let lease = take(&mailbox, &mut [0; 17]);
    assert_eq!(stop(baseline).0, 0);
    let before = mailbox.usage().unwrap();
    let baseline = track(1);
    let failure = mailbox.post(&lease, b"completion snapshot");
    let failed_post = stop(baseline);
    assert_eq!(failure, Err(Error::AllocationFailure));
    assert_eq!(failed_post, (1, 0, 0));
    assert_eq!(mailbox.usage().unwrap(), before);
    assert_eq!(mailbox.poll(id, &mut []), Ok(Poll::Pending));
    let baseline = track(0);
    mailbox.post(&lease, b"completion snapshot").unwrap();
    assert_eq!(stop(baseline), (1, 19, 19));
    let baseline = track(1);
    assert_eq!(
        mailbox.poll(id, &mut [0; 19]),
        Ok(Poll::Ready { length: 19 })
    );
    mailbox.ack_exit(&lease).unwrap();
    assert_eq!(stop(baseline).0, 0);
    assert_eq!(mailbox.usage().unwrap().reserved_bytes, 0);

    // A full mailbox has exactly sixteen payload allocations, no expanding
    // metadata/queue, and its 8MiB reservation covers these Vec capacities only.
    let arguments = vec![7; MAX_PAYLOAD_BYTES];
    let completions = vec![8; MAX_PAYLOAD_BYTES];
    let mut output = vec![0; MAX_PAYLOAD_BYTES];
    let full = Mailbox::new(Limits::default()).unwrap();
    full.enable().unwrap();
    let turn = full.begin_turn().unwrap();
    let baseline = track(0);
    let mut ids = [None; MAX_REQUESTS];
    let mut leases = [None; MAX_REQUESTS];
    for id in &mut ids {
        *id = Some(full.enqueue(turn, Operation::Get, &arguments).unwrap());
    }
    full.finish_turn(turn, TurnOutcome::Success).unwrap();
    for lease in &mut leases {
        let taken = take(&full, &mut output);
        full.post(&taken, &completions).unwrap();
        *lease = Some(taken);
    }
    let measured = stop(baseline);
    assert_eq!(measured, (16, MAX_RESERVATION_BYTES, MAX_RESERVATION_BYTES));
    assert_eq!(full.usage().unwrap().reserved_bytes, MAX_RESERVATION_BYTES);
    let before = full.usage().unwrap();
    let turn = full.begin_turn().unwrap();
    let baseline = track(1);
    assert_eq!(
        full.enqueue(turn, Operation::Get, b"x"),
        Err(Error::QuotaExceeded)
    );
    for id in ids.into_iter().flatten() {
        assert_eq!(full.cancel(id), Err(Error::AlreadyTerminal));
        assert_eq!(
            full.poll(id, &mut []),
            Ok(Poll::BufferTooSmall {
                required: MAX_PAYLOAD_BYTES
            })
        );
    }
    assert_eq!(stop(baseline).0, 0);
    assert_eq!(full.usage().unwrap(), before_with_active(before));
    full.finish_turn(turn, TurnOutcome::Success).unwrap();
    let baseline = track(1);
    let report = full.close().unwrap();
    assert_eq!(report.cancellations.iter().flatten().count(), MAX_REQUESTS);
    assert_eq!(full.close(), Ok(report));
    for lease in leases.into_iter().flatten() {
        full.ack_exit(&lease).unwrap();
    }
    assert_eq!(stop(baseline).0, 0);
    assert_eq!(full.usage().unwrap().reserved_bytes, 0);

    let cancellation = Mailbox::new(Limits::default()).unwrap();
    cancellation.enable().unwrap();
    let turn = cancellation.begin_turn().unwrap();
    let id = cancellation
        .enqueue(turn, Operation::Delete, b"cancel")
        .unwrap();
    cancellation
        .finish_turn(turn, TurnOutcome::Success)
        .unwrap();
    let lease = take(&cancellation, &mut [0; 6]);
    let baseline = track(1);
    cancellation.cancel(id).unwrap();
    for _ in 0..1_000 {
        assert_eq!(cancellation.cancel(id), Err(Error::AlreadyTerminal));
    }
    assert_eq!(cancellation.take(&mut []), Ok(Take::Cancel { lease }));
    assert_eq!(cancellation.take(&mut []), Ok(Take::None));
    assert_eq!(
        cancellation.poll(id, &mut []),
        Ok(Poll::Failure(FailureCode::Cancelled))
    );
    cancellation.ack_exit(&lease).unwrap();
    assert_eq!(stop(baseline).0, 0);

    // Allocation may stall after post's first clock check. A private second
    // check must install deadline instead of publishing late success.
    let slow = Mailbox::new(Limits {
        timeout_milliseconds: 100,
        ..Limits::default()
    })
    .unwrap();
    slow.enable().unwrap();
    let turn = slow.begin_turn().unwrap();
    let id = slow.enqueue(turn, Operation::HttpRequest, b"args").unwrap();
    slow.finish_turn(turn, TurnOutcome::Success).unwrap();
    let lease = take(&slow, &mut [0; 4]);
    ENTERED.store(false, SeqCst);
    RELEASE.store(false, SeqCst);
    PAUSE.store(true, SeqCst);
    let release = std::thread::spawn(|| {
        let deadline = Instant::now() + Duration::from_secs(5);
        while !ENTERED.load(SeqCst) && Instant::now() < deadline {
            std::hint::spin_loop();
        }
        let entered = ENTERED.load(SeqCst);
        std::thread::sleep(Duration::from_millis(120));
        RELEASE.store(true, SeqCst);
        entered
    });
    let baseline = track(0);
    let result = slow.post(&lease, b"a stalled success");
    let slow_post = stop(baseline);
    PAUSE.store(false, SeqCst);
    assert!(
        release.join().unwrap(),
        "did not reach post allocation gate"
    );
    assert_eq!(result, Err(Error::AlreadyTerminal));
    assert_eq!(slow_post.0, 1);
    assert_eq!(slow.usage().unwrap().completion_bytes, 0);
    assert_eq!(
        slow.poll(id, &mut []),
        Ok(Poll::Failure(FailureCode::DeadlineExceeded))
    );
    slow.ack_exit(&lease).unwrap();
    println!("inline metadata bytes={}; construction allocations=0; std first-lock allocation={first_lock:?}; enqueue allocations=1 bytes=17; post allocations=1 bytes=19; failure ordinals=1 per payload allocating path; failure retained delta=0; full mailbox allocations={} retained={} peak={}; auxiliary take/poll/cancel/close/ack allocations=0; delayed post refuses late success", std::mem::size_of::<Mailbox>(), measured.0, measured.1, measured.2);
}
fn before_with_active(mut usage: Usage) -> Usage {
    usage.turn_active = true;
    usage
}
