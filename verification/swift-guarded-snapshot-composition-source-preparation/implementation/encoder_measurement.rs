// Root-released append-only private measurement seam. No behavior calls.
#[cfg(mixer_snapshot_composition_layout)]
#[used]
static MIXER_COMPOSITION_ENCODER_HELPER_LAYOUTS_V1:[usize;108]=[
 std::mem::size_of::<[u64;11]>(),std::mem::align_of::<[u64;11]>(), // [u64;11]
 std::mem::size_of::<&mut[u8;576]>(),std::mem::align_of::<&mut[u8;576]>(), // &mut[u8;576]
 std::mem::size_of::<&mut[u8;512]>(),std::mem::align_of::<&mut[u8;512]>(), // &mut[u8;512]
 std::mem::size_of::<&[u64]>(),std::mem::align_of::<&[u64]>(), // &[u64]
 std::mem::size_of::<&mut[u8]>(),std::mem::align_of::<&mut[u8]>(), // &mut[u8]
 std::mem::size_of::<Result<&mut[u8;576],std::array::TryFromSliceError>>(),std::mem::align_of::<Result<&mut[u8;576],std::array::TryFromSliceError>>(), // Result<&mut[u8;576],std::array::TryFromSliceError>
 std::mem::size_of::<Result<&mut[u8;512],std::array::TryFromSliceError>>(),std::mem::align_of::<Result<&mut[u8;512],std::array::TryFromSliceError>>(), // Result<&mut[u8;512],std::array::TryFromSliceError>
 std::mem::size_of::<Result<[u8;8],std::array::TryFromSliceError>>(),std::mem::align_of::<Result<[u8;8],std::array::TryFromSliceError>>(), // Result<[u8;8],std::array::TryFromSliceError>
 std::mem::size_of::<std::ops::Range<usize>>(),std::mem::align_of::<std::ops::Range<usize>>(), // std::ops::Range<usize>
 std::mem::size_of::<Option<usize>>(),std::mem::align_of::<Option<usize>>(), // Option<usize>
 std::mem::size_of::<Result<usize,std::num::TryFromIntError>>(),std::mem::align_of::<Result<usize,std::num::TryFromIntError>>(), // Result<usize,std::num::TryFromIntError>
 std::mem::size_of::<Option<&metadata::Signature>>(),std::mem::align_of::<Option<&metadata::Signature>>(), // Option<&metadata::Signature>
 std::mem::size_of::<Option<&Type>>(),std::mem::align_of::<Option<&Type>>(), // Option<&Type>
 std::mem::size_of::<Option<&metadata::Import>>(),std::mem::align_of::<Option<&metadata::Import>>(), // Option<&metadata::Import>
 std::mem::size_of::<Option<&metadata::Function>>(),std::mem::align_of::<Option<&metadata::Function>>(), // Option<&metadata::Function>
 std::mem::size_of::<Option<&metadata::Global>>(),std::mem::align_of::<Option<&metadata::Global>>(), // Option<&metadata::Global>
 std::mem::size_of::<Option<&metadata::Export>>(),std::mem::align_of::<Option<&metadata::Export>>(), // Option<&metadata::Export>
 std::mem::size_of::<Option<&metadata::Segment>>(),std::mem::align_of::<Option<&metadata::Segment>>(), // Option<&metadata::Segment>
 std::mem::size_of::<(usize,&u64)>(),std::mem::align_of::<(usize,&u64)>(), // (usize,&u64)
 std::mem::size_of::<(usize,&WasiFunction)>(),std::mem::align_of::<(usize,&WasiFunction)>(), // (usize,&WasiFunction)
 std::mem::size_of::<usize>(),std::mem::align_of::<usize>(), // usize
 std::mem::size_of::<u64>(),std::mem::align_of::<u64>(), // u64
 std::mem::size_of::<u32>(),std::mem::align_of::<u32>(), // u32
 std::mem::size_of::<bool>(),std::mem::align_of::<bool>(), // bool
 std::mem::size_of::<(u32,u32)>(),std::mem::align_of::<(u32,u32)>(), // (u32,u32)
 std::mem::size_of::<Option<(u32,u32)>>(),std::mem::align_of::<Option<(u32,u32)>>(), // Option<(u32,u32)>
 std::mem::size_of::<Result<(u32,u32),SnapshotEncodeErrorV2>>(),std::mem::align_of::<Result<(u32,u32),SnapshotEncodeErrorV2>>(), // Result<(u32,u32),SnapshotEncodeErrorV2>
 std::mem::size_of::<Result<&metadata::Signature,SnapshotEncodeErrorV2>>(),std::mem::align_of::<Result<&metadata::Signature,SnapshotEncodeErrorV2>>(), // Result<&metadata::Signature,SnapshotEncodeErrorV2>
 std::mem::size_of::<Result<&Type,SnapshotEncodeErrorV2>>(),std::mem::align_of::<Result<&Type,SnapshotEncodeErrorV2>>(), // Result<&Type,SnapshotEncodeErrorV2>
 std::mem::size_of::<Result<&metadata::Import,SnapshotEncodeErrorV2>>(),std::mem::align_of::<Result<&metadata::Import,SnapshotEncodeErrorV2>>(), // Result<&metadata::Import,SnapshotEncodeErrorV2>
 std::mem::size_of::<Result<&metadata::Function,SnapshotEncodeErrorV2>>(),std::mem::align_of::<Result<&metadata::Function,SnapshotEncodeErrorV2>>(), // Result<&metadata::Function,SnapshotEncodeErrorV2>
 std::mem::size_of::<Result<&metadata::Global,SnapshotEncodeErrorV2>>(),std::mem::align_of::<Result<&metadata::Global,SnapshotEncodeErrorV2>>(), // Result<&metadata::Global,SnapshotEncodeErrorV2>
 std::mem::size_of::<Result<&metadata::Export,SnapshotEncodeErrorV2>>(),std::mem::align_of::<Result<&metadata::Export,SnapshotEncodeErrorV2>>(), // Result<&metadata::Export,SnapshotEncodeErrorV2>
 std::mem::size_of::<Result<&metadata::Segment,SnapshotEncodeErrorV2>>(),std::mem::align_of::<Result<&metadata::Segment,SnapshotEncodeErrorV2>>(), // Result<&metadata::Segment,SnapshotEncodeErrorV2>
 std::mem::size_of::<Option<u64>>(),std::mem::align_of::<Option<u64>>(), // Option<u64>
 std::mem::size_of::<Option<&u64>>(),std::mem::align_of::<Option<&u64>>(), // Option<&u64>
 std::mem::size_of::<Option<u32>>(),std::mem::align_of::<Option<u32>>(), // Option<u32>
 std::mem::size_of::<Resource>(),std::mem::align_of::<Resource>(), // Resource
 std::mem::size_of::<std::array::IntoIter<u64,8>>(),std::mem::align_of::<std::array::IntoIter<u64,8>>(), // std::array::IntoIter<u64,8>
 std::mem::size_of::<std::iter::Enumerate<std::array::IntoIter<u64,8>>>(),std::mem::align_of::<std::iter::Enumerate<std::array::IntoIter<u64,8>>>(), // std::iter::Enumerate<std::array::IntoIter<u64,8>>
 std::mem::size_of::<(usize,u64)>(),std::mem::align_of::<(usize,u64)>(), // (usize,u64)
 std::mem::size_of::<&crate::experimental_swift_reactor::InitialProfileBorrowV1>(),std::mem::align_of::<&crate::experimental_swift_reactor::InitialProfileBorrowV1>(), // &crate::experimental_swift_reactor::InitialProfileBorrowV1
 std::mem::size_of::<&ValidatedSwiftReactor>(),std::mem::align_of::<&ValidatedSwiftReactor>(), // &ValidatedSwiftReactor
 std::mem::size_of::<&LoaderProvenanceV1>(),std::mem::align_of::<&LoaderProvenanceV1>(), // &LoaderProvenanceV1
 std::mem::size_of::<&SwiftMetadata>(),std::mem::align_of::<&SwiftMetadata>(), // &SwiftMetadata
 std::mem::size_of::<&[u8;4096]>(),std::mem::align_of::<&[u8;4096]>(), // &[u8;4096]
 std::mem::size_of::<&mut[u8;4096]>(),std::mem::align_of::<&mut[u8;4096]>(), // &mut[u8;4096]
 std::mem::size_of::<Type>(),std::mem::align_of::<Type>(), // Type
 std::mem::size_of::<Option<Type>>(),std::mem::align_of::<Option<Type>>(), // Option<Type>
 std::mem::size_of::<WasiFunction>(),std::mem::align_of::<WasiFunction>(), // WasiFunction
 std::mem::size_of::<crate::experimental_wasi::WasiBudget>(),std::mem::align_of::<crate::experimental_wasi::WasiBudget>(), // crate::experimental_wasi::WasiBudget
 std::mem::size_of::<crate::experimental_wasi::WasiGrants>(),std::mem::align_of::<crate::experimental_wasi::WasiGrants>(), // crate::experimental_wasi::WasiGrants
 std::mem::size_of::<(crate::experimental_wasi::WasiBudget,crate::experimental_wasi::WasiGrants)>(),std::mem::align_of::<(crate::experimental_wasi::WasiBudget,crate::experimental_wasi::WasiGrants)>(), // (crate::experimental_wasi::WasiBudget,crate::experimental_wasi::WasiGrants)
 std::mem::size_of::<(usize,&[u8;32])>(),std::mem::align_of::<(usize,&[u8;32])>(), // (usize,&[u8;32])
];

