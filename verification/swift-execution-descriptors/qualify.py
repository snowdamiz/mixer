#!/usr/bin/env python3
"""Qualify this bounded overlay on an isolated immutable baseline; no target execution."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASELINE = "bd8a8967d32692765de0d4dd14f5d88b7d5009ff"
OWNED = [
    "vm/src/experimental/descriptors.rs",
    "vm/src/experimental/mod.rs",
    "vm/src/experimental/policy.rs",
    "vm/src/experimental/swift.rs",
    "vm/src/experimental/swift_descriptor_tests.rs",
]
FEATURES = "experimental-swift-reactor,experimental-span-execution"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(directory):
    items = []
    for file in sorted((directory / "vm").rglob("*")):
        if file.is_file() and "target" not in file.relative_to(directory).parts:
            items.append({"path": str(file.relative_to(directory)), "sha256": sha(file.read_bytes())})
    return {"files": items, "digest": sha(json.dumps(items, sort_keys=True).encode())}


def declaration(source, marker):
    start = source.index(marker)
    opened = source.index("{", start)
    depth = 1
    end = opened + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=HERE / "2026-10-23-host")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PATH"] = "/opt/homebrew/opt/rustup/bin:" + env.get("PATH", "")
    cargo = shutil.which("cargo", path=env["PATH"])
    rustc = shutil.which("rustc", path=env["PATH"])
    if not cargo or not rustc:
        raise RuntimeError("Rust toolchain is required")
    receipt = {
        "baseline": BASELINE,
        "scope": "borrowed Swift execution descriptor prerequisite only",
        "targetExecution": False,
        "physicalDevices": "pending; phones disconnected; no discovery or runs attempted",
        "publication": False,
        "commands": [],
        "limitations": [
            "Host validation/borrow tests do not qualify reactor execution or any GA gate.",
            "The actual 53,777,114-byte target is never instantiated, initialized or invoked.",
            "Isolated candidate contains baseline VM plus only the five owned source files; concurrent root changes are excluded.",
            "Allocator observations cover requested operations on the test thread, not RSS or allocator overhead.",
            "Pointer-width-specific layout assertions qualify aarch64-apple-darwin with the recorded toolchain only.",
        ],
        "verificationInputs": [
            {"path": file.name, "sha256": sha(file.read_bytes())}
            for file in sorted(HERE.iterdir()) if file.is_file()
        ],
    }

    def save():
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def run(label, command, cwd, expected=0, codes=None):
        started = time.monotonic()
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True)
        stdout = output / (label + ".stdout")
        stderr = output / (label + ".stderr")
        stdout.write_bytes(result.stdout)
        stderr.write_bytes(result.stderr)
        observed_codes = []
        if codes is not None:
            for line in result.stderr.splitlines():
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if message.get("level") == "error" and message.get("code"):
                    observed_codes.append(message["code"]["code"])
        passed = result.returncode == expected
        if codes is not None:
            passed &= sorted(observed_codes) == sorted(codes)
        receipt["commands"].append({
            "label": label, "command": [str(value) for value in command], "cwd": str(cwd),
            "seconds": time.monotonic() - started, "exitCode": result.returncode,
            "expectedExitCode": expected, "expectedErrorCodes": codes, "observedErrorCodes": observed_codes,
            "stdout": {"path": stdout.name, "sha256": sha(result.stdout)},
            "stderr": {"path": stderr.name, "sha256": sha(result.stderr)}, "passed": passed,
        })
        save()
        print(label + (": PASS" if passed else ": FAIL"), flush=True)
        if not passed:
            raise RuntimeError("Command failed: " + label)
        return result.stdout

    run("rustc-version", [rustc, "--version", "--verbose"], ROOT)
    run("cargo-version", [cargo, "--version", "--verbose"], ROOT)
    run("python-version", [shutil.which("python3"), "--version"], ROOT)
    run("host", ["uname", "-a"], ROOT)
    receipt["headAtStart"] = run("head", ["git", "rev-parse", "HEAD"], ROOT).decode().strip()
    receipt["baselineVmTree"] = run("baseline-vm-tree", ["git", "rev-parse", BASELINE + ":vm"], ROOT).decode().strip()
    with tempfile.TemporaryDirectory(prefix="mixer-swift-descriptors-") as temporary:
        checkout = Path(temporary) / "checkout"
        checkout.mkdir()
        archive = subprocess.run(["git", "archive", BASELINE, "vm"], cwd=ROOT, check=True, capture_output=True).stdout
        receipt["baselineArchiveSha256"] = sha(archive)
        with tarfile.open(fileobj=io.BytesIO(archive)) as archive_file:
            archive_file.extractall(checkout, filter="data")
        baseline = inventory(checkout)
        receipt["baselineSource"] = baseline
        baseline_text = {path: (checkout / path).read_text() for path in OWNED if (checkout / path).exists()}
        module = checkout / "vm/src/experimental/mod.rs"
        module.write_text(module.read_text() + "\n" + (HERE / "baseline-layout-probe.rs").read_text())
        env["CARGO_TARGET_DIR"] = str(Path(temporary) / "target")
        receipt["environmentOverrides"] = {"PATH": env["PATH"], "CARGO_TARGET_DIR": env["CARGO_TARGET_DIR"]}
        command = [cargo, "test", "--locked", "--manifest-path", "vm/Cargo.toml"]
        for release in [False, True]:
            mode = "release" if release else "debug"
            flags = ["--release"] if release else []
            run("baseline-" + mode + "-layouts", command + flags + ["--features", FEATURES, "--lib", "descriptor_baseline_layout", "--", "--nocapture"], checkout)
        for path in OWNED:
            (checkout / path).write_bytes((ROOT / path).read_bytes())
        candidate = inventory(checkout)
        receipt["candidateSource"] = candidate
        receipt["overlay"] = [{"path": path, "sha256": sha((checkout / path).read_bytes())} for path in OWNED]
        changed = [item["path"] for item in candidate["files"] if item not in baseline["files"]]
        assert sorted(changed) == sorted(OWNED), changed
        comparisons = {}
        for path, markers in {
            "vm/src/experimental/mod.rs": ["pub struct ValidatedSpans {", "pub struct SegmentView<'a> {", "impl ValidatedSpans {"],
            "vm/src/experimental/swift.rs": ["pub struct ValidatedSwiftReactor {", "impl ValidatedSwiftReactor {"],
        }.items():
            current = (checkout / path).read_text()
            for marker in markers:
                old = declaration(baseline_text[path], marker)
                new = declaration(current, marker)
                assert old == new, (path, marker)
                comparisons[path + ":" + marker] = sha(old.encode())
        descriptors = "vm/src/experimental/descriptors.rs"
        current = (checkout / descriptors).read_text()
        assert baseline_text[descriptors].split("impl ValidatedSpans {", 1)[1] == current.split("impl ValidatedSpans {", 1)[1]
        for name in ["SignatureView", "GlobalView"]:
            old = declaration(baseline_text[descriptors], "pub(super) struct " + name)
            new = declaration(current, "pub(crate) struct " + name)
            assert old.replace("pub(super)", "pub(crate)").replace("    pub ", "    pub(crate) ") == new
        policy = "vm/src/experimental/policy.rs"
        assert baseline_text[policy].replace("pub(super) enum Policy", "pub(crate) enum Policy") == (checkout / policy).read_text()
        for path in ["vm/src/experimental/mod.rs", "vm/src/experimental/swift.rs"]:
            tail = "pub fn validate_spans(" if path.endswith("mod.rs") else "\nfn usage(raw:"
            assert baseline_text[path].split(tail, 1)[1] == (checkout / path).read_text().split(tail, 1)[1]
        receipt["preservedLiteralDefinitions"] = comparisons
        receipt["sourceComparisonPassed"] = True
        save()
        run("candidate-rustfmt-check", [shutil.which("rustfmt", path=env["PATH"]), "--check", "--config", "skip_children=true", "--edition", "2021"] + OWNED, checkout)
        for release in [False, True]:
            mode = "release" if release else "debug"
            flags = ["--release"] if release else []
            run(mode + "-swift-only-descriptors", command + flags + ["--features", "experimental-swift-reactor", "--lib", "swift_descriptor", "--", "--nocapture"], checkout)
            run(mode + "-default-unit", command + flags + ["--lib"], checkout)
            run(mode + "-combined-unit", command + flags + ["--features", FEATURES, "--lib", "--", "--nocapture"], checkout)
            integration = ["experimental_stream", "span_function_cache", "span_execution", "span_function_cache_allocations", "span_execution_allocations", "swift_reactor_validation", "swift_reactor_validation_allocations"]
            selections = [arg for name in integration for arg in ["--test", name]]
            run(mode + "-public-regressions", command + flags + ["--features", FEATURES] + selections + ["--", "--nocapture"], checkout)
            run(mode + "-doctests", command + flags + ["--features", FEATURES, "--doc"], checkout)
            run(mode + "-public-build", [cargo, "build", "--locked", "--manifest-path", "vm/Cargo.toml", "--features", FEATURES, "--lib"] + flags, checkout)
            library = Path(env["CARGO_TARGET_DIR"]) / mode / "libmixer_vm.rlib"
            rust_command = [rustc, "--edition=2021", "--crate-type=lib", "--emit=metadata", "--error-format=json", "--extern", "mixer_vm=" + str(library), "-o", str(Path(temporary) / "probe.rmeta")]
            cases = {"public-control": ("fn f(p: &ValidatedSwiftReactor) { let _: &[u8] = p.source(); let _ = p.observations(); }", None)}
            methods = {"execution_signature": "0", "execution_type": "0", "execution_function": "34", "execution_global": "0", "execution_global_initializer_offset": "0", "execution_data": "0", "execution_element": "0", "execution_global_count": "", "execution_data_count": "", "execution_element_count": "", "execution_memory": "", "execution_table": "", "execution_imports": "", "decode_policy": ""}
            for name, arguments in methods.items():
                cases["private-" + name] = ("fn f(p: &ValidatedSwiftReactor) { let _ = p." + name + "(" + arguments + "); }", ["E0624"])
            cases.update({
                "private-descriptor-module": ("use mixer_vm::experimental::descriptors::SignatureView;", ["E0603"]),
                "private-policy-module": ("use mixer_vm::experimental::policy::Policy;", ["E0603"]),
                "private-metadata": ("fn f(p: ValidatedSwiftReactor) { let _ = p.metadata; }", ["E0616"]),
                "source-lifetime": ("fn f(p: ValidatedSwiftReactor) -> &'static [u8] { p.source() }", ["E0515"]),
                "source-drop": ("fn f(p: ValidatedSwiftReactor) { let bytes = p.source(); drop(p); std::hint::black_box(bytes); }", ["E0505"]),
                "source-mutation": ("fn f(p: &ValidatedSwiftReactor) { p.source()[0] = 0; }", ["E0594"]),
                "proof-clone": ("fn f(p: ValidatedSwiftReactor) { let _ = p.clone(); }", ["E0599"]),
                "legacy-conversion": ("fn f(p: ValidatedSwiftReactor) -> mixer_vm::experimental::ValidatedSpans { p }", ["E0308"]),
            })
            for name, (body, codes) in cases.items():
                probe = Path(temporary) / (name.replace("-", "_") + ".rs")
                probe.write_text("use mixer_vm::experimental_swift_reactor::ValidatedSwiftReactor;\n" + body + "\n")
                run(mode + "-" + name, rust_command + [str(probe)], checkout, expected=1 if codes else 0, codes=codes)
        # Trusted in-crate code can use the views but cannot make their borrows
        # escape the proof or mutate the borrowed storage. Compile the literal
        # hand-authored negative source without cfg(test), then restore it.
        original_module = module.read_bytes()
        try:
            module.write_bytes(original_module + b"\n" + (HERE / "borrow-negatives.rs").read_bytes())
            run("internal-borrow-negatives", [rustc, "--edition=2021", "--crate-name=mixer_descriptor_negative", "--crate-type=rlib", "--emit=metadata", "--error-format=json", "--cfg", 'feature="experimental-stream-validation"', "--cfg", 'feature="experimental-swift-wasi"', "--cfg", 'feature="experimental-swift-reactor"', "vm/src/lib.rs", "-o", str(Path(temporary) / "negative.rmeta")], checkout, expected=1, codes=["E0515"] * 8 + ["E0594"] * 6)
        finally:
            module.write_bytes(original_module)
        assert inventory(checkout) == candidate
        for path in OWNED:
            assert (ROOT / path).read_bytes() == (checkout / path).read_bytes(), "Owned source changed during run: " + path
        receipt["passed"] = True
        save()
    print("Receipt: " + str(output / "receipt.json"), flush=True)


if __name__ == "__main__":
    main()
