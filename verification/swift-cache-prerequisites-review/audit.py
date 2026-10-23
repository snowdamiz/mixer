#!/usr/bin/env python3
"""Check preserved literal source and the new private composition boundary."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
SOURCE = OUT / ".build/source"
receipt = json.loads((OUT / "receipt.json").read_text())
base = receipt["baseline"]
def sha(data):
    return hashlib.sha256(data).hexdigest()
def old(path):
    return subprocess.check_output(["git", "show", base + ":" + path], cwd=ROOT).decode()
def current(path):
    return (SOURCE / path).read_text()
def literal(text, marker):
    tail = text[text.index(marker):]
    return tail[:tail.index("\n}") + 2]

checks = []
for path, marker in [
    ("vm/src/experimental_swift_reactor/control.rs", "pub(crate) struct RuntimeControl {"),
    ("vm/src/experimental_swift_reactor/control.rs", "pub(crate) struct ReservationTicket {"),
    ("vm/src/experimental_swift_reactor/control.rs", "pub(crate) struct AdoptedProof {"),
    ("vm/src/experimental/swift.rs", "pub struct ValidatedSwiftReactor {"),
    ("vm/src/experimental/mod.rs", "pub struct ValidatedSpans {"),
    ("vm/src/experimental/mod.rs", "pub struct SegmentView<'a> {"),
    ("vm/src/experimental/metadata.rs", "pub(super) struct Metadata<D: Declaration = FrozenDeclaration> {"),
    ("vm/src/experimental_wasi/accounted.rs", "pub(crate) struct AccountedWasi {"),
    ("vm/src/experimental/descriptors.rs", "impl ValidatedSpans {"),
]:
    before = literal(old(path), marker)
    after = literal(current(path), marker)
    assert before == after, marker
    checks.append({"path": path, "literal": marker, "unchanged_sha256": sha(after.encode())})
path = "vm/src/experimental_wasi/accounted.rs"
def dispatch(text):
    return text[text.index("    pub(crate) fn dispatch("):text.index("    /// No checks, admission, work charging, allocation or services during cleanup.")]
assert dispatch(old(path)) == dispatch(current(path))
checks.append({"path": path, "literal": "complete AccountedWasi::dispatch including pre/post checks", "unchanged_sha256": sha(dispatch(current(path)).encode())})
for path in ["vm/src/experimental/cache/mod.rs", "vm/src/experimental/cache/decode.rs", "vm/src/experimental/execution/mod.rs", "vm/src/experimental/metadata.rs", "vm/src/experimental/validate.rs", "vm/src/experimental_wasi/mod.rs", "vm/Cargo.toml", "vm/Cargo.lock", "vm/src/lib.rs"]:
    assert old(path) == current(path), path
    checks.append({"path": path, "literal": "entire file", "unchanged_sha256": sha(current(path).encode())})
(OUT / "source-audit.json").write_text(json.dumps(checks, indent=2) + "\n")

env = os.environ.copy()
env["PATH"] = "/opt/homebrew/opt/rustup/bin:" + env["PATH"]
env["CARGO_TARGET_DIR"] = str(OUT / ".build/privacy-target")
probe = OUT / ".build/privacy-probe"
(probe / "src").mkdir(parents=True)
(probe / "Cargo.toml").write_text('[package]\nname = "mixer-prerequisite-review-privacy"\nversion = "0.0.0"\nedition = "2021"\n[dependencies]\nmixer-vm = { path = "../source/vm", features = ["experimental-swift-reactor"] }\n')
inputs = {
    "privacy-public-control": ('use mixer_vm::experimental_swift_reactor::{ValidatedSwiftReactor, SwiftValidationBudget};\nfn inspect(p: &ValidatedSwiftReactor) { let _ = (p.source(), p.usage(), p.observations()); let _ = SwiftValidationBudget::default(); }\n', 0),
    "privacy-runtime-control": ('use mixer_vm::experimental_swift_reactor::control::{RuntimeControl, AdoptedProof, ReservationTicket};\n', 101),
    "privacy-accounted-wasi": ('use mixer_vm::experimental_wasi::accounted::AccountedWasi;\n', 101),
}
for label, (source, expected) in inputs.items():
    (OUT / (label + ".rs")).write_text(source)
    (probe / "src/lib.rs").write_text(source)
    argv = ["cargo", "check", "--offline", "--manifest-path", str(probe / "Cargo.toml")]
    started = time.monotonic()
    result = subprocess.run(argv, cwd=SOURCE, env=env, capture_output=True)
    for stream in ["stdout", "stderr"]:
        (OUT / (label + "." + stream)).write_bytes(getattr(result, stream))
    assert result.returncode == expected, label
    if expected:
        assert b"error[E0603]" in result.stderr
    receipt["commands"].append({"label": label, "argv": argv, "cwd": str(SOURCE), "environment_overrides": {"PATH": env["PATH"], "CARGO_TARGET_DIR": env["CARGO_TARGET_DIR"]}, "exit": result.returncode, "expected_exit": expected, "seconds": time.monotonic() - started, "source_input": {"path": label + ".rs", "sha256": sha(source.encode())}, "stdout": {"path": label + ".stdout", "sha256": sha(result.stdout)}, "stderr": {"path": label + ".stderr", "sha256": sha(result.stderr)}})
    print(label, result.returncode, flush=True)
receipt["source_audit_sha256"] = sha((OUT / "source-audit.json").read_bytes())
receipt["audit_collector_sha256"] = sha(Path(__file__).read_bytes())
receipt["final_overlay_stable"] = {path: sha((ROOT / path).read_bytes()) == digest for path, digest in json.loads((OUT / "freeze.json").read_text())["overlay_sha256"].items()}
assert all(receipt["final_overlay_stable"].values())
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
