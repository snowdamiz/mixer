//! Independent allocation failure, capacity, and stalled-copy synchronization probe.
use mixer_vm::experimental_capability::*;
use std::alloc::{GlobalAlloc, Layout, System};
use std::os::unix::process::ExitStatusExt;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering::SeqCst};
use std::sync::Arc;
use std::time::{Duration, Instant};

struct ObservedAllocator;
static LIVE: AtomicUsize = AtomicUsize::new(0);
static OBSERVE: AtomicBool = AtomicBool::new(false);
static CALLS: AtomicUsize = AtomicUsize::new(0);
static PEAK: AtomicUsize = AtomicUsize::new(0);
static REFUSE_BYTES: AtomicUsize = AtomicUsize::new(0);
static PAUSE_BYTES: AtomicUsize = AtomicUsize::new(0);
static PAUSE_ENTERED: AtomicBool = AtomicBool::new(false);
static PAUSE_RELEASE: AtomicBool = AtomicBool::new(false);

fn permit(bytes: usize) -> bool {
    if OBSERVE.load(SeqCst) {
        CALLS.fetch_add(1, SeqCst);
    }
    if PAUSE_BYTES.load(SeqCst) == bytes {
        PAUSE_ENTERED.store(true, SeqCst);
        let bound = Instant::now() + Duration::from_secs(5);
        while !PAUSE_RELEASE.load(SeqCst) && Instant::now() < bound {
            std::thread::yield_now();
        }
    }
    REFUSE_BYTES
        .compare_exchange(bytes, 0, SeqCst, SeqCst)
        .is_err()
}
fn added(bytes: usize) {
    let live = LIVE.fetch_add(bytes, SeqCst) + bytes;
    if OBSERVE.load(SeqCst) {
        PEAK.fetch_max(live, SeqCst);
    }
}
unsafe impl GlobalAlloc for ObservedAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if !permit(layout.size()) {
            return std::ptr::null_mut();
        }
        let p = unsafe { System.alloc(layout) };
        if !p.is_null() {
            added(layout.size());
        }
        p
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        if !permit(layout.size()) {
            return std::ptr::null_mut();
        }
        let p = unsafe { System.alloc_zeroed(layout) };
        if !p.is_null() {
            added(layout.size());
        }
        p
    }
    unsafe fn realloc(&self, ptr: *mut u8, layout: Layout, length: usize) -> *mut u8 {
        if !permit(length) {
            return std::ptr::null_mut();
        }
        let p = unsafe { System.realloc(ptr, layout, length) };
        if !p.is_null() {
            LIVE.fetch_sub(layout.size(), SeqCst);
            added(length);
        }
        p
    }
    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        unsafe { System.dealloc(ptr, layout) };
        LIVE.fetch_sub(layout.size(), SeqCst);
    }
}
#[global_allocator]
static ALLOCATOR: ObservedAllocator = ObservedAllocator;
fn observe() -> usize {
    CALLS.store(0, SeqCst);
    let base = LIVE.load(SeqCst);
    PEAK.store(base, SeqCst);
    OBSERVE.store(true, SeqCst);
    base
}
fn observed(base: usize) -> (usize, isize, usize) {
    OBSERVE.store(false, SeqCst);
    (
        CALLS.load(SeqCst),
        LIVE.load(SeqCst) as isize - base as isize,
        PEAK.load(SeqCst).saturating_sub(base),
    )
}
fn admit(m: &Mailbox, bytes: &[u8]) -> (RequestId, NativeLease) {
    let t = m.begin_turn().unwrap();
    let id = m.enqueue(t, Operation::HttpRequest, bytes).unwrap();
    m.finish_turn(t, TurnOutcome::Success).unwrap();
    let mut out = vec![0; bytes.len()];
    match m.take(&mut out).unwrap() {
        Take::Call { lease, .. } => (id, lease),
        other => panic!("unexpected {other:?}"),
    }
}

