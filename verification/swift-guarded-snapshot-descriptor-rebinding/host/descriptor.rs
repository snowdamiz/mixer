#![allow(dead_code)]
mod descriptor_harness {
use std::io;
// Only the unrelated validator error's name is stubbed for this pure parser
// harness. No validator, proof, loader ingress, VM or writer is linked/run.
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
mod platform {
    use super::*;
    use std::ffi::c_void;
    #[link(name="System")] unsafe extern "C" {
        fn CC_SHA256(data:*const c_void,len:u32,md:*mut u8)->*mut u8;
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

}

fn checked_descriptor(build:&[u8],usage:&mut LoaderUsageV1)->Result<(),LoaderFailureV1>{
    let b=parse_build(build)?;
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

    Ok(())
}
// Pure harness controls. The parser, identity/digest checks and CommonCrypto
// wrapper preceding this file are copied verbatim from the selected loader.
// No source validation, process observation, retained File ingress or writer.
fn put(b:&mut [u8], offset:usize, value:u64) {
    b[offset..offset+8].copy_from_slice(&value.to_le_bytes());
}
fn pack(values:&[&[u8]])->Vec<u8>{
    let mut out=(values.len() as u64).to_le_bytes().to_vec();
    for value in values {
        out.extend_from_slice(&(value.len() as u64).to_le_bytes());
        out.extend_from_slice(value);
    }
    out
}
fn rebuild(golden:&[u8],parts:&[Vec<u8>;4])->Vec<u8>{
    let mut out=golden[..512].to_vec();
    let mut usage=LoaderUsageV1::default();
    put(&mut out,24,(512+parts.iter().map(Vec::len).sum::<usize>()) as u64);
    for (i,part) in parts.iter().enumerate(){
        put(&mut out,48+8*i,part.len() as u64);
        out[152+32*i..184+32*i].copy_from_slice(&platform::hash(part,&mut usage).unwrap());
    }
    for part in parts {out.extend_from_slice(part);}
    out
}
fn expect(label:&str,input:&[u8],kind:Refusal,cases:&mut usize){
    let err=checked_descriptor(input,&mut LoaderUsageV1::default()).expect_err(label);
    assert_eq!(err.kind,kind,"{label}");
    *cases+=1;
}
pub(super) fn main(){
    let args:Vec<_>=std::env::args_os().collect();
    assert_eq!(args.len(),3);
    let golden=std::fs::read(&args[1]).unwrap();
    let selected=parse_build(&golden).unwrap();
    assert_eq!(word(&golden,32),145);
    assert_eq!(word(&golden,40),11);
    let variant=args[2].to_str().unwrap();
    if variant!="bound" {
        let expected=match variant {
            "missing"|"malformed"=>Refusal::UnsupportedBuild,
            "stale"=>Refusal::BuildIdentity,
            _=>panic!("unknown negative variant"),
        };
        let mut cases=0;
        expect("private compiled identity refusal",&golden,expected,&mut cases);
        println!("identity_negative={variant} actual={expected:?} cases={cases}");
        return;
    }
    let mut cases=0;
    let mut usage=LoaderUsageV1::default();
    checked_descriptor(&golden,&mut usage).unwrap(); cases+=1;
    let parts:[Vec<u8>;4]=std::array::from_fn(|i|selected.sections[i].bytes.to_vec());
    for count in [0,144,146,u64::MAX]{
        let mut b=golden.clone();put(&mut b,32,count);
        expect("exact source cardinality",&b,Refusal::BuildIdentity,&mut cases);
    }
    for count in [0,10,12,u64::MAX]{
        let mut b=golden.clone();put(&mut b,40,count);
        expect("exact unchanged support cardinality",&b,Refusal::BuildIdentity,&mut cases);
    }
    for count in [0,67108865]{
        let mut b=golden.clone();put(&mut b,80,count);
        expect("output extent bound",&b,Refusal::BuildIdentity,&mut cases);
    }
    for at in [88,108,344]{
        let mut b=golden.clone();b[at]^=1;
        expect("target and reserved bytes",&b,Refusal::Reserved,&mut cases);
    }
    let mut b=golden.clone();b.push(0);let n=b.len();put(&mut b,24,n as u64);
    expect("trailing section bytes",&b,Refusal::Extent,&mut cases);
    for at in [0,8,16,24]{
        let mut b=golden.clone();b[at]^=1;
        expect("fixed header identity",&b,Refusal::Header,&mut cases);
    }
    let mut changed=parts.clone();changed[0].clear();
    expect("nonempty manifest",&rebuild(&golden,&changed),Refusal::Extent,&mut cases);
    let mut changed=parts.clone();changed[0]=vec![b'x';65537];
    expect("manifest section cap",&rebuild(&golden,&changed),Refusal::Extent,&mut cases);
    for argv in [pack(&[]),pack(&[b"a\0"]),{let mut p=pack(&[b"valid"]);p.push(0);p}]{
        let mut changed=parts.clone();changed[1]=argv;
        expect("counted argv grammar",&rebuild(&golden,&changed),Refusal::ProcessEncoding,&mut cases);
    }
    for env in [pack(&[b"Z=x",b"A=y"]),pack(&[b"A=x",b"A=y"]),pack(&[b"MIXER_LOADER_MANIFEST_SHA256=x"])]{
        let mut changed=parts.clone();changed[2]=env;
        expect("environment ordering duplicate identity injection",&rebuild(&golden,&changed),Refusal::ProcessEncoding,&mut cases);
    }
    let mut b=golden.clone();b[512]^=1;
    expect("manifest bytes rehashed independently",&b,Refusal::Digest,&mut cases);
    let mut changed=parts.clone();
    let at=changed[0].windows(10).position(|p|p==b"\"sha256\":\"").unwrap()+10;
    changed[0][at]=if changed[0][at]==b'0'{b'1'}else{b'0'};
    expect("same145 same11 altered valid JSON source hash with rebound header",&rebuild(&golden,&changed),Refusal::BuildIdentity,&mut cases);
    for (index,newpart) in [(1,pack(&[b"different compiler command"])),(2,pack(&[b"A=different compile environment"])),(3,b"different compiler version\n".to_vec())]{
        let mut changed=parts.clone();changed[index]=newpart;
        expect("fresh header cannot replace independently compiled commitment",&rebuild(&golden,&changed),Refusal::BuildIdentity,&mut cases);
    }
    let mut b=golden.clone();b[280]^=1;
    expect("compiler executable commitment",&b,Refusal::BuildIdentity,&mut cases);
    // These two positives deliberately expose this boundary's limitation:
    // actual executable/session/source checks live later in the real loader.
    let mut b=golden.clone();b[312]^=1;
    checked_descriptor(&b,&mut LoaderUsageV1::default()).unwrap();cases+=1;
    let mut b=golden.clone();put(&mut b,80,1);
    checked_descriptor(&b,&mut LoaderUsageV1::default()).unwrap();cases+=1;
    let mut b=golden.clone();put(&mut b,48,u64::MAX);
    expect("section checked conversion and extent",&b,Refusal::Extent,&mut cases);
    let mut changed=parts.clone();changed[2]=pack(&[]);
    expect("valid empty compile environment remains identity bound",&rebuild(&golden,&changed),Refusal::BuildIdentity,&mut cases);
    assert!(parse_hex(&[b'A';64]).is_none());cases+=1;
    assert!(parse_hex(&[b'0';63]).is_none());cases+=1;
    assert_eq!(parse_hex(&[b'0';64]),Some([0;32]));cases+=1;
    assert_eq!(usage.hash_bytes,parts.iter().map(|p|p.len() as u64).sum::<u64>());cases+=1;
    assert_eq!(cases,41);
    println!("descriptor_controls={cases} source145_host11=true actual_loader_ingress=false engine_VM_writer=false");
}

}
fn main(){descriptor_harness::main();}
