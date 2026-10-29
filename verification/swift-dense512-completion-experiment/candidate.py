#!/usr/bin/env python3
"""One private dense512 completion hypothesis; no canonical engine edits."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / "swift-cachework-128-experiment"
PRIOR_SEAL = "dce182dba6c4e4bf38738b486276596c7b0cbc17c798e8780ebd19287bced0d0"
THRESHOLDS = (25_000_000, 50_000_000, 100_000_000, 250_000_000, 500_000_000,
              750_000_000, 1_000_000_000, 1_250_000_000, 1_500_000_000, 1_750_000_000)


def bound_prior():
    raw = (PRIOR / "seal.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != PRIOR_SEAL:
        raise RuntimeError("closed capacity-window source seal changed")
    for name, row in json.loads(raw)["files"].items():
        data = (PRIOR / name).read_bytes()
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise RuntimeError("closed capacity-window source member changed: " + name)


bound_prior()
spec = importlib.util.spec_from_file_location("closed_capacity_window_candidate", PRIOR / "candidate.py")
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
replace = prior.replace


def selected(capacity):
    if capacity is not True:
        raise ValueError("only the dense512 completion profile is admitted")


def expected_bounds(capacity=True):
    selected(capacity)
    bounds = prior.expected_bounds(True)
    bounds["run_budget"].update(instruction_fuel=4_000_000_000, deadline_ms=1_200_000)
    bounds["wasi_budget"]["deadline_ms"] = 1_200_000
    return bounds


def parameterize(original, capacity=True):
    selected(capacity)
    bound_prior()
    out = prior.parameterize(original, True)
    def edit(name, old, new, count=1):
        out[name] = replace(out[name].decode(), old, new, count).encode()
    control = "src/experimental_swift_reactor/control.rs"
    edit(control, "instruction_fuel: 2_000_000_000,", "instruction_fuel: 4_000_000_000,")
    edit(control, "deadline_ms: 600_000,", "deadline_ms: 1_200_000,")
    edit("src/experimental_wasi/mod.rs", "deadline_ms: 600_000,", "deadline_ms: 1_200_000,")
    edit("src/experimental_swift_reactor/cache_tests.rs",
        "2_000_000_000, 16_000_000_000, 600_000", "4_000_000_000, 16_000_000_000, 1_200_000", 2)
    # Replace only the previously appended finite guard, preserving its original
    # seventeen-dimension, cumulative, overflow and consuming-cleanup controls.
    edit("src/experimental_swift_reactor/control_tests.rs",
        (PRIOR / "scalar-guards.rs").read_text(), (HERE / "scalar-guards.rs").read_text())
    return out
