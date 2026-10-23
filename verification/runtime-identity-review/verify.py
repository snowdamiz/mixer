#!/usr/bin/env python3
"""Independent frozen-source identity/parser/CLI/activation review. No devices."""
import concurrent.futures
import datetime
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
LOGS = OUT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)
REVISION = "fb4691a6fee4e3591f5d45adbcd1d6b93862b437"
PACKAGES = ["runtime-identity", "activation", "updates", "runtime", "contracts/runtime-identity-v1.json"]
NATIVE = ROOT / "runtime/.build/native-host-reclamation"
EXPECTED_NATIVE_SHA = "5053e0d03513bfd43c09863c6da0f01b578f55acf7b6157cae68134281da52ff"
EXPECTED_VM_REVISION = "64123c509e861ddd522631b293eadebdaca11341"

def sha(data): return hashlib.sha256(data).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def capture(command): return subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
def git(*args):
    result = capture(["git", *args])
    if result.returncode: raise ValueError(result.stdout)
    return result.stdout.strip()
def require(value, message):
    if not value: raise ValueError(message)

def manifest(folder, paths):
    entries = [{"path": str(path), "bytes": (folder / path).stat().st_size, "sha256": sha((folder / path).read_bytes())} for path in sorted(paths)]
    return dict(algorithm="SHA256 of canonical JSON source entries sorted by path", digest=sha(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()), files=entries)

def run(name, command, scope, expected_functions=None):
    started = now(); result = capture(command)
    path = LOGS / (name + ".log"); path.write_text(result.stdout)
    record = dict(name=name, command=list(map(str, command)), cwd=str(ROOT), startedAt=started, endedAt=now(), exitCode=result.returncode,
                  output=str(path.relative_to(ROOT)), outputSHA256=sha(path.read_bytes()), scope=scope)
    if expected_functions is not None:
        functions = sum(map(int, re.findall(r"Test run with (\d+) tests? in", result.stdout)))
        extra = sum(int(n) - 1 for n in re.findall(r"with (\d+) test cases passed", result.stdout))
        record.update(functions=functions, cases=functions + extra, expectedFunctions=expected_functions, countMatches=functions == expected_functions)
    return record

