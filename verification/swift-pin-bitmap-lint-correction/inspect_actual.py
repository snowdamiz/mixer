from offline_guard import install
install()

import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTUAL = ROOT / "verification/clock-format-actual-results/local/format-extract/_temp/pin-bitmap-format-lint-v1-evidence"

for name in ("source-manifest.json", "comparison.json"):
    doc = json.loads((ACTUAL / name).read_text())
    print(name, [(k, len(v) if isinstance(v, (list, dict)) else v) for k, v in doc.items()])

seen = set()
for arm in ("baseline", "candidate"):
    doc = json.loads((ACTUAL / f"clippy-{arm}.json").read_text())
    print("ARM", arm, [(k, len(v) if isinstance(v, (list, dict)) else v) for k, v in doc.items() if k != "diagnostics"])
    counts = collections.Counter()
    for d in doc["diagnostics"]:
        if d.get("level") != "error" or not d.get("code"):
            continue
        spans = [s for s in d["spans"] if s["is_primary"]]
        counts[d["code"]["code"]] += 1
        key = (d["code"]["code"], tuple((s["file_name"], s["byte_start"], s["byte_end"]) for s in spans))
        if key in seen:
            continue
        seen.add(key)
        print("DIAG", arm, d["code"]["code"], d["message"])
        for s in spans:
            print(s["file_name"], s["line_start"], s["column_start"], s["byte_start"], s["byte_end"])
            for t in s["text"]:
                print("TEXT", t["text"])
        for child in d["children"]:
            for s in child["spans"]:
                if s.get("suggested_replacement") is not None:
                    print("SUGGEST", s["byte_start"], s["byte_end"], repr(s["suggested_replacement"]))
    print("COUNTS", dict(counts))
