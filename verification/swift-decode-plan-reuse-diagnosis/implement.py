from pathlib import Path
H=Path(__file__).resolve().parent
p=H/'source/src/experimental_swift_reactor/cache.rs'
s=p.read_text()
def replace(a,b,n=1):
 global s
 assert s.count(a)==n,(a[:100],s.count(a),n)
 s=s.replace(a,b)
replace('const PATCH_CAPACITY: usize = 512;', '''const PATCH_CAPACITY: usize = 512;
// Finite private prototype: direct-map counts, never resident IR or a proof.
const PLAN_CAPACITY: usize = 512;
const PLAN_CELL_CREDITS: u64 = 8; // tag + four identity fields + three Counts fields
#[derive(Clone, Copy)]
struct ScanPlan {
    function: u32,
    body_offset: usize,
    body_len: usize,
    type_index: u32,
    counts: decode::Counts,
}
// These disjoint model fields conservatively cover named added locals, borrows,
// reborrows, caller/return copies, reserve::<Option<ScanPlan>> monomorphization,
// and the Option owner used by infallible publication. Three complete copies
// are admitted alongside existing generic scan/build/phase inventories.
struct PlanInventory {
    cell: Option<ScanPlan>,
    plan: ScanPlan,
    borrowed: &'static ScanPlan,
    slots: &'static mut [Option<ScanPlan>],
    vec: &'static mut Vec<Option<ScanPlan>>,
    reserve_receiver: &'static mut Vec<Option<ScanPlan>>,
    reserve_control: &'static mut CacheControl<'static>,
    index: usize,
    bytes: usize,
    counts: decode::Counts,
    output: Result<decode::Counts, SwiftRunFailure>,
    init: std::ops::Range<usize>,
}''')
replace("    index: &'a mut [u8],", "    index: &'a mut [u8],\n    plans: &'a mut [Option<ScanPlan>],")
replace('    index: Vec<u8>,','    index: Vec<u8>,\n    plans: Vec<Option<ScanPlan>>,',2)
replace('            index: Vec::new(),','            index: Vec::new(),\n            plans: Vec::new(),')
replace('        drop(take(&mut self.index));','        drop(take(&mut self.index));\n        drop(take(&mut self.plans));')
replace('        drop(take(&mut cache.index));','        drop(take(&mut cache.index));\n        drop(take(&mut cache.plans));')
replace('                index: take(&mut partial.index),','                index: take(&mut partial.index),\n                plans: take(&mut partial.plans),')
# Scratch construction at actual pin/release and invariant test helpers.
replace('                    index: &mut self.index,','                    index: &mut self.index,\n                    plans: &mut self.plans,',1) if '                    index: &mut self.index,' in s else None
# Other locations have receiver cache.
for receiver in ('cache','self'):
 a=f'                    index: &mut {receiver}.index,'
 if a in s:s=s.replace(a,a+f'\n                    plans: &mut {receiver}.plans,')
# Invariant helper has indentation different.
a='                index: &mut cache.index,'
if a in s:s=s.replace(a,a+'\n                plans: &mut cache.plans,')
replace('        self.control.check()?;\n        let owner = next_owner()', '''        // Header includes the complete payload before this allocation begins.
        reserve(&mut partial.plans, PLAN_CAPACITY, &mut self.control)?;
        for _ in 0..PLAN_CAPACITY {
            self.control.work(PLAN_CELL_CREDITS)?;
            partial.plans.push(None);
        }
        self.control.check()?;
        let owner = next_owner()''')
replace('    header.checked_add(RESIDENT_INDEX_BYTES)', '    header.checked_add(RESIDENT_INDEX_BYTES)?.checked_add(PLAN_CAPACITY * size_of::<Option<ScanPlan>>())')
# const fn ? not allowed for const Option, use explicit matches instead.
replace('    header.checked_add(RESIDENT_INDEX_BYTES)?.checked_add(PLAN_CAPACITY * size_of::<Option<ScanPlan>>())', '''    let Some(header) = header.checked_add(RESIDENT_INDEX_BYTES) else { return None; };
    header.checked_add(PLAN_CAPACITY * size_of::<Option<ScanPlan>>())''')
