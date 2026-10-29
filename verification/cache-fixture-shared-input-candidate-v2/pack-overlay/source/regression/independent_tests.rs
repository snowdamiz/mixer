//! Independent test transport and vector encoder. Test allocations are not the analyzer inventory.
#![allow(dead_code)]
#[path = "../library/analyzer.rs"]
mod product;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Seek, SeekFrom};
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};

const M: u64 = u64::MAX;
const ROWS: usize = 80_000;
const REPORT: usize = 49_152;
static NEXT: AtomicU64 = AtomicU64::new(0);

fn put(bytes: &mut [u8], word: usize, value: u64) {
    bytes[word * 8..word * 8 + 8].copy_from_slice(&value.to_le_bytes());
}
fn get(bytes: &[u8], word: usize) -> u64 {
    u64::from_le_bytes(bytes[word * 8..word * 8 + 8].try_into().unwrap())
}
fn encode(words: &[u64]) -> Vec<u8> {
    words.iter().flat_map(|value| value.to_le_bytes()).collect()
}

#[derive(Clone)]
struct Fixture { stream: Vec<u8>, profile: Vec<u8>, context: Vec<u8> }
impl Fixture {
    fn new() -> Self {
        let mut context = vec![0; 8192];
        let values = [u64::from_le_bytes(*b"MIXFIX01"),1,8192,1,32,33,1000,3,2,3,1,100,1000,500,0,0];
        for (index, value) in values.into_iter().enumerate() { put(&mut context,index,value); }
        for digest in 0..8 { context[128 + digest*32..160 + digest*32].fill(17 + digest as u8); }
        let mut profile = vec![0; 512 + ROWS*32];
        let values = [u64::from_le_bytes(*b"MIXPRF01"),1,512,32,80000,1000,3,2,3,1,100,1000,500,0,0,0];
        for (index, value) in values.into_iter().enumerate() { put(&mut profile,index,value); }
        // Only baseline/candidate/event-schema have corresponding fixture context identities.
        profile[128..160].copy_from_slice(&context[320..352]);
        profile[160..192].copy_from_slice(&context[352..384]);
        profile[224..256].copy_from_slice(&context[160..192]);
        for row in 0..ROWS {
            let start = 512 + row*32;
            profile[start+4..start+8].copy_from_slice(&u32::MAX.to_le_bytes());
            profile[start+8..start+16].copy_from_slice(&M.to_le_bytes());
        }
        for (row, ty, offset, len) in [(40usize,2u32,10u64,20u64),(41,1,100,50)] {
            let start = 512 + row*32;
            profile[start..start+4].copy_from_slice(&1u32.to_le_bytes());
            profile[start+4..start+8].copy_from_slice(&ty.to_le_bytes());
            profile[start+8..start+16].copy_from_slice(&offset.to_le_bytes());
            profile[start+16..start+24].copy_from_slice(&len.to_le_bytes());
        }
        let mut header = vec![0;512];
        let values = [u64::from_le_bytes(*b"MIXORDR1"),1,512,128,512,32,80000,64,512,33];
        for (index, value) in values.into_iter().enumerate() { put(&mut header,index,value); }
        header[128..192].copy_from_slice(&context[128..192]);
        header[192..256].copy_from_slice(&context[320..384]);
        let mut records = Vec::new();
        for kind in 1..=13 {
            let mut w = [0,kind,0,1,kind*10,kind*2,40,10,20,2,M,M,0,0,0,0];
            match kind {
                1 => { w[7..10].fill(M); }
                2 => {}
                3 => { w[15]=40; }
                4 => { w[14]=M; w[15]=40; }
                5 => { w[13]=60; w[14]=100; w[15]=1000; }
                6..=8 => { w[10]=0; w[13]=60; }
                9|10 => { w[13]=60; }
                11 => { w[10]=0; w[11]=0; w[12]=1; w[13]=1; w[14]=60; w[15]=1; }
                12 => { w[3]=0; w[8]=M; w[10]=0; w[11]=0; w[12]=1; w[13]=60; }
                13 => { w[2]=5; w[3]=0; w[6..10].fill(M); w[13]=5; }
                _ => unreachable!(),
            }
            w[0]=kind;
            records.push(w);
        }
        let mut footer = vec![0;512];
        for (index,value) in [(0,u64::from_le_bytes(*b"MIXOEND1")),(1,1),(2,13),(3,13),(5,13),(6,130),(7,26),(8,1),(10,130),(11,26),(14,M),(15,33),(33,5),(34,2),(35,32)] {
            put(&mut footer,index,value);
        }
        footer[288..352].copy_from_slice(&context[128..192]);
        let mut stream=header;
        for record in records { stream.extend(encode(&record)); }
        stream.extend(footer);
        Self {stream, profile, context}
    }
    fn header(&mut self, word: usize, value: u64) { put(&mut self.stream[..512],word,value); }
    fn record(&mut self, record: usize, word: usize, value: u64) { let start=512+record*128; put(&mut self.stream[start..start+128],word,value); }
    fn footer(&mut self, word: usize, value: u64) { let start=self.stream.len()-512; put(&mut self.stream[start..],word,value); }
    fn context(&mut self, word: usize, value: u64) { put(&mut self.context,word,value); }
    fn profile_header(&mut self, word: usize, value: u64) { put(&mut self.profile[..512],word,value); }
    fn defined(&mut self, row: usize, defined: u32, ty: u32, offset: u64, len: u64, reserved: u64) {
        let start=512+row*32;
        self.profile[start..start+4].copy_from_slice(&defined.to_le_bytes());
        self.profile[start+4..start+8].copy_from_slice(&ty.to_le_bytes());
        self.profile[start+8..start+16].copy_from_slice(&offset.to_le_bytes());
        self.profile[start+16..start+24].copy_from_slice(&len.to_le_bytes());
        self.profile[start+24..start+32].copy_from_slice(&reserved.to_le_bytes());
    }
    fn phases_only(mask: u64) -> Self {
        let mut f=Self::new();
        f.context(5,mask);f.header(9,mask);
        let mut stream=f.stream[..512].to_vec();
        let mut count=0;
        for phase in 1..=5 {
            if mask&(1<<phase)==0 {continue;}
            count+=1;
            stream.extend(encode(&[count,13,phase,0,count*10,count*2,M,M,M,M,M,M,0,phase,0,0]));
        }
        let mut footer=f.stream[f.stream.len()-512..].to_vec();
        for (word,value) in [(2,count),(3,count),(5,count),(6,count*10),(7,count*2),(8,0),(10,count*10),(11,count*2),(15,mask)] {put(&mut footer,word,value);}
        stream.extend(footer);f.stream=stream;f
    }
}

