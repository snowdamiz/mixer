#!/usr/bin/env python3
"""Bind source-built FieldLog calculation outputs, then use the maintained APK assembler."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

MIXER = "5dea19db36610e312b51918b384364ba590b6ef8"
FIELDLOG = "552559d2d3278abb9b1aa7dcf0288102c09a202b"
FIELDLOG_TREE = "7753563b91fe162cfb058cb175ccde979b430033"
APP = "Integrations/GeneratedReport"
PACKAGE = "dev.fieldlog.generatedr90.calculation"
JNI = "lib/arm64-v8a/libmixer_public_android_jni.so"
SEED = "f202de8c0101f04e7d6624f90a7f521ce416eb36ae3994d7b1f0692380043260"
PUBLIC_IDENTITY = "1f866af2cd94cf7dac5f09c55c50758950d19f25dec607959e3129fa63cf62bb"
APPEARANCE = "1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3"
MANIFEST = "14e8fb39c7f845dfcc1fe231a4a6fe51a09d9b0ae0290007ca73fcf56772028a"
DISTRIBUTOR = "014f203cb3c14cc454cedb981b206b9a6ae97ffc12d540a2847b8d374828baac"
ADAPTED_DISTRIBUTOR = "8e5830a4b5915f7f6a31eb6687fbc5a46ef50951dfff8d8dc4ea25863502e398"
TRACE = "1f375a5637f950cf4c2816b7aaa86d266ec7bf5b94eac46fa063db85b35b700f"
INPUTS = {
    "bridge.json": "6f05eb3fa8780ee6102d181b0710765214e51168b1429c52dd10dfd1b96873e5",
    "storage.json": "a5946bce4d20c315896cac254404f5fd2910b39e7982ba53744592d5d6e84f67",
    "storage-grant.json": "f630fb1bca6042918d6c29b88027dd8c8da28771599469aee06ff3cd5a3789be",
}
GUESTS = {
    "baseline": "35feea36a6c37cfb6d7c104143f8da041acd93551f42e23fe42f1b885e107610",
    "reviewed": "904f5d414478dcacab2efdcf91f1969b3036ed9b5a763bb5943ad80843a5ea2f",
}


def require(valid, message):
    if not valid:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pin(path, expected):
    require(digest(path) == expected, f"SHA-256 differs for {path}")


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def inventory(root, folder):
    return {p.relative_to(root).as_posix(): digest(p) for p in folder.rglob("*") if p.is_file()}


def tree(pins):
    return hashlib.sha256("".join(f"{value}  {key}\n" for key, value in sorted(pins.items())).encode()).hexdigest()


def capture(env, *command):
    return subprocess.check_output(command, env=env, stderr=subprocess.STDOUT, text=True, timeout=90)


def module(path, work):
    # The pinned distributor owns dependency resolution, licenses, assembly and signing.
    # Apply the calculation profile to its validated six-asset API 37 input contract.
    pin(path, DISTRIBUTOR)
    source = path.read_bytes().decode("utf-8")
    changes = {
        '    "bridge.json": 65_536,': '    "bridge.json": 65_536,\n    "calculation-seed.json": 3530,',
        "targetSdkVersion:'37'": "targetSdkVersion:'36'",
        "package: name='dev.fieldlog.generatedr90' ": f"package: name='{PACKAGE}' ",
        "six Installed": "seven Installed",
    }
    for prior, updated in changes.items():
        require(prior in source, f"Unexpected pinned packager source: {prior}")
        source = source.replace(prior, updated)
    destination = work / "calculation-distributor.py"
    destination.write_bytes(source.encode("utf-8"))
    pin(destination, ADAPTED_DISTRIBUTOR)
    spec = importlib.util.spec_from_file_location("distribution", destination)
    distributor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(distributor)
    return distributor, destination


def verify_jni(ndk, jni, work, env):
    symbols = capture(env, ndk / "bin/llvm-nm", "--dynamic", "--defined-only", jni)
    exported = {line.split()[-1] for line in symbols.splitlines() if line.strip()}
    headers = work / "java/jni"
    checklist, = headers.glob("*ChecklistPanel.h")
    checklist_entries = set(re.findall(r"\bJava_\w+", checklist.read_text()))
    required = {"JNI_OnLoad", "mxis_guest_ui_witness", "mixer_vm_capability_guest_ui_validate_deferred_v1",
                "Java_dev_fieldlog_generatedr90_androidhost_CalculationTrace_record"}
    require(len(checklist_entries) == 5 and checklist_entries | required <= exported,
            "Compiled JNI exports differ from javac headers or trace/VM requirements")
    bridge, = headers.glob("*PublicBridge.h")
    dynamic = re.findall(r"Method:\s+(\w+)\n \* Signature:\s+(\S+)", bridge.read_text())
    c = (work / "fieldlog" / APP / "Platforms/Android/Bridge/PublicBridge.c").read_text()
    binary = jni.read_bytes()
    require(len(dynamic) == 6 and all(f'{{"{name}","{signature}"' in c for name, signature in dynamic)
            and all(token.encode() + b"\0" in binary for pair in dynamic for token in pair)
            and b"FieldLogCalcTrace\0" in binary, "Dynamic JNI registration or trace tag differs")
    return sorted(checklist_entries | required)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("work", "templates", "output", "engine-pair", "android-sdk", "swift-android-sdk", "java-home"):
        parser.add_argument("--" + name, type=lambda p: Path(p).resolve(strict=True), required=True)
    parser.add_argument("--port", type=int, default=41897)
    args = parser.parse_args()
    os.umask(0o077)
    require(0 < args.port <= 65535, "Invalid loopback port")
    work, recipe = args.work, Path(__file__).resolve().parent
    env = os.environ | {"JAVA_HOME": str(args.java_home), "LC_ALL": "C", "TMPDIR": str(work / "tmp")}
    os.environ["TMPDIR"] = env["TMPDIR"]
    tools = args.android_sdk / "build-tools/36.0.0"
    ndk = args.android_sdk / "ndk/27.1.12297006/toolchains/llvm/prebuilt/darwin-x86_64"
    swift = Path.home() / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift-frontend"
    source = work / "fieldlog"
    engine = work / "android-engine"
    engine_receipt = read(engine / "receipt.json")
    vm = engine / "lib/libmixer_vm_capability_experimental.a"
    require(capture(env, "git", "-C", source, "rev-parse", "HEAD").strip() == FIELDLOG
            and capture(env, "git", "-C", source, "write-tree").strip() == FIELDLOG_TREE
            and capture(env, "git", "-C", source, "diff", "--name-only").strip() == "",
            "Expected the verified traced FieldLog checkout")
    require(engine_receipt["source_revision"] == MIXER, "Wrong engine source revision")
    require(engine_receipt["source_manifest_sha256"] ==
            "2d6fb9128e74ec80d3c3c180ffb0d41ec54a376fc6d79f52951093b6a84bd4a3", "Wrong VM source inventory")
    pin(vm, engine_receipt["library"]["sha256"])
    pin(vm, "af8147961b1ffc138a38208fbb1a25481f75c36baac20a9e10a2b4355ca93c20")
    pin(args.templates / "mixer-first-open-trace.patch", TRACE)

    java, native = work / "java", work / "payload"
    jni, dex, manifest = native / Path(JNI).name, java / "dex/classes.dex", java / "manifest.apk"
    pin(dex, "4a828ecb6f73a2f93e52535b914136462828187c84313ffe165607924734c985")
    exports = verify_jni(ndk, jni, work, env)
    distributor, distributor_path = module(source / APP / "scripts/build-signed-checklist-android.py", work)
    project = work / "project"
    appearance = distributor.appearance_asset(project)
    require(hashlib.sha256(appearance).hexdigest() == APPEARANCE, "Unexpected appearance")
    libraries = distributor.native_libraries(jni, ndk, args.swift_android_sdk, env)
    notices = distributor.runtime_notices(project, libraries, ndk, args.swift_android_sdk)
    distribution = {f"lib/arm64-v8a/{name}": digest(path) for name, path in libraries.items() if path != jni}
    distribution.update({name: hashlib.sha256(data).hexdigest() for name, data in notices.items()})
    require(distribution == read(recipe / "distribution-pins.json"),
            "SDK/NDK library or notice inventory differs from the pinned distribution")

    delivery = args.output / "delivery-android"
    installed = delivery / "Installed"
    installed.mkdir(parents=True)
    for name, expected in INPUTS.items():
        path = args.engine_pair / "inputs" / name
        pin(path, expected)
        shutil.copyfile(path, installed / name)
        pin(installed / name, expected)
    seed = args.templates / "calculation-seed.json"
    pin(seed, SEED)
    require(seed.stat().st_size == 3530, "Unexpected seed size")
    shutil.copyfile(seed, installed / seed.name)
    (installed / "port.txt").write_text(f"{args.port}\n")
    pin(installed / seed.name, SEED)
    require((installed / "port.txt").read_text() == f"{args.port}\n", "Loopback port differs")
    template = args.templates / "identity-template.json"
    pin(template, PUBLIC_IDENTITY)
    pin(args.templates / "manifest.json", MANIFEST)
    for variant, expected in GUESTS.items():
        payload = work / "guests" / (variant + ".wasm")
        pin(payload, expected)
        require(payload.stat().st_size == 10540, "Unexpected guest size")

    mixer = work / "mixer"
    fallback = inventory(source, source / APP / "Sources") | inventory(source, source / "Integrations/InstalledGuest")
    bridge_objects = {path.name: digest(path) for path in native.glob("*.o")}
    require(bridge_objects == {
        "CalculationTrace.o": "85cc471eda4922a8ec3598f5e2b29ab0251ef39cf0a15570cc6b4d27b0f3e271",
        "ChecklistBridge.o": "61561485b2faac000ef2321fc8d6073415fc75b73c58f57747df9ffc6d356494",
        "PublicBridge.o": "d6e795216e179ad9709a11d3c9ad0832cf5b84342034a705d8bb7b896f91df75",
        "platform_android.o": "e7e5f24a72dd690d9db422ac8449a5d3f5ed0bc32b27750af3aa98ecb554b164",
        "transport.o": "41906f017b85018c9cb2bba57fa1e108c0b7e0d56e42d5e89ea9c7e9b9e2622c",
    }, "Linked bridge objects differ from the reviewed build")
    link = {
        "mixerSourceInventory": tree(inventory(mixer, mixer)),
        "fieldlogFallbackInventory": tree(fallback),
        "fieldlogAndroidPlatformInventory": tree(inventory(source, source / APP / "Platforms/Android")),
        "vm": digest(vm), "jni": digest(jni), "dex": digest(dex), "linkedManifest": digest(manifest),
        "swiftPackage": digest(recipe / "Package.swift"), "swiftLock": digest(recipe / "Package.resolved"),
        "androidBuildRecipe": digest(recipe / "build-native.zsh"), "javaBuildRecipe": digest(recipe / "build-java.zsh"),
        "appearance": APPEARANCE, "distributor": digest(distributor_path), "publicIdentityTemplate": PUBLIC_IDENTITY,
        "originalDistributor": DISTRIBUTOR, "manifestTemplate": MANIFEST,
        "recipeLock": digest(recipe / "recipe.sha256"), "toolchainLock": digest(recipe / "toolchain-pins.json"),
        "mixerTraceOverlay": TRACE, "javaAdapterPins": digest(recipe / "java-adapter-pins.json"),
    }
    link.update({"bridge/" + name: pin_value for name, pin_value in bridge_objects.items()})
    link.update({"installed/" + name: digest(installed / name) for name in (*INPUTS, seed.name, "port.txt")})
    link.update(distribution)
    compiler_version = capture(env, swift, "-version").splitlines()[0]
    binding = {
        "engine": {"version": MIXER, "source_sha256": engine_receipt["source_manifest_sha256"],
                   "artifact_sha256": digest(vm)},
        "toolchain": {"compiler_version": compiler_version, "compiler_sha256": digest(swift),
                      "sdk_version": "android28", "sdk_sha256": digest(args.swift_android_sdk.parent / "info.json"),
                      "build_tools_sha256": hashlib.sha256(capture(env, tools / "aapt2", "version").strip().encode()).hexdigest()},
        "build": {"settings_sha256": link["swiftPackage"], "link_inputs_sha256": tree(link),
                  "native_fallback_sha256": tree(fallback),
                  "permissions_sha256": digest(java / "AndroidManifest.xml"), "resource_policy_sha256": INPUTS["bridge.json"]},
    }
    write(delivery / "binding.json", binding)
    runtime = capture(env, work / "host-build/debug/Seal", args.templates, delivery, work / "guests").strip()
    identity = read(installed / "identity.json")
    require(runtime == read(delivery / "host.json")["runtime"]
            and all(identity[section][key] == value for section, fields in binding.items() for key, value in fields.items())
            and identity["build"]["trust_roots_sha256"] == digest(installed / "roots.json")
            and identity["capability_execution"]["turn_milliseconds"] == 50 and identity["execution"]["fuel"] == 1000000,
            "Sealed runtime, material or limits differ")

    installed_pins = {path.name: digest(path) for path in installed.iterdir()}
    pin_file = args.output / "installed.sha256.json"
    materials_file = args.output / "materials.sha256.json"
    materials = inventory(args.output, delivery)
    apk = args.output / "FieldLog-calculation-debug-api36.apk"
    write(pin_file, installed_pins)
    write(materials_file, materials)
    distributor.build(argparse.Namespace(output=apk, mixer_project=project, installed_checklist=installed,
        checklist_sha256=pin_file, java_home=args.java_home, android_sdk=args.android_sdk,
        swift_android_sdk=args.swift_android_sdk, jni_library=jni, dex=dex, manifest_apk=manifest))

    signature = capture(env, tools / "apksigner", "verify", "--verbose", "--print-certs", "-Werr", apk)
    signer, = re.findall(r"Signer #1 certificate SHA-256 digest: ([0-9a-f]{64})", signature)
    require("Verified using v3 scheme (APK Signature Scheme v3): true" in signature
            and "Number of signers: 1" in signature, "Expected one v3 signer")
    capture(env, tools / "zipalign", "-c", "-P", "16", "4", apk)
    badging = capture(env, tools / "aapt2", "dump", "badging", apk)
    require("application-debuggable" in badging and "android.permission.INTERNET" in badging, "Missing Debug or loopback permission")
    policy = capture(env, tools / "aapt2", "dump", "xmltree", apk, "--file", "res/xml/checklist_network.xml")
    expected_policy = [
        "E: network-security-config (line=2)", "E: base-config (line=3)", "A: cleartextTrafficPermitted=false",
        "E: domain-config (line=4)", "A: cleartextTrafficPermitted=true", "E: domain (line=4)", "T: '127.0.0.1'",
    ]
    require([line.strip() for line in policy.splitlines() if line.strip()] == expected_policy,
            "Loopback cleartext policy differs")
    with zipfile.ZipFile(apk) as image, zipfile.ZipFile(manifest) as resources:
        require(len(set(image.namelist())) == len(image.namelist()), "Duplicate APK member")
        members = {}
        for name in image.namelist():
            if not name.startswith("META-INF/"):
                with image.open(name) as stream:
                    members[name] = hashlib.file_digest(stream, "sha256").hexdigest()
        expected = distribution | {JNI: digest(jni), "classes.dex": digest(dex),
            "assets/MixerAppearanceV2/descriptor.json": APPEARANCE}
        expected.update({"assets/ChecklistRelease/" + name: value for name, value in installed_pins.items()})
        expected.update({name: hashlib.sha256(resources.read(name)).hexdigest() for name in resources.namelist()})
        require(members == expected, "APK member bytes differ from rebuilt or pinned inputs")
    write(args.output / "build-receipt.json", {
        "apk": apk.name, "apkSHA256": digest(apk), "apkSignerSHA256": signer, "apkV3": True, "aligned16KiB": True,
        "package": PACKAGE, "minSdk": 36, "targetSdk": 36, "abi": "arm64-v8a", "configuration": "debug",
        "androidRuntime": runtime, "binding": binding, "mixerRevision": MIXER, "fieldlogRevision": FIELDLOG,
        "fieldlogTree": FIELDLOG_TREE, "linkedInputs": link, "apkMembersSHA256": members,
        "jniExportsVerified": exports, "guestSHA256": GUESTS, "relayPort": args.port,
        "limits": {"turnMilliseconds": 50, "fuel": 1000000, "ordinaryTransportBytes": 8192, "fixturePayloadBytes": 10540},
        "storage": {"namespace": "fieldlog-task-v1", "key": "completion-rows", "operations": ["get"]},
        "signatureVerification": signature.splitlines(), "badging": badging.splitlines(), "loopbackPolicy": policy.splitlines(),
    })
    print(runtime)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"{error}\n{error.output}") from error
