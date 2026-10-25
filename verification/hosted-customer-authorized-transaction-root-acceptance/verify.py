#!/usr/bin/env python3
"""Bind the corrected local transaction prerequisite to reviewed source/evidence."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REVIEW = "verification/hosted-customer-authorized-transaction-review/review.json"
REVIEW_SHA = "826c498065389dd6924ae16d346e1f66db44c705b9e1bcaa9593aae3c63cd83f"
PACKETS = ["hosted-customer-authorized-transaction", "hosted-customer-authorized-transaction-review",
           "hosted-customer-authorized-transaction-ci"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not (OUT / "acceptance.json").exists()
assert digest(ROOT / REVIEW) == REVIEW_SHA
review = json.loads((ROOT / REVIEW).read_text())
assert review["disposition"] == "accepted_selected_local_prerequisite_after_review_repairs"
assert review["final_tests"]["methods"] == 21 and review["final_tests"]["failures"] == 0
assert all(digest(ROOT / p) == h for p, h in review["live_input_sha256"].items())
live = dict(review["live_input_sha256"])
historical_copies = 0
for packet in PACKETS:
    folder = ROOT / "verification" / packet
    for rp in sorted(folder.glob("run-*/receipt.json")):
        receipt = json.loads(rp.read_text())
        assert receipt["cleanup"]["scratch_removed"]
        assert receipt["cleanup"].get("postgres_stopped") or receipt["cleanup"].get("postgres_started") is False
        if "scratch" in receipt:
            assert not Path(receipt["scratch"]).exists()
        inputs = receipt.get("input_sha256", receipt.get("inputs"))
        assert inputs
        for name, expected in inputs.items():
            assert digest(rp.parent / "inputs" / name) == expected
            historical_copies += 1
        if (packet, rp.parent.name) in [
            (PACKETS[0], "run-5"), (PACKETS[1], "run-5-final"), (PACKETS[2], "run-2")
        ]:
            assert receipt["success"]
            assert all(command["exit_code"] == 0 for command in receipt["commands"])
            assert all(digest(ROOT / p) == h for p, h in inputs.items())
            live.update(inputs)
for folder, count, log in [
    (PACKETS[0] + "/run-5", 18, "tests.log"),
    (PACKETS[1] + "/run-5-final", 21, "tests.log"),
    (PACKETS[2] + "/run-2", 18, "tests.stdout")
]:
    assert f"Result: {count} passed" in (ROOT / "verification" / folder / log).read_text()
for name, record in review["runs"].items():
    assert digest(ROOT / "verification" / PACKETS[1] / name / "receipt.json") == record["receipt_sha256"]
assert digest(ROOT / review["report"]["path"]) == review["report"]["sha256"]
bindings = {}
for packet in PACKETS:
    for p in sorted((ROOT / "verification" / packet).rglob("*")):
        if p.is_file():
            assert not p.is_symlink() and "__pycache__" not in p.parts
            bindings[str(p.relative_to(ROOT))] = digest(p)
for name in ["docs/hosted-customer-authorized-transaction.md", review["report"]["path"]]:
    bindings[name] = digest(ROOT / name)
receipt = {
    "schema": 1, "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "baseRevision": "d385adf3dd110da44ba290a7221278c48e39b882",
    "command": [sys.executable, str(Path(__file__).resolve())], "python": sys.version,
    "verifierSHA256": digest(Path(__file__)), "reviewSHA256": REVIEW_SHA,
    "producerMethodsPassed": 18, "independentMethodsPassed": 21,
    "ciEquivalentMethodsPassed": 18, "ordinaryMigrations": 6,
    "historicalSourceCopiesVerified": historical_copies,
    "retainedFilesVerified": len(bindings), "files": bindings,
    "liveInputBindings": live, "ownedCleanupVerified": True,
    "decision": "Accept corrected local transaction-owned authorization prerequisite.",
    "limitations": [
        "PG17 local; full standard CI and PG16 on the new checkpoint remain pending.",
        "No protected domain storage, metadata resolver, immutable audit/idempotency, customer HTTP or console connection.",
        "Trusted BEAM composition only; no hostile-code sandbox or OS clock-adjustment claim.",
        "No provider/deployment/native/physical/published-dogfood or GA qualification."
    ]
}
(OUT / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({k: receipt[k] for k in ["producerMethodsPassed", "independentMethodsPassed", "ciEquivalentMethodsPassed", "ordinaryMigrations", "historicalSourceCopiesVerified", "retainedFilesVerified", "ownedCleanupVerified"]}))
