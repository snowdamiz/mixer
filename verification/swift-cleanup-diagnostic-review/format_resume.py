#!/usr/bin/env python3
"""Resume formatting after a helper command-name collision, without reruns."""
import difflib,json,sys
sys.dont_write_bytecode=True
import collect as c
from validate import item

vm=c.source('candidate');source=c.digest(c.manifest(vm));fragments={}
for scope in ['default','experimental-stream-validation','experimental-function-cache','experimental-span-execution','experimental-swift-wasi','experimental-swift-reactor','experimental-capability-mailbox','experimental-capability-guest','experimental-capability-native','all']:
    assert json.loads((c.HERE/'commands'/('library-check-'+scope)/'receipt.json').read_text())['exitCode']==0
for scope in ['swift','all']:assert json.loads((c.HERE/'commands'/('clippy-'+scope)/'receipt.json').read_text())['exitCode']==0
for file,methods,free in [('control.rs',['pub(crate) fn remove_live_at_with_wasi('],False),('frame_operations.rs',['fn remove_live_at('],False),('value_operations.rs',['fn primitive_pop(','fn primitive_numeric('],True),('control_operations.rs',['fn control_remove('],False)]:
    for ordinal,method in enumerate(methods):
        body=item((vm/'src/experimental_swift_reactor'/file).read_text(),method)
        text=(body+'\n')if free else('impl Placeholder {\n    '+body+'\n}\n')
        path=c.HERE/'format-fragments'/(file+'-'+str(ordinal)+'.rs');path.parent.mkdir(exist_ok=True);path.write_text(text)
        c.command('format-check-'+file+'-'+str(ordinal),['rustfmt','--edition','2021','--check',str(path)],vm)
        fragments[str(path.relative_to(c.HERE))]=c.sha(path.read_bytes())
before=c.manifest(c.source('baseline'));after=c.manifest(vm);additions=[]
for n in after:
    if before[n]==after[n]:continue
    for line in difflib.unified_diff((c.source('baseline')/n).read_text().splitlines(True),(vm/n).read_text().splitlines(True)):
        if line.startswith('+')and not line.startswith('+++'):
            raw=line[1:].rstrip('\n');assert raw==raw.rstrip();additions.append(raw)
c.save('compiler-checks.json',dict(sourceSHA256=source,libraryFeatureChecks=10,clippyProductionScopes=['swift','all'],warningsDenied=True,scopedRustfmtFragments=fragments,addedLinesCheckedForTrailingWhitespace=len(additions),sourceUnchanged=c.digest(c.manifest(vm))==source,helperResume='checks.py command-name collision; completed compiler checks retained, formatting resumed without repeats'))
