#!/usr/bin/env python3
"""Bounded exact-source reproduction; original nested-cargo wrapper stays unrun."""
from pathlib import Path
import json,re,sys
sys.dont_write_bytecode=True
import evidence as E
HERE=E.HERE
def main():
 mode=sys.argv[1];group=sys.argv[2];library=E.WORK/f'libmixer_vm_public_{mode}.rlib'
 if group=='build':
  E.run('public-library-'+mode,E.flags(mode)+['--crate-type','rlib',E.SOURCE/'src/lib.rs','-o',library]);E.write(HERE/f'public-library-{mode}.json',E.ident(library));return
 source=E.SOURCE/'src/experimental_swift_reactor/cache_tests.rs';text=source.read_text();start=text.index('let cases=[');part=text[start:text.index('];',start)+2]
 found=re.findall(r'\("([a-z_]+)", "((?:[^"\\]|\\.)*)",(None|Some\("[^"]+"\))\)',part)
 assert len(found)==13,len(found)
 cases=[]
 for name,body,diagnostic in found:
  decoded=json.loads('"'+body+'"');expected=None if diagnostic=='None'else diagnostic[6:-2]
  cases.append((name,decoded,expected))
 mapping=[{'original_test':'external_surface_and_borrow_privacy','source_path':str(source.relative_to(HERE)),'source_file':E.ident(source),'case':name,'exact_source':body,'expected_diagnostic':diag,'original_wrapper_executed':False}for name,body,diag in cases]
 E.write(HERE/'public-compiler-source-mapping.json',mapping)
 for name,body,expected in cases[int(group)*7:(int(group)+1)*7]:
  fixture=HERE/'compile_cases'/('public-'+name+'.rs');fixture.write_text(body+'\n')
  record={'mode':mode,'fixture':E.ident(fixture),'library':E.ident(library),'exact_original_source_reproduced':True,'original_wrapper_unrun':True,'expected_diagnostic':expected}
  E.write(HERE/'compiler-variants'/f'public-{mode}-{name}.json',record)
  E.run('public-contract-'+mode+'-'+name,[E.RUSTC,'--crate-type','lib','--edition=2021','--extern','mixer_vm='+str(library),fixture,'--emit=metadata','-o',E.WORK/f'public-case-{mode}.rmeta'],expected=expected)
if __name__=='__main__':main()
