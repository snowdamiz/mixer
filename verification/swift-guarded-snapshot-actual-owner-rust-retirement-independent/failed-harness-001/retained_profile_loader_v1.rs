//! Private retained-source correlation under a trusted, quiescent macOS launcher.
//! No package authentication, exporter or public route. Private adoption retains full provenance.
#![allow(dead_code)]
#![allow(clippy::result_large_err)]
use super::{
    validate_swift_reactor, SwiftValidationBudget, SwiftValidationFailure, SwiftValidationUsage,
    ValidatedSwiftReactor,
};
use crate::Cancellation;
use super::control::{AdoptedProof, RuntimeControl, SwiftRunBudget, SwiftRunFailure};
use std::time::Instant;
use std::fs::File;
use std::io::{self, Read, Seek};

const HEADER: usize = 512;
const SOURCE_CAP: usize = 64 * 1024 * 1024;
const BUILD_CAP: usize = 128 * 1024;
const SESSION_CAP: usize = 64 * 1024;
const BLOCK: usize = 4096;
const ATTEMPTS: u32 = 32;
const PROCESS_CAP: usize = 16384;
const STR_CAP: usize = 4096;
const ENTRY_CAP: usize = 64;
const COMPILE_IDENTITIES: [&str; 5] = [
    "MIXER_LOADER_MANIFEST_SHA256",
    "MIXER_LOADER_COMMAND_SHA256",
    "MIXER_LOADER_COMPILE_ENV_SHA256",
    "MIXER_LOADER_COMPILER_SHA256",
    "MIXER_LOADER_COMPILER_VERSION_SHA256",
];
const COMPILED: [Option<&str>; 5] = [
    option_env!("MIXER_LOADER_MANIFEST_SHA256"),
    option_env!("MIXER_LOADER_COMMAND_SHA256"),
    option_env!("MIXER_LOADER_COMPILE_ENV_SHA256"),
    option_env!("MIXER_LOADER_COMPILER_SHA256"),
    option_env!("MIXER_LOADER_COMPILER_VERSION_SHA256"),
];
const SESSION_IDENTITY: &[u8] = b"MIXER_LOADER_EXPECTED_SESSION_SHA256";
const SESSION_NONCE: &[u8] = b"MIXER_LOADER_EXPECTED_NONCE_HEX";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
enum Role {
    Source = 0,
    Build = 1,
    Session = 2,
    Executable = 3,
    Process = 4,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Refusal {
    UnsupportedScope,
    UnsupportedBuild,
    ProcessApi,
    ProcessEncoding,
    ProcessLimit,
    DuplicateEnvironment,
    MissingIdentity,
    InvalidIdentity,
    FileType,
    FileOffset,
    FileLimit,
    AliasedFiles,
    MetadataChanged,
    Allocation,
    Capacity,
    Io,
    ShortInput,
    ExtraInput,
    Attempts,
    OverreportedRead,
    Header,
    Extent,
    Reserved,
    Digest,
    BuildIdentity,
    SessionIdentity,
    SessionNonce,
    ProcessMismatch,
    SourceIdentity,
    BudgetMismatch,
    InvalidBudget,
    Validation,
    SourceEquality,
}
#[derive(Debug)]
pub(super) struct LoaderFailureV1 {
    kind: Refusal,
    role: Role,
    offset: u64,
    attempts: u32,
    io: Option<io::Error>,
    validation: Option<SwiftValidationFailure>,
}
impl LoaderFailureV1 {
    pub(super) fn original_validation(&self) -> Option<&SwiftValidationFailure> {
        self.validation.as_ref()
    }
    pub(super) fn original_io(&self) -> Option<&io::Error> {
        self.io.as_ref()
    }

    fn new(kind: Refusal, role: Role, offset: usize, attempts: u32) -> Self {
        Self {
            kind,
            role,
            offset: offset as u64,
            attempts,
            io: None,
            validation: None,
        }
    }
    fn io(role: Role, offset: usize, attempts: u32, error: io::Error) -> Self {
        Self {
            io: Some(error),
            ..Self::new(Refusal::Io, role, offset, attempts)
        }
    }
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(super) struct LoaderUsageV1 {
    read_calls: [u64; 4],
    read_bytes: [u64; 4],
    hash_bytes: u64,
    source_equality_bytes: u64,
    allocated_peak_requested: usize,
}
/// All actual File owners return on every result. This is not a close receipt.
pub(super) struct ReturnedLoaderFilesV1 {
    pub(super) source: File,
    pub(super) build: File,
    pub(super) session: File,
    pub(super) executable: Option<File>,
}
/// No Clone, deserializer, parts extraction, public fields or arbitrary-proof mint.
pub(super) struct SelectedValidatedProfileV1 {
    proof: ValidatedSwiftReactor,
    provenance: LoaderProvenanceV1,
}
/// Opaque actual proof owner. Only the consuming carrier method below can
/// attach selected provenance. No fields, parts or owned extraction are exposed.
pub(super) struct AdoptionBodyV1 {
    proof: ValidatedSwiftReactor,
    selected: Option<LoaderProvenanceV1>,
}
impl AdoptionBodyV1 {
    pub(super) fn ordinary(proof: ValidatedSwiftReactor) -> Self {
        Self { proof, selected: None }
    }
    pub(super) fn proof(&self) -> &ValidatedSwiftReactor { &self.proof }
    pub(super) fn selected_provenance(&self) -> Option<&LoaderProvenanceV1> {
        self.selected.as_ref()
    }
}
/// Authentic selected-only capability. The tuple constructor is loader-private.
pub(super) struct SelectedSnapshotBodyV1(AdoptionBodyV1);
impl SelectedSnapshotBodyV1 {
    pub(super) fn into_adoption_body_v1(self)->AdoptionBodyV1{self.0}
}
impl SelectedValidatedProfileV1 {
    #[cfg(test)]
    pub(super) fn test_provenance_v1(&self) -> &LoaderProvenanceV1 { &self.provenance }
    pub(super) fn adopt(
        self, budget: SwiftRunBudget, started: Instant, cancellation: Cancellation,
    ) -> Result<(RuntimeControl, AdoptedProof), SwiftRunFailure> {
        RuntimeControl::adopt_body(self.into_adoption_body_v1(),budget,started,cancellation)
    }

