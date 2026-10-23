//! Bounded persistent native sessions. Handles carry slot generations, never pointers.
use crate::{
    ffi::{arg, arguments, boundary, bytes, limits_from, report_error},
    *,
};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex, MutexGuard, OnceLock, TryLockError,
};

const SESSION_CAP: usize = 16;
const TRANSFER_CAP: usize = 1024 * 1024;
type Failure = (Error, u32);
fn failure(code: &'static str, message: &str, status: u32) -> Failure {
    (Error::new(code, message, None, 0), status)
}
struct Session {
    instance: Mutex<Instance>,
    limits: Limits,
    cancellation: Cancellation,
    terminal: AtomicBool,
}
impl Session {
    fn stop(&self) {
        self.terminal.store(true, Ordering::Release);
        self.cancellation.cancel();
    }
    fn lock(&self) -> Result<MutexGuard<'_, Instance>, Failure> {
        let guard = match self.instance.try_lock() {
            Ok(g) => g,
            Err(TryLockError::WouldBlock) => {
                return Err(failure(
                    "session_busy",
                    "another session operation is running",
                    3,
                ))
            }
            Err(TryLockError::Poisoned(_)) => {
                self.stop();
                return Err(failure(
                    "session_poisoned",
                    "session is unusable after internal panic",
                    4,
                ));
            }
        };
        if self.terminal.load(Ordering::Acquire) {
            return Err(failure(
                "session_terminal",
                "session was cancelled, closed or failed",
                2,
            ));
        }
        Ok(guard)
    }
}
enum State {
    Empty,
    Reserved,
    Live(Arc<Session>),
    // A closed in-flight instance still counts against the allocation ceiling.
    Closing(Arc<Session>),
    // Payload destruction has started outside the registry lock, but has not
    // completed. This slot cannot be reused until the final Arc drop returns.
    Reclaiming,
    Retired,
}
struct Slot {
    generation: u32,
    state: State,
}
impl Slot {
    fn release(&mut self) {
        if let Some(next) = self.generation.checked_add(1) {
            self.generation = next;
            self.state = State::Empty;
        } else {
            self.state = State::Retired;
        }
    }
}
struct Registry([Slot; SESSION_CAP]);
impl Registry {
    fn new() -> Self {
        Self(std::array::from_fn(|_| Slot {
            generation: 1,
            state: State::Empty,
        }))
    }
    fn reserve(&mut self) -> Result<(usize, u32), Failure> {
        for (index, slot) in self.0.iter_mut().enumerate() {
            if matches!(slot.state, State::Empty) {
                slot.state = State::Reserved;
                return Ok((index, slot.generation));
            }
        }
        Err(failure(
            "session_limit",
            "persistent session ceiling reached",
            3,
        ))
    }
    fn slot(&mut self, handle: u64) -> Result<&mut Slot, Failure> {
        let index = (handle as u32)
            .checked_sub(1)
            .filter(|i| (*i as usize) < SESSION_CAP);
        let generation = (handle >> 32) as u32;
        if let Some(index) = index {
            let slot = &mut self.0[index as usize];
            if generation != 0
                && generation == slot.generation
                && matches!(slot.state, State::Live(_))
            {
                return Ok(slot);
            }
        }
        Err(failure(
            "invalid_session",
            "unknown, closed or stale session handle",
            3,
        ))
    }
    fn begin_reclaim(&mut self, handle: u64) -> Option<(usize, Arc<Session>)> {
        let index = (handle as u32).checked_sub(1)? as usize;
        let slot = self.0.get_mut(index)?;
        if slot.generation != (handle >> 32) as u32 {
            return None;
        }
        if matches!(&slot.state, State::Closing(session) if Arc::strong_count(session) == 1) {
            let State::Closing(session) = std::mem::replace(&mut slot.state, State::Reclaiming)
            else {
                unreachable!()
            };
            Some((index, session))
        } else {
            None
        }
    }
}
fn registry() -> &'static Mutex<Registry> {
    static REGISTRY: OnceLock<Mutex<Registry>> = OnceLock::new();
    REGISTRY.get_or_init(|| Mutex::new(Registry::new()))
}
fn registry_lock() -> Result<MutexGuard<'static, Registry>, Failure> {
    registry()
        .lock()
        .map_err(|_| failure("registry_poisoned", "session registry is unavailable", 4))
}
fn get(handle: u64) -> Result<SessionLease, Failure> {
    match &registry_lock()?.slot(handle)?.state {
        State::Live(session) => Ok(SessionLease {
            handle,
            session: Some(Arc::clone(session)),
        }),
        _ => unreachable!("slot checks live state"),
    }
}
struct SessionLease {
    handle: u64,
    session: Option<Arc<Session>>,
}
impl std::ops::Deref for SessionLease {
    type Target = Session;
    fn deref(&self) -> &Session {
        self.session.as_ref().expect("live operation lease")
    }
}
impl Drop for SessionLease {
    fn drop(&mut self) {
        drop(self.session.take());
        reclaim(self.handle);
    }
}
fn reclaim(handle: u64) {
    let pending = {
        let Ok(mut registry) = registry().lock() else {
            return;
        };
        registry.begin_reclaim(handle)
    };
    if let Some((index, session)) = pending {
        drop(session); // complete all instance and Arc deallocation before reuse
        if let Ok(mut registry) = registry().lock() {
            let slot = &mut registry.0[index];
            if slot.generation == (handle >> 32) as u32 && matches!(slot.state, State::Reclaiming) {
                slot.release();
            }
        }
    }
}
struct Reservation {
    index: usize,
    generation: u32,
    published: bool,
}
impl Reservation {
    fn new() -> Result<Self, Failure> {
        let (index, generation) = registry_lock()?.reserve()?;
        Ok(Self {
            index,
            generation,
            published: false,
        })
    }
    fn publish(mut self, session: Session) -> Result<u64, Failure> {
        let session = Arc::new(session);
        let mut registry = registry_lock()?;
        let slot = &mut registry.0[self.index];
        // No handle can address a reservation. Only its owner can publish it.
        debug_assert!(matches!(slot.state, State::Reserved));
        debug_assert_eq!(slot.generation, self.generation);
        slot.state = State::Live(session);
        self.published = true;
        Ok(((self.generation as u64) << 32) | (self.index as u64 + 1))
    }
}
impl Drop for Reservation {
    fn drop(&mut self) {
        if !self.published {
            // No panic from cleanup while unwinding. A poisoned registry stays closed.
            if let Ok(mut registry) = registry().lock() {
                let slot = &mut registry.0[self.index];
                if slot.generation == self.generation && matches!(slot.state, State::Reserved) {
                    slot.release();
                }
            }
        }
    }
}