// Exact-expression closure shape definitions; never evaluate the closures.
#[cfg(mixer_snapshot_composition_layout)]
impl SpanCheckV2 {
 const fn composer_measure_span_capture_v1(&self)->(usize,usize){
  let c=|end:usize| end <= self.source;
  (std::mem::size_of_val(&c),std::mem::align_of_val(&c))
 }
}
#[cfg(mixer_snapshot_composition_layout)]
const fn composer_measure_parameter_span_capture_v1(view:&SnapshotViewV2<'_>)->(usize,usize){
  let m=&view.proof.metadata;
  let c=|n:usize| n <= m.parameters.len();
  (std::mem::size_of_val(&c),std::mem::align_of_val(&c))
 }
#[cfg(mixer_snapshot_composition_layout)]
#[used]
static COMPOSITION_PARAMETER_CAPTURE_MEASURER_V1:fn(&SnapshotViewV2<'_>)->(usize,usize)=composer_measure_parameter_span_capture_v1;
#[cfg(mixer_snapshot_composition_layout)]
#[used]
static MIXER_COMPOSITION_ENCODER_CAPTURE_LAYOUTS_V1:[usize;50]=[
 {let c=|_:std::num::TryFromIntError| SnapshotEncodeErrorV2::Arithmetic;(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let c=|_:std::num::TryFromIntError| SnapshotEncodeErrorV2::Arithmetic;(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // word-conversion
 SpanCheckV2 {source:0,section:0,index:0}.composer_measure_span_capture_v1().0,SpanCheckV2 {source:0,section:0,index:0}.composer_measure_span_capture_v1().1, // span-end
 {let c=|_:()| SnapshotEncodeErrorV2::Arithmetic;(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let c=|_:()| SnapshotEncodeErrorV2::Arithmetic;(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // provenance-map-error
 {let c=|| field(2, 0, 0);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let c=|| field(2, 0, 0);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // memory-absent
 {let c=|| field(3, 0, 0);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let c=|| field(3, 0, 0);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // table-absent
 {let c=|_:()| SnapshotEncodeErrorV2::Arithmetic;(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let c=|_:()| SnapshotEncodeErrorV2::Arithmetic;(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // runtime-map-error
 {let c=|n:usize| n <= 80000;(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let c=|n:usize| n <= 80000;(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // function-total
 {let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // entry-signatures
 {let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // entry-parameters
 {let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // entry-imports
 {let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // entry-functions
 {let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // entry-globals
 {let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // entry-exports
 {let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // entry-data
 {let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let sid=0usize;let index=0usize;let c=|| field(16, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // entry-elements
 {let sid=0usize;let index=0usize;let c=|| field(21, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let sid=0usize;let index=0usize;let c=|| field(21, sid, index);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // record-word-result
 {let c=|| field(28, 0, 0);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let c=|| field(28, 0, 0);(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // directory-absent
 {let c=|_:std::num::TryFromIntError| SnapshotEncodeErrorV2::Arithmetic;(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let c=|_:std::num::TryFromIntError| SnapshotEncodeErrorV2::Arithmetic;(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // source-copy-count
 {let c=|_:std::num::TryFromIntError| SnapshotEncodeErrorV2::Arithmetic;(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let c=|_:std::num::TryFromIntError| SnapshotEncodeErrorV2::Arithmetic;(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // source-offset
 {let c=|_:std::num::TryFromIntError| SnapshotEncodeErrorV2::Arithmetic;(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let c=|_:std::num::TryFromIntError| SnapshotEncodeErrorV2::Arithmetic;(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // metadata-index
 {let c=|n:usize| u64::try_from(n).map_err(|_|());(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let c=|n:usize| u64::try_from(n).map_err(|_|());(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // runtime-convert
 {let c=|_:std::num::TryFromIntError| ();(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let c=|_:std::num::TryFromIntError| ();(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // runtime-inner-convert
 {let c=|_:std::num::TryFromIntError| ();(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let c=|_:std::num::TryFromIntError| ();(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // provenance-source-convert
 {let c=|_:std::num::TryFromIntError| ();(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let c=|_:std::num::TryFromIntError| ();(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // provenance-metadata-convert
 {let c=|_:std::num::TryFromIntError| ();(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.0,{let c=|_:std::num::TryFromIntError| ();(std::mem::size_of_val(&c),std::mem::align_of_val(&c))}.1, // provenance-scratch-convert
];
#[cfg(mixer_snapshot_composition_layout)]
const fn composer_checked_capture_static_sum_v1()->Option<usize>{
 let mut i=0usize;let mut sum=0usize;
 while i<MIXER_COMPOSITION_ENCODER_CAPTURE_LAYOUTS_V1.len(){
  sum=match sum.checked_add(MIXER_COMPOSITION_ENCODER_CAPTURE_LAYOUTS_V1[i]){Some(n)=>n,None=>return None};
  i+=2;
 }Some(sum)
}
#[cfg(mixer_snapshot_composition_layout)]
#[used]
static MIXER_COMPOSITION_CAPTURE_PARTIAL_SUM_V1:[usize;2]=match composer_checked_capture_static_sum_v1(){Some(n)=>[1,n],None=>[0,0]};
// This checked sum covers only the25 statically evaluable exact occurrences.
// The separately compiler-measured parameter-range capture still joins the
// occurrence roster; neither number is a source/phase/foundation floor.
