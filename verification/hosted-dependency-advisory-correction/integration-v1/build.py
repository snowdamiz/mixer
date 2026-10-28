#!/usr/bin/env python3
"""Derive a proposed integration packet from retained Mix evidence; no runtime."""
import time
START = time.monotonic()
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
PACKET = HERE.parent
ROOT = PACKET.parents[1]
ATTEMPT = PACKET / "resolution-v4/attempts/fe41774456c8435e841b30f9b48cb7ec"
SELECTED = {"bandit": "1.14.0", "jose": "1.11.13"}


def read(path):
    assert time.monotonic() - START < 20, "20s source-preparation bound"
    data = path.read_bytes()
    assert len(data) <= 1_048_576, str(path)
    return data


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(name, value):
    data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    assert len(data) <= 1_048_576
    (HERE / name).write_bytes(data)


def lock_entries(raw):
    lines = raw.splitlines(keepends=True)
    assert lines[0] == b"%{\n" and lines[-1] == b"}\n"
    entries = {}
    pattern = rb'  "([a-z0-9_]+)": (\{:hex, :([a-z0-9_]+), "([0-9.]+)", "([a-f0-9]{64})", .+, "hexpm", "([a-f0-9]{64})"\}),\n'
    for line in lines[1:-1]:
        match = re.fullmatch(pattern, line)
        assert match and match[1] == match[3]
        name = match[1].decode()
        assert name not in entries
        entries[name] = {"line": line.decode(), "entry_sha256": sha(line),
                         "version": match[4].decode(), "inner_checksum": match[5].decode(),
                         "outer_checksum": match[6].decode()}
    assert len(entries) == 21
    return entries


