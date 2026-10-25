#!/usr/bin/env python3
"""Apply only test observation seams to the owned accepted source reconstruction."""
from pathlib import Path
import difflib,hashlib,json
H=Path(__file__).resolve().parent;P=H.parent/'swift-plan-cache-remaining-work-diagnosis';S=H/'owned-source'
base=json.loads((H/'baseline-manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert {n:sha(S/n) for n in base}==base
# Reuse the demonstrated exact transforms as data, never execute its driver.
patch=(P/'instrumentation.patch').read_text()
changed=['src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs']
# Restore demonstrated copy-only instrumented files directly from its sealed archive.
import tarfile
with tarfile.open(P/'isolated-source.tar.gz','r:gz') as t:
 for n in changed[:2]:(S/n).write_bytes(t.extractfile(n).read())
def edit(n,old,new):
 p=S/n;s=p.read_text();assert s.count(old)==1,(n,old,s.count(old));p.write_text(s.replace(old,new))
edit(changed[0],'fn diagnostic_completed(&mut self) {}','fn diagnostic_completed(&mut self, _: u32) {}')
edit(changed[0],'meter.diagnostic_completed();','meter.diagnostic_completed(function);')
edit(changed[1],'super::cache_tests::remaining_plan_work(n, result.is_ok());','super::cache_tests::remaining_plan_work(n, self.cursor, result.as_ref().err());')
edit(changed[1],'fn diagnostic_completed(&mut self) { super::cache_tests::remaining_plan_completed(); }','fn diagnostic_completed(&mut self, function: u32) { super::cache_tests::remaining_plan_completed(function); }')
edit(changed[1],'        SwiftMeter { operation, usage }','        #[cfg(test)] super::cache_tests::remaining_plan_begin(function);\n        SwiftMeter { operation, usage }')
p=S/changed[2];p.write_bytes(p.read_bytes()+b'\n'+(H/'observer-and-controls.rs').read_bytes())
modified={n:sha(S/n) for n in base}
assert [n for n in base if base[n]!=modified[n]]==changed
(H/'copied-source-manifest.json').write_text(json.dumps(modified,indent=2,sort_keys=True)+'\n')
(H/'instrumentation.patch').write_text(''.join(''.join(difflib.unified_diff((P/'originals'/n).read_text().splitlines(True),(S/n).read_text().splitlines(True),fromfile='accepted/'+n,tofile='isolated/'+n)) for n in changed))
print(json.dumps({'sourceFiles':len(base),'changedFiles':changed,'manifestSHA256':sha(H/'copied-source-manifest.json')}))