fn scratch(label: &str) -> PathBuf {
    let root=PathBuf::from(std::env::var_os("MIXER_REVIEW_SCRATCH").expect("owned scratch required"));
    let path=root.join(format!("{}-{}",NEXT.fetch_add(1,Ordering::SeqCst),label));
    fs::create_dir(&path).unwrap(); path
}
fn open_inputs(f: &Fixture, path: &std::path::Path) -> (File,File,File,File) {
    for (name,bytes) in [("stream",&f.stream),("profile",&f.profile),("context",&f.context)] {fs::write(path.join(name),bytes).unwrap();}
    let output=OpenOptions::new().read(true).write(true).create_new(true).open(path.join("report")).unwrap();
    (File::open(path.join("stream")).unwrap(),File::open(path.join("profile")).unwrap(),File::open(path.join("context")).unwrap(),output)
}
fn check_report(bytes: &[u8], framing: bool) {
    assert_eq!(bytes.len(),REPORT,"physical report length");
    assert_eq!(&bytes[..8],b"MIXANL01");
    assert_eq!(get(bytes,1),1); assert_eq!(get(bytes,2),REPORT as u64);
    assert_eq!(get(bytes,4),0,"full replay acceptance withheld");
    assert_eq!(get(bytes,5),0,"semantic accepted coordinate withheld");
    for word in [8,11,12,13,16,17,18,19] {assert_eq!(get(bytes,word),0,"semantic header word {word}");}
    assert!(bytes[512..].iter().all(|byte| *byte==0),"all semantic report regions unavailable");
    if framing {assert_eq!(get(bytes,3),5,"well framed fixture is unavailable"); assert_eq!(get(bytes,10),7,"missing real binding");}
}
fn run(f: &Fixture, framing: bool, label: &str) {
    let path=scratch(label);
    let (mut stream,mut profile,mut context,mut output)=open_inputs(f,&path);
    let result=product::analyze_fixture(&mut stream,&mut profile,&mut context,&mut output);
    output.seek(SeekFrom::Start(0)).unwrap(); let mut report=Vec::new(); output.read_to_end(&mut report).unwrap();
    match &result {
        Ok(outcome)=>{assert!(!outcome.stored_prefix_validated());assert!(!outcome.full_replay_accepted());},
        Err(error)=>{assert_eq!(error.reserved,0);assert!(report.len()<=REPORT);if report.len()==REPORT {assert_eq!(get(&report,4),0);}},
    }
    if framing { assert!(result.is_ok(),"expected framing observation {label}"); check_report(&report,true); }
    else if result.is_ok() {check_report(&report,false); assert_eq!(get(&report,3),3,"malformed vector admitted: {label}");}
    drop((stream,profile,context,output));
    fs::remove_dir_all(&path).unwrap();
}

