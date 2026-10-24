#!/usr/bin/env python3
"""Executable, bounded next-behavior gate. This contract packet does not run it.

Usage: --vm PATH --source-tree-sha256 DIGEST --run. Refuses a source mismatch,
missing exact test identity, ignored test, unsupported config or external target.
Caller must separately bind full source/binaries/output and independent review.
"""
from pathlib import Path
import argparse,json,subprocess,os,hashlib,sys
HERE=Path(__file__).resolve().parent
specs=[
 ('mm01_all_load_store_shapes','14 load and 9 store opcodes, four Value types, full/narrow signed+unsigned, negative values, high bits; exact bytes/result bits and delta values'),
 ('mm02_little_endian_nan_unaligned','little endian non-palindromic bytes, unaligned offsets1/3/7, f32/f64 positive/negative zero, infinity, quiet/signaling NaN payload preservation'),
 ('mm03_memory_bounds_overflow','valid final range; one-byte end OOB; unsigned i32 max+u32 max offset; direct usizeMAX checked-add overflow; no host panic or out-of-range access'),
 ('mm04_opcode_type_floor_closed','nonmemory and wrong Load/Store scalar opcode reject before pop/work; absent frame; caller/local operand floors; wrong address/store value type, insufficient count'),
 ('mm05_load_store_work_prefix','load pop/width/push, store value-pop/address-pop/width work denial prefixes, exact live values and memory write prefix; helper charges no instruction fuel'),
 ('mm06_cancel_prefix','cancellation at every accepted primitive work checkpoint and caller boundary; no mutation after failed check; final width-success store is atomic bounded write'),
 ('mm07_pinned_decoded_caller','actual retained frame pin selects instruction; cursor actual function/offset; one instruction+fuel+caller work+pc advance exactly once; no borrow survives effect'),
 ('mm08_post_pop_live_fault','existing post-pop live-removal failure latches original Cleanup with absent cursor/resource and real WASI; debt retained; no fabricated source diagnostic'),
 ('mm09_held_pin_cleanup','deepest retained frames/pins survive every helper failure and release rejection; drain once retains failed releases; explicit cleanup retry then fixed completion exact restore'),
 ('mm10_actual_live_capacity','actual/live preflight mismatch; injected existing push room/predebit denial after load read; no result publication, no allocation, actual reduction tracked'),
 ('mm11_slot_vacancy','occupied entry Some(Ok) and Some(Err) preserved; no fetch/debit/pc/value/memory effect before vacancy; prior first failure sticky; no overwrite of entry guard/pin'),
 ('mm12_outcome_completion','outer Ok only slot publication; stored Err stops next fetch; take/drop success before reuse; pass actual fixed storage and retained diagnostics through original completion/owner cleanup'),
 ('mm13_no_alloc_warm','after cache/pins/arenas warmed, allocation observer refusing first request sees zero requests over all selected load/store success/trap/work/cancel paths'),
 ('mm14_frozen_parity','unchanged expanded Frozen range/load/store/run/copy/fill/grow and original 2912 reservation; executed baseline vs candidate values/bytes/traps/work/fuel/cache/allocation parity'),
 ('mm15_deferred_fail_closed','MemoryCopy, MemoryFill, MemoryGrow, MemorySize and all non-Load/Store operations reject in this API; original memory ticket identity and capacity unchanged'),
 ('mm16_accounting_restore','exact positive actual authored/canonical inventory replay; all 8 profile/feature/unit layouts; original containing owner identity; frame bound old+nested/new active once; header positive permanent; exact restoration or retained debt'),
]
CASES=[dict(id=n,requiredTest='experimental_swift_reactor::execution::frame_operations::memory_operations::tests::'+n,requirement=d,status='pending-behavior-lane',maxGuestSteps=64,maxCallFrames=3,maxMemoryPages=584,phoneOrUI=False,maxFixtureInstancesPerCase=64,maxTotalGuestStepsPerCase=4096) for n,d in specs]
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--vm',type=Path);parser.add_argument('--source-tree-sha256');parser.add_argument('--run',action='store_true');args=parser.parse_args()
 if not args.run:
  print(json.dumps(dict(status='behavior-not-run',cases=CASES,configurations=['swift-debug','swift-release','all-debug','all-release'],scope='Host development only; 584-page strict-ABI synthetic fixture; no full target or device',limits=dict(maxGuestStepsPerCase=64,maxCallFrames=3,serial=True)),sort_keys=True,indent=2));sys.exit(0)
 assert args.vm and args.source_tree_sha256
 sys.path.insert(0,str(HERE));import build_overlay as b
 assert b.digest(b.manifest(args.vm))==args.source_tree_sha256
 env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH']);env.pop('RUSTFLAGS',None);env.pop('RUSTC_BOOTSTRAP',None)
 # The future behavior lane owns a separate bounded target directory and records cleanup.
 assert 'CARGO_TARGET_DIR' in env,'set an owned CARGO_TARGET_DIR before --run'
 for feature,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
  for release in [False,True]:
   common=['cargo','test','--lib','--locked','--offline',*flags,*(['--release'] if release else [])]
   listed=subprocess.run([*common,'--','--list'],cwd=args.vm,env=env,capture_output=True,text=True,timeout=600);assert listed.returncode==0,listed.stderr
   names={line.removesuffix(': test') for line in listed.stdout.splitlines() if line.endswith(': test')}
   assert {c['requiredTest'] for c in CASES}<=names,'required exact memory tests absent; contract typing is not behavior evidence'
   for case in CASES:
    result=subprocess.run([*common,case['requiredTest'],'--','--exact','--nocapture','--test-threads=1'],cwd=args.vm,env=env,capture_output=True,text=True,timeout=180)
    print(feature,'release' if release else 'debug',case['id'],result.returncode,flush=True)
    assert result.returncode==0 and '1 passed; 0 failed; 0 ignored' in result.stdout,(case,result.stdout,result.stderr)
    assert b.digest(b.manifest(args.vm))==args.source_tree_sha256
