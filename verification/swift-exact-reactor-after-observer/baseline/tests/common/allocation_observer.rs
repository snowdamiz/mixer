//! Requested-byte observation for one synchronous test lane, independent of the
//! process's harness threads. Ownership spans the test; fault/peak intervals are
//! shorter so proof construction and later destruction remain in leak baselines.
use mixer_vm::Cancellation;
use std::alloc::{GlobalAlloc, Layout, System};
use std::cell::{Cell, RefCell, UnsafeCell};
use std::marker::PhantomData;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

pub static LIVE: AtomicUsize = AtomicUsize::new(0);
pub static PEAK: AtomicUsize = AtomicUsize::new(0);
pub static CALLS: AtomicUsize = AtomicUsize::new(0);
pub static REALLOCATIONS: AtomicUsize = AtomicUsize::new(0);
pub static MAX_SLOTS: AtomicUsize = AtomicUsize::new(0);

thread_local! {
    static OWNED: Cell<bool> = const { Cell::new(false) };
    static ACTIVE: Cell<bool> = const { Cell::new(false) };
    static FAIL: Cell<usize> = const { Cell::new(0) };
    static CANCEL_AT: Cell<usize> = const { Cell::new(0) };
    static CANCEL: RefCell<Option<Cancellation>> = const { RefCell::new(None) };
}
fn owned() -> bool {
    OWNED.try_with(Cell::get).unwrap_or(false)
}
fn active() -> bool {
    ACTIVE.try_with(Cell::get).unwrap_or(false)
}
fn request() -> bool {
    if !active() {
        return true;
    }
    let call = CALLS.fetch_add(1, Ordering::SeqCst) + 1;
    if CANCEL_AT.with(Cell::get) == call {
        CANCEL.with(|slot| {
            if let Some(cancellation) = slot.borrow().as_ref() {
                cancellation.cancel();
            }
        });
    }
    call != FAIL.with(Cell::get)
}

#[derive(Clone, Copy)]
struct Slot {
    address: usize,
    bytes: usize,
}
const EMPTY: Slot = Slot {
    address: 0,
    bytes: 0,
};
const CAPACITY: usize = 4096;
struct Ledger {
    slots: [Slot; CAPACITY],
    used: usize,
}
impl Ledger {
    fn find(&self, address: usize) -> Option<usize> {
        self.slots.iter().position(|slot| slot.address == address)
    }
    fn insert(&mut self, address: usize, bytes: usize) {
        // A full ledger fails closed; an observation must never silently omit
        // an owned allocation. No heap, formatting, or panicking in this hook.
        let Some(index) = self.find(0) else {
            std::process::abort();
        };
        self.slots[index] = Slot { address, bytes };
        self.used += 1;
        MAX_SLOTS.fetch_max(self.used, Ordering::SeqCst);
        let live = LIVE.fetch_add(bytes, Ordering::SeqCst) + bytes;
        PEAK.fetch_max(live, Ordering::SeqCst);
    }
    fn remove(&mut self, address: usize) -> bool {
        let Some(index) = self.find(address) else {
            return false;
        };
        LIVE.fetch_sub(self.slots[index].bytes, Ordering::SeqCst);
        self.slots[index] = EMPTY;
        self.used -= 1;
        true
    }
}
struct SharedLedger(UnsafeCell<Ledger>);
// Only LedgerGuard accesses the cell, with exclusive access under LOCK.
unsafe impl Sync for SharedLedger {}
static LEDGER: SharedLedger = SharedLedger(UnsafeCell::new(Ledger {
    slots: [EMPTY; CAPACITY],
    used: 0,
}));
static LOCK: AtomicBool = AtomicBool::new(false);
struct LedgerGuard;
impl LedgerGuard {
    fn acquire() -> Self {
        while LOCK
            .compare_exchange(false, true, Ordering::Acquire, Ordering::Relaxed)
            .is_err()
        {
            std::hint::spin_loop();
        }
        Self
    }
    fn ledger(&mut self) -> &mut Ledger {
        unsafe { &mut *LEDGER.0.get() }
    }
}
impl Drop for LedgerGuard {
    fn drop(&mut self) {
        LOCK.store(false, Ordering::Release);
    }
}

