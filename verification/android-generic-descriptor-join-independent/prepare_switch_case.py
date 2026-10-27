"""Read only the separately identified historical rows and retained hierarchy as data."""
import gzip
import json
from custody import read, RUN33, OWN, digest
from classfile_data import parse, invocation_at


def main():
    compact_member = RUN33 + "boundary-162.rows.jsonl.gz.compact.jsonl"
    raw_member = RUN33 + "boundary-162.rows.jsonl.gz"
    compact_lines = read(compact_member).splitlines()
    raw_lines = gzip.decompress(read(raw_member)).splitlines()
    out = []
    for number in [3, 5]:
        row = json.loads(compact_lines[number - 1])
        raw_row = json.loads(raw_lines[number - 1])
        assert row["state"] == raw_row["state"]
        frames = row["selected_immutable_event_points"][0]["production_frames"]
        frame = next(f for f in frames if f["class"] == "dev.mixer.android.NativeAppearanceViewsV2$NativeSwitch"
                     and f["method"] == "performAccessibilityAction")
        parsed = parse(read(RUN33 + "classes/" + frame["class"].replace(".", "/") + ".class"))
        invocation = invocation_at(parsed, frame["method"], frame["descriptor"], frame["bci"])
        path, cls = [], invocation["owner"]
        while True:
            parsed = parse(read(RUN33 + "classes/" + cls + ".class"))
            declares = any(m["name"] == invocation["name"] and m["descriptor"] == invocation["descriptor"] for m in parsed["methods"])
            path.append({"class": cls, "super": parsed["super"], "declares_exact_method": declares})
            if declares:
                break
            cls = parsed["super"]
        assert [p["class"] for p in path] == ["android/widget/Switch", "android/widget/Button", "android/widget/TextView"]
        assert invocation["opcode"] == 183 and frame["bci"] == 50
        out.append({"compact_member": compact_member, "raw_member": raw_member, "row": number, "state": row["state"],
                    "compact_row_bytes_sha256": digest(compact_lines[number - 1]), "raw_row_bytes_sha256": digest(raw_lines[number - 1]),
                    "selected_actual_call": row["selected"], "first_product_caller": frame, "compiled_invocation": invocation,
                    "retained_resolution_path": path, "selected_actual_native_completions": row["selected_actual_native_completions"],
                    "raw_matching_view_observations": [o for o in raw_row["actual_native_outcomes"] if o["method"] == "View.performAccessibilityAction"],
                    "expected": "View inner observation remains retained; no exact resolved TextView outer-callee normal completion credit"})
    sources = []
    for name in ["Switch.java", "Button.java", "TextView.java", "View.java", "NativeAppearanceViewsV2.java"]:
        raw = read(RUN33 + name)
        sources.append({"member": RUN33 + name, "sha256": digest(raw),
                        "matching_source_lines": [(i, l) for i, l in enumerate(raw.decode().splitlines(), 1) if "performAccessibilityAction" in l]})
    (OWN / "switch-outer-versus-inner-source-case.json").write_text(json.dumps({"cases": out, "sources": sources}, indent=2) + "\n")
    print(json.dumps({"historical_cases": len(out), "candidate_accessed": False}))


if __name__ == "__main__":
    main()
