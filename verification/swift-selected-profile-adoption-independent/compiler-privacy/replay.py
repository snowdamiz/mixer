#!/usr/bin/python3
"""Independent, bounded compiler controls. Never imports candidate orchestration."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "source/vm"
CANDIDATE = HERE.parents[1] / "swift-selected-profile-adoption"
RUSTC = Path("/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc")
WORK = HERE / "scratch"
FEATURES = ["experimental-swift-reactor", "experimental-swift-wasi", "experimental-stream-validation", "experimental-function-cache"]
PRELUDE = """use super::retained_profile_loader_v1::{AdoptionBodyV1, SelectedValidatedProfileV1, LoaderProvenanceV1};
use super::control::{AdoptedProof, RuntimeControl, SwiftRunBudget, SwiftRunFailure};
use super::{ValidatedSwiftReactor, SwiftValidationBudget};
use crate::Cancellation;
use std::time::Instant;
"""
CASES = [
    ("positive-production-contract", None, """
fn selected(p: SelectedValidatedProfileV1) -> Result<(RuntimeControl, AdoptedProof), SwiftRunFailure> {
    p.adopt(SwiftRunBudget::default(), Instant::now(), Cancellation::default())
}
fn ordinary(p: ValidatedSwiftReactor) -> Result<(RuntimeControl, AdoptedProof), SwiftRunFailure> {
    RuntimeControl::adopt(p, SwiftRunBudget::default(), Instant::now(), Cancellation::default())
}
fn selected_borrow(p: &AdoptedProof) -> Option<&LoaderProvenanceV1> { p.selected_provenance() }
fn ordinary_body(p: ValidatedSwiftReactor) -> AdoptionBodyV1 { AdoptionBodyV1::ordinary(p) }
fn body_borrow(p: &AdoptionBodyV1) -> (&ValidatedSwiftReactor, Option<&LoaderProvenanceV1>) {
    (p.proof(), p.selected_provenance())
}
fn selected_read(p: &SelectedValidatedProfileV1) -> (&[u8], SwiftValidationBudget) {
    (p.source(), p.validation_budget())
}
"""),
    ("body-literal-private", "E0451", "fn f(proof: ValidatedSwiftReactor) { let _ = AdoptionBodyV1 { proof, selected: None }; }"),
    ("carrier-literal-private", "E0451", "fn f(proof: ValidatedSwiftReactor, provenance: LoaderProvenanceV1) { let _ = SelectedValidatedProfileV1 { proof, provenance }; }"),
    ("carrier-proof-private", "E0616", "fn f(p: SelectedValidatedProfileV1) { let _ = p.proof; }"),
    ("carrier-provenance-private", "E0616", "fn f(p: SelectedValidatedProfileV1) { let _ = p.provenance; }"),
    ("body-proof-private", "E0616", "fn f(p: AdoptionBodyV1) { let _ = p.proof; }"),
    ("body-selection-private", "E0616", "fn f(p: AdoptionBodyV1) { let _ = p.selected; }"),
    ("adopted-body-private", "E0616", "fn f(p: AdoptedProof) { let _ = p.body; }"),
    ("provenance-fields-private", "E0616", "fn f(p: &LoaderProvenanceV1) { let _ = (p.source, p.validation_budget, p.identities); }"),
    ("carrier-not-clone", "E0277", "fn bound<T: Clone>() {} fn f() { bound::<SelectedValidatedProfileV1>(); }"),
    ("body-not-clone", "E0277", "fn bound<T: Clone>() {} fn f() { bound::<AdoptionBodyV1>(); }"),
    ("provenance-not-clone", "E0277", "fn bound<T: Clone>() {} fn f() { bound::<LoaderProvenanceV1>(); }"),
    ("adopted-not-clone", "E0277", "fn bound<T: Clone>() {} fn f() { bound::<AdoptedProof>(); }"),
    ("body-no-parts", "E0599", "fn f(p: AdoptionBodyV1) { let _ = p.into_parts(); }"),
    ("carrier-no-parts", "E0599", "fn f(p: SelectedValidatedProfileV1) { let _ = p.into_parts(); }"),
    ("body-no-owned-proof", "E0599", "fn f(p: AdoptionBodyV1) { let _ = p.into_proof(); }"),
    ("carrier-no-owned-proof", "E0599", "fn f(p: SelectedValidatedProfileV1) { let _ = p.into_proof(); }"),
    ("adopted-no-owned-proof", "E0599", "fn f(p: AdoptedProof) { let _ = p.into_proof(); }"),
    ("borrowed-proof-cannot-remint", "E0308", "fn f(p: &AdoptionBodyV1) { let _ = AdoptionBodyV1::ordinary(p.proof().clone()); }"),
    ("carrier-no-default", "E0277", "fn f() { let _: SelectedValidatedProfileV1 = Default::default(); }"),
    ("body-no-default", "E0277", "fn f() { let _: AdoptionBodyV1 = Default::default(); }"),
    ("carrier-no-proof-conversion", "E0277", "fn f(p: ValidatedSwiftReactor) { let _: SelectedValidatedProfileV1 = p.into(); }"),
    ("body-no-boolean-selected-mint", "E0599", "fn f(p: ValidatedSwiftReactor) { let _ = AdoptionBodyV1::selected(p, true); }"),
    ("carrier-no-digest-selected-mint", "E0599", "fn f(p: ValidatedSwiftReactor) { let _ = SelectedValidatedProfileV1::new(p, [0u8; 32]); }"),
    ("provenance-is-not-body-authority", "E0308", "fn f(p: &AdoptedProof) { let _ = RuntimeControl::adopt_body(p.selected_provenance().unwrap(), SwiftRunBudget::default(), Instant::now(), Cancellation::default()); }"),
    ("carrier-is-not-ordinary-proof", "E0308", "fn f(p: SelectedValidatedProfileV1) { let _ = RuntimeControl::adopt(p, SwiftRunBudget::default(), Instant::now(), Cancellation::default()); }"),
    ("selected-adopt-consumes-owner", "E0382", "fn f(p: SelectedValidatedProfileV1) { let _ = p.adopt(SwiftRunBudget::default(), Instant::now(), Cancellation::default()); let _ = p.adopt(SwiftRunBudget::default(), Instant::now(), Cancellation::default()); }"),
    ("provenance-cannot-outlive-owned-adoption", "E0515", "fn f(p: AdoptedProof) -> Option<&'static LoaderProvenanceV1> { p.selected_provenance() }"),
    ("provenance-cannot-extend-borrow", "lifetime may not live long enough", "fn f(p: &AdoptedProof) -> Option<&'static LoaderProvenanceV1> { p.selected_provenance() }"),
    ("provenance-cannot-outlive-body", "E0515", "fn f(p: AdoptionBodyV1) -> Option<&'static LoaderProvenanceV1> { p.selected_provenance() }"),
    ("provenance-cannot-be-mutably-borrowed", "E0308", "fn f(p: &mut AdoptedProof) { let _: &mut LoaderProvenanceV1 = p.selected_provenance().unwrap(); }"),
    ("adoption-cannot-drop-during-provenance-use", "E0505", "fn f(c: &mut RuntimeControl, p: AdoptedProof) { let q = p.selected_provenance(); let _ = c.drop_proof(p); std::hint::black_box(q); }"),
    ("body-cannot-drop-during-provenance-use", "E0505", "fn f(p: AdoptionBodyV1) { let q = p.selected_provenance(); drop(p); std::hint::black_box(q); }"),
    ("adoption-cannot-replace-during-provenance-use", "E0502", "fn f(p: &mut AdoptedProof, other: AdoptedProof) { let q = p.selected_provenance(); let _ = std::mem::replace(p, other); std::hint::black_box(q); }"),
    ("source-cannot-outlive-selected-owner", "E0515", "fn f(p: SelectedValidatedProfileV1) -> &'static [u8] { p.source() }"),
    ("production-has-no-test-provenance-accessor", "E0599", "fn f(p: &SelectedValidatedProfileV1) { let _ = p.test_provenance_v1(); }"),
]
PUBLIC = [
    ("public-validator-positive", None, "use mixer_vm::experimental_swift_reactor::{validate_swift_reactor, SwiftValidationBudget, ValidatedSwiftReactor}; use mixer_vm::Cancellation; fn f(b: &[u8]) -> Option<ValidatedSwiftReactor> { validate_swift_reactor(b, SwiftValidationBudget::default(), &Cancellation::default()).ok() }"),
    ("public-loader-is-private", "E0603", "use mixer_vm::experimental_swift_reactor::retained_profile_loader_v1::SelectedValidatedProfileV1; fn f(_: SelectedValidatedProfileV1) {}"),
    ("public-adopted-is-private", "E0603", "use mixer_vm::experimental_swift_reactor::control::AdoptedProof; fn f(_: AdoptedProof) {}"),
    ("public-control-is-private", "E0603", "use mixer_vm::experimental_swift_reactor::control::RuntimeControl; fn f(_: RuntimeControl) {}"),
    ("public-no-selected-reexport", "E0432", "use mixer_vm::experimental_swift_reactor::SelectedValidatedProfileV1; fn f(_: SelectedValidatedProfileV1) {}"),
]

def sha(b):
    return hashlib.sha256(b).hexdigest()

def ident(p):
    p = Path(p)
    b = p.read_bytes()
    return {"path": str(p), "bytes": len(b), "sha256": sha(b)}

def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def manifest(root):
    paths = sorted(p for p in root.rglob("*") if p.is_file())
    assert not any(p.is_symlink() for p in root.rglob("*"))
    members = [{"path": str(p.relative_to(root)), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in paths]
    return {"member_count": len(members), "members": members, "tree_sha256": sha(json.dumps(members, sort_keys=True, separators=(",", ":")).encode())}

def source_auth():
    seal = CANDIDATE / "seal.json"
    assert sha(seal.read_bytes()) == "83a7c57bc5f208b06a42384f14b4056040604ef01685a9dfbe8bbe32b832a7ad"
    selected = json.loads((CANDIDATE / "source-manifest.json").read_text())
    assert selected["member_count"] == 144
    assert selected["tree_sha256"] == "22b6e945a062b3465156bb9995bce610bd712fa9d3e283e176316d75104bb442"
    actual = manifest(SOURCE)
    assert actual["members"] == selected["members"]
    assert actual["tree_sha256"] == selected["tree_sha256"]
    tool = json.loads((CANDIDATE / "build-input-manifest.json").read_text())["tools"]["rustc"]
    assert str(RUSTC) == tool["path"]
    assert ident(RUSTC) == tool
    return actual

def flags(mode):
    result = [str(RUSTC), "--crate-name", "mixer_vm", "--edition=2021", "--target", "aarch64-apple-darwin", "-C", "opt-level=" + ("0" if mode == "debug" else "3"), "-C", "overflow-checks=yes", "-C", "panic=unwind"]
    for feature in FEATURES:
        result += ["--cfg", 'feature="' + feature + '"']
    return result

def run(label, argv, expected=None, env=None, variant=None):
    records = HERE / "commands"
    records.mkdir(exist_ok=True)
    folder = records / (f"{len(list(records.iterdir())) + 1:04d}-" + label)
    folder.mkdir()
    environment = env or {"PATH": "/usr/bin:/bin", "TMPDIR": str(WORK), "CARGO_MANIFEST_DIR": str(SOURCE)}
    started = time.monotonic()
    killed = None
    code = None
    with (folder / "stdout").open("wb") as out, (folder / "stderr").open("wb") as err:
        child = subprocess.Popen(argv, cwd=HERE, env=environment, stdout=out, stderr=err)
        try:
            while True:
                try:
                    code = child.wait(timeout=.05)
                    break
                except subprocess.TimeoutExpired:
                    if time.monotonic() - started > 55:
                        killed = "time"
                    if (folder / "stdout").stat().st_size + (folder / "stderr").stat().st_size > 1048576:
                        killed = "output"
                    if killed:
                        child.kill()
                        code = child.wait()
                        break
        finally:
            if child.poll() is None:
                child.kill()
            child.wait()
    stderr = (folder / "stderr").read_text(errors="replace")
    passed = not killed and (code == 0 if expected is None else code != 0 and expected in stderr)
    receipt = {"label": label, "argv": argv, "cwd": str(HERE), "environment": environment, "expected_diagnostic": expected, "expectation_met": passed, "exit_code": code, "timeout_seconds": 55, "output_byte_limit": 1048576, "supervisor_killed_for": killed, "elapsed_seconds": time.monotonic() - started, "terminally_waited": True, "compiler": ident(RUSTC), "runner": ident(__file__), "source_tree_sha256": source_auth()["tree_sha256"], "variant": variant, "stdout": ident(folder / "stdout"), "stderr": ident(folder / "stderr")}
    write(folder / "receipt.json", receipt)
    print(label + ": " + ("pass" if passed else "FAIL"), flush=True)
    if not passed:
        raise AssertionError((label, expected, code, stderr[-4000:]))
    return receipt

def sibling(mode, context, group):
    selected = CASES[group * 9:(group + 1) * 9]
    if context == "test":
        selected = [c for c in selected if c[0] != "production-has-no-test-provenance-accessor"]
    for name, diagnostic, body in selected:
        fixture = HERE / "fixtures" / (name + ".rs")
        fixture.parent.mkdir(exist_ok=True)
        fixture.write_text(PRELUDE + body + "\n")
        variant = WORK / (mode + "-" + context + "-" + name)
        shutil.copytree(SOURCE, variant)
        target = variant / "src/experimental_swift_reactor/mod.rs"
        delta = '\n#[allow(dead_code, unused_imports)] mod independent_privacy_case { include!(env!("MIXER_INDEPENDENT_PRIVACY_CASE")); }\n'
        target.write_text(target.read_text() + delta)
        vm = manifest(variant)
        info = {"fixture": ident(fixture), "mode": mode, "context": context, "append_path": "src/experimental_swift_reactor/mod.rs", "append_bytes": delta, "manifest": vm}
        write(HERE / "variants" / (mode + "-" + context + "-" + name + ".json"), info)
        env = {"PATH": "/usr/bin:/bin", "TMPDIR": str(WORK), "CARGO_MANIFEST_DIR": str(variant), "MIXER_INDEPENDENT_PRIVACY_CASE": str(fixture)}
        argv = flags(mode) + (["--test"] if context == "test" else ["--crate-type", "lib"])
        argv += ["--emit=metadata", str(variant / "src/lib.rs"), "-o", str(WORK / "case.rmeta")]
        try:
            run(mode + "-" + context + "-" + name, argv, diagnostic, env, info)
        finally:
            shutil.rmtree(variant)

def public(mode):
    library = WORK / ("libmixer_vm_" + mode + ".rmeta")
    run(mode + "-public-library", flags(mode) + ["--crate-type", "rlib", "--emit=metadata", str(SOURCE / "src/lib.rs"), "-o", str(library)])
    for name, diagnostic, body in PUBLIC:
        fixture = HERE / "fixtures" / (name + ".rs")
        fixture.parent.mkdir(exist_ok=True)
        fixture.write_text(body + "\n")
        info = {"fixture": ident(fixture), "library": ident(library), "mode": mode, "context": "separate-crate public import"}
        write(HERE / "variants" / (mode + "-" + name + ".json"), info)
        run(mode + "-" + name, [str(RUSTC), "--crate-type", "lib", "--edition=2021", "--extern", "mixer_vm=" + str(library), str(fixture), "--emit=metadata", "-o", str(WORK / "public-case.rmeta")], diagnostic, variant=info)

def main():
    WORK.mkdir(exist_ok=True)
    source_auth()
    if sys.argv[1] == "version":
        r = run("rustc-version", [str(RUSTC), "-vV"])
        expected = json.loads((CANDIDATE / "build-input-manifest.json").read_text())["tools"]["rustc_version_sha256"]
        assert r["stdout"]["sha256"] == expected
    elif sys.argv[1] == "public":
        public(sys.argv[2])
    elif sys.argv[1] == "matrix":
        for group in range(int(sys.argv[4]), 4):
            sibling(sys.argv[2], sys.argv[3], group)
    else:
        sibling(sys.argv[1], sys.argv[2], int(sys.argv[3]))

if __name__ == "__main__":
    main()
