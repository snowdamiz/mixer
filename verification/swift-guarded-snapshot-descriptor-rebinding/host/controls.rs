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