/// Validate and instantiate a persistent session. Profile IDs are 1, 2 and 3.
/// # Safety
/// Pointers obey mixer_vm.h. out_handle is writable and does not alias any buffer.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_session_create_v1(
    profile: u32,
    data: *const u8,
    len: usize,
    limits: *const MixerVmLimits,
    out_handle: *mut u64,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe {
        boundary(out, || {
            if out_handle.is_null() {
                return Err((arg("null output handle"), 3));
            }
            out_handle.write_unaligned(0);
            let profile = match profile {
                1 => Profile::IntegerV1,
                2 => Profile::NumericV2,
                3 => Profile::TableMemoryV3,
                _ => return Err((arg("unknown session profile"), 3)),
            };
            let mut limits = limits_from(limits).map_err(|e| (e, 3))?;
            limits.profile = profile;
            let input = bytes(data, len, limits.module_bytes).map_err(|e| (e, 3))?;
            let reservation = Reservation::new()?;
            let module = Module::decode(input, &limits).map_err(|e| (e, 1))?;
            let instance = Instance::new(module, limits.clone()).map_err(|e| (e, 2))?;
            let cancellation = instance.cancellation();
            let handle = reservation.publish(Session {
                instance: Mutex::new(instance),
                limits,
                cancellation,
                terminal: AtomicBool::new(false),
            })?;
            out_handle.write_unaligned(handle);
            Ok(MixerVmReport::default())
        })
    }
}

