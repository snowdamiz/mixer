"""Data-only root audit of the frozen loader's actual build and session preimages."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import struct

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "verification/swift-real-profile-loader-binding"
OUT = Path(__file__).with_name("real-loader-preimage-review.json")
assert not OUT.exists()
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": sha(raw)}
def load(name):
    return json.loads((P / name).read_bytes())
def word(raw, offset):
    return struct.unpack_from("<Q", raw, offset)[0]
def parts(raw, offset):
    at = 512
    result = []
    for i in range(4):
        count = word(raw, offset + i * 8)
        assert count > 0 and at + count <= len(raw)
        result.append(raw[at:at + count])
        at += count
    assert at == len(raw)
    return result
def packed(items):
    return struct.pack("<Q", len(items)) + b"".join(struct.pack("<Q", len(v)) + v for v in items)

commands = load("command-receipts.json")
assert len(commands) == 105 and all(r["expectation_met"] and r["terminally_waited"] and r["killed_for"] is None for r in commands)
by_label = {r["label"]: r for r in commands}
assert len(by_label) == len(commands)
for r in commands:
    for key in ("stdout", "stderr"):
        item = r[key]
        path = Path(item["path"])
        assert path.is_relative_to(P / "logs")
        assert identity(path) == {k: item[k] for k in ("bytes", "sha256")}
    assert (r["exit_code"] == 0) == (r["expected_diagnostic"] is None)

manifest = load("build-input-manifest.json")
source = load("source-manifest.json")
assert manifest["distribution"] == source and source["member_count"] == 144
assert manifest["host_support"] == load("baseline-host-support-manifest.json")
for member in manifest["orchestration"]:
    path = Path(member["path"])
    assert path.parent == P
    assert identity(path) == {k: member[k] for k in ("bytes", "sha256")}
builds = {}
for mode in ("debug", "optimized"):
    raw = (P / ("build-preimage-" + mode + ".bin")).read_bytes()
    assert raw[:8] == b"MIXLBD01" and [word(raw, i) for i in (8, 16, 24, 32, 40)] == [1, 512, len(raw), 144, 11]
    sections = parts(raw, 48)
    assert json.loads(sections[0]) == manifest
    assert all(bytes.fromhex(sha(v)) == raw[152 + i * 32:184 + i * 32] for i, v in enumerate(sections))
    assert sections[1] == packed([bytes.fromhex(v) for v in by_label["compile-" + mode]["argv_raw_hex"]])
    assert sections[3] == (P / "logs/rustc-version.stdout").read_bytes()
    assert raw[280:312].hex() == manifest["tools"]["rustc"]["sha256"]
    artifact = next(v for v in load("receipt.json")["artifacts_measured_then_removed"] if v["path"].endswith("/unit-" + mode))
    assert word(raw, 80) == artifact["bytes"] and raw[312:344].hex() == artifact["sha256"]
    builds[mode] = raw

observations = load("session-observations.json")
assert len(observations) == 74
checked = []
for item in observations:
    mode, scenario = item["mode"], item["scenario"]
    source_bytes = (P / item["source_preimage"]).read_bytes()
    assert sha(source_bytes) == item["source_sha256"]
    session_path = Path(item["session"]["path"])
    assert session_path.is_relative_to(P / "sessions")
    assert identity(session_path) == {k: item["session"][k] for k in ("bytes", "sha256")}
    raw = session_path.read_bytes()
    build_path = P / "sessions" / (mode + "-" + scenario + "-build.bin")
    build = build_path.read_bytes() if build_path.exists() else builds[mode]
    assert sha(build) == item["build_sha256"]
    command = by_label[mode + "-" + scenario]
    if scenario != "session-overcap":
        assert raw[:8] == b"MIXLSE01" and [word(raw, i) for i in (8, 16, 24)] == [1, 512, len(raw)]
        sections = parts(raw, 40)
        assert all(bytes.fromhex(sha(v)) == raw[240 + i * 32:272 + i * 32] for i, v in enumerate(sections))
        assert sections[0].hex() == item["source_identity_hex"]
        if scenario != "argv":
            assert sections[1] == packed([bytes.fromhex(v) for v in command["argv_raw_hex"]])
            assert sha(sections[1]) == item["actual_argv_encoding_sha256"]
        if scenario != "environment":
            assert sha(sections[2]) == item["actual_environment_encoding_sha256"]
        if scenario != "cwd":
            assert sections[3].hex() == item["actual_cwd_raw_hex"] == command["cwd_raw_hex"]
        if scenario != "source-substitute":
            assert raw[144:176].hex() == item["source_sha256"]
        if scenario != "build-overcap":
            assert raw[176:208].hex() == item["build_sha256"]
        assert raw[208:240].hex() == item["producer_binary_sha256"]
        if scenario not in ("nonce", "session-digest"):
            assert raw[112:144].hex() == item["nonce_from_OS_randomness_hex"]
        if scenario != "session-digest":
            assert sha(raw) == item["session_commitment_from_trusted_launcher"]
    checked.append({"mode": mode, "scenario": scenario, "session_sha256": sha(raw)})

report = {"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "python_version": platform.python_version(),
          "script": identity(Path(__file__)), "frozen_seal_sha256": sha((P / "seal.json").read_bytes()),
          "status": "root-source-and-data-preimage-review-no-blocker-found-independent-runtime-review-pending",
          "source_tree_sha256": source["tree_sha256"], "command_logs_verified": 105,
          "build_preimages_verified": 2, "actual_session_records_verified": checked,
          "source_review": "Reviewed loader control flow, exact-limit comparison, borrowed complete input equality before private mint, actual file retention on success/failure, pre/post metadata and alias checks, standard SHA256, bounded byte encodings, all original validation failure peaks, and trusted-runner precompile identity. No runtime route or owner accounting change.",
          "limits": ["Trusted launcher and quiescent process only; no hostile-parent or signed package authentication", "Removed executable identities are receipt-correlated, not freshly rehashed", "Successful producer children terminally waited; no descendant/process-group cleanup claim", "Fixed named-storage and conservative union are not operational admission or RSS", "Two invalid-UTF8 path creations per mode refused before loader; remain unrun", "Independent actual implementation review, runtime adoption/export/context and native/GA remain pending"],
          "candidate_accepted": False, "native_UI_capture_process_inventory_started": False}
OUT.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"builds": 2, "sessions": len(checked), "command_logs": 105, "receipt": identity(OUT)}))
