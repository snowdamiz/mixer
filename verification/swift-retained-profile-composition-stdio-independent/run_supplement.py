"""Append one independently owned nested-child join without repeating green cases."""
import json
import os
import sys
from run_review import ROOT, run, dump
from verify_inputs import verify

if __name__ == "__main__":
    verify()
    commands = json.loads((ROOT / "command-receipts.json").read_text())
    extra = run([os.path.realpath(sys.executable), "-B", str(ROOT / "mixed_child_case.py")], ROOT, "062-mixed-child-cleanup-join", 0, "independent additional nested actual-child behavioral requirement")
    commands["commands"].append(extra)
    dump(ROOT / "command-receipts.json", commands)
    assert extra["command_disposition_matches"] and extra["terminal_reaped"] and not extra["timed_out"]
    assert not list((ROOT / "owned-scratch").iterdir())
    results = json.loads((ROOT / "results.json").read_text())
    results["new_independent_cases"] += 1
    results["new_independent_behavior_passes"] += 1
    results["additional_nested_fixed_child_join"] = extra["observations"][0]
    dump(ROOT / "results.json", results)
    receipt = json.loads((ROOT / "receipt.json").read_text())
    receipt["fresh_commands"] += 1
    receipt["independent_cases"] += 1
    receipt["independent_passes"] += 1
    receipt["supplement_command"] = [os.path.realpath(sys.executable), "-B", "run_supplement.py"]
    dump(ROOT / "receipt.json", receipt)
    print(json.dumps({"total_fresh_commands": receipt["fresh_commands"], "new_independent_cases": receipt["independent_cases"], "independent_passes": receipt["independent_passes"], "required_R03_failures": receipt["required_R03_failures"]}, sort_keys=True))