native_receipt = json.loads((NATIVE / "receipt.json").read_text())
native_sha = sha((NATIVE / "lib/libmixer_vm.a").read_bytes())
require(native_sha == EXPECTED_NATIVE_SHA == native_receipt["static_library_sha256"], "native archive changed")
require(native_receipt["source_revision"] == EXPECTED_VM_REVISION, "native VM source changed")
archive = subprocess.check_output(["git", "archive", "--format=tar", REVISION, *PACKAGES], cwd=ROOT)
commands = []
with tempfile.TemporaryDirectory(prefix="mixer-identity-final-review-") as temporary:
    export = Path(temporary) / "source"; export.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream: stream.extractall(export, filter="data")
    paths = [path.relative_to(export) for path in export.rglob("*") if path.is_file()]
    before = manifest(export, paths)
    require(sha((export / "runtime/Sources/CMixerVM/include/mixer_vm.h").read_bytes()) == native_receipt["header_sha256"], "C header does not match frozen archive receipt")
    shutil.copyfile(OUT / "IndependentIdentityParserTests.swift", export / "runtime-identity/Tests/MixerRuntimeIdentityTests/IndependentIdentityParserTests.swift")
    for name in ["IndependentIdentityBindingTests.swift", "IndependentIdentityExecutionTests.swift"]:
        shutil.copyfile(OUT / name, export / "activation/Tests/MixerActivationTests" / name)
    activation = ["swift", "test", "--package-path", str(export / "activation"), "-Xlinker", "-L" + str(NATIVE / "lib")]
    identity = ["swift", "test", "--package-path", str(export / "runtime-identity")]
    jobs = [
        ("identity-host", identity, "eight original and seven independent parser/encoding functions", 15),
        ("activation-host", activation, "thirteen original functions/fourteen cases and three independent public policy/factory functions", 16),
        ("updates-host", ["swift", "test", "--package-path", str(export / "updates")], "complete frozen update suite including new descriptor-file guards", 40),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        commands += list(executor.map(lambda job: run(*job), jobs))
    commands += [run("identity-release", identity + ["-c", "release"], "all fifteen identity/parser functions under release optimization", 15),
                 run("activation-independent-release", activation + ["-c", "release", "--filter", "IndependentIdentity"], "three independent policy/factory functions under release optimization", 3)]
    result = capture(["swift", "build", "--package-path", str(export / "runtime-identity"), "--show-bin-path"])
    require(result.returncode == 0, "missing CLI build path")
    tool = str(Path(result.stdout.strip().splitlines()[-1]) / "mixer-identity")
    vectors = str(export / "runtime-identity/Tests/MixerRuntimeIdentityTests/Fixtures/vectors.json")
    commands += [run("cli-oracle", [sys.executable, str(OUT / "cli-oracle.py"), "--tool", tool, "--vectors", vectors, "--revision", REVISION,
                 "--output", str(OUT / "final-cli-oracle.json")], "independent restricted deterministic CBOR/SHA256 oracle and bounded CLI input matrix"),
                 run("fixed-fifo-race", [sys.executable, str(OUT / "probe-fifo-race.py"), "--tool", tool, "--vectors", vectors, "--revision", REVISION,
                 "--output", str(OUT / "fixed-fifo-race.json")], "same isolated regular/FIFO replacement probe that previously reproduced blocking and stream admission")]
    unchanged = before == manifest(export, paths)
    test_entries = [{"path": name, "sha256": sha((OUT / name).read_bytes())} for name in ["IndependentIdentityParserTests.swift", "IndependentIdentityBindingTests.swift", "IndependentIdentityExecutionTests.swift"]]

oracle = json.loads((OUT / "final-cli-oracle.json").read_text())
fifo = json.loads((OUT / "fixed-fifo-race.json").read_text())
fifo_pass = (fifo["attempts"] == 80 and not fifo["confirmedFIFOAccepted"] and not fifo["unconfirmedTimeout"] and fifo["threadError"] is None and fifo["threadStopped"])
references = []
for name in ["initial-mixed-host-reproduction.json", "fixed-mixed-host-reproduction.json", "initial-fifo-race.json", "fifo-race-frozen-replay.json", "initial-cli-oracle.json", "final-cli-oracle.json", "fixed-fifo-race.json"]:
    references.append(dict(path=str((OUT / name).relative_to(ROOT)), sha256=sha((OUT / name).read_bytes())))
receipt = dict(schemaVersion=1, createdAt=now(), reviewer=dict(model="gpt-6.1-sol", reasoningEffort="xhigh", independent=True),
    reviewedRevision=REVISION, reviewedTree=git("rev-parse", REVISION + "^{tree}"), packages=PACKAGES, gitArchiveSHA256=sha(archive),
    source=before, sourceUnchangedDuringRun=unchanged, productionSourceModified=False, addedTests=test_entries, commands=commands,
    originalNativeVM=dict(sourceRevision=EXPECTED_VM_REVISION, reusedStaticArchive=True, archiveSHA256=native_sha,
        headerSHA256=native_receipt["header_sha256"], receiptSHA256=sha((NATIVE / "receipt.json").read_bytes()),
        scope="exact previously frozen host artifact reused; no third-party VM and no fresh Rust rebuild; Swift tests execute original tiny VM fixtures, not full Swift guests"),
    probes=dict(validCLIOracleCases=oracle["validOracleCases"], rejectedCLIFileOrWireCases=oracle["invalidFileOrWireCases"],
        CLIOraclePassed=oracle["passed"], finalFIFOAttempts=fifo["attempts"], finalFIFORacePassed=fifo_pass, references=references),
    findings=[
        dict(id="IDENTITY-REVIEW-01", severity="P2", status="fixed and independently replayed", discoveredRevision="6cb27591319a2066e1eb8b3025400137373cb2d6",
             description="Descriptor-derived execution accepted a same-fingerprint verifier host with changed scope/protocol/state/payload/memory/fuel/startup policy",
             reproduction="initial-mixed-host-reproduction.json", originalFailures=7, fixRevision="188e88ad4429397a22b9c578ebb2b769475a26e9",
             fix="Private immutable full host binding retained for descriptor-derived execution; exact represented policy checked at public runtime open; explicit legacy string API unchanged"),
        dict(id="IDENTITY-REVIEW-02", severity="P2", status="fixed and independently replayed", discoveredRevision="188e88ad4429397a22b9c578ebb2b769475a26e9",
             description="Path metadata check followed by blocking open allowed regular-file replacement with FIFO; retained writer rescued blocked CLI and supplied accepted descriptor bytes",
             reproduction="fifo-race-frozen-replay.json", firstObservedAttempt=12, independentReplayAttempt=4, fixRevision=REVISION,
             fix="Nonblocking no-follow close-on-exec open, then fstat actual descriptor type/size and bounded reads; explicit final symlink and malformed URL rejection")],
    observations=["Closed descriptor includes every declared field in the hash; public policy factory derives represented host/VM values rather than reparsing release-selected inputs",
        "NUL domain, shortest unsigned lengths, deterministic encoded-key ordering, exact scalar UTF8 export spelling, strict numeric/duplicate/type/resource behavior exercised against an independently authored stdlib oracle",
        "Declared fingerprints identify descriptor contents, not complete/true captured build graphs or artifact provenance; no attestation authority is inferred",
        "Capabilities remain declarations; activation rejects all nonempty capability maps and does not enable native guest imports",
        "Subpage linear-memory ceilings round down to native pages, never expand authority; exact profile enum mapping and legacy trusted string-policy semantics preserved"],
    tools=dict(host=platform.platform(), python=sys.version, swift=capture(["swift", "--version"]).stdout.strip(), xcode=capture(["xcodebuild", "-version"]).stdout.strip()),
    runnerSHA256=sha(Path(__file__).read_bytes()), probeSources=[dict(path=name, sha256=sha((OUT / name).read_bytes())) for name in ["cli-oracle.py", "probe-fifo-race.py"]],
    specification="https://www.rfc-editor.org/rfc/rfc8949.html#section-4.2.1",
    limitations=["No proof of actual complete build-input capture, supplied hash truth, native graph/artifact attestation, binary embedding, signing/store publication or native dependency shipping",
        "Descriptor trust-root/grant/permission file hashes do not bind actual separately supplied policy objects to file bytes; complete installed native identity provenance remains a build-pipeline gate",
        "Current activation has no capability imports; no FieldLog guest/UI/plugin or general Swift guest acceptance implied",
        "No physical commands or new independent cross-platform qualification; root-owned host/iOS/Android/simulator qualification is separate",
        "The FIFO replay is a bounded scheduling probe, not exhaustive filesystem fuzzing or hard real-time I/O proof; Rust VM archive is reused and not sanitizer-instrumented here",
        "External audit, continuous fuzzing, actual immutable published runtime identity/graph capture and all corresponding GA gates remain open"],
    deviceCommandsAttempted=False, sourceOrStorePublication=False, GAAccepted=False)
receipt["scopedChecksPassed"] = unchanged and fifo_pass and oracle["passed"] and all(c["exitCode"] == 0 and c.get("countMatches", True) for c in commands)
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(dict(passed=receipt["scopedChecksPassed"], revision=REVISION, tree=receipt["reviewedTree"], sourceDigest=before["digest"], archiveSHA256=sha(archive),
    commands=[{key: c[key] for key in ["name", "exitCode", "functions", "cases"] if key in c} for c in commands], fifoPassed=fifo_pass, oraclePassed=oracle["passed"]), indent=2))
raise SystemExit(0 if receipt["scopedChecksPassed"] else 1)