pub struct Observed;
fn probe_allocator() -> &'static dyn GlobalAlloc {
    // Probe calls must execute in optimized builds too. The std::alloc wrappers
    // permit allocation elision; an opaque call through the observer's trait
    // interface exercises the same GlobalAlloc methods without that assumption.
    std::hint::black_box(&Observed)
}
unsafe impl GlobalAlloc for Observed {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if !request() {
            return std::ptr::null_mut();
        }
        let pointer = unsafe { System.alloc(layout) };
        if !pointer.is_null() && owned() {
            LedgerGuard::acquire()
                .ledger()
                .insert(pointer as usize, layout.size());
        }
        pointer
    }
    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        if !request() {
            return std::ptr::null_mut();
        }
        let pointer = unsafe { System.alloc_zeroed(layout) };
        if !pointer.is_null() && owned() {
            LedgerGuard::acquire()
                .ledger()
                .insert(pointer as usize, layout.size());
        }
        pointer
    }
    unsafe fn dealloc(&self, pointer: *mut u8, layout: Layout) {
        // Forget ownership before freeing the address. A different thread can
        // immediately reuse it without the old deallocation removing its entry.
        LedgerGuard::acquire().ledger().remove(pointer as usize);
        unsafe { System.dealloc(pointer, layout) };
    }
    unsafe fn realloc(&self, pointer: *mut u8, layout: Layout, bytes: usize) -> *mut u8 {
        if active() {
            REALLOCATIONS.fetch_add(1, Ordering::SeqCst);
        }
        if !request() {
            return std::ptr::null_mut();
        }
        // Retain the old entry on failure. Hold the ledger lock across System's
        // realloc so a moved old address cannot be registered by another thread
        // until its previous lifetime has been removed. System does not call
        // back into this Rust global allocator.
        let mut guard = LedgerGuard::acquire();
        let ledger = guard.ledger();
        let was_owned = ledger.find(pointer as usize).is_some();
        let next = unsafe { System.realloc(pointer, layout, bytes) };
        if !next.is_null() {
            ledger.remove(pointer as usize);
            if was_owned || owned() {
                ledger.insert(next as usize, bytes);
            }
        }
        next
    }
}

#[must_use]
pub struct Ownership(PhantomData<*mut ()>);
impl Ownership {
    pub fn new() -> Self {
        assert!(!OWNED.with(|value| value.replace(true)));
        Self(PhantomData)
    }
}
fn disarm() {
    ACTIVE.with(|value| value.set(false));
    CANCEL.with(|value| value.borrow_mut().take());
    FAIL.with(|value| value.set(0));
    CANCEL_AT.with(|value| value.set(0));
}
impl Drop for Ownership {
    fn drop(&mut self) {
        disarm();
        OWNED.with(|value| value.set(false));
    }
}
#[must_use]
pub struct Operation<'a> {
    baseline: usize,
    _cancellation: &'a Cancellation,
    _same_thread: PhantomData<*mut ()>,
}
pub fn begin(fail: usize, cancel_at: usize, cancellation: &Cancellation) -> Operation<'_> {
    assert!(owned());
    assert!(!active());
    let baseline = LIVE.load(Ordering::SeqCst);
    PEAK.store(baseline, Ordering::SeqCst);
    CALLS.store(0, Ordering::SeqCst);
    REALLOCATIONS.store(0, Ordering::SeqCst);
    FAIL.with(|value| value.set(fail));
    CANCEL_AT.with(|value| value.set(cancel_at));
    // Cancellation::clone only retains its existing Arc; it allocates no heap.
    // Keeping a token in TLS also remains safe if a guard is accidentally leaked.
    CANCEL.with(|value| *value.borrow_mut() = Some(cancellation.clone()));
    ACTIVE.with(|value| value.set(true));
    let operation = Operation {
        baseline,
        _cancellation: cancellation,
        _same_thread: PhantomData,
    };
    if NOISE_ENABLED.load(Ordering::SeqCst) {
        // Change unrelated live bytes after each baseline, retaining the change
        // through the existing cleanup assertions. Requests occur while this
        // lane's failure/cancellation gate is armed.
        command(if NOISE_HELD.load(Ordering::SeqCst) {
            FREE
        } else {
            ALLOCATE
        });
    }
    operation
}
impl Operation<'_> {
    pub fn finish(self) -> usize {
        self.baseline
    }
}
impl Drop for Operation<'_> {
    fn drop(&mut self) {
        disarm();
    }
}

