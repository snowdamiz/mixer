#!/usr/bin/env python3
"""Build-only preparation; sealed run is root-only after independent review.

No native operation occurs on import, verify, or prepare. Only `run`/`cleanup`
address a simulator. They never address physical devices or baseline instances.
"""
import argparse
import join_support
import hashlib
import gzip
import io
import importlib.util
import json
import os
import pathlib
import plistlib
import secrets
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import tarfile
import time
import uuid
from bridge import Bridge, server_for, json_bytes, require
from oracle import CASES

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DEVELOPER = pathlib.Path("/Applications/Xcode_26.6.app/Contents/Developer")
RUNTIME = "com.apple.CoreSimulator.SimRuntime.iOS-26-5"
DEVICE_TYPE = "com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro"
RUNTIME_BUILD = "23F77"
PRODUCTS = BASE / "build/Build/Products"
PRODUCT_ARCHIVE = BASE / "test-runner-products.tar.gz"
RUN_DIR = BASE / "runtime"
SOURCE_REVISION_CONTEXT = "ef7510043e8ea9fc55dd7555dc91e9265b0215e3"
import apps as packet

def write(path, value):
    payload = json_bytes(value) + b"\n"
    descriptor, name = tempfile.mkstemp(prefix=".receipt-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream: stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if os.path.exists(name): os.unlink(name)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def tree(path):
    result = {}
    for entry in sorted(path.rglob("*")):
        relative = str(entry.relative_to(path)); mode = entry.lstat().st_mode
        if stat.S_ISLNK(mode):
            require(entry.resolve().is_relative_to(path.resolve()), "Product symlink escapes build tree")
            result[relative] = {"kind": "symlink", "target": os.readlink(entry)}
        elif stat.S_ISREG(mode): result[relative] = {"kind": "file", "sha256": sha(entry), "bytes": entry.stat().st_size, "mode": format(stat.S_IMODE(mode), "04o")}
        elif stat.S_ISDIR(mode): result[relative] = {"kind": "directory", "mode": format(stat.S_IMODE(mode), "04o")}
        else: raise ValueError("Special build product")
    return result

def source_tree():
    paths = list((BASE / "harness").rglob("*")) + list(BASE.glob("*.py")) + list((BASE / "app/source").rglob("*")) + [BASE / "app/build.py", BASE / "policy-probe.swift"]
    return {str(path.relative_to(BASE)): sha(path) for path in sorted(paths) if path.is_file() and not path.is_symlink()}

def archive_products(products):
    with PRODUCT_ARCHIVE.open("wb") as output, gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed, tarfile.open(fileobj=compressed, mode="w") as archive:
        for name, expected in products.items():
            require(expected["kind"] in {"file", "directory"}, "Only regular prepared products allowed")
            info = tarfile.TarInfo(name); info.mode = int(expected["mode"], 8)
            if expected["kind"] == "directory": info.type = tarfile.DIRTYPE; archive.addfile(info)
            else:
                payload = (PRODUCTS / name).read_bytes(); info.size = len(payload)
                require(hashlib.sha256(payload).hexdigest() == expected["sha256"], "Product changed during archive")
                archive.addfile(info, io.BytesIO(payload))
    return sha(PRODUCT_ARCHIVE)

def product_archive_payload(manifest):
    require(sha(PRODUCT_ARCHIVE) == manifest["productArchiveSHA256"], "Prepared runner archive changed")
    expected = manifest["products"]; seen = set(); payload = {}
    with tarfile.open(PRODUCT_ARCHIVE, "r:gz") as archive:
        for member in archive:
            name = member.name; path = pathlib.PurePosixPath(name)
            require(not path.is_absolute() and ".." not in path.parts and str(path) == name and name in expected and name not in seen, "Unknown/duplicate/unsafe runner archive entry")
            seen.add(name); item = expected[name]
            require(member.mode == int(item["mode"], 8), "Runner archive mode changed")
            if item["kind"] == "directory": require(member.isdir(), "Runner archive directory type changed")
            else:
                require(member.isfile() and member.size == item["bytes"], "Runner archive file type/size changed")
                data = archive.extractfile(member).read(item["bytes"] + 1)
                require(len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"], "Runner archive payload changed")
                payload[name] = data
    require(seen == set(expected), "Runner archive missing entries")
    return payload

def restore_products():
    verify_seal_files()
    manifest = json.loads((BASE / "build-products-manifest.json").read_text())
    payload = product_archive_payload(manifest)
    require(not PRODUCTS.exists() and PRODUCTS.resolve() == PRODUCTS, "Product restore requires an absent canonical destination")
    PRODUCTS.mkdir(parents=True)
    for name, item in manifest["products"].items():
        path = PRODUCTS / name
        if item["kind"] == "directory": path.mkdir(parents=True, exist_ok=True)
        else: path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(payload[name])
        path.chmod(int(item["mode"], 8))
    require(tree(PRODUCTS) == manifest["products"], "Restored runner tree mismatch")

class Commands:
    def __init__(self, output, capability=None): self.output = output; self.events = []; self.capability = capability
    def redact(self, text): return text.replace(self.capability, "[ephemeral-capability-redacted]") if self.capability else text
    def record(self, name, value):
        event = {"kind": name, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **value}
        self.events.append(event); write(self.output, self.events)
    def run(self, argv, timeout=45, check=True, retained_stdout_filter=None):
        if join_support.is_selected(argv):
            return join_support.run_observed(self, argv, timeout, check, retained_stdout_filter)
        started = time.monotonic()
        env = {**os.environ, "DEVELOPER_DIR": str(DEVELOPER), "PYTHONDONTWRITEBYTECODE": "1"}
        process = subprocess.Popen([str(v) for v in argv], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except BaseException as failure:
            stdout, stderr = "", ""
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try: stdout, stderr = process.communicate(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL); stdout, stderr = process.communicate(timeout=8)
            else: stdout, stderr = process.communicate(timeout=8)
            retained_stdout = retained_stdout_filter(stdout) if retained_stdout_filter else stdout
            self.record("command-interrupted", {"argv": [str(v) for v in argv], "exitCode": process.returncode, "failureType": type(failure).__name__, "stdout": self.redact(retained_stdout), "stderr": self.redact(stderr), "elapsedSeconds": time.monotonic()-started})
            raise
        retained_stdout = retained_stdout_filter(stdout) if retained_stdout_filter else stdout
        self.record("command", {"argv": [str(v) for v in argv], "DEVELOPER_DIR": str(DEVELOPER), "exitCode": process.returncode, "stdout": self.redact(retained_stdout), "stdoutScope": "pinned Simulator frontend rows only" if retained_stdout_filter else "complete", "stderr": self.redact(stderr), "elapsedSeconds": time.monotonic()-started})
        if check: require(process.returncode == 0, "Command failed: " + repr(argv))
        return process.returncode, stdout.strip(), stderr.strip()
    def simctl(self, *args, check=True): return self.run(["/usr/bin/xcrun", "simctl", *args], check=check)[1]

def verify_sources_and_build():
    frozen = packet.verify_packet()
    manifest = json.loads((BASE / "build-products-manifest.json").read_text())
    require(source_tree() == manifest["sourceFiles"], "Prepared harness sources changed")
    require(hashlib.sha256(json_bytes(manifest["sourceFiles"])).hexdigest() == manifest["sourceTreeSHA256"], "Prepared source tree digest mismatch")
    require(sha(BASE / "oracle.py") == sha(ROOT / "verification/apple-toggle-xctest-preparation/oracle.py"), "Original strict oracle changed")
    require(tree(PRODUCTS) == manifest["products"], "Prepared test runner products changed")
    require(all(sha(pathlib.Path(name)) == digest for name, digest in manifest["toolFiles"].items()), "Pinned compiler/build tool/SDK settings changed")
    require(hashlib.sha256(json_bytes(manifest["products"])).hexdigest() == manifest["productTreeSHA256"], "Prepared product tree digest mismatch")
    product_archive_payload(manifest)
    return {"frozen": frozen, "testRunnerProductTreeSHA256": manifest["productTreeSHA256"], "sourceTreeSHA256": manifest["sourceTreeSHA256"]}

def verify_seal_files():
    seal_path = BASE / "packet-seal.json"
    seal = json.loads(seal_path.read_text())
    require(seal["schema"] == "mixer.apple-toggle.pan-origin-correction.1", "Wrong handoff seal")
    require(seal["excludedMutableSubtrees"] == [str((BASE / "runtime").relative_to(ROOT)) + "/", str((BASE / "runtime-direct").relative_to(ROOT)) + "/"], "Wrong mutable native scope")
    for name, digest in seal["files"].items():
        path = ROOT / packet.relative_name(name)
        require(path.is_file() and not path.is_symlink() and sha(path) == digest, "Sealed handoff changed: " + name)
    return {"sealSHA256": sha(seal_path)}

def verify_controls_and_bindings():
    controls = json.loads((BASE / "host-checks.json").read_text())
    require(controls["exitCode"] == 0 and "Ran 92 tests" in controls["stderr"] and controls["stderr"].rstrip().endswith("OK"), "Host controls failed")
    actual_python = {str(path.relative_to(BASE)): sha(path) for path in sorted(BASE.glob("*.py"))}
    require(controls["sourceFiles"] == actual_python, "Host controls do not match current Python sources")
    policy = json.loads((BASE / "policy-receipt.json").read_text())
    result = json.loads((BASE / "policy-result.json").read_text())
    require(policy["passed"] and result["pass"] and len(result["checks"]) == 58 and all(item["pass"] is True for item in result["checks"]), "Swift host policy/lifecycle controls failed")
    require(all(sha(BASE / packet.relative_name(name)) == digest for name,digest in policy["sourceFiles"].items()), "Swift host controls source closure changed")
    require(hashlib.sha256(json_bytes(policy["sourceFiles"])).hexdigest() == policy["sourceTreeSHA256"], "Swift host source tree digest mismatch")
    bindings = json.loads((BASE / "evidence-bindings.json").read_text())
    require(all(sha(ROOT / packet.relative_name(name)) == digest for name,digest in bindings["files"].items()), "Historical root evidence changed")
    official = json.loads((BASE / "official/manifest.json").read_text())
    require(len(official["sources"]) == 6 and sha(BASE / "official/fetch.py") == official["scriptSHA256"], "Official contract retrieval identity changed")
    for row in official["sources"]:
        path = BASE / "official" / packet.relative_name(row["snapshot"])
        require(sha(path) == row["sha256"] and path.stat().st_size == row["bytes"], "Official contract source changed")
    return {"pythonHostControls": 92, "swiftHostPolicyControls": 58, "historicalEvidenceFiles": len(bindings["files"]), "officialAppleContracts": 6}

def verify(): return {**verify_seal_files(), **verify_sources_and_build(), **verify_controls_and_bindings(), "nativeExecution": False}

def prepare():
    require(not (BASE / "packet-seal.json").exists(), "Sealed build is immutable; make a separate reviewed attempt")
    commands = Commands(BASE / "preparation-commands.json")
    sources = source_tree()
    versions = {}
    for key, argv in {"xcode": [str(DEVELOPER / "usr/bin/xcodebuild"), "-version"], "swift": [str(DEVELOPER / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc"), "--version"], "python": [sys.executable, "--version"]}.items():
        versions[key] = commands.run(argv)[1]
    argv = [str(DEVELOPER / "usr/bin/xcodebuild"), "build-for-testing", "-project", str(BASE / "harness/MixerToggleUITests.xcodeproj"), "-scheme", "MixerToggleUITests", "-sdk", "iphonesimulator", "-destination", "generic/platform=iOS Simulator", "-derivedDataPath", str(BASE / "build"), "CODE_SIGNING_ALLOWED=NO", "ARCHS=arm64"]
    commands.run(argv, timeout=180)
    require(source_tree() == sources, "Sources changed during preparation")
    products = tree(PRODUCTS)
    tool_paths = [DEVELOPER / "usr/bin/xcodebuild", DEVELOPER / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc", DEVELOPER / "Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator26.5.sdk/SDKSettings.json", pathlib.Path("/usr/bin/xcrun"), pathlib.Path("/usr/bin/codesign"), pathlib.Path(sys.executable).resolve()]
    manifest = {"schema": "mixer.apple-toggle.xctest-build.1", "sourceRevisionContext": SOURCE_REVISION_CONTEXT, "sourceFiles": sources, "sourceTreeSHA256": hashlib.sha256(json_bytes(sources)).hexdigest(), "products": products, "productTreeSHA256": hashlib.sha256(json_bytes(products)).hexdigest(), "productArchiveSHA256": archive_products(products), "versions": versions, "toolFiles": {str(path): sha(path) for path in tool_paths}, "nativeBootInstallRun": False, "physicalDeviceCommands": False}
    write(BASE / "build-products-manifest.json", manifest)
    print(json.dumps({"status": "build-for-testing-succeeded-no-native-run", "productTreeSHA256": manifest["productTreeSHA256"], "versions": versions}))

INTERACTION_METHODS = ["test010StandaloneNativePanPositiveControl", "test020BlankListUpwardScrollPositiveControl", "test030LTRPanOffToOn", "test040LTRPanOnToOff", "test050RTLPanOffToOn", "test060RTLPanOnToOff", "test070VerticalDragStartingOnCarrierScrolls", "test080DiagnosticAuthoredNativeTapPair", "test090DiagnosticPlainUIButtonNativeTapPair", "test100ComparatorAuthoredNativeTapPair"]
DIRECT_METHODS = ["test110DiagnosticDirectAPIOriginalStrictChecks", "test120ComparatorDirectAPIOriginalStrictChecks"]
SCOPES = {"interaction": {"methods": INTERACTION_METHODS, "cases": CASES - {"diagnostic-direct", "comparator-direct"}},
          "direct": {"methods": DIRECT_METHODS, "cases": {"diagnostic-direct", "comparator-direct"}}}

def runtime_summary(scope, bridge, xctest_exit, failure, cleanup_results):
    cases = SCOPES[scope]["cases"]
    expected = {name: (2 if name.endswith("taps") else 1) for name in sorted(cases)}
    results = None if bridge is None else list(bridge.verdicts)
    failures = None if bridge is None else list(bridge.failures)
    counts = None if results is None else {name: sum(value["case"] == name for value in results) for name in sorted(cases)}
    complete = counts == expected
    strict = None if results is None else complete and all(value["passed"] is True for value in results)
    return {"schema": "mixer.apple-toggle.pan-origin-runtime.1", "scope": scope,
            "xcodebuildExitCode": xctest_exit, "xcodebuildTerminalResultAvailable": xctest_exit is not None,
            "expectedCaseEvaluations": expected, "actualCaseEvaluations": counts, "completeCaseSet": complete,
            "strictNativeVerdictsPassed": strict, "bridgeFailures": failures,
            "bridgeEvidenceAvailable": bridge is not None, "sessionFailure": failure,
            "officialSummaryAvailable": (RUN_DIR / "xctest-summary.json").is_file(),
            "officialTestsAvailable": (RUN_DIR / "xctest-tests.json").is_file(),
            "cleanupResults": cleanup_results,
            "runPassed": xctest_exit == 0 and strict is True and failures == [] and failure is None
                and cleanup_results is not None and all(value["passed"] is True for value in cleanup_results),
            "nativeUserInteractionVerdicts": None if results is None else [value for value in results if value["action"] != "direct-suite"],
            "directOriginalVerdicts": None if results is None else [value for value in results if value["action"] == "direct-suite"],
            "directOriginalScope": "selected-strict" if scope == "direct" else "not-selected-pending-historical-failures-retained",
            "carrierAccepted": False, "capabilityRetained": False, "physicalPhones": "disconnected-deferred", "gaAccepted": False}

def flattened(snapshot): return {device["udid"]: {**device, "runtimeIdentifier": runtime} for runtime, group in snapshot["devices"].items() for device in group}
def devices(commands): return json.loads(commands.simctl("list", "devices", "--json"))
def owned_device(lifecycle, current):
    identifier = lifecycle["ownedSimulator"]
    require(identifier is not None, "Creation must be reconciled before cleanup")
    require(identifier not in flattened(lifecycle["before"]), "Refusing baseline device")
    value = flattened(current).get(identifier)
    if value: require(value["name"] == lifecycle["ownedName"] and value["deviceTypeIdentifier"] == DEVICE_TYPE and value["runtimeIdentifier"] == RUNTIME, "Owned device identity changed; preserve it")
    return value

def reconcile_creation(lifecycle, current):
    require(lifecycle["ownedSimulator"] is None, "Creation already has an identity")
    before = flattened(lifecycle["before"])
    matches = [value for key, value in flattened(current).items() if key not in before and value["name"] == lifecycle["ownedName"] and value.get("deviceTypeIdentifier") == DEVICE_TYPE and value["runtimeIdentifier"] == RUNTIME]
    require(len(matches) <= 1, "Ambiguous fresh creation; preserve all instances")
    if matches: lifecycle["ownedSimulator"] = matches[0]["udid"]
    lifecycle["creationReconciled"] = {"exactFreshMatches": len(matches), "ownedSimulator": lifecycle["ownedSimulator"]}
    return matches[0] if matches else None

def frontends(commands):
    # Read only pinned Simulator executable identities; no frontend is launched.
    executable = str(DEVELOPER / "Applications/Simulator.app/Contents/MacOS/Simulator")
    retain = lambda output: "\n".join(line.strip() for line in output.splitlines() if line.strip().endswith(executable))
    _, output, _ = commands.run(["/bin/ps", "-axo", "pid=,lstart=,comm="], retained_stdout_filter=retain)
    return [line.strip() for line in output.splitlines() if line.strip().endswith(executable)]

def cleanup(lifecycle, commands):
    current = devices(commands)
    owned = owned_device(lifecycle, current) if lifecycle["ownedSimulator"] else reconcile_creation(lifecycle, current)
    if owned:
        if owned["state"] != "Shutdown": commands.simctl("shutdown", lifecycle["ownedSimulator"])
        commands.simctl("delete", lifecycle["ownedSimulator"])
    final = devices(commands)
    require((owned_device(lifecycle, final) if lifecycle["ownedSimulator"] else reconcile_creation(lifecycle, final)) is None, "Owned device remains")
    before, after = flattened(lifecycle["before"]), flattened(final)
    require(all(key in after and all(after[key].get(field) == value.get(field) for field in ("state", "name", "runtimeIdentifier", "deviceTypeIdentifier")) for key, value in before.items()), "Baseline device identity/state changed")
    unknown = set(after) - set(before)
    require(not unknown, "Unexpected new simulator preserved; reconcile root ownership")
    after_frontends = frontends(commands)
    require(after_frontends == lifecycle.get("beforeFrontends", []), "Pinned Simulator frontend identities changed; all frontends preserved for root reconciliation")
    lifecycle.update(nativeDeviceCleanupPassed=True, after=final, ownedDeviceAbsent=True, baselineStatesPreserved=True, afterFrontends=after_frontends, frontendScope="Pinned frontend identities preserved; no frontend launched or signalled by this runner")
    write(RUN_DIR / "lifecycle.json", lifecycle)

def validate_container(path, identifier, data=False):
    path = pathlib.Path(path)
    parent = pathlib.Path.home() / "Library/Developer/CoreSimulator/Devices" / identifier / "data/Containers" / ("Data/Application" if data else "Bundle/Application")
    expected_parent = path.parent if data else path.parent.parent
    require(expected_parent == parent and path.resolve() == path and path.is_dir(), "Container outside exact owned simulator")
    return path

def cleanup_independently(operations, redact=lambda value: value):
    results = []
    for label, operation in operations:
        try: operation(); results.append({"resource": label, "passed": True})
        except BaseException as failure: results.append({"resource": label, "passed": False, "failureType": type(failure).__name__, "message": redact(str(failure))})
    return results

def remove_ephemeral(lifecycle):
    expected = lifecycle.get("ephemeralWorkspace")
    if expected is None: return
    path = pathlib.Path(expected["path"])
    require(path.parent == pathlib.Path(tempfile.gettempdir()).resolve() and path.name.startswith("mixer-toggle-xctest-") and path.resolve() == path, "Ephemeral workspace identity/path changed")
    if not path.exists(): lifecycle["ephemeralWorkspaceAbsent"] = True; return
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and not path.is_symlink() and info.st_dev == expected["device"] and info.st_ino == expected["inode"] and info.st_uid == expected["uid"] and stat.S_IMODE(info.st_mode) == 0o700, "Ephemeral workspace identity changed; preserve it")
    shutil.rmtree(path)
    lifecycle["ephemeralWorkspaceAbsent"] = not path.exists()

def select_runtime_directory(scope):
    require(scope in SCOPES, "Unsupported closed replay scope")
    return BASE / ("runtime" if scope == "interaction" else "runtime-direct")

def run(reviewed_seal, scope="interaction"):
    global RUN_DIR
    RUN_DIR = select_runtime_directory(scope)
    selected_cases = SCOPES[scope]["cases"]
    verified = verify()
    require(reviewed_seal == verified["sealSHA256"], "Root reviewed seal does not match")
    RUN_DIR.mkdir(exist_ok=False)
    capability = secrets.token_hex(32)
    commands = Commands(RUN_DIR / "commands.json", capability)
    lifecycle = None; server = None; thread = None; ephemeral = None; xctest_exit = None
    bridge = None; failure_record = None; cleanup_results = None; result_path = None
    try:
        runtime_list = json.loads(commands.simctl("list", "runtimes", "--json"))
        runtime = next(value for value in runtime_list["runtimes"] if value["identifier"] == RUNTIME)
        require(runtime["isAvailable"] and runtime["buildversion"] == RUNTIME_BUILD, "Exact available iOS26.5(23F77) runtime required")
        before = devices(commands)
        name = "MixerTogglePanOrigin-" + str(uuid.uuid4())
        lifecycle = {"schema": "mixer.apple-toggle.xctest-lifecycle.1", "ownedName": name, "ownedSimulator": None, "creationIntentRecordedBeforeCommand": True, "before": before, "beforeFrontends": frontends(commands), "verifiedHandoff": verified, "runtime": runtime, "apps": {}, "cleanedUp": False, "nativeExecutionAttempted": True, "physicalDevices": "disconnected-deferred"}
        write(RUN_DIR / "lifecycle.json", lifecycle)
        identifier = commands.simctl("create", name, DEVICE_TYPE, RUNTIME)
        uuid.UUID(identifier)
        lifecycle["ownedSimulator"] = identifier
        write(RUN_DIR / "lifecycle.json", lifecycle)
        owned_device(lifecycle, devices(commands))
        commands.simctl("boot", identifier)
        commands.run(["/usr/bin/xcrun", "simctl", "bootstatus", identifier, "-b"], timeout=120)
        documents = {}
        for key, config in packet.CONFIGS.items():
            destination = RUN_DIR / "restored-app" / key
            packet.restore(destination, key)
            app = destination / config["app"]
            commands.simctl("install", identifier, str(app))
            installed = validate_container(commands.simctl("get_app_container", identifier, config["bundle"], "app"), identifier)
            installed_validation = packet.verify_installed(installed, key, commands.record)
            container = validate_container(commands.simctl("get_app_container", identifier, config["bundle"], "data"), identifier, data=True)
            docs = container / "Documents"; docs.mkdir(exist_ok=True)
            require(docs.resolve() == docs, "Documents redirected")
            documents[key] = docs
            lifecycle["apps"][key] = {"container": str(container), "installed": installed_validation}
            write(RUN_DIR / "lifecycle.json", lifecycle)
        bridge = Bridge(documents, RUN_DIR / "captures", capability, {"udid": identifier, "name": name, "runtime": RUNTIME, "build": RUNTIME_BUILD}, lifetime=600, allowed_cases=selected_cases)
        server = server_for(bridge)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        original = list(PRODUCTS.glob("*.xctestrun"))
        require(len(original) == 1, "One exact prepared xctestrun required")
        configuration = plistlib.loads(original[0].read_bytes())
        target = configuration["MixerToggleUITests"]
        for key in ("EnvironmentVariables", "TestingEnvironmentVariables"):
            target[key].update(MIXER_BRIDGE_URL=f"http://127.0.0.1:{server.server_port}", MIXER_BRIDGE_CAPABILITY=capability)
        target.update(TestTimeoutsEnabled=True, DefaultTestExecutionTimeAllowance=30, MaximumTestExecutionTimeAllowance=45, ParallelizationEnabled=False, UserAttachmentLifetime="keepAlways", SystemAttachmentLifetime="keepAlways")
        def absolute(value):
            if isinstance(value, str): return value.replace("__TESTROOT__", str(PRODUCTS))
            if isinstance(value, dict): return {key: absolute(item) for key, item in value.items()}
            if isinstance(value, list): return [absolute(item) for item in value]
            return value
        ephemeral = pathlib.Path(tempfile.mkdtemp(prefix="mixer-toggle-xctest-")).resolve()
        ephemeral.chmod(0o700)
        ephemeral_info = ephemeral.stat()
        lifecycle["ephemeralWorkspace"] = {"path": str(ephemeral), "device": ephemeral_info.st_dev, "inode": ephemeral_info.st_ino, "uid": ephemeral_info.st_uid}
        write(RUN_DIR / "lifecycle.json", lifecycle)
        config_path = ephemeral / "session.xctestrun"; config_path.write_bytes(plistlib.dumps(absolute(configuration))); config_path.chmod(0o600)
        result_path = ephemeral / "session.xcresult"
        argv = [str(DEVELOPER / "usr/bin/xcodebuild"), "test-without-building", "-xctestrun", str(config_path), "-destination", "platform=iOS Simulator,id=" + identifier, "-parallel-testing-enabled", "NO", "-maximum-concurrent-test-simulator-destinations", "1", "-resultBundlePath", str(result_path)]
        argv += ["-only-testing:MixerToggleUITests/ToggleUITests/" + method for method in SCOPES[scope]["methods"]]
        xctest_exit = commands.run(argv, timeout=600, check=False)[0]
        summary = runtime_summary(scope, bridge, xctest_exit, failure_record, cleanup_results)
        write(RUN_DIR / "runtime-verdict.json", summary)
        require(xctest_exit == 0 and summary["strictNativeVerdictsPassed"] is True and summary["bridgeFailures"] == [], "Strict XCTest result failed; preserved evidence is authoritative")
    except BaseException as failure:
        failure_record = {"type": type(failure).__name__, "message": commands.redact(str(failure))}
        commands.record("session-failure", {"type": type(failure).__name__, "message": commands.redact(str(failure))})
        raise
    finally:
        if result_path and result_path.exists():
            for kind in ("summary", "tests"):
                try:
                    code, output, _ = commands.run(["/usr/bin/xcrun", "xcresulttool", "get", "test-results", kind, "--path", str(result_path)], check=False)
                    if code == 0: (RUN_DIR / ("xctest-" + kind + ".json")).write_text(commands.redact(output) + "\n")
                except BaseException as export_failure:
                    commands.record("official-result-export-unavailable", {"kind": kind, "type": type(export_failure).__name__, "message": commands.redact(str(export_failure))})
        operations = []
        if server: operations.append(("loopback-server-shutdown", server.shutdown))
        if server: operations.append(("loopback-server-close", server.server_close))
        if thread:
            def join_thread():
                thread.join(timeout=3); require(not thread.is_alive(), "Bridge thread did not exit")
            operations.append(("loopback-thread-join", join_thread))
        if ephemeral: operations.append(("ephemeral-capability-workspace-removal", lambda: remove_ephemeral(lifecycle)))
        capability = None
        if lifecycle: operations.append(("owned-simulator-and-baseline-reconciliation", lambda: cleanup(lifecycle, commands)))
        cleanup_results = cleanup_independently(operations, commands.redact)
        commands.record("all-independent-cleanup-attempts", {"results": cleanup_results})
        if lifecycle:
            lifecycle["cleanedUp"] = all(value["passed"] for value in cleanup_results)
            lifecycle["cleanupResults"] = cleanup_results
            write(RUN_DIR / "lifecycle.json", lifecycle)
        write(RUN_DIR / "runtime-verdict.json", runtime_summary(scope, bridge, xctest_exit, failure_record, cleanup_results))
        require(all(value["passed"] for value in cleanup_results), "One or more cleanup resources failed; root recovery required")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "restore-products", "verify", "run", "cleanup"))
    parser.add_argument("--reviewed-seal")
    parser.add_argument("--scope", choices=tuple(SCOPES), default="interaction")
    args = parser.parse_args()
    if args.action == "prepare": prepare()
    elif args.action == "restore-products": restore_products()
    elif args.action == "verify": print(json.dumps(verify(), sort_keys=True))
    elif args.action == "run": run(args.reviewed_seal, args.scope)
    elif args.action == "cleanup":
        global RUN_DIR
        RUN_DIR = select_runtime_directory(args.scope)
        lifecycle = json.loads((RUN_DIR / "lifecycle.json").read_text())
        require(lifecycle["verifiedHandoff"]["sealSHA256"] == verify()["sealSHA256"], "Cleanup handoff identity changed")
        commands = Commands(RUN_DIR / "recovery-commands.json")
        results = cleanup_independently([("owned-simulator-and-baseline-reconciliation", lambda: cleanup(lifecycle, commands)), ("ephemeral-capability-workspace-removal", lambda: remove_ephemeral(lifecycle))])
        lifecycle.update(cleanedUp=all(value["passed"] for value in results), recoveryCleanupResults=results)
        write(RUN_DIR / "lifecycle.json", lifecycle)
        commands.record("all-independent-recovery-cleanup-attempts", {"results": results})
        require(lifecycle["cleanedUp"], "Recovery cleanup incomplete")

if __name__ == "__main__":
    def stop(signum, frame): raise KeyboardInterrupt("Root harness interruption")
    signal.signal(signal.SIGINT, stop); signal.signal(signal.SIGTERM, stop)
    main()
