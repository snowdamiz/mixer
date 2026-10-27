#!/usr/bin/env python3
"""Compiler-check remaining standard helper-place shapes; no runtime or authority."""
from pathlib import Path
import json,shutil,sys
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT/'host'))
import runner
ROWS=[('[u64;11]',88,8),('&mut[u8;576]',8,8),('&mut[u8;512]',8,8),('&[u64]',16,8),('&mut[u8]',16,8),
 ('Result<&mut[u8;576],std::array::TryFromSliceError>',16,8),('Result<&mut[u8;512],std::array::TryFromSliceError>',16,8),
 ('Result<[u8;8],std::array::TryFromSliceError>',16,8),('std::ops::Range<usize>',16,8),('Option<usize>',16,8),
 ('Result<usize,std::num::TryFromIntError>',16,8),('Option<&metadata::Signature>',8,8),('Option<&Type>',8,8),
 ('Option<&metadata::Import>',8,8),('Option<&metadata::Function>',8,8),('Option<&metadata::Global>',8,8),
 ('Option<&metadata::Export>',8,8),('Option<&metadata::Segment>',8,8),('(usize,&u64)',16,8),('(usize,&WasiFunction)',16,8),
 ('usize',8,8),('u64',8,8),('u32',4,4),('bool',1,1)]
LOADER=[('std::iter::Enumerate<std::slice::Iter<\'static,FileIdentityV1>>',24,8),('(usize,&FileIdentityV1)',16,8),('(usize,&[u8;32])',16,8)]
def constants(rows):
 return '\nconst _:()={\n'+''.join(f'assert!(std::mem::size_of::<{ty}>()=={n});assert!(std::mem::align_of::<{ty}>()=={a});\n'for ty,n,a in rows)+'};\n'
def main():
 variant=runner.WORK/'layout-supplement';shutil.copytree(runner.SOURCE,variant)
 try:
  p=variant/'src/experimental/swift.rs';s=p.read_text();assert s.endswith('\n}\n');p.write_text(s[:-3]+constants(ROWS)+'\n}\n')
  p=variant/'src/experimental_swift_reactor/retained_profile_loader_v1.rs';p.write_text(p.read_text()+constants(LOADER))
  receipts=[]
  for mode in ['debug','optimized']:
   for kind in ['unit','production']:
    argv=runner.flags(mode)+(['--test']if kind=='unit'else['--crate-type','rlib'])+['--emit=metadata',variant/'src/lib.rs','-o',runner.WORK/'supplement.rmeta']
    _,receipt=runner.run('layout-supplement-'+kind+'-'+mode,argv,runner.cleanenv()|{'CARGO_MANIFEST_DIR':str(variant)})
    receipts.append(receipt)
  runner.save(OUT/'layout-supplement.json',{'schema':1,'source':runner.manifest(runner.SOURCE),'variant':runner.manifest(variant),'assertions':ROWS+LOADER,'compiler_configurations':receipts,'scope':'27 helper-place size/alignment compiler assertions; no runtime/source floor or new budget grant'})
 finally:
  shutil.rmtree(variant);(runner.WORK/'supplement.rmeta').unlink(missing_ok=True)
if __name__=='__main__':main()
