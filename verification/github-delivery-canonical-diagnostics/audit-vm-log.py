"""Read-only audit of the completed canonical Linux VM job, without replay."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
HEAD = "b4a9fd46e8b1b349118a212dcdc871d6fd025a35"
raw = (OUT / "vm-job-log-2.stdout").read_bytes()
lines = raw.decode().splitlines()
snapshot = json.loads((OUT / "ci-jobs-3.stdout").read_bytes())
assert snapshot["headSha"] == HEAD and snapshot["attempt"] == 1
job = next(j for j in snapshot["jobs"] if j["name"] == "vm")
assert job["databaseId"] == 122082898540 and job["conclusion"] == "success"
assert all(s["conclusion"] == "success" for s in job["steps"])
assert any(line.endswith(HEAD) for line in lines)
assert any("rustc 1.99.0 (b940084d7 2026-09-28)" in line for line in lines)
assert any("host: x86_64-unknown-linux-gnu" in line for line in lines)

runs = []
current = None
for number, line in enumerate(lines, 1):
    if "Running unittests src/lib.rs" in line:
        assert current is None
        current = {"log_start_line": number, "invocation": line, "diagnostics": []}
    elif current is not None:
        if "test experimental_swift_reactor::diagnostic" in line and " ... " in line:
            match = re.search(r"test (\S+) \.\.\. (\S+)$", line)
            assert match and match[2] == "ok", line
            current["diagnostics"].append(match[1])
        if "test result:" in line:
            assert "test result: ok." in line and "0 failed;" in line
            current.update(log_end_line=number, summary=line)
            runs.append(current)
            current = None
assert current is None and len(runs) == 8
selected = [r for r in runs if r["diagnostics"]]
assert len(selected) == 4
expected = set(selected[0]["diagnostics"])
assert len(expected) == 44
for run, count in zip(selected, (460, 460, 430, 430), strict=True):
    assert Counter(run["diagnostics"]) == Counter(expected)
    assert f"{count} passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;" in run["summary"]
assert all("/debug/" in selected[i]["invocation"] for i in (0, 2))
assert all("/release/" in selected[i]["invocation"] for i in (1, 3))
assert sum("diagnostic_profile::" in name for name in expected) == 17
assert sum("diagnostic_result_v1::" in name for name in expected) == 27

result = {
    "schema": 1,
    "at": datetime.now(timezone.utc).isoformat(),
    "commit": HEAD,
    "run": 40472556591,
    "attempt": 1,
    "job": job["databaseId"],
    "job_url": job["url"],
    "job_all_steps_succeeded": True,
    "log_sha256": hashlib.sha256(raw).hexdigest(),
    "log_bytes": len(raw),
    "target": "x86_64-unknown-linux-gnu",
    "rustc": "1.99.0 (b940084d7 2026-09-28)",
    "focused_methods_each_configuration_and_mode": 44,
    "combined_feature_library_methods_each_mode": 460,
    "reactor_only_library_methods_each_mode": 430,
    "focused_method_executions": 176,
    "library_runs": selected,
    "qualification": "Canonical private diagnostic codec and original row helper on Linux in the two recorded Cargo feature sets, debug and release; reactor-only production Clippy step succeeded.",
    "not_qualified": ["isolated snapshot loader/adoption/writer", "complete snapshot funding or work", "device/runtime/store/customer/GA"],
    "prior_download_failure": "vm-job-log: gh refused terminal escapes; retry retained raw bytes in file without rendering escapes",
}
(OUT / "canonical-linux-vm-audit.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"passed": True, "focused_executions": 176, "library_each_mode": [460, 430]}))
