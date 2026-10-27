from pathlib import Path
import json, shutil, sys
sys.dont_write_bytecode=True
import run_review as r
kind,mode=sys.argv[1:]
root=r.HERE/'privacy-work'/f'{kind}-{mode}'
shutil.copytree(r.SOURCE,root)
p=root/'src/lib.rs';base=p.read_text()
api='crate::experimental::swift::snapshot_encoder_v2'
g='crate::experimental_swift_reactor::InitialProfileBorrowV1'
v=api+'::SnapshotViewV2';c=api+'::SnapshotCursorV2';b=api+'::SnapshotBlockV2'
cases={
'positive':(None,f"fn check(g:&{g}<'_>){{let v={api}::borrow_snapshot_v2(g).unwrap();let mut c=v.into_cursor().unwrap();let mut b=[3u8;4096];{{let x=c.next_block(&mut b).unwrap();drop(x);}}let _=c.next_block(&mut b);}}"),
'positive-separate-array':(None,f"fn check(c:&mut {c}<'_>){{let mut a=[0u8;4096];let mut b=[0u8;4096];let x=c.next_block(&mut a).unwrap();let _=c.next_block(&mut b);drop(x);}}"),
'positive-block-outlives-cursor':(None,f"fn check<'b>(g:&{g}<'_>,b:&'b mut[u8;4096])->{b}<'b>{{let mut c={api}::borrow_snapshot_v2(g).unwrap().into_cursor().unwrap();let block=c.next_block(b).unwrap().unwrap();drop(c);block}}"),
'raw-proof':(['E0308'],f"fn check(p:&crate::experimental_swift_reactor::ValidatedSwiftReactor){{let _={api}::borrow_snapshot_v2(p);}}"),
'foreign-source':(['E0061'],f"fn check(g:&{g}<'_>,s:&[u8]){{let _={api}::borrow_snapshot_v2(g,s);}}"),
'foreign-provenance':(['E0061'],f"fn check(g:&{g}<'_>,p:&crate::experimental_swift_reactor::LoaderProvenanceV1){{let _={api}::borrow_snapshot_v2(g,p);}}"),
'digest':(['E0308'],f"fn check(){{let _={api}::borrow_snapshot_v2(&[0u8;32]);}}"),
'bool':(['E0308'],f"fn check(){{let _={api}::borrow_snapshot_v2(&true);}}"),
'callback':(['E0061'],f"fn check(g:&{g}<'_>){{let _={api}::borrow_snapshot_v2(g,|_:&[u8]|{{}});}}"),
'view-literal':(['E0451'],f"fn check(){{let _={v}{{initial:unimplemented!(),proof:unimplemented!(),provenance:unimplemented!()}};}}"),
'cursor-literal':(['E0451'],f"fn check(){{let _={c}{{view:unimplemented!(),header:[0;2560],extent:0,emitted:0}};}}"),
'block-literal':(['E0451'],f"fn check(){{let _={b}{{bytes:&[],offset:0,final_block:false}};}}"),
'guard-literal':(['E0451'],f"fn check(){{let _={g}{{cache:unimplemented!(),control:unimplemented!(),wasi:None,scalars:unimplemented!()}};}}"),
'guard-clone':(['E0599'],f"fn check(g:{g}<'_>){{let _=g.clone();}}"),
'provenance-clone':(['E0599'],"fn check(p:crate::experimental_swift_reactor::LoaderProvenanceV1){let _=p.clone();}"),
'view-clone':(['E0599'],f"fn check(v:{v}<'_>){{let _=v.clone();}}"),
'cursor-clone':(['E0599'],f"fn check(c:{c}<'_>){{let _=c.clone();}}"),
'view-copy':(['E0277'],f"fn needs<T:Copy>(){{}}fn check(){{needs::<{v}<'static>>();}}"),
'cursor-copy':(['E0277'],f"fn needs<T:Copy>(){{}}fn check(){{needs::<{c}<'static>>();}}"),
'view-reuse':(['E0382'],f"fn check(v:{v}<'_>){{let _=v.into_cursor();let _=v.into_cursor();}}"),
'guard-escape':(['E0515'],f"fn check<'a>(g:{g}<'a>)->{c}<'a>{{{api}::borrow_snapshot_v2(&g).unwrap().into_cursor().unwrap()}}"),
'guard-move':(['E0505'],f"fn check(g:{g}<'_>){{let v={api}::borrow_snapshot_v2(&g).unwrap();drop(g);let _=v.into_cursor();}}"),
'source-mutation':(['E0594'],f"fn check(g:&{g}<'_>){{g.snapshot_proof_v2().source()[0]=1;}}"),
'transfer-reborrow':(['E0499'],f"fn check(c:&mut {c}<'_>){{let mut b=[0;4096];let x=c.next_block(&mut b).unwrap().unwrap();let _=c.next_block(&mut b);let _=x.bytes();}}"),
'transfer-mutation':(['E0506'],f"fn check(c:&mut {c}<'_>){{let mut b=[0;4096];let x=c.next_block(&mut b).unwrap().unwrap();b[0]=1;let _=x.bytes();}}"),
'transfer-escape':(['E0515'],f"fn check(c:&mut {c}<'_>)->{b}<'static>{{let mut b=[0;4096];c.next_block(&mut b).unwrap().unwrap()}}"),
'transfer-slice':(['E0308'],f"fn check(c:&mut {c}<'_>,b:&mut[u8]){{let _=c.next_block(b);}}"),
'transfer-wrong-size':(['E0308'],f"fn check(c:&mut {c}<'_>){{let mut b=[0;4095];let _=c.next_block(&mut b);}}"),
'transfer-owned':(['E0308'],f"fn check(c:&mut {c}<'_>){{let b=[0;4096];let _=c.next_block(b);}}"),
'transfer-vector':(['E0308'],f"fn check(c:&mut {c}<'_>){{let mut b=vec![0u8;4096];let _=c.next_block(&mut b);}}"),
'cursor-reset':(['E0599'],f"fn check(c:&mut {c}<'_>){{c.reset();}}"),
'cursor-rewind':(['E0599'],f"fn check(c:&mut {c}<'_>){{c.rewind();}}"),
}
results=[]
try:
 for name,(allowed,source)in cases.items():
  p.write_text(base+'\nmod independent_privacy{'+source+'}\n')
  args=r.flags(mode)+(['--test']if kind=='unit'else['--crate-type','rlib'])+['--emit=metadata',p,'-o',r.WORK/f'probe-{kind}-{mode}.rmeta']
  label=f'privacy-{kind}-{mode}-{name}'
  r.run(label,args,r.env()|{'CARGO_MANIFEST_DIR':str(root)},allowed)
  receipt=json.loads((r.HERE/'commands'/label/'receipt.json').read_text())
  results.append({'name':name,'source':source,'expected_diagnostics':allowed,'receipt':receipt,'source_sha256':r.sha(p.read_bytes())})
finally:
 shutil.rmtree(root);(r.WORK/f'probe-{kind}-{mode}.rmeta').unlink(missing_ok=True)
r.save(r.HERE/'privacy'/f'{kind}-{mode}.json',{'cases':results,'source_base':r.manifest(r.SOURCE),'scratch_removed':not root.exists()})