#[derive(Default)]
struct ContextPhaseTimes {
    prepare: std::time::Duration,
    analyze: std::time::Duration,
    report_assert: std::time::Duration,
    cleanup: std::time::Duration,
}

fn run_context_opened(
    files: (File, File, File, File), framing: bool, label: &str, path: &std::path::Path,
) -> ContextPhaseTimes {
    let (mut stream,mut profile,mut context,mut output)=files;
    let analyze_start=std::time::Instant::now();
    let result=product::analyze_fixture(&mut stream,&mut profile,&mut context,&mut output);
    let analyze=analyze_start.elapsed();
    let report_start=std::time::Instant::now();
    output.seek(SeekFrom::Start(0)).unwrap(); let mut report=Vec::new(); output.read_to_end(&mut report).unwrap();
    match &result {
        Ok(outcome)=>{assert!(!outcome.stored_prefix_validated());assert!(!outcome.full_replay_accepted());},
        Err(error)=>{assert_eq!(error.reserved,0);assert!(report.len()<=REPORT);if report.len()==REPORT {assert_eq!(get(&report,4),0);}},
    }
    if framing { assert!(result.is_ok(),"expected framing observation {label}"); check_report(&report,true); }
    else if result.is_ok() {check_report(&report,false); assert_eq!(get(&report,3),3,"malformed vector admitted: {label}");}
    let report_assert=report_start.elapsed();
    let cleanup_start=std::time::Instant::now();
    drop((stream,profile,context,output));
    fs::remove_dir_all(path).unwrap();
    ContextPhaseTimes { prepare: std::time::Duration::ZERO, analyze, report_assert, cleanup: cleanup_start.elapsed() }
}

fn assert_shared_context_inputs(shared: &std::path::Path, baseline: &Fixture) {
    for (name,expected) in [("stream",&baseline.stream),("profile",&baseline.profile)] {
        let path=shared.join(name);
        let metadata=fs::metadata(&path).unwrap();
        assert!(metadata.is_file());
        assert!(metadata.permissions().readonly());
        assert_eq!(&fs::read(&path).unwrap(),expected,"shared context input bytes changed: {name}");
    }
}