/// Invoke once on retained state. Any interpreter error permanently terminates it.
/// # Safety
/// Pointers obey mixer_vm.h; all buffers remain valid for this complete call.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_session_invoke_v1(
    handle: u64,
    export: *const u8,
    export_len: usize,
    args: *const MixerVmValue,
    args_len: usize,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe {
        boundary(out, || {
            let session = get(handle)?;
            let name = bytes(export, export_len, 4096).map_err(|e| (e, 3))?;
            let name =
                std::str::from_utf8(name).map_err(|_| (arg("export name is not UTF-8"), 3))?;
            let values = arguments(
                session.limits.profile,
                session.limits.locals,
                args,
                args_len,
            )
            .map_err(|e| (e, 3))?;
            let mut instance = session.lock()?;
            let mut result = instance.invoke(name, &values);
            // Cancellation may arrive at the last instruction. State is discarded, never reused.
            if session.cancellation.is_cancelled() {
                result = Err(Error::new(
                    "cancelled",
                    "session execution cancelled",
                    None,
                    0,
                ));
            }
            let mut report = match result {
                Ok(value) => {
                    let mut report = MixerVmReport::default();
                    if let Some(value) = value {
                        (report.value_type, report.value) = match value {
                            Value::I32(v) => (1, v as i64),
                            Value::I64(v) => (2, v),
                            Value::F32(v) => (3, v as i64),
                            Value::F64(v) => (4, v as i64),
                        };
                    }
                    report
                }
                Err(error) => {
                    session.stop();
                    report_error(error, 2)
                }
            };
            report.fuel_used = session.limits.fuel - instance.fuel_remaining;
            report.host_calls_used = instance.host_calls_used;
            Ok(report)
        })
    }
}

/// Copy guest memory to a host-owned buffer; never exposes a guest-memory pointer.
/// # Safety
/// destination holds len writable bytes (null only for zero length), disjoint from out.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_session_read_v1(
    handle: u64,
    offset: u32,
    destination: *mut u8,
    len: usize,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe {
        boundary(out, || {
            if len > TRANSFER_CAP || (len > 0 && destination.is_null()) {
                return Err((arg("invalid destination buffer or transfer length"), 3));
            }
            let session = get(handle)?;
            let instance = session.lock()?;
            let start = offset as usize;
            let end = start
                .checked_add(len)
                .filter(|n| *n <= instance.memory().len())
                .ok_or_else(|| {
                    failure("memory_out_of_bounds", "host transfer exceeds memory", 3)
                })?;
            if len > 0 {
                std::ptr::copy_nonoverlapping(
                    instance.memory()[start..end].as_ptr(),
                    destination,
                    len,
                );
            }
            Ok(MixerVmReport::default())
        })
    }
}

/// Copy host bytes into bounded guest memory, with whole-range validation before mutation.
/// # Safety
/// source holds len readable bytes (null only for zero length), disjoint from out.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_session_write_v1(
    handle: u64,
    offset: u32,
    source: *const u8,
    len: usize,
    out: *mut MixerVmReport,
) -> u32 {
    unsafe {
        boundary(out, || {
            let input = bytes(source, len, TRANSFER_CAP).map_err(|e| (e, 3))?;
            let session = get(handle)?;
            let mut instance = session.lock()?;
            instance.write_memory(offset, input).map_err(|e| (e, 3))?;
            Ok(MixerVmReport::default())
        })
    }
}

/// Permanent cooperative cancellation; does not wait for an active invocation.
/// # Safety
/// out points to writable non-aliasing MixerVmReport storage.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_session_cancel_v1(handle: u64, out: *mut MixerVmReport) -> u32 {
    unsafe {
        boundary(out, || {
            get(handle)?.stop();
            Ok(MixerVmReport::default())
        })
    }
}

