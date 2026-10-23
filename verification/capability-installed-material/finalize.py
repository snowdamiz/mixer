#!/usr/bin/env python3
"""Audit exact material evidence bindings and seal only source/evidence, never build caches."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXCLUDED = {".build", ".swiftpm", "__pycache__"}
HOST = HERE / "2026-10-23-candidate-2/receipt.json"
CROSS = HERE / "2026-10-23-candidate-2-cross/receipt.json"
HOST_PIN = "0c3b8df6a04fabda6ad0f8301832d7679dc216c1a5a4bf23983ebb332f29db31"
CROSS_PIN = "ce3c65abf4cd45e5cc7ef4877d11a31a625da17a63bfe76c0c434a88eecd7694"
def sha(raw): return hashlib.sha256(raw).hexdigest()
def require(value, message):
    if not value: raise RuntimeError(message)
def manifest(paths):
    records = {}
    for path in sorted(set(paths)):
        require(not EXCLUDED.intersection(path.relative_to(ROOT).parts), "ignored cache in manifest")
        require(not path.is_symlink(), "regular source/evidence file")
        records[path.relative_to(ROOT).as_posix()] = sha(path.read_bytes())
    return records, "".join(digest + "  " + path + "\n" for path, digest in sorted(records.items())).encode()


def main():
    require(sha(HOST.read_bytes()) == HOST_PIN, "final host receipt binding")
    require(sha(CROSS.read_bytes()) == CROSS_PIN, "final cross receipt binding")
    host = json.loads(HOST.read_bytes()); cross = json.loads(CROSS.read_bytes())
    source = Path(host["immutable_source_export"])
    for path, digest in host["source_files"].items():
        require(sha((ROOT / path).read_bytes()) == digest, "unchanged source " + path)
        require(sha((source / path).read_bytes()) == digest, "unchanged export " + path)
    require(cross["source_manifest_sha256"] == host["source_manifest_sha256"] and cross["host_receipt_sha256"] == HOST_PIN, "cross/host source agreement")
    for receipt in [host, cross]:
        require(receipt["source_and_export_unchanged"], "qualification completed unchanged")
        for row in receipt["commands"]:
            require(sha((ROOT / row["log"]).read_bytes()) == row["sha256"], "exact command log " + row["name"])
            require(row["exit_code"] == row.get("expected_exit", 0), "expected exit " + row["name"])
    for artifact in cross["artifacts"].values():
        for record in artifact: require(sha(Path(record["path"]).read_bytes()) == record["sha256"], "target module/object pin")
    native = Path(host["native_copy"])
    for path, digest in host["native_files"].items(): require(sha((native / path).read_bytes()) == digest, "qualified native copy")
    require(sha(Path(host["public_client"]["path"]).read_bytes()) == host["public_client"]["sha256"], "linked public consumer")
    freeze_path = ROOT / "verification/capability-authority-contract-freeze-2026-10-23.json"
    freeze = json.loads(freeze_path.read_bytes())
    for path, digest in (freeze["normative_contracts"] | freeze["preserved_old_contracts"]).items():
        require(host["source_files"][path] == digest, "exact frozen contract " + path)
    old = "1ab4d4ee76a5d4ba206bd370cbeeeb73a7c6c636"
    # The identity CLI intentionally gained explicit inspect-v2 in its separate
    # approved slice; preserve the old identity library API, not its widened CLI.
    oldpaths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", old, "--", "updates/Sources", "runtime-identity/Sources/MixerRuntimeIdentity/RuntimeIdentity.swift", "activation/Sources"], cwd=ROOT, text=True).splitlines()
    preserved = {}
    for relative in oldpaths:
        raw = subprocess.check_output(["git", "show", old + ":" + relative], cwd=ROOT)
        require((ROOT / relative).read_bytes() == raw, "old production source unchanged " + relative)
        preserved[relative] = sha(raw)
    own = [p for p in (ROOT / "capability-activation").rglob("*") if p.is_file() and not EXCLUDED.intersection(p.relative_to(ROOT).parts)]
    own += [ROOT / "capabilities/tools/export-native-preimage.py"]
    own += [p for p in HERE.rglob("*") if p.is_file() and p.suffix in {".py", ".swift", ".md"} and not EXCLUDED.intersection(p.relative_to(ROOT).parts)]
    own_records, own_manifest = manifest(own)
    (HERE / "qualification-source.sha256").write_bytes(own_manifest)
    excluded_names = {"final-receipt.json", "evidence-manifest.sha256", "qualification-source.sha256"}
    evidence = [p for p in HERE.rglob("*") if p.is_file() and p.name not in excluded_names and not EXCLUDED.intersection(p.relative_to(ROOT).parts)]
    evidence_records, evidence_manifest = manifest(evidence)
    (HERE / "evidence-manifest.sha256").write_bytes(evidence_manifest)
    receipt = dict(schema=1, status="material-only owner qualification complete; independent integration review required", sealed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_manifest_sha256=host["source_manifest_sha256"], frozen_inputs=len(host["source_files"]),
        host_receipt=dict(path=str(HOST.relative_to(ROOT)), sha256=HOST_PIN, commands=len(host["commands"])),
        cross_receipt=dict(path=str(CROSS.relative_to(ROOT)), sha256=CROSS_PIN, commands=len(cross["commands"])),
        qualification_source_manifest_sha256=sha(own_manifest), qualification_source_files=len(own_records),
        evidence_manifest_sha256=sha(evidence_manifest), evidence_files=len(evidence_records),
        normative_freeze=dict(path=str(freeze_path.relative_to(ROOT)), sha256=sha(freeze_path.read_bytes())),
        preserved_legacy_production_sources=preserved, legacy_baseline=old,
        native_preimage=dict(sha256="4fcc770e62d39b415e657ce03aa11fa7fb83ee8bfe1a99567716e9b4372d1c59", sources=17, bytes=2394, final_lf=False),
        observed=dict(material_tests_per_mode=16, host_modes=["debug", "release", "swift-thread-sanitizer"], test_case_executions=48,
            helper_tests=3, external_release_client="linked and ran", external_positive_typecheck=True, intentional_opacity_rejections=5,
            official_mobile="iOS and Android target module/object compilation only"),
        earlier_candidate=dict(path="verification/capability-installed-material/2026-10-23-candidate-1/receipt.json", sha256="0f262de6c0712fbb718e5b8d22557249e820b0392606d2b27937e1f8c399b235",
            superseded_reason="Independent root review found unbounded role-ID Set hashing; final candidate adds bounded129-byte prefix guard before hashing/concatenation"),
        limitations=host["limitations"] + ["No selection, durable updater, adapter/session construction, validation call, startup/effects/health/recovery integration or installed execution authority"])
    target = HERE / "final-receipt.json"; target.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"final_receipt_sha256":sha(target.read_bytes()), "qualification_source_sha256":sha(own_manifest), "evidence_manifest_sha256":sha(evidence_manifest), "source_files":len(own_records), "evidence_files":len(evidence_records)}))


if __name__ == "__main__": main()