    fn into_adoption_body_v1(self)->AdoptionBodyV1 {
        let Self { proof,provenance }=self;
        // Sole authentic selected body literal. No parts constructor is exposed.
        AdoptionBodyV1 { proof,selected:Some(provenance) }
    }
    pub(super) fn into_snapshot_scope_v1(
        self,budget:SwiftRunBudget,started:Instant,cancellation:Cancellation,
    )->Result<super::control::SnapshotScopeV1,super::control::SnapshotPreScopeFailureV1> {
        let selected_body=SelectedSnapshotBodyV1(self.into_adoption_body_v1());
        RuntimeControl::adopt_snapshot_body_v1(selected_body,budget,started,cancellation)
    }
    pub(super) fn validation_budget(&self) -> SwiftValidationBudget {
        self.provenance.validation_budget
    }
    pub(super) fn source(&self) -> &[u8] {
        self.proof.source()
    }
}
pub(crate) struct LoaderProvenanceV1 {
    validation_budget: SwiftValidationBudget,
    source_extent: u64,
    source: [u8; 32],
    manifest: [u8; 32],
    build: [u8; 32],
    session: [u8; 32],
    executable: [u8; 32],
    nonce: [u8; 32],
    identities: [FileIdentityV1; 4],
}
pub(super) struct LoaderOutcomeV1 {
    pub(super) selected: Result<SelectedValidatedProfileV1, LoaderFailureV1>,
    pub(super) files: ReturnedLoaderFilesV1,
    pub(super) usage: LoaderUsageV1,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
struct FileIdentityV1 {
    dev: u64,
    inode: u64,
    bytes: u64,
    mode: u64,
    mtime: i64,
    mtime_ns: i64,
    ctime: i64,
    ctime_ns: i64,
}
impl FileIdentityV1 {
    fn encode(self) -> [u8; 64] {
        let mut out = [0; 64];
        for (i, n) in [
            self.dev,
            self.inode,
            self.bytes,
            self.mode,
            self.mtime as u64,
            self.mtime_ns as u64,
            self.ctime as u64,
            self.ctime_ns as u64,
        ]
        .into_iter()
        .enumerate()
        {
            out[i * 8..i * 8 + 8].copy_from_slice(&n.to_le_bytes());
        }
        out
    }
}
#[derive(Clone, Copy)]
struct Section<'a> {
    bytes: &'a [u8],
}
struct BuildView<'a> {
    sections: [Section<'a>; 4],
    output_bytes: u64,
    digests: [&'a [u8]; 6],
}
struct SessionView<'a> {
    sections: [Section<'a>; 4],
    source_bytes: u64,
    budget: SwiftValidationBudget,
    nonce: &'a [u8],
    source: &'a [u8],
    build: &'a [u8],
    executable: &'a [u8],
    digests: [&'a [u8]; 4],
}
struct Bytes<const N: usize> {
    data: [u8; N],
    len: usize,
}
impl<const N: usize> Bytes<N> {
    fn new() -> Self {
        Self {
            data: [0; N],
            len: 0,
        }
    }
    fn slice(&self) -> &[u8] {
        &self.data[..self.len]
    }
    fn put(&mut self, input: &[u8]) -> Result<(), LoaderFailureV1> {
        let end = self.len.checked_add(input.len()).ok_or_else(|| {
            LoaderFailureV1::new(Refusal::ProcessLimit, Role::Process, self.len, 0)
        })?;
        if end > N {
            return Err(LoaderFailureV1::new(
                Refusal::ProcessLimit,
                Role::Process,
                end,
                0,
            ));
        }
        self.data[self.len..end].copy_from_slice(input);
        self.len = end;
        Ok(())
    }
    fn word(&mut self, n: usize) -> Result<(), LoaderFailureV1> {
        self.put(&(n as u64).to_le_bytes())
    }
}
struct ProcessObservationV1 {
    argv: Bytes<PROCESS_CAP>,
    environment: Bytes<PROCESS_CAP>,
    cwd: Bytes<STR_CAP>,
    executable_path: Bytes<STR_CAP>,
    expected_session: [u8; 32],
    nonce: [u8; 32],
}

fn word(b: &[u8], offset: usize) -> u64 {
    u64::from_le_bytes(
        b[offset..offset + 8]
            .try_into()
            .expect("prechecked fixed header"),
    )
}
fn parse_hex(value: &[u8]) -> Option<[u8; 32]> {
    if value.len() != 64 {
        return None;
    }
    let mut out = [0; 32];
    for i in 0..32 {
        let digit = |b| match b {
            b'0'..=b'9' => Some(b - b'0'),
            b'a'..=b'f' => Some(b - b'a' + 10),
            _ => None,
        };
        out[i] = digit(value[2 * i])?
            .checked_mul(16)?
            .checked_add(digit(value[2 * i + 1])?)?;
    }
    Some(out)
}
fn sections<'a>(
    b: &'a [u8],
    offsets: usize,
    role: Role,
) -> Result<[Section<'a>; 4], LoaderFailureV1> {
    let mut out = [Section { bytes: &[] }; 4];
    let mut cursor = HEADER;
    for (i, output) in out.iter_mut().enumerate() {
        let count = usize::try_from(word(b, offsets + i * 8))
            .map_err(|_| LoaderFailureV1::new(Refusal::Extent, role, offsets + i * 8, 0))?;
        let end = cursor
            .checked_add(count)
            .ok_or_else(|| LoaderFailureV1::new(Refusal::Extent, role, cursor, 0))?;
        if count == 0 || end > b.len() {
            return Err(LoaderFailureV1::new(Refusal::Extent, role, cursor, 0));
        }
        output.bytes = &b[cursor..end];
        cursor = end;
    }
    if cursor != b.len() {
        return Err(LoaderFailureV1::new(Refusal::Extent, role, cursor, 0));
    }
    Ok(out)
}
fn header(b: &[u8], magic: &[u8; 8], role: Role, cap: usize) -> Result<(), LoaderFailureV1> {
    if b.len() < HEADER || b.len() > cap {
        return Err(LoaderFailureV1::new(Refusal::Extent, role, b.len(), 0));
    }
    if &b[..8] != magic
        || word(b, 8) != 1
        || word(b, 16) != HEADER as u64
        || word(b, 24) != b.len() as u64
    {
        return Err(LoaderFailureV1::new(Refusal::Header, role, 0, 0));
    }
    Ok(())
}
fn validate_list(input: &[u8], environment: bool, compile: bool) -> Result<(), LoaderFailureV1> {
    let bad = || LoaderFailureV1::new(Refusal::ProcessEncoding, Role::Process, 0, 0);
    if input.len() < 8 || input.len() > PROCESS_CAP {
        return Err(bad());
    }
    let count = usize::try_from(word(input, 0)).map_err(|_| bad())?;
    if count > ENTRY_CAP || (!environment && count == 0) {
        return Err(bad());
    }
    let mut at = 8usize;
    let mut previous: Option<&[u8]> = None;
    for _ in 0..count {
        if at.checked_add(8).is_none_or(|end| end > input.len()) {
            return Err(bad());
        }
        let len = usize::try_from(word(input, at)).map_err(|_| bad())?;
        at += 8;
        let end = at.checked_add(len).ok_or_else(bad)?;
        if len >= STR_CAP || end > input.len() {
            return Err(bad());
        }
        let value = &input[at..end];
        if value.contains(&0) {
            return Err(bad());
        }
        at = end;
        if environment {
            let equal = value.iter().position(|b| *b == b'=').ok_or_else(bad)?;
            if equal == 0 {
                return Err(bad());
            }
            let key = &value[..equal];
            if previous.is_some_and(|prior| prior >= key) {
                return Err(bad());
            }
            previous = Some(key);
            if compile && COMPILE_IDENTITIES.iter().any(|name| name.as_bytes() == key) {
                return Err(bad());
            }
            if !compile && (key == SESSION_IDENTITY || key == SESSION_NONCE) {
                return Err(bad());
            }
        }
    }
    if at != input.len() {
        return Err(bad());
    }
    Ok(())
}
fn parse_build(b: &[u8]) -> Result<BuildView<'_>, LoaderFailureV1> {
    header(b, b"MIXLBD01", Role::Build, BUILD_CAP)?;
    if word(b, 32) != 146
        || word(b, 40) != 11
        || word(b, 80) > SOURCE_CAP as u64
        || word(b, 80) == 0
    {
        return Err(LoaderFailureV1::new(
            Refusal::BuildIdentity,
            Role::Build,
            32,
            0,
        ));
    }
    let target = b"aarch64-apple-darwin";
    if &b[88..88 + target.len()] != target
        || b[88 + target.len()..152].iter().any(|x| *x != 0)
        || b[344..HEADER].iter().any(|x| *x != 0)
    {
        return Err(LoaderFailureV1::new(Refusal::Reserved, Role::Build, 88, 0));
    }
    let parts = sections(b, 48, Role::Build)?;
    // Exact section caps include the complete manifest and complete byte encodings.
    for (part, cap) in parts.iter().zip([65536, 16384, 16384, 16384]) {
        if part.bytes.len() > cap {
            return Err(LoaderFailureV1::new(
                Refusal::Extent,
                Role::Build,
                part.bytes.len(),
                0,
            ));
        }
    }
    validate_list(parts[1].bytes, false, true)?;
    validate_list(parts[2].bytes, true, true)?;
    Ok(BuildView {
        sections: parts,
        output_bytes: word(b, 80),
        digests: [
            &b[152..184],
            &b[184..216],
            &b[216..248],
            &b[248..280],
            &b[280..312],
            &b[312..344],
        ],
    })
}
fn parse_session(b: &[u8]) -> Result<SessionView<'_>, LoaderFailureV1> {
    header(b, b"MIXLSE01", Role::Session, SESSION_CAP)?;
    if b[368..HEADER].iter().any(|x| *x != 0) {
        return Err(LoaderFailureV1::new(
            Refusal::Reserved,
            Role::Session,
            368,
            0,
        ));
    }
    let parts = sections(b, 40, Role::Session)?;
    for (part, cap) in parts.iter().zip([64, PROCESS_CAP, PROCESS_CAP, STR_CAP]) {
        if part.bytes.len() > cap {
            return Err(LoaderFailureV1::new(
                Refusal::Extent,
                Role::Session,
                part.bytes.len(),
                0,
            ));
        }
    }
    if parts[0].bytes.len() != 64 {
        return Err(LoaderFailureV1::new(Refusal::Extent, Role::Session, 40, 0));
    }
    validate_list(parts[1].bytes, false, false)?;
    validate_list(parts[2].bytes, true, false)?;
    if parts[3].bytes.first() != Some(&b'/')
        || parts[3].bytes.contains(&0)
        || parts[3].bytes.len() >= STR_CAP
    {
        return Err(LoaderFailureV1::new(
            Refusal::ProcessEncoding,
            Role::Session,
            0,
            0,
        ));
    }
    let native = |offset| {
        usize::try_from(word(b, offset))
            .map_err(|_| LoaderFailureV1::new(Refusal::InvalidBudget, Role::Session, offset, 0))
    };
    Ok(SessionView {
        sections: parts,
        source_bytes: word(b, 32),
        budget: SwiftValidationBudget {
            source_bytes: native(72)?,
            metadata_bytes: native(80)?,
            scratch_bytes: native(88)?,
            work_credits: word(b, 96),
            deadline_ms: word(b, 104),
        },
        nonce: &b[112..144],
        source: &b[144..176],
        build: &b[176..208],
        executable: &b[208..240],
        digests: [&b[240..272], &b[272..304], &b[304..336], &b[336..368]],
    })
}
fn budget_valid(b: SwiftValidationBudget) -> bool {
    let max = SwiftValidationBudget::default();
    b.source_bytes <= max.source_bytes
        && b.metadata_bytes <= max.metadata_bytes
        && b.scratch_bytes <= max.scratch_bytes
        && b.work_credits <= max.work_credits
        && b.deadline_ms <= max.deadline_ms
}

/// Complete every block or EOF request within exactly32 attempts. All attempts,
/// including Interrupted, are counted; no33rd call is made.
fn read_request<R: Read>(
    input: &mut R,
    output: &mut [u8],
    eof: bool,
    role: Role,
    base: usize,
    usage: &mut LoaderUsageV1,
) -> Result<(), LoaderFailureV1> {
    let mut used = 0;
    for attempt in 1..=ATTEMPTS {
        usage.read_calls[role as usize] += 1;
        match input.read(&mut output[used..]) {
            Ok(n) if n > output.len() - used => {
                return Err(LoaderFailureV1::new(
                    Refusal::OverreportedRead,
                    role,
                    base + used,
                    attempt,
                ))
            }
            Ok(0) if eof => return Ok(()),
            Ok(0) => {
                return Err(LoaderFailureV1::new(
                    Refusal::ShortInput,
                    role,
                    base + used,
                    attempt,
                ))
            }
            Ok(n) => {
                usage.read_bytes[role as usize] += n as u64;
                if eof {
                    return Err(LoaderFailureV1::new(
                        Refusal::ExtraInput,
                        role,
                        base,
                        attempt,
                    ));
                }
                used += n;
                if used == output.len() {
                    return Ok(());
                }
            }
            Err(error) if error.kind() == io::ErrorKind::Interrupted => {}
            Err(error) => return Err(LoaderFailureV1::io(role, base + used, attempt, error)),
        }
    }
    Err(LoaderFailureV1::new(
        Refusal::Attempts,
        role,
        base + used,
        ATTEMPTS,
    ))
}
#[cfg(target_os = "macos")]
fn identity(file: &File, role: Role) -> Result<FileIdentityV1, LoaderFailureV1> {
    use std::os::unix::fs::MetadataExt;
    let m = file
        .metadata()
        .map_err(|e| LoaderFailureV1::io(role, 0, 0, e))?;
    if !m.file_type().is_file() {
        return Err(LoaderFailureV1::new(Refusal::FileType, role, 0, 0));
    }
    Ok(FileIdentityV1 {
        dev: m.dev(),
        inode: m.ino(),
        bytes: m.len(),
        mode: m.mode() as u64,
        mtime: m.mtime(),
        mtime_ns: m.mtime_nsec(),
        ctime: m.ctime(),
        ctime_ns: m.ctime_nsec(),
    })
}
#[cfg(target_os = "macos")]
fn retained(
    file: &mut File,
    role: Role,
    cap: usize,
    initial: FileIdentityV1,
    usage: &mut LoaderUsageV1,
    other_live: usize,
) -> Result<Vec<u8>, LoaderFailureV1> {
    let position = file
        .stream_position()
        .map_err(|e| LoaderFailureV1::io(role, 0, 0, e))?;
    if position != 0 {
        return Err(LoaderFailureV1::new(
            Refusal::FileOffset,
            role,
            position as usize,
            0,
        ));
    }
    let count = usize::try_from(initial.bytes)
        .map_err(|_| LoaderFailureV1::new(Refusal::FileLimit, role, usize::MAX, 0))?;
    if count > cap {
        return Err(LoaderFailureV1::new(Refusal::FileLimit, role, count, 0));
    }
    let mut data = Vec::new();
    data.try_reserve_exact(count)
        .map_err(|_| LoaderFailureV1::new(Refusal::Allocation, role, count, 0))?;
    if data.capacity() != count {
        return Err(LoaderFailureV1::new(
            Refusal::Capacity,
            role,
            data.capacity(),
            0,
        ));
    }
    usage.allocated_peak_requested = usage.allocated_peak_requested.max(other_live + count);
    data.resize(count, 0);
    for (index, block) in data.chunks_mut(BLOCK).enumerate() {
        read_request(file, block, false, role, index * BLOCK, usage)?;
    }
    read_request(file, &mut [0; 1], true, role, count, usage)?;
    if identity(file, role)? != initial {
        return Err(LoaderFailureV1::new(
            Refusal::MetadataChanged,
            role,
            count,
            0,
        ));
    }
    Ok(data)
}

#[cfg(target_os = "macos")]
mod platform {
    use super::*;
    use std::ffi::{c_char, c_int, c_void};
    #[link(name = "System")]
    unsafe extern "C" {
        fn CC_SHA256(data: *const c_void, len: u32, md: *mut u8) -> *mut u8;
        fn _NSGetArgc() -> *mut c_int;
        fn _NSGetArgv() -> *mut *mut *mut c_char;
        fn _NSGetEnviron() -> *mut *mut *mut c_char;
        fn _NSGetExecutablePath(buf: *mut c_char, size: *mut u32) -> c_int;
        fn getcwd(buf: *mut c_char, size: usize) -> *mut c_char;
    }
    pub(super) fn hash(
        input: &[u8],
        usage: &mut LoaderUsageV1,
    ) -> Result<[u8; 32], LoaderFailureV1> {
        let len = u32::try_from(input.len())
            .map_err(|_| LoaderFailureV1::new(Refusal::Extent, Role::Process, input.len(), 0))?;
        let mut out = [0; 32];
        // Official CommonCrypto ABI: u32 length,32 writable digest bytes; input
        // remains alive/read-only and output disjoint for this synchronous call.
        let result = unsafe { CC_SHA256(input.as_ptr().cast(), len, out.as_mut_ptr()) };
        if result != out.as_mut_ptr() {
            return Err(LoaderFailureV1::new(
                Refusal::ProcessApi,
                Role::Process,
                0,
                0,
            ));
        }
        usage.hash_bytes += input.len() as u64;
        Ok(out)
    }
    pub(super) unsafe fn c_string<'a>(p: *const c_char) -> Result<&'a [u8], LoaderFailureV1> {
        if p.is_null() {
            return Err(LoaderFailureV1::new(
                Refusal::ProcessApi,
                Role::Process,
                0,
                0,
            ));
        }
        // Caller supplies an OS-owned valid NUL-terminated process string and
        // forbids concurrent argv/environ mutation. Scan stops at first NUL;
        // reading at most4096 bytes bounds supported input, not invalid pointers.
        for n in 0..STR_CAP {
            if unsafe { *p.add(n) } == 0 {
                return Ok(unsafe { std::slice::from_raw_parts(p.cast(), n) });
            }
        }
        Err(LoaderFailureV1::new(
            Refusal::ProcessLimit,
            Role::Process,
            STR_CAP,
            0,
        ))
    }
    pub(super) fn observe() -> Result<ProcessObservationV1, LoaderFailureV1> {
        let mut argv = Bytes::new();
        let mut environment = Bytes::new();
        let mut cwd = Bytes::new();
        let mut executable_path = Bytes::new();
        // Darwin returns valid process-lifetime argc/argv/environ pointer slots.
        // Supported scope has no concurrent mutation or callbacks; every count,
        // string and serialized byte extent is checked before retained copying.
        let (argc, args, vars) = unsafe {
            let ac = _NSGetArgc();
            let av = _NSGetArgv();
            let en = _NSGetEnviron();
            if ac.is_null() || av.is_null() || en.is_null() {
                return Err(LoaderFailureV1::new(
                    Refusal::ProcessApi,
                    Role::Process,
                    0,
                    0,
                ));
            }
            (*ac, *av, *en)
        };
        if !(1..=ENTRY_CAP as i32).contains(&argc) || args.is_null() || vars.is_null() {
            return Err(LoaderFailureV1::new(
                Refusal::ProcessLimit,
                Role::Process,
                0,
                0,
            ));
        }
        argv.word(argc as usize)?;
        for n in 0..argc as usize {
            let value = unsafe { c_string(*args.add(n))? };
            argv.word(value.len())?;
            argv.put(value)?;
        }
        let mut raw = Bytes::<PROCESS_CAP>::new();
        let mut entries = [(0usize, 0usize, 0usize); ENTRY_CAP];
        let mut count = 0;
        let mut expected_session = None;
        let mut nonce = None;
        let mut terminated = false;
        for n in 0..=ENTRY_CAP {
            let ptr = unsafe { *vars.add(n) };
            if ptr.is_null() {
                terminated = true;
                break;
            }
            if n == ENTRY_CAP {
                return Err(LoaderFailureV1::new(
                    Refusal::ProcessLimit,
                    Role::Process,
                    n,
                    0,
                ));
            }
            let value = unsafe { c_string(ptr)? };
            let equals = value.iter().position(|x| *x == b'=').ok_or_else(|| {
                LoaderFailureV1::new(Refusal::ProcessEncoding, Role::Process, n, 0)
            })?;
            if equals == 0 {
                return Err(LoaderFailureV1::new(
                    Refusal::ProcessEncoding,
                    Role::Process,
                    n,
                    0,
                ));
            }
            let key = &value[..equals];
            let payload = &value[equals + 1..];
            if key == SESSION_IDENTITY || key == SESSION_NONCE {
                let target = if key == SESSION_IDENTITY {
                    &mut expected_session
                } else {
                    &mut nonce
                };
                if target.is_some() {
                    return Err(LoaderFailureV1::new(
                        Refusal::DuplicateEnvironment,
                        Role::Process,
                        n,
                        0,
                    ));
                }
                *target = Some(parse_hex(payload).ok_or_else(|| {
                    LoaderFailureV1::new(Refusal::InvalidIdentity, Role::Process, n, 0)
                })?);
                continue;
            }
            let begin = raw.len;
            raw.put(value)?;
            entries[count] = (begin, value.len(), equals);
            count += 1;
        }
        if !terminated {
            return Err(LoaderFailureV1::new(
                Refusal::ProcessLimit,
                Role::Process,
                ENTRY_CAP,
                0,
            ));
        }
        encode_environment(&raw.data, &mut entries[..count], &mut environment)?;
        // Caller-provided4096-byte buffers avoid unbounded PathBuf allocation.
        let mut size = STR_CAP as u32;
        let result =
            unsafe { _NSGetExecutablePath(executable_path.data.as_mut_ptr().cast(), &mut size) };
        if result != 0 || size as usize > STR_CAP {
            return Err(LoaderFailureV1::new(
                Refusal::ProcessLimit,
                Role::Executable,
                size as usize,
                0,
            ));
        }
        executable_path.len = executable_path
            .data
            .iter()
            .position(|x| *x == 0)
            .ok_or_else(|| {
                LoaderFailureV1::new(Refusal::ProcessEncoding, Role::Executable, STR_CAP, 0)
            })?;
        if executable_path.len == 0 || executable_path.data[0] != b'/' {
            return Err(LoaderFailureV1::new(
                Refusal::ProcessEncoding,
                Role::Executable,
                0,
                0,
            ));
        }
        if unsafe { getcwd(cwd.data.as_mut_ptr().cast(), STR_CAP) }.is_null() {
            return Err(LoaderFailureV1::io(
                Role::Process,
                0,
                0,
                io::Error::last_os_error(),
            ));
        }
        cwd.len = cwd.data.iter().position(|x| *x == 0).ok_or_else(|| {
            LoaderFailureV1::new(Refusal::ProcessEncoding, Role::Process, STR_CAP, 0)
        })?;
        if cwd.len == 0 || cwd.data[0] != b'/' {
            return Err(LoaderFailureV1::new(
                Refusal::ProcessEncoding,
                Role::Process,
                0,
                0,
            ));
        }
        Ok(ProcessObservationV1 {
            argv,
            environment,
            cwd,
            executable_path,
            expected_session: expected_session.ok_or_else(|| {
                LoaderFailureV1::new(Refusal::MissingIdentity, Role::Process, 0, 0)
            })?,
            nonce: nonce.ok_or_else(|| {
                LoaderFailureV1::new(Refusal::MissingIdentity, Role::Process, 0, 0)
            })?,
        })
    }
}
fn encode_environment(
    raw: &[u8],
    entries: &mut [(usize, usize, usize)],
    out: &mut Bytes<PROCESS_CAP>,
) -> Result<(), LoaderFailureV1> {
    // Closed raw-byte encoding: count:u64, then len:u64 + exact key=value bytes;
    // order is lexicographic key bytes, duplicate keys refuse, no UTF8 conversion.
    for i in 1..entries.len() {
        let mut j = i;
        while j > 0 {
            let a = entries[j - 1];
            let b = entries[j];
            if raw[a.0..a.0 + a.2] <= raw[b.0..b.0 + b.2] {
                break;
            }
            entries.swap(j - 1, j);
            j -= 1;
        }
    }
    out.word(entries.len())?;
    let mut previous: Option<&[u8]> = None;
    for &(begin, len, key_len) in entries.iter() {
        let value = raw.get(begin..begin + len).ok_or_else(|| {
            LoaderFailureV1::new(Refusal::ProcessEncoding, Role::Process, begin, 0)
        })?;
        if key_len == 0 || key_len >= len || value[key_len] != b'=' {
            return Err(LoaderFailureV1::new(
                Refusal::ProcessEncoding,
                Role::Process,
                begin,
                0,
            ));
        }
        let key = &value[..key_len];
        if previous == Some(key) {
            return Err(LoaderFailureV1::new(
                Refusal::DuplicateEnvironment,
                Role::Process,
                begin,
                0,
            ));
        }
        previous = Some(key);
        out.word(value.len())?;
        out.put(value)?;
    }
    Ok(())
}
#[cfg(target_os = "macos")]
fn load_inner(
    files: &mut ReturnedLoaderFilesV1,
    budget: SwiftValidationBudget,
    cancellation: &Cancellation,
    usage: &mut LoaderUsageV1,
) -> Result<SelectedValidatedProfileV1, LoaderFailureV1> {
    use std::os::unix::ffi::OsStrExt;
    if !budget_valid(budget) {
        return Err(LoaderFailureV1::new(
            Refusal::InvalidBudget,
            Role::Source,
            0,
            0,
        ));
    }
    let observed = platform::observe()?;
    let executable = File::open(std::path::Path::new(std::ffi::OsStr::from_bytes(
        observed.executable_path.slice(),
    )))
    .map_err(|e| LoaderFailureV1::io(Role::Executable, 0, 0, e))?;
    files.executable = Some(executable);
    let identities = [
        identity(&files.source, Role::Source)?,
        identity(&files.build, Role::Build)?,
        identity(&files.session, Role::Session)?,
        identity(
            files.executable.as_ref().expect("owned opened file"),
            Role::Executable,
        )?,
    ];
    for i in 0..4 {
        for j in 0..i {
            if identities[i].dev == identities[j].dev && identities[i].inode == identities[j].inode
            {
                return Err(LoaderFailureV1::new(
                    Refusal::AliasedFiles,
                    Role::Source,
                    i,
                    0,
                ));
            }
        }
    }
    let build = retained(
        &mut files.build,
        Role::Build,
        BUILD_CAP,
        identities[1],
        usage,
        0,
    )?;
    let session = retained(
        &mut files.session,
        Role::Session,
        SESSION_CAP,
        identities[2],
        usage,
        build.capacity(),
    )?;
    let b = parse_build(&build)?;
    let s = parse_session(&session)?;
    let embedded = COMPILED.map(|v| v.and_then(|s| parse_hex(s.as_bytes())));
    if embedded.iter().any(Option::is_none) {
        return Err(LoaderFailureV1::new(
            Refusal::UnsupportedBuild,
            Role::Build,
            0,
            0,
        ));
    }
    // Embedded hash order differs intentionally from header compiler/version order.
    for (index, claim) in [
        b.digests[0],
        b.digests[1],
        b.digests[2],
        b.digests[4],
        b.digests[3],
    ]
    .into_iter()
    .enumerate()
    {
        if claim != embedded[index].expect("all present") {
            return Err(LoaderFailureV1::new(
                Refusal::BuildIdentity,
                Role::Build,
                index,
                0,
            ));
        }
    }
    for i in 0..4 {
        if platform::hash(b.sections[i].bytes, usage)? != b.digests[i] {
            return Err(LoaderFailureV1::new(Refusal::Digest, Role::Build, i, 0));
        }
    }
    let build_digest = platform::hash(&build, usage)?;
    let session_digest = platform::hash(&session, usage)?;
    if session_digest != observed.expected_session {
        return Err(LoaderFailureV1::new(
            Refusal::SessionIdentity,
            Role::Session,
            0,
            0,
        ));
    }
    if s.nonce != observed.nonce {
        return Err(LoaderFailureV1::new(
            Refusal::SessionNonce,
            Role::Session,
            112,
            0,
        ));
    }
    if s.build != build_digest {
        return Err(LoaderFailureV1::new(
            Refusal::BuildIdentity,
            Role::Session,
            176,
            0,
        ));
    }
    if s.budget != budget {
        return Err(LoaderFailureV1::new(
            Refusal::BudgetMismatch,
            Role::Session,
            72,
            0,
        ));
    }
    for i in 0..4 {
        if platform::hash(s.sections[i].bytes, usage)? != s.digests[i] {
            return Err(LoaderFailureV1::new(Refusal::Digest, Role::Session, i, 0));
        }
    }
    if s.sections[0].bytes != identities[0].encode() || s.source_bytes != identities[0].bytes {
        return Err(LoaderFailureV1::new(
            Refusal::SourceIdentity,
            Role::Source,
            0,
            0,
        ));
    }
    if s.sections[1].bytes != observed.argv.slice()
        || s.sections[2].bytes != observed.environment.slice()
        || s.sections[3].bytes != observed.cwd.slice()
    {
        return Err(LoaderFailureV1::new(
            Refusal::ProcessMismatch,
            Role::Process,
            0,
            0,
        ));
    }
    let executable = retained(
        files.executable.as_mut().expect("opened owner"),
        Role::Executable,
        SOURCE_CAP,
        identities[3],
        usage,
        build.capacity() + session.capacity(),
    )?;
    let executable_digest = platform::hash(&executable, usage)?;
    if b.output_bytes != identities[3].bytes
        || b.digests[5] != executable_digest
        || s.executable != executable_digest
    {
        return Err(LoaderFailureV1::new(
            Refusal::BuildIdentity,
            Role::Executable,
            0,
            0,
        ));
    }
    drop(executable); // executable bytes never coexist with source/proof buffers.
    let input = retained(
        &mut files.source,
        Role::Source,
        budget.source_bytes,
        identities[0],
        usage,
        build.capacity() + session.capacity(),
    )?;
    let source_digest = platform::hash(&input, usage)?;
    if s.source != source_digest {
        return Err(LoaderFailureV1::new(
            Refusal::SourceIdentity,
            Role::Source,
            0,
            0,
        ));
    }
    let validation = validate_swift_reactor(&input, budget, cancellation);
    let baseline = build.capacity() + session.capacity() + input.capacity();
    let proof = match validation {
        Ok(proof) => {
            record_validation_peak(usage, baseline, proof.usage());
            proof
        }
        Err(failure) => {
            record_validation_peak(usage, baseline, failure.usage);
            return Err(LoaderFailureV1 {
                validation: Some(failure),
                ..LoaderFailureV1::new(Refusal::Validation, Role::Source, failure.offset, 0)
            });
        }
    };
    // Both immutable buffers remain live for the complete equality check.
    if !source_bytes_equal(&proof, &input) {
        return Err(LoaderFailureV1::new(
            Refusal::SourceEquality,
            Role::Source,
            0,
            0,
        ));
    }
    usage.source_equality_bytes = input.len() as u64;
    final_metadata_recheck_v1(files, &identities)?;
    Ok(SelectedValidatedProfileV1 {
        proof,
        provenance: LoaderProvenanceV1 {
            validation_budget: budget,
            source_extent: input.len() as u64,
            source: source_digest,
            manifest: embedded[0].expect("checked"),
            build: build_digest,
            session: session_digest,
            executable: executable_digest,
            nonce: observed.nonce,
            identities,
        },
    })
}
// Metadata errors retain their original typed payload and exact role. Mismatch
// offsets remain the original identity-array coordinate (0..3).
fn check_final_identity_v1(
    role: Role, index: usize, expected: FileIdentityV1,
    observed: Result<FileIdentityV1, LoaderFailureV1>,
) -> Result<(), LoaderFailureV1> {
    if observed? != expected {
        return Err(LoaderFailureV1::new(Refusal::MetadataChanged, role, index, 0));
    }
    Ok(())
}
#[cfg(target_os = "macos")]
fn final_metadata_recheck_v1(
    files: &ReturnedLoaderFilesV1, identities: &[FileIdentityV1; 4],
) -> Result<(), LoaderFailureV1> {
    for (index, (file, role)) in [
        (&files.source, Role::Source), (&files.build, Role::Build),
        (&files.session, Role::Session),
        (files.executable.as_ref().expect("opened owner"), Role::Executable),
    ].into_iter().enumerate() {
        check_final_identity_v1(role, index, identities[index], identity(file, role))?;
    }
    Ok(())
}
fn record_validation_peak(
    usage: &mut LoaderUsageV1,
    input_and_preimages: usize,
    validation: SwiftValidationUsage,
) {
    // The original usage survives both return branches. Peak components are
    // conservatively summed; this is a logical requested-storage observation.
    usage.allocated_peak_requested = usage.allocated_peak_requested.max(
        input_and_preimages
            + validation.source_bytes
            + validation.metadata_peak_reserved
            + validation.scratch_peak_reserved,
    );
}
fn source_bytes_equal(proof: &ValidatedSwiftReactor, retained: &[u8]) -> bool {
    proof.source() == retained
}
pub(super) fn load_selected_retained_profile_v1(
    source: File,
    build: File,
    session: File,
    budget: SwiftValidationBudget,
    cancellation: &Cancellation,
) -> LoaderOutcomeV1 {
    let mut files = ReturnedLoaderFilesV1 {
        source,
        build,
        session,
        executable: None,
    };
    let mut usage = LoaderUsageV1::default();
    #[cfg(target_os = "macos")]
    let selected = load_inner(&mut files, budget, cancellation, &mut usage);
    #[cfg(not(target_os = "macos"))]
    let selected = {
        let _ = (budget, cancellation);
        Err(LoaderFailureV1::new(
            Refusal::UnsupportedScope,
            Role::Source,
            0,
            0,
        ))
    };
    LoaderOutcomeV1 {
        selected,
        files,
        usage,
    }
}
// Conservative named source-object places, including explicit argument,
// return, result, refusal and move overlap. Not physical compiler stack/RSS,
// allocator overhead, a runtime reservation or authority from the old165 list.
struct ObservationPlacesV1 {
    caller: ProcessObservationV1,
    return_expression: ProcessObservationV1,
    call_result: Result<ProcessObservationV1, LoaderFailureV1>,
    argv: Bytes<PROCESS_CAP>,
    environment: Bytes<PROCESS_CAP>,
    cwd: Bytes<STR_CAP>,
    executable: Bytes<STR_CAP>,
    environment_raw: Bytes<PROCESS_CAP>,
    entries: [(usize, usize, usize); ENTRY_CAP],
    session: Option<[u8; 32]>,
    nonce: Option<[u8; 32]>,
    pointers_and_cursors: [usize; 24],
}
struct LoaderPlacesV1 {
    file_arguments: [File; 3],
    files: ReturnedLoaderFilesV1,
    return_expression: LoaderOutcomeV1,
    returned: LoaderOutcomeV1,
    caller_result: Option<LoaderOutcomeV1>,
    selection_result: Result<SelectedValidatedProfileV1, LoaderFailureV1>,
    carrier_literal: SelectedValidatedProfileV1,
    validation_result: Result<ValidatedSwiftReactor, SwiftValidationFailure>,
    proof: ValidatedSwiftReactor,
    provenance_literal: LoaderProvenanceV1,
    build_view: BuildView<'static>,
    build_result: Result<BuildView<'static>, LoaderFailureV1>,
    session_view: SessionView<'static>,
    session_result: Result<SessionView<'static>, LoaderFailureV1>,
    vec_headers: [Vec<u8>; 4],
    read_results: [Result<Vec<u8>, LoaderFailureV1>; 4],
    refusal_places: [LoaderFailureV1; 8],
    validation_failure_places: [SwiftValidationFailure; 4],
    validation_usage_places: [SwiftValidationUsage; 2],
    budgets: [SwiftValidationBudget; 3],
    identities: [FileIdentityV1; 4],
    embedded: [Option<[u8; 32]>; 5],
    hash_output_places: [[u8; 32]; 12],
    metadata: [std::fs::Metadata; 2],
    metadata_results: [Result<std::fs::Metadata, io::Error>; 3],
    io_results: [Result<usize, io::Error>; 4],
    position_results: [Result<u64, io::Error>; 2],
    error_places: [io::Error; 4],
    scalar_and_borrow_places: [usize; 128],
}
struct ReadHashPlacesV1 {
    eof: [u8; 1],
    hash: [u8; 32],
    hash_return: [u8; 32],
    hash_result: Result<[u8; 32], LoaderFailureV1>,
    chunk_iterator: std::iter::Enumerate<std::slice::ChunksMut<'static, u8>>,
    stream_result: Result<usize, io::Error>,
    position_result: Result<u64, io::Error>,
    metadata_result: Result<FileIdentityV1, LoaderFailureV1>,
    arguments_cursors_loops_and_borrows: [usize; 64],
}
fn fixed_named_storage_bound_v1() -> usize {
    std::mem::size_of::<ObservationPlacesV1>()
        + std::mem::size_of::<LoaderPlacesV1>()
        + std::mem::size_of::<ReadHashPlacesV1>()
        + std::mem::size_of::<FinalRecheckPlacesV1>()
}
#[cfg(test)]
#[path = "retained_profile_loader_v1_tests.rs"]
mod tests;

// Conservative complete new ingress and transfer source places. Whole owners
// are counted independently instead of borrowing containing padding.
struct AdoptionEntryPlacesV1 {
    ordinary_proof: ValidatedSwiftReactor,
    ordinary_body_return: AdoptionBodyV1,
    selected_carrier: SelectedValidatedProfileV1,
    selected_proof_pattern: ValidatedSwiftReactor,
    selected_provenance_pattern: LoaderProvenanceV1,
    selected_some: Option<LoaderProvenanceV1>,
    selected_body_literal: AdoptionBodyV1,
    inner_body_argument: AdoptionBodyV1,
    budgets: [SwiftRunBudget; 3],
    started: [Instant; 3],
    cancellations: [Cancellation; 3],
    validation_return: SwiftValidationUsage,
    proof_borrows: [&'static ValidatedSwiftReactor; 2],
    body_borrow: &'static AdoptionBodyV1,
    provenance_borrow: Option<&'static LoaderProvenanceV1>,
}
struct AdoptionMovePlacesV1 {
    adopted_literal: AdoptedProof,
    pair_literal: (RuntimeControl, AdoptedProof),
    inner_return: Result<(RuntimeControl, AdoptedProof), SwiftRunFailure>,
    ordinary_return: Result<(RuntimeControl, AdoptedProof), SwiftRunFailure>,
    selected_return: Result<(RuntimeControl, AdoptedProof), SwiftRunFailure>,
    caller_pair: (RuntimeControl, AdoptedProof),
    caller_option: Option<(RuntimeControl, AdoptedProof)>,
    caller_result: Result<(RuntimeControl, AdoptedProof), SwiftRunFailure>,
}
struct FinalRecheckPlacesV1 {
    arguments: (&'static ReturnedLoaderFilesV1, &'static [FileIdentityV1;4]),
    array: [(&'static File, Role);4],
    iterator: std::iter::Enumerate<std::array::IntoIter<(&'static File,Role),4>>,
    item: Option<(usize,(&'static File,Role))>,
    pattern: (usize,(&'static File,Role)),
    expected_argument: FileIdentityV1,
    observed_result: Result<FileIdentityV1,LoaderFailureV1>,
    helper_argument: Result<FileIdentityV1,LoaderFailureV1>,
    observed_pattern: FileIdentityV1,
    result_places: [Result<(),LoaderFailureV1>;3],
    mismatch_literal: LoaderFailureV1,
}
pub(super) const ADOPTION_ENTRY_BYTES_V1: usize = std::mem::size_of::<AdoptionEntryPlacesV1>();
pub(super) const ADOPTION_MOVE_BYTES_V1: usize = std::mem::size_of::<AdoptionMovePlacesV1>();
pub(super) static ADOPTION_LAYOUTS_V1: [(&str,usize,usize); 36] = [
    ("SelectedValidatedProfileV1",std::mem::size_of::<SelectedValidatedProfileV1>(),std::mem::align_of::<SelectedValidatedProfileV1>()),
    ("LoaderProvenanceV1",std::mem::size_of::<LoaderProvenanceV1>(),std::mem::align_of::<LoaderProvenanceV1>()),
    ("LoaderFailureV1",std::mem::size_of::<LoaderFailureV1>(),std::mem::align_of::<LoaderFailureV1>()),
    ("LoaderOutcomeV1",std::mem::size_of::<LoaderOutcomeV1>(),std::mem::align_of::<LoaderOutcomeV1>()),
    ("ReturnedLoaderFilesV1",std::mem::size_of::<ReturnedLoaderFilesV1>(),std::mem::align_of::<ReturnedLoaderFilesV1>()),
    ("LoaderUsageV1",std::mem::size_of::<LoaderUsageV1>(),std::mem::align_of::<LoaderUsageV1>()),
    ("FileIdentityV1",std::mem::size_of::<FileIdentityV1>(),std::mem::align_of::<FileIdentityV1>()),
    ("BuildView",std::mem::size_of::<BuildView<'static>>(),std::mem::align_of::<BuildView<'static>>()),
    ("SessionView",std::mem::size_of::<SessionView<'static>>(),std::mem::align_of::<SessionView<'static>>()),
    ("ProcessObservationV1",std::mem::size_of::<ProcessObservationV1>(),std::mem::align_of::<ProcessObservationV1>()),
    ("BytesProcess",std::mem::size_of::<Bytes<PROCESS_CAP>>(),std::mem::align_of::<Bytes<PROCESS_CAP>>()),
    ("BytesPath",std::mem::size_of::<Bytes<STR_CAP>>(),std::mem::align_of::<Bytes<STR_CAP>>()),
    ("EnvironmentEntries",std::mem::size_of::<[(usize,usize,usize);ENTRY_CAP]>(),std::mem::align_of::<[(usize,usize,usize);ENTRY_CAP]>()),
    ("ResultSelected",std::mem::size_of::<Result<SelectedValidatedProfileV1,LoaderFailureV1>>(),std::mem::align_of::<Result<SelectedValidatedProfileV1,LoaderFailureV1>>()),
    ("ValidationResult",std::mem::size_of::<Result<ValidatedSwiftReactor,SwiftValidationFailure>>(),std::mem::align_of::<Result<ValidatedSwiftReactor,SwiftValidationFailure>>()),
    ("VecHeader",std::mem::size_of::<Vec<u8>>(),std::mem::align_of::<Vec<u8>>()),
    ("File",std::mem::size_of::<File>(),std::mem::align_of::<File>()),
    ("OptionFile",std::mem::size_of::<Option<File>>(),std::mem::align_of::<Option<File>>()),
    ("ValidationBudget",std::mem::size_of::<SwiftValidationBudget>(),std::mem::align_of::<SwiftValidationBudget>()),
    ("ValidationFailure",std::mem::size_of::<SwiftValidationFailure>(),std::mem::align_of::<SwiftValidationFailure>()),
    ("ObservationPlaces",std::mem::size_of::<ObservationPlacesV1>(),std::mem::align_of::<ObservationPlacesV1>()),
    ("LoaderPlaces",std::mem::size_of::<LoaderPlacesV1>(),std::mem::align_of::<LoaderPlacesV1>()),
    ("ReadHashPlaces",std::mem::size_of::<ReadHashPlacesV1>(),std::mem::align_of::<ReadHashPlacesV1>()),
    ("AdoptionBodyV1",std::mem::size_of::<AdoptionBodyV1>(),std::mem::align_of::<AdoptionBodyV1>()),
    ("OptionalProvenance",std::mem::size_of::<Option<LoaderProvenanceV1>>(),std::mem::align_of::<Option<LoaderProvenanceV1>>()),
    ("BorrowedProvenance",std::mem::size_of::<Option<&'static LoaderProvenanceV1>>(),std::mem::align_of::<Option<&'static LoaderProvenanceV1>>()),
    ("AdoptionEntryPlacesV1",std::mem::size_of::<AdoptionEntryPlacesV1>(),std::mem::align_of::<AdoptionEntryPlacesV1>()),
    ("AdoptionMovePlacesV1",std::mem::size_of::<AdoptionMovePlacesV1>(),std::mem::align_of::<AdoptionMovePlacesV1>()),
    ("AdoptionPair",std::mem::size_of::<(RuntimeControl,AdoptedProof)>(),std::mem::align_of::<(RuntimeControl,AdoptedProof)>()),
    ("AdoptionResult",std::mem::size_of::<Result<(RuntimeControl,AdoptedProof),SwiftRunFailure>>(),std::mem::align_of::<Result<(RuntimeControl,AdoptedProof),SwiftRunFailure>>()),
    ("OptionalAdoptionPair",std::mem::size_of::<Option<(RuntimeControl,AdoptedProof)>>(),std::mem::align_of::<Option<(RuntimeControl,AdoptedProof)>>()),
    ("BorrowedAdoptionBody",std::mem::size_of::<&'static AdoptionBodyV1>(),std::mem::align_of::<&'static AdoptionBodyV1>()),
    ("BorrowedSelectedCarrier",std::mem::size_of::<&'static SelectedValidatedProfileV1>(),std::mem::align_of::<&'static SelectedValidatedProfileV1>()),
    ("FinalRecheckPlacesV1",std::mem::size_of::<FinalRecheckPlacesV1>(),std::mem::align_of::<FinalRecheckPlacesV1>()),
    ("AdoptionCleanupPlacesV1",super::control::ADOPTION_CLEANUP_BYTES_V1,super::control::ADOPTION_CLEANUP_ALIGNMENT_V1),
    ("FullProvenanceEncoding",std::mem::size_of::<[u8;496]>(),std::mem::align_of::<[u8;496]>()),
];

// Test-only complete field encoding. This borrows real provenance and is never
// parsed into authority, object memory, a proof, a body or a carrier.
#[cfg(test)]
pub(super) fn test_provenance_encoding_v1(p: &LoaderProvenanceV1) -> [u8;496] {
    let mut bytes=[0u8;496];
    let mut at=0;
    for value in [p.validation_budget.source_bytes as u64,
        p.validation_budget.metadata_bytes as u64,p.validation_budget.scratch_bytes as u64,
        p.validation_budget.work_credits,p.validation_budget.deadline_ms,p.source_extent] {
        bytes[at..at+8].copy_from_slice(&value.to_le_bytes());at+=8;
    }
    for digest in [&p.source,&p.manifest,&p.build,&p.session,&p.executable,&p.nonce] {
        bytes[at..at+32].copy_from_slice(digest);at+=32;
    }
    for identity in p.identities {
        bytes[at..at+64].copy_from_slice(&identity.encode());at+=64;
    }
    assert_eq!(at,bytes.len());bytes
}

impl LoaderProvenanceV1 {
 pub(crate) fn snapshot_encode_v2(&self,out:&mut[u8;576])->Result<(),()> {
  out.fill(0);out[..8].copy_from_slice(b"MIXLPR01");
  let limits=&self.validation_budget;
  let values=[1,576,self.source_extent,u64::try_from(limits.source_bytes).map_err(|_|())?,
   u64::try_from(limits.metadata_bytes).map_err(|_|())?,u64::try_from(limits.scratch_bytes).map_err(|_|())?,
   limits.work_credits,limits.deadline_ms];
  for (i,n) in values.iter().enumerate(){out[8+i*8..16+i*8].copy_from_slice(&n.to_le_bytes());}
  for (i,value) in [&self.source,&self.manifest,&self.build,&self.session,&self.executable,&self.nonce].iter().enumerate(){
   out[72+i*32..104+i*32].copy_from_slice(*value);
  }
  for (i,identity) in self.identities.iter().enumerate(){out[264+i*64..328+i*64].copy_from_slice(&identity.encode());}
  Ok(())
 }
}

// Root-released append-only private measurement seam. No behavior calls.
#[cfg(mixer_snapshot_composition_layout)]
#[used]
static MIXER_COMPOSITION_LOADER_HELPER_LAYOUTS_V1:[usize;8]=[
 std::mem::size_of::<FileIdentityV1>(),std::mem::align_of::<FileIdentityV1>(), // FileIdentityV1
 std::mem::size_of::<std::iter::Enumerate<std::slice::Iter<'static,FileIdentityV1>>>(),std::mem::align_of::<std::iter::Enumerate<std::slice::Iter<'static,FileIdentityV1>>>(), // std::iter::Enumerate<std::slice::Iter<'static,FileIdentityV1>>
 std::mem::size_of::<(usize,&FileIdentityV1)>(),std::mem::align_of::<(usize,&FileIdentityV1)>(), // (usize,&FileIdentityV1)
 std::mem::size_of::<&FileIdentityV1>(),std::mem::align_of::<&FileIdentityV1>(), // &FileIdentityV1
];

// Actual private ownership core. Native startup/allocator/source authority is
// intentionally unselected; integer prices and test guards cannot select it.
mod prepaid_input_owner_v1 {
    use super::*;
    use std::cell::Cell;
    use std::path::Path;
    use crate::experimental_swift_reactor::cache::SnapshotClaimsV1 as UnverifiedProfileDigestBytesV1;

    #[derive(Clone, Copy, Debug, PartialEq, Eq)]
    pub(in crate::experimental_swift_reactor) enum BootstrapFailureV1 {
        BootstrapPolicyPending, NativeStartupBridgePending, NativeAllocatorBridgePending,
        CompileClosureAuthorityPending, Overflow, InsufficientAcquisitionWork,
        InsufficientCleanupWork, InsufficientStorage, AlreadyReserved, AlreadyAttempted,
        Incomplete, AliasedIdentity, Extent, Offset, Packet, Nul, MetadataChanged,
        Io, Allocation, ShortInput, ExtraInput, Attempts, OverreportedRead,
        Record, Digest, BodyRole, LiveOwner, Correlation(usize), RetirementIncomplete,
    }
    // Complete originals are retained, never formatted/coerced into a scalar.
    struct OriginalAcquisitionFailureV1 {
        kind: BootstrapFailureV1, slot: usize, offset: usize, attempts: u32,
        io: Option<io::Error>, allocation: Option<std::collections::TryReserveError>,
        loader: Option<LoaderFailureV1>,
    }
    impl OriginalAcquisitionFailureV1 {
        fn new(kind: BootstrapFailureV1, slot: usize) -> Self {
            Self { kind, slot, offset: 0, attempts: 0, io: None, allocation: None, loader: None }
        }
        fn io(slot: usize, offset: usize, attempts: u32, original: io::Error) -> Self {
            Self { io: Some(original), offset, attempts, ..Self::new(BootstrapFailureV1::Io, slot) }
        }
    }
    struct FixtureBootstrapPolicyV1 {
        role_caps: [usize; 12], path_caps: [usize; 5], packet_cap: usize,
        validation: SwiftValidationBudget, product: SwiftRunBudget,
        allocation_slack: usize, original_failure_backing: usize,
        bridge: BridgePricesV1,
    }
    impl FixtureBootstrapPolicyV1 {
        fn selected_fixture_v1() -> Result<Self, BootstrapFailureV1> {
            Err(BootstrapFailureV1::BootstrapPolicyPending)
        }
    }
    #[derive(Clone, Copy)]
    struct BridgePricesV1 {
        metadata: u64, offset: u64, allocation: u64, read: u64, hash_per_byte: u64,
        path_per_byte: u64, correlation: u64, correlation_storage: u64, retirement: u64,
    }
    struct ReviewedAcquisitionQuoteV1 { acquisition_work: u64, cleanup_work: u64, peak_storage: u64 }
    #[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
    struct BootstrapUsageV1 { work: u64, storage: u64, peak: u64 }
    pub(in crate::experimental_swift_reactor) struct BootstrapLedgerV1 {
        policy: FixtureBootstrapPolicyV1, work_limit: u64, storage_limit: u64,
        usage: Cell<BootstrapUsageV1>, reserved: Cell<bool>,
    }
    impl BootstrapLedgerV1 {
        pub(in crate::experimental_swift_reactor) fn from_preexisting_fixture_startup_v1() -> Result<Self, BootstrapFailureV1> {
            // This call has no argument-derived policy, File call or allocation.
            let _policy = FixtureBootstrapPolicyV1::selected_fixture_v1()?;
            Err(BootstrapFailureV1::NativeStartupBridgePending)
        }
        fn reserve_before_any_input_effect_v1(&self, quote: ReviewedAcquisitionQuoteV1)
            -> Result<AcquisitionReservationV1<'_>, BootstrapFailureV1>
        {
            if self.reserved.get() { return Err(BootstrapFailureV1::AlreadyReserved); }
            if quote.acquisition_work == 0 || quote.cleanup_work == 0 || quote.peak_storage == 0 {
                return Err(BootstrapFailureV1::Incomplete);
            }
            let old = self.usage.get();
            let total = quote.acquisition_work.checked_add(quote.cleanup_work).ok_or(BootstrapFailureV1::Overflow)?;
            let work = old.work.checked_add(total).ok_or(BootstrapFailureV1::Overflow)?;
            let storage = old.storage.checked_add(quote.peak_storage).ok_or(BootstrapFailureV1::Overflow)?;
            if work > self.work_limit { return Err(BootstrapFailureV1::InsufficientAcquisitionWork); }
            if storage > self.storage_limit { return Err(BootstrapFailureV1::InsufficientStorage); }
            self.usage.set(BootstrapUsageV1 { work, storage, peak: old.peak.max(storage) });
            self.reserved.set(true);
            Ok(AcquisitionReservationV1 { root: self, operation_left: quote.acquisition_work,
                cleanup_left: quote.cleanup_work, storage_left: quote.peak_storage,
                original_storage: quote.peak_storage })
        }
    }
    // Affine, no Clone/Copy, no renewal and no work-refund path.
    struct AcquisitionReservationV1<'root> {
        root: &'root BootstrapLedgerV1, operation_left: u64, cleanup_left: u64,
        storage_left: u64, original_storage: u64,
    }
    struct PaidOperationV1<'root> { _root: &'root BootstrapLedgerV1 }
    impl<'root> AcquisitionReservationV1<'root> {
        fn operation_v1(&mut self, work: u64, storage: u64) -> Result<PaidOperationV1<'root>, BootstrapFailureV1> {
            if work == 0 { return Err(BootstrapFailureV1::Incomplete); }
            if work > self.operation_left { return Err(BootstrapFailureV1::InsufficientAcquisitionWork); }
            if storage > self.storage_left { return Err(BootstrapFailureV1::InsufficientStorage); }
            self.operation_left -= work;
            self.storage_left -= storage;
            Ok(PaidOperationV1 { _root: self.root })
        }
        fn cleanup_v1(&mut self) -> Result<PaidOperationV1<'root>, BootstrapFailureV1> {
            let work = self.root.policy.bridge.retirement;
            if work == 0 || work > self.cleanup_left { return Err(BootstrapFailureV1::InsufficientCleanupWork); }
            self.cleanup_left -= work;
            Ok(PaidOperationV1 { _root: self.root })
        }
    }
    struct ImmutableOwnedBytesV1 { bytes: Box<[u8]>, initialized: usize, allocation_bound: u64 }
    impl ImmutableOwnedBytesV1 {
        fn complete_v1(&self) -> bool { self.initialized == self.bytes.len() && !self.bytes.is_empty() }
        fn slice_v1(&self) -> &[u8] { &self.bytes[..self.initialized] }
    }
    struct NativePathBackingV1 {
        native: [Option<ImmutableOwnedBytesV1>; 5],
        retained: [Option<ImmutableOwnedBytesV1>; 5],
    }
    impl NativePathBackingV1 {
        fn empty_v1() -> Self { Self { native: std::array::from_fn(|_| None), retained: std::array::from_fn(|_| None) } }
    }
    struct RawSlotObligationV1 { slot: usize, checked: bool }
    // Raw never contains an integer that is converted to a File. Preowned means
    // an already-valid Rust owner, NOT authority to adopt an inherited raw slot.
    enum ActualInputSlotV1<R> {
        Raw(RawSlotObligationV1),
        Preowned { resource: R, initial: FileIdentityV1 },
        Owned(RetainedIdentityFileV1<R>), Retired,
    }
    struct RetainedIdentityFileV1<R> {
        role: usize, resource: R, initial: FileIdentityV1,
        body: Option<ImmutableOwnedBytesV1>, sha256: Option<[u8; 32]>,
    }
    struct PartialActualOwnersV1<R> {
        slots: [ActualInputSlotV1<R>; 13], adoption_bits: u16,
        paths: NativePathBackingV1, original: Option<OriginalAcquisitionFailureV1>,
        unresolved: bool,
    }
    impl<R> PartialActualOwnersV1<R> {
        fn all_owned_v1(&self) -> bool {
            self.adoption_bits == 0x1fff && !self.unresolved && self.slots.iter().all(|s| matches!(s, ActualInputSlotV1::Owned(_)))
        }
    }
    struct AcquiredUnverifiedOwnerV1<R> {
        partial: PartialActualOwnersV1<R>, claims: UnverifiedProfileDigestBytesV1,
    }
    #[must_use]
    struct PrepaidInputOwnerV1<'root, R> {
        reservation: AcquisitionReservationV1<'root>, actual: Option<AcquiredUnverifiedOwnerV1<R>>, retirement_started: bool,
        // Correlation can return owned proof/files/errors with no owner borrow.
        // Issuing its scope therefore permanently retains this acquisition's
        // charge. No result Drop, extraction, forget or ended borrow clears it.
        // A future reviewed joint-retirement protocol may replace this barrier.
        correlation_retirement_blocked: Cell<bool>,
    }
    // The trait is private, closed to external implementations. It selects no
    // authority. Every operation receives a consumed ticket before its effect.
    trait InputBridgeV1<R> {
        fn metadata_v1(&mut self, paid: PaidOperationV1<'_>, resource: &mut R, slot: usize)
            -> Result<FileIdentityV1, OriginalAcquisitionFailureV1>;
        fn offset_v1(&mut self, paid: PaidOperationV1<'_>, resource: &mut R, slot: usize)
            -> Result<u64, OriginalAcquisitionFailureV1>;
        fn allocate_v1(&mut self, paid: PaidOperationV1<'_>, count: usize, bound: u64, slot: usize)
            -> Result<ImmutableOwnedBytesV1, OriginalAcquisitionFailureV1>;
        fn read_v1(&mut self, paid: PaidOperationV1<'_>, resource: &mut R, output: &mut [u8]) -> io::Result<usize>;
        fn hash_v1(&mut self, paid: PaidOperationV1<'_>, bytes: &[u8], slot: usize)
            -> Result<[u8; 32], OriginalAcquisitionFailureV1>;
        fn retire_v1(&mut self, paid: PaidOperationV1<'_>, resource: R, slot: usize)
            -> Result<(), (R, OriginalAcquisitionFailureV1)>;
    }
    struct NativeInputBridgeV1;
    impl InputBridgeV1<File> for NativeInputBridgeV1 {
        fn metadata_v1(&mut self, _paid: PaidOperationV1<'_>, resource: &mut File, slot: usize)
            -> Result<FileIdentityV1, OriginalAcquisitionFailureV1> {
            #[cfg(target_os = "macos")]
            { identity(resource, Role::Source).map_err(|original| OriginalAcquisitionFailureV1 {
                loader: Some(original), ..OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Io, slot) }) }
            #[cfg(not(target_os = "macos"))]
            { let _ = resource; Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::NativeStartupBridgePending, slot)) }
        }
        fn offset_v1(&mut self, _paid: PaidOperationV1<'_>, resource: &mut File, slot: usize)
            -> Result<u64, OriginalAcquisitionFailureV1> {
            resource.stream_position().map_err(|e| OriginalAcquisitionFailureV1::io(slot, 0, 0, e))
        }
        fn allocate_v1(&mut self, _paid: PaidOperationV1<'_>, _count: usize, _bound: u64, slot: usize)
            -> Result<ImmutableOwnedBytesV1, OriginalAcquisitionFailureV1> {
            // std allocator capacity is NOT a pre-call slack/failure bound.
            Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::NativeAllocatorBridgePending, slot))
        }
        fn read_v1(&mut self, _paid: PaidOperationV1<'_>, resource: &mut File, output: &mut [u8]) -> io::Result<usize> {
            resource.read(output)
        }
        fn hash_v1(&mut self, _paid: PaidOperationV1<'_>, bytes: &[u8], slot: usize)
            -> Result<[u8; 32], OriginalAcquisitionFailureV1> {
            #[cfg(target_os = "macos")]
            { platform::hash(bytes, &mut LoaderUsageV1::default()).map_err(|original| OriginalAcquisitionFailureV1 {
                loader: Some(original), ..OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Io, slot) }) }
            #[cfg(not(target_os = "macos"))]
            { let _ = bytes; Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::NativeStartupBridgePending, slot)) }
        }
        fn retire_v1(&mut self, _paid: PaidOperationV1<'_>, resource: File, slot: usize)
            -> Result<(), (File, OriginalAcquisitionFailureV1)> {
            // File::drop cannot certify healthy native close. Keep owner.
            Err((resource, OriginalAcquisitionFailureV1::new(BootstrapFailureV1::RetirementIncomplete, slot)))
        }
    }
    fn store_failure_v1<R>(partial: &mut PartialActualOwnersV1<R>, original: OriginalAcquisitionFailureV1) {
        // First original wins; no later diagnosis replaces its backing.
        if partial.original.is_none() { partial.original = Some(original); }
    }
    fn adopt_preowned_slots_core_v1<R, B: InputBridgeV1<R>>(
        paid: &mut AcquisitionReservationV1<'_>, partial: &mut PartialActualOwnersV1<R>, bridge: &mut B,
    ) {
        for i in 0..13 {
            if partial.original.is_some() { return; }
            let ticket = match paid.operation_v1(paid.root.policy.bridge.metadata, 0) {
                Ok(t) => t, Err(e) => { store_failure_v1(partial, OriginalAcquisitionFailureV1::new(e, i)); return; }
            };
            let observed = match &mut partial.slots[i] {
                ActualInputSlotV1::Preowned { resource, .. } => bridge.metadata_v1(ticket, resource, i),
                _ => { partial.unresolved = true; store_failure_v1(partial,
                    OriginalAcquisitionFailureV1::new(BootstrapFailureV1::NativeStartupBridgePending, i)); return; }
            };
            let observed = match observed { Ok(v) => v, Err(e) => { store_failure_v1(partial, e); return; } };
            if observed.mode & 0o170000 != 0o100000 || observed.bytes == 0 {
                store_failure_v1(partial, OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Extent, i)); return;
            }
            for j in 0..i {
                if let ActualInputSlotV1::Owned(old) = &partial.slots[j] {
                    if (old.initial.dev, old.initial.inode) == (observed.dev, observed.inode) {
                        store_failure_v1(partial, OriginalAcquisitionFailureV1::new(BootstrapFailureV1::AliasedIdentity, i)); return;
                    }
                }
            }
            // No fallible gap after moving the represented resource. Raw slots
            // never take this branch, and no raw-FD conversion exists here.
            let old = std::mem::replace(&mut partial.slots[i], ActualInputSlotV1::Retired);
            match old {
                ActualInputSlotV1::Preowned { resource, initial } => {
                    partial.slots[i] = ActualInputSlotV1::Owned(RetainedIdentityFileV1 {
                        role: i, resource, initial, body: None, sha256: None });
                    partial.adoption_bits |= 1 << i;
                    if initial != observed { store_failure_v1(partial,
                        OriginalAcquisitionFailureV1::new(BootstrapFailureV1::MetadataChanged, i)); return; }
                }
                other => { partial.slots[i] = other; partial.unresolved = true; return; }
            }
        }
    }
    fn allocation_bound_v1(count: usize, policy: &FixtureBootstrapPolicyV1) -> Result<u64, BootstrapFailureV1> {
        let n = count.checked_add(policy.allocation_slack)
            .and_then(|n| n.checked_add(policy.original_failure_backing)).ok_or(BootstrapFailureV1::Overflow)?;
        u64::try_from(n).map_err(|_| BootstrapFailureV1::Overflow)
    }
    fn read_owned_body_once_v1<R, B: InputBridgeV1<R>>(
        paid: &mut AcquisitionReservationV1<'_>, owned: &mut RetainedIdentityFileV1<R>, cap: usize, bridge: &mut B,
    ) -> Result<(), OriginalAcquisitionFailureV1> {
        let slot = owned.role;
        if owned.body.is_some() { return Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::AlreadyAttempted, slot)); }
        let price = paid.root.policy.bridge;
        let effect = |kind| OriginalAcquisitionFailureV1::new(kind, slot);
        let t = paid.operation_v1(price.metadata, 0).map_err(effect)?;
        let initial = bridge.metadata_v1(t, &mut owned.resource, slot)?;
        if initial != owned.initial || initial.mode & 0o170000 != 0o100000 {
            return Err(effect(BootstrapFailureV1::MetadataChanged));
        }
        let t = paid.operation_v1(price.offset, 0).map_err(effect)?;
        if bridge.offset_v1(t, &mut owned.resource, slot)? != 0 { return Err(effect(BootstrapFailureV1::Offset)); }
        let count = usize::try_from(initial.bytes).map_err(|_| effect(BootstrapFailureV1::Extent))?;
        if count == 0 || count > cap { return Err(effect(BootstrapFailureV1::Extent)); }
        let bound = allocation_bound_v1(count, &paid.root.policy).map_err(effect)?;
        let t = paid.operation_v1(price.allocation, bound).map_err(effect)?;
        let backing = bridge.allocate_v1(t, count, bound, slot)?;
        // Move initialized/partial allocation into its original File owner BEFORE
        // reads or any subsequent fallible check; errors borrow, never consume it.
        owned.body = Some(backing);
        let body = owned.body.as_mut().expect("just stored private backing");
        if body.bytes.len() != count || body.initialized != 0 || body.allocation_bound > bound {
            return Err(effect(BootstrapFailureV1::Allocation));
        }
        for base in (0..count).step_by(BLOCK) {
            let end = count.min(base + BLOCK);
            let mut used = 0;
            let mut complete = false;
            for attempt in 1..=ATTEMPTS {
                let t = paid.operation_v1(price.read, 0).map_err(effect)?;
                match bridge.read_v1(t, &mut owned.resource, &mut body.bytes[base + used..end]) {
                    Ok(n) if n > end - base - used => return Err(OriginalAcquisitionFailureV1 {
                        offset: base + used, attempts: attempt, ..effect(BootstrapFailureV1::OverreportedRead) }),
                    Ok(0) => return Err(OriginalAcquisitionFailureV1 {
                        offset: base + used, attempts: attempt, ..effect(BootstrapFailureV1::ShortInput) }),
                    Ok(n) => { used += n; body.initialized = base + used;
                        if base + used == end { complete = true; break; } }
                    Err(e) if e.kind() == io::ErrorKind::Interrupted => {}
                    Err(e) => return Err(OriginalAcquisitionFailureV1::io(slot, base + used, attempt, e)),
                }
            }
            if !complete { return Err(OriginalAcquisitionFailureV1 {
                offset: base + used, attempts: ATTEMPTS, ..effect(BootstrapFailureV1::Attempts) }); }
        }
        let mut eof = [0u8; 1];
        let mut complete = false;
        for attempt in 1..=ATTEMPTS {
            let t = paid.operation_v1(price.read, 0).map_err(effect)?;
            match bridge.read_v1(t, &mut owned.resource, &mut eof) {
                Ok(0) => { complete = true; break; }
                Ok(1) => return Err(effect(BootstrapFailureV1::ExtraInput)),
                Ok(_) => return Err(effect(BootstrapFailureV1::OverreportedRead)),
                Err(e) if e.kind() == io::ErrorKind::Interrupted => {}
                Err(e) => return Err(OriginalAcquisitionFailureV1::io(slot, count, attempt, e)),
            }
        }
        if !complete { return Err(effect(BootstrapFailureV1::Attempts)); }
        let t = paid.operation_v1(price.metadata, 0).map_err(effect)?;
        if bridge.metadata_v1(t, &mut owned.resource, slot)? != initial { return Err(effect(BootstrapFailureV1::MetadataChanged)); }
        let hash_work = price.hash_per_byte.checked_mul(count as u64).ok_or_else(|| effect(BootstrapFailureV1::Overflow))?;
        let t = paid.operation_v1(hash_work, 0).map_err(effect)?;
        owned.sha256 = Some(bridge.hash_v1(t, body.slice_v1(), slot)?);
        Ok(())
    }
    fn decode_path_packet_v1<'a>(packet: &'a [u8], policy: &FixtureBootstrapPolicyV1)
        -> Result<[&'a [u8]; 5], BootstrapFailureV1>
    {
        if packet.len() < 64 || packet.len() > policy.packet_cap || &packet[..8] != b"MIXPTH01"
            || word(packet, 8) != 1 || word(packet, 16) != packet.len() as u64 { return Err(BootstrapFailureV1::Packet); }
        let mut out = [&[][..]; 5]; let mut at = 64usize;
        for i in 0..5 {
            let n = usize::try_from(word(packet, 24 + i * 8)).map_err(|_| BootstrapFailureV1::Extent)?;
            let end = at.checked_add(n).ok_or(BootstrapFailureV1::Overflow)?;
            if n == 0 || n > policy.path_caps[i] || end > packet.len() { return Err(BootstrapFailureV1::Extent); }
            let bytes = &packet[at..end];
            if bytes.contains(&0) { return Err(BootstrapFailureV1::Nul); }
            out[i] = bytes; at = end;
        }
        if at != packet.len() { return Err(BootstrapFailureV1::Packet); }
        Ok(out)
    }
    fn copy_native_paths_once_v1<R, B: InputBridgeV1<R>>(
        paid: &mut AcquisitionReservationV1<'_>, paths: [&[u8]; 5], output: &mut NativePathBackingV1, bridge: &mut B,
    ) -> Result<(), OriginalAcquisitionFailureV1> {
        for i in 0..5 {
            for native in [true, false] {
                let place = if native { &mut output.native[i] } else { &mut output.retained[i] };
                let fail = |kind| OriginalAcquisitionFailureV1::new(kind, 13 + i);
                if place.is_some() { return Err(fail(BootstrapFailureV1::AlreadyAttempted)); }
                let n = paths[i].len();
                if n == 0 || n > paid.root.policy.path_caps[i] || paths[i].contains(&0) { return Err(fail(BootstrapFailureV1::Extent)); }
                let bound = allocation_bound_v1(n, &paid.root.policy).map_err(fail)?;
                let t = paid.operation_v1(paid.root.policy.bridge.allocation, bound).map_err(fail)?;
                *place = Some(bridge.allocate_v1(t, n, bound, 13 + i)?);
                let owned = place.as_mut().expect("stored before fallible copy prepay");
                if owned.bytes.len() != n || owned.initialized != 0 || owned.allocation_bound > bound { return Err(fail(BootstrapFailureV1::Allocation)); }
                let work = paid.root.policy.bridge.path_per_byte.checked_mul(n as u64).ok_or_else(|| fail(BootstrapFailureV1::Overflow))?;
                let _paid = paid.operation_v1(work, 0).map_err(fail)?;
                owned.bytes.copy_from_slice(paths[i]); owned.initialized = n;
            }
        }
        Ok(())
    }
    // Production acquisition cannot manufacture File ownership. All thirteen raw
    // obligations enter the carrier before the missing bridge refusal is stored.
    fn acquire_inherited_inputs_once_v1<'root>(paid: AcquisitionReservationV1<'root>, claims: UnverifiedProfileDigestBytesV1)
        -> PrepaidInputOwnerV1<'root, File>
    {
        let mut partial = PartialActualOwnersV1 { slots: std::array::from_fn(|slot|
            ActualInputSlotV1::Raw(RawSlotObligationV1 { slot, checked: false })),
            adoption_bits: 0, paths: NativePathBackingV1::empty_v1(), original: None, unresolved: true };
        store_failure_v1(&mut partial, OriginalAcquisitionFailureV1::new(BootstrapFailureV1::NativeStartupBridgePending, 0));
        PrepaidInputOwnerV1 { reservation: paid, actual: Some(AcquiredUnverifiedOwnerV1 { partial, claims }), retirement_started: false,
            correlation_retirement_blocked: Cell::new(false) }
    }
    // Compiled File specialization of all executable ownership/read/path cores.
    // No caller can reach this without a privately selected root and valid owners.
    fn read_preowned_file_set_once_v1(owner: &mut PrepaidInputOwnerV1<'_, File>) {
        let mut bridge = NativeInputBridgeV1;
        let actual = match owner.actual.as_mut() { Some(v) => v, None => return };
        adopt_preowned_slots_core_v1(&mut owner.reservation, &mut actual.partial, &mut bridge);
        for i in 0..13 {
            if actual.partial.original.is_some() { return; }
            let cap = if i < 12 { owner.reservation.root.policy.role_caps[i] } else { owner.reservation.root.policy.packet_cap };
            let result = match &mut actual.partial.slots[i] {
                ActualInputSlotV1::Owned(file) => read_owned_body_once_v1(&mut owner.reservation, file, cap, &mut bridge),
                _ => Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Incomplete, i)),
            };
            if let Err(original) = result { store_failure_v1(&mut actual.partial, original); return; }
        }
        let packet = match &actual.partial.slots[12] {
            ActualInputSlotV1::Owned(file) => file.body.as_ref().expect("read success stored body").slice_v1(), _ => return,
        };
        let paths = match decode_path_packet_v1(packet, &owner.reservation.root.policy) {
            Ok(v) => v, Err(kind) => { store_failure_v1(&mut actual.partial, OriginalAcquisitionFailureV1::new(kind, 12)); return; }
        };
        if let Err(original) = copy_native_paths_once_v1(&mut owner.reservation, paths, &mut actual.partial.paths, &mut bridge) {
            store_failure_v1(&mut actual.partial, original);
        }
    }
    fn owned_file_v1<R>(actual: &AcquiredUnverifiedOwnerV1<R>, i: usize) -> Result<&RetainedIdentityFileV1<R>, BootstrapFailureV1> {
        match &actual.partial.slots[i] { ActualInputSlotV1::Owned(v) => Ok(v), _ => Err(BootstrapFailureV1::Incomplete) }
    }
    fn body_v1<R>(actual: &AcquiredUnverifiedOwnerV1<R>, i: usize) -> Result<&[u8], BootstrapFailureV1> {
        let f = owned_file_v1(actual, i)?;
        match &f.body { Some(v) if v.complete_v1() && f.role == i && f.initial.bytes == v.bytes.len() as u64 => Ok(v.slice_v1()),
            _ => Err(BootstrapFailureV1::BodyRole) }
    }
    fn decode_identity_v1(bytes: &[u8]) -> Result<FileIdentityV1, BootstrapFailureV1> {
        if bytes.len() != 64 { return Err(BootstrapFailureV1::Record); }
        let identity = FileIdentityV1 { dev: word(bytes, 0), inode: word(bytes, 8), bytes: word(bytes, 16),
            mode: word(bytes, 24), mtime: word(bytes, 32) as i64, mtime_ns: word(bytes, 40) as i64,
            ctime: word(bytes, 48) as i64, ctime_ns: word(bytes, 56) as i64 };
        if identity.bytes == 0 || identity.mode & 0o170000 != 0o100000 { return Err(BootstrapFailureV1::Record); }
        Ok(identity)
    }
    // Nine groups are derived from live owned production records, never a map.
    fn derive_provenance_v1<R>(actual: &AcquiredUnverifiedOwnerV1<R>, policy: &FixtureBootstrapPolicyV1)
        -> Result<LoaderProvenanceV1, OriginalAcquisitionFailureV1>
    {
        let fail = |kind| OriginalAcquisitionFailureV1::new(kind, 2);
        if !actual.partial.all_owned_v1() || actual.partial.original.is_some() { return Err(fail(BootstrapFailureV1::Incomplete)); }
        for i in 0..13 { let _ = body_v1(actual, i).map_err(fail)?; }
        let build = body_v1(actual, 1).map_err(fail)?;
        let session = body_v1(actual, 2).map_err(fail)?;
        let b = parse_build(build).map_err(|original| OriginalAcquisitionFailureV1 { loader: Some(original), ..fail(BootstrapFailureV1::Record) })?;
        let s = parse_session(session).map_err(|original| OriginalAcquisitionFailureV1 { loader: Some(original), ..fail(BootstrapFailureV1::Record) })?;
        let mut ids = [FileIdentityV1::default(); 4];
        for (i, output) in ids.iter_mut().enumerate() { *output = owned_file_v1(actual, i).map_err(fail)?.initial; }
        let digest = |i| owned_file_v1(actual, i).and_then(|f| f.sha256.ok_or(BootstrapFailureV1::Digest));
        let source = digest(0).map_err(fail)?; let build_digest = digest(1).map_err(fail)?;
        let session_digest = digest(2).map_err(fail)?; let executable = digest(3).map_err(fail)?;
        let manifest = digest(6).map_err(fail)?;
        if s.source_bytes == 0 || s.budget.source_bytes == 0 || s.budget.metadata_bytes == 0
            || s.budget.scratch_bytes == 0 || s.budget.work_credits == 0 || s.budget.deadline_ms == 0
            || s.source_bytes != ids[0].bytes || decode_identity_v1(s.sections[0].bytes).map_err(fail)? != ids[0]
            || s.budget != policy.validation || !budget_valid(s.budget) || s.source != source || s.build != build_digest
            || s.executable != executable || b.digests[0] != manifest || b.digests[5] != executable
            || b.output_bytes != ids[3].bytes { return Err(fail(BootstrapFailureV1::Record)); }
        // Complete byte-level record/body joins retain binary ordering.
        for (part, slot) in [(0,6), (1,7), (2,8), (3,5)] {
            if b.sections[part].bytes != body_v1(actual, slot).map_err(fail)? || b.digests[part] != digest(slot).map_err(fail)? {
                return Err(fail(BootstrapFailureV1::Digest));
            }
        }
        if b.digests[4] != digest(4).map_err(fail)? || s.sections[1].bytes != body_v1(actual, 9).map_err(fail)?
            || s.sections[2].bytes != body_v1(actual, 10).map_err(fail)? { return Err(fail(BootstrapFailureV1::Digest)); }
        let paths = decode_path_packet_v1(body_v1(actual, 12).map_err(fail)?, policy).map_err(fail)?;
        for i in 0..5 {
            let native = actual.partial.paths.native[i].as_ref().ok_or_else(|| fail(BootstrapFailureV1::Incomplete))?;
            let retained = actual.partial.paths.retained[i].as_ref().ok_or_else(|| fail(BootstrapFailureV1::Incomplete))?;
            if !native.complete_v1() || !retained.complete_v1() || native.slice_v1() != paths[i] || retained.slice_v1() != paths[i] {
                return Err(fail(BootstrapFailureV1::Packet));
            }
        }
        Ok(LoaderProvenanceV1 { validation_budget: s.budget, source_extent: s.source_bytes, source, manifest,
            build: build_digest, session: session_digest, executable, nonce: s.nonce.try_into().expect("binary fixed width"), identities: ids })
    }
    // No production constructor exists for this witness. Concrete source-root
    // compile closure, external review, process/image and launcher custody must
    // first be independently selected; digest equality is never that witness.
    struct TrustedLocalLauncherCustodyV1 { _private: () }
    static NEXT_ADMISSION_ASSOCIATION_V1: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(1);
    struct AdmittedImmutableOwnerCoreV1<'root,R> {
        owned: PrepaidInputOwnerV1<'root,R>, expected: LoaderProvenanceV1,
        custody: TrustedLocalLauncherCustodyV1, attempt_taken: Cell<bool>, association: u64,
    }
    pub(in crate::experimental_swift_reactor) struct AdmittedImmutableOwnerV1<'root>(AdmittedImmutableOwnerCoreV1<'root,File>);
    enum OwnedAdmissionCoreOutcomeV1<'root,R> {
        Admitted(AdmittedImmutableOwnerCoreV1<'root,R>), Refused(PrepaidInputOwnerV1<'root,R>),
    }
    fn verify_actual_bodies_core_v1<R,B:InputBridgeV1<R>>(paid:&mut AcquisitionReservationV1<'_>,actual:&mut AcquiredUnverifiedOwnerV1<R>,bridge:&mut B)
        -> Result<LoaderProvenanceV1,OriginalAcquisitionFailureV1>
    {
        if actual.partial.original.is_some() { return Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Incomplete,0)); }
        for i in 0..13 {
            let fail=|kind|OriginalAcquisitionFailureV1::new(kind,i);
            let owned=match &mut actual.partial.slots[i] { ActualInputSlotV1::Owned(v)=>v,_=>return Err(fail(BootstrapFailureV1::Incomplete)) };
            let t=paid.operation_v1(paid.root.policy.bridge.metadata,0).map_err(fail)?;
            if bridge.metadata_v1(t,&mut owned.resource,i)?!=owned.initial { return Err(fail(BootstrapFailureV1::MetadataChanged)); }
            let body=match owned.body.as_ref() {Some(v) if v.complete_v1()=>v,_=>return Err(fail(BootstrapFailureV1::Incomplete))};
            let work=paid.root.policy.bridge.hash_per_byte.checked_mul(body.bytes.len() as u64).ok_or_else(||fail(BootstrapFailureV1::Overflow))?;
            let t=paid.operation_v1(work,0).map_err(fail)?;
            if Some(bridge.hash_v1(t,body.slice_v1(),i)?)!=owned.sha256 {return Err(fail(BootstrapFailureV1::Digest));}
        }
        let bytes=body_v1(actual,1).map_err(|kind|OriginalAcquisitionFailureV1::new(kind,1))?.len()
            .checked_add(body_v1(actual,2).map_err(|kind|OriginalAcquisitionFailureV1::new(kind,2))?.len())
            .and_then(|n|n.checked_add(64)).ok_or_else(||OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Overflow,1))?;
        let _paid=paid.operation_v1(bytes as u64,0).map_err(|kind|OriginalAcquisitionFailureV1::new(kind,1))?;
        derive_provenance_v1(actual,&paid.root.policy)
    }
    fn complete_admission_core_v1<'root,R,B:InputBridgeV1<R>>(mut owned: PrepaidInputOwnerV1<'root,R>, custody: TrustedLocalLauncherCustodyV1,bridge:&mut B)
        -> OwnedAdmissionCoreOutcomeV1<'root,R>
    {
        let derived = match owned.actual.as_mut() {
            Some(actual) => verify_actual_bodies_core_v1(&mut owned.reservation,actual,bridge),
            None => Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Incomplete,0)),
        };
        let expected = match derived {
            Ok(expected) => expected,
            Err(original) => {
                if let Some(actual) = owned.actual.as_mut() { store_failure_v1(&mut actual.partial,original); }
                return OwnedAdmissionCoreOutcomeV1::Refused(owned);
            }
        };
        let prices = owned.reservation.root.policy.bridge;
        // Entire fixed ingress/call/result/refusal overlap debited from the
        // original acquisition partition BEFORE admission publication.
        if let Err(kind) = owned.reservation.operation_v1(prices.correlation, prices.correlation_storage) {
            if let Some(actual) = owned.actual.as_mut() { store_failure_v1(&mut actual.partial,
                OriginalAcquisitionFailureV1::new(kind,13)); }
            return OwnedAdmissionCoreOutcomeV1::Refused(owned);
        }
        // Private non-renewable association bookkeeping only. This number is
        // never an authority source or a new reservation; exhaustion refuses.
        let association = match NEXT_ADMISSION_ASSOCIATION_V1.fetch_update(std::sync::atomic::Ordering::Relaxed,
            std::sync::atomic::Ordering::Relaxed,|old|old.checked_add(1)) {
                Ok(v)=>v,Err(_)=>{if let Some(actual)=owned.actual.as_mut() {store_failure_v1(&mut actual.partial,
                    OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Overflow,13));}
                    return OwnedAdmissionCoreOutcomeV1::Refused(owned);}
            };
        OwnedAdmissionCoreOutcomeV1::Admitted(AdmittedImmutableOwnerCoreV1 {
            owned, expected, custody, attempt_taken: Cell::new(false),association })
    }
    fn verify_owned_once_v1<'root>(mut owner: PrepaidInputOwnerV1<'root,File>) -> OwnedAdmissionCoreOutcomeV1<'root,File> {
        let result = match owner.actual.as_mut() {
            Some(actual) => verify_actual_bodies_core_v1(&mut owner.reservation,actual,&mut NativeInputBridgeV1),
            None => Err(OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Incomplete,0)),
        };
        let original = match result { Err(e) => e, Ok(_) => OriginalAcquisitionFailureV1::new(BootstrapFailureV1::CompileClosureAuthorityPending,11) };
        if let Some(actual) = owner.actual.as_mut() { store_failure_v1(&mut actual.partial,original); }
        // No production TrustedLocalLauncherCustodyV1 producer exists.
        OwnedAdmissionCoreOutcomeV1::Refused(owner)
    }
    pub(in crate::experimental_swift_reactor) fn selected_bootstrap_ledger_v1()
        -> Result<BootstrapLedgerV1, BootstrapFailureV1>
    {
        BootstrapLedgerV1::from_preexisting_fixture_startup_v1()
    }
    pub(in crate::experimental_swift_reactor) struct BorrowedOwnerDataV1<'owner> {
        pub(in crate::experimental_swift_reactor) identities: [(&'owner [u8], [u8;32]);12],
        pub(in crate::experimental_swift_reactor) paths: [&'owner Path;5],
        pub(in crate::experimental_swift_reactor) retained_paths: [&'owner [u8];5],
        pub(in crate::experimental_swift_reactor) claims: &'owner UnverifiedProfileDigestBytesV1,
        pub(in crate::experimental_swift_reactor) validation: SwiftValidationBudget,
        pub(in crate::experimental_swift_reactor) product: SwiftRunBudget,
    }
    pub(in crate::experimental_swift_reactor) struct AdmittedLoaderCorrespondenceV1<'owner> {
        owner_data: &'owner LoaderProvenanceV1, association:u64,
    }
    pub(in crate::experimental_swift_reactor) struct PrepaidCorrelationAttemptV1<'owner> {
        expected: &'owner LoaderProvenanceV1, live: &'owner Cell<bool>, association:u64,
    }
    impl<R> AdmittedImmutableOwnerCoreV1<'_,R> {
        fn correlation_scope_core_v1(&self)
            -> Result<(AdmittedLoaderCorrespondenceV1<'_>, PrepaidCorrelationAttemptV1<'_>), BootstrapFailureV1>
        {
            // Before publishing either borrowed input, retain the entire
            // acquisition charge for every eventual matched/refused carrier.
            // Association checks and result lifetime cannot discharge it.
            self.owned.correlation_retirement_blocked.set(true);
            if self.attempt_taken.replace(true) { return Err(BootstrapFailureV1::AlreadyAttempted); }
            Ok((AdmittedLoaderCorrespondenceV1 { owner_data: &self.expected,association:self.association },
                PrepaidCorrelationAttemptV1 { expected: &self.expected, live: &self.attempt_taken,association:self.association }))
        }
    }
    impl AdmittedImmutableOwnerV1<'_> {
        pub(in crate::experimental_swift_reactor) fn scoped_binding_v1(&self) -> BorrowedOwnerDataV1<'_> {
            use std::os::unix::ffi::OsStrExt;
            let actual = self.0.owned.actual.as_ref().expect("private admitted invariant");
            BorrowedOwnerDataV1 { identities: std::array::from_fn(|i| (body_v1(actual, i).expect("admitted body"),
                    owned_file_v1(actual, i).expect("admitted file").sha256.expect("admitted hash"))),
                paths: std::array::from_fn(|i| Path::new(std::ffi::OsStr::from_bytes(
                    actual.partial.paths.native[i].as_ref().expect("admitted path").slice_v1()))),
                retained_paths: std::array::from_fn(|i| actual.partial.paths.retained[i].as_ref().expect("admitted retained path").slice_v1()),
                claims: &actual.claims, validation: self.0.owned.reservation.root.policy.validation,
                product: self.0.owned.reservation.root.policy.product }
        }
        pub(in crate::experimental_swift_reactor) fn correlation_scope_v1(&self)
            -> Result<(AdmittedLoaderCorrespondenceV1<'_>, PrepaidCorrelationAttemptV1<'_>), BootstrapFailureV1>
        {
            self.0.correlation_scope_core_v1()
        }
    }
    // Fixed typed actual carrier; the generic form substitutes ONLY File guards
    // in host tests. It never substitutes the real validator proof/provenance.
    struct LoaderCarrierCoreV1<R> {
        selected: Result<SelectedValidatedProfileV1, LoaderFailureV1>,
        files: [R;3], executable: Option<R>, usage: LoaderUsageV1,
    }
    pub(in crate::experimental_swift_reactor) struct SuppliedLoaderCarrierV1 { original: LoaderOutcomeV1 }
    impl SuppliedLoaderCarrierV1 {
        pub(in crate::experimental_swift_reactor) fn retain_complete_v1(original: LoaderOutcomeV1) -> Self { Self { original } }
    }
    pub(in crate::experimental_swift_reactor) struct CorrelatedSelectedProfileV1(SelectedValidatedProfileV1);
    impl CorrelatedSelectedProfileV1 {
        pub(in crate::experimental_swift_reactor) fn into_selected_v1(self) -> SelectedValidatedProfileV1 { self.0 }
    }
    pub(in crate::experimental_swift_reactor) struct OriginalCorrelationRefusalV1 { kind: BootstrapFailureV1, retained_selection: Option<Result<SelectedValidatedProfileV1,LoaderFailureV1>> }
    pub(in crate::experimental_swift_reactor) enum OwnedCorrelationOutcomeV1 {
        Correlated { selected: CorrelatedSelectedProfileV1, files: ReturnedLoaderFilesV1, usage: LoaderUsageV1 },
        LoaderRefused { original: LoaderFailureV1, files: ReturnedLoaderFilesV1, usage: LoaderUsageV1 },
        Refused { original: OriginalCorrelationRefusalV1, files: ReturnedLoaderFilesV1, usage: LoaderUsageV1 },
    }
    fn same_provenance_group_v1(a: &LoaderProvenanceV1, b: &LoaderProvenanceV1) -> Result<(), BootstrapFailureV1> {
        let groups = [a.source == b.source, a.manifest == b.manifest, a.build == b.build,
            a.session == b.session, a.executable == b.executable, a.nonce == b.nonce,
            a.validation_budget == b.validation_budget, a.source_extent == b.source_extent,
            a.identities == b.identities];
        for (i, same) in groups.into_iter().enumerate() { if !same { return Err(BootstrapFailureV1::Correlation(i)); } }
        if a.source_extent == 0 { return Err(BootstrapFailureV1::Correlation(7)); }
        Ok(())
    }
    fn correlate_core_v1<R>(attempt: PrepaidCorrelationAttemptV1<'_>, carrier: LoaderCarrierCoreV1<R>,
        expected: &AdmittedLoaderCorrespondenceV1<'_>) -> Result<LoaderCarrierCoreV1<R>, (OriginalCorrelationRefusalV1, LoaderCarrierCoreV1<R>)>
    {
        // COMPLETE original proof/result/files/usage already moved into carrier.
        let refusal = if !attempt.live.get() || attempt.association!=expected.association { Err(BootstrapFailureV1::LiveOwner) }
            else { same_provenance_group_v1(attempt.expected, expected.owner_data) };
        if let Err(kind) = refusal { return Err((OriginalCorrelationRefusalV1 { kind, retained_selection: None }, carrier)); }
        if let Ok(selected) = &carrier.selected {
            if let Err(kind) = same_provenance_group_v1(&selected.provenance, attempt.expected) {
                return Err((OriginalCorrelationRefusalV1 { kind, retained_selection: None }, carrier));
            }
        }
        Ok(carrier)
    }
    pub(in crate::experimental_swift_reactor) fn correlate_admitted_loader_v1(
        attempt: PrepaidCorrelationAttemptV1<'_>, carrier: SuppliedLoaderCarrierV1,
        expected: &AdmittedLoaderCorrespondenceV1<'_>,
    ) -> OwnedCorrelationOutcomeV1 {
        // First receive and retain the WHOLE outcome, then move it into the
        // fixed owning generic program. No fallible operation intervenes.
        let LoaderOutcomeV1 { selected, files, usage } = carrier.original;
        let ReturnedLoaderFilesV1 { source, build, session, executable } = files;
        let complete = LoaderCarrierCoreV1 { selected, files: [source,build,session], executable, usage };
        match correlate_core_v1(attempt, complete, expected) {
            Ok(LoaderCarrierCoreV1 { selected, files: [source,build,session], executable, usage }) => {
                let files = ReturnedLoaderFilesV1 { source,build,session,executable };
                match selected {
                    Ok(selected) => OwnedCorrelationOutcomeV1::Correlated { selected: CorrelatedSelectedProfileV1(selected), files, usage },
                    Err(original) => OwnedCorrelationOutcomeV1::LoaderRefused { original, files, usage },
                }
            }
            Err((mut original, LoaderCarrierCoreV1 { selected, files: [source,build,session], executable, usage })) => {
                original.retained_selection = Some(selected);
                OwnedCorrelationOutcomeV1::Refused { original, files: ReturnedLoaderFilesV1 { source,build,session,executable }, usage }
            }
        }
    }
    #[must_use]
    struct CompleteAcquisitionRetirementV1<'root> { paid: AcquisitionReservationV1<'root> }
    enum AcquisitionRetirementOutcomeV1<'root, R> {
        Complete(CompleteAcquisitionRetirementV1<'root>), Retained(PrepaidInputOwnerV1<'root, R>),
    }
    fn retire_acquired_owner_core_v1<'root, R, B: InputBridgeV1<R>>(
        mut owner: PrepaidInputOwnerV1<'root,R>, bridge: &mut B,
    ) -> AcquisitionRetirementOutcomeV1<'root,R> {
        // The same production/test core enforces this before any cleanup
        // effect. A result may outlive all expected/attempt borrows, may be
        // destructured, or may be forgotten; none authorizes a Complete token.
        if owner.correlation_retirement_blocked.get() { return AcquisitionRetirementOutcomeV1::Retained(owner); }
        if owner.retirement_started { return AcquisitionRetirementOutcomeV1::Retained(owner); }
        owner.retirement_started = true;
        let actual = match owner.actual.as_mut() { Some(v) => v, None => return AcquisitionRetirementOutcomeV1::Retained(owner) };
        // Never close raw/unresolved obligations or mint a complete token.
        if actual.partial.unresolved || actual.partial.slots.iter().any(|s| matches!(s,ActualInputSlotV1::Raw(_) | ActualInputSlotV1::Preowned {..})) {
            return AcquisitionRetirementOutcomeV1::Retained(owner);
        }
        for i in 0..13 {
            if matches!(actual.partial.slots[i], ActualInputSlotV1::Retired) { continue; }
            let t = match owner.reservation.cleanup_v1() {
                Ok(t) => t, Err(kind) => { store_failure_v1(&mut actual.partial, OriginalAcquisitionFailureV1::new(kind,i));
                    return AcquisitionRetirementOutcomeV1::Retained(owner); }
            };
            let slot = std::mem::replace(&mut actual.partial.slots[i], ActualInputSlotV1::Retired);
            if let ActualInputSlotV1::Owned(RetainedIdentityFileV1 { role, resource, initial, body, sha256 }) = slot {
                match bridge.retire_v1(t, resource, i) {
                    Ok(()) => drop(body),
                    Err((resource, original)) => {
                        actual.partial.slots[i] = ActualInputSlotV1::Owned(RetainedIdentityFileV1 { role,resource,initial,body,sha256 });
                        store_failure_v1(&mut actual.partial, original); return AcquisitionRetirementOutcomeV1::Retained(owner);
                    }
                }
            }
        }
        // Cleanup separately pays each native+retained backing, claims/errors
        // and final carrier. No acquisition ticket or child refund is borrowed.
        for i in 0..10 {
            if owner.reservation.cleanup_v1().is_err() { return AcquisitionRetirementOutcomeV1::Retained(owner); }
            let place = if i < 5 { &mut actual.partial.paths.native[i] } else { &mut actual.partial.paths.retained[i-5] };
            drop(place.take());
        }
        if owner.reservation.cleanup_v1().is_err() { return AcquisitionRetirementOutcomeV1::Retained(owner); }
        drop(owner.actual.take());
        if owner.reservation.cleanup_v1().is_err() { return AcquisitionRetirementOutcomeV1::Retained(owner); }
        let PrepaidInputOwnerV1 { reservation: paid, actual: None, retirement_started: _, correlation_retirement_blocked: _ } = owner else { unreachable!() };
        AcquisitionRetirementOutcomeV1::Complete(CompleteAcquisitionRetirementV1 { paid })
    }
    impl CompleteAcquisitionRetirementV1<'_> {
        fn release_v1(self) {
            let old = self.paid.root.usage.get();
            if let Some(storage) = old.storage.checked_sub(self.paid.original_storage) {
                self.paid.root.usage.set(BootstrapUsageV1 { storage, ..old });
            }
        }
    }
    pub(in crate::experimental_swift_reactor) fn retire_admitted_owner_v1(owner: AdmittedImmutableOwnerV1<'_>) {
        // Ending borrowed views does not prove retirement of owned results.
        // Any issued correlation scope permanently blocks Complete/refund.
        // Without a scope, the native bridge still cannot certify healthy close.
        match retire_acquired_owner_core_v1(owner.0.owned, &mut NativeInputBridgeV1) {
            AcquisitionRetirementOutcomeV1::Retained(original) => drop(original),
            AcquisitionRetirementOutcomeV1::Complete(token) => token.release_v1(),
        }
    }
    #[cfg(test)]
    mod prepaid_actual_owner_v1 {
        use super::*;
        use std::rc::Rc;
        use std::panic::{catch_unwind,AssertUnwindSafe};
        #[derive(Default)]
        struct Trace { drops: std::cell::RefCell<Vec<usize>>, allocated: Cell<usize>, read_calls: Cell<usize>, storage_at_allocation: Cell<u64> }
        struct Guard {
            tag:usize, identity:FileIdentityV1, data:Vec<u8>, position:usize,
            interruptions:u32, eof_interruptions:u32, chunk:usize, overreported:bool, error:Option<i32>, fail_after:Option<usize>,
            meta_fail:bool, trace:Rc<Trace>,
        }
        impl Drop for Guard { fn drop(&mut self) { self.trace.drops.borrow_mut().push(self.tag); } }
        struct TestBridge { trace:Rc<Trace>, fail_allocation:bool, fail_retirement:Option<usize>, unwind_retirement:Option<usize> }
        impl InputBridgeV1<Guard> for TestBridge {
            fn metadata_v1(&mut self,_paid:PaidOperationV1<'_>,r:&mut Guard,slot:usize)->Result<FileIdentityV1,OriginalAcquisitionFailureV1> {
                if r.meta_fail { return Err(OriginalAcquisitionFailureV1::io(slot,0,0,io::Error::from_raw_os_error(817))); }
                Ok(r.identity)
            }
            fn offset_v1(&mut self,_paid:PaidOperationV1<'_>,r:&mut Guard,_slot:usize)->Result<u64,OriginalAcquisitionFailureV1> { Ok(r.position as u64) }
            fn allocate_v1(&mut self,paid:PaidOperationV1<'_>,n:usize,bound:u64,slot:usize)->Result<ImmutableOwnedBytesV1,OriginalAcquisitionFailureV1> {
                self.trace.allocated.set(self.trace.allocated.get()+1);
                self.trace.storage_at_allocation.set(paid._root.usage.get().storage);
                if self.fail_allocation {
                    let mut empty=Vec::<u8>::new();
                    let original=empty.try_reserve(usize::MAX).unwrap_err();
                    return Err(OriginalAcquisitionFailureV1 { allocation:Some(original),..OriginalAcquisitionFailureV1::new(BootstrapFailureV1::Allocation,slot) });
                }
                // Test-only std allocation exercises the same pre-call ordering;
                // it is not an assertion about a native allocation/slack price.
                Ok(ImmutableOwnedBytesV1 { bytes:vec![0;n].into_boxed_slice(),initialized:0,allocation_bound:bound })
            }
            fn read_v1(&mut self,_paid:PaidOperationV1<'_>,r:&mut Guard,output:&mut[u8])->io::Result<usize> {
                self.trace.read_calls.set(self.trace.read_calls.get()+1);
                if r.interruptions>0 { r.interruptions-=1;return Err(io::Error::from(io::ErrorKind::Interrupted)); }
                if r.position>=r.identity.bytes as usize && r.eof_interruptions>0 {r.eof_interruptions-=1;return Err(io::Error::from(io::ErrorKind::Interrupted));}
                if r.fail_after.is_none_or(|at|r.position>=at) {if let Some(code)=r.error.take() { return Err(io::Error::from_raw_os_error(code)); }}
                if r.overreported { return Ok(output.len()+1); }
                let n=output.len().min(r.chunk).min(r.data.len().saturating_sub(r.position));
                output[..n].copy_from_slice(&r.data[r.position..r.position+n]);r.position+=n;Ok(n)
            }
            fn hash_v1(&mut self,_paid:PaidOperationV1<'_>,bytes:&[u8],_slot:usize)->Result<[u8;32],OriginalAcquisitionFailureV1> {
                // Fixed test digest labels, not cryptographic authentication.
                Ok(test_digest(bytes))
            }
            fn retire_v1(&mut self,_paid:PaidOperationV1<'_>,r:Guard,slot:usize)->Result<(),(Guard,OriginalAcquisitionFailureV1)> {
                if self.unwind_retirement==Some(slot) { panic!("owned retirement test unwind"); }
                if self.fail_retirement==Some(slot) { return Err((r,OriginalAcquisitionFailureV1::io(slot,0,0,io::Error::from_raw_os_error(829)))); }
                drop(r);Ok(())
            }
        }
        fn test_digest(bytes:&[u8])->[u8;32] { [bytes.first().copied().unwrap_or(0);32] }
        fn root()->BootstrapLedgerV1 {
            BootstrapLedgerV1 { policy:FixtureBootstrapPolicyV1 { role_caps:[100_000;12],path_caps:[9000;5],packet_cap:100_000,
                validation:SwiftValidationBudget { source_bytes:1947,metadata_bytes:1_000_000,scratch_bytes:65_536,work_credits:1_000_000,deadline_ms:10_000 },
                product:SwiftRunBudget::default(),allocation_slack:7,original_failure_backing:19,
                bridge:BridgePricesV1 { metadata:1,offset:1,allocation:1,read:1,hash_per_byte:1,path_per_byte:1,
                    correlation:31,correlation_storage:43,retirement:1 } },
                work_limit:10_000_000,storage_limit:10_000_000,usage:Cell::new(BootstrapUsageV1::default()),reserved:Cell::new(false) }
        }
        fn paid(root:&BootstrapLedgerV1)->AcquisitionReservationV1<'_> { root.reserve_before_any_input_effect_v1(
            ReviewedAcquisitionQuoteV1 { acquisition_work:1_000_000,cleanup_work:100,peak_storage:1_000_000 }).unwrap() }
        fn identity_for(tag:usize,n:usize)->FileIdentityV1 { FileIdentityV1 { dev:19,inode:tag as u64+1,bytes:n as u64,mode:0o100600,
            mtime:i64::MIN,mtime_ns:-1,ctime:i64::MAX,ctime_ns:-9 } }
        fn guard(tag:usize,data:Vec<u8>,trace:&Rc<Trace>)->Guard { Guard { tag,identity:identity_for(tag,data.len()),data,
            position:0,interruptions:0,eof_interruptions:0,chunk:usize::MAX,overreported:false,error:None,fail_after:None,meta_fail:false,trace:trace.clone() } }
        fn bridge(trace:&Rc<Trace>)->TestBridge { TestBridge { trace:trace.clone(),fail_allocation:false,fail_retirement:None,unwind_retirement:None } }
        fn claims()->UnverifiedProfileDigestBytesV1 { UnverifiedProfileDigestBytesV1::test_prepaid_actual_owner_fixed_claims_v1() }
        fn word_put(bytes:&mut[u8],at:usize,n:u64) { bytes[at..at+8].copy_from_slice(&n.to_le_bytes()); }
        fn packet(paths:[&[u8];5])->Vec<u8> {
            let mut out=vec![0;64];out[..8].copy_from_slice(b"MIXPTH01");word_put(&mut out,8,1);
            for (i,path) in paths.into_iter().enumerate() { word_put(&mut out,24+i*8,path.len() as u64);out.extend_from_slice(path); }
            let n=out.len();word_put(&mut out,16,n as u64);out
        }
        fn list(value:&[u8])->Vec<u8> { let mut out=1u64.to_le_bytes().to_vec();out.extend_from_slice(&(value.len() as u64).to_le_bytes());out.extend_from_slice(value);out }
        fn encode_record(magic:&[u8;8],sections:[&[u8];4],offset:usize)->Vec<u8> {
            let mut out=vec![0;512];out[..8].copy_from_slice(magic);word_put(&mut out,8,1);word_put(&mut out,16,512);
            for (i,s) in sections.into_iter().enumerate() { word_put(&mut out,offset+i*8,s.len() as u64);out.extend_from_slice(s); }
            let n=out.len();word_put(&mut out,24,n as u64);out
        }
        fn leb(mut n:u32,out:&mut Vec<u8>) { loop { let b=(n&127) as u8;n>>=7;out.push(b|if n>0 {128}else{0});if n==0{return;} } }
        fn text(s:&[u8],out:&mut Vec<u8>) { leb(s.len() as u32,out);out.extend_from_slice(s); }
        fn section(id:u8,bytes:&[u8],out:&mut Vec<u8>) { out.push(id);leb(bytes.len() as u32,out);out.extend_from_slice(bytes); }
        fn wasm_source()->Vec<u8> {
            // Independently assembled product-owned validator component input.
            // It is never emitted to disk or passed to the genuine File loader.
            use crate::{Type,experimental_wasi::WasiFunction};
            fn ty(t:Type)->u8 { match t {Type::I32=>0x7f,Type::I64=>0x7e,Type::F32=>0x7d,Type::F64=>0x7c} }
            let mut out=b"\0asm\x01\0\0\0".to_vec();let mut types=vec![37];
            for import in WasiFunction::ALL { types.push(0x60);leb(import.parameters().len() as u32,&mut types);
                types.extend(import.parameters().iter().copied().map(ty));leb(import.results().len() as u32,&mut types);types.extend(import.results().iter().copied().map(ty)); }
            types.extend_from_slice(&[0x60,0,0,0x60,0,1,0x7f,0x60,0,0]);section(1,&types,&mut out);
            let mut imports=vec![34];for (i,import) in WasiFunction::ALL.into_iter().enumerate() {
                text(b"wasi_snapshot_preview1",&mut imports);text(import.name(),&mut imports);imports.push(0);leb(i as u32,&mut imports); }
            section(2,&imports,&mut out);let mut functions=vec![64];for i in 0..64 {leb(if i==0 {36}else if i==28 {35}else{34},&mut functions);}
            section(3,&functions,&mut out);let mut table=vec![1,0x70,1];leb(46713,&mut table);leb(46713,&mut table);section(4,&table,&mut out);
            let mut memory=vec![1,0];leb(584,&mut memory);section(5,&memory,&mut out);section(6,&[1,0x7f,1,0x41,0,0x0b],&mut out);
            let mut exports=vec![3];for (name,kind,index) in [(b"memory".as_slice(),2,0),(b"_initialize".as_slice(),0,35),(b"mixer_fieldlog_corpus_v1".as_slice(),0,62)] {
                text(name,&mut exports);exports.push(kind);leb(index,&mut exports); }
            section(7,&exports,&mut out);let mut code=vec![64];for i in 0..64 { let body:&[u8]=if i==28 {&[0,0x41,0,0x0b]}else{&[0,0x0b]};leb(body.len() as u32,&mut code);code.extend_from_slice(body); }
            section(10,&code,&mut out);assert_eq!(out.len(),1947);out
        }
        fn data_set(policy:&FixtureBootstrapPolicyV1)->[Vec<u8>;13] {
            let source=wasm_source();let executable=vec![0x45;17];let compiler=vec![0x43;9];
            let version=b"rust-test-only".to_vec();let manifest=b"exact-source-shape-test".to_vec();
            let argv=list(b"rustc");let env=list(b"A=B");let proc_argv=list(b"host");let proc_env=list(b"X=Y");
            let mut build=encode_record(b"MIXLBD01",[&manifest,&argv,&env,&version],48);
            word_put(&mut build,32,146);word_put(&mut build,40,11);word_put(&mut build,80,executable.len() as u64);
            build[88..108].copy_from_slice(b"aarch64-apple-darwin");
            for (i,data) in [&manifest,&argv,&env,&version,&compiler,&executable].into_iter().enumerate() {build[152+i*32..184+i*32].copy_from_slice(&test_digest(data));}
            let source_id=identity_for(0,source.len()).encode();
            let mut session=encode_record(b"MIXLSE01",[&source_id,&proc_argv,&proc_env,b"/test"],40);
            word_put(&mut session,32,source.len() as u64);
            for (at,n) in [(72,policy.validation.source_bytes as u64),(80,policy.validation.metadata_bytes as u64),(88,policy.validation.scratch_bytes as u64),(96,policy.validation.work_credits),(104,policy.validation.deadline_ms)] {word_put(&mut session,at,n);}
            session[112..144].fill(0x61);session[144..176].copy_from_slice(&test_digest(&source));session[176..208].copy_from_slice(&test_digest(&build));session[208..240].copy_from_slice(&test_digest(&executable));
            for (i,data) in [&source_id[..],&proc_argv,&proc_env,b"/test"].into_iter().enumerate() {session[240+i*32..272+i*32].copy_from_slice(&test_digest(data));}
            [source,build,session,executable,compiler,version,manifest,argv,env,proc_argv,proc_env,b"review-test-only".to_vec(),packet([b"/s",b"/b",b"/t",b"/r",b"/o"])]
        }
        fn preowned<'r>(root:&'r BootstrapLedgerV1,data:[Vec<u8>;13],trace:&Rc<Trace>)->PrepaidInputOwnerV1<'r,Guard> {
            let mut iter=data.into_iter().enumerate();let slots=std::array::from_fn(|_| {let(i,bytes)=iter.next().unwrap();let resource=guard(i,bytes,trace);let initial=resource.identity;ActualInputSlotV1::Preowned {resource,initial}});
            PrepaidInputOwnerV1 { reservation:paid(root),actual:Some(AcquiredUnverifiedOwnerV1 { partial:PartialActualOwnersV1 {
                slots,adoption_bits:0,paths:NativePathBackingV1::empty_v1(),original:None,unresolved:false },claims:claims() }),retirement_started:false,
                correlation_retirement_blocked:Cell::new(false) }
        }
        fn acquired<'r>(root:&'r BootstrapLedgerV1,trace:&Rc<Trace>)->PrepaidInputOwnerV1<'r,Guard> {
            let mut owner=preowned(root,data_set(&root.policy),trace);let mut b=bridge(trace);let actual=owner.actual.as_mut().unwrap();
            adopt_preowned_slots_core_v1(&mut owner.reservation,&mut actual.partial,&mut b);
            for i in 0..13 {let cap=if i<12 {root.policy.role_caps[i]}else{root.policy.packet_cap};if let ActualInputSlotV1::Owned(file)=&mut actual.partial.slots[i] {
                read_owned_body_once_v1(&mut owner.reservation,file,cap,&mut b).unwrap_or_else(|e|panic!("read slot{} {:?}",i,e.kind)); }else{panic!("missing slot");}}
            let PartialActualOwnersV1 {slots,paths:output,..}=&mut actual.partial;
            let path_bytes=match &slots[12] {ActualInputSlotV1::Owned(f)=>f.body.as_ref().unwrap().slice_v1(),_=>panic!()};
            let paths=decode_path_packet_v1(path_bytes,&root.policy).unwrap();
            copy_native_paths_once_v1(&mut owner.reservation,paths,output,&mut b).unwrap_or_else(|e|panic!("path {:?}",e.kind));owner
        }
        fn admitted<'r>(root:&'r BootstrapLedgerV1,trace:&Rc<Trace>)->AdmittedImmutableOwnerCoreV1<'r,Guard> {
            match complete_admission_core_v1(acquired(root,trace),TrustedLocalLauncherCustodyV1 {_private:()},&mut bridge(trace)) {
                OwnedAdmissionCoreOutcomeV1::Admitted(v)=>v,OwnedAdmissionCoreOutcomeV1::Refused(v)=>panic!("admission {:?}",v.actual.as_ref().unwrap().partial.original.as_ref().map(|e|e.kind)), }
        }
        fn provenance_copy(p:&LoaderProvenanceV1)->LoaderProvenanceV1 { LoaderProvenanceV1 {
            validation_budget:p.validation_budget,source_extent:p.source_extent,source:p.source,manifest:p.manifest,
            build:p.build,session:p.session,executable:p.executable,nonce:p.nonce,identities:p.identities } }
        fn carrier(p:&LoaderProvenanceV1,trace:&Rc<Trace>)->LoaderCarrierCoreV1<Guard> {
            let source=wasm_source();let proof=validate_swift_reactor(&source,p.validation_budget,&Cancellation::default()).unwrap();
            assert_eq!(proof.source(),source);assert_ne!(proof.source().as_ptr(),source.as_ptr());
            LoaderCarrierCoreV1 { selected:Ok(SelectedValidatedProfileV1 {proof,provenance:provenance_copy(p)}),
                files:std::array::from_fn(|i|{let mut resource=guard(20+i,Vec::new(),trace);resource.identity=p.identities[i];resource}),
                executable:Some({let mut resource=guard(23,Vec::new(),trace);resource.identity=p.identities[3];resource}),
                usage:LoaderUsageV1 {hash_bytes:912,source_equality_bytes:1947,..LoaderUsageV1::default()} }
        }
        fn refusal<T>(r:Result<T,BootstrapFailureV1>)->BootstrapFailureV1 {match r {Err(e)=>e,Ok(_)=>panic!("expected refusal")}}
        #[test] fn h01_startup_policy_is_closed_and_original_policy_claims_retained() {
            assert_eq!(refusal(FixtureBootstrapPolicyV1::selected_fixture_v1()),BootstrapFailureV1::BootstrapPolicyPending);
            assert_eq!(refusal(selected_bootstrap_ledger_v1()),BootstrapFailureV1::BootstrapPolicyPending);
            let r=root();let trace=Rc::new(Trace::default());let owner=acquired(&r,&trace);
            assert_eq!(owner.reservation.root.policy.product,SwiftRunBudget::default());
            assert_eq!(owner.reservation.root.policy.product.execution_work,1_000_000_000);
            assert_eq!(owner.reservation.root.policy.product.combined_bytes,268_435_456);
            owner.actual.as_ref().unwrap().claims.test_prepaid_actual_owner_assert_eight_v1();
            assert!(trace.drops.borrow().is_empty());drop(owner);assert_eq!(trace.drops.borrow().len(),13);
        }
        #[test] fn h02_atomic_reservation_overflow_and_partition_exhaustion() {
            for case in 0..4 {let mut r=root();let before=r.usage.get();let mut q=ReviewedAcquisitionQuoteV1 {acquisition_work:10,cleanup_work:11,peak_storage:12};
                let expected=match case {0=>{q.acquisition_work=u64::MAX;BootstrapFailureV1::Overflow},1=>{r.work_limit=20;BootstrapFailureV1::InsufficientAcquisitionWork},2=>{r.storage_limit=11;BootstrapFailureV1::InsufficientStorage},_=>{r.usage.set(BootstrapUsageV1 {work:0,storage:u64::MAX,peak:u64::MAX});BootstrapFailureV1::Overflow}};
                let before=if case==3 {r.usage.get()}else{before};assert_eq!(refusal(r.reserve_before_any_input_effect_v1(q)),expected);assert_eq!(r.usage.get(),before);assert!(!r.reserved.get());}
            let r=root();let mut p=paid(&r);let old=r.usage.get();p.operation_left=0;assert_eq!(refusal(p.operation_v1(1,0)),BootstrapFailureV1::InsufficientAcquisitionWork);assert_eq!(p.cleanup_left,100);
            p.cleanup_left=0;assert_eq!(refusal(p.cleanup_v1()),BootstrapFailureV1::InsufficientCleanupWork);drop(p);assert_eq!(r.usage.get(),old);
        }
        #[test] fn h03_all_thirteen_partial_refusals_keep_original_resources() {
            for stop in 0..13 {let r=root();let trace=Rc::new(Trace::default());let mut owner=preowned(&r,std::array::from_fn(|_|vec![9]),&trace);
                if let ActualInputSlotV1::Preowned {resource,..}=&mut owner.actual.as_mut().unwrap().partial.slots[stop] {resource.meta_fail=true;}
                let actual=owner.actual.as_mut().unwrap();adopt_preowned_slots_core_v1(&mut owner.reservation,&mut actual.partial,&mut bridge(&trace));
                let e=actual.partial.original.as_ref().unwrap();assert_eq!(e.slot,stop);assert_eq!(e.io.as_ref().unwrap().raw_os_error(),Some(817));assert!(trace.drops.borrow().is_empty());
                assert_eq!(actual.partial.adoption_bits,(1u16<<stop)-1);drop(owner);assert_eq!(trace.drops.borrow().len(),13);assert_eq!(r.usage.get().storage,1_000_000);}
            let r=root();let owner=acquire_inherited_inputs_once_v1(paid(&r),claims());assert!(owner.actual.as_ref().unwrap().partial.unresolved);
            let before=r.usage.get();let result=retire_acquired_owner_core_v1(owner,&mut NativeInputBridgeV1);
            assert!(matches!(result,AcquisitionRetirementOutcomeV1::Retained(_)));assert_eq!(r.usage.get(),before);
        }
        fn read_case(n:usize,adjust:impl FnOnce(&mut Guard))->(Result<(),OriginalAcquisitionFailureV1>,RetainedIdentityFileV1<Guard>,Rc<Trace>) {
            let r=Box::new(root()); // root cannot escape; return contains no reservation borrow
            let trace=Rc::new(Trace::default());let mut resource=guard(0,vec![3;n],&trace);adjust(&mut resource);
            let mut file=RetainedIdentityFileV1 {role:0,initial:identity_for(0,n),resource,body:None,sha256:None};
            let result=read_owned_body_once_v1(&mut paid(&r),&mut file,9000,&mut bridge(&trace));(result,file,trace)
        }
        #[test] fn h04_bounded_read_blocks_attempts_and_original_io() {
            for n in [4095,4096,4097,8192] {let(result,file,trace)=read_case(n,|_|{});assert!(result.is_ok());assert_eq!(file.body.as_ref().unwrap().initialized,n);assert_eq!(trace.read_calls.get(),n.div_ceil(4096)+1);}
            let(result,_,trace)=read_case(1,|r|r.interruptions=31);assert!(result.is_ok());assert_eq!(trace.read_calls.get(),33); //32 data+one EOF
            let(result,file,trace)=read_case(1,|r|r.interruptions=32);assert_eq!(result.err().unwrap().kind,BootstrapFailureV1::Attempts);assert_eq!(trace.read_calls.get(),32);assert_eq!(file.body.as_ref().unwrap().initialized,0);
            let(result,_,_)=read_case(3,|r|r.chunk=1);assert!(result.is_ok());
            let(result,_,trace)=read_case(1,|r|r.eof_interruptions=31);assert!(result.is_ok());assert_eq!(trace.read_calls.get(),33);
            let(result,_,trace)=read_case(1,|r|r.eof_interruptions=32);assert_eq!(result.err().unwrap().kind,BootstrapFailureV1::Attempts);assert_eq!(trace.read_calls.get(),33);
            let(result,file,_)=read_case(3,|r|{r.chunk=1;r.error=Some(919);r.fail_after=Some(1);});
            let e=result.err().unwrap();assert_eq!(e.io.as_ref().unwrap().raw_os_error(),Some(919));assert_eq!(file.body.as_ref().unwrap().initialized,1);
            for kind in 0..4 {let(result,file,_)=read_case(3,|r|match kind {0=>{r.data.pop();},1=>r.data.push(4),2=>r.overreported=true,_=>r.error=Some(911)});let e=result.err().unwrap();
                assert_eq!(e.kind,[BootstrapFailureV1::ShortInput,BootstrapFailureV1::ExtraInput,BootstrapFailureV1::OverreportedRead,BootstrapFailureV1::Io][kind]);
                if kind==3 {assert_eq!(e.io.as_ref().unwrap().raw_os_error(),Some(911));}assert!(file.body.is_some());}
        }
        #[test] fn h05_allocator_bound_precedes_call_and_original_error_stays() {
            let r=root();let trace=Rc::new(Trace::default());let mut p=paid(&r);let mut resource=guard(0,vec![1;9],&trace);
            let mut f=RetainedIdentityFileV1 {role:0,initial:resource.identity,resource,body:None,sha256:None};p.storage_left=34; //9+7+19 needs35
            let e=read_owned_body_once_v1(&mut p,&mut f,9,&mut bridge(&trace)).err().unwrap();assert_eq!(e.kind,BootstrapFailureV1::InsufficientStorage);assert_eq!(trace.allocated.get(),0);
            p.storage_left=35;let mut b=bridge(&trace);b.fail_allocation=true;let e=read_owned_body_once_v1(&mut p,&mut f,9,&mut b).err().unwrap();assert!(e.allocation.is_some());assert_eq!(p.storage_left,0);assert_eq!(trace.storage_at_allocation.get(),1_000_000);
            assert_eq!(allocation_bound_v1(usize::MAX,&r.policy),Err(BootstrapFailureV1::Overflow));
        }
        #[test] fn h06_production_packet_and_separate_raw_path_backing() {
            let r=root();let bytes=packet([b"/a",b"/b",b"/c",b"/d",b"/\xff"]);let paths=decode_path_packet_v1(&bytes,&r.policy).unwrap();assert_eq!(paths[4],b"/\xff");
            let trace=Rc::new(Trace::default());let mut p=paid(&r);let mut out=NativePathBackingV1::empty_v1();copy_native_paths_once_v1(&mut p,paths,&mut out,&mut bridge(&trace)).unwrap_or_else(|_|panic!());
            for i in 0..5 {let a=out.native[i].as_ref().unwrap();let b=out.retained[i].as_ref().unwrap();assert_eq!(a.slice_v1(),b.slice_v1());assert_ne!(a.bytes.as_ptr(),b.bytes.as_ptr());}
            assert_eq!(trace.allocated.get(),10);
            for case in 0..8 {let mut b=bytes.clone();match case {0=>b[0]=0,1=>word_put(&mut b,8,2),2=>word_put(&mut b,16,1),3=>word_put(&mut b,24,u64::MAX),4=>word_put(&mut b,24,0),5=>{b.pop();},6=>b.push(9),_=>b[64]=0};assert!(decode_path_packet_v1(&b,&r.policy).is_err());}
        }
        #[test] fn h07_binary_records_and_full_signed_identity() {
            let r=root();let d=data_set(&r.policy);assert!(parse_build(&d[1]).is_ok());let s=parse_session(&d[2]).unwrap();assert_eq!(s.budget,r.policy.validation);
            let id=decode_identity_v1(s.sections[0].bytes).unwrap();assert_eq!(id.mtime,i64::MIN);assert_eq!(id.ctime,i64::MAX);assert_eq!(id.mtime_ns,-1);
            assert!(parse_session(b"{\"extent\":1947}").is_err());
            for slot in [1,2] {for at in [0,8,16,24] {let mut b=d[slot].clone();b[at]^=1;assert!(if slot==1 {parse_build(&b).is_err()}else{parse_session(&b).is_err()});}}
            for at in [32,40] {let mut b=d[1].clone();word_put(&mut b,at,145);assert!(parse_build(&b).is_err());}
            for index in 0..5 {let r=root();let trace=Rc::new(Trace::default());let mut owner=acquired(&r,&trace);let at=[72,80,88,96,104][index];
                if let ActualInputSlotV1::Owned(f)=&mut owner.actual.as_mut().unwrap().partial.slots[2] {word_put(&mut f.body.as_mut().unwrap().bytes,at,0);}
                assert!(derive_provenance_v1(owner.actual.as_ref().unwrap(),&r.policy).is_err());}
        }
        #[test] fn h08_all_nine_groups_five_limits_and_thirty_two_identity_fields_refuse() {
            for mutation in 0..46 {let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);let (expected,attempt)=owner.correlation_scope_core_v1().unwrap();let mut c=carrier(&owner.expected,&trace);
                let p=&mut c.selected.as_mut().unwrap().provenance;
                match mutation {0=>p.source[0]^=1,1=>p.manifest[0]^=1,2=>p.build[0]^=1,3=>p.session[0]^=1,4=>p.executable[0]^=1,5=>p.nonce[0]^=1,6..=10=>match mutation-6 {0=>p.validation_budget.source_bytes+=1,1=>p.validation_budget.metadata_bytes+=1,2=>p.validation_budget.scratch_bytes+=1,3=>p.validation_budget.work_credits+=1,_=>p.validation_budget.deadline_ms+=1},11=>p.source_extent+=1,
                    12..=43=>{let n=mutation-12;let id=&mut p.identities[n/8];match n%8 {0=>id.dev^=1,1=>id.inode^=1,2=>id.bytes^=1,3=>id.mode^=1,4=>id.mtime^=1,5=>id.mtime_ns^=1,6=>id.ctime^=1,_=>id.ctime_ns^=1}},44=>p.source_extent=0,_=>p.identities[0].mtime_ns=i64::MAX}
                match correlate_core_v1(attempt,c,&expected) {Err((e,held))=>{assert!(matches!(e.kind,BootstrapFailureV1::Correlation(_)));assert!(held.selected.is_ok());assert_eq!(held.usage.hash_bytes,912);assert!(trace.drops.borrow().is_empty());drop(held);},Ok(_)=>panic!("mutation{} admitted",mutation)}
                assert_eq!(trace.drops.borrow().len(),4);drop(owner);assert_eq!(trace.drops.borrow().len(),17);
            }
        }
        struct OwnedSentinelResultV1 {
            selected:CorrelatedSelectedProfileV1, files:[Guard;3],executable:Option<Guard>,usage:LoaderUsageV1,
        }
        fn leaf_sentinel_return_owned_v1(matched:LoaderCarrierCoreV1<Guard>,leaf:&Cell<usize>)->OwnedSentinelResultV1 {
            let LoaderCarrierCoreV1 {selected,files,executable,usage}=matched;
            let selected=CorrelatedSelectedProfileV1(selected.unwrap());
            leaf.set(leaf.get()+1);
            OwnedSentinelResultV1 {selected,files,executable,usage}
        }
        #[test] fn h09_distinct_guard_handles_same_identity_real_proof_only_one_leaf() {
            let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);let (expected,attempt)=owner.correlation_scope_core_v1().unwrap();let c=carrier(&owner.expected,&trace);
            assert!(c.files[0].tag!=0);let proof_source=c.selected.as_ref().unwrap().proof.source().as_ptr();
            let leaf=Cell::new(0);let matched=match correlate_core_v1(attempt,c,&expected) {Ok(v)=>v,Err(_)=>panic!("correlation")};
            let result=leaf_sentinel_return_owned_v1(matched,&leaf);
            // The owned result retains the SAME real validator-created Box and
            // every original File substitute through this complete inspection.
            assert_eq!(result.selected.0.proof.source().as_ptr(),proof_source);
            assert_eq!(result.selected.0.source(),body_v1(owner.owned.actual.as_ref().unwrap(),0).unwrap());
            assert_eq!(result.files.each_ref().map(|f|f.tag),[20,21,22]);assert_eq!(result.executable.as_ref().unwrap().tag,23);
            for i in 0..3 {assert_eq!(result.files[i].identity,owner.expected.identities[i]);}
            assert_eq!(result.executable.as_ref().unwrap().identity,owner.expected.identities[3]);
            assert_eq!(result.usage.hash_bytes,912);assert_eq!(leaf.get(),1);assert!(trace.drops.borrow().is_empty());
            assert_eq!(refusal(owner.correlation_scope_core_v1()),BootstrapFailureV1::AlreadyAttempted);
            drop(result);assert_eq!(*trace.drops.borrow(),vec![20,21,22,23]);
            let AdmittedImmutableOwnerCoreV1 {owned,..}=owner;
            let retained=match retire_acquired_owner_core_v1(owned,&mut bridge(&trace)) {AcquisitionRetirementOutcomeV1::Retained(v)=>v,_=>panic!("correlation barrier")};
            // This conservative correction has no discharge route even after
            // result destruction. Useful joint retirement remains unqualified.
            assert_eq!(*trace.drops.borrow(),vec![20,21,22,23]);assert_eq!(r.usage.get().storage,1_000_000);
            drop(retained);assert_eq!(*trace.drops.borrow(),(20..24).chain(0..13).collect::<Vec<_>>());assert_eq!(r.usage.get().storage,1_000_000);
        }
        #[test] fn h08_cross_owner_equal_metadata_retains_complete_carrier() {
            let a=root();let b=root();let trace=Rc::new(Trace::default());let first=admitted(&a,&trace);let second=admitted(&b,&trace);
            assert!(same_provenance_group_v1(&first.expected,&second.expected).is_ok());
            let (_own,attempt)=first.correlation_scope_core_v1().unwrap();let(foreign,_unused)=second.correlation_scope_core_v1().unwrap();
            let supplied=carrier(&first.expected,&trace);
            match correlate_core_v1(attempt,supplied,&foreign) {Err((e,held))=>{assert_eq!(e.kind,BootstrapFailureV1::LiveOwner);assert!(held.selected.is_ok());assert!(trace.drops.borrow().is_empty());drop(held);},Ok(_)=>panic!("foreign association")}
        }
        #[derive(Debug)]
        struct OriginalIoMarkerV1 { id:u64,drops:std::sync::Arc<std::sync::atomic::AtomicUsize> }
        impl std::fmt::Display for OriginalIoMarkerV1 {fn fmt(&self,f:&mut std::fmt::Formatter<'_>)->std::fmt::Result {write!(f,"original-test-marker-{}",self.id)}}
        impl std::error::Error for OriginalIoMarkerV1 {}
        impl Drop for OriginalIoMarkerV1 {fn drop(&mut self){self.drops.fetch_add(1,std::sync::atomic::Ordering::SeqCst);}}
        #[test] fn h10_whole_error_result_files_usage_move_before_live_refusal() {
            let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);let(expected,attempt)=owner.correlation_scope_core_v1().unwrap();owner.attempt_taken.set(false);
            let mut c=carrier(&owner.expected,&trace);let failure=validate_swift_reactor(b"bad",owner.expected.validation_budget,&Cancellation::default()).err().unwrap();
            let drops=std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
            let original_io=io::Error::new(io::ErrorKind::Other,OriginalIoMarkerV1 {id:0x9197,drops:drops.clone()});
            let payload_before=original_io.get_ref().unwrap().downcast_ref::<OriginalIoMarkerV1>().unwrap() as *const OriginalIoMarkerV1;
            c.selected=Err(LoaderFailureV1 {io:Some(original_io),validation:Some(failure),..LoaderFailureV1::new(Refusal::Validation,Role::Source,7,3)});
            let (original,c)=match correlate_core_v1(attempt,c,&expected) {Err(v)=>v,Ok(_)=>panic!()};assert_eq!(original.kind,BootstrapFailureV1::LiveOwner);
            let e=c.selected.as_ref().err().unwrap();let payload_after=e.io.as_ref().unwrap().get_ref().unwrap().downcast_ref::<OriginalIoMarkerV1>().unwrap();
            assert_eq!(payload_after.id,0x9197);assert!(std::ptr::eq(payload_before,payload_after));assert_eq!(drops.load(std::sync::atomic::Ordering::SeqCst),0);
            assert!(e.validation.is_some());assert_eq!(e.offset,7);assert_eq!(e.attempts,3);
            assert_eq!(c.files.each_ref().map(|r|r.tag),[20,21,22]);assert_eq!(c.executable.as_ref().unwrap().tag,23);assert_eq!(c.usage.hash_bytes,912);
            assert!(trace.drops.borrow().is_empty());drop(c);assert_eq!(drops.load(std::sync::atomic::Ordering::SeqCst),1);
            assert_eq!(*trace.drops.borrow(),vec![20,21,22,23]);assert_eq!(r.usage.get().storage,1_000_000);
        }
        #[test] fn h11_retirement_order_complete_token_failure_unwind_no_token() {
            let r=root();let trace=Rc::new(Trace::default());let owner=acquired(&r,&trace);let before=r.usage.get();let token=match retire_acquired_owner_core_v1(owner,&mut bridge(&trace)) {
                AcquisitionRetirementOutcomeV1::Complete(t)=>t,_=>panic!("complete typed guards")};assert_eq!(*trace.drops.borrow(),(0..13).collect::<Vec<_>>());assert_eq!(r.usage.get(),before);token.release_v1();assert_eq!(r.usage.get().storage,0);assert_eq!(r.usage.get().work,before.work);
            for fail in 0..13 {let r=root();let trace=Rc::new(Trace::default());let owner=acquired(&r,&trace);let mut b=bridge(&trace);b.fail_retirement=Some(fail);let result=retire_acquired_owner_core_v1(owner,&mut b);
                let owner=match result {AcquisitionRetirementOutcomeV1::Retained(v)=>v,_=>panic!()};assert_eq!(trace.drops.borrow().len(),fail);assert_eq!(r.usage.get().storage,1_000_000);assert!(owner.retirement_started);drop(owner);}
            let r=root();let trace=Rc::new(Trace::default());let owner=acquired(&r,&trace);let mut b=bridge(&trace);b.unwind_retirement=Some(3);let result=catch_unwind(AssertUnwindSafe(||retire_acquired_owner_core_v1(owner,&mut b)));assert!(result.is_err());assert_eq!(r.usage.get().storage,1_000_000);
            let r=root();let trace=Rc::new(Trace::default());let mut owner=acquired(&r,&trace);owner.reservation.cleanup_left=0;assert!(matches!(retire_acquired_owner_core_v1(owner,&mut bridge(&trace)),AcquisitionRetirementOutcomeV1::Retained(_)));assert_eq!(r.usage.get().storage,1_000_000);
        }
        #[test] fn h12_prepaid_ingress_required_before_private_admission_publication() {
            for work in [true,false] {let r=root();let trace=Rc::new(Trace::default());let mut owner=acquired(&r,&trace);if work {
                    let actual=owner.actual.as_ref().unwrap();let final_work=(0..13).map(|i|body_v1(actual,i).unwrap().len() as u64).sum::<u64>()+13
                        +body_v1(actual,1).unwrap().len() as u64+body_v1(actual,2).unwrap().len() as u64+64;
                    owner.reservation.operation_left=final_work+30;
                }else{owner.reservation.storage_left=42;}
                let result=complete_admission_core_v1(owner,TrustedLocalLauncherCustodyV1 {_private:()},&mut bridge(&trace));let held=match result {OwnedAdmissionCoreOutcomeV1::Refused(v)=>v,_=>panic!("unprepaid admission")};assert_eq!(held.actual.as_ref().unwrap().partial.original.as_ref().unwrap().slot,13);assert!(trace.drops.borrow().is_empty());}
        }
        #[test] fn h13_real_validator_backing_owned_independently_and_old_limits_unselected() {
            let r=root();let source=wasm_source();let proof=validate_swift_reactor(&source,r.policy.validation,&Cancellation::default()).unwrap();assert_eq!(proof.source(),source);assert_ne!(proof.source().as_ptr(),source.as_ptr());drop(source);assert_eq!(proof.source().len(),1947);
            assert_eq!(refusal(selected_bootstrap_ledger_v1()),BootstrapFailureV1::BootstrapPolicyPending);
        }
        fn assert_correlation_barrier_v1<'r>(owner:AdmittedImmutableOwnerCoreV1<'r,Guard>,trace:&Rc<Trace>)
            -> PrepaidInputOwnerV1<'r,Guard>
        {
            let owned=owner.owned;assert!(owned.correlation_retirement_blocked.get());
            let cleanup_before=owned.reservation.cleanup_left;let usage_before=owned.reservation.root.usage.get();
            let retained=match retire_acquired_owner_core_v1(owned,&mut bridge(trace)) {
                AcquisitionRetirementOutcomeV1::Retained(v)=>v,
                AcquisitionRetirementOutcomeV1::Complete(_)=>panic!("correlated acquisition completed"),
            };
            assert!(!retained.retirement_started);assert_eq!(retained.reservation.cleanup_left,cleanup_before);
            assert_eq!(retained.reservation.root.usage.get(),usage_before);retained
        }
        #[test] fn h14_live_matched_carrier_cannot_coexist_with_complete_acquisition() {
            let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);
            let (held,proof_source)={let(expected,attempt)=owner.correlation_scope_core_v1().unwrap();let supplied=carrier(&owner.expected,&trace);
                let proof_source=supplied.selected.as_ref().unwrap().proof.source().as_ptr();
                (match correlate_core_v1(attempt,supplied,&expected) {Ok(v)=>v,Err(_)=>panic!("matched")},proof_source)};
            let retained=assert_correlation_barrier_v1(owner,&trace);
            assert!(trace.drops.borrow().is_empty());assert_eq!(r.usage.get().storage,1_000_000);
            drop(retained);assert_eq!(*trace.drops.borrow(),(0..13).collect::<Vec<_>>());
            let proof=&held.selected.as_ref().unwrap().proof;assert_eq!(proof.source().as_ptr(),proof_source);assert_eq!(proof.source().len(),1947);
            assert_eq!(held.files.each_ref().map(|f|f.tag),[20,21,22]);assert_eq!(held.executable.as_ref().unwrap().tag,23);
            assert_eq!(held.usage.hash_bytes,912);assert_eq!(r.usage.get().storage,1_000_000);
            drop(held);assert_eq!(*trace.drops.borrow(),(0..13).chain(20..24).collect::<Vec<_>>());assert_eq!(r.usage.get().storage,1_000_000);
        }
        #[test] fn h15_live_loader_refusal_retains_original_error_and_acquisition_charge() {
            let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);
            let drops=std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
            let original=io::Error::new(io::ErrorKind::Other,OriginalIoMarkerV1 {id:0x1519,drops:drops.clone()});
            let original_pointer=original.get_ref().unwrap().downcast_ref::<OriginalIoMarkerV1>().unwrap() as *const OriginalIoMarkerV1;
            let held={let(expected,attempt)=owner.correlation_scope_core_v1().unwrap();let mut supplied=carrier(&owner.expected,&trace);
                supplied.selected=Err(LoaderFailureV1 {io:Some(original),..LoaderFailureV1::new(Refusal::Io,Role::Build,19,5)});
                match correlate_core_v1(attempt,supplied,&expected) {Ok(v)=>v,Err(_)=>panic!("loader refusal correlation")}};
            let retained=assert_correlation_barrier_v1(owner,&trace);assert!(trace.drops.borrow().is_empty());drop(retained);
            let original=held.selected.as_ref().err().unwrap();assert_eq!(original.offset,19);assert_eq!(original.attempts,5);
            let marker=original.io.as_ref().unwrap().get_ref().unwrap().downcast_ref::<OriginalIoMarkerV1>().unwrap();
            assert!(std::ptr::eq(original_pointer,marker));assert_eq!(marker.id,0x1519);assert_eq!(drops.load(std::sync::atomic::Ordering::SeqCst),0);
            assert_eq!(held.usage.hash_bytes,912);assert_eq!(held.files.each_ref().map(|f|f.tag),[20,21,22]);assert_eq!(held.executable.as_ref().unwrap().tag,23);
            assert_eq!(r.usage.get().storage,1_000_000);drop(held);assert_eq!(drops.load(std::sync::atomic::Ordering::SeqCst),1);assert_eq!(r.usage.get().storage,1_000_000);
        }
        #[test] fn h16_live_provenance_refusal_keeps_proof_guard_carrier_charged() {
            let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);
            let (original,held,proof_source)={let(expected,attempt)=owner.correlation_scope_core_v1().unwrap();let mut supplied=carrier(&owner.expected,&trace);
                let selected=supplied.selected.as_mut().unwrap();let proof_source=selected.proof.source().as_ptr();selected.provenance.source[0]^=1;
                let(original,held)=match correlate_core_v1(attempt,supplied,&expected) {Err(v)=>v,Ok(_)=>panic!("provenance refusal")};(original,held,proof_source)};
            let retained=assert_correlation_barrier_v1(owner,&trace);assert_eq!(original.kind,BootstrapFailureV1::Correlation(0));assert!(trace.drops.borrow().is_empty());drop(retained);
            let proof=&held.selected.as_ref().unwrap().proof;assert_eq!(proof.source().as_ptr(),proof_source);assert_eq!(proof.source().len(),1947);
            assert_eq!(held.files.each_ref().map(|f|f.tag),[20,21,22]);assert_eq!(held.executable.as_ref().unwrap().tag,23);assert_eq!(held.usage.hash_bytes,912);
            assert_eq!(r.usage.get().storage,1_000_000);drop(held);assert_eq!(r.usage.get().storage,1_000_000);
        }
        #[test] fn h17_live_cross_owner_refusal_blocks_both_acquisition_retirements() {
            let a=root();let b=root();let trace=Rc::new(Trace::default());let first=admitted(&a,&trace);let second=admitted(&b,&trace);
            let (original,held)={let(_own,attempt)=first.correlation_scope_core_v1().unwrap();let(foreign,_unused)=second.correlation_scope_core_v1().unwrap();
                match correlate_core_v1(attempt,carrier(&first.expected,&trace),&foreign) {Err(v)=>v,Ok(_)=>panic!("foreign association")}};
            let retained_first=assert_correlation_barrier_v1(first,&trace);let retained_second=assert_correlation_barrier_v1(second,&trace);
            assert_eq!(original.kind,BootstrapFailureV1::LiveOwner);assert!(trace.drops.borrow().is_empty());
            drop(retained_first);drop(retained_second);assert_eq!(trace.drops.borrow().len(),26);
            assert_eq!(held.selected.as_ref().unwrap().proof.source().len(),1947);assert_eq!(held.files.each_ref().map(|f|f.tag),[20,21,22]);
            assert_eq!(a.usage.get().storage,1_000_000);assert_eq!(b.usage.get().storage,1_000_000);drop(held);
        }
        #[test] fn h18_extracted_selected_and_guard_parts_cannot_discharge_barrier() {
            let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);
            let held={let(expected,attempt)=owner.correlation_scope_core_v1().unwrap();match correlate_core_v1(attempt,carrier(&owner.expected,&trace),&expected) {Ok(v)=>v,Err(_)=>panic!()}};
            let LoaderCarrierCoreV1 {selected,files,executable,usage}=held;
            let selected=CorrelatedSelectedProfileV1(selected.unwrap()).into_selected_v1();let proof_source=selected.proof.source().as_ptr();
            let retained=assert_correlation_barrier_v1(owner,&trace);assert!(trace.drops.borrow().is_empty());drop(retained);
            assert_eq!(selected.proof.source().as_ptr(),proof_source);assert_eq!(selected.proof.source().len(),1947);
            assert_eq!(files.each_ref().map(|f|f.tag),[20,21,22]);assert_eq!(executable.as_ref().unwrap().tag,23);assert_eq!(usage.hash_bytes,912);
            assert_eq!(r.usage.get().storage,1_000_000);drop(selected);drop(files);drop(executable);assert_eq!(r.usage.get().storage,1_000_000);
        }
        #[test] fn h19_forgotten_matched_and_refused_outcomes_never_authorize_complete() {
            for kind in 0..4 {let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);
                let outcome={let(mut expected,attempt)=owner.correlation_scope_core_v1().unwrap();let mut supplied=carrier(&owner.expected,&trace);
                    match kind {1=>supplied.selected=Err(LoaderFailureV1::new(Refusal::Io,Role::Source,17,2)),
                        2=>supplied.selected.as_mut().unwrap().provenance.source[0]^=1,3=>expected.association+=1,_=>{}}
                    correlate_core_v1(attempt,supplied,&expected)};
                assert_eq!(outcome.is_err(),kind>=2);std::mem::forget(outcome);
                let retained=assert_correlation_barrier_v1(owner,&trace);assert!(trace.drops.borrow().is_empty());drop(retained);
                assert_eq!(*trace.drops.borrow(),(0..13).collect::<Vec<_>>());assert_eq!(r.usage.get().storage,1_000_000);
            }
        }
        #[test] fn h20_issued_unused_scope_is_sticky_but_unissued_owner_keeps_original_cleanup() {
            let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);
            {let(_expected,_unused)=owner.correlation_scope_core_v1().unwrap();}
            assert_eq!(refusal(owner.correlation_scope_core_v1()),BootstrapFailureV1::AlreadyAttempted);
            let retained=assert_correlation_barrier_v1(owner,&trace);assert!(trace.drops.borrow().is_empty());drop(retained);assert_eq!(r.usage.get().storage,1_000_000);
            let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);assert!(!owner.owned.correlation_retirement_blocked.get());
            let before=r.usage.get();let token=match retire_acquired_owner_core_v1(owner.owned,&mut bridge(&trace)) {AcquisitionRetirementOutcomeV1::Complete(v)=>v,_=>panic!("unissued cleanup")};
            assert_eq!(*trace.drops.borrow(),(0..13).collect::<Vec<_>>());assert_eq!(r.usage.get(),before);token.release_v1();assert_eq!(r.usage.get().storage,0);assert_eq!(r.usage.get().work,before.work);
        }
        #[test] fn h21_absent_optional_executable_preserves_every_correlation_barrier() {
            for kind in 0..4 {let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);
                let (refused,held)={let(mut expected,attempt)=owner.correlation_scope_core_v1().unwrap();let mut supplied=carrier(&owner.expected,&trace);
                    drop(supplied.executable.take());
                    match kind {1=>supplied.selected=Err(LoaderFailureV1::new(Refusal::Io,Role::Source,21,3)),
                        2=>supplied.selected.as_mut().unwrap().provenance.source[0]^=1,3=>expected.association+=1,_=>{}}
                    match correlate_core_v1(attempt,supplied,&expected) {Ok(v)=>(false,v),Err((_original,v))=>(true,v)}};
                assert_eq!(refused,kind>=2);assert_eq!(*trace.drops.borrow(),vec![23]);
                let retained=assert_correlation_barrier_v1(owner,&trace);assert_eq!(*trace.drops.borrow(),vec![23]);drop(retained);
                assert!(held.executable.is_none());assert_eq!(held.files.each_ref().map(|f|f.tag),[20,21,22]);assert_eq!(held.usage.hash_bytes,912);
                match held.selected.as_ref() {Ok(v)=>assert_eq!(v.proof.source().len(),1947),Err(e)=>{assert_eq!(e.offset,21);assert_eq!(e.attempts,3);}}
                assert_eq!(r.usage.get().storage,1_000_000);drop(held);assert_eq!(r.usage.get().storage,1_000_000);
            }
        }
        #[test] fn h22_positive_move_and_borrowed_return_controls() {
            fn move_reservation<'r>(paid:AcquisitionReservationV1<'r>)->AcquisitionReservationV1<'r> {paid}
            fn move_attempt<'o>(attempt:PrepaidCorrelationAttemptV1<'o>)->PrepaidCorrelationAttemptV1<'o> {attempt}
            fn borrow_source(selected:&SelectedValidatedProfileV1)->&[u8] {selected.proof.source()}
            fn borrow_correspondence<'o>(expected:&AdmittedLoaderCorrespondenceV1<'o>)->&'o LoaderProvenanceV1 {expected.owner_data}
            let r=root();let reservation=move_reservation(paid(&r));assert_eq!(reservation.root.usage.get().storage,1_000_000);drop(reservation);assert_eq!(r.usage.get().storage,1_000_000);
            let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);
            let held={let(expected,attempt)=owner.correlation_scope_core_v1().unwrap();assert_eq!(borrow_correspondence(&expected).source_extent,1947);
                match correlate_core_v1(move_attempt(attempt),carrier(&owner.expected,&trace),&expected) {Ok(v)=>v,Err(_)=>panic!("positive move")}};
            assert_eq!(borrow_source(held.selected.as_ref().unwrap()).len(),1947);drop(held);
            let retained=assert_correlation_barrier_v1(owner,&trace);drop(retained);assert_eq!(r.usage.get().storage,1_000_000);
        }
        // Independent desired-property witness. Test-only construction uses the
        // frozen candidate's real admitted core and real validator-created proof.
        // All ownership/correlation/retirement functions remain production code.
        #[test]
        fn independent_result_live_acquisition_retirement_v1() {
            let r = root();
            let trace = Rc::new(Trace::default());
            let owner = admitted(&r, &trace);
            let (expected, attempt) = owner.correlation_scope_core_v1().unwrap();
            let supplied = carrier(&owner.expected, &trace);
            let proof_pointer = supplied.selected.as_ref().unwrap().proof.source().as_ptr();
            let retained_result = match correlate_core_v1(attempt, supplied, &expected) {
                Ok(original) => original,
                Err(_) => panic!("positive control unexpectedly refused"),
            };
            drop(expected);
            let before = r.usage.get();
            let AdmittedImmutableOwnerCoreV1 { owned, .. } = owner;
            let token = match retire_acquired_owner_core_v1(owned, &mut bridge(&trace)) {
                AcquisitionRetirementOutcomeV1::Complete(token) => token,
                AcquisitionRetirementOutcomeV1::Retained(_) => {
                    // Retention is a valid fail-closed desired outcome.
                    assert_eq!(r.usage.get().storage, before.storage);
                    return;
                }
            };
            let while_token_owned = r.usage.get();
            token.release_v1();
            let after_release = r.usage.get();
            let live_proof = &retained_result.selected.as_ref().unwrap().proof;
            assert_eq!(live_proof.source().as_ptr(), proof_pointer);
            assert_eq!(live_proof.source().len(), 1947);
            assert_eq!(retained_result.files.each_ref().map(|guard| guard.tag), [20, 21, 22]);
            assert_eq!(retained_result.executable.as_ref().unwrap().tag, 23);
            assert_eq!(*trace.drops.borrow(), (0..13).collect::<Vec<_>>());
            eprintln!("INDEPENDENT_RETIREMENT_WITNESS before_storage={} token_storage={} released_storage={} live_proof_bytes={} live_loader_tags=20,21,22,23 acquisition_drops={:?}",
                before.storage, while_token_owned.storage, after_release.storage,
                live_proof.source().len(), trace.drops.borrow());
            // Required PA06/H11 property: complete acquisition release must not
            // discharge its fixed correlation/result/proof overlap while live.
            assert_eq!(after_release.storage, before.storage,
                "desired property failed: acquisition storage released while actual correlated proof and four original guard resources remain live");
            drop(retained_result);
        }