const ALLOCATE: usize = 1;
const FREE: usize = 2;
const RESIZE_TRANSFER: usize = 3;
const FREE_TRANSFER: usize = 4;
const ROUNDTRIP: usize = 5;
const STOP: usize = 6;
static COMMAND: AtomicUsize = AtomicUsize::new(0);
static COMPLETE: AtomicBool = AtomicBool::new(false);
static TRANSFER: AtomicUsize = AtomicUsize::new(0);
static TRANSFER_SIZE: AtomicUsize = AtomicUsize::new(0);
static NOISE_ENABLED: AtomicBool = AtomicBool::new(false);
static NOISE_HELD: AtomicBool = AtomicBool::new(false);
fn command(value: usize) {
    COMPLETE.store(false, Ordering::SeqCst);
    COMMAND.store(value, Ordering::SeqCst);
    while !COMPLETE.load(Ordering::SeqCst) {
        std::hint::spin_loop();
    }
}
pub struct Background(Option<std::thread::JoinHandle<()>>);
impl Background {
    // Construct before Ownership: the harness-like worker's setup and lifetime
    // are deliberately outside the synchronous lane.
    pub fn new() -> Self {
        let noisy = std::env::var_os("MIXER_ALLOCATOR_NOISE").is_some();
        let worker = std::thread::spawn(|| {
            let layout = Layout::from_size_align(900, 1).unwrap();
            let mut held = std::ptr::null_mut();
            COMPLETE.store(true, Ordering::SeqCst);
            loop {
                let next = COMMAND.load(Ordering::SeqCst);
                match next {
                    ALLOCATE => {
                        held = unsafe { probe_allocator().alloc(layout) };
                        if held.is_null() {
                            std::process::abort();
                        }
                        NOISE_HELD.store(true, Ordering::SeqCst);
                    }
                    FREE => {
                        unsafe { probe_allocator().dealloc(held, layout) };
                        held = std::ptr::null_mut();
                        NOISE_HELD.store(false, Ordering::SeqCst);
                    }
                    RESIZE_TRANSFER => {
                        let size = TRANSFER_SIZE.load(Ordering::SeqCst);
                        let pointer = TRANSFER.load(Ordering::SeqCst) as *mut u8;
                        let next = unsafe {
                            probe_allocator().realloc(
                                pointer,
                                Layout::from_size_align(size, 8).unwrap(),
                                size * 2,
                            )
                        };
                        if next.is_null() {
                            std::process::abort();
                        }
                        TRANSFER.store(next as usize, Ordering::SeqCst);
                        TRANSFER_SIZE.store(size * 2, Ordering::SeqCst);
                    }
                    FREE_TRANSFER => {
                        let size = TRANSFER_SIZE.load(Ordering::SeqCst);
                        let pointer = TRANSFER.load(Ordering::SeqCst) as *mut u8;
                        unsafe {
                            probe_allocator()
                                .dealloc(pointer, Layout::from_size_align(size, 8).unwrap())
                        };
                    }
                    ROUNDTRIP => unsafe {
                        let pointer = probe_allocator().alloc_zeroed(layout);
                        if pointer.is_null() {
                            std::process::abort();
                        }
                        let resized = probe_allocator().realloc(pointer, layout, 1800);
                        if resized.is_null() {
                            std::process::abort();
                        }
                        probe_allocator()
                            .dealloc(resized, Layout::from_size_align(1800, 1).unwrap());
                    },
                    STOP => {
                        if !held.is_null() {
                            unsafe { probe_allocator().dealloc(held, layout) };
                        }
                        return;
                    }
                    _ => {
                        std::hint::spin_loop();
                        continue;
                    }
                }
                COMMAND.store(0, Ordering::SeqCst);
                COMPLETE.store(true, Ordering::SeqCst);
            }
        });
        while !COMPLETE.load(Ordering::SeqCst) {
            std::hint::spin_loop();
        }
        NOISE_ENABLED.store(noisy, Ordering::SeqCst);
        Self(Some(worker))
    }
    pub fn check_observer(&self) {
        let cancellation = Cancellation::default();
        let before = LIVE.load(Ordering::SeqCst);
        let layout = Layout::from_size_align(64, 8).unwrap();
        // Dropping an unfinished interval must disarm both borrowed cancellation
        // and refusal before normal owned allocations resume.
        drop(begin(1, 1, &cancellation));
        let pointer = unsafe { probe_allocator().alloc_zeroed(layout) };
        assert!(!pointer.is_null());
        assert_eq!(LIVE.load(Ordering::SeqCst), before + 64);
        assert!(!cancellation.is_cancelled());
        let operation = begin(1, 0, &cancellation);
        let denied = unsafe { probe_allocator().realloc(pointer, layout, 128) };
        operation.finish();
        assert!(denied.is_null());
        assert_eq!(CALLS.load(Ordering::SeqCst), 1);
        assert_eq!(REALLOCATIONS.load(Ordering::SeqCst), 1);
        assert_eq!(LIVE.load(Ordering::SeqCst), before + 64);
        TRANSFER.store(pointer as usize, Ordering::SeqCst);
        TRANSFER_SIZE.store(64, Ordering::SeqCst);
        command(RESIZE_TRANSFER);
        assert_eq!(LIVE.load(Ordering::SeqCst), before + 128);
        command(FREE_TRANSFER);
        assert_eq!(LIVE.load(Ordering::SeqCst), before);
        // Deterministically reuse the former address in the ledger. This checks
        // lifetime removal/size replacement even on allocators that choose a
        // different address on their next real allocation; no memory is read.
        let address = TRANSFER.load(Ordering::SeqCst);
        let (previous_lifetime_removed, first_removed, replacement_live, second_removed) = {
            let mut guard = LedgerGuard::acquire();
            let ledger = guard.ledger();
            let absent = ledger.find(address).is_none();
            ledger.insert(address, 64);
            let first_removed = ledger.remove(address);
            ledger.insert(address, 128);
            let replacement_live = LIVE.load(Ordering::SeqCst);
            let second_removed = ledger.remove(address);
            (absent, first_removed, replacement_live, second_removed)
        };
        // Assertions run after releasing the allocator lock, so even a failing
        // check can format its panic without recursively acquiring that lock.
        assert!(previous_lifetime_removed);
        assert!(first_removed);
        assert_eq!(replacement_live, before + 128);
        assert!(second_removed);
        assert_eq!(LIVE.load(Ordering::SeqCst), before);
        let operation = begin(1, 1, &cancellation);
        command(ROUNDTRIP);
        let calls_before_owned_request = CALLS.load(Ordering::SeqCst);
        let resizes_before_owned_request = REALLOCATIONS.load(Ordering::SeqCst);
        let peak_before_owned_request = PEAK.load(Ordering::SeqCst);
        let cancelled_before_owned_request = cancellation.is_cancelled();
        let pointer = unsafe { probe_allocator().alloc(layout) };
        let baseline = operation.finish();
        assert_eq!(calls_before_owned_request, 0);
        assert_eq!(resizes_before_owned_request, 0);
        assert_eq!(peak_before_owned_request, baseline);
        assert!(!cancelled_before_owned_request);
        assert!(pointer.is_null());
        assert!(cancellation.is_cancelled());
        assert_eq!(CALLS.load(Ordering::SeqCst), 1);
        assert_eq!(LIVE.load(Ordering::SeqCst), baseline);
    }
}
impl Drop for Background {
    fn drop(&mut self) {
        NOISE_ENABLED.store(false, Ordering::SeqCst);
        COMMAND.store(STOP, Ordering::SeqCst);
        self.0.take().unwrap().join().unwrap();
    }
}