#[test]
fn independent_allocator_measurements_and_stalled_snapshot_race() {
    if std::env::var_os("MIXER_INDEPENDENT_REVIEW_MUTEX_REFUSAL").is_some() {
        let m = Mailbox::new(Limits::default()).unwrap();
        REFUSE_BYTES.store(64, SeqCst);
        let _ = m.enable();
        return;
    }
    let _ = Instant::now();
    let base = observe();
    let m = Mailbox::new(Limits::default()).unwrap();
    assert_eq!(observed(base), (0, 0, 0));
    let base = observe();
    m.enable().unwrap();
    let first_lock = observed(base);
    assert_eq!(
        first_lock,
        (1, 64, 64),
        "observed host-specific std mutex allocation changed"
    );
    assert_eq!(
        std::mem::size_of::<Mailbox>(),
        984,
        "observed host-specific metadata size changed"
    );
    let child = std::process::Command::new(std::env::current_exe().unwrap())
        .args([
            "--exact",
            "independent_allocator_measurements_and_stalled_snapshot_race",
            "--nocapture",
        ])
        .env("MIXER_INDEPENDENT_REVIEW_MUTEX_REFUSAL", "1")
        .output()
        .unwrap();
    assert_eq!(child.status.signal(), Some(6));
    assert!(String::from_utf8_lossy(&child.stderr).contains("memory allocation of 64 bytes failed"));
    println!(
        "independent expected std first-lock OOM negative probe: status={}; stderr={}",
        child.status,
        String::from_utf8_lossy(&child.stderr).trim()
    );

    let args = [0x18; 4093];
    let result = [0x52; 4091];
    let t = m.begin_turn().unwrap();
    let before = m.usage().unwrap();
    REFUSE_BYTES.store(args.len(), SeqCst);
    let base = observe();
    let failure = m.enqueue(t, Operation::Put, &args);
    let measurement = observed(base);
    assert_eq!(failure, Err(Error::AllocationFailure));
    assert_eq!(measurement, (1, 0, 0));
    assert_eq!(m.usage().unwrap(), before);
    let id = m.enqueue(t, Operation::Put, &args).unwrap();
    assert_eq!(id.token_bits(), 1u64 << 32 | 1);
    m.finish_turn(t, TurnOutcome::Success).unwrap();
    let mut out = [0; 4093];
    let Take::Call { lease, .. } = m.take(&mut out).unwrap() else {
        panic!()
    };
    let before = m.usage().unwrap();
    REFUSE_BYTES.store(result.len(), SeqCst);
    let base = observe();
    let failure = m.post(&lease, &result);
    let measurement = observed(base);
    assert_eq!(failure, Err(Error::AllocationFailure));
    assert_eq!(measurement, (1, 0, 0));
    assert_eq!(m.usage().unwrap(), before);
    assert_eq!(m.poll(id, &mut []), Ok(Poll::Pending));
    m.cancel(id).unwrap();
    let base = observe();
    assert_eq!(m.take(&mut []), Ok(Take::Cancel { lease }));
    assert_eq!(
        m.poll(id, &mut []),
        Ok(Poll::Failure(FailureCode::Cancelled))
    );
    m.ack_exit(&lease).unwrap();
    let control = observed(base);
    assert_eq!(control.0, 0);

    // Vary argument lengths so accounting must include actual Vec capacities,
    // while every admitted request still reserves a full maximum completion.
    let full = Mailbox::new(Limits::default()).unwrap();
    full.enable().unwrap();
    let payload = vec![0xc1; MAX_PAYLOAD_BYTES];
    let mut output = vec![0; MAX_PAYLOAD_BYTES];
    let t = full.begin_turn().unwrap();
    let mut ids = [None; 8];
    let mut leases = [None; 8];
    let base = observe();
    for i in 0..8 {
        ids[i] = Some(
            full.enqueue(t, Operation::Get, &payload[..MAX_PAYLOAD_BYTES - i])
                .unwrap(),
        );
    }
    full.finish_turn(t, TurnOutcome::Success).unwrap();
    for l in &mut leases {
        let Take::Call { lease, .. } = full.take(&mut output).unwrap() else {
            panic!()
        };
        full.post(&lease, &payload).unwrap();
        *l = Some(lease);
    }
    let occupancy = observed(base);
    assert_eq!(
        occupancy,
        (
            16,
            (MAX_RESERVATION_BYTES - 28) as isize,
            MAX_RESERVATION_BYTES - 28
        )
    );
    assert_eq!(
        full.usage().unwrap().reserved_bytes,
        MAX_RESERVATION_BYTES - 28
    );
    let t = full.begin_turn().unwrap();
    let base = observe();
    let ninth = full.enqueue(t, Operation::Get, b"x");
    assert_eq!(observed(base).0, 0);
    assert_eq!(ninth, Err(Error::QuotaExceeded));
    full.finish_turn(t, TurnOutcome::Success).unwrap();
    let base = observe();
    full.close().unwrap();
    full.close().unwrap();
    for l in leases.into_iter().flatten() {
        full.ack_exit(&l).unwrap();
    }
    let cleanup = observed(base);
    assert_eq!(cleanup.0, 0);
    assert_eq!(full.usage().unwrap().reserved_bytes, 0);
    println!("independent observed metadata=984; construction=0 allocations; first-lock={first_lock:?}; payload refusals=2 atomic; varying-size full payload allocations/retained/peak={occupancy:?}; no new allocations for control delivery, quota refusal, close or acknowledgements");

    // Pause only the uniquely sized native completion allocation. The mailbox
    // mutex must prevent a simultaneous cancel from completing mid-snapshot;
    // after the stall the private clock must defeat the late success.
    const COPY_BYTES: usize = 31_337;
    let stalled = Arc::new(
        Mailbox::new(Limits {
            timeout_milliseconds: 500,
            ..Limits::default()
        })
        .unwrap(),
    );
    stalled.enable().unwrap();
    let (id, lease) = admit(&stalled, b"slow native completion");
    let payload = vec![0xb7; COPY_BYTES];
    let contender_started = Arc::new(AtomicBool::new(false));
    let contender_finished = Arc::new(AtomicBool::new(false));
    PAUSE_ENTERED.store(false, SeqCst);
    PAUSE_RELEASE.store(false, SeqCst);
    PAUSE_BYTES.store(COPY_BYTES, SeqCst);
    let (posting, cancelling) = std::thread::scope(|scope| {
        let post = scope.spawn(|| stalled.post(&lease, &payload));
        let cancel = scope.spawn(|| {
            let bound = Instant::now() + Duration::from_secs(4);
            while !PAUSE_ENTERED.load(SeqCst) && Instant::now() < bound {
                std::thread::yield_now();
            }
            contender_started.store(true, SeqCst);
            let result = stalled.cancel(id);
            contender_finished.store(true, SeqCst);
            result
        });
        let bound = Instant::now() + Duration::from_secs(4);
        while !contender_started.load(SeqCst) && Instant::now() < bound {
            std::thread::yield_now();
        }
        let entered = PAUSE_ENTERED.load(SeqCst);
        let started = contender_started.load(SeqCst);
        std::thread::sleep(Duration::from_millis(600));
        let completed_inside_copy = contender_finished.load(SeqCst);
        PAUSE_RELEASE.store(true, SeqCst);
        let results = (post.join().unwrap(), cancel.join().unwrap());
        assert!(
            entered && started,
            "allocation gate was not reached before timeout"
        );
        assert!(
            !completed_inside_copy,
            "cancel passed the lock while post snapshot was paused"
        );
        results
    });
    PAUSE_BYTES.store(0, SeqCst);
    assert_eq!(posting, Err(Error::AlreadyTerminal));
    assert_eq!(cancelling, Err(Error::AlreadyTerminal));
    assert_eq!(stalled.usage().unwrap().completion_bytes, 0);
    assert_eq!(
        stalled.poll(id, &mut []),
        Ok(Poll::Failure(FailureCode::DeadlineExceeded))
    );
    assert_eq!(stalled.take(&mut []), Ok(Take::Cancel { lease }));
    stalled.ack_exit(&lease).unwrap();
    assert_eq!(stalled.usage().unwrap().reserved_bytes, 0);
    println!("independent paused-copy race: cancel waits for mutex; 600ms stall exceeds 500ms enqueue deadline; post and cancel observe first DeadlineExceeded terminal; candidate completion dropped");
}
