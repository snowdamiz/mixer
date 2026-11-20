"""Seal the two row guests against the fresh Android APK link inputs."""
import argparse
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import zipfile

from prepare import FIELDLOG_ROW_TREE, git

ROW = Path(__file__).resolve().parent
CALC = ROW.parent / "fieldlog-task-calculation/android-packaging"
PAIR = ROW.parent / "fieldlog-android-engine-pair/inputs"
MIXER = "71e6ffa51e857d5a1eda3f74c26941996ed275de"
NATIVE_ID = "29ab6ba4a86990bc99d4f510fc005a17d84426d8c893d36f5061f17c46786adf"
GUESTS = {
    "baseline": "c76c22bfa086ce6b19775f282cf36f8690464c63374085046fbc337226c49b42",
    "reviewed": "de422cba560554bc8642a4c3205c320a7ce870a8a05ff61be3231bbe5a9da9ab",
}

spec = importlib.util.spec_from_file_location("calculation_packager", CALC / "package.py")
calculation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calculation)
digest, pin, read, require, tree, write = (
    calculation.digest, calculation.pin, calculation.read, calculation.require, calculation.tree, calculation.write
)


def package(work, output):
    sdk = Path("/opt/homebrew/share/android-commandlinetools")
    java_home = Path("/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home")
    swift_sdk = Path.home() / ".swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android"
    tools = sdk / "build-tools/36.0.0"
    ndk = sdk / "ndk/27.1.12297006/toolchains/llvm/prebuilt/darwin-x86_64"
    env = os.environ | {"TMPDIR": str(work / "tmp"), "JAVA_HOME": str(java_home), "LC_ALL": "C"}

    def capture(*argv):
        return calculation.capture(env, *argv)

    source = work / "fieldlog"
    engine = read(work / "android-engine/receipt.json")
    vm = work / "android-engine/lib/libmixer_vm_capability_experimental.a"
    require(git(source, "rev-parse", "HEAD") == calculation.FIELDLOG
            and git(source, "write-tree") == FIELDLOG_ROW_TREE and not git(source, "diff", "--name-only"),
            "Expected the pinned FieldLog row projection")
    require(engine["source_revision"] == MIXER, "Wrong VM revision")
    pin(vm, engine["library"]["sha256"])
    for name, expected in GUESTS.items():
        pin(work / "guests" / (name + ".wasm"), expected)

    jni = work / "payload" / Path(calculation.JNI).name
    java = work / "java"
    dex, manifest = java / "dex/classes.dex", java / "manifest.apk"
    exports = calculation.verify_jni(ndk, jni, work, env)

    templates = work / "templates"
    templates.mkdir()
    original_template = CALC / "rebuild-inputs/identity-template.json"
    pin(original_template, calculation.PUBLIC_IDENTITY)
    identity = read(original_template)
    identity["build"]["generated_bridge_sha256"] = NATIVE_ID
    identity["capabilities"][0]["native_sha256"] = NATIVE_ID
    write(templates / "identity-template.json", identity)
    pin(PAIR / "manifest.json", calculation.MANIFEST)
    shutil.copyfile(PAIR / "manifest.json", templates / "manifest.json")

    delivery = output / "delivery-android"
    installed = delivery / "Installed"
    installed.mkdir(parents=True)
    for name, expected in calculation.INPUTS.items():
        pin(PAIR / name, expected)
        shutil.copyfile(PAIR / name, installed / name)
    seed = CALC / "rebuild-inputs/calculation-seed.json"
    pin(seed, calculation.SEED)
    shutil.copyfile(seed, installed / "calculation-seed.json")
    with socket.socket() as chooser:
        chooser.bind(("127.0.0.1", 0))
        port = chooser.getsockname()[1]
    (installed / "port.txt").write_text(f"{port}\n")

    app = source / calculation.APP
    distributor, distributor_path = calculation.module(app / "scripts/build-signed-checklist-android.py", work)
    project = work / "project"
    appearance = distributor.appearance_asset(project)
    require(sha256(appearance).hexdigest() == calculation.APPEARANCE, "Unexpected appearance asset")
    libraries = distributor.native_libraries(jni, ndk, swift_sdk, env)
    notices = distributor.runtime_notices(project, libraries, ndk, swift_sdk)
    distribution = {f"lib/arm64-v8a/{name}": digest(path) for name, path in libraries.items() if path != jni}
    distribution.update({name: sha256(data).hexdigest() for name, data in notices.items()})
    require(distribution == read(CALC / "distribution-pins.json"), "SDK/NDK distribution differs")

    fallback = calculation.inventory(source, app / "Sources") | calculation.inventory(source, source / "Integrations/InstalledGuest")
    link = {
        "mixerSource": tree(calculation.inventory(work, work / "mixer")),
        "fieldlogPlatform": tree(calculation.inventory(source, app / "Platforms/Android")), "vm": digest(vm),
        "jni": digest(jni), "dex": digest(dex), "linkedManifest": digest(manifest),
        "rowRecipe": tree(calculation.inventory(ROW, ROW)),
        "calculationRecipe": digest(CALC / "recipe.sha256"),
        "distributor": digest(distributor_path), "appearance": calculation.APPEARANCE,
    }
    link.update({f"installed/{path.name}": digest(path) for path in installed.iterdir()})
    link.update(distribution)
    binding = {
        "engine": {"version": MIXER, "source_sha256": engine["source_manifest_sha256"], "artifact_sha256": digest(vm)},
        "toolchain": identity["toolchain"],
        "build": {"settings_sha256": digest(CALC / "Package.swift"), "link_inputs_sha256": tree(link),
                  "native_fallback_sha256": tree(fallback), "permissions_sha256": digest(java / "AndroidManifest.xml"),
                  "resource_policy_sha256": calculation.INPUTS["bridge.json"]},
    }
    write(delivery / "binding.json", binding)
    runtime = capture(work / "host-build/debug/Seal", templates, delivery, work / "guests").strip()
    sealed = read(installed / "identity.json")
    require(runtime == read(delivery / "host.json")["runtime"]
            and all(sealed[section][key] == value for section, fields in binding.items() for key, value in fields.items())
            and sealed["build"]["trust_roots_sha256"] == digest(installed / "roots.json"), "Runtime binding differs")

    apk = output / "FieldLog-reorder-debug-api36.apk"
    installed_pins = {path.name: digest(path) for path in installed.iterdir()}
    pin_file = output / "installed.sha256.json"
    write(pin_file, installed_pins)
    write(output / "materials.sha256.json", calculation.inventory(output, delivery))
    distributor.build(argparse.Namespace(output=apk, mixer_project=project, installed_checklist=installed,
        checklist_sha256=pin_file, java_home=java_home, android_sdk=sdk, swift_android_sdk=swift_sdk,
        jni_library=jni, dex=dex, manifest_apk=manifest))

    signature = capture(tools / "apksigner", "verify", "--verbose", "--print-certs", "-Werr", apk)
    require("Verified using v3 scheme (APK Signature Scheme v3): true" in signature
            and "Number of signers: 1" in signature, "Expected one v3 signer")
    capture(tools / "zipalign", "-c", "-P", "16", "4", apk)
    badging = capture(tools / "aapt2", "dump", "badging", apk)
    require(f"package: name='{calculation.PACKAGE}'" in badging and "targetSdkVersion:'36'" in badging
            and "application-debuggable" in badging and "android.permission.INTERNET" in badging,
            "Unexpected application identity or permission")
    with zipfile.ZipFile(apk) as image, zipfile.ZipFile(manifest) as resources:
        require(len(set(image.namelist())) == len(image.namelist()), "Duplicate APK member")
        members = {name: sha256(image.read(name)).hexdigest() for name in image.namelist()
                   if not name.startswith("META-INF/")}
        expected = distribution | {calculation.JNI: digest(jni), "classes.dex": digest(dex),
                                     "assets/MixerAppearanceV2/descriptor.json": calculation.APPEARANCE}
        expected.update({"assets/ChecklistRelease/" + name: value for name, value in installed_pins.items()})
        expected.update({name: sha256(resources.read(name)).hexdigest() for name in resources.namelist()})
        require(members == expected, "APK member bytes differ from source-built or pinned inputs")
    write(output / "build-receipt.json", {
        "apk": apk.name, "apkSHA256": digest(apk), "androidRuntime": runtime, "binding": binding,
        "androidPackage": calculation.PACKAGE, "targetSdk": 36, "abi": "arm64-v8a", "port": port,
        "mixerRevision": MIXER, "fieldlogRevision": calculation.FIELDLOG, "fieldlogTree": FIELDLOG_ROW_TREE,
        "linkedInputs": link, "apkMembersSHA256": members, "guestSHA256": GUESTS, "jniExportsVerified": exports,
        "signatureVerification": signature.splitlines(), "badging": badging.splitlines(),
    })
    shutil.copyfile(CALC / "origin.py", output / "origin.py")
    print(runtime)


if __name__ == "__main__":
    os.umask(0o077)
    package(*(Path(arg).resolve(strict=True) for arg in sys.argv[1:]))
