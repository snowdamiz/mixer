from pathlib import Path
import difflib,hashlib,json
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for variant in ['baseline','selected']:
 s=P/'scratch'/variant
 f=s/'src/experimental_swift_reactor/cache_tests.rs'
 f.write_text(f.read_text()+'\n'+(P/'owner-control.rs').read_text())
 if variant=='selected':
  f.write_text(f.read_text()+'\n'+(P/'lifetime-controls.rs').read_text())
  f=s/'src/experimental_swift_reactor/cache.rs'
  v=f.read_text()
  v=v.replace('        drop(take(&mut self.index));','        #[cfg(test)] grouped_review::before(self.control_ref_placeholder, None, &self.index, self.header.is_some());\n        drop(take(&mut self.index));\n        #[cfg(test)] grouped_review::after(control.control, control.observation(), &self.index);')
  v=v.replace('self.control_ref_placeholder, None','control.control, control.observation()')
  v=v.replace('        drop(take(&mut cache.index));','        #[cfg(test)] grouped_review::before(control, wasi.map(AccountedWasi::usage), &cache.index, cache.header.is_some());\n        drop(take(&mut cache.index));\n        #[cfg(test)] grouped_review::after(control, wasi.map(AccountedWasi::usage), &cache.index);')
  v=v.replace('    drop((storage, failure));\n    (control, wasi, header)','    drop((storage, failure));\n    #[cfg(test)] grouped_review::completing(control, wasi.map(AccountedWasi::usage));\n    (control, wasi, header)')
  f.write_text(v+'\n'+(P/'lifetime-observers.rs').read_text())
  f=s/'src/experimental_swift_reactor/allocation_tests.rs'
  f.write_text(f.read_text()+'\n// Independent review observer of the existing test allocator.\npub(crate) fn review_allocator_snapshot() -> AllocationStats { STATS.with(Cell::get) }\n')
 m={str(f.relative_to(s)):sha(f) for f in sorted(s.rglob('*')) if f.is_file()}
 (P/(variant+'-overlay-source-manifest.json')).write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
 clean=json.loads((P/(variant+'-source-manifest.json')).read_text())
 changes=[n for n in clean if clean[n]!=m[n]]
 (P/(variant+'-review-overlay.patch')).write_text(''.join(''.join(difflib.unified_diff((P.parent/'swift-resident-index-grouped-reservation'/'source'/n).read_text().splitlines(True),(s/n).read_text().splitlines(True),fromfile='selected/'+n,tofile=variant+'-review/'+n)) for n in changes))
 print(variant,len(m),changes)
