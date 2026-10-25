#!/usr/bin/env python3
"""Prepare bounded baseline/candidate source copies from the strict VM132 closure."""
from pathlib import Path
import hashlib,json,shutil,sys,difflib
out=Path(__file__).resolve().parent;root=out.parent.parent
mode=sys.argv[1];assert mode in ('baseline','candidate')
manifest=json.loads((out/'baseline-manifest.json').read_text());scratch=out/'scratch'
for rel,expected in manifest.items():
 source=root/'vm'/rel;assert hashlib.sha256(source.read_bytes()).hexdigest()==expected,rel
 dest=scratch/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
cache_path=scratch/'src/experimental_swift_reactor/cache.rs'
cache=cache_path.read_text()
needle='pub(super) mod inspection {\n    use super::*;\n'
assert cache.count(needle)==1
cache=cache.replace(needle,needle+(out/'test-seam.rs').read_text())
if mode=='candidate':
 old='''    // One Cache credit/check before each of 512 writes, in each sequential pass.
    for patch in patches {
        meter.work(1)?;
        *patch = decode::EMPTY_PATCH;
    }
    Ok(())'''
 new='''    // Both passes start at depth zero and fully initialize each active slot
    // before reading it. Keep initialized reserved storage and the ordinary
    // cancellation/deadline boundary check; inactive slots need no clearing.
    #[cfg(test)]
    super::cache_tests::elision_dirty_before_boundary(patches);
    meter.check()'''
 assert cache.count(old)==1;cache=cache.replace(old,new)
cache_path.write_text(cache)
tests_path=scratch/'src/experimental_swift_reactor/cache_tests.rs'
tests=tests_path.read_text()
needle='pub(super) fn checkpoint(control: &RuntimeControl, _: Cursor) {\n'
assert tests.count(needle)==1
tests=tests.replace(needle,needle+'    elision_observe_checkpoint(control);\n')
needle='fn finish(cache: SwiftFunctionCache, mut control: RuntimeControl) {\n'
assert tests.count(needle)==1
tests=tests.replace(needle,needle+'    let before_cleanup_work = control.usage(None).cache_work;\n')
needle='    let final_usage = control.finish_owned_cleanup(None);\n'
assert tests.count(needle)==1
tests=tests.replace(needle,needle+'    assert_eq!(\n        final_usage.cache_work, before_cleanup_work,\n        "consuming cleanup must add no work"\n    );\n')
tests+=(out/'tests.rs').read_text()
tests_path.write_text(tests)
if mode=='candidate':
 lifecycle_path=scratch/'src/experimental_swift_reactor/lifecycle_tests.rs'
 lifecycle=lifecycle_path.read_text()
 begin=lifecycle.index('fn swift_lifecycle_sl13_cumulative_instruction_host_and_cache_usage()')
 end=lifecycle.index('\n#[test]',begin)
 selected=lifecycle[begin:end]
 assert selected.count('1151')==4
 selected=selected.replace('1151','127').replace('1803','779').replace('4196','1124').replace('4206','1134')
 lifecycle=lifecycle[:begin]+selected+lifecycle[end:]
 begin=lifecycle.index('fn swift_lifecycle_sl14_later_work_cache_and_absolute_deadline_do_not_reset()')
 end=lifecycle.index('\n#[test]',begin)
 selected=lifecycle[begin:end]
 assert selected.count('1764')==3
 selected=selected.replace('1151+1+4+3=1159','127+1+4+3=135').replace('1764','740')
 lifecycle=lifecycle[:begin]+selected+lifecycle[end:]
 lifecycle_path.write_text(lifecycle)
source={rel:hashlib.sha256((scratch/rel).read_bytes()).hexdigest() for rel in manifest}
(out/f'{mode}-source-manifest.json').write_text(json.dumps(source,sort_keys=True,indent=2)+'\n')
if mode=='candidate':
 diffs=[]
 for rel in manifest:
  old=(root/'vm'/rel).read_text();new=(scratch/rel).read_text()
  if old!=new:
   dest=out/'candidate'/'vm'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(scratch/rel,dest)
   diffs.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/vm/'+rel,tofile='b/vm/'+rel))
 (out/'candidate.patch').write_text(''.join(diffs))
print(f'Prepared {mode}: {len(source)} exact source members, {sum(manifest[r]!=source[r] for r in manifest)} changed private files')
