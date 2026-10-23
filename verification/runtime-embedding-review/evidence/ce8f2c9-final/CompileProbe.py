#!/usr/bin/env python3
"""Compile generated source in Swift 6 mode; corrupt constants and recompile."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from ReviewTests import C, Review, SEED, SOURCE, TOOL, embed

WORK = Path(os.environ["EMBED_REVIEW_WORK"])
OUT = Path(os.environ["EMBED_REVIEW_OUTPUT"])
SWIFT = Path(os.environ["EMBED_REVIEW_SWIFT"])

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    receipt = {"schema": 1, "commands": [], "cases": [], "status": "running"}
    def run(name, command, expected=0):
        command = [str(x) for x in command]; start = time.monotonic()
        result = subprocess.run(command, capture_output=True, timeout=300)
        logs = {}
        for kind, data in [("stdout", result.stdout), ("stderr", result.stderr)]:
            path = OUT / (name + "." + kind); path.write_bytes(data)
            logs[kind] = {"path": path.name, "sha256": sha(path), "bytes": len(data)}
        receipt["commands"].append({"name": name, "argv": command, "exit_code": result.returncode,
            "host_development_elapsed_seconds": round(time.monotonic()-start, 6), "output": logs})
        print(name + ": " + str(result.returncode), flush=True)
        if result.returncode != expected: raise RuntimeError("unexpected result: " + name + ": " + result.stderr.decode()[-4000:])
        return result
    fixture = Review(); fixture.setUp()
    try:
        raw = fixture.stored()
        descriptor = raw + b" " * (131072 - len(raw))
        fixture.write_descriptor(descriptor)
        expected = json.loads(run("trusted-inspect-exact-max", [TOOL, "inspect", fixture.snapshot / "descriptor.json"]).stdout)
        emitted = fixture.emit()
        generated = (fixture.output / "MixerInstalledRuntime.swift").read_bytes()
        (OUT / "exact-max-generated.swift").write_bytes(generated)
        (OUT / "exact-max-embedding.json").write_text(json.dumps(emitted, indent=2) + "\n")
        receipt["exact_max"] = {"descriptor_bytes": len(descriptor), "descriptor_sha256": hashlib.sha256(descriptor).hexdigest(),
            "generated_bytes": len(generated), "generated_sha256": hashlib.sha256(generated).hexdigest(),
            "fingerprint": fixture.fingerprint}
        package = WORK / "consumer"; sources = package / "Sources/Consumer"; sources.mkdir(parents=True)
        manifest = '''// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "EmbeddingReview", platforms: [.macOS(.v14)],
    dependencies: [.package(path: "../source/runtime-identity")],
    targets: [.executableTarget(name: "Consumer", dependencies: [
        .product(name: "MixerRuntimeIdentity", package: "runtime-identity")])],
    swiftLanguageModes: [.v6])
'''
        (package / "Package.swift").write_text(manifest)
        source = sources / "MixerInstalledRuntime.swift"; source.write_bytes(generated)
        (sources / "main.swift").write_text('''import Foundation
import MixerRuntimeIdentity
do {
    let identity = try MixerInstalledRuntime.load()
    let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
    print(String(decoding: try encoder.encode(identity.installedRuntime), as: UTF8.self))
    print(String(decoding: try encoder.encode(identity.descriptor), as: UTF8.self))
    let execution = ["fingerprint": identity.fingerprint, "profile": identity.execution.profile,
        "startupExport": identity.execution.startupExport, "operandStack": String(identity.execution.operandStack),
        "callDepth": String(identity.execution.callDepth), "hostCalls": String(identity.execution.hostCalls)]
    print(String(decoding: try encoder.encode(execution), as: UTF8.self))
} catch {
    FileHandle.standardError.write(Data("LOAD_ERROR:\\(error)".utf8)); exit(7)
}
''')
        receipt["consumer_source_manifest"] = {p.relative_to(package).as_posix(): sha(p) for p in sorted(package.rglob("*")) if p.is_file()}
        fixture.tearDown()
        receipt["original_data_removed_before_compilation"] = not fixture.root.exists()
        command = [SWIFT, "build", "--package-path", package, "-c", "release", "--product", "Consumer", "-j", "4",
                   "-Xswiftc", "-strict-concurrency=complete", "-Xswiftc", "-warnings-as-errors"]
        run("strict6-exact-max-build", command)
        resolved = package / "Package.resolved"
        shutil.copyfile(resolved, OUT / "consumer-Package.resolved")
        receipt["resolved_dependencies"] = {"sha256": sha(resolved), "pins": json.loads(resolved.read_bytes())["pins"]}
        binary = Path(run("strict6-binary-location", [SWIFT, "build", "--package-path", package, "-c", "release", "--show-bin-path"]).stdout.decode().strip()) / "Consumer"
        loaded = run("strict6-exact-max-run", [binary])
        lines = loaded.stdout.splitlines()
        if len(lines) != 3: raise ValueError("unexpected compiled output")
        if json.loads(lines[0]) != expected["installedRuntime"]: raise ValueError("installed policy mismatch")
        if json.loads(lines[1]) != json.loads(descriptor): raise ValueError("complete descriptor policy mismatch")
        desired = {"fingerprint": fixture.fingerprint, "profile": "mixer-table-memory-v3", "startupExport": fixture.raw["execution"]["startup_export"],
                   "operandStack": "71", "callDepth": "9", "hostCalls": "3"}
        if json.loads(lines[2]) != desired: raise ValueError("execution policy mismatch")
        receipt["cases"].append({"name": "exact-max-malicious-Unicode-full-policy", "status": "passed", "binary_sha256": sha(binary)})
        needle = base64.b64encode(descriptor)
        valid_edited = json.loads(descriptor); valid_edited["execution"]["host_calls"] = 4
        invalid_policy = json.loads(descriptor); invalid_policy["execution"]["host_calls"] = 1025
        cases = [
            ("invalid-base64", b"?", "encoding"),
            ("invalid-utf8", base64.b64encode(b"\xff"), None),
            ("invalid-json", base64.b64encode(b"{"), None),
            ("duplicate-json-fields", base64.b64encode(b'{"schema":1,"schema":1}'), None),
            ("unsupported-policy", base64.b64encode(C.canonical(invalid_policy)), "Invalid installed runtime identity: number"),
            ("edited-valid-policy", base64.b64encode(C.canonical(valid_edited)), "fingerprintMismatch"),
            ("oversized-compiled-descriptor", base64.b64encode(descriptor + b" "), None),
        ]
        for name, encoded, diagnostic in cases:
            changed = generated.replace(needle, encoded)
            if changed == generated: raise ValueError("source mutation did not apply")
            source.write_bytes(changed); run(name + "-build", command)
            result = run(name + "-run", [binary], expected=7)
            if result.stdout or not result.stderr.startswith(b"LOAD_ERROR:"): raise ValueError("invalid identity exposed policy")
            if diagnostic and diagnostic.encode() not in result.stderr: raise ValueError("wrong failure: " + name)
            receipt["cases"].append({"name": name, "status": "rejected", "source_sha256": sha(source), "binary_sha256": sha(binary)})
        changed_fp = ("0" if fixture.fingerprint[0] != "0" else "1") + fixture.fingerprint[1:]
        source.write_bytes(generated.replace(('fingerprint = "' + fixture.fingerprint + '"').encode(), ('fingerprint = "' + changed_fp + '"').encode()))
        run("changed-fingerprint-build", command)
        result = run("changed-fingerprint-run", [binary], expected=7)
        if result.stdout or b"fingerprintMismatch" not in result.stderr: raise ValueError("changed fingerprint accepted")
        receipt["cases"].append({"name": "changed-pinned-fingerprint", "status": "rejected", "source_sha256": sha(source), "binary_sha256": sha(binary)})
        receipt["status"] = "passed real compiled Swift 6 consumer and eight recompiled invalid constants"
    except BaseException as error:
        receipt["status"] = "failed"; receipt["error"] = str(error); raise
    finally:
        if fixture.root.exists(): fixture.tearDown()
        (OUT / "compiled-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

if __name__ == "__main__": main()
