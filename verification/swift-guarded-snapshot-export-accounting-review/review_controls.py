#!/usr/bin/env python3
"""Independent finite arithmetic/source-data review; no exporter authority.

Never imports or executes producer controls, Rust, or a product/runtime entry.
Inputs are read-only copies captured from the explicitly frozen preparation.
"""
from pathlib import Path
import hashlib
import json
import platform
import sys

HERE = Path(__file__).resolve().parent
U64 = (1 << 64) - 1
U32 = (1 << 32) - 1


def read(path):
    return (HERE / "inputs" / path).read_text()


def load(path):
    return json.loads(read(path))


def checked_add(a, b):
    if not (0 <= a <= U64 and 0 <= b <= U64 and a <= U64 - b):
        raise ValueError("u64 addition overflow")
    return a + b


def checked_mul(a, b):
    if not (0 <= a <= U64 and 0 <= b <= U64 and (not b or a <= U64 // b)):
        raise ValueError("u64 multiplication overflow")
    return a * b


def refused(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


def fields(source, name):
    # Deliberately only a finite source-data inventory, never a parser,
    # compiler, validator, or authorization route.
    part = source.split("struct " + name, 1)[1].split("{", 1)[1].split("}", 1)[0]
    return [line.strip().removeprefix("pub ").split(":", 1)[0]
            for line in part.splitlines() if ":" in line and not line.lstrip().startswith("//")]


def policy_value(source, name):
    part = source.split("pub fn " + name + "(", 1)[1].split("\n    }", 1)[0]
    if "Self::SwiftReactorExperimentV1 => " in part:
        expression = part.split("Self::SwiftReactorExperimentV1 => ", 1)[1].split(",", 1)[0]
    else:
        expression = part.split("-> usize {", 1)[1].strip()
    factors = expression.replace("_", "").split("*")
    result = 1
    for factor in factors:
        result *= int(factor.strip())
    return result


def buffer_charge(count, capacity, width, charged, category=2):
    if count > capacity or category != 2 or checked_mul(capacity, width) != charged:
        raise ValueError("invalid native Buffer inventory")
    return charged


def metadata_total(inventories):
    total = 664  # inherited current accepted native identity; not a new measurement
    for inventory in inventories:
        total = checked_add(total, buffer_charge(*inventory))
    if total > 16 * 1024 * 1024:
        raise ValueError("metadata ceiling")
    return total


def main():
    results = []
    def record(name, detail):
        results.append({"id": name, "passed": True, "detail": detail})

    manifest = load("input-manifest.json")
    for member in manifest["copied_members"]:
        data = (HERE / "inputs" / member["copy_path"]).read_bytes()
        assert len(data) == member["bytes"]
        assert hashlib.sha256(data).hexdigest() == member["sha256"]
    assert manifest["source_roster_all_entries_match_accepted144_manifest"]
    record("A01-input-custody", {"copied_members": len(manifest["copied_members"]),
           "producer_seal_sha256": manifest["producer_seal_sha256"],
           "all14_source_roster_entries_match_frozen_members": manifest["source_roster_all_entries_match"]})

    swift = read("source/swift.rs")
    metadata = read("source/metadata.rs")
    policy = read("source/policy.rs")
    account = read("source/account.rs")
    proof = fields(swift, "ValidatedSwiftReactor")
    assert proof == ["source", "metadata", "policy", "imports", "usage", "observations"]
    usage = fields(swift, "SwiftValidationUsage")
    observations = fields(swift, "SwiftReactorObservations")
    assert len(usage) == 10 and len(observations) == 18
    assert "std::mem::size_of::<ValidatedSwiftReactor>()" in swift
    assert "meter.reserve(Resource::Source, input.len(), cursor)?;" in swift
    assert "source.capacity() != input.len()" in swift
    record("A02-all6-proof-fields", {"fields": proof, "usage_fields": usage,
           "observation_fields": observations, "wire_observation_words": 20,
           "coverage": "six fields have explicit proposed wire locations; metadata scalar state separately reviewed"})

    buffer_names = ["signatures", "parameters", "imports", "functions", "globals", "exports", "data", "elements"]
    metadata_fields = fields(metadata, "Metadata")
    assert metadata_fields == buffer_names + ["memory", "table", "declarations", "instructions"]
    record_fields = {name: fields(metadata, name) for name in
                     ["Span", "Signature", "Import", "Function", "Global", "Export", "Segment", "SwiftDeclaration"]}
    expected = {"Span": ["offset", "bytes"], "Signature": ["first", "count", "result"],
                "Import": ["pub(super) module", "pub(super) name", "type_index"],
                "Function": ["body", "type_index"], "Global": ["ty", "mutable", "initializer"],
                "Export": ["pub(super) name", "pub(super) kind", "pub(super) index"],
                "Segment": ["payload", "destination", "count"],
                "SwiftDeclaration": ["memory_maximum", "table_maximum", "memory_offset", "table_offset"]}
    assert record_fields == expected
    assert "values: Vec<T>" in account and "charged: usize" in account and "category: Resource" in account
    assert "checked_mul(std::mem::size_of::<T>())" in account
    assert "meter.reserve(self.category, bytes, cursor)?;" in account
    assert "next.capacity() != capacity" in account
    assert "meter.release(self.category, self.charged);" in account
    record("A03-all8-buffers", {"buffers": buffer_names, "metadata_scalars": metadata_fields[8:],
           "record_fields": record_fields, "native_element_bytes_inherited_not_remeasured": [12, 1, 20, 12, 12, 16, 16, 16],
           "native_charge_rule": "actual Vec capacity * actual native element size; metadata category; count <= capacity"})

    source_cap = policy_value(policy, "module_bytes")
    all_imports = read("source/descriptor.rs").split("pub const ALL: [Self; 34] = [", 1)[1].split("];", 1)[0]
    assert all_imports.count("Self::") == 34 and "if m.imports.len() != 34" in swift
    caps = [policy_value(policy, n) for n in ["types", "type_parameters_total"]]
    caps += [34, policy_value(policy, "functions") - 34, policy_value(policy, "globals")]
    caps += [policy_value(policy, name) for name in ["exports", "data_segments", "element_segments"]]
    words = [3, 1, 5, 3, 4, 4, 4, 4]
    encoded_sections = [checked_mul(checked_mul(cap, width), 8) for cap, width in zip(caps, words)]
    maximum = 2560
    for byte_count in [source_cap] + encoded_sections:
        maximum = checked_add(maximum, byte_count)
    assert maximum == 69_765_152
    assert 2560 <= 4096 and 1600 + 9 * 64 == 2176 and 2176 + 34 * 8 == 2448
    blocks, final_block = divmod(maximum, 4096)
    blocks += bool(final_block)
    record("A04-source-derived-wire-envelope", {"source_cap": source_cap,
           "logical_caps": dict(zip(buffer_names, caps)), "wire_record_words": dict(zip(buffer_names, words)),
           "maximum_section_bytes": dict(zip(buffer_names, encoded_sections)),
           "header_bytes": 2560, "complete_maximum_bytes": maximum,
           "maximum_continuous_blocks": blocks, "last_block_bytes": final_block,
           "maximum_write_attempts_at32_perblock": blocks * 32,
           "scope": "independent logical envelope only, no allocation, work grant, reachability, or RSS claim"})

    assert checked_add(U64 - 1, 1) == U64
    assert refused(lambda: checked_add(U64, 1))
    assert checked_mul(U64, 1) == U64
    assert refused(lambda: checked_mul(U64, 2))
    assert checked_add(U32, 0) == U32
    assert checked_add(source_cap - 1, 1) == source_cap
    assert checked_add(source_cap, 1) > source_cap
    record("A05-width-and-overflow-controls", {"cases": 7, "u32_widens_losslessly": True,
           "native_target": "selected 64-bit little-endian aarch64 Apple; different layout must be selected",
           "scope": "independent arithmetic model only; future exporter checked conversions not executed"})

    capacities = [512, 8192, 64, 131072, 8192, 4096, 4096, 4096]
    native_widths = [12, 1, 20, 12, 12, 16, 16, 16]
    inventories = [(n, c, w, c * w) for n, c, w in zip(caps, capacities, native_widths)]
    retained = metadata_total(inventories)
    assert retained == 1_884_056
    assert buffer_charge(79_966, 131_072, 12, 1_572_864) == 1_572_864
    assert refused(lambda: buffer_charge(5, 4, 12, 48))
    assert refused(lambda: buffer_charge(4, 4, 12, 47))
    assert refused(lambda: buffer_charge(4, 4, 12, 48, 1))
    assert refused(lambda: buffer_charge(1, U64, 12, 0))
    assert refused(lambda: metadata_total([(1, 16_777_216, 1, 16_777_216)]))
    record("A06-capacity-charge-controls", {"cases": 7,
           "independent_hypothetical_inventory_bytes": retained,
           "capacity_above_logical_cap_allowed": {"functions_count": 79966, "capacity": 131072},
           "native_proof_bytes_inherited": 664,
           "scope": "synthetic arithmetic; not a claim that a genuine accepted proof reaches all logical maxima together"})

    storage = load("storage-plan.json")
    assert storage["unit_foundation_unchanged"] == 366896
    assert storage["production_foundation_unchanged"] == 366312
    assert 300000 < storage["unit_foundation_unchanged"]
    assert 300000 < storage["production_foundation_unchanged"]
    assert "refusal-path evidence only" in storage["existing400000fixture"]
    assert storage["no_actual_reservation_performed"]
    roster = storage["roster"]
    assert len(roster) == 8
    assert all(place["count"] > 0 for group in roster for place in group["proposed_distinct_places"])
    record("A07-source-place-and-original-grants", {"groups": [{"type": g["proposed_type"],
           "lifetime": g["lifetime"], "named_places": sum(p["count"] for p in g["proposed_distinct_places"])} for g in roster],
           "original300000": "refuses both inherited foundation floors before exporter additions",
           "original400000fixture": "refusal-path only; no positive relabelling",
           "future_host_positive_grant": "requires fresh complete measured source-place requirement and separate root selection",
           "new_measurement_or_reservation": False})

    contract = read("contract.md")
    clauses = ["before allocation or output I/O", "before guard creation", "all simultaneous moves",
               "No independent untracked ledger", "before it creates them or acquires",
               "No export failure retries construction", "no mutable RuntimeControl access or new ledger operation",
               "read-only check contract", "does not reenter"]
    # The last concept uses the explicit actual spelling in the proposed text.
    clauses[-1] = "it must not reenter"
    assert all(clause in contract for clause in clauses)
    control = read("source/control.rs")
    assert "pub(crate) fn check(&mut self" in control
    assert "pub(crate) fn work(" in control
    assert "self.work_with_wasi(component, credits, cursor, None)" in control
    assert "self.cancellation.clone()" in control
    assert "pub(crate) fn deadline(&self)" in control
    record("A08-work-lifetime-reentrancy-and-stop-contract", {
           "source_fact": "existing work/check mutate RuntimeControl; current cancellation accessor clones handle; deadline reads immutably",
           "proposed_safety_boundary": "admit all storage/work before sole immutable guard; no ledger mutation or construction reentry while live",
           "pending": ["concrete checked work formula and charging category", "per-place native measurement/simultaneous floor",
                       "read-only cancellation/deadline observation and bounded check schedule",
                       "accounted cancellation handle/backing if cloned", "actual failure/cleanup/return move accounting"],
           "conclusion": "explicit selection/implementation obligations, not claimed implemented admission"})

    source_roster = load("source-roster.json")
    cache_entry = next(e for e in source_roster["sources"] if e["accepted_member_path"].endswith("/cache.rs"))
    prepare_fact = next(f for f in cache_entry["facts"] if f["token"] == "pub(crate) fn prepare(")
    cache_source = read("source/cache.rs")
    prepare_token = "    pub(crate) fn prepare<'a>("
    prepare_line = cache_source[:cache_source.index(prepare_token)].count("\n") + 1
    assert prepare_line == 1473
    assert prepare_fact["line"] is None and prepare_fact["status"] == "planned accessor absent in actual source"
    assert "SwiftFunctionCache::prepare(control,wasi,&adopted,CONSTRUCTION_CURSOR_V1)" in read("source/initial_profile_v1.rs")
    source_roster_findings = [{"id": "SR01", "severity": "documentation correction required",
        "producer_path": "source-roster.json", "actual_source_path": cache_entry["path"],
        "actual_source_line": prepare_line,
        "problem": "Existing generic prepare function is marked as a planned absent accessor because roster token omits its lifetime generic.",
        "expected_correction": "Use existing pub(crate) fn prepare<'a> at line1473, remove planned-absent status, preserve original shared admission role.",
        "scope": "source-roster accuracy only; no product/runtime defect alleged"}]
    output = {"schema": 1, "status": "finite-independent-accounting-controls-pass-with-source-roster-finding",
              "tool": {"python": platform.python_version(), "implementation": platform.python_implementation()},
              "controls": results, "control_groups": len(results), "actionable_accounting_findings": [],
              "actionable_source_roster_findings": source_roster_findings,
              "limitations": ["source-data/arithmetic only", "no product or runtime tests/builds",
                              "no new native size measurement", "no actual exporter or operational admission",
                              "no semantic validation, custody, replay, release, publication or GA authority",
                              "no producer import/execution", "no Git/native/UI/capture/process inventories"]}
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
