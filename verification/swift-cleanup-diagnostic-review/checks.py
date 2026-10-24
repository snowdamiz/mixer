#!/usr/bin/env python3
import json,re,difflib
from pathlib import Path
import collect as c
from validate import item

def main():
 vm=c.source('candidate');source=c.digest(c.manifest(vm))
 records=[]
 for name,flags in [('default',[]),*[(f,['--features',f])for f in ['experimental-stream-validation','experimental-function-cache','experimental-span-execution','experimental-swift-wasi','experimental-swift-reactor','experimental-capability-mailbox','experimental-capability-guest','experimental-capability-native']],('all',['--all-features'])]:
  t=c.target(vm,name,'debug','library-check');_,r=c.command('library-check-'+name,['cargo','check','--lib','--offline','--locked',*flags],vm,{'CARGO_TARGET_DIR':str(t)});records.append(r)
 for name,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
  t=c.target(vm,name,'debug','clippy');_,r=c.command('clippy-'+name,['cargo','clippy','--lib','--offline','--locked',*flags,'--','-D','warnings'],vm,{'CARGO_TARGET_DIR':str(t)});records.append(r)
 c.command('tool-rustfmt',['rustfmt','--version'],vm)
 fragments={}
 for file,methods,free in [('control.rs',['pub(crate) fn remove_live_at_with_wasi('],False),('frame_operations.rs',['fn remove_live_at('],False),('value_operations.rs',['fn primitive_pop(','fn primitive_numeric('],True),('control_operations.rs',['fn control_remove('],False)]:
  for ordinal,method in enumerate(methods):
   body=item((vm/'src/experimental_swift_reactor'/file).read_text(),method)
   text=(body+'\n')if free else('impl Placeholder {\n    '+body+'\n}\n')
   path=c.HERE/'format-fragments'/(file+'-'+str(ordinal)+'.rs');path.parent.mkdir(exist_ok=True);path.write_text(text)
   c.command('format-check-'+file+'-'+str(ordinal),['rustfmt','--edition','2021','--check',str(path)],vm)
   fragments[str(path.relative_to(c.HERE))]=c.sha(path.read_bytes())
 before=c.manifest(c.source('baseline'));after=c.manifest(vm);changed=[n for n in after if before.get(n)!=after[n]]
 additions=[]
 for name in changed:
  b=(c.source('baseline')/name).read_text().splitlines(True);a=(vm/name).read_text().splitlines(True)
  for line in difflib.unified_diff(b,a):
   if line.startswith('+')and not line.startswith('+++'):
    raw=line[1:].rstrip('\n');assert raw==raw.rstrip(),(name,raw);additions.append(raw)
 c.save('compiler-checks.json',dict(sourceSHA256=source,libraryFeatureChecks=10,clippyProductionScopes=['swift','all'],warningsDenied=True,scopedRustfmtFragments=fragments,addedLinesCheckedForTrailingWhitespace=len(additions),sourceUnchanged=c.digest(c.manifest(vm))==source))
if __name__=='__main__':main()
