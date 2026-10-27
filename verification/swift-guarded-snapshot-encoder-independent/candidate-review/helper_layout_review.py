import json,re,shutil,sys
import run_review as r
ROWS=['[u64;11]','&mut[u8;576]','&mut[u8;512]','&[u64]','&mut[u8]',
'Result<&mut[u8;576],std::array::TryFromSliceError>','Result<&mut[u8;512],std::array::TryFromSliceError>',
'Result<[u8;8],std::array::TryFromSliceError>','std::ops::Range<usize>','Option<usize>','Result<usize,std::num::TryFromIntError>',
'Option<&metadata::Signature>','Option<&Type>','Option<&metadata::Import>','Option<&metadata::Function>','Option<&metadata::Global>','Option<&metadata::Export>','Option<&metadata::Segment>',
'(usize,&u64)','(usize,&WasiFunction)','usize','u64','u32','bool','(u32,u32)','Option<(u32,u32)>','Result<(u32,u32),SnapshotEncodeErrorV2>',
'Result<&metadata::Signature,SnapshotEncodeErrorV2>','Result<&Type,SnapshotEncodeErrorV2>','Result<&metadata::Import,SnapshotEncodeErrorV2>','Result<&metadata::Function,SnapshotEncodeErrorV2>','Result<&metadata::Global,SnapshotEncodeErrorV2>','Result<&metadata::Export,SnapshotEncodeErrorV2>','Result<&metadata::Segment,SnapshotEncodeErrorV2>',
'Option<u64>','Option<&u64>','Option<u32>','Resource','std::array::IntoIter<u64,8>','std::iter::Enumerate<std::array::IntoIter<u64,8>>','(usize,u64)','&crate::experimental_swift_reactor::InitialProfileBorrowV1','&ValidatedSwiftReactor','&LoaderProvenanceV1','&SwiftMetadata','&[u8;4096]','&mut[u8;4096]']
ROWS+=['Type','Option<Type>','WasiFunction','crate::experimental_wasi::WasiBudget','crate::experimental_wasi::WasiGrants','(crate::experimental_wasi::WasiBudget,crate::experimental_wasi::WasiGrants)']
LOADER=['FileIdentityV1','std::iter::Enumerate<std::slice::Iter<\'static,FileIdentityV1>>','(usize,&FileIdentityV1)','(usize,&[u8;32])','&FileIdentityV1']
kind,mode=sys.argv[1:3]
suffix='-'+sys.argv[3]if len(sys.argv)>3 else''
path=r.HERE/'helper-work'/f'{kind}-{mode}';shutil.copytree(r.SOURCE,path)
def function(name,rows):
 return '\npub(crate)fn '+name+'(){\n'+''.join('println!("INDEPENDENT_HELPER\\t'+t.replace('"','\\"')+'\\t{}\\t{}",std::mem::size_of::<'+t+'>(),std::mem::align_of::<'+t+'>());\n'for t in rows)+'}\n'
p=path/'src/experimental/swift.rs';s=p.read_text();original=(r.CANDIDATE/'source/vm/src/experimental/swift.rs').read_text();assert s.startswith(original)
extra=function('independent_helper_shapes',ROWS)+'''\nconst _:()={
 let sid=0usize;let index=0usize;let c=||field(16,sid,index);assert!(std::mem::size_of_val(&c)==16);
 let source=0usize;let c=|end:usize|end<=source;assert!(std::mem::size_of_val(&c)==8);
 let c=|_:std::num::TryFromIntError|SnapshotEncodeErrorV2::Arithmetic;assert!(std::mem::size_of_val(&c)==0);
 let c=||field(2,0,0);assert!(std::mem::size_of_val(&c)==0);
};\n'''
p.write_text(original[:-3]+extra+'\n}\n'+s[len(original):])
p=path/'src/experimental_swift_reactor/retained_profile_loader_v1.rs';p.write_text(p.read_text()+function('independent_identity_shapes',LOADER))
p=path/'src/experimental_swift_reactor/cache/initial_profile_v1/tests.rs';s=p.read_text();needle='if action=="layouts"{';assert s.count(needle)==1;s=s.replace(needle,needle+'crate::experimental::swift::snapshot_encoder_v2::independent_helper_shapes();crate::experimental_swift_reactor::retained_profile_loader_v1::independent_identity_shapes();');p.write_text(s)
variant=r.manifest(path);binary=r.WORK/f'helper-{kind}-{mode}'
try:
 args=r.flags(mode)+(['--test']if kind=='unit'else['--crate-type','bin','--cfg','mixer_initial_profile_component_host','--cfg','mixer_snapshot_encoder_host'])+[path/'src/lib.rs','-o',binary]
 r.run(f'helper-{kind}-{mode}{suffix}-compile',args,r.env()|{'CARGO_MANIFEST_DIR':str(path)})
 args=[binary]+(['--exact',r.METHOD,'--nocapture','--test-threads=1']if kind=='unit'else[])
 text=r.run(f'helper-{kind}-{mode}{suffix}-measure',args,r.env()|{'MIXER_REVIEW_ACTION':'layouts'})
 rows=[{'name':' '.join(n.split()),'bytes':int(b),'alignment':int(a)}for n,b,a in re.findall(r'INDEPENDENT_HELPER\t(.*?)\t(\d+)\t(\d+)',text,re.S)]
 assert len(rows)==len(ROWS)+len(LOADER)
 r.save(r.HERE/'helper-layouts'/f'{kind}-{mode}{suffix}.json',{'rows':rows,'closure_shape_assertions':4,'source':variant,'compiler':r.desc(r.RUSTC),'binary':r.desc(binary),'scope':'independent supplementary source-place/helper shapes; no admitted simultaneous sum'})
finally:
 shutil.rmtree(path);binary.unlink(missing_ok=True)