fn run_context_case(
    bytes: &[u8], shared: &std::path::Path, label: &str,
    completed: &mut usize, total: &mut ContextPhaseTimes, started: std::time::Instant,
) {
    let prepare_start=std::time::Instant::now();
    let path=scratch(label);
    fs::write(path.join("context"),bytes).unwrap();
    let mut stream=File::open(shared.join("stream")).unwrap();
    let mut profile=File::open(shared.join("profile")).unwrap();
    let mut context=File::open(path.join("context")).unwrap();
    let mut output=OpenOptions::new().read(true).write(true).create_new(true).open(path.join("report")).unwrap();
    for file in [&mut stream,&mut profile,&mut context,&mut output] {
        assert_eq!(file.stream_position().unwrap(),0,"fresh offset-zero handle required");
    }
    let prepare=prepare_start.elapsed();
    let phases=run_context_opened((stream,profile,context,output),false,label,&path);
    total.prepare+=prepare;total.analyze+=phases.analyze;
    total.report_assert+=phases.report_assert;total.cleanup+=phases.cleanup;
    *completed+=1;
    if *completed%64==0 || *completed==1003 {
        eprintln!("context_progress completed={}/1003 elapsed_ms={} prepare_ms={} analyze_ms={} report_assert_ms={} cleanup_ms={}",
            *completed,started.elapsed().as_millis(),total.prepare.as_millis(),total.analyze.as_millis(),
            total.report_assert.as_millis(),total.cleanup.as_millis());
    }
}

#[test]
fn independently_encoded_all_kind_baseline() { run(&Fixture::new(),true,"baseline"); }

#[test]
fn stream_header_every_closed_scalar_reserved_and_digest() {
    for (word,value) in [(0,0),(1,2),(2,511),(3,129),(4,513),(5,0),(5,4194305),(6,79999),(7,63),(8,511),(9,32),(9,64)] {
        let mut f=Fixture::new(); f.header(word,value); run(&f,false,&format!("header-{word}-{value}"));
    }
    for word in (10..16).chain(32..64) {let mut f=Fixture::new(); f.header(word,1); run(&f,false,&format!("header-reserved-{word}"));}
    for byte in [128usize,159,160,191,192,223,224,255] {let mut f=Fixture::new(); f.stream[byte]^=1; run(&f,false,&format!("header-digest-{byte}"));}
}

#[test]
fn footer_closed_scalar_reserved_flags_and_digest() {
    for (word,value) in [(0,0),(1,2),(2,14),(3,12),(4,1),(5,12),(6,129),(7,25),(8,0),(9,2),(9,3),(9,128),(9,256),(9,512),(10,129),(11,25),(12,22),(13,1),(14,0),(15,32),(15,64),(31,6),(32,1),(33,4),(33,6),(34,4194337),(35,31)] {
        let mut f=Fixture::new(); f.footer(word,value); run(&f,false,&format!("footer-{word}-{value}"));
    }
    for word in 44..64 {let mut f=Fixture::new(); f.footer(word,1); run(&f,false,&format!("footer-reserved-{word}"));}
    for byte in [288usize,319,320,351] {let mut f=Fixture::new(); let start=f.stream.len()-512; f.stream[start+byte]^=1; run(&f,false,&format!("footer-digest-{byte}"));}
}

#[test]
fn cap_and_terminal_scalar_forms_are_framing_only() {
    let mut f=Fixture::new(); f.context(4,13); f.header(5,13); f.footer(35,13); f.footer(9,1); f.footer(3,14); f.footer(4,1); run(&f,true,"cap");
    for (word,value) in [(2,12),(3,13),(4,0),(15,1),(33,4)] {let mut x=f.clone(); x.footer(word,value); run(&x,false,&format!("bad-cap-{word}"));}
    for (kind,code,stage) in [(1,1,1),(21,24,6)] {let mut x=Fixture::new(); x.footer(12,kind);x.footer(13,code);x.footer(14,stage);x.footer(32,1);run(&x,true,"failure-observation");}
    for (word,value) in [(12,22),(13,0),(13,25),(14,0),(14,7),(32,0)] {let mut x=Fixture::new();x.footer(12,1);x.footer(13,1);x.footer(14,1);x.footer(32,1);x.footer(word,value);run(&x,false,&format!("bad-terminal-{word}-{value}"));}
    // Final consuming ledger observations do not become semantic ledger claims.
    for word in 16..31 {let mut x=Fixture::new();x.footer(word,M);run(&x,true,&format!("opaque-ledger-{word}"));}
}

