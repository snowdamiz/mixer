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
