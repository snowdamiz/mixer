import json,sys
import run_review as r
mode=sys.argv[1]
metadata=r.WORK/f'libordinary-{mode}.rmeta';library=r.WORK/f'ordinary-{mode}.dylib'
tag='default-corrected-'+mode+'-'
r.run(tag+'metadata',r.flags(mode)+['--crate-type','rlib','--emit=metadata',r.SOURCE/'src/lib.rs','-o',metadata])
cases={'encoder':'use mixer_vm::experimental::swift::snapshot_encoder_v2::SnapshotCursorV2;',
       'guard':'use mixer_vm::experimental_swift_reactor::InitialProfileBorrowV1;',
       'provenance':'use mixer_vm::experimental_swift_reactor::LoaderProvenanceV1;'}
for name,source in cases.items():
 p=r.WORK/f'external-{mode}-{name}.rs';p.write_text('extern crate mixer_vm;\n'+source+'\n')
 r.run(tag+'external-'+name,[r.RUSTC,'--crate-name','review_external','--edition=2021','--crate-type','lib','--emit=metadata',p,'--extern','mixer_vm='+str(metadata),'-o',r.WORK/f'external-{mode}.rmeta'],allowed=['E0603'])
 p.unlink();(r.WORK/f'external-{mode}.rmeta').unlink(missing_ok=True)
r.run(tag+'library',r.flags(mode)+['--crate-type','cdylib',r.SOURCE/'src/lib.rs','-o',library])
symbols=r.run(tag+'symbols',['/usr/bin/nm','-gU',library])
assert 'snapshot_encoder_v2'not in symbols and 'mixer_snapshot_encoder_host_v2'not in symbols
r.save(r.HERE/'default'/f'{mode}.json',{'source':r.manifest(r.SOURCE),'library':r.desc(library),'metadata':r.desc(metadata),'external_refusals':list(cases),'no_host_encoder_export':True,'compiler':r.desc(r.RUSTC)})
for method in ('finite_enum_and_option_mappings_v2','span_checks_refuse_bounds_v2'):
 r.run('enum-span-'+mode+'-'+method,[r.WORK/f'unit-{mode}','--exact','experimental::swift::snapshot_encoder_v2::encoder_unit::'+method,'--nocapture','--test-threads=1'])
metadata.unlink();library.unlink()