#[test]
fn coordinated_positive_scalar_boundaries_and_unavailable_getters() {
    for cap in [13u64,4194304] {let mut f=Fixture::new();f.context(4,cap);f.header(5,cap);f.footer(35,cap);run(&f,true,&format!("cap-positive-{cap}"));}
    for limit in [1u64,64] {
        let mut f=Fixture::new();f.context(8,limit);f.context(9,limit);f.profile_header(7,limit);f.profile_header(8,limit);run(&f,true,&format!("limits-positive-{limit}"));
    }
    let f=Fixture::new();let path=scratch("getter-boundary");
    let (mut stream,mut profile,mut context,mut output)=open_inputs(&f,&path);
    let result=product::analyze_fixture(&mut stream,&mut profile,&mut context,&mut output).expect("framing outcome");
    assert!(result.fixture_framing_observed());assert!(!result.stored_prefix_validated());assert!(!result.full_replay_accepted());
    assert_eq!(result.framed_records,13);assert_eq!(result.physical_records,13);assert_eq!(result.report_bytes,49152);
    assert!(result.steps_used<=268435456);assert!(result.input_attempts<=263584);assert!(result.output_attempts<=32);
    assert_eq!(result.input_bytes_read,(f.stream.len()+f.profile.len()+f.context.len()) as u64);
    drop((stream,profile,context,output));fs::remove_dir_all(path).unwrap();
}

#[test]
fn all_phase_masks_and_empty_scalar_domain_are_admitted_as_fixtures_only() {
    for middle in 0..16 {run(&Fixture::phases_only(33|(middle<<1)),true,&format!("phase-mask-{middle}"));}
    let mut f=Fixture::phases_only(33);
    f.defined(40,0,u32::MAX,M,0,0);f.defined(41,0,u32::MAX,M,0,0);
    for (context,profile) in [(6,5),(7,6),(11,10),(12,11),(13,12)] {f.context(context,0);f.profile_header(profile,0);}
    run(&f,true,"empty-domain");
    // A finite defined zero-length body exactly at the source extent is legal.
    f.context(7,1);f.profile_header(6,1);f.defined(79999,1,0,0,0,0);run(&f,true,"empty-defined-body");
    let mut f=Fixture::phases_only(33);f.context(7,u32::MAX as u64);f.profile_header(6,u32::MAX as u64);run(&f,true,"type-count-max32");
}

#[test]
fn context_schema_scalar_reserved_and_lengths() {
    let started=std::time::Instant::now();
    let baseline=Fixture::new();
    let shared=scratch("context-shared-inputs");
    for (name,bytes) in [("stream",&baseline.stream),("profile",&baseline.profile)] {
        let path=shared.join(name);
        fs::write(&path,bytes).unwrap();
        let mut permissions=fs::metadata(&path).unwrap().permissions();
        permissions.set_readonly(true);
        fs::set_permissions(&path,permissions).unwrap();
    }
    assert_shared_context_inputs(&shared,&baseline);
    let mut completed=0usize;
    let mut total=ContextPhaseTimes::default();
    for (word,value) in [(1,2),(2,8191),(3,0),(3,2),(4,0),(4,4194305),(5,32),(5,64),(6,M),(7,0),(7,4294967296),(8,0),(8,65),(9,0),(9,65),(10,0),(10,2),(11,M),(12,99),(13,0),(13,1001),(14,1),(15,1)] {
        let mut context=baseline.context.clone();put(&mut context,word,value);run_context_case(&context,&shared,&format!("context-{word}-{value}"),&mut completed,&mut total,started);
    }
    for word in 48..1024 {let mut context=baseline.context.clone();put(&mut context,word,1);run_context_case(&context,&shared,&format!("context-reserved-{word}"),&mut completed,&mut total,started);}
    for len in [0usize,1,8191,8193] {let mut context=baseline.context.clone();context.resize(len,0);run_context_case(&context,&shared,&format!("context-length-{len}"),&mut completed,&mut total,started);}
    assert_eq!(completed,1003,"complete ordered context vector coverage");
    assert_shared_context_inputs(&shared,&baseline);
    fs::remove_dir_all(&shared).unwrap();
}

