#!/usr/bin/env python3
"""Independent frozen-data checks and bounded host SwiftPM manifest probe.

No producer harness or product module is imported/executed. SwiftPM evaluates
the copied first-party manifest only; no dependency resolution or build runs.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = HERE / "inputs/verification/android-copied-sdk-appearance-contract"
SOURCE = PACKET / "source-inputs"
RUN = HERE / "host-probe"
RUN.mkdir(exist_ok=True)
commands = []


def identity(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def execute(label, argv, env=None):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        completed = subprocess.run(argv, cwd=HERE, env=env, capture_output=True, timeout=60)
        code, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as error:
        code, stdout, stderr = "timeout", error.stdout or b"", error.stderr or b""
    (RUN / (label + ".stdout")).write_bytes(stdout)
    (RUN / (label + ".stderr")).write_bytes(stderr)
    commands.append({"label": label, "argv": list(map(str, argv)), "cwd": str(HERE),
                     "started_utc": started, "exit_code": code,
                     "stdout": identity(RUN / (label + ".stdout")),
                     "stderr": identity(RUN / (label + ".stderr"))})
    (HERE / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    return code, stdout


source_manifest = json.loads((PACKET / "source-manifest.json").read_text())
observation = json.loads((PACKET / "proposed-profile-observation.json").read_text())
packaging = json.loads((SOURCE / "verification/android-default-appearance-packaging/run-2/product-before.json").read_text())
sdk = source_manifest["sdk_projection"]
adapter = source_manifest["adapter_projection"]
assert len(sdk) == 22 and len(adapter) == 20
assert all(identity(SOURCE / p) == source_manifest["files"][p] for p in sdk + adapter)
assert all(identity(SOURCE / p) == packaging["files"][p] for p in sdk + adapter)
sdk_map = {str(Path(p).relative_to("sdk")): identity(SOURCE / p) for p in sdk}
adapter_map = {}
for path in adapter:
    label = str(Path(path).relative_to("native/android"))
    if label.startswith("engine/"):
        label = label[len("engine/"):]
    adapter_map[label] = identity(SOURCE / path)


def digest_map(mapping):
    return hashlib.sha256(b"".join((p + "\0" + v["sha256"] + "\n").encode()
                                   for p, v in sorted(mapping.items()))).hexdigest()


assert sdk_map == observation["sdk_files"]
assert adapter_map == observation["adapter_files"]
assert digest_map(sdk_map) == observation["sdk_compatibility_sha256"]
assert digest_map(adapter_map) == observation["adapter_compatibility_sha256"]
conditional_lines = []
for path in sdk + adapter:
    if path.endswith(".swift"):
        for n, line in enumerate((SOURCE / path).read_text().splitlines(), 1):
            if line.lstrip().startswith(("#if", "#elseif", "#else", "#endif")):
                conditional_lines.append({"path": path, "line": n, "text": line})

swift = shutil.which("swift")
assert swift
version_code, version = execute("swift-version", [swift, "--version"])
assert version_code == 0
assert b"Swift version 6.4" in version, "Probe filename deliberately bound to observed Swift 6.4"

for candidate in ("baseline", "alternate-manifest"):
    directory = RUN / candidate
    directory.mkdir(exist_ok=True)
    for path in sdk:
        destination = directory / Path(path).relative_to("sdk")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((SOURCE / path).read_bytes())

alternate = RUN / "alternate-manifest"
manifest = (alternate / "Package.swift").read_text()
needle = '.target(name: "MixerUI", dependencies: ["MixerCore"])'
assert manifest.count(needle) == 1
manifest = manifest.replace(needle, '.target(name: "MixerUI", dependencies: ["MixerCore"], path: "Sources/UnreviewedUI")')
(alternate / "Package@swift-6.4.swift").write_text(manifest)
unreviewed = alternate / "Sources/UnreviewedUI/Unreviewed.swift"
unreviewed.parent.mkdir(parents=True, exist_ok=True)
unreviewed.write_text("public let unreviewedManifestSelected = true\n")

summaries = {}
try:
    for candidate in ("baseline", "alternate-manifest"):
        directory = RUN / candidate
        expected_map = {p: identity(directory / p) for p in sdk_map}
        assert expected_map == sdk_map
        env = os.environ.copy()
        env["CLANG_MODULE_CACHE_PATH"] = str(RUN / "module-cache")
        env["SWIFTPM_MODULECACHE_OVERRIDE"] = str(RUN / "module-cache")
        args = [swift, "package", "--package-path", str(directory),
                "--cache-path", str(RUN / "cache"), "--config-path", str(RUN / "config"),
                "--security-path", str(RUN / "security"), "--scratch-path", str(RUN / "scratch" / candidate),
                "dump-package"]
        code, stdout = execute(candidate + "-dump-package", args, env)
        assert code == 0, candidate
        decoded = json.loads(stdout)
        targets = {t["name"]: {k: t[k] for k in ("name", "path", "dependencies", "settings") if k in t}
                   for t in decoded["targets"]}
        summaries[candidate] = {"profile_map_equal": True, "profile_digest": digest_map(expected_map),
                                "package_name": decoded["name"], "targets": targets,
                                "sdk_files": {p.relative_to(directory).as_posix(): identity(p)
                                              for p in sorted(directory.rglob("*")) if p.is_file()}}
    assert summaries["baseline"]["targets"]["MixerUI"].get("path") is None
    assert summaries["alternate-manifest"]["targets"]["MixerUI"]["path"] == "Sources/UnreviewedUI"
finally:
    cleanup = []
    for name in ("cache", "config", "security", "scratch", "module-cache"):
        path = RUN / name
        if path.exists():
            shutil.rmtree(path)
        cleanup.append({"path": str(path.relative_to(HERE)), "absent": not path.exists()})
    (HERE / "cleanup.json").write_text(json.dumps(cleanup, indent=2) + "\n")

result = {"schema": "mixer.independent-contract-review.probe.v1",
          "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "python_version": platform.python_version(),
          "sdk_file_count": len(sdk), "adapter_file_count": len(adapter),
          "all_42_match_frozen_packaging_source_manifest": True,
          "sdk_projection_sha256": digest_map(sdk_map), "adapter_projection_sha256": digest_map(adapter_map),
          "swift_conditional_directives_in_42_file_projection": conditional_lines,
          "alternate_manifest": summaries,
          "finding": "A copied Package@swift-6.4.swift redirects MixerUI to an unreviewed source directory while the entire proposed 22-file profile stays equal.",
          "scope": "Frozen-source identity validation and host SwiftPM manifest selection only; not app compilation, codec/runtime behavior, ABI, distribution or release acceptance."}
(HERE / "probe-result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "alternate_manifest"}, indent=2))
