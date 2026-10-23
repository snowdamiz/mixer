#!/usr/bin/env python3
"""Owned native HTTP implementer receipt. No devices, trust changes or remote service."""
import concurrent.futures
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
LOGS = OUT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)
SWIFT = "/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
SDKS = "/Users/andreyyurlov/.swiftpm/swift-sdks"
XENV = {"DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer"}
JDK = "/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home"
OPENSSL = "/opt/homebrew/opt/openssl@3/bin/openssl"
JENV = {"JAVA_HOME": JDK, "PATH": JDK + "/bin:" + os.environ["PATH"]}


def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()


def capture(args, environment=None):
    return subprocess.run(args, cwd=ROOT, env=os.environ | (environment or {}), text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def run(name, args, scope, environment=None):
    started = now()
    result = capture(args, environment)
    path = LOGS / (name + ".log")
    path.write_text(result.stdout)
    record = dict(name=name, command=args, cwd=str(ROOT), startedAt=started, endedAt=now(), exitCode=result.returncode,
                  output=str(path.relative_to(ROOT)), outputSHA256=hashlib.sha256(path.read_bytes()).hexdigest(), scope=scope)
    if environment: record["environment"] = environment
    return record


def source():
    files = []
    for folder in [ROOT / "sdk", ROOT / "capabilities"]:
        files += [p for p in folder.rglob("*") if p.is_file() and not {".build", ".swiftpm", "verification", "__pycache__"}.intersection(p.relative_to(folder).parts)]
    entries = [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]
    data = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return dict(algorithm="SHA256 of canonical JSON source entries sorted by path; sdk and capabilities excluding build/verification artifacts", digest=hashlib.sha256(data).hexdigest(), files=entries)


def local_untrusted_tls():
    """An ephemeral self-signed server; no certificate/key enters the repository."""
    records = []
    with tempfile.TemporaryDirectory(prefix="mixer-http-tls-") as temporary:
        certificate, key = [str(Path(temporary) / name) for name in ["certificate.pem", "private-key.pem"]]
        records.append(run("local-tls-certificate", [OPENSSL, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                           "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1", "-keyout", key, "-out", certificate],
                           "ephemeral local self-signed TLS fixture generation; key destroyed with private temporary directory"))
        if records[-1]["exitCode"] != 0: return records, dict(passed=False)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(certificate, key)
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(8)
        listener.settimeout(0.2)
        port = listener.getsockname()[1]
        stop = threading.Event()
        observations = dict(acceptedConnections=0, failedTLSHandshakes=0, successfulTLSHandshakes=0, applicationBytes=0)

        def serve():
            while not stop.is_set():
                try: connection, _ = listener.accept()
                except socket.timeout: continue
                except OSError: return
                observations["acceptedConnections"] += 1
                connection.settimeout(4)
                try:
                    with context.wrap_socket(connection, server_side=True) as secure:
                        observations["successfulTLSHandshakes"] += 1
                        observations["applicationBytes"] += len(secure.recv(65536))
                        secure.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                except (ssl.SSLError, OSError):
                    observations["failedTLSHandshakes"] += 1
                    connection.close()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        try:
            records.append(run("local-untrusted-tls", ["swift", "test", "--package-path", "capabilities", "--scratch-path", "capabilities/.build/http-tls",
                               "-Xswiftc", "-DMIXER_HTTP_LOCAL_TLS_TEST", "--filter", "systemTLSRejectsUntrustedLocalCertificate"],
                               "actual loopback TLS with normal URLSession verification; an untrusted matching-IP certificate must fail; not a successful production TLS receipt",
                               {"MIXER_HTTP_UNTRUSTED_TLS_URL": "https://127.0.0.1:" + str(port) + "/"}))
        finally:
            stop.set()
            listener.close()
            thread.join(timeout=5)
        observations.update(certificateDER_SHA256=hashlib.sha256(ssl.PEM_cert_to_DER_cert(Path(certificate).read_text())).hexdigest(),
                            trustStoreModified=False, trustOverrideInstalled=False, privateKeyPersisted=False)
        observations["passed"] = (records[-1]["exitCode"] == 0 and not thread.is_alive() and observations["acceptedConnections"] >= 1
                                  and observations["failedTLSHandshakes"] >= 1 and observations["successfulTLSHandshakes"] == 0 and observations["applicationBytes"] == 0)
        return records, observations


def delayed_watchdog_regression():
    # An isolated mutation restores only the reviewed defect. It must fail the
    # deterministic regression without touching the shared source working tree.
    with tempfile.TemporaryDirectory(prefix="mixer-http-late-result-") as temporary:
        snapshot = Path(temporary)
        for name in ["sdk", "capabilities"]:
            shutil.copytree(ROOT / name, snapshot / name, ignore=shutil.ignore_patterns(".build", ".swiftpm", "verification", "__pycache__"))
        path = snapshot / "sdk/Sources/MixerCapabilities/URLSessionHTTPTransport.swift"
        original = path.read_text()
        guard = """        if case .success = proposed, clock.now() >= deadline {
            result = .failure(CapabilityFailure.deadlineExceeded)
            cancel = true
        }
"""
        if original.count(guard) != 1: raise ValueError("deadline mutation does not match exact reviewed guard")
        mutated = original.replace(guard, "")
        path.write_text(mutated)
        record = run("delayed-watchdog-regression-mutant", ["swift", "test", "--package-path", str(snapshot / "capabilities"),
                     "--filter", "lateSuccessFailsEvenWhenWatchdogHasNotRun"],
                     "isolated intentional mutation removes final monotonic-success guard; deterministic regression must reject late success (expected test failure)")
        record.update(expectedExitCode=1, originalTransportSHA256=hashlib.sha256(original.encode()).hexdigest(),
                      mutatedTransportSHA256=hashlib.sha256(mutated.encode()).hexdigest(), sharedSourceModified=False)
        return record


before = source()
head = capture(["git", "rev-parse", "HEAD"]).stdout.strip()
tree = capture(["git", "rev-parse", "HEAD^{tree}"]).stdout.strip()
contracts = json.loads((ROOT / "capabilities/schema/hashes.json").read_text())
prior = json.loads(capture(["git", "show", "444e607:capabilities/schema/hashes.json"]).stdout)
wire_unchanged = {k: v for k, v in contracts.items() if k != "nativeImplementationSHA256"} == {k: v for k, v in prior.items() if k != "nativeImplementationSHA256"}
commands = [run("generated-check", ["python3", "capabilities/tools/generate.py", "--check"], "generated models/dispatch/native identity match owned source; wire hashes unchanged")]
android = [SWIFT, "build", "--package-path", "capabilities", "--swift-sdks-path", SDKS, "--swift-sdk", "aarch64-unknown-linux-android28"]
jobs = [
    ("capability-tests", ["swift", "test", "--package-path", "capabilities"], "macOS complete capability suite including eleven native HTTP tests; injected URLProtocol is not real network/TLS", None),
    ("existing-sdk-tests", ["swift", "test", "--package-path", "sdk"], "all existing Core/UI/Apple SDK host tests", None),
    ("ios-build", ["swift", "build", "--package-path", "sdk", "--target", "MixerCapabilities", "--triple", "arm64-apple-ios17.0", "--sdk", "/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS27.1.sdk", "--scratch-path", "capabilities/.build/http-ios", "-Xswiftc", "-warnings-as-errors"], "iOS arm64 target compilation only, warnings treated as errors", None),
    ("android-build", android + ["--static-swift-stdlib", "-c", "release", "--product", "capability-probe", "--scratch-path", "capabilities/.build/http-android", "-Xlinker", "-lssl", "-Xlinker", "-lcrypto", "-Xlinker", "-lz"], "Android aarch64 API28 static Swift codec probe cross-compilation with explicit official SDK curl SSL/crypto/zlib dependencies; not APK/runtime qualification", XENV),
    ("android-test-build", android + ["-c", "release", "--build-tests", "-Xswiftc", "-enable-testing", "--scratch-path", "capabilities/.build/http-android-tests"], "Android dynamic Swift Testing runner compilation, including native HTTP tests; not executed", XENV),
    ("wasi-build", [SWIFT, "build", "--package-path", "sdk", "--swift-sdks-path", SDKS, "--swift-sdk", "swift-6.3.3-RELEASE_wasm", "--triple", "wasm32-unknown-wasip1", "-c", "release", "--target", "MixerCapabilities", "--scratch-path", "capabilities/.build/http-wasm"], "WASI guest value module compilation; native URLSession adapter excluded; no linked/executed guest", XENV),
    ("thread-sanitizer", ["swift", "test", "--package-path", "capabilities", "--scratch-path", "capabilities/.build/http-tsan", "--sanitize", "thread", "--filter", "NativeHTTPTransportTests"], "macOS eleven native transport tests with owned Swift code instrumented; system frameworks not instrumented", None),
    ("java-build", [JDK + "/bin/javac", "--release", "8", "-Xlint:all,-options", "-Werror", "-d", "capabilities/.build/java"] + [str(p.relative_to(ROOT)) for p in sorted((ROOT / "capabilities/java").rglob("*.java"))] + ["capabilities/Tests/Java/CapabilityCodecTests.java"], "Java8 codecs including regenerated native identity", JENV),
]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    commands += list(executor.map(lambda job: run(*job), jobs))
commands += [run("java-tests", [JDK + "/bin/java", "-cp", "capabilities/.build/java", "mixer.capabilities.CapabilityCodecTests"], "20 Java codec/ownership regressions", JENV),
             run("codec-differential", ["python3", "capabilities/tools/codec-differential.py"], "24 valid/66 hostile inbound cases;38 completion directions/four forged completion cases")]
tls_commands, tls = local_untrusted_tls()
commands += tls_commands
commands += [delayed_watchdog_regression()]
after = source()
receipt = dict(schemaVersion=1, createdAt=now(), repositoryHeadAtRun=head, repositoryCommittedTreeAtRun=tree,
    implementer=dict(model="gpt-6.1-sol", reasoningEffort="xhigh", independentReview=False), source=before,
    sourceUnchangedDuringRun=before == after, evidenceRunnerSHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    commands=commands, contracts=contracts, wireSchemaUnchanged=wire_unchanged,
    historicalFailedAttempt="capabilities/verification/http-transport/initial-android-static-link.json",
    nativeIdentityChange=dict(previous=prior["nativeImplementationSHA256"], current=contracts["nativeImplementationSHA256"],
        reason="Explicit native URLSession transport code changes installed native behavior and therefore requires a new native implementation identity/new store binary; wire v1 unchanged"),
    localUntrustedTLS=tls,
    environment=dict(host=platform.platform(), python=sys.version, pythonSSL=ssl.OPENSSL_VERSION,
        swift=capture(["swift", "--version"]).stdout.strip(), xcode=capture(["xcodebuild", "-version"]).stdout.strip(),
        androidSwift=capture([SWIFT, "--version"], XENV).stdout.strip(), androidManifestHostXcode=capture(["xcodebuild", "-version"], XENV).stdout.strip(),
        javac=capture([JDK + "/bin/javac", "-version"]).stdout.strip(), openssl=capture([OPENSSL, "version"]).stdout.strip()),
    devicePolicy="Phones disconnected per user instruction; no physical-device commands attempted; new physical checks pending",
    assertions=dict(explicitOptIn=True, defaultHookUnavailable=True, noAmbientCookieCredentialCacheStores=True,
        normalTLSNoOverrides=True, rejectsRedirectsAndCredentialNegotiation=True, requestPreflightAndRetainedResponseBounds=True,
        monotonicDeadlineAndExactlyOneTerminalResult=True, nativeLeaseUntilInvalidation=True,
        noAdapterRetry=True, noExactlyOnceRemoteEffectClaim=True, noGuestImports=True, noDeviceReceipt=True, W06Accepted=False),
    limitations=["Injected URLProtocol tests bypass real network parsing/TLS; system framework internals are opaque and not memory bounded or sanitizer instrumented by these tests",
        "Actual loopback TLS proves only untrusted-certificate rejection on this macOS; successful production TLS and Android runtime CA/configuration remain unqualified",
        "Android runtime CA/trust-store behavior, libz/native dependency APK packaging/notices/security approval pending; no exact SDK backend binary version independently established",
        "Physical iOS/Android cancellation, radio/background lifecycle, minimum OS and real redirect/auth/cookie/cache/network parser matrix pending",
        "No guest network import/JNI activation, signed network grant consumption, FieldLog network integration or immutable published package acceptance claimed",
        "No adapter retries; OS retransmission/reconnection and uncertain remote mutation effects remain possible",
        "Encoded responses, credential negotiation, streaming/resumable guest APIs and connectivity unavailable; broader Section9/W06/W09/GA gates remain open"])
receipt["scopedChecksPassed"] = before == after and wire_unchanged and tls["passed"] and all(c["exitCode"] == c.get("expectedExitCode", 0) for c in commands)
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(dict(sourceDigest=before["digest"], checksPassed=receipt["scopedChecksPassed"], localTLS=tls,
                     commands=[dict(name=c["name"], exitCode=c["exitCode"]) for c in commands]), indent=2))
sys.exit(0 if receipt["scopedChecksPassed"] else 1)
