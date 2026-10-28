#!/usr/bin/env python3
"""Check the offline proposal and its custody; never launch a runtime."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt = json.loads((HERE / "preparation-receipt.json").read_text())
    plan = json.loads((HERE / "resolution-plan.json").read_text())
    checks = []
    for name, item in receipt["selected_inputs"].items():
        assert sha(ROOT / name) == item["sha256"], name
    checks.append("all 13 selected canonical source files retain prepared bytes")
    prior = ROOT / "verification/hosted-dependency-advisory-review"
    frozen = receipt["prior_advisory_packet"]
    assert sha(prior / "seal.sha256") == frozen["seal_sha256"]
    for item in frozen["entries"]:
        assert sha(prior / item["path"]) == item["sha256"], item["path"]
    checks.append("prior advisory packet seal and all 15 members remain unchanged")
    original = (HERE / "inputs/mix.exs").read_text()
    expected = original.replace('{:bandit, "== 1.13.1"}', '{:bandit, "== 1.14.0"}')
    expected = expected.replace('{:jose, "== 1.11.12"}', '{:jose, "== 1.11.13"}')
    assert (HERE / "proposal/mix.exs").read_text() == expected
    checks.append("mix.exs proposal changes exactly the two selected pins")
    original = (HERE / "inputs/THIRD_PARTY.yml").read_text()
    expected = original
    for package, old, new, previous_receipt in [
        ("bandit", "1.13.1", "1.14.0", "verification/phoenix-foundation/dependencies.json"),
        ("jose", "1.11.12", "1.11.13", "verification/hosted-verifier-dependency/root-selection.json"),
    ]:
        first = expected.index("  - name: Hex " + package + "\n")
        last = expected.index("  - name:", first + 1)
        block = expected[first:last]
        block = block.replace('version: "' + old + '"', 'version: "' + new + '"')
        block = block.replace("inventory_receipt: " + previous_receipt,
                              "inventory_receipt: verification/hosted-dependency-advisory-correction/dependencies.json")
        expected = expected[:first] + block + expected[last:]
    assert (HERE / "proposal/THIRD_PARTY.yml").read_text() == expected
    checks.append("THIRD_PARTY proposal changes exactly two versions and two pending receipt links")
    assert sha(HERE / "inputs/mix.lock") == receipt["selected_inputs"]["hosted/mix.lock"]["sha256"]
    assert not (HERE / "proposal/mix.lock").exists()
    assert not (HERE / "dependencies.json").exists()
    checks.append("original lock unchanged; no replacement lock/checksums or dependency receipt invented")
    assert [c["argv"][1:] for c in plan["commands"]] == [
        ["--version"], ["--version"], ["deps.unlock", "bandit", "jose"],
        ["deps.get", "--only", "prod"], ["deps.get", "--only", "prod", "--check-locked"]]
    assert plan["commands"][-1]["environment_override"] == {"HEX_OFFLINE": "1"}
    assert plan["state"] == "proposed_only_pending_root_runtime_lane_release"
    assert sum(c["timeout_seconds"] for c in plan["commands"]) == 260
    assert plan["controller_bounds"]["root_operation_wall_seconds"] == 300
    checks.append("five bounded argv operations remain proposed; no compile/test/start task selected")
    assert not (HERE / "source-only-scratch").exists()
    assert not (HERE / "runtime-scratch").exists()
    checks.append("preparation scratch removed; no runtime scratch created")
    result = {"checked_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
              "command": ["python3", "-B", "verification/hosted-dependency-advisory-correction/validate_plan.py"],
              "status": "pass", "checks": checks,
              "scope": "Offline proposal/custody validation; no Elixir/OTP/Mix/Hex execution or product test."}
    (HERE / "preparation-validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
