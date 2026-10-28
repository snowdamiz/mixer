#!/usr/bin/env python3
"""Pure copied-source proposal. No compiler, runtime, dispatch or publication."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PRIOR = HERE.parent / "swift-execution-architecture-correction"
PRIOR_SEAL = "4efa21ab9e7bf43cec647c760bdacf6c3e5b2be944976240ec186c738370a6d2"


def bound_prior():
    raw = (PRIOR / "seal.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != PRIOR_SEAL:
        raise RuntimeError("prior source seal changed")
    for name, row in json.loads(raw)["files"].items():
        data = (PRIOR / name).read_bytes()
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise RuntimeError("prior source packet changed: " + name)


bound_prior()
spec = importlib.util.spec_from_file_location("framepin_frozen_candidate", PRIOR / "candidate.py")
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
replace = prior.replace


def parameterize(original, algorithm):
    if type(algorithm) is not bool:
        raise ValueError("algorithm selection must be boolean")
    bound_prior()
    out = prior.parameterize(original, algorithm)
    def edit(name, old, new, count=1):
        out[name] = replace(out[name].decode(), old, new, count).encode()
    control = "src/experimental_swift_reactor/control.rs"
    edit(control, "active_pins: 64,", "active_pins: 128,")
    edit(control, "frames: 64,", "frames: 128,")
    # Adoption still rejects any budget wider than this copied private default;
    # frame publication checks both the selected limit and exact arena capacity.
    edit("src/experimental_swift_reactor/frame_operations.rs",
         "budget().frames.min(64)", "budget().frames.min(128)")
    cache = "src/experimental_swift_reactor/cache.rs"
    tests = "src/experimental_swift_reactor/cache_tests.rs"
    if algorithm:
        s = out[cache].decode()
        for old, new, count in (
            ("free_pins: &'a mut u64", "free_pins: &'a mut [u64; 2]", 1),
            ("free_pins: u64", "free_pins: [u64; 2]", 2),
            ("free_pins: 0,", "free_pins: [0; 2],", 1),
            ("mask: u64, permitted: u64, slot: usize", "mask: [u64; 2], permitted: [u64; 2], word: usize, slot: usize", 1),
            ("free_bits: &'static mut u64", "free_bits: &'static mut [u64; 2]", 1),
            ("pub fn dense_pin_mask(cache: &SwiftFunctionCache) -> u64", "pub fn dense_pin_mask(cache: &SwiftFunctionCache) -> [u64; 2]", 1),
            ("pub fn dense_set_pin_mask(cache: &mut SwiftFunctionCache, value: u64)", "pub fn dense_set_pin_mask(cache: &mut SwiftFunctionCache, value: [u64; 2])", 1),
            ("self.control.work(1)?;\n        partial.free_pins", "self.control.work(2)?;\n        partial.free_pins", 1),
        ):
            s = replace(s, old, new, count)
        start = s.index("fn dense_allowed_pins(")
        end = s.index("fn dense_audit(", start)
        s = s[:start] + (HERE / "dense-pins.rs").read_text().split("// MODE METHODS\n")[0] + s[end:]
        start = s.index("    fn available_pin(", s.index("impl CacheMode for SwiftMode"))
        end = s.index("    fn resident_lookup(", start)
        s = s[:start] + (HERE / "dense-pins.rs").read_text().split("// MODE METHODS\n")[1] + s[end:]
        # Existing three-copy DensePinInventory terms recalculate the complete
        # helper storage at cleanup, construction and operation admission.
        out[cache] = s.encode()
        s = out[tests].decode()
        s = replace(s, "let mut expected = 0u64;", "let mut expected = [0u64; 2];")
        s = replace(s, "expected |= 1u64 << slot;", "expected[slot / 64] |= 1u64 << (slot % 64);")
        for old, new in (
            ("held | (1u64 << 63)", "[held[0], held[1] | (1u64 << 63)]"),
            ("held ^ 3", "[held[0] ^ 3, held[1]]"),
            ("dense_set_pin_mask(&mut cache, 0)", "dense_set_pin_mask(&mut cache, [0; 2])"),
            ("held | 1", "[held[0] | 1, held[1]]"),
            ("(256, 64, 64)", "(256, 128, 128)"),
            ("free_pin_bytes=8", "free_pin_bytes=16"),
            ("pin_bitmap_bytes=8", "pin_bitmap_bytes=16"),
        ):
            s = replace(s, old, new)
        s += "\n" + (HERE / "dense-tests.rs").read_text()
        out[tests] = s.encode()
    # Retain all original tests, updating only selected-profile expectations.
    s = out[tests].decode()
    for old, new in (
        ("assert_eq!(SwiftRunBudget::default().active_pins, 64);", "assert_eq!(SwiftRunBudget::default().active_pins, 128);"),
        ("// A larger resident table must not create a 65th active pin.", "// This copied profile must not create a 129th active pin."),
        ("for _ in 0..64 { pins.push(pin(&mut cache, &mut c, 35, None).unwrap()); }", "for _ in 0..128 { pins.push(pin(&mut cache, &mut c, 35, None).unwrap()); }"),
        ("assert_eq!(c.usage(None).live.active_pins.current, 64);", "assert_eq!(c.usage(None).live.active_pins.current, 128);"),
        ("(16 << 20, 8 << 20, 64)", "(16 << 20, 8 << 20, 128)"),
    ):
        s = replace(s, old, new)
    original_controls = (
        "dense_campaign_retention_churn_and_pin_bound();\n    dense_campaign_map_corruption_and_duplicate_prevention();\n    dense_campaign_pin_identity_mask_and_release();\n    dense_campaign_every_replacement_and_hit_failure_prefix();\n    dense_campaign_constructor_allocation_and_header_lifetimes();\n    dense_campaign_full_geometry_and_conservative_envelope();"
        if algorithm else
        "campaign_retention_churn_and_pin_bound();\n    campaign_full_chain_cycle_and_high_link();\n    campaign_original_failure_atomicity_and_allocation_controls();\n    campaign_budget_geometry_and_reservations();"
    )
    s += "\n#[test]\nfn framepin_campaign_original_controls_and_geometry() {\n    " + original_controls + "\n}\n"
    s += "\n" + (HERE / "cache-tests.rs").read_text()
    out[tests] = s.encode()
    out["src/experimental_swift_reactor/frame_operations_tests.rs"] += b"\n" + (HERE / "frame-tests.rs").read_bytes()
    out["src/experimental_swift_reactor/execution_tests.rs"] += b"\n" + (HERE / "construction-tests.rs").read_bytes()
    return out


def expected_bounds():
    bounds = prior.expected_bounds()
    bounds["run_budget"].update(active_pins=128, frames=128)
    return bounds