# Existing owner sizeof terms automatically include plans Vec/Scratch borrows.
# Add explicit vectors for transfer and added helper inventories per phase.
replace('        (4, size_of::<Vec<u8>>()),','        (4, size_of::<Vec<u8>>()),\n        (4, size_of::<Vec<Option<ScanPlan>>>()),')
replace('        (3, size_of::<Vec<u8>>()),','        (3, size_of::<Vec<u8>>()),\n        (3, size_of::<Vec<Option<ScanPlan>>>()),\n        (3, size_of::<PlanInventory>()),')
replace('        (3, size_of::<ResidentIndexInventory>()),','        (3, size_of::<ResidentIndexInventory>()),\n        (3, size_of::<PlanInventory>()),')
start='''        let policy = policy(snapshot, body, meter)?;
        meter.step(CacheStep::ScanReset);'''
replace(start,'''        let policy = policy(snapshot, body, meter)?;
        if scratch.plans.len() != PLAN_CAPACITY {
            return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_plan_layout"));
        }
        meter.work(1)?; // requested identity hash, collision alone never authorizes
        let index = body.absolute_index as usize & (PLAN_CAPACITY - 1);
        meter.work(1)?; // actual Option tag probe
        if let Some(plan) = &scratch.plans[index] {
            meter.work(1)?; // actual function identity probe
            if plan.function == body.absolute_index {
                // Probe all three remaining immutable-identity cells, including
                // malformed metadata. Do not short-circuit their accounting.
                meter.work(3)?;
                if plan.body_offset != body.body_offset
                    || plan.body_len != body.body.len()
                    || plan.type_index != body.type_index {
                    return Err(meter.error(CacheFailureKind::DecoderMismatch, "swift_plan_identity"));
                }
                meter.work(3)?; // actual three-field Counts copy; also checks stop
                return Ok(plan.counts);
            }
        }
        meter.step(CacheStep::ScanReset);''')
# scan first only, retain build complete pass.
replace('''            None,
        )
    }
    fn build(''','''            None,
        )?;
        // Successful complete scan is the only publishing source. All checks
        // and charges precede the single infallible full-cell replacement.
        meter.work(PLAN_CELL_CREDITS + 3)?;
        scratch.plans[index] = Some(ScanPlan {
            function: body.absolute_index,
            body_offset: body.body_offset,
            body_len: body.body.len(),
            type_index: body.type_index,
            counts,
        });
        Ok(counts)
    }
    fn build(''')
# Above call previously expression; capture returned Counts.
needle='''        decode::scan_borrowed(
            body.body,
            body.body_offset,
            &policy,'''
replace(needle,'''        let counts = decode::scan_borrowed(
            body.body,
            body.body_offset,
            &policy,''')
s+='''
#[cfg(test)]
pub(super) mod plan_inspection {
    use super::*;
    pub fn shape() -> (usize,usize,usize,usize,usize,usize) {
        (size_of::<Option<ScanPlan>>(), PLAN_CAPACITY * size_of::<Option<ScanPlan>>(), size_of::<PlanInventory>(), cache_header_bytes().unwrap(), cache_construction_bytes().unwrap(), cache_operation_bytes().unwrap())
    }
    pub fn count(cache: &SwiftFunctionCache) -> usize { cache.plans.iter().filter(|x| x.is_some()).count() }
    pub fn key(cache: &SwiftFunctionCache, f:u32) -> Option<u32> { cache.plans[f as usize & (PLAN_CAPACITY - 1)].as_ref().map(|p|p.function) }
    pub fn corrupt(cache: &mut SwiftFunctionCache, f:u32, field:usize) {
        let p = cache.plans[f as usize & (PLAN_CAPACITY - 1)].as_mut().unwrap();
        match field { 0 => p.body_offset += 1, 1 => p.body_len += 1, 2 => p.type_index += 1, 3 => p.counts = p.counts.test_changed_instructions(), _ => panic!("field") }
    }
    pub fn states(cache:&SwiftFunctionCache) -> Vec<(u32,usize,u64)> {cache.slots.iter().filter_map(|s|s.entry().map(|e|(e.function,s.pins,s.last_used))).collect()}
}
'''
p.write_text(s)
print('modified isolated cache.rs only')