def main():
    source_names = ["hosted/mix.exs", "hosted/mix.lock", "THIRD_PARTY.yml"]
    protected_names = [".github/workflows/hosted.yml", "hosted/lib/mixer_hosted/browser_auth/store.ex",
                       "hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex",
                       "hosted/test/mixer_hosted/identity/key_owner_inflight_lifecycle_test.exs",
                       "hosted/test/mixer_hosted/browser_auth/run_callback_fixture.py"]
    before = {name: sha(read(ROOT / name)) for name in source_names + protected_names}
    for base, seal in [(PACKET, "preparation-seal.sha256"),
                       (PACKET / "resolution-v2", "seal.sha256"),
                       (PACKET / "resolution-v3", "seal.sha256"),
                       (PACKET / "resolution-v4", "seal.sha256")]:
        for line in read(base / seal).decode().splitlines():
            expected, name = line.split("  ", 1)
            assert sha(read(base / name)) == expected, name

    receipt_raw = read(ATTEMPT / "receipt.json")
    receipt = json.loads(receipt_raw)
    assert receipt["status"] == "resolved_two_pins_only" and receipt["errors"] == []
    assert len(receipt["commands"]) == 5 and all(c["returncode"] == 0 and c["closed"] for c in receipt["commands"])
    assert receipt["groups_closed"] and receipt["scratch_removed"] and not Path(receipt["scratch"]).exists()
    assert not receipt["cancelled_through_cutoff"] and receipt["ended_elapsed_seconds"] < 55
    retained = {}
    for name, expected in receipt["retained_output_hashes"].items():
        actual = sha(read(ATTEMPT / name))
        assert actual == expected, name
        retained[name] = actual
    actual_lock = read(ATTEMPT / "actual-mix.lock")
    assert sha(actual_lock) == receipt["retained_lock_sha256"]
    before_lock = read(PACKET / "inputs/mix.lock")
    old, new = lock_entries(before_lock), lock_entries(actual_lock)
    assert old.keys() == new.keys()
    changed = [name for name in new if old[name]["line"] != new[name]["line"]]
    assert sorted(changed) == sorted(SELECTED)
    recorded_inventory = json.loads(read(ATTEMPT / "lock-inventory.json"))
    assert recorded_inventory["verified"] and recorded_inventory["entry_count"] == 21
    for name, item in new.items():
        assert {k: value for k, value in item.items() if k != "line"} == recorded_inventory["entries"][name]
        if name in SELECTED:
            assert item["version"] == SELECTED[name]
        else:
            assert item["line"] == old[name]["line"]
    candidates = json.loads(read(ROOT / "verification/hosted-dependency-advisory-review/upgrade-candidates.json"))
    for candidate in candidates:
        assert new[candidate["package"]]["outer_checksum"] == candidate["metadata"]["checksum"]

    # No lock tuple/checksum is generated here: preserve the actual Mix bytes.
    proposed_mix = read(PACKET / "proposal/mix.exs")
    pins = dict(re.findall(r'\{:(\w+), "== ([^"]+)"\}', proposed_mix.decode()))
    assert len(pins) == 9 and all(new[name]["version"] == value for name, value in pins.items())
    assert b'elixir: "== 1.20.4"' in proposed_mix
    bandit = next(c for c in candidates if c["package"] == "bandit")
    requirements = bandit["metadata"]["requirements"]
    declared = {name: requirement for name, requirement in re.findall(r'\{:(\w+), "([^"]+)", \[hex:', new["bandit"]["line"])}
    assert declared == {name: item["requirement"] for name, item in requirements.items()}
    assert requirements.keys() <= new.keys()
    assert all(new[name]["version"] == old[name]["version"] for name in requirements)

    third_original = read(ROOT / "THIRD_PARTY.yml").decode()
    third_proposal = read(PACKET / "proposal/THIRD_PARTY.yml").decode()
    inventory_path = str((HERE / "dependencies.json").relative_to(ROOT))
    assert third_proposal.count("inventory_receipt: verification/hosted-dependency-advisory-correction/dependencies.json") == 2
    third_proposal = third_proposal.replace("inventory_receipt: verification/hosted-dependency-advisory-correction/dependencies.json",
                                            "inventory_receipt: " + inventory_path)
    for name, version in SELECTED.items():
        block = third_proposal.split("  - name: Hex " + name + "\n", 1)[1].split("  - name:", 1)[0]
        assert 'version: "' + version + '"' in block and "inventory_receipt: " + inventory_path in block

    proposals = {"hosted/mix.exs": proposed_mix, "hosted/mix.lock": actual_lock,
                 "THIRD_PARTY.yml": third_proposal.encode()}
    assert read(ROOT / "hosted/mix.lock") == before_lock
    assert read(ROOT / "hosted/mix.exs") == read(PACKET / "inputs/mix.exs")
    assert third_original.encode() == read(PACKET / "inputs/THIRD_PARTY.yml")
    patches = []
    application = []
    for name, data in proposals.items():
        target = HERE / "proposed" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        patches.extend(difflib.unified_diff(read(ROOT / name).decode().splitlines(keepends=True),
                                          data.decode().splitlines(keepends=True), fromfile="a/" + name, tofile="b/" + name))
        application.append({"canonical_path": name, "proposed_path": str(target.relative_to(ROOT)),
                            "required_before_sha256": before[name], "proposed_sha256": sha(data)})
    (HERE / "canonical.patch").write_text("".join(patches))

    dependencies = []
    for name, item in new.items():
        declared_name = "Mint" if name == "mint" else "Hex " + name
        block = third_proposal.split("  - name: " + declared_name + "\n", 1)[1].split("  - name:", 1)[0]
        license_match = re.search(r"^    license: (.+)$", block, re.M)
        dependencies.append({"name": name, "version": item["version"], "origin": "https://hex.pm/packages/" + name,
                             "checksum": item["inner_checksum"], "outer_checksum": item["outer_checksum"],
                             "lock_entry_sha256": item["entry_sha256"], "previous_version": old[name]["version"],
                             "previous_lock_entry_sha256": old[name]["entry_sha256"],
                             "selection": "selected-upgrade" if name in SELECTED else "unchanged",
                             "declared_license": license_match[1] if license_match else None})
    dependency_record = {"schema": "mixer.hosted-dependencies.actual-lock-integration.v1",
                         "derivation": "Source-only projection of actual Mix-generated retained lock; no tuple or checksum synthesized.",
                         "dependencies": dependencies, "entry_count": 21, "selected": SELECTED, "unchanged_count": 19,
                         "provenance": {"attempt": str(ATTEMPT.relative_to(ROOT)), "receipt_sha256": sha(receipt_raw),
                                        "actual_lock_sha256": sha(actual_lock), "old_lock_sha256": sha(before_lock),
                                        "controller_sha256": receipt["controller_sha256"], "plan_sha256": receipt["plan_sha256"],
                                        "retained_output_hashes": retained},
                         "resolution": {"commands": [{"argv": c["argv"], "returncode": c["returncode"]} for c in receipt["commands"]],
                                        "elapsed_seconds": receipt["ended_elapsed_seconds"], "groups_closed": True, "scratch_removed": True,
                                        "Elixir_Mix": "1.20.4", "OTP_patch_bound_install_manifest": "29.1.1", "Hex_bound_archive_manifest": "2.5.1",
                                        "signed_registry_TLS_origin_checks": "enabled in recorded sanitized environment"},
                         "limitations": ["Dependency resolution and source derivation only; no compiler/product tests or new network call in this integration preparation.",
                                         "Private Mix rebar3 bootstrap was reported during the accepted resolver operation; no rebar compilation command selected and scratch removed.",
                                         "Declared licenses come from THIRD_PARTY.yml; new package notice files were not retained/qualified by this lock-only operation.",
                                         "Terminal independent review selection, canonical application and ordinary remote CI remain root-owned and pending here.",
                                         "Both separate HTTP/2 post-upgrade wire qualifications, production/provider/native/device and all GA gates remain pending."]}
    write_json("dependencies.json", dependency_record)
    write_json("application-map.json", {"state": "proposal_only_not_applied", "canonical_files": application,
                                        "dependency_inventory_path": inventory_path,
                                        "root_application": "Verify each current before hash, then apply only canonical.patch or copy its three proposed files; preserve all other dirty work.",
                                        "validation_after_application": "Existing ordinary remote Phoenix CI; no local broad callback/authority replay is proposed."})
    after = {name: sha(read(ROOT / name)) for name in before}
    assert after == before, "canonical/protected sources changed during source preparation"
    write_json("preparation-receipt.json", {"schema": "mixer.hosted-dependency-integration.preparation.v1",
                                            "prepared_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
                                            "command": ["python3", "-B", str(Path(__file__).relative_to(ROOT))], "python": sys.version,
                                            "source_revision": receipt["source_revision"], "source_tree": receipt["source_tree"],
                                            "source_input_hashes": {"runtime_receipt": sha(receipt_raw), "actual_mix_lock": sha(actual_lock),
                                                                    "runtime_inventory": sha(read(ATTEMPT / "lock-inventory.json")),
                                                                    "original_mix_proposal": sha(proposed_mix)},
                                            "protected_and_canonical_before_after": {n: {"before": before[n], "after": after[n]} for n in before},
                                            "checks": ["five existing resolution commands exit0 with no errors and closed groups/removed scratch",
                                                       "all retained resolver output hashes match actual receipt", "exact21-entry actual lock agrees with resolver inventory",
                                                       "only two selected entries changed;19 complete entries remain identical", "all9 exact direct pins match actual lock",
                                                       "Bandit runtime requirements match official saved metadata and unchanged children", "both generated outer checksums agree with official saved release metadata",
                                                       "three proposed source files and inventory references agree", "all selected canonical and protected dirty files remain untouched"],
                                            "test_execution": "none; existing methods are selected in README only", "network_runtime_execution": "none in source preparation",
                                            "terminal_independent_review": "pending root selection; no unsealed reviewer packet consumed",
                                            "elapsed_seconds": time.monotonic() - START, "state": "source_preparation_pass_proposal_only"})
    print(json.dumps({"status": "source_preparation_pass", "canonical_files": list(proposals), "entries": 21,
                      "selected": SELECTED, "unchanged": 19, "actual_lock_sha256": sha(actual_lock), "canonical_applied": False}, indent=2))


if __name__ == "__main__":
    main()