#[test]
fn profile_schema_reserved_digest_and_row_boundaries() {
    for (word,value) in [(0,0),(1,2),(2,511),(3,31),(4,79999),(5,999),(6,2),(7,1),(8,2),(9,2),(10,99),(11,999),(12,499),(13,1),(14,1),(15,1)] {
        let mut f=Fixture::new();f.profile_header(word,value);run(&f,false,&format!("profile-header-{word}-{value}"));
    }
    for word in 48..64 {let mut f=Fixture::new();f.profile_header(word,1);run(&f,false,&format!("profile-reserved-{word}"));}
    for byte in [128usize,159,160,191,224,255] {let mut f=Fixture::new();f.profile[byte]^=1;run(&f,false,&format!("profile-digest-{byte}"));}
    for (def,ty,off,len,res) in [(2,0,0,0,0),(0,0,M,0,0),(0,u32::MAX,0,0,0),(0,u32::MAX,M,1,0),(0,u32::MAX,M,0,1),(1,3,0,1,0),(1,0,M,0,0),(1,0,999,2,0),(1,0,M-1,4,0),(1,0,0,M,0),(1,0,0,0,1)] {
        let mut f=Fixture::new();f.defined(79999,def,ty,off,len,res);run(&f,false,&format!("profile-row-{def}-{ty}-{off}-{len}-{res}"));
    }
    for len in [0usize,511,512,2560511,2560513] {let mut f=Fixture::new();f.profile.resize(len,0);run(&f,false,&format!("profile-length-{len}"));}
}

#[test]
fn record_all_kind_unused_payloads_and_selected_limits() {
    let cases: &[(usize,usize,u64)] = &[
        (0,3,0),(0,6,80000),(0,7,0),(0,8,0),(0,9,0),(0,10,0),(0,11,0),(0,12,1),(0,13,1),(0,14,1),(0,15,1),
        (1,3,0),(1,7,11),(1,8,21),(1,9,1),(1,10,0),(1,11,0),(1,12,1),(1,13,2),(1,14,1),(1,15,1),
        (2,10,0),(2,11,0),(2,12,1),(2,13,1),(2,14,1),(2,15,41),
        (3,10,0),(3,11,0),(3,12,1),(3,13,3),(3,14,40),(3,15,41),
        (4,10,0),(4,11,0),(4,12,1),(4,13,0),(4,13,501),(4,14,99),(4,15,999),
        (5,10,2),(5,11,0),(5,12,1),(5,13,0),(5,14,1),(5,15,1),
        (6,10,2),(6,11,0),(6,12,1),(6,13,0),(6,14,1),(6,15,1),
        (7,10,2),(7,11,0),(7,12,1),(7,13,0),(7,14,1),(7,15,1),
        (8,10,0),(8,11,0),(8,12,1),(8,13,0),(8,14,1),(8,15,1),
        (9,10,0),(9,11,0),(9,12,1),(9,13,0),(9,14,1),(9,15,1),
        (10,10,2),(10,11,3),(10,12,0),(10,13,2),(10,14,0),(10,15,0),(10,15,4),
        (11,3,1),(11,6,80000),(11,7,11),(11,8,20),(11,9,1),(11,10,2),(11,11,3),(11,12,0),(11,13,0),(11,14,1),(11,15,3),
        (12,3,1),(12,6,40),(12,7,0),(12,8,0),(12,9,0),(12,10,0),(12,11,0),(12,12,1),(12,13,4),(12,14,1),(12,15,1),
    ];
    for &(record,word,value) in cases {let mut f=Fixture::new();f.record(record,word,value);run(&f,false,&format!("record-{record}-{word}-{value}"));}
    for (record,word,value) in [(0,0,0),(0,0,2),(1,1,0),(1,1,15),(1,2,6),(1,4,0),(1,5,0),(1,6,41),(1,6,80000),(1,7,M),(1,8,M),(1,9,M)] {let mut f=Fixture::new();f.record(record,word,value);run(&f,false,&format!("record-common-{record}-{word}-{value}"));}
}