// Generated only from immutable preaccess vector bytes; no production authority.
fn independent_binary_vectors_v1() -> Vec<(&'static str,u8,Vec<u8>,bool,&'static str)> { vec![
("build-version",0,&[77,73,88,76,66,68,48,49,2,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"Header/Build/0"),
("build-header-size",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,255,1,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"Header/Build/0"),
("build-total",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,138,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"Header/Build/0"),
("build-source-count",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,145,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"BuildIdentity/Build/32"),
("build-host-count",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,12,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"BuildIdentity/Build/32"),
("build-output-zero",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"BuildIdentity/Build/32"),
("build-output-over-cap",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,1,0,0,4,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"BuildIdentity/Build/32"),
("build-target",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,88,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"Reserved/Build/88"),
("build-target-padding",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,120,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"Reserved/Build/88"),
("build-reserved",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,120,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"Reserved/Build/88"),
("build-empty-section-0",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"Extent/Build/current cursor"),
("build-overflow-section-0",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,255,255,255,255,255,255,255,255,43,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"Extent/Build/current cursor"),
("build-empty-section-1",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"Extent/Build/current cursor"),
("build-overflow-section-1",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,255,255,255,255,255,255,255,255,30,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"Extent/Build/current cursor"),
("build-empty-section-2",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"Extent/Build/current cursor"),
("build-overflow-section-2",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,255,255,255,255,255,255,255,255,18,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"Extent/Build/current cursor"),
("build-empty-section-3",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"Extent/Build/current cursor"),
("build-overflow-section-3",0,&[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,255,255,255,255,255,255,255,255,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10].to_vec(),false,"Extent/Build/current cursor"),
("session-reserved",1,&[77,73,88,76,83,69,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,139,2,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,0,0,0,0,0,0,0,35,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,1,0,0,0,0,0,64,66,15,0,0,0,0,0,16,39,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,120,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,129,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115].to_vec(),false,"Reserved/Session/368"),
("session-version",1,&[77,73,88,76,83,69,48,49,7,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,139,2,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,0,0,0,0,0,0,0,35,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,1,0,0,0,0,0,64,66,15,0,0,0,0,0,16,39,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,129,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115].to_vec(),false,"Header/Session/0"),
("session-header-size",1,&[77,73,88,76,83,69,48,49,1,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,139,2,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,0,0,0,0,0,0,0,35,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,1,0,0,0,0,0,64,66,15,0,0,0,0,0,16,39,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,129,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115].to_vec(),false,"Header/Session/0"),
("session-total",1,&[77,73,88,76,83,69,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,7,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,0,0,0,0,0,0,0,35,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,1,0,0,0,0,0,64,66,15,0,0,0,0,0,16,39,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,129,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115].to_vec(),false,"Header/Session/0"),
("session-empty-section-0",1,&[77,73,88,76,83,69,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,139,2,0,0,0,0,0,0,155,7,0,0,0,0,0,0,0,0,0,0,0,0,0,0,35,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,1,0,0,0,0,0,64,66,15,0,0,0,0,0,16,39,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,129,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115].to_vec(),false,"Extent/Session/current cursor"),
("session-empty-section-1",1,&[77,73,88,76,83,69,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,139,2,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,1,0,0,0,0,0,64,66,15,0,0,0,0,0,16,39,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,129,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115].to_vec(),false,"Extent/Session/current cursor"),
("session-empty-section-2",1,&[77,73,88,76,83,69,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,139,2,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,0,0,0,0,0,0,0,35,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,1,0,0,0,0,0,64,66,15,0,0,0,0,0,16,39,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,129,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115].to_vec(),false,"Extent/Session/current cursor"),
("session-empty-section-3",1,&[77,73,88,76,83,69,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,139,2,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,0,0,0,0,0,0,0,35,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,1,0,0,0,0,0,64,66,15,0,0,0,0,0,16,39,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,129,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115].to_vec(),false,"Extent/Session/current cursor"),
("session-zero-source-extent",1,&[77,73,88,76,83,69,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,139,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,64,0,0,0,0,0,0,0,35,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,1,0,0,0,0,0,64,66,15,0,0,0,0,0,16,39,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,129,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115].to_vec(),true,"positive source extent; old parser positive"),
("session-zero-limit-0",1,&[77,73,88,76,83,69,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,139,2,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,0,0,0,0,0,0,0,35,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,1,0,0,0,0,0,64,66,15,0,0,0,0,0,16,39,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,129,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115].to_vec(),true,"positive exact selected limit; old parser positive"),
("session-zero-limit-1",1,&[77,73,88,76,83,69,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,139,2,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,0,0,0,0,0,0,0,35,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,64,66,15,0,0,0,0,0,16,39,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,129,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115].to_vec(),true,"positive exact selected limit; old parser positive"),
("session-zero-limit-2",1,&[77,73,88,76,83,69,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,139,2,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,0,0,0,0,0,0,0,35,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,0,0,0,0,0,0,64,66,15,0,0,0,0,0,16,39,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,129,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115].to_vec(),true,"positive exact selected limit; old parser positive"),
("session-zero-limit-3",1,&[77,73,88,76,83,69,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,139,2,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,0,0,0,0,0,0,0,35,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,16,39,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,129,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115].to_vec(),true,"positive exact selected limit; old parser positive"),
("session-zero-limit-4",1,&[77,73,88,76,83,69,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,139,2,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,0,0,0,0,0,0,0,35,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,1,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,129,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115].to_vec(),true,"positive exact selected limit; old parser positive"),
("session-nonregular-identity",1,&[77,73,88,76,83,69,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,139,2,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,0,0,0,0,0,0,0,35,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,1,0,0,0,0,0,64,66,15,0,0,0,0,0,16,39,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,65,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115].to_vec(),true,"regular complete source identity; old parser positive"),
("path-magic",2,&[88,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"magic"),
("path-version",2,&[77,73,88,80,84,72,48,49,2,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"version"),
("path-total",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,99,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"total"),
("path-empty-0",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"positive length"),
("path-overflow-0",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,255,255,255,255,255,255,255,255,5,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"cap or checked end"),
("path-nul-0",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,0,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"NUL"),
("path-empty-1",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"positive length"),
("path-overflow-1",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,255,255,255,255,255,255,255,255,7,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"cap or checked end"),
("path-nul-1",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,115,111,117,114,99,101,0,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"NUL"),
("path-empty-2",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"positive length"),
("path-overflow-2",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,255,255,255,255,255,255,255,255,6,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"cap or checked end"),
("path-nul-2",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,0,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"NUL"),
("path-empty-3",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"positive length"),
("path-overflow-3",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,255,255,255,255,255,255,255,255,10,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"cap or checked end"),
("path-nul-3",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,0,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"NUL"),
("path-empty-4",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"positive length"),
("path-overflow-4",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,255,255,255,255,255,255,255,255,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254].to_vec(),false,"cap or checked end"),
("path-nul-4",2,&[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,0,110,97,112,115,104,111,116,45,254].to_vec(),false,"NUL"),
] }
const INDEPENDENT_MIXLBD01: &[u8] = &[77,73,88,76,66,68,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,137,2,0,0,0,0,0,0,146,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,46,0,0,0,0,0,0,0,43,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,18,0,0,0,0,0,0,0,33,0,0,0,0,0,0,0,97,97,114,99,104,54,52,45,97,112,112,108,101,45,100,97,114,119,105,110,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,166,3,104,154,248,163,233,34,143,174,192,161,236,176,232,199,233,218,170,253,181,201,118,174,81,18,251,74,80,216,63,186,109,103,7,169,6,206,42,141,13,201,85,128,127,119,106,92,51,170,124,145,118,172,165,47,23,147,111,57,78,11,32,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,198,75,57,210,88,152,253,101,117,112,156,159,100,23,147,106,110,166,154,223,221,180,69,156,203,219,245,15,239,230,45,132,35,161,160,210,208,159,209,83,12,81,56,207,7,71,31,24,180,118,123,218,105,215,224,207,14,93,221,85,180,79,40,124,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,32,112,97,114,115,101,114,45,111,110,108,121,32,109,97,110,105,102,101,115,116,59,32,110,111,116,32,97,117,116,104,111,114,105,116,121,10,2,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,114,117,115,116,99,14,0,0,0,0,0,0,0,45,45,101,100,105,116,105,111,110,61,50,48,50,49,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,112,114,101,97,99,99,101,115,115,32,118,101,114,115,105,111,110,10];
const INDEPENDENT_MIXLSE01: &[u8] = &[77,73,88,76,83,69,48,49,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,139,2,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,0,0,0,0,0,0,0,35,0,0,0,0,0,0,0,30,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,64,66,15,0,0,0,0,0,0,0,1,0,0,0,0,0,64,66,15,0,0,0,0,0,16,39,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,165,45,145,255,116,63,187,167,27,227,246,249,229,23,104,149,191,135,48,114,212,88,192,206,220,116,159,247,103,239,95,35,136,70,70,40,244,47,25,116,3,88,125,180,169,11,148,105,163,188,145,143,132,49,224,213,112,142,183,186,196,240,176,8,38,123,28,241,143,253,1,67,17,71,30,162,119,125,181,13,27,135,204,35,71,137,103,21,73,160,76,83,175,65,149,159,91,183,85,108,143,104,67,84,45,223,139,48,84,201,174,182,137,26,217,22,205,26,105,237,145,204,208,156,223,28,2,254,72,227,106,102,161,41,54,239,163,27,98,106,46,109,234,22,151,168,20,43,155,96,100,0,205,150,242,30,171,114,148,113,162,158,200,254,15,13,135,200,113,101,156,99,240,162,151,244,2,32,160,34,217,89,197,153,91,73,39,227,78,230,74,182,138,194,92,176,35,205,122,88,72,6,205,48,149,190,162,100,70,17,38,115,163,91,146,18,111,123,223,213,162,169,153,39,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,11,0,0,0,0,0,0,0,101,0,0,0,0,0,0,0,155,7,0,0,0,0,0,0,128,129,0,0,0,0,0,0,0,0,0,0,0,0,0,128,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,127,1,0,0,0,0,0,0,0,19,0,0,0,0,0,0,0,112,114,101,97,99,99,101,115,115,45,99,111,109,112,111,110,101,110,116,2,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,65,61,49,3,0,0,0,0,0,0,0,66,61,50,47,112,114,101,97,99,99,101,115,115];
const INDEPENDENT_MIXPTH01: &[u8] = &[77,73,88,80,84,72,48,49,1,0,0,0,0,0,0,0,98,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,7,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,10,0,0,0,0,0,0,0,115,111,117,114,99,101,98,117,105,108,100,115,101,115,115,105,111,110,114,111,119,115,45,255,115,110,97,112,115,104,111,116,45,254];
fn independent_provenance_vectors_v1() -> Vec<(&'static str,usize,usize,usize,u64)> { vec![
("correlation-source-byte-00",0,0,0,1u64),
("correlation-source-byte-01",0,1,0,1u64),
("correlation-source-byte-02",0,2,0,1u64),
("correlation-source-byte-03",0,3,0,1u64),
("correlation-source-byte-04",0,4,0,1u64),
("correlation-source-byte-05",0,5,0,1u64),
("correlation-source-byte-06",0,6,0,1u64),
("correlation-source-byte-07",0,7,0,1u64),
("correlation-source-byte-08",0,8,0,1u64),
("correlation-source-byte-09",0,9,0,1u64),
("correlation-source-byte-10",0,10,0,1u64),
("correlation-source-byte-11",0,11,0,1u64),
("correlation-source-byte-12",0,12,0,1u64),
("correlation-source-byte-13",0,13,0,1u64),
("correlation-source-byte-14",0,14,0,1u64),
("correlation-source-byte-15",0,15,0,1u64),
("correlation-source-byte-16",0,16,0,1u64),
("correlation-source-byte-17",0,17,0,1u64),
("correlation-source-byte-18",0,18,0,1u64),
("correlation-source-byte-19",0,19,0,1u64),
("correlation-source-byte-20",0,20,0,1u64),
("correlation-source-byte-21",0,21,0,1u64),
("correlation-source-byte-22",0,22,0,1u64),
("correlation-source-byte-23",0,23,0,1u64),
("correlation-source-byte-24",0,24,0,1u64),
("correlation-source-byte-25",0,25,0,1u64),
("correlation-source-byte-26",0,26,0,1u64),
("correlation-source-byte-27",0,27,0,1u64),
("correlation-source-byte-28",0,28,0,1u64),
("correlation-source-byte-29",0,29,0,1u64),
("correlation-source-byte-30",0,30,0,1u64),
("correlation-source-byte-31",0,31,0,1u64),
("correlation-manifest-byte-00",1,0,0,1u64),
("correlation-manifest-byte-01",1,1,0,1u64),
("correlation-manifest-byte-02",1,2,0,1u64),
("correlation-manifest-byte-03",1,3,0,1u64),
("correlation-manifest-byte-04",1,4,0,1u64),
("correlation-manifest-byte-05",1,5,0,1u64),
("correlation-manifest-byte-06",1,6,0,1u64),
("correlation-manifest-byte-07",1,7,0,1u64),
("correlation-manifest-byte-08",1,8,0,1u64),
("correlation-manifest-byte-09",1,9,0,1u64),
("correlation-manifest-byte-10",1,10,0,1u64),
("correlation-manifest-byte-11",1,11,0,1u64),
("correlation-manifest-byte-12",1,12,0,1u64),
("correlation-manifest-byte-13",1,13,0,1u64),
("correlation-manifest-byte-14",1,14,0,1u64),
("correlation-manifest-byte-15",1,15,0,1u64),
("correlation-manifest-byte-16",1,16,0,1u64),
("correlation-manifest-byte-17",1,17,0,1u64),
("correlation-manifest-byte-18",1,18,0,1u64),
("correlation-manifest-byte-19",1,19,0,1u64),
("correlation-manifest-byte-20",1,20,0,1u64),
("correlation-manifest-byte-21",1,21,0,1u64),
("correlation-manifest-byte-22",1,22,0,1u64),
("correlation-manifest-byte-23",1,23,0,1u64),
("correlation-manifest-byte-24",1,24,0,1u64),
("correlation-manifest-byte-25",1,25,0,1u64),
("correlation-manifest-byte-26",1,26,0,1u64),
("correlation-manifest-byte-27",1,27,0,1u64),
("correlation-manifest-byte-28",1,28,0,1u64),
("correlation-manifest-byte-29",1,29,0,1u64),
("correlation-manifest-byte-30",1,30,0,1u64),
("correlation-manifest-byte-31",1,31,0,1u64),
("correlation-build-byte-00",2,0,0,1u64),
("correlation-build-byte-01",2,1,0,1u64),
("correlation-build-byte-02",2,2,0,1u64),
("correlation-build-byte-03",2,3,0,1u64),
("correlation-build-byte-04",2,4,0,1u64),
("correlation-build-byte-05",2,5,0,1u64),
("correlation-build-byte-06",2,6,0,1u64),
("correlation-build-byte-07",2,7,0,1u64),
("correlation-build-byte-08",2,8,0,1u64),
("correlation-build-byte-09",2,9,0,1u64),
("correlation-build-byte-10",2,10,0,1u64),
("correlation-build-byte-11",2,11,0,1u64),
("correlation-build-byte-12",2,12,0,1u64),
("correlation-build-byte-13",2,13,0,1u64),
("correlation-build-byte-14",2,14,0,1u64),
("correlation-build-byte-15",2,15,0,1u64),
("correlation-build-byte-16",2,16,0,1u64),
("correlation-build-byte-17",2,17,0,1u64),
("correlation-build-byte-18",2,18,0,1u64),
("correlation-build-byte-19",2,19,0,1u64),
("correlation-build-byte-20",2,20,0,1u64),
("correlation-build-byte-21",2,21,0,1u64),
("correlation-build-byte-22",2,22,0,1u64),
("correlation-build-byte-23",2,23,0,1u64),
("correlation-build-byte-24",2,24,0,1u64),
("correlation-build-byte-25",2,25,0,1u64),
("correlation-build-byte-26",2,26,0,1u64),
("correlation-build-byte-27",2,27,0,1u64),
("correlation-build-byte-28",2,28,0,1u64),
("correlation-build-byte-29",2,29,0,1u64),
("correlation-build-byte-30",2,30,0,1u64),
("correlation-build-byte-31",2,31,0,1u64),
("correlation-session-byte-00",3,0,0,1u64),
("correlation-session-byte-01",3,1,0,1u64),
("correlation-session-byte-02",3,2,0,1u64),
("correlation-session-byte-03",3,3,0,1u64),
("correlation-session-byte-04",3,4,0,1u64),
("correlation-session-byte-05",3,5,0,1u64),
("correlation-session-byte-06",3,6,0,1u64),
("correlation-session-byte-07",3,7,0,1u64),
("correlation-session-byte-08",3,8,0,1u64),
("correlation-session-byte-09",3,9,0,1u64),
("correlation-session-byte-10",3,10,0,1u64),
("correlation-session-byte-11",3,11,0,1u64),
("correlation-session-byte-12",3,12,0,1u64),
("correlation-session-byte-13",3,13,0,1u64),
("correlation-session-byte-14",3,14,0,1u64),
("correlation-session-byte-15",3,15,0,1u64),
("correlation-session-byte-16",3,16,0,1u64),
("correlation-session-byte-17",3,17,0,1u64),
("correlation-session-byte-18",3,18,0,1u64),
("correlation-session-byte-19",3,19,0,1u64),
("correlation-session-byte-20",3,20,0,1u64),
("correlation-session-byte-21",3,21,0,1u64),
("correlation-session-byte-22",3,22,0,1u64),
("correlation-session-byte-23",3,23,0,1u64),
("correlation-session-byte-24",3,24,0,1u64),
("correlation-session-byte-25",3,25,0,1u64),
("correlation-session-byte-26",3,26,0,1u64),
("correlation-session-byte-27",3,27,0,1u64),
("correlation-session-byte-28",3,28,0,1u64),
("correlation-session-byte-29",3,29,0,1u64),
("correlation-session-byte-30",3,30,0,1u64),
("correlation-session-byte-31",3,31,0,1u64),
("correlation-executable-byte-00",4,0,0,1u64),
("correlation-executable-byte-01",4,1,0,1u64),
("correlation-executable-byte-02",4,2,0,1u64),
("correlation-executable-byte-03",4,3,0,1u64),
("correlation-executable-byte-04",4,4,0,1u64),
("correlation-executable-byte-05",4,5,0,1u64),
("correlation-executable-byte-06",4,6,0,1u64),
("correlation-executable-byte-07",4,7,0,1u64),
("correlation-executable-byte-08",4,8,0,1u64),
("correlation-executable-byte-09",4,9,0,1u64),
("correlation-executable-byte-10",4,10,0,1u64),
("correlation-executable-byte-11",4,11,0,1u64),
("correlation-executable-byte-12",4,12,0,1u64),
("correlation-executable-byte-13",4,13,0,1u64),
("correlation-executable-byte-14",4,14,0,1u64),
("correlation-executable-byte-15",4,15,0,1u64),
("correlation-executable-byte-16",4,16,0,1u64),
("correlation-executable-byte-17",4,17,0,1u64),
("correlation-executable-byte-18",4,18,0,1u64),
("correlation-executable-byte-19",4,19,0,1u64),
("correlation-executable-byte-20",4,20,0,1u64),
("correlation-executable-byte-21",4,21,0,1u64),
("correlation-executable-byte-22",4,22,0,1u64),
("correlation-executable-byte-23",4,23,0,1u64),
("correlation-executable-byte-24",4,24,0,1u64),
("correlation-executable-byte-25",4,25,0,1u64),
("correlation-executable-byte-26",4,26,0,1u64),
("correlation-executable-byte-27",4,27,0,1u64),
("correlation-executable-byte-28",4,28,0,1u64),
("correlation-executable-byte-29",4,29,0,1u64),
("correlation-executable-byte-30",4,30,0,1u64),
("correlation-executable-byte-31",4,31,0,1u64),
("correlation-nonce-byte-00",5,0,0,1u64),
("correlation-nonce-byte-01",5,1,0,1u64),
("correlation-nonce-byte-02",5,2,0,1u64),
("correlation-nonce-byte-03",5,3,0,1u64),
("correlation-nonce-byte-04",5,4,0,1u64),
("correlation-nonce-byte-05",5,5,0,1u64),
("correlation-nonce-byte-06",5,6,0,1u64),
("correlation-nonce-byte-07",5,7,0,1u64),
("correlation-nonce-byte-08",5,8,0,1u64),
("correlation-nonce-byte-09",5,9,0,1u64),
("correlation-nonce-byte-10",5,10,0,1u64),
("correlation-nonce-byte-11",5,11,0,1u64),
("correlation-nonce-byte-12",5,12,0,1u64),
("correlation-nonce-byte-13",5,13,0,1u64),
("correlation-nonce-byte-14",5,14,0,1u64),
("correlation-nonce-byte-15",5,15,0,1u64),
("correlation-nonce-byte-16",5,16,0,1u64),
("correlation-nonce-byte-17",5,17,0,1u64),
("correlation-nonce-byte-18",5,18,0,1u64),
("correlation-nonce-byte-19",5,19,0,1u64),
("correlation-nonce-byte-20",5,20,0,1u64),
("correlation-nonce-byte-21",5,21,0,1u64),
("correlation-nonce-byte-22",5,22,0,1u64),
("correlation-nonce-byte-23",5,23,0,1u64),
("correlation-nonce-byte-24",5,24,0,1u64),
("correlation-nonce-byte-25",5,25,0,1u64),
("correlation-nonce-byte-26",5,26,0,1u64),
("correlation-nonce-byte-27",5,27,0,1u64),
("correlation-nonce-byte-28",5,28,0,1u64),
("correlation-nonce-byte-29",5,29,0,1u64),
("correlation-nonce-byte-30",5,30,0,1u64),
("correlation-nonce-byte-31",5,31,0,1u64),
("correlation-limit-0",6,0,0,7u64),
("correlation-limit-1",6,1,0,1u64),
("correlation-limit-2",6,2,0,1u64),
("correlation-limit-3",6,3,0,1u64),
("correlation-limit-4",6,4,0,1u64),
("correlation-extent",7,0,0,7u64),
("correlation-identity-0-0",8,0,0,7u64),
("correlation-identity-0-1",8,0,1,3u64),
("correlation-identity-0-2",8,0,2,7u64),
("correlation-identity-0-3",8,0,3,1u64),
("correlation-identity-0-4",8,0,4,1u64),
("correlation-identity-0-5",8,0,5,18446744073709551615u64),
("correlation-identity-0-6",8,0,6,1u64),
("correlation-identity-0-7",8,0,7,1u64),
("correlation-identity-1-0",8,1,0,7u64),
("correlation-identity-1-1",8,1,1,1u64),
("correlation-identity-1-2",8,1,2,3u64),
("correlation-identity-1-3",8,1,3,1u64),
("correlation-identity-1-4",8,1,4,3u64),
("correlation-identity-1-5",8,1,5,18446744073709551615u64),
("correlation-identity-1-6",8,1,6,3u64),
("correlation-identity-1-7",8,1,7,1u64),
("correlation-identity-2-0",8,2,0,7u64),
("correlation-identity-2-1",8,2,1,15u64),
("correlation-identity-2-2",8,2,2,7u64),
("correlation-identity-2-3",8,2,3,1u64),
("correlation-identity-2-4",8,2,4,1u64),
("correlation-identity-2-5",8,2,5,18446744073709551615u64),
("correlation-identity-2-6",8,2,6,1u64),
("correlation-identity-2-7",8,2,7,3u64),
("correlation-identity-3-0",8,3,0,7u64),
("correlation-identity-3-1",8,3,1,1u64),
("correlation-identity-3-2",8,3,2,3u64),
("correlation-identity-3-3",8,3,3,1u64),
("correlation-identity-3-4",8,3,4,7u64),
("correlation-identity-3-5",8,3,5,18446744073709551615u64),
("correlation-identity-3-6",8,3,6,7u64),
("correlation-identity-3-7",8,3,7,1u64),
] }
fn independent_read_vectors_v1() -> Vec<(&'static str,usize,usize,usize,Vec<i64>,u8)> { vec![
("all-last-attempt-4095",4095,64,4095,vec![-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4095, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0],0),
("all-last-attempt-4096",4096,64,4096,vec![-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4096, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0],0),
("all-last-attempt-4097",4097,96,4097,vec![-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4096, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0],0),
("all-last-attempt-8192",8192,96,8192,vec![-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4096, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 4096, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0],0),
("no33rd-block",1,32,0,vec![-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 1, 0],1),
("no33rd-eof",1,33,1,vec![1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0],1),
("partial-original-io",4097,2,2048,vec![2048, -2],2),
("short-after-prefix",4096,2,13,vec![13, 0],3),
("overreported",4096,1,0,vec![4097],4),
("extra-eof",1,2,2,vec![1, 1],5),
("32-positive-partials",32,33,32,vec![1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],0),
("original-eof-io",1,2,1,vec![1, -2],2),
] }

        // All functions below are additive private cfg(test) review methods.
        // Frozen producer methods and every production byte are unchanged.
        fn independent_retained_v1<'r>(owner:AdmittedImmutableOwnerCoreV1<'r,Guard>, trace:&Rc<Trace>) -> PrepaidInputOwnerV1<'r,Guard> {
            let before=owner.owned.reservation.root.usage.get();
            let cleanup=owner.owned.reservation.cleanup_left;
            let operation=owner.owned.reservation.operation_left;
            let storage=owner.owned.reservation.storage_left;
            let retained=match retire_acquired_owner_core_v1(owner.owned,&mut bridge(trace)) {
                AcquisitionRetirementOutcomeV1::Retained(v)=>v,
                AcquisitionRetirementOutcomeV1::Complete(_)=>panic!("independent: issued scope minted Complete"),
            };
            assert!(!retained.retirement_started);
            assert_eq!(retained.reservation.cleanup_left,cleanup);
            assert_eq!(retained.reservation.operation_left,operation);
            assert_eq!(retained.reservation.storage_left,storage);
            assert_eq!(retained.reservation.root.usage.get(),before);
            retained
        }
        fn independent_usage_v1()->LoaderUsageV1 { LoaderUsageV1 {read_calls:[11,13,17,19],read_bytes:[23,29,31,37],
            hash_bytes:41,source_equality_bytes:43,allocated_peak_requested:47} }
        #[test]
        fn independent_i01_all_51_frozen_binary_substitutions_v1() {
            let mut r=root();r.policy.path_caps=[6,5,7,6,10];r.policy.packet_cap=98;
            assert!(parse_build(INDEPENDENT_MIXLBD01).is_ok());
            assert!(parse_session(INDEPENDENT_MIXLSE01).is_ok());
            let paths=decode_path_packet_v1(INDEPENDENT_MIXPTH01,&r.policy).unwrap();
            assert_eq!(paths,[b"source".as_slice(),b"build",b"session",b"rows-\xff",b"snapshot-\xfe"]);
            let vectors=independent_binary_vectors_v1();assert_eq!(vectors.len(),51);
            let mut strict=0;
            for (id,kind,bytes,owner_only,diagnostic) in vectors {
                if kind==2 {assert!(decode_path_packet_v1(&bytes,&r.policy).is_err(),"{}",id);continue;}
                let err=if kind==0 {parse_build(&bytes).err()} else {parse_session(&bytes).err()};
                if owner_only {
                    assert!(err.is_none(),"{} old parser must remain positive",id);
                    // Same absolute frozen replacement at the same session byte
                    // offset, applied to actual proof-valid acquisition bodies.
                    let selected=root();let trace=Rc::new(Trace::default());let mut acquired=acquired(&selected,&trace);
                    let actual=acquired.actual.as_mut().unwrap();
                    let f=match &mut actual.partial.slots[2] {ActualInputSlotV1::Owned(v)=>v,_=>panic!()};
                    let (at,n)=if id=="session-zero-source-extent" {(32,0)}
                        else if id=="session-nonregular-identity" {(536,0o040600)}
                        else {let i=id.rsplit('-').next().unwrap().parse::<usize>().unwrap();(72+i*8,0)};
                    f.body.as_mut().unwrap().bytes[at..at+8].copy_from_slice(&(n as u64).to_le_bytes());
                    assert!(parse_session(f.body.as_ref().unwrap().slice_v1()).is_ok());
                    let held=match complete_admission_core_v1(acquired,TrustedLocalLauncherCustodyV1 {_private:()},&mut bridge(&trace)) {
                        OwnedAdmissionCoreOutcomeV1::Refused(v)=>v,_=>panic!("{} owner accepted invalid input",id)};
                    let original=held.actual.as_ref().unwrap().partial.original.as_ref().unwrap();
                    assert_eq!(original.kind,BootstrapFailureV1::Record,"{}",id);
                    assert!(trace.drops.borrow().is_empty());assert_eq!(selected.usage.get().storage,1_000_000);
                    drop(held);assert_eq!(trace.drops.borrow().len(),13);assert_eq!(selected.usage.get().storage,1_000_000);
                    strict+=1;continue;
                }
                let err=err.unwrap_or_else(||panic!("{} accepted",id));
                let expected=diagnostic.split('/').collect::<Vec<_>>();
                assert_eq!(format!("{:?}",err.kind),expected[0],"{}",id);
                assert_eq!(format!("{:?}",err.role),expected[1],"{}",id);
                let offset=if expected[2]=="current cursor" {
                    let index=id.rsplit('-').next().unwrap().parse::<usize>().unwrap();
                    let base=if kind==0 {INDEPENDENT_MIXLBD01}else{INDEPENDENT_MIXLSE01};
                    let start=if kind==0 {48}else{40};512+(0..index).map(|i|word(base,start+i*8)).sum::<u64>()
                }else{expected[2].parse::<u64>().unwrap()};
                assert_eq!(err.offset,offset,"{}",id);assert_eq!(err.attempts,0,"{}",id);
            }
            assert_eq!(strict,7);
            eprintln!("INDEPENDENT_BINARY51 exact_frozen_bytes=51 strict_owner_mapped=7 original_parser_positives_preserved=true");
        }
        fn independent_mutate_provenance_v1(p:&mut LoaderProvenanceV1,g:usize,a:usize,b:usize,delta:u64) {
            match g {
                0=>p.source[a]^=delta as u8,1=>p.manifest[a]^=delta as u8,2=>p.build[a]^=delta as u8,
                3=>p.session[a]^=delta as u8,4=>p.executable[a]^=delta as u8,5=>p.nonce[a]^=delta as u8,
                6=>match a {0=>p.validation_budget.source_bytes^=delta as usize,1=>p.validation_budget.metadata_bytes^=delta as usize,
                    2=>p.validation_budget.scratch_bytes^=delta as usize,3=>p.validation_budget.work_credits^=delta,4=>p.validation_budget.deadline_ms^=delta,_=>panic!()},
                7=>p.source_extent^=delta,
                8=>{let f=&mut p.identities[a];match b {0=>f.dev^=delta,1=>f.inode^=delta,2=>f.bytes^=delta,3=>f.mode^=delta,
                    4=>f.mtime=((f.mtime as u64)^delta) as i64,5=>f.mtime_ns=((f.mtime_ns as u64)^delta) as i64,
                    6=>f.ctime=((f.ctime as u64)^delta) as i64,7=>f.ctime_ns=((f.ctime_ns as u64)^delta) as i64,_=>panic!()}},_=>panic!()
            }
        }
        #[test]
        fn independent_i02_all_230_frozen_provenance_deltas_actual_proof_v1() {
            let vectors=independent_provenance_vectors_v1();assert_eq!(vectors.len(),230);
            for optional in [false,true] { for &(id,group,a,b,delta) in &vectors {
                let r=root();let trace=Rc::new(Trace::default());let mut owner=admitted(&r,&trace);
                let usage=independent_usage_v1();
                if !optional && id=="correlation-source-byte-00" {
                    let encoded=test_provenance_encoding_v1(&owner.expected);
                    let hex=encoded.iter().map(|b|format!("{:02x}",b)).collect::<String>();
                    eprintln!("INDEPENDENT_ACTUAL_PROVENANCE_BASELINE496 {}",hex);
                }
                // Admission already prepaid ingress. Later exhaustion must not
                // renew it or borrow cleanup funds to preserve originals.
                owner.owned.reservation.operation_left=0;owner.owned.reservation.storage_left=0;
                let (original,held,pointer)={let(expected,attempt)=owner.correlation_scope_core_v1().unwrap();
                    let mut supplied=carrier(&owner.expected,&trace);supplied.usage=usage;
                    if !optional {drop(supplied.executable.take());}
                    let selected=supplied.selected.as_mut().unwrap();let pointer=selected.proof.source().as_ptr();
                    independent_mutate_provenance_v1(&mut selected.provenance,group,a,b,delta);
                    let (original,held)=match correlate_core_v1(attempt,supplied,&expected) {Err(v)=>v,Ok(_)=>panic!("{} accepted",id)};
                    (original,held,pointer)};
                assert_eq!(original.kind,BootstrapFailureV1::Correlation(group),"{}",id);
                assert_eq!(refusal(owner.correlation_scope_core_v1()),BootstrapFailureV1::AlreadyAttempted);
                let retained=independent_retained_v1(owner,&trace);
                assert_eq!(*trace.drops.borrow(),if optional {vec![]}else{vec![23]});
                assert_eq!(held.usage,usage);assert_eq!(held.files.each_ref().map(|v|v.tag),[20,21,22]);
                assert_eq!(held.executable.as_ref().map(|v|v.tag),if optional {Some(23)}else{None});
                drop(retained);
                let proof=&held.selected.as_ref().unwrap().proof;assert_eq!(proof.source().as_ptr(),pointer);assert_eq!(proof.source().len(),1947);
                let before=r.usage.get();assert_eq!(before.storage,1_000_000);drop(held);assert_eq!(r.usage.get(),before);
                assert_eq!(trace.drops.borrow().len(),17);
                assert_eq!(refusal(r.reserve_before_any_input_effect_v1(ReviewedAcquisitionQuoteV1 {acquisition_work:1,cleanup_work:1,peak_storage:1})),BootstrapFailureV1::AlreadyReserved);
            }}
            eprintln!("INDEPENDENT_PROVENANCE230 vectors=230 optional_shapes=2 actual_cases=460 proof_pointer_and_all_usage_preserved=true issued_charge_permanent=true");
        }
        struct IndependentScheduleBridgeV1 { inner:TestBridge,responses:Vec<i64>,at:usize,bytes:usize,
            marker_drops:std::sync::Arc<std::sync::atomic::AtomicUsize> }
        impl InputBridgeV1<Guard> for IndependentScheduleBridgeV1 {
            fn metadata_v1(&mut self,p:PaidOperationV1<'_>,r:&mut Guard,s:usize)->Result<FileIdentityV1,OriginalAcquisitionFailureV1>{self.inner.metadata_v1(p,r,s)}
            fn offset_v1(&mut self,p:PaidOperationV1<'_>,r:&mut Guard,s:usize)->Result<u64,OriginalAcquisitionFailureV1>{self.inner.offset_v1(p,r,s)}
            fn allocate_v1(&mut self,p:PaidOperationV1<'_>,n:usize,b:u64,s:usize)->Result<ImmutableOwnedBytesV1,OriginalAcquisitionFailureV1>{self.inner.allocate_v1(p,n,b,s)}
            fn hash_v1(&mut self,p:PaidOperationV1<'_>,b:&[u8],s:usize)->Result<[u8;32],OriginalAcquisitionFailureV1>{self.inner.hash_v1(p,b,s)}
            fn retire_v1(&mut self,p:PaidOperationV1<'_>,r:Guard,s:usize)->Result<(),(Guard,OriginalAcquisitionFailureV1)>{self.inner.retire_v1(p,r,s)}
            fn read_v1(&mut self,_p:PaidOperationV1<'_>,r:&mut Guard,out:&mut[u8])->io::Result<usize> {
                let response=*self.responses.get(self.at).expect("read beyond exact frozen schedule");self.at+=1;
                if response==-1 {return Err(io::Error::from(io::ErrorKind::Interrupted));}
                if response==-2 {return Err(io::Error::new(io::ErrorKind::Other,OriginalIoMarkerV1 {id:0x7712,drops:self.marker_drops.clone()}));}
                let n=response as usize;
                if n<=out.len() {out[..n].fill(0x71);r.position+=n;self.bytes+=n;}Ok(n)
            }
        }
        #[test]
        fn independent_i03_all_12_frozen_read_schedules_actual_core_v1() {
            let vectors=independent_read_vectors_v1();assert_eq!(vectors.len(),12);
            for (id,extent,calls,bytes,responses,outcome) in vectors {
                let r=root();let trace=Rc::new(Trace::default());let mut paid=paid(&r);
                let resource=guard(77,vec![0;extent],&trace);let initial=resource.identity;
                let mut owned=RetainedIdentityFileV1 {role:0,resource,initial,body:None,sha256:None};
                let drops=std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
                let mut b=IndependentScheduleBridgeV1 {inner:bridge(&trace),responses,at:0,bytes:0,marker_drops:drops.clone()};
                let old=r.usage.get();let result=read_owned_body_once_v1(&mut paid,&mut owned,extent,&mut b);
                assert_eq!(b.at,calls,"{}",id);assert_eq!(b.bytes,bytes,"{}",id);
                let body=owned.body.as_ref().unwrap();assert_eq!(body.bytes.len(),extent);
                let expected_initialized=if outcome==5 {extent}else{bytes};assert_eq!(body.initialized,expected_initialized,"{}",id);
                assert_eq!(body.allocation_bound,extent as u64+26);assert_eq!(trace.storage_at_allocation.get(),old.storage);
                match outcome {
                    0=>{assert!(result.is_ok(),"{}",id);assert_eq!(body.initialized,extent);assert!(owned.sha256.is_some());},
                    n=>{let e=match result {Err(v)=>v,Ok(())=>panic!("{} accepted",id)};
                        assert_eq!(e.kind,match n {1=>BootstrapFailureV1::Attempts,2=>BootstrapFailureV1::Io,3=>BootstrapFailureV1::ShortInput,4=>BootstrapFailureV1::OverreportedRead,5=>BootstrapFailureV1::ExtraInput,_=>panic!()},"{}",id);
                        if n==2 {let marker=e.io.as_ref().unwrap().get_ref().unwrap().downcast_ref::<OriginalIoMarkerV1>().unwrap();assert_eq!(marker.id,0x7712);assert_eq!(drops.load(std::sync::atomic::Ordering::SeqCst),0);}
                        assert!(owned.sha256.is_none());drop(e);
                    }
                }
                let before_retry=(b.at,paid.operation_left,paid.storage_left);
                assert_eq!(match read_owned_body_once_v1(&mut paid,&mut owned,extent,&mut b) {Err(v)=>v.kind,_=>panic!()},BootstrapFailureV1::AlreadyAttempted);
                assert_eq!((b.at,paid.operation_left,paid.storage_left),before_retry);
                assert!(trace.drops.borrow().is_empty());drop(owned);drop(paid);assert_eq!(*trace.drops.borrow(),vec![77]);assert_eq!(r.usage.get(),old);
                if outcome==2 {assert_eq!(drops.load(std::sync::atomic::Ordering::SeqCst),1);}
            }
            eprintln!("INDEPENDENT_READ12 exact_response_queues=12 no33rd_read=true original_io_and_partial_allocation_retained=true no_retry=true");
        }
        // This helper uses ONLY the production-visible opaque File facade API.
        // It is compiled but never called: no File or native fixture is created.
        // The result type lacks the input's root lifetime and can be returned
        // after consuming its owner. No private expected/result fields needed.
        #[allow(dead_code)]
        fn independent_facade_result_escape_signature_v1<'root>(owner:AdmittedImmutableOwnerV1<'root>,supplied:SuppliedLoaderCarrierV1)->OwnedCorrelationOutcomeV1 {
            let result={let(expected,attempt)=owner.correlation_scope_v1().unwrap();correlate_admitted_loader_v1(attempt,supplied,&expected)};
            retire_admitted_owner_v1(owner);result
        }
        #[test]
        fn independent_i04_result_outlives_original_owner_and_ledger_v1() {
            let trace=Rc::new(Trace::default());
            let (held,pointer,charged_at_ledger_end)={let r=root();let owner=admitted(&r,&trace);
                let (held,pointer)={let(expected,attempt)=owner.correlation_scope_core_v1().unwrap();let c=carrier(&owner.expected,&trace);
                    let pointer=c.selected.as_ref().unwrap().proof.source().as_ptr();let held=match correlate_core_v1(attempt,c,&expected) {Ok(v)=>v,Err(_)=>panic!()};(held,pointer)};
                let retained=independent_retained_v1(owner,&trace);drop(retained);
                assert_eq!(*trace.drops.borrow(),(0..13).collect::<Vec<_>>());
                let charge=r.usage.get();assert_eq!(charge.storage,1_000_000);(held,pointer,charge)};
            // The originating ledger has ended; carrier remains accessible.
            assert_eq!(held.selected.as_ref().unwrap().proof.source().as_ptr(),pointer);
            assert_eq!(held.selected.as_ref().unwrap().proof.source().len(),1947);
            assert_eq!(held.files.each_ref().map(|v|v.tag),[20,21,22]);assert_eq!(held.executable.as_ref().unwrap().tag,23);
            assert_eq!(charged_at_ledger_end.storage,1_000_000);drop(held);assert_eq!(trace.drops.borrow().len(),17);
            eprintln!("INDEPENDENT_ROOT_LIFETIME carrier_accessible_after_ledger_end=true last_live_ledger_charge={} Complete_or_refund=false full_root_charge_lifetime_established=false",charged_at_ledger_end.storage);
        }
        #[test]
        fn independent_i05_unissued_immediate_token_release_drop_and_no_renewal_v1() {
            for release in [false,true] {let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);
                let before=r.usage.get();let token=match retire_acquired_owner_core_v1(owner.owned,&mut bridge(&trace)) {
                    AcquisitionRetirementOutcomeV1::Complete(v)=>v,_=>panic!("unissued positive control")};
                assert_eq!(*trace.drops.borrow(),(0..13).collect::<Vec<_>>());assert_eq!(r.usage.get(),before);
                if release {token.release_v1();}else{drop(token);}
                let after=r.usage.get();assert_eq!(after.work,before.work);assert_eq!(after.peak,before.peak);
                assert_eq!(after.storage,if release {0}else{before.storage});
                assert_eq!(refusal(r.reserve_before_any_input_effect_v1(ReviewedAcquisitionQuoteV1 {acquisition_work:1,cleanup_work:1,peak_storage:1})),BootstrapFailureV1::AlreadyReserved);
                assert_eq!(r.usage.get(),after);
            }
        }
        #[test]
        fn independent_i06_issued_barrier_preempts_failing_or_panicking_bridge_v1() {
            for fail in 0..13 {for panic in [false,true] {let r=root();let trace=Rc::new(Trace::default());let owner=admitted(&r,&trace);
                {let(_expected,_attempt)=owner.correlation_scope_core_v1().unwrap();}
                let mut b=bridge(&trace);if panic {b.unwind_retirement=Some(fail);}else{b.fail_retirement=Some(fail);}
                let before=r.usage.get();let cleanup=owner.owned.reservation.cleanup_left;
                let retained=match retire_acquired_owner_core_v1(owner.owned,&mut b) {AcquisitionRetirementOutcomeV1::Retained(v)=>v,_=>panic!()};
                assert_eq!(retained.reservation.cleanup_left,cleanup);assert!(!retained.retirement_started);assert!(trace.drops.borrow().is_empty());
                let retained=match retire_acquired_owner_core_v1(retained,&mut b) {AcquisitionRetirementOutcomeV1::Retained(v)=>v,_=>panic!()};
                assert_eq!(retained.reservation.cleanup_left,cleanup);assert!(trace.drops.borrow().is_empty());drop(retained);assert_eq!(r.usage.get(),before);
            }}
        }

    }

    // OWNER_PROBE_INSERTION
}
pub(super) use prepaid_input_owner_v1::{
    AdmittedImmutableOwnerV1, AdmittedLoaderCorrespondenceV1, PrepaidCorrelationAttemptV1,
    BootstrapFailureV1, BootstrapLedgerV1, BorrowedOwnerDataV1, SuppliedLoaderCarrierV1, CorrelatedSelectedProfileV1,
    OriginalCorrelationRefusalV1, OwnedCorrelationOutcomeV1, selected_bootstrap_ledger_v1,
    correlate_admitted_loader_v1, retire_admitted_owner_v1,
};
