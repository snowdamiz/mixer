#!/usr/bin/env python3
"""Pure private-copy experiment: identical observation window, 256/512 residents."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PRIOR = HERE.parent / "swift-frame-pin-admission-candidate"
PRIOR_SEAL = "c5d0e8b29625e09bc5bc6ef73094edc4aebdc03ee5d4e27cafa34b5eda05bd6a"
CACHE_WORK = 4_000_000_000
INSTRUCTION_FUEL = 2_000_000_000
EXECUTION_WORK = 16_000_000_000
THRESHOLDS = (25_000_000, 50_000_000, 100_000_000, 250_000_000, 500_000_000,
              750_000_000, 1_000_000_000, 1_250_000_000, 1_500_000_000, 1_750_000_000)


def bound_prior():
    raw = (PRIOR / "seal.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != PRIOR_SEAL:
        raise RuntimeError("closed 128-frame source seal changed")
    for name, row in json.loads(raw)["files"].items():
        data = (PRIOR / name).read_bytes()
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise RuntimeError("closed 128-frame source member changed: " + name)


bound_prior()
spec = importlib.util.spec_from_file_location("closed_framepin_candidate", PRIOR / "candidate.py")
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
replace = prior.replace


def residents(capacity):
    if type(capacity) is not bool:
        raise ValueError("capacity selection must be boolean")
    return 512 if capacity else 256


def expected_bounds(capacity=False):
    bounds = prior.expected_bounds()
    bounds["run_budget"].update(cache_entries=residents(capacity), cache_work=CACHE_WORK,
        instruction_fuel=INSTRUCTION_FUEL, execution_work=EXECUTION_WORK)
    return bounds


def parameterize(original, capacity):
    n = residents(capacity)
    bound_prior()
    out = prior.parameterize(original, True)  # Same previously executed dense policy in both arms.
    def edit(name, old, new, count=1):
        out[name] = replace(out[name].decode(), old, new, count).encode()
    control = "src/experimental_swift_reactor/control.rs"
    for old, new in (("cache_work: 768_000_000,", "cache_work: 4_000_000_000,"),
        ("instruction_fuel: 1_000_000_000,", "instruction_fuel: 2_000_000_000,"),
        ("execution_work: 8_000_000_000,", "execution_work: 16_000_000_000,")):
        edit(control, old, new)
    edit(control, "25_000_000 | 50_000_000 | 100_000_000",
        " | ".join(f"{value:_}" for value in THRESHOLDS))
    tests = "src/experimental_swift_reactor/cache_tests.rs"
    for old, new in (("assert_eq!(b.cache_work, 768_000_000);", "assert_eq!(b.cache_work, 4_000_000_000);"),
        ("(1_000_000_000, 8_000_000_000, 600_000)", "(2_000_000_000, 16_000_000_000, 600_000)"),
        ("(768_000_000, 1_000_000_000, 8_000_000_000, 600_000)", "(4_000_000_000, 2_000_000_000, 16_000_000_000, 600_000)")):
        edit(tests, old, new)
    if capacity:
        edit(control, "MAX_RESERVATION_TICKETS: usize = 278;", "MAX_RESERVATION_TICKETS: usize = 534;")
        edit(control, "cache_entries: 256,", "cache_entries: 512,")
        edit("src/experimental/cache/mod.rs", "const MAX_ENTRIES: usize = 256;", "const MAX_ENTRIES: usize = 512;")
        edit("src/experimental_swift_reactor/cache.rs", "const RESIDENT_LINKS: usize = 256;", "const RESIDENT_LINKS: usize = 512;")
        # Only selected-profile test expectations change. Keep original bodies,
        # allocation/capacity/identity negatives and full target/oracle intact.
        for old, new, count in (
            ("let mut seen = [false; 256];", "let mut seen = [false; 512];", 1),
            ("fixture(0,&[0,0x0b],296)", "fixture(0,&[0,0x0b],552)", 1),
            ("for f in 34..290 {", "for f in 34..546 {", 1),
            ("resident.live.cache_entries.current,256", "resident.live.cache_entries.current,512", 1),
            ("resident.reservations.live_tickets,277", "resident.reservations.live_tickets,533", 1),
            ("assert!([64, 128, 256].contains(&n));", "assert!([64, 128, 256, 512].contains(&n));", 1),
            ("inspection::corrupt_index(&mut cache, 34, 257)", "inspection::corrupt_index(&mut cache, 34, 513)", 1),
            ("(256, 128, 128)", "(512, 128, 128)", 1),
            ("assert_eq!(MAX_RESERVATION_TICKETS, 278);", "assert_eq!(MAX_RESERVATION_TICKETS, 534);", 1),
            ("fixture(0, &[0, 0x0b], 296)", "fixture(0, &[0, 0x0b], 552)", 1),
            ("for function in 34..290 {", "for function in 34..546 {", 1),
            ("inspection::resident_index(&cache)[289], 256", "inspection::resident_index(&cache)[545], 512", 1),
            ("c.usage(None).live.cache_entries.current, 256", "c.usage(None).live.cache_entries.current, 512", 1),
        ):
            edit(tests, old, new, count)
    out[tests] += b"\n" + (HERE / "capacity-controls.rs").read_bytes()
    out["src/experimental_swift_reactor/control_tests.rs"] += b"\n" + (HERE / "scalar-guards.rs").read_bytes()
    return out
