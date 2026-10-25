#!/usr/bin/env python3
"""Apply only the root-selected private seam to the exact isolated candidate."""
import hashlib,json,pathlib,datetime
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
BASE=OUT/'.scratch/candidate'
proposal=OUT/'proposed-seam.md'
(OUT/'root-selection.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'proposal':'verification/swift-count-plan-retention-candidate/proposed-seam.md','proposalSHA256':hashlib.sha256(proposal.read_bytes()).hexdigest(),
  'authorization':'Root explicitly selected this finite isolated implementation after measured layout and full debit/failure schedule review.',
  'inventoryBytes':20472,'deltaExistingExpected':0,'debits':[41,16],'operationBytesExpected':112822,
  'scope':'finite host feasibility only; no live integration or full target; unchanged limits; memory admission regression retained'},indent=2)+'\n')
p=BASE/'src/experimental/cache/borrowed.rs';s=p.read_text()
s=s.replace('    type Scratch<\'a>;','    type Scratch<\'a>;\n    type ScanOutcome: Copy;\n    fn scan_counts(outcome: &Self::ScanOutcome) -> decode::Counts;\n    fn prepare_miss_publication(meter: &mut Self::Meter<\'_, \'_>) -> Result<(), Self::Failure>;\n    fn miss_timestamp(outcome: &Self::ScanOutcome, meter: &Self::Meter<\'_, \'_>) -> u64;')
s=s.replace('    ) -> Result<decode::Counts, Self::Failure>;','    ) -> Result<Self::ScanOutcome, Self::Failure>;')
s=s.replace("    type Scratch<'a> = ();", """    type Scratch<'a> = ();
    type ScanOutcome = decode::Counts;
    fn scan_counts(outcome: &decode::Counts) -> decode::Counts { *outcome }
    fn prepare_miss_publication(_: &mut Meter<'_>) -> Result<(), CacheFailure> { Ok(()) }
    fn miss_timestamp(_: &decode::Counts, meter: &Meter<'_>) -> u64 { meter.work_used() }""")
begin=s.index('fn pin_acquired<M: CacheMode>');prefix=s[:begin];body=s[begin:]
tail=body[body.index('    let slot = &mut parts.slots[index];'):body.rfind('\n}')]
assert tail.endswith('    Ok(pin)')
body=body.replace('    let index = if let Some(index) = hit {','    if let Some(index) = hit {',1)
body=body.replace('        meter.usage_mut().hit(hits);\n        index\n    } else {',
  '        meter.usage_mut().hit(hits);\n'+'\n'.join('    '+l for l in tail.splitlines())+'\n    } else {',1)
body=body.replace('        let counts = M::scan(parts.snapshot, defined, &mut parts.scratch, meter)?;',
  '        let outcome = M::scan(parts.snapshot, defined, &mut parts.scratch, meter)?;\n        let counts = M::scan_counts(&outcome);',1)
needle='        if let Err(error) =\n            M::resident_insert('
assert needle in body
body=body.replace(needle,"""        if let Err(error) = M::prepare_miss_publication(meter) {
            let _ = M::drop_entry(entry, meter);
            let _ = meter.construction(0);
            return Err(error);
        }
"""+needle,1)
miss_tail=tail.replace('slot.set_last_used(meter.work_used());','slot.set_last_used(M::miss_timestamp(&outcome, meter));')
body=body.replace('        parts.slots[index].set(entry);\n        index\n    };\n'+tail,
  '        parts.slots[index].set(entry);\n'+'\n'.join('    '+l for l in miss_tail.splitlines())+'\n    }',1)