#[test]
fn failure_record_closed_payload_and_bounds() {
    let mut f=Fixture::new();
    // Replace the ordinary BuildBegin with Failure; source applicability and FSM are deliberately not claimed.
    for (word,value) in [(1,14),(6,M),(7,M),(8,M),(9,M),(13,1),(14,1),(15,1)] {f.record(8,word,value);}
    run(&f,true,"failure-record");
    for (word,value) in [(6,80000),(7,0),(8,0),(9,0),(10,0),(11,0),(12,1),(13,0),(13,22),(14,0),(14,25),(15,0),(15,7)] {let mut x=f.clone();x.record(8,word,value);run(&x,false,&format!("failure-record-{word}-{value}"));}
}

#[test]
fn exact_stream_length_and_coordinates() {
    for len in [0usize,1,511,512,1023,1024,2687,2689] {let mut f=Fixture::new();f.stream.resize(len,0);run(&f,false,&format!("stream-length-{len}"));}
    for cut in [512usize,640,1024,2176] {let mut f=Fixture::new();f.stream.remove(cut);run(&f,false,&format!("stream-missing-byte-{cut}"));}
    let mut f=Fixture::new();f.record(5,4,49);run(&f,false,"decreasing-work");
    let mut f=Fixture::new();f.record(5,5,9);run(&f,false,"decreasing-instructions");
}

#[test]
fn oversized_sparse_stream_is_refused_before_reading_the_envelope() {
    let f=Fixture::new();let path=scratch("oversized-stream");let (stream,mut profile,mut context,mut output)=open_inputs(&f,&path);drop(stream);
    let stream=OpenOptions::new().write(true).open(path.join("stream")).unwrap();stream.set_len(536871937).unwrap();drop(stream);
    let mut stream=File::open(path.join("stream")).unwrap();
    let result=product::analyze_fixture(&mut stream,&mut profile,&mut context,&mut output);
    if let Ok(outcome)=result {
        assert!(!outcome.fixture_framing_observed(),"oversized stream framing observed");
        output.seek(SeekFrom::Start(0)).unwrap();let mut report=Vec::new();output.read_to_end(&mut report).unwrap();
        check_report(&report,false);assert_eq!(get(&report,3),3);
    }
    assert_eq!(stream.stream_position().unwrap(),0,"oversized stream bytes read");
    drop((stream,profile,context,output));fs::remove_dir_all(path).unwrap();
}

#[test]
fn report_source_digest_echoes_are_observations() {
    let f=Fixture::new();let path=scratch("digest-echoes");
    let (mut stream,mut profile,mut context,mut output)=open_inputs(&f,&path);
    assert!(product::analyze_fixture(&mut stream,&mut profile,&mut context,&mut output).is_ok());
    output.seek(SeekFrom::Start(0)).unwrap();let mut report=Vec::new();output.read_to_end(&mut report).unwrap();
    assert_eq!(&report[256..512],&f.context[128..384]);
    drop((stream,profile,context,output));fs::remove_dir_all(path).unwrap();
}

