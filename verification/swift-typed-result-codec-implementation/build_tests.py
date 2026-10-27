from pathlib import Path
H=Path(__file__).resolve().parent; ROOT=H.parents[1]
proposal=(ROOT/'verification/swift-retained-profile-real-binding-preparation/typed_wire_proposal.rs').read_text()
review=(ROOT/'verification/swift-retained-profile-real-binding-contract-review/codec_controls.rs').read_text()
original=proposal[proposal.index('    fn usage()->SwiftRunUsage'):].rsplit('\n}',1)[0]
ledger=proposal[proposal.index('fn ledger('):proposal.index('\n#[cfg(test)] mod tests')]
helpers='''//! Actual imported-type tests. Proposal and independent controls are ported here.
use super::*;
fn bytes<const N: usize>(words: &[u64]) -> [u8; N] { let mut out=[0;N]; write_words(&mut out, words); out }
fn encode_usage(u: &SwiftRunUsage) -> Result<[u8;512],Refusal> { let mut out=[0;512]; encode_usage_v1(u,&mut out)?; Ok(out) }
fn decode_usage(raw: &[u8;512]) -> Result<SwiftRunUsage,Refusal> { decode_usage_v1(raw) }
fn encode_failure_meta(f: &SwiftRunFailure) -> Result<[u8;256],Refusal> { let mut out=[0;256]; encode_failure_scalar_v1(f,&mut out)?; Ok(out) }
fn decode_failure_meta(raw: &[u8;256]) -> Result<UnverifiedFailureScalarsV1<'_>,Refusal> { decode_failure_scalar_v1(raw) }
'''
# Change original snapshot test into actual complete result integration, rather than ad hoc slicing.
start=original.index('    #[test]fn original_snapshots_and_final_consumption_stay_distinct()')
end=original.index('    #[test]fn absent_wasi_tail_and_presence_refuse()',start)
original=original[:start]+'''    #[test]fn original_snapshots_and_final_consumption_stay_distinct(){
        let mut f=failure(); let mut after=f.after_cleanup.unwrap();
        after.reservations.construction.current=331496; after.reservations.live_tickets=1;
        f.after_cleanup=Some(after); let mut final_u=after; final_u.elapsed_micros+=1;
        final_u.reservations.construction.current=0;final_u.reservations.live_tickets=0;
        let zero=[0;32]; let refs=references(0,0,&zero,&zero);
        let mut raw=[0;2048]; encode_result_v1(ResultObservationV1{failure:Some(&f),final_consuming:Some(&final_u),references:refs},&mut raw).unwrap();
        let d=decode_result_v1(&raw).unwrap();
        assert_eq!(d.at_failure(),Some(&f.at_failure));assert_eq!(d.after_cleanup(),Some(&after));assert_eq!(d.final_consuming(),Some(&final_u));
        assert_ne!(ledger(&after),ledger(&final_u));
    }
''' +original[end:]
ind=review[review.index('#[cfg(test)]'):]
start=ind.index('    fn check(raw: &[u8])')
end=ind.index('    #[test]', start)
ind=ind[:start]+'''    fn check(raw: &[u8]) -> Result<(), Refusal> { decode_result_v1(raw).map(|_|()) }

'''+ind[end:]
start=ind.index('    fn record(mask: u64, constructor: u64)')
end=ind.index('    fn check(',start)
ind=ind[:start]+'''    fn record(mask: u64, constructor: u64) -> [u8;2048] {
        let zero=[0;32]; let opaque=[23;32]; let raw_digest=[11;32]; let session=[13;32]; let schema=[17;32]; let writer=[19;32];
        let refs=UnverifiedResultReferencesV1 {raw_original_bytes:17,constructor_tag:constructor,
            constructor_bytes:if constructor==0{0}else{65536},raw_original_digest:&raw_digest,
            constructor_digest:if constructor==0{&zero}else{&opaque},session_digest:&session,
            typed_result_schema_digest:&schema,writer_digest:&writer};
        let mut f=failure(); if mask&2==0 {f.after_cleanup=None;}
        let final_u=usage(109); let mut out=[0;2048];
        encode_result_v1(ResultObservationV1{failure:if mask&1==0{None}else{Some(&f)},
            final_consuming:if mask&4==0{None}else{Some(&final_u)},references:refs},&mut out).unwrap();
        let d=decode_result_v1(&out).unwrap(); assert_eq!(d.encoded(),&out);
        assert_eq!(d.references(),&refs);
        assert_eq!(d.at_failure(),if mask&1==0{None}else{Some(&f.at_failure)});
        assert_eq!(d.after_cleanup(),if mask&2==0{None}else{f.after_cleanup.as_ref()});
        assert_eq!(d.final_consuming(),if mask&4==0{None}else{Some(&final_u)});
        if let Some(s)=d.failure_scalars() {
            assert_eq!((s.stage,s.kind,s.code()),(f.stage,f.kind,f.code));
            assert_eq!((s.function,s.offset,s.resource),(f.function,f.offset,f.resource));
            assert_eq!((s.attempted,s.limit,s.observed_capacity),(f.attempted,f.limit,f.observed_capacity));
            assert_eq!((s.deadline_origin,s.wasi_failure,s.guest_exit),(f.deadline_origin,f.wasi_failure,f.guest_exit));
            assert_eq!(s.code().as_ptr(),out[384..].as_ptr());
        } else { assert_eq!(mask&1,0); }
        out
    }
'''+ind[end:]
extra='''
fn references<'a>(tag:u64, len:u64, zero:&'a [u8;32], opaque:&'a [u8;32]) -> UnverifiedResultReferencesV1<'a> {
    UnverifiedResultReferencesV1{raw_original_bytes:0,constructor_tag:tag,constructor_bytes:len,
        raw_original_digest:zero,constructor_digest:if tag==0{zero}else{opaque},
        session_digest:zero,typed_result_schema_digest:zero,writer_digest:zero}
}
#[test]
fn every_wrong_extent_refuses_without_writing() {
    let f=failure(); let u=usage(); let zero=[0;32];
    let observation=ResultObservationV1{failure:Some(&f),final_consuming:Some(&u),references:references(0,0,&zero,&zero)};
    for n in 0..=2049 {
        let mut out=[0xa5;2049]; let before=out;
        if n!=2048 {assert_eq!(encode_result_v1(observation,&mut out[..n]),Err(CodecRefusalV1::Extent));assert_eq!(out,before);}
        if n!=512 {assert_eq!(encode_usage_v1(&u,&mut out[..n]),Err(CodecRefusalV1::Extent));assert_eq!(out,before);}
        if n!=256 {assert_eq!(encode_failure_scalar_v1(&f,&mut out[..n]),Err(CodecRefusalV1::Extent));assert_eq!(out,before);}
        let input=[0;2049];
        if n!=2048 {assert_eq!(decode_result_v1(&input[..n]).unwrap_err(),CodecRefusalV1::Extent);}
        if n!=512 {assert_eq!(decode_usage_v1(&input[..n]),Err(CodecRefusalV1::Extent));}
        if n!=256 {assert_eq!(decode_failure_scalar_v1(&input[..n]),Err(CodecRefusalV1::Extent));}
    }
}
#[test]
fn full_and_scalar_refusal_preserves_caller_bytes_and_originals() {
    let zero=[0;32]; let opaque=[77;32]; let u=usage();
    for code in ["","bad\\ncode","bad\\0code","\\u{7f}","é", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"] {
        let mut f=failure();f.code=code;let original=f;
        let mut scalar=[0xa5;256];let mut output=[0x3c;2048];
        assert!(encode_failure_scalar_v1(&f,&mut scalar).is_err());assert_eq!(scalar,[0xa5;256]);
        assert!(encode_result_v1(ResultObservationV1{failure:Some(&f),final_consuming:Some(&u),references:references(1,1,&zero,&opaque)},&mut output).is_err());
        assert_eq!(output,[0x3c;2048]);assert_eq!(f,original);
    }
    for (tag,len,digest) in [(0,1,&zero),(0,0,&opaque),(1,0,&zero),(1,65537,&zero),(8,u64::MAX,&opaque),(9,1,&opaque),(u64::MAX,1,&opaque)] {
        let f=failure();let original=f;let mut output=[0x7e;2048];
        let mut refs=references(tag,len,&zero,&opaque);refs.constructor_digest=digest;
        assert!(encode_result_v1(ResultObservationV1{failure:Some(&f),final_consuming:Some(&u),references:refs},&mut output).is_err());
        assert_eq!(output,[0x7e;2048]);assert_eq!(f,original);
    }
}
#[test]
fn raw_zero_length_and_arbitrary_digests_are_required_unverified_data() {
    for len in [0,1,u64::MAX] { for digest in [[0;32],[255;32],[0x42;32]] { for tag in 0..=8 {
        let zero=[0;32]; let mut refs=references(tag,if tag==0{0}else{1},&zero,&digest);
        refs.raw_original_bytes=len;refs.raw_original_digest=&digest;refs.session_digest=&digest;
        refs.typed_result_schema_digest=&digest;refs.writer_digest=&digest;
        let mut raw=[0x55;2048]; encode_result_v1(ResultObservationV1{failure:None,final_consuming:None,references:refs},&mut raw).unwrap();
        let d=decode_result_v1(&raw).unwrap();assert_eq!(d.references(),&refs);assert!(d.failure_scalars().is_none());
    }}}
}
#[test]
fn full_header_magic_version_length_and_form_are_exact() {
    let zero=[0;32];let mut good=[0;2048];
    encode_result_v1(ResultObservationV1{failure:None,final_consuming:None,references:references(0,0,&zero,&zero)},&mut good).unwrap();
    for i in 0..8 {let mut bad=good;bad[i]^=1;assert!(decode_result_v1(&bad).is_err());}
    for (word,valid) in [(1,1u64),(2,2048),(3,1)] {for value in [0,valid+1,u64::MAX]{
        let mut bad=good;bad[word*8..word*8+8].copy_from_slice(&value.to_le_bytes());assert!(decode_result_v1(&bad).is_err());
    }}
}
#[test]
fn decoded_view_borrows_input_without_fabricating_static_failure() {
    let mut f=failure();f.code="unknown printable code";let zero=[0;32];let mut raw=[0;2048];
    encode_result_v1(ResultObservationV1{failure:Some(&f),final_consuming:None,references:references(0,0,&zero,&zero)},&mut raw).unwrap();
    let d=decode_result_v1(&raw).unwrap();assert_eq!(d.encoded().as_ptr(),raw.as_ptr());
    assert_eq!(d.failure_scalars().unwrap().code().as_ptr(),raw[384..].as_ptr());
    assert_eq!(d.references().raw_original_digest.as_ptr(),raw[64..].as_ptr());assert_eq!(f.code,"unknown printable code");
}
#[test]
fn codec_data_layouts_are_reported_separately_from_owner_inventory() {
    macro_rules! show {($($t:ty),* $(,)?)=>{$(println!("CODEC_DATA\\t{}\\t{}\\t{}",stringify!($t),std::mem::size_of::<$t>(),std::mem::align_of::<$t>());)*};}
    show!(CodecRefusalV1, UnverifiedFailureScalarsV1<'static>, UnverifiedResultReferencesV1<'static>, ResultObservationV1<'static>, UnverifiedResultViewV1<'static>, [u64;64], Option<[u64;64]>, [u64;16], Option<[u64;16]>, [u8;512], [u8;256], [u8;2048]);
}
'''
(H/'source/vm/src/experimental_swift_reactor/diagnostic_result_v1_tests.rs').write_text(helpers+ledger+original+'\n'+ind+'\n'+extra)
print('21 ported plus 6 fresh actual-module methods written')
