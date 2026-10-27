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

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) enum SnapshotStopV1 {Existing(SwiftRunFailure),Cancelled,Deadline(SwiftDeadlineOrigin)}

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) enum SnapshotAdmissionErrorV1 {
    Stop(SnapshotStopV1),Owner,Layout,Arithmetic,WorkAuditPending,
    Work {used:u64,requested:u64,limit:u64},
    Storage {current:usize,additional:usize,limit:usize},
}

struct SnapshotShapeV1 {counts:[u64;9],extent:u64,blocks:u64,records:u64,words:u64}

fn checked_add_v1(a:u64,b:u64)->Result<u64,AError>{a.checked_add(b).ok_or(AError::Arithmetic)}

fn checked_mul_v1(a:u64,b:u64)->Result<u64,AError>{a.checked_mul(b).ok_or(AError::Arithmetic)}

fn snapshot_shape_v1(counts:[usize;9])->Result<SnapshotShapeV1,AError>{
    const CAPS:[u64;9]=[67108864,512,8192,34,79966,8192,4096,4096,4096];
    const WIDTHS:[u64;9]=[0,3,1,5,3,4,4,4,4];
    let mut converted=[0u64;9];let mut words=0;let mut records=0;
    for i in 0..9 {
        let n=u64::try_from(counts[i]).map_err(|_|AError::Arithmetic)?;
        if n>CAPS[i]{return Err(AError::Layout);}
        converted[i]=n;
        if i!=0 {records=checked_add_v1(records,n)?;words=checked_add_v1(words,checked_mul_v1(n,WIDTHS[i])?)?;}
    }
    let extent=checked_add_v1(checked_add_v1(2560,converted[0])?,checked_mul_v1(8,words)?)?;
    let blocks=checked_add_v1(extent/4096,u64::from(extent%4096!=0))?;
    Ok(SnapshotShapeV1 {counts:converted,extent,blocks,records,words})
}
