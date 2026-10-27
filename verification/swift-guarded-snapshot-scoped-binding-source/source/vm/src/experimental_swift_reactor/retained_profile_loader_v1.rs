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