assert body.count('let slot = &mut parts.slots[index];')==2
p.write_text(prefix+body)
p=BASE/'src/experimental_swift_reactor/cache.rs';s=p.read_text()
decl="""
// Root-selected isolated finite policy: no permanent state or new allocation.
#[repr(u8)]
#[derive(Clone, Copy)]
enum CountPlanInsertion { Cold, Reused }
#[repr(C)]
#[derive(Clone, Copy)]
pub(crate) struct CountPlanScanOutcome {
    counts: decode::Counts,
    insertion: CountPlanInsertion,
    reserved: [u8; 7],
}
// Complete source, argument/return and caller inventories are disjoint from
// every original inventory. Result sizes include the complete error variant.
struct CountPlanPolicyInventory {
    scan_created: CountPlanScanOutcome, scan_return: CountPlanScanOutcome, scan_caller: CountPlanScanOutcome,
    result_created: Result<CountPlanScanOutcome, SwiftRunFailure>,
    result_return: Result<CountPlanScanOutcome, SwiftRunFailure>,
    result_caller: Result<CountPlanScanOutcome, SwiftRunFailure>,
    index_created: usize, index_caller: usize,
    timestamp_created: u64, timestamp_return: u64, timestamp_caller: u64,
    original_match: bool, identity_valid: bool, reused_choice: bool, cold_choice: bool,
    counts_borrow: &'static CountPlanScanOutcome,
    prepare_meter: &'static mut SwiftMeter<'static, 'static>,
    timestamp_borrow: &'static CountPlanScanOutcome,
    timestamp_meter: &'static SwiftMeter<'static, 'static>,
    counts_created: decode::Counts, counts_return: decode::Counts, counts_caller: decode::Counts,
    preparation_created: Result<(), SwiftRunFailure>,
    preparation_return: Result<(), SwiftRunFailure>,
    preparation_caller: Result<(), SwiftRunFailure>,
}
const _: () = { assert!(size_of::<CountPlanScanOutcome>() == 32); };
"""
s=s.replace('const RESIDENT_BUCKETS: usize = 128;',decl+'\nconst RESIDENT_BUCKETS: usize = 128;',1)
at=s.index('const fn compute_cache_operation_bytes()');s=s[:at]+s[at:].replace('        (3, size_of::<PlanInventory>()),',
  '        (3, size_of::<PlanInventory>()),\n        (3, size_of::<CountPlanPolicyInventory>()),',1)
impl=s.index('impl CacheMode for SwiftMode');a=s[:impl];b=s[impl:]
needle="    type Scratch<'a> = SwiftScratch<'a>;";assert needle in b
b=b.replace(needle,needle+"""
    type ScanOutcome = CountPlanScanOutcome;
    fn scan_counts(outcome: &CountPlanScanOutcome) -> decode::Counts {
        // The complete borrow/read/copy boundary was precharged by scan.
        outcome.counts
    }
    fn prepare_miss_publication(meter: &mut SwiftMeter<'_, '_>) -> Result<(), SwiftRunFailure> {
        // Full preparation and later infallible choice/write, before index mutation.
        meter.work(16)
    }
    fn miss_timestamp(outcome: &CountPlanScanOutcome, meter: &SwiftMeter<'_, '_>) -> u64 {
        match outcome.insertion {
            CountPlanInsertion::Cold => 0,
            CountPlanInsertion::Reused => meter.work_used(),
        }
    }
""",1)
start=b.index('    fn scan(');end=b.index('    fn build(',start);scan=b[start:end]
scan=scan.replace(') -> Result<decode::Counts, SwiftRunFailure> {',') -> Result<CountPlanScanOutcome, SwiftRunFailure> {',1)
scan=scan.replace('                return Ok(plan.counts);',"""                meter.work(41)?; // complete outcome + later counts extraction
                return Ok(CountPlanScanOutcome {
                    counts: plan.counts,
                    insertion: CountPlanInsertion::Reused,
                    reserved: [0; 7],
                });""",1)
scan=scan.replace('        meter.work(PLAN_CELL_CREDITS + 3)?;',"""        meter.work(41)?; // before outcome and complete scan-plan publication
        let outcome = CountPlanScanOutcome {
            counts,
            insertion: CountPlanInsertion::Cold,
            reserved: [0; 7],
        };
        meter.work(PLAN_CELL_CREDITS + 3)?;""",1)
scan=scan.replace('        Ok(counts)\n','        Ok(outcome)\n',1)
b=b[:start]+scan+b[end:];p.write_text(a+b)
print('Applied selected isolated 41+16 seam; no live source edited')
