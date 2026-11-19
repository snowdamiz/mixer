"""Bind each linked engine, sign its loopback packet and package the APK pair."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import zipfile

CAMPAIGN = Path(sys.argv[1]).resolve()
RECIPE = Path(sys.argv[2]).resolve()
INPUTS = RECIPE / "inputs"
SCRATCH = CAMPAIGN / "scratch"
HANDOFF = CAMPAIGN / "handoff"
APP = SCRATCH / "app"
SIGNING = SCRATCH / "signing"
VERIFIER = HANDOFF / "tools/verify-release"
SDK = Path("/opt/homebrew/share/android-commandlinetools")
TOOLS = SDK / "build-tools/36.0.0"
JAVA = Path("/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home")
SWIFT_ANDROID_SDK = Path(os.environ["MIXER_RECIPE_SWIFT_ANDROID_SDK"])
SWIFT_FRONTEND = Path(os.environ["SWIFT_DRIVER_SWIFT_FRONTEND_EXEC"])
GO = Path(os.environ["MIXER_RECIPE_GO"])
CONSUMER_SOURCE_SHA256 = "e619e155178db0433d6ef554fb8729d73609e7b0ebd648183b9b6bf7c4b8099a"
RUST_BIN = Path.home() / ".rustup/toolchains/1.99.0-aarch64-apple-darwin/bin"
NDK = SDK / "ndk/27.1.12297006/toolchains/llvm/prebuilt/darwin-x86_64/bin"
LABELS = {"old": ("baseline", 24101, 7), "new": ("reviewed", 24102, 1)}
APK_PREFIX = "lib/arm64-v8a/"
JNI = "libmixer_public_android_jni.so"
COMMANDS = []
ENV = os.environ | {"TMPDIR": str(SCRATCH / "tmp"), "JAVA_HOME": str(JAVA), "LC_ALL": "C"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def filehash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(pins):
    return sha("".join(f"{value}  {name}\n" for name, value in sorted(pins.items(),
                   key=lambda item: Path(item[0]))).encode())


def write(path, obj):
    path.write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n")
    return path


def read(path):
    return json.loads(path.read_bytes())


def command(*argv, env=ENV, timeout=18):
    argv = [str(arg) for arg in argv]
    COMMANDS.append(argv)
    result = subprocess.run(argv, env=env, timeout=timeout, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{argv[0]} exited {result.returncode}: {result.stdout[-1700:]!r} {result.stderr[-1700:]!r}")
    return result.stdout


def available(label, minimum_mb, measurements):
    usage = shutil.disk_usage(SCRATCH)
    measurement = {"stage": label, "freeBytes": usage.free, "requiredBytes": minimum_mb * 1024 * 1024}
    measurements.append(measurement)
    require(usage.free >= measurement["requiredBytes"], f"volume budget at {label}: {measurement}")


def gp(label):
    return HANDOFF / label


def linked_engine(label):
    vm_parent = SCRATCH / f"pair-{label}"
    source = vm_parent / "vm"
    jni_parent = APP / label
    archive = vm_parent / "target/aarch64-linux-android/release/libmixer_vm.a"
    linked_archive = jni_parent / "libmixer_vm_capability_experimental.a"
    require(linked_archive.resolve() == archive.resolve(), f"wrong {label} archive link input")
    rev, vm_tree, *_ = (SCRATCH / f"engine-{label}.txt").read_text().splitlines()
    sources = {str(path.relative_to(vm_parent)): filehash(path) for path in source.rglob("*") if path.is_file()}
    linker_map = jni_parent / "linker.map"
    archive_lines = [line.strip() for line in (jni_parent / "archive-extraction.tsv").read_text().splitlines()
                     if "mixer_vm::validate::module_with_admission" in line]
    map_lines = [line.strip() for line in linker_map.read_text().splitlines()
                 if str(linked_archive) in line and
                 ("mixer_vm_capability_guest_ui_validate_deferred_v1" in line or "module_with_admission" in line)]
    require(len(archive_lines) >= 1 and len(map_lines) >= 2, f"no link evidence for the {label} archive")
    elf = command(NDK / "llvm-nm", "--dynamic", "--defined-only", jni_parent / JNI).decode()
    require(re.search(r" T mixer_vm_capability_guest_ui_validate_deferred_v1$", elf, re.M),
            f"{label} JNI lacks the capability validator")
    require("Java_dev_fieldlog_generatedr90_androidhost_ChecklistPanel_cycle" in elf, "missing signed-checklist JNI entry")
    return {"revision": rev, "vmTree": vm_tree, "sourceCount": len(sources),
            "sourceSHA256": inventory(sources), "archiveSHA256": filehash(archive), "archiveBytes": archive.stat().st_size,
            "hostArchiveSHA256": filehash(vm_parent / "target/release/libmixer_vm.a"),
            "jni": {"sha256": filehash(jni_parent / JNI), "bytes": (jni_parent / JNI).stat().st_size},
            "linkerMapSHA256": filehash(linker_map),
            "whyExtractSHA256": filehash(jni_parent / "archive-extraction.tsv"),
            "linkedValidatorEvidence": archive_lines + map_lines[:8]}


def bind(label, roots, port, source_pins, archive_info):
    installed = gp(label) / "Installed"
    installed.mkdir()
    for name in ("storage.json", "storage-grant.json", "bridge.json"):
        shutil.copyfile(INPUTS / name, installed / name)
    (installed / "roots.json").write_bytes(roots)
    (installed / "port.txt").write_text(f"{port}\n")
    identity = read(INPUTS / "identity.json")
    build = identity["build"]
    fallback = {path: pin for path, pin in source_pins.items() if path.startswith(
        ("fieldlog/Integrations/InstalledGuest/", "fieldlog/Integrations/GeneratedReport/Sources/",
         "fieldlog/Integrations/GeneratedReport/Platforms/"))}
    bridge = {
        name: filehash(APP / "lib-android" / name)
        for name in ("ChecklistBridge.o", "PublicBridge.o", "platform_android.o", "transport.o")
    }
    link = source_pins | bridge | {
        "engine/archive.a": archive_info["archiveSHA256"],
        "build/libmixer_public_android_jni.so": archive_info["jni"]["sha256"],
        "build/classes.dex": filehash(APP / "apk/dex/classes.dex"),
        "build/manifest.apk": filehash(APP / "apk" / f"manifest-{label}.apk"),
        "build/manifest.xml": filehash(APP / "apk" / f"manifest-{label}.xml"),
        "build/android-jni.sh": filehash(RECIPE / "replay/android-jni.sh"),
    }
    build["link_inputs_sha256"] = inventory(link)
    build["native_fallback_sha256"] = inventory(fallback)
    build["settings_sha256"] = link["android-package/Package.swift"]
    build["permissions_sha256"] = link["build/manifest.xml"]
    build["trust_roots_sha256"] = filehash(installed / "roots.json")
    identity["engine"].update(version=archive_info["revision"], source_sha256=archive_info["sourceSHA256"],
                              artifact_sha256=archive_info["archiveSHA256"])
    require(identity["toolchain"]["compiler_sha256"] == filehash(SWIFT_FRONTEND), "Swift compiler drift")
    require(identity["toolchain"]["sdk_sha256"] == filehash(SWIFT_ANDROID_SDK.parent / "info.json"), "Swift SDK descriptor drift")
    identity["toolchain"]["build_tools_sha256"] = inventory({name: filehash(TOOLS / name) for name in ("aapt2", "apksigner", "zipalign", "d8")})
    require(identity["application"]["bundle_id"] == "dev.fieldlog.generatedr90", "scope drift")
    descriptor = write(installed / "identity.json", identity)
    host = json.loads(command(VERIFIER, "identity", descriptor))
    write(gp(label) / "host.json", host)
    write(SIGNING / f"{label}.host.json", host)
    pins = {path.name: filehash(path) for path in installed.iterdir()}
    write(gp(label) / "installed.sha256.json", pins)
    return host


def consumer_sources(app):
    source_paths = [app / "android-package" / name for name in ("Package.swift", "Package.resolved")]
    source_paths.extend(app / name for name in ("compile-android-java.sh", "offline-env.sh", "manifest-base.xml"))
    for name in ("fieldlog/Integrations/GeneratedReport", "fieldlog/Integrations/InstalledGuest",
                 "mixer/sdk", "mixer/capability-activation", "mixer/runtime-identity", "mixer/updates",
                 "mixer/experimental-capability-runtime", "mixer/native/android",
                 "mixer/verification/android-binding-stage4/host-bridge", "mixer/vm/include", "prepared"):
        source_paths.extend(path for path in (app / name).rglob("*") if path.is_file())
    source_pins = {str(path.relative_to(app)): filehash(path) for path in source_paths}
    digest = inventory(source_pins)
    require(digest == CONSUMER_SOURCE_SHA256, f"consumer source differs from the admitted inventory: {digest}")
    return source_pins, digest


def run():
    os.umask(0o077)
    source_pins, source_digest = consumer_sources(APP)
    SIGNING.mkdir()
    h = HANDOFF
    result = {"createdUTC": datetime.now(timezone.utc).isoformat(), "volume": [], "cases": {}, "tools": {}}
    try:
        available("bind", 7168, result["volume"])
        result["fieldLog"] = {"baseRevision": "552559d2d3278abb9b1aa7dcf0288102c09a202b",
                             "mixerHostSourceBasis": "c392e762d6bb24562647fe22a2de738250ba3e7f",
                             "sourceInventorySHA256": source_digest}
        engine_pins = read(INPUTS / "engines.json")
        guest_sources = SCRATCH / "guest-source"
        guest_pins = {p.name: filehash(p) for p in sorted(guest_sources.iterdir()) if p.is_file()}
        guest_pins["selected-task.patch"] = filehash(RECIPE / "overlays/selected-task.patch")
        guest_source_digest = inventory(guest_pins)
        require(guest_source_digest == "92797cc9e62b0a64f199d81c6ade62e6960393c61faf7c05ebf0b4115a1ace80",
                "selected-task guest source differs from the admitted overlay")
        result["guestSources"] = guest_pins
        result["guestSourceSHA256"] = guest_source_digest
        for label, (release_name, version, sequence) in LABELS.items():
            gp(label).mkdir()
            shutil.copyfile(SCRATCH / f"{label}.wasm", gp(label) / "guest.wasm")
            shutil.copyfile(gp(label) / "guest.wasm", SIGNING / f"{label}.wasm")
            payload = gp(label) / "guest.wasm"
            template = read(INPUTS / "manifest.json")
            template.update(
                created_at_unix=0,
                key_id="unissued",
                runtime="0" * 64,
                source_commit="3184c398ba5e5dcded110a65772d793ba9caf9f6",
                release_id=f"fieldlog-{release_name}",
                payload_sha256=filehash(payload),
                compressed_bytes=payload.stat().st_size,
                expanded_bytes=payload.stat().st_size,
                provenance_id=f"fieldlog-cohort-rebuild-{guest_source_digest[:24]}",
            )
            write(SIGNING / f"{label}.original.manifest.json", template)
            engine = linked_engine(label)
            for key, expected in engine_pins[label].items():
                require(engine[key] == expected, f"{label} engine {key}: expected {expected}, found {engine[key]}")
            result["cases"][label] = {
                "versionCode": version, "sequence": sequence, "engine": engine,
                "guestSHA256": filehash(payload),
            }
        records = [value["engine"] for value in result["cases"].values()]
        for field in ("revision", "vmTree", "sourceSHA256", "archiveSHA256"):
            require(records[0][field] != records[1][field], f"unchanged engine {field}")
        require(records[0]["jni"]["sha256"] != records[1]["jni"]["sha256"], "unchanged linked JNI")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        result["port"] = port
        roots = command(SCRATCH / "sign-cohort", "root", SIGNING)
        for label, case in result["cases"].items():
            case["host"] = bind(label, roots, port, source_pins, case["engine"])
        signed = json.loads(command(SCRATCH / "sign-cohort", "issue", SIGNING))
        (SIGNING / "ota-private-seed").unlink()
        write(h / "signed-pair.json", signed)
        for label in LABELS:
            issued = signed[label]
            origin = read(SIGNING / f"{label}.original.manifest.json")
            manifest = issued["manifest"]["manifest"]
            require({key for key in origin.keys() | manifest.keys() if origin.get(key) != manifest.get(key)}
                    == {"runtime", "key_id", "created_at_unix"},
                    f"unexpected changes in the {label} signed guest contract")
            write(gp(label) / "manifest.json", issued["manifest"])
            write(gp(label) / "assignment.json", issued["assignment"])
            result["cases"][label]["artifactSHA256"] = issued["digest"]
        assemble(result)
    finally:
        for name in ("ota-private-seed", "development.p12"):
            (SIGNING / name).unlink(missing_ok=True)
        result["commands"] = COMMANDS
        write(h / "package-result.json", result)
    print("APK pair, signer, engine archive links and embedded assets verified")


def assemble(result):
    h = HANDOFF
    recipe = APP / "fieldlog/Integrations/GeneratedReport/scripts/build-signed-checklist-android.py"
    packager = SCRATCH / "build-signed-checklist-android.py"
    shutil.copyfile(recipe, packager)
    command("patch", "-s", packager, RECIPE / "overlays/one-apk-signer.patch")
    signenv = ENV | {"FIELDLOG_LOCAL_APK_PASSWORD": secrets.token_hex(24)}
    apk_key = SIGNING / "development.p12"
    command(JAVA / "bin/keytool", "-genkeypair", "-storetype", "PKCS12", "-keystore", apk_key,
            "-alias", "fieldlog-local", "-storepass:env", "FIELDLOG_LOCAL_APK_PASSWORD",
            "-keypass:env", "FIELDLOG_LOCAL_APK_PASSWORD", "-keyalg", "EC", "-groupname", "secp256r1",
            "-validity", "30", "-dname", "CN=FieldLog Local Engine Cohort Pair", env=signenv)
    signenv["FIELDLOG_PAIR_APK_KEYSTORE"] = str(apk_key)
    for label, (_, version, _) in LABELS.items():
        available(f"apk-{label}", 7168, result["volume"])
        output = gp(label) / "FieldLog.apk"
        cmd = [sys.executable, "-B", packager, "--mixer-project", APP / "prepared", "--manifest-apk",
               APP / "apk" / f"manifest-{label}.apk", "--dex", APP / "apk/dex/classes.dex", "--jni-library",
               APP / label / JNI, "--installed-checklist", gp(label) / "Installed", "--checklist-sha256",
               gp(label) / "installed.sha256.json", "--android-sdk", SDK, "--swift-android-sdk",
               SWIFT_ANDROID_SDK, "--java-home", JAVA, "--output", output]
        # Both invocations are sequential and reuse the one development keystore.
        command(*cmd, env=signenv, timeout=90)
        result["cases"][label]["apk"] = check_apk(label, version, output, result["cases"][label])
    apk_key.unlink()
    old, new = (result["cases"][label]["apk"] for label in LABELS)
    require(old["signerSHA256"] == new["signerSHA256"], "APK certificates differ")
    require(old["membersSHA256"].keys() == new["membersSHA256"].keys(), "APK member inventories differ")
    changed = {name for name in old["membersSHA256"] if old["membersSHA256"][name] != new["membersSHA256"][name]}
    require(changed == {"AndroidManifest.xml", "assets/ChecklistRelease/identity.json", APK_PREFIX + JNI},
            f"unexpected non-signature APK byte changes: {sorted(changed)}")
    result["changedAPKMembers"] = sorted(changed)
    result["tools"] = {
        "rustc": command(RUST_BIN / "rustc", "--version").decode().strip(),
        "cargo": command(RUST_BIN / "cargo", "--version").decode().strip(),
        "go": command(GO, "version", env=ENV | {"HOME": os.environ["MIXER_RECIPE_GO_HOME"]}).decode().strip(),
        "xcode": command("/usr/bin/xcodebuild", "-version").decode().strip(),
        "java": command(JAVA / "bin/javac", "-version").decode().strip(),
        "apksigner": command(TOOLS / "apksigner", "version").decode().strip(),
        "aapt2": command(SDK / "build-tools/37.0.0/aapt", "version").decode().strip(),
        "ndkClang": command(NDK / "aarch64-linux-android28-clang", "--version").decode().strip(),
        "swiftFrontendSHA256": filehash(SWIFT_FRONTEND),
        "sdkInfoSHA256": filehash(SWIFT_ANDROID_SDK.parent / "info.json"),
    }
    result["status"] = "apk-pair-verified"


def check_apk(label, version, apk, case):
    cert = command(TOOLS / "apksigner", "verify", "--verbose", "--print-certs", "-Werr", apk).decode()
    signer = re.findall(r"Signer #\d+ certificate SHA-256 digest: ([0-9a-f]{64})", cert)
    require(len(signer) == 1 and "Verified using v3 scheme (APK Signature Scheme v3): true" in cert,
            f"invalid signer or signature for {label}")
    command(TOOLS / "zipalign", "-c", "-P", "16", "4", apk)
    cross_tools = SDK / "build-tools/37.0.0"
    command(cross_tools / "zipalign", "-c", "-P", "16", "4", apk)
    independent_cert = command(cross_tools / "apksigner", "verify", "--verbose", "--print-certs", "-Werr", apk).decode()
    require(re.findall(r"^V3\.0 Signer: certificate SHA-256 digest: ([0-9a-f]{64})$", independent_cert, re.M) == signer and
            "Verified using v3 scheme (APK Signature Scheme v3): true" in independent_cert, "37.0.0 signature disagrees")
    badging = command(cross_tools / "aapt", "dump", "badging", apk).decode()
    require(f"package: name='dev.fieldlog.generatedr90' versionCode='{version}'" in badging and
            "launchable-activity: name='dev.fieldlog.generatedr90.androidhost.PublicActivity'" in badging
            and "sdkVersion:'36'" in badging and "targetSdkVersion:'37'" in badging and
            "native-code: 'arm64-v8a'" in badging, f"APK package, version or launch surface differs for {label}")
    xml = command(cross_tools / "aapt", "dump", "xmltree", apk, "res/xml/checklist_network.xml").decode()
    require("127.0.0.1" in xml and xml.count("cleartextTrafficPermitted=") == 2 and
            "E: base-config (line=3)\n    A: cleartextTrafficPermitted=(type 0x12)0x0" in xml and
            "E: domain-config (line=4)\n    A: cleartextTrafficPermitted=(type 0x12)0xffffffff" in xml, f"APK loopback policy differs for {label}")
    members = {}
    with zipfile.ZipFile(apk) as image:
        for name in image.namelist():
            if not name.startswith("META-INF/"):
                with image.open(name) as stream:
                    members[name] = hashlib.file_digest(stream, "sha256").hexdigest()
        for name, digest in read(gp(label) / "installed.sha256.json").items():
            require(members["assets/ChecklistRelease/" + name] == digest, f"APK member mismatch: {label} {name}")
        require(members[APK_PREFIX + JNI] == case["engine"]["jni"]["sha256"], f"{label} APK JNI differs from link output")
        for name in ("identity.json", "roots.json"):
            extracted = SCRATCH / f"{label}.apk.{name}"
            extracted.write_bytes(image.read(f"assets/ChecklistRelease/{name}"))
        require(json.loads(command(VERIFIER, "identity", SCRATCH / f"{label}.apk.identity.json")) == case["host"],
                f"{label} extracted identity is different")
    return {"sha256": filehash(apk), "bytes": apk.stat().st_size, "signerSHA256": signer[0],
            "signatureSchemeV3": True, "zipAlignmentKiB": 16, "badging": badging.splitlines(),
            "membersSHA256": members}


if __name__ == "__main__":
    run()
