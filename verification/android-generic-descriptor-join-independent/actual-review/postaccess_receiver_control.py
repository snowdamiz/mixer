"""Source-review-discovered control, separate from the immutable original119 plan."""
import copy
import json
from review_support import *


def replace_exact(value, replacements):
    if isinstance(value, dict): return {k: replace_exact(v, replacements) for k, v in value.items()}
    if isinstance(value, list): return [replace_exact(v, replacements) for v in value]
    return replacements.get(value, value) if isinstance(value, str) else value


def main():
    check_preaccess()
    d, original = load_candidate()
    j = d.Joiner(d.Inputs())
    d.importlib.util.spec_from_file_location = original
    member = "reference-tree/" + str(d.RUN / "boundary-162.rows.jsonl.gz.compact.jsonl")
    rows = [d.loads(line) for line in archive(member).splitlines()]
    prior_file = next(f for f in j.ledger["files"] if f["file"] == "boundary-162.rows.jsonl.gz")
    out = []
    for number in [6, 7]:
        original_row = rows[number - 1]
        prior = copy.deepcopy(prior_file["rows"][number - 1])
        baseline = j.row(original_row, prior, prior_file["file"])
        completion = original_row["selected_actual_native_completions"][0]
        binding = next(b for b in original_row["native_receiver_bindings"] if b["global_identity"] == completion["receiver_identity"])
        replacements = {binding["global_identity"]: "missing.NativeSwitch@999", binding["row_identity"]: "missing.NativeSwitch@row-" + str(binding["ordinal"])}
        row = replace_exact(copy.deepcopy(original_row), replacements)
        modified_binding = next(b for b in row["native_receiver_bindings"] if b["global_identity"] == "missing.NativeSwitch@999")
        modified_binding["class"] = "missing.NativeSwitch"
        # Unchanged prior typed observations contain original throwable identities, not receiver labels.
        actual = j.row(row, prior, prior_file["file"])
        result = actual["native_completions"][0]
        assert result["receiver"]["status"] == "unresolved"
        out.append({"id": "unknown-invokespecial-hook-receiver-row" + str(number), "member": member, "row": number,
                    "state": row["state"], "source_row_sha256": sha(canonical(original_row)),
                    "mutation": {"exact_identity_replacements": replacements, "binding_class": "missing.NativeSwitch"},
                    "coherence": "All exact repeated global and row receiver identities were replaced recursively; class field agrees. Actual source/class frames, throwable observation and prior typed outcome remain unchanged.",
                    "baseline_status": baseline["native_completions"][0]["status"], "actual_status": result["status"],
                    "actual_receiver_relation": result["receiver"], "actual_original_exception": result["value"],
                    "expected": "Retain original observed hook exception and normal-return pending; descriptor join must stay unresolved while receiver relation is unresolved.",
                    "full_immutable_input_admission": "Changed raw/compact bytes would separately fail source input hashes; this is a coherent row-utility control."})
    write("postaccess-unknown-invokespecial-hook-receiver.json", out)
    write("receiver-control-inputs.json", USED)
    check_preaccess()
    print(json.dumps({"controls": len(out), "joined_with_unresolved_receiver": sum(x["actual_status"].startswith("joined-") for x in out)}))


if __name__ == "__main__":
    main()