#[test]
fn output_alias_stale_length_and_cursor_fail_before_mutation() {
    for input in ["stream","profile","context"] {
        let f=Fixture::new();let path=scratch("alias");let (mut stream,mut profile,mut context,output)=open_inputs(&f,&path);drop(output);
        let mut output=OpenOptions::new().write(true).open(path.join(input)).unwrap();
        let result=product::analyze_fixture(&mut stream,&mut profile,&mut context,&mut output);
        assert!(result.is_err(),"output alias accepted: {input}");
        assert_eq!(fs::read(path.join("stream")).unwrap(),f.stream);assert_eq!(fs::read(path.join("profile")).unwrap(),f.profile);assert_eq!(fs::read(path.join("context")).unwrap(),f.context);
        drop((stream,profile,context,output));fs::remove_dir_all(path).unwrap();
    }
    for (length,position) in [(1u64,0u64),(49153,0),(0,1)] {
        let f=Fixture::new();let path=scratch("output-freshness");let (mut stream,mut profile,mut context,mut output)=open_inputs(&f,&path);
        output.set_len(length).unwrap();output.seek(SeekFrom::Start(position)).unwrap();
        assert!(product::analyze_fixture(&mut stream,&mut profile,&mut context,&mut output).is_err(),"stale output accepted {length}/{position}");
        assert_eq!(output.metadata().unwrap().len(),length);
        drop((stream,profile,context,output));fs::remove_dir_all(path).unwrap();
    }
}

#[test]
fn output_clone_hardlink_and_input_aliases_refuse_without_input_mutation() {
    for mode in ["clone","hardlink","inputs"] {
        let f=Fixture::new();let path=scratch("alias-modes");let (mut stream,mut profile,mut context,mut output)=open_inputs(&f,&path);
        if mode=="clone" {output=stream.try_clone().unwrap();}
        if mode=="hardlink" {fs::hard_link(path.join("profile"),path.join("linked")).unwrap();output=OpenOptions::new().write(true).open(path.join("linked")).unwrap();}
        if mode=="inputs" {profile=stream.try_clone().unwrap();}
        assert!(product::analyze_fixture(&mut stream,&mut profile,&mut context,&mut output).is_err(),"alias mode accepted {mode}");
        assert_eq!(fs::read(path.join("stream")).unwrap(),f.stream);assert_eq!(fs::read(path.join("profile")).unwrap(),f.profile);assert_eq!(fs::read(path.join("context")).unwrap(),f.context);
        drop((stream,profile,context,output));fs::remove_dir_all(path).unwrap();
    }
}

#[test]
fn readonly_output_and_nonregular_descriptor_refuse() {
    let f=Fixture::new();let path=scratch("readonly-output");let (mut stream,mut profile,mut context,output)=open_inputs(&f,&path);drop(output);
    let mut output=File::open(path.join("report")).unwrap();
    assert!(product::analyze_fixture(&mut stream,&mut profile,&mut context,&mut output).is_err());assert_eq!(output.metadata().unwrap().len(),0);
    drop((stream,profile,context,output));fs::remove_dir_all(path).unwrap();
    let path=scratch("nonregular");let (stream,mut profile,mut context,mut output)=open_inputs(&f,&path);drop(stream);let mut stream=File::open(&path).unwrap();
    let outcome=product::analyze_fixture(&mut stream,&mut profile,&mut context,&mut output).unwrap();
    assert_eq!(outcome.decision,product::Decision::Invalid);assert!(!outcome.fixture_framing_observed());
    output.seek(SeekFrom::Start(0)).unwrap();let mut report=Vec::new();output.read_to_end(&mut report).unwrap();check_report(&report,false);
    drop((stream,profile,context,output));fs::remove_dir_all(path).unwrap();
}

#[test]
fn unknown_context_magic_refuses_real_binding_without_framing() {
    let mut f=Fixture::new();f.context(0,0);let path=scratch("unknown-binding");
    let (mut stream,mut profile,mut context,mut output)=open_inputs(&f,&path);
    let outcome=product::analyze_fixture(&mut stream,&mut profile,&mut context,&mut output).unwrap();
    assert_eq!(outcome.decision,product::Decision::Unavailable);assert!(!outcome.fixture_framing_observed());assert!(!outcome.stored_prefix_validated());assert!(!outcome.full_replay_accepted());
    drop((stream,profile,context,output));fs::remove_dir_all(path).unwrap();
}