/// Invalidate a handle and cancel execution. Storage survives until in-flight calls return.
/// # Safety
/// out points to writable non-aliasing MixerVmReport storage.
#[no_mangle]
pub unsafe extern "C" fn mixer_vm_session_close_v1(handle: u64, out: *mut MixerVmReport) -> u32 {
    unsafe {
        boundary(out, || {
            let session = {
                let mut registry = registry_lock()?;
                let slot = registry.slot(handle)?;
                let State::Live(session) = &slot.state else {
                    unreachable!()
                };
                let session = Arc::clone(session);
                session.stop();
                slot.state = State::Closing(Arc::clone(&session));
                session
            };
            drop(session); // large instance destruction does not hold the registry mutex
            reclaim(handle);
            Ok(MixerVmReport::default())
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn session() -> Arc<Session> {
        let limits = Limits::default();
        let module = Module::decode(b"\0asm\x01\0\0\0", &limits).unwrap();
        let instance = Instance::new(module, limits.clone()).unwrap();
        Arc::new(Session {
            cancellation: instance.cancellation(),
            instance: Mutex::new(instance),
            limits,
            terminal: AtomicBool::new(false),
        })
    }

    #[test]
    fn generation_exhaustion_permanently_retires_slot() {
        let mut registry = Registry::new();
        registry.0[0].generation = u32::MAX;
        assert_eq!(registry.reserve().unwrap(), (0, u32::MAX));
        registry.0[0].release();
        assert!(matches!(registry.0[0].state, State::Retired));
        assert_eq!(registry.reserve().unwrap(), (1, 1));
        assert!(registry.slot((u32::MAX as u64) << 32 | 1).is_err());
    }

    #[test]
    fn closed_in_flight_and_reserved_slots_still_count_against_cap() {
        let mut registry = Registry::new();
        let session = session();
        registry.0[0].state = State::Closing(Arc::clone(&session));
        for i in 1..SESSION_CAP {
            assert_eq!(registry.reserve().unwrap().0, i);
        }
        assert_eq!(registry.reserve().unwrap_err().0.code, "session_limit");
        drop(session);
        let (index, session) = registry.begin_reclaim(1u64 << 32 | 1).unwrap();
        assert_eq!(index, 0);
        assert_eq!(registry.reserve().unwrap_err().0.code, "session_limit");
        drop(session);
        registry.0[index].release();
        assert_eq!(registry.reserve().unwrap(), (0, 2));
        assert_eq!(registry.reserve().unwrap_err().0.code, "session_limit");
    }

    #[test]
    fn busy_session_and_cross_thread_stop_are_nonblocking() {
        let session = session();
        let instance = session.lock().unwrap();
        let shared = Arc::clone(&session);
        std::thread::spawn(move || {
            assert!(matches!(
                shared.lock(),
                Err((
                    Error {
                        code: "session_busy",
                        ..
                    },
                    3
                ))
            ));
            shared.stop();
        })
        .join()
        .unwrap();
        assert!(instance.cancellation().is_cancelled());
        drop(instance);
        assert!(matches!(
            session.lock(),
            Err((
                Error {
                    code: "session_terminal",
                    ..
                },
                2
            ))
        ));
    }

    #[test]
    fn panic_poison_prevents_state_reuse_without_poisoning_registry() {
        let session = session();
        let mut report = MixerVmReport::default();
        let status = unsafe {
            boundary(&mut report, || {
                let _held = session.lock()?;
                panic!("test panic during a session operation")
            })
        };
        assert_eq!(status, 4);
        assert!(matches!(
            session.lock(),
            Err((
                Error {
                    code: "session_poisoned",
                    ..
                },
                4
            ))
        ));
        assert!(session.cancellation.is_cancelled());
        assert!(registry_lock().is_ok());
    }

    #[test]
    fn unwound_creation_releases_unpublished_reservation() {
        let mut index = usize::MAX;
        let mut generation = 0;
        let mut report = MixerVmReport::default();
        let status = unsafe {
            boundary(&mut report, || {
                let reservation = Reservation::new()?;
                index = reservation.index;
                generation = reservation.generation;
                panic!("test creation failure before publication")
            })
        };
        assert_eq!(status, 4);
        let registry = registry_lock().unwrap();
        assert!(matches!(registry.0[index].state, State::Empty));
        assert_eq!(registry.0[index].generation, generation + 1);
    }
}
