"""Host-only oracle mutations against the immutable first keyboard packet."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

sys.dont_write_bytecode = True
BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PACKET = ROOT / "verification/apple-toggle-keyboard-focus"
sys.path.insert(0, str(PACKET))
import test_keyboard as fixtures

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
rows = []
mutations = [
    ("application focus false while native toggle focused", lambda b, a: (
        b["state"].update(focused=False), a["state"].update(focused=False))),
    ("native toggle label changed", lambda b, a:
        b["keyboardWitness"]["after"]["elements"]["authored-toggle"].update(label="unexpected label")),
]
for label, mutate in mutations:
    case, before, after = fixtures.fixture()
    mutate(before, after)
    verdict = fixtures.verdict(case, before, after)
    rows.append({"mutation": label, "passed": verdict["passed"], "predicates": verdict["predicates"]})
tool = pathlib.Path(sys.executable).resolve()
receipt = {
    "schema": "mixer.apple-toggle.keyboard-root-initial-review.1",
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "producerSealSHA256": sha(PACKET / "packet-seal.json"),
    "sourceContext": {n: sha(PACKET / n) for n in ["keyboard_oracle.py", "test_keyboard.py"]},
    "sourceRevisionContext": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "command": [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
    "tool": {"path": str(tool), "version": sys.version, "sha256": sha(tool)},
    "reproducerSHA256": sha(pathlib.Path(__file__)),
    "exitCode": 0,
    "observations": rows,
    "nativeExecution": False,
    "status": "clarification-and-repair-required-before-selection",
    "scope": "Synthetic oracle behavior only; not observed native behavior or product failure.",
}
assert all(row["passed"] is True for row in rows), "Original finding changed; do not overwrite receipt"
(BASE / "initial-findings.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(rows))
