import shutil
import run_review as r
path=r.HERE/'capture-work';shutil.copytree(r.SOURCE,path)
p=path/'src/experimental/swift.rs';s=p.read_text();original=(r.CANDIDATE/'source/vm/src/experimental/swift.rs').read_text();assert s.startswith(original)
source='''\nconst _:()={
 let sid=0usize;let index=0usize;let c=||field(16,sid,index);assert!(std::mem::size_of_val(&c)==16);assert!(std::mem::align_of_val(&c)==8);
 let source=0usize;let c=|end:usize|end<=source;assert!(std::mem::size_of_val(&c)==8);assert!(std::mem::align_of_val(&c)==8);
 let c=|_:std::num::TryFromIntError|SnapshotEncodeErrorV2::Arithmetic;assert!(std::mem::size_of_val(&c)==0);assert!(std::mem::align_of_val(&c)==1);
 let c=||field(2,0,0);assert!(std::mem::size_of_val(&c)==0);assert!(std::mem::align_of_val(&c)==1);
};\n'''
p.write_text(original[:-3]+source+'\n}\n'+s[len(original):])
manifest=r.manifest(path);profiles=[]
try:
 for kind,mode in[('host','debug'),('host','optimized'),('unit','debug'),('unit','optimized')]:
  args=r.flags(mode)+(['--test']if kind=='unit'else['--crate-type','rlib'])+['--emit=metadata',path/'src/lib.rs','-o',r.WORK/'capture.rmeta']
  r.run(f'capture-{kind}-{mode}',args,r.env()|{'CARGO_MANIFEST_DIR':str(path)});profiles.append(kind+'-'+mode)
 r.save(r.HERE/'capture-layouts.json',{'source':manifest,'assertions_source':source,'profiles':profiles,'compiler':r.desc(r.RUSTC),'scope':'four source capture size/alignment shapes; no source-place multiplicity or operational floor'})
finally:
 shutil.rmtree(path);(r.WORK/'capture.rmeta').unlink(missing_ok=True)
