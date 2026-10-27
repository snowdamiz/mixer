#![allow(dead_code)]
// Exact verification/swift-initial-profile-construction-implementation/source/vm/src/experimental/swift.rs:58-70
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct SwiftValidationUsage {
    pub input_visible_bytes: usize,
    pub source_bytes: usize,
    pub metadata_reserved: usize,
    pub scratch_reserved: usize,
    pub metadata_peak_reserved: usize,
    pub scratch_peak_reserved: usize,
    pub total_peak_reserved: usize,
    pub work_used: u64,
    pub elapsed_micros: u64,
    pub deadline_ms: u64,
}
// Exact verification/swift-initial-profile-construction-implementation/source/vm/src/experimental_wasi/mod.rs:83-101
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Resource {
    Calls,
    Transfer,
    TransferSize,
    Work,
    Iovecs,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WasiFailure {
    InvalidBudget,
    Allocation,
    InvalidArguments,
    InvalidMemory,
    Budget(Resource),
    Cancelled,
    Deadline,
    Invariant,
}
// Exact verification/swift-initial-profile-construction-implementation/source/vm/src/experimental_wasi/mod.rs:109-131
/// Capacity accounting, not RSS. Fixed state excludes the caller-shared cancellation Arc.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct WasiReservations {
    pub fixed_state_bytes: u64,
    pub staging_bytes: u64,
    pub rollback_bytes: u64,
    pub stdout_bytes: u64,
    pub stderr_bytes: u64,
    pub current_bytes: u64,
    pub peak_bytes: u64,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct WasiUsage {
    pub calls: u64,
    pub work: u64,
    pub transfer_bytes: u64,
    /// Successful OS random bytes, including bytes discarded after a later failure.
    pub random_bytes: u64,
    pub log_bytes: u64,
    /// Non-success errno outcomes and the first terminal failure/exit.
    pub failures: u64,
    pub reservations: WasiReservations,
}
// Exact verification/swift-initial-profile-construction-implementation/source/vm/src/experimental_swift_reactor/control.rs:64-230
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SwiftReservationCategory {
    RetainedSource,
    RetainedMetadata,
    Cache,
    State,
    Wasi,
    Shared,
    Construction,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct SwiftReservationUsage {
    pub current: usize,
    pub peak: usize,
}
/// Logical requested capacity and explicitly modelled headers; excludes allocator
/// overhead and is never an RSS or compiler-stack measurement.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct SwiftReservations {
    pub retained_source: SwiftReservationUsage,
    pub retained_metadata: SwiftReservationUsage,
    pub cache: SwiftReservationUsage,
    pub state: SwiftReservationUsage,
    pub wasi: SwiftReservationUsage,
    pub shared: SwiftReservationUsage,
    pub construction: SwiftReservationUsage,
    pub combined: SwiftReservationUsage,
    pub live_tickets: usize,
    pub peak_tickets: usize,
}
impl SwiftReservations {
    fn category(&self, category: SwiftReservationCategory) -> &SwiftReservationUsage {
        match category {
            SwiftReservationCategory::RetainedSource => &self.retained_source,
            SwiftReservationCategory::RetainedMetadata => &self.retained_metadata,
            SwiftReservationCategory::Cache => &self.cache,
            SwiftReservationCategory::State => &self.state,
            SwiftReservationCategory::Wasi => &self.wasi,
            SwiftReservationCategory::Shared => &self.shared,
            SwiftReservationCategory::Construction => &self.construction,
        }
    }
    fn category_mut(&mut self, category: SwiftReservationCategory) -> &mut SwiftReservationUsage {
        match category {
            SwiftReservationCategory::RetainedSource => &mut self.retained_source,
            SwiftReservationCategory::RetainedMetadata => &mut self.retained_metadata,
            SwiftReservationCategory::Cache => &mut self.cache,
            SwiftReservationCategory::State => &mut self.state,
            SwiftReservationCategory::Wasi => &mut self.wasi,
            SwiftReservationCategory::Shared => &mut self.shared,
            SwiftReservationCategory::Construction => &mut self.construction,
        }
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SwiftDeadlineOrigin {
    Run,
    Wasi,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SwiftRunStage {
    Adoption,
    Cache,
    Initialization,
    Invocation,
    Wasi,
    Cleanup,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SwiftRunResource {
    Reservation(SwiftReservationCategory),
    Combined,
    CacheEntryBytes,
    CacheEntries,
    ActivePins,
    Frames,
    Values,
    Controls,
    MemoryPages,
    CacheWork,
    ExecutionWork,
    InstructionFuel,
    HostCalls,
    Deadline,
    TicketInventory,
    OwnerIdentity,
    ExactCapacity,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SwiftRunFailureKind {
    InvalidBudget,
    Cancelled,
    Deadline,
    Allocation,
    Adoption,
    CategoryExhausted,
    CombinedExhausted,
    ResourceExhausted,
    FuelExhausted,
    WorkExhausted,
    HostCallLimit,
    PinLimit,
    FrameLimit,
    ValueLimit,
    ControlLimit,
    DecoderMismatch,
    UnsupportedEnvironment,
    GuestTrap,
    GuestExit,
    Wasi,
    Invariant,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SwiftCleanupInvariant {
    ReservationOwner,
    ReservationUnderflow,
    MissingConstruction,
    ConstructionBound,
    LiveUnderflow,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct SwiftLiveUsage {
    pub cache_entries: SwiftReservationUsage,
    pub active_pins: SwiftReservationUsage,
    pub frames: SwiftReservationUsage,
    pub values: SwiftReservationUsage,
    pub controls: SwiftReservationUsage,
    pub memory_pages: SwiftReservationUsage,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SwiftRunUsage {
    pub reservations: SwiftReservations,
    pub live: SwiftLiveUsage,
    pub cache_work: u64,
    pub execution_work: u64,
    pub instruction_fuel: u64,
    pub instructions: u64,
    pub host_calls: u64,
    /// Independent cleanup observation; never replaces the first terminal cause.
    pub cleanup_invariant: Option<SwiftCleanupInvariant>,
    pub elapsed_micros: u64,
    pub deadline_ms: u64,
    pub deadline_origin: SwiftDeadlineOrigin,
    pub deadline_overshoot_micros: u64,
    /// Historical validation observations, never added to runtime admission.
    pub validation: SwiftValidationUsage,
    /// Copied observation only. None means no context observation was supplied;
    /// no field in this snapshot is consulted for admission by RuntimeControl.
    pub wasi: Option<WasiUsage>,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SwiftRunFailure {
    pub stage: SwiftRunStage,
    pub kind: SwiftRunFailureKind,
    pub code: &'static str,
    pub function: Option<u32>,
    pub offset: Option<usize>,
    pub resource: Option<SwiftRunResource>,
    pub attempted: u64,
    pub limit: u64,
    pub observed_capacity: Option<usize>,
    pub deadline_origin: SwiftDeadlineOrigin,
    pub wasi_failure: Option<WasiFailure>,
    pub guest_exit: Option<u32>,
    pub at_failure: SwiftRunUsage,
    pub after_cleanup: Option<SwiftRunUsage>,
}
