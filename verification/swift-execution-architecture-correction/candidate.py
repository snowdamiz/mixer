#!/usr/bin/env python3
"""Pure transforms of the bound source archive; no compiler or guest execution."""
import hashlib
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
V1 = ROOT / "verification/swift-cache-capacity-campaign-v1"
require_sha = "5266e70df6e79054ffdc1abfc64b300d9f6252f11e55eb340716ab346bc4c556"
if hashlib.sha256((V1 / "campaign.py").read_bytes()).hexdigest() != require_sha:
    raise RuntimeError("frozen helper changed")
spec = importlib.util.spec_from_file_location("architecture_base", V1 / "campaign.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
replace = base.replace


def between(s, start, end, new):
    a = s.index(start)
    b = s.index(end, a)
    return s[:a] + new + s[b:]


def common_profile(source):
    out = dict(source)
    name = "src/experimental_swift_reactor/control.rs"
    s = out[name].decode()
    for old, new in (("instruction_fuel: 100_000_000,", "instruction_fuel: 1_000_000_000,"),
                     ("execution_work: 1_000_000_000,", "execution_work: 8_000_000_000,"),
                     ("cache_work: 128000000,", "cache_work: 768_000_000,"),
                     ("deadline_ms: 30_000,", "deadline_ms: 600_000,")):
        s = replace(s, old, new)
    begin = s.index("    pub(crate) fn instruction_with_wasi(")
    end = s.index("    pub(crate) fn charge_fuel(", begin)
    section = s[begin:end]
    section = replace(section, "        Ok(())\n", '''        // Identical bounded external observation in both experiment arms.
        // Charged original instruction count, before dispatch effect. Not an oracle.
        #[cfg(test)]
        if matches!(self.instructions, 25_000_000 | 50_000_000 | 100_000_000) {
            let observed = self.usage(wasi);
            eprintln!("MIXER_PREFIX {{\\\"threshold\\\":{},\\\"instructions\\\":{},\\\"instruction_fuel\\\":{},\\\"cache_work\\\":{},\\\"execution_work\\\":{},\\\"host_calls\\\":{},\\\"elapsed_micros\\\":{},\\\"function\\\":{},\\\"offset\\\":{}}}",
                self.instructions, self.instructions, self.instruction_fuel, self.cache_work,
                self.execution_work, self.host_calls, observed.elapsed_micros,
                cursor.function.map(u64::from).unwrap_or(u64::MAX),
                cursor.offset.map(|n| n as u64).unwrap_or(u64::MAX));
        }
        Ok(())
''')
    s = s[:begin] + section + s[end:]
    out[name] = s.encode()
    name = "src/experimental_wasi/mod.rs"
    out[name] = replace(out[name].decode(), "deadline_ms: 30_000,", "deadline_ms: 600_000,").encode()
    name = "src/experimental_swift_reactor/cache_tests.rs"
    s = out[name].decode()
    s = replace(s, "assert!([64_000_000, 128_000_000].contains(&b.cache_work));", "assert_eq!(b.cache_work, 768_000_000);")
    s = replace(s, "assert_eq!((b.instruction_fuel, b.execution_work, b.deadline_ms), (100_000_000, 1_000_000_000, 30_000));", "assert_eq!((b.instruction_fuel, b.execution_work, b.deadline_ms), (1_000_000_000, 8_000_000_000, 600_000));")
    s = replace(s, "    plan_reuse_profile_envelopes_without_guest_execution();\n}", "    plan_reuse_profile_envelopes_without_guest_execution();\n    crate::experimental::cache::architecture_frozen_controls();\n}")
    out[name] = s.encode()
    # Run the same original frozen-mode controls in both arms. Only visibility
    # changes; these existing test bodies are not rewritten for the candidate.
    name = "src/experimental/cache/tests.rs"
    s = out[name].decode()
    for function in ("frozen_ir_parity_for_all_supported_opcode_shapes", "stale_token_nonce_and_owner_exhaustion_fail_closed"):
        s = replace(s, "fn " + function + "()", "pub(super) fn " + function + "()")
    out[name] = s.encode()
    out["src/experimental/cache/mod.rs"] += b'''\n#[cfg(test)]
pub(crate) fn architecture_frozen_controls() {
    tests::frozen_ir_parity_for_all_supported_opcode_shapes();
    tests::stale_token_nonce_and_owner_exhaustion_fail_closed();
}
'''
    return out


def parameterize(original, algorithm: bool):
    if type(algorithm) is not bool:
        raise ValueError("algorithm selection must be boolean")
    out = common_profile(base.parameterize(original, 256, 128_000_000))
    if not algorithm:
        return out
    name = "src/experimental_swift_reactor/cache.rs"
    s = out[name].decode()
    s = replace(s, "const RESIDENT_INDEX_CELLS: usize = RESIDENT_BUCKETS + RESIDENT_LINKS;", "const RESIDENT_INDEX_CELLS: usize = DENSE_FUNCTIONS;")
    s = replace(s, "    plans: &'a mut [Option<ScanPlan>],", "    plans: &'a mut [Option<ScanPlan>],\n    free_pins: &'a mut u64,")
    s = replace(s, "    pins: Vec<PinRecord>,", "    pins: Vec<PinRecord>,\n    free_pins: u64,", 2)
    s = replace(s, "            pins: Vec::new(),", "            pins: Vec::new(),\n            free_pins: 0,")
    s = replace(s, "                pins: take(&mut partial.pins),", "                pins: take(&mut partial.pins),\n                free_pins: partial.free_pins,")
    s = replace(s, "                    plans: &mut self.plans,", "                    plans: &mut self.plans,\n                    free_pins: &mut self.free_pins,")
    s = replace(s, "                    plans: &mut cache.plans,", "                    plans: &mut cache.plans,\n                    free_pins: &mut cache.free_pins,")
    s = replace(s, "\n                plans: &mut cache.plans,", "\n                plans: &mut cache.plans,\n                free_pins: &mut cache.free_pins,", 2)
    s = between(s, "fn resident_find(\n", "static NEXT_OWNER:", (HERE / "dense-index.rs").read_text() + "\n")
    a = s.index("impl CacheMode for SwiftMode {")
    start = s.index("    fn resident_lookup(\n", a)
    end = s.index("    fn scan(\n", start)
    s = s[:start] + (HERE / "dense-mode.rs").read_text() + "\n" + s[end:]
    # Every new scalar/borrow/return helper chain is included before admission.
    inventory = "        (3, size_of::<DenseIndexInventory>()),\n        (3, size_of::<DensePinInventory>()),\n"
    for function in ("compute_cache_cleanup_temporary_bytes", "compute_cache_construction_bytes", "compute_cache_operation_bytes"):
        start = s.index("const fn " + function + "()")
        at = s.index("    sum_named!(&[\n", start) + len("    sum_named!(&[\n")
        s = s[:at] + inventory + s[at:]
    # Precharge all initialization writes, then infallibly zero exact admitted
    # capacity. This is a bounded 160KB fill with stop checks on both sides.
    old = """        for _ in 0..RESIDENT_INDEX_CELLS {
            self.control.work(1)?;
            partial.index.push(0);
        }
"""
    new = """        self.control.work(RESIDENT_INDEX_CELLS as u64)?;
        partial.index.resize(RESIDENT_INDEX_CELLS, 0);
        self.control.check()?;
        self.control.work(1)?;
        partial.free_pins = dense_allowed_pins(budget.active_pins);
"""
    s = replace(s, old, new)
    # Test-only accessors expose private state for independently scanning it.
    marker = "    pub fn resident_index(cache: &SwiftFunctionCache) -> &[u16] {"
    accessors = """    pub fn dense_pin_mask(cache: &SwiftFunctionCache) -> u64 { cache.free_pins }
    pub fn dense_set_pin_mask(cache: &mut SwiftFunctionCache, value: u64) { cache.free_pins = value; }
    pub fn dense_pin_records(cache: &SwiftFunctionCache) -> Vec<(u64, usize)> { cache.pins.iter().map(|p| (p.nonce, p.entry)).collect() }
"""
    s = replace(s, marker, accessors + marker)
    out[name] = s.encode()

    name = "src/experimental/cache/borrowed.rs"
    s = out[name].decode()
    marker = "    // Defaults deliberately preserve the literal frozen lookup and work trace."
    s = replace(s, marker, (HERE / "pin-hooks.rs").read_text() + "\n" + marker)
    start = s.index("    let mut pin_slot = None;", s.index("pub(crate) fn pin<M: CacheMode>"))
    end = s.index("    meter.acquire_pin()?;", start)
    s = s[:start] + "    let pin_slot = M::available_pin(parts.pins, &mut parts.scratch, &mut meter)?;\n" + s[end:]
    s = replace(s, "pub(crate) fn release<M: CacheMode>(\n    parts: CacheParts<'_, M>,", "pub(crate) fn release<M: CacheMode>(\n    mut parts: CacheParts<'_, M>,")
    s = replace(s, "    if let Err(e) = operation.release_pin() {", "    if let Err(e) = M::validate_pin_release(parts.pins, &mut parts.scratch, pin.slot(), operation) { return Err((e, pin)); }\n    if let Err(e) = operation.release_pin() {")
    s = replace(s, "    parts.pins[pin.slot()] = PinRecord::default();", "    parts.pins[pin.slot()] = PinRecord::default();\n    M::pin_released(&mut parts.scratch, pin.slot());")
    s = replace(s, "    let pin = M::Pin::new(parts.owner, pin_slot, *parts.next_nonce);", "    M::pin_published(&mut parts.scratch, pin_slot);\n    let pin = M::Pin::new(parts.owner, pin_slot, *parts.next_nonce);")
    out[name] = s.encode()

    name = "src/experimental_swift_reactor/cache_tests.rs"
    s = out[name].decode()
    s = between(s, "fn resident_assert_index(cache:", "fn resident_seed(", (HERE / "dense-assert.rs").read_text() + "\n")
    s += "\n" + (HERE / "dense-controls.rs").read_text()
    out[name] = s.encode()
    return out


def expected_bounds():
    return {
        "validation_budget": {"source_bytes": 67_108_864, "metadata_bytes": 16_777_216, "scratch_bytes": 1_048_576, "work_credits": 512_000_000, "deadline_ms": 120_000},
        "run_budget": {"source_bytes": 67_108_864, "metadata_bytes": 16_777_216, "cache_bytes": 16_777_216, "cache_entry_bytes": 8_388_608,
                       "cache_entries": 256, "active_pins": 64, "cache_work": 768_000_000, "frames": 64, "values": 16_384,
                       "controls": 4096, "memory_pages": 768, "state_bytes": 134_217_728, "combined_bytes": 268_435_456,
                       "instruction_fuel": 1_000_000_000, "execution_work": 8_000_000_000, "host_calls": 32_768, "deadline_ms": 600_000},
        "wasi_budget": {"calls": 32_768, "iovecs": 64, "one_transfer_bytes": 65_536, "transfer_bytes": 4_194_304, "log_bytes": 65_536, "work": 32_000_000, "deadline_ms": 600_000},
        "wasi_grants": {"monotonic": True, "realtime": True, "secure_random": True, "stderr": True, "stdout": True},
    }
