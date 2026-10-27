#![allow(dead_code)]
mod independent {
use std::io;
#[derive(Debug)] struct SwiftValidationFailure;
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
#[derive(Clone, Copy)]
struct Section<'a> {
    bytes: &'a [u8],
}
struct BuildView<'a> {
    sections: [Section<'a>; 4],
    output_bytes: u64,
    digests: [&'a [u8]; 6],
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
    if word(b, 32) != 145
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

mod platform {use super::*;use std::ffi::c_void;#[link(name="System")] unsafe extern "C" {fn CC_SHA256(data:*const c_void,len:u32,md:*mut u8)->*mut u8;}
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
}
fn checked(build:&[u8])->Result<(),LoaderFailureV1>{let b=parse_build(build)?;let usage=&mut LoaderUsageV1::default();
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
Ok(())}
fn put(b: &mut [u8], at: usize, n: u64) { b[at..at+8].copy_from_slice(&n.to_le_bytes()); }
fn packed(items: &[&[u8]]) -> Vec<u8> {
    let mut b = (items.len() as u64).to_le_bytes().to_vec();
    for p in items { b.extend_from_slice(&(p.len() as u64).to_le_bytes()); b.extend_from_slice(p); }
    b
}
fn rebuild(original: &[u8], parts: &[Vec<u8>; 4]) -> Vec<u8> {
    let mut b = original[..HEADER].to_vec();
    put(&mut b, 24, (HEADER + parts.iter().map(Vec::len).sum::<usize>()) as u64);
    for (i,p) in parts.iter().enumerate() {
        put(&mut b, 48+i*8, p.len() as u64);
        b[152+i*32..184+i*32].copy_from_slice(&platform::hash(p, &mut LoaderUsageV1::default()).unwrap());
    }
    for p in parts { b.extend_from_slice(p); }
    b
}
fn rejects(b: &[u8], refusal: Refusal) { assert_eq!(checked(b).unwrap_err().kind, refusal); }
pub(super) fn main() {
    let args: Vec<_> = std::env::args_os().collect();
    assert_eq!(args.len(), 3);
    let b = std::fs::read(&args[1]).unwrap();
    let mode = args[2].to_str().unwrap();
    if mode != "positive" {
        rejects(&b, if mode == "unsupported" {Refusal::UnsupportedBuild} else {Refusal::BuildIdentity});
        println!("independent_identity_refusal={mode}"); return;
    }
    checked(&b).unwrap();
    let view = parse_build(&b).unwrap();
    let parts: [Vec<u8>;4] = std::array::from_fn(|i|view.sections[i].bytes.to_vec());
    let mut n = 1usize;
    for (at, counts) in [(32, [0,144,146,u64::MAX]), (40,[0,10,12,u64::MAX])] {
        for value in counts { let mut x=b.clone(); put(&mut x,at,value); rejects(&x,Refusal::BuildIdentity); n+=1; }
    }
    for value in [0, SOURCE_CAP as u64+1] { let mut x=b.clone();put(&mut x,80,value);rejects(&x,Refusal::BuildIdentity);n+=1; }
    for at in [0,8,16,24] {let mut x=b.clone();x[at]^=1;rejects(&x,Refusal::Header);n+=1;}
    for at in [88,108,344,511] {let mut x=b.clone();x[at]^=1;rejects(&x,Refusal::Reserved);n+=1;}
    for value in [0,u64::MAX] {let mut x=b.clone();put(&mut x,48,value);rejects(&x,Refusal::Extent);n+=1;}
    for index in 0..5 {let mut x=b.clone();x[152+index*32]^=1;rejects(&x,Refusal::BuildIdentity);n+=1;}
    for index in 0..4 {
        let mut x=b.clone();let start=HEADER+parts[..index].iter().map(Vec::len).sum::<usize>();
        x[start]^=1;
        // Corrupting argv/environment framing is refused before digest checks.
        assert!(checked(&x).is_err()); n+=1;
    }
    for (index,value) in [(0,vec![b'x';65537]),(1,vec![b'x';16385]),(2,vec![b'x';16385]),(3,vec![b'x';16385])] {
        let mut p=parts.clone();p[index]=value;rejects(&rebuild(&b,&p),Refusal::Extent);n+=1;
    }
    for value in [packed(&[]),packed(&[b"a\0"]),packed(&[b""])] {
        let mut p=parts.clone();p[1]=value;rejects(&rebuild(&b,&p),Refusal::ProcessEncoding);n+=1;
    }
    for value in [packed(&[b"Z=z",b"A=a"]),packed(&[b"A=a",b"A=b"]),packed(&[b"=empty"]),packed(&[b"NO_EQUAL"]),packed(&[b"MIXER_LOADER_COMMAND_SHA256=x"])] {
        let mut p=parts.clone();p[2]=value;rejects(&rebuild(&b,&p),Refusal::ProcessEncoding);n+=1;
    }
    // Same 145/11 roster shape, valid JSON and fresh section hash cannot replace compiled manifest commitment.
    let mut p=parts.clone(); let needle=b"\"sha256\":\"";
    let at=p[0].windows(needle.len()).position(|v|v==needle).unwrap()+needle.len();
    p[0][at]=if p[0][at]==b'0'{b'1'}else{b'0'};
    rejects(&rebuild(&b,&p),Refusal::BuildIdentity);n+=1;
    for (index,value) in [(1,packed(&[b"changed-argv"])),(2,packed(&[b"A=changed"])),(3,b"changed-version".to_vec())] {
        let mut p=parts.clone();p[index]=value;rejects(&rebuild(&b,&p),Refusal::BuildIdentity);n+=1;
    }
    // Deliberate positive limitations: this extracted identity boundary does not authenticate actual output.
    let mut x=b.clone();x[312]^=1;checked(&x).unwrap();n+=1;
    let mut x=b.clone();put(&mut x,80,1);checked(&x).unwrap();n+=1;
    assert_eq!(parse_hex(&[b'0';64]),Some([0;32]));n+=1;
    for value in [vec![b'0';63],vec![b'0';65],vec![b'A';64],vec![b'G';64]] {assert!(parse_hex(&value).is_none());n+=1;}
    println!("independent_pure_controls={n} real_ingress=false type_layout=false writer=false");
}

}
fn main(){independent::main();}
