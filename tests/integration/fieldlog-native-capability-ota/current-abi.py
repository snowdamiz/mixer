"""Seal the current-ABI FieldLog Android pair and check its stock CLI admission."""

import argparse
from hashlib import sha256
import importlib.util
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CALC = HERE.parent / "fieldlog-task-calculation/android-packaging"
sys.path.insert(0, str(CALC))
import package as calc

spec = importlib.util.spec_from_file_location("pair", HERE / "package-android-pair.py")
pair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pair)
from package import capture, digest, inventory, pin, read, require, tree, write
from current_abi_packet import SEALED, bindings, require_members, validate_for_seal
from current_abi_recipe import CALCULATION_LOCK, verify as verify_recipe

REVISION = "b144c2c2042a4499365d1186f46d43fba1832143"
ABI = "29ab6ba4a86990bc99d4f510fc005a17d84426d8c893d36f5061f17c46786adf"
SUCCESSOR = "1e790dafda9fb7f730003cc678209e7a716a910b"
FIXTURES = "capability-activation/Tests/MixerCapabilityActivationTests/Fixtures"
ARCHIVE = "libmixer_vm_capability_experimental.a"
VM_SYMBOL = "mixer_vm_capability_guest_ui_validate_deferred_v1"
LABELS = ("old", "successor")
PROJECT = "Integrations/GeneratedReport"


def adapter_pins(repo, output):
    pins = {}
    for name in read(CALC / "java-adapter-pins.json"):
        data = subprocess.check_output(["git", "-C", repo, "show", f"{REVISION}:native/android/{name}"], timeout=15)
        pins[name] = {"bytes": len(data), "sha256": sha256(data).hexdigest()}
    write(output, pins)


def check_link(work, vm):
    link_map = work / "link.map"
    sections = set()
    with link_map.open() as rows:
        for row in rows:
            if f"/{ARCHIVE}(" not in row:
                continue
            match = re.search(r"\s(/.*?/" + re.escape(ARCHIVE) + r")\(([^)]+)\):\((.+)\)", row)
            require(match is not None, "Unexpected LLD archive map entry")
            archive, member, section = match.groups()
            require(Path(archive).resolve(strict=True) == vm, "A different VM archive participated in the link")
            if section == f".text.{VM_SYMBOL}":
                sections.add(member)
    require(len(sections) == 1, "Expected the deferred Guest UI implementation from the pinned VM archive")
    return {"mapSHA256": digest(link_map), "symbol": VM_SYMBOL, "archiveMember": sections.pop()}


def check_swiftpm(work, env):
    inputs = read(work / "preflight.json")["swiftPMInputs"]
    for variant in (work, work / "successor"):
        for build in ("android-build", "host-build"):
            for name, expected in inputs.items():
                checkout = variant / build / "checkouts" / name
                git = ("git", "-C", checkout)
                require(capture(env, *git, "log", "-1", "--format=%H %T").strip() ==
                        f'{expected["revision"]} {expected["tree"]}'
                        and not capture(env, *git, "status", "--porcelain", "--untracked-files=all").strip(),
                        f"{build} checkout differs: {name}")


def contract(image, tools, env):
    permissions = capture(env, tools / "aapt2", "dump", "permissions", image).splitlines()
    require(permissions == [f"package: {calc.PACKAGE}", "uses-permission: name='android.permission.INTERNET'"],
            "Unexpected packaged Android permissions")
    return {
        "bundleID": calc.PACKAGE, "permissions": permissions[1:],
        "compiledManifest": capture(env, tools / "aapt2", "dump", "xmltree", image, "--file", "AndroidManifest.xml"),
    }


def package(work, packet):
    env = os.environ.copy()
    check_swiftpm(work, env)
    sdk, java_home = Path(env["ANDROID_HOME"]), Path(env["JAVA_HOME"])
    tools = sdk / "build-tools/36.0.0"
    ndk = sdk / "ndk/27.1.12297006/toolchains/llvm/prebuilt/darwin-x86_64"
    swift_sdk = next((work / "swift-sdks").iterdir()) / "swift-android"
    vm = (work / "android-engine/lib" / ARCHIVE).resolve(strict=True)
    receipt = read(work / "android-engine/receipt.json")
    require(receipt["source_revision"] == REVISION and receipt["rust_target"] == "aarch64-linux-android"
            and receipt["commands"] and all(row["exit_code"] == 0 and row["problem"] is None
                                             for row in receipt["commands"]), "Expected a closed pinned Android VM build")
    pin(vm, receipt["library"]["sha256"])
    fixture = work / "mixer" / FIXTURES
    pin(fixture / "native-preimage.json", ABI)
    sdk_identity = work / "mixer/sdk/Sources/MixerCapabilities/GeneratedIdentity.swift"
    require(f'"{ABI}"' in sdk_identity.read_text(), "SDK native identity differs from the pinned preimage")
    template = CALC / "rebuild-inputs/identity-template.json"
    pin(template, calc.PUBLIC_IDENTITY)
    pair_inputs = HERE.parent / "fieldlog-android-engine-pair/inputs"
    manifest = pair_inputs / "manifest.json"
    pin(manifest, calc.MANIFEST)

    for variant, expected in calc.GUESTS.items():
        guest = work / "guests" / f"{variant}.wasm"
        pin(guest, expected)
        shutil.copyfile(guest, packet / guest.name)
    source_map = packet / "source-map.json"
    source_map.write_bytes(b"{}")
    pin(source_map, read(manifest)["source_map_sha256"])
    (packet / "refused").mkdir()

    assembler, _ = calc.module(
        work / "fieldlog" / PROJECT / "scripts/build-signed-checklist-android.py", work)
    scripts = pair.distributor(work, work)
    project = work / "project"
    require(sha256(assembler.appearance_asset(project)).hexdigest() == calc.APPEARANCE,
            "Appearance resource differs from pinned input")
    with socket.socket() as chooser:
        chooser.bind(("127.0.0.1", 0))
        port = chooser.getsockname()[1]

    variants = (work, work / "successor")
    links, distributions, exports = {}, {}, {}
    for label, variant, expected_tree, script in zip(LABELS, variants, (pair.OLD_TREE, SUCCESSOR), scripts, strict=True):
        fieldlog, java, payload = (variant / name for name in ("fieldlog", "java", "payload"))
        git = ("git", "-C", fieldlog)
        require(capture(env, *git, "rev-parse", "HEAD").strip() == calc.FIELDLOG
                and capture(env, *git, "write-tree").strip() == expected_tree
                and not capture(env, *git, "diff", "--name-only").strip(), "FieldLog build tree differs")
        folder = packet / label
        installed = folder / "Installed"
        installed.mkdir(parents=True)
        for name, expected in calc.INPUTS.items():
            pin(pair_inputs / name, expected)
            shutil.copyfile(pair_inputs / name, installed / name)
        seed = CALC / "rebuild-inputs/calculation-seed.json"
        pin(seed, calc.SEED)
        shutil.copyfile(seed, installed / seed.name)
        (installed / "port.txt").write_text(f"{port}\n")

        identity = read(template)
        identity["capabilities"][0]["native_sha256"] = ABI
        if label == "successor":
            http, = [item for item in read(fixture / "identity.json")["capabilities"] if item["id"] == pair.CAPABILITY]
            require(http["native_sha256"] == ABI
                    and http["configuration_sha256"] == pair.HTTPS["http.json"]
                    and http["grants_sha256"] == pair.HTTPS["http-grant.json"], "HTTPS material metadata differs")
            for name, expected in pair.HTTPS.items():
                pin(fixture / name, expected)
                shutil.copyfile(fixture / name, installed / name)
            identity["capabilities"].insert(0, http)

        jni = payload / Path(calc.JNI).name
        exports[label] = calc.verify_jni(ndk, jni, variant, env)
        require(ABI.encode() in jni.read_bytes(), "Linked JNI lacks the current SDK native identity")
        link_observation = check_link(variant, vm)
        native = assembler.native_libraries(jni, ndk, swift_sdk, env)
        notices = assembler.runtime_notices(project, native, ndk, swift_sdk)
        distribution = {f"lib/arm64-v8a/{name}": digest(path) for name, path in native.items() if path != jni}
        distribution.update({name: sha256(data).hexdigest() for name, data in notices.items()})
        require(distribution == read(CALC / "distribution-pins.json"), "SDK/NDK distribution differs")
        distributions[label] = distribution
        compiled = java / "manifest.apk"
        write(folder / "permissions.json", contract(compiled, tools, env))
        fallback = inventory(fieldlog, fieldlog / PROJECT / "Sources") | inventory(fieldlog, fieldlog / "Integrations/InstalledGuest")
        link = {
            "mixerSource": tree(inventory(work, work / "mixer")),
            "fieldlogPlatform": tree(inventory(fieldlog, fieldlog / PROJECT / "Platforms/Android")),
            "vm": digest(vm), "jni": digest(jni), "dex": digest(java / "dex/classes.dex"),
            "linkedManifest": digest(compiled), "nativeABI": digest(fixture / "native-preimage.json"),
            "swiftPackage": digest(CALC / "Package.swift"), "swiftLock": digest(CALC / "Package.resolved"),
            "nativeRecipe": digest(CALC / "build-native.zsh"), "javaRecipe": digest(CALC / "build-java.zsh"),
            "adapterPins": digest(work / "current-adapter-pins.json"), "distributor": digest(script),
            "appearance": calc.APPEARANCE,
        }
        link.update({"bridge/" + path.name: digest(path) for path in payload.glob("*.o")})
        link.update({"installed/" + name: value for name, value in inventory(installed, installed).items()})
        link.update(distribution)
        identity["build"].update(
            generated_bridge_sha256=ABI, settings_sha256=link["swiftPackage"], link_inputs_sha256=tree(link),
            native_fallback_sha256=tree(fallback), permissions_sha256=digest(folder / "permissions.json"))
        identity["engine"].update(version=REVISION, source_sha256=receipt["source_manifest_sha256"], artifact_sha256=link["vm"])
        # The historical template already pins these tools. Re-observe them for this build.
        compiler = Path(env["MIXER_SWIFT"]).with_name("swift-frontend")
        identity["toolchain"].update(
            compiler_version=capture(env, compiler, "-version").splitlines()[0], compiler_sha256=digest(compiler),
            sdk_sha256=digest(swift_sdk.parent / "info.json"),
            build_tools_sha256=sha256(capture(env, tools / "aapt2", "version").strip().encode()).hexdigest())
        write(folder / "identity-input.json", identity)
        write(folder / "linked-inputs.json", link)
        links[label] = link_observation

    capture(env, variants[1] / "host-build/debug/Seal", packet, manifest, packet / "reviewed.wasm", REVISION,
            packet / "baseline.wasm")
    key = work / "https-development.p12"
    password = "FIELDLOG_LOCAL_APK_PASSWORD"
    sign_env = env | {password: secrets.token_hex(24), "FIELDLOG_PAIR_APK_KEYSTORE": str(key)}
    results = {}
    try:
        capture(sign_env, java_home / "bin/keytool", "-genkeypair", "-storetype", "PKCS12", "-keystore", key,
                "-alias", "fieldlog-local", "-storepass:env", password, "-keypass:env", password,
                "-keyalg", "EC", "-groupname", "secp256r1", "-validity", "30", "-dname", "CN=FieldLog Native HTTPS Test Pair")
        for label, variant, script in zip(LABELS, variants, scripts, strict=True):
            folder = packet / label
            installed = folder / "Installed"
            identity = read(installed / "identity.json")
            require(identity["build"]["link_inputs_sha256"] == tree(read(folder / "linked-inputs.json"))
                    and identity["build"]["trust_roots_sha256"] == digest(installed / "roots.json")
                    and read(folder / "host.json")["runtime"] == read(folder / "assignment.json")["assignment"]["runtime"],
                    "Sealed runtime does not bind the recorded APK inputs and offer")
            (folder / "identity-input.json").unlink()
            pins = folder / "installed.sha256.json"
            write(pins, inventory(installed, installed))
            apk, java, payload = folder / "FieldLog.apk", variant / "java", variant / "payload"
            capture(sign_env, sys.executable, "-B", script, "--output", apk, "--mixer-project", project,
                    "--installed-checklist", installed, "--checklist-sha256", pins, "--java-home", java_home,
                    "--android-sdk", sdk, "--swift-android-sdk", swift_sdk, "--jni-library", payload / Path(calc.JNI).name,
                    "--dex", java / "dex/classes.dex", "--manifest-apk", java / "manifest.apk")
            result = pair.verify_image(apk, installed, java, payload, variant, tools, ndk, env, 1)
            require(contract(apk, tools, env) == read(folder / "permissions.json"), "Signed manifest contract drift")
            require(all(result["members"][name] == value for name, value in distributions[label].items()),
                    "Signed APK Swift/NDK distribution differs")
            result["jniExports"] = exports[label]
            result["vmLink"] = links[label]
            result["runtime"] = read(folder / "host.json")["runtime"]
            results[label] = result
    finally:
        key.unlink(missing_ok=True)

    old, new = results.values()
    changed = pair.changed_members(old["members"], new["members"])
    require(old["signerSHA256"] == new["signerSHA256"] and old["elfNeeded"] == new["elfNeeded"]
            and digest(packet / "old/permissions.json") == digest(packet / "successor/permissions.json")
            and digest(packet / "old/Installed/roots.json") == digest(packet / "successor/Installed/roots.json"),
            "APK signer, manifest, OTA root or dependency drift")
    require(changed == {calc.JNI, "classes.dex", pair.ASSETS + "identity.json"} | {pair.ASSETS + name for name in pair.HTTPS},
            f"Unexpected signed APK member delta: {sorted(changed)}")
    write(packet / "build.json", {
        "mixerRevision": REVISION, "fieldlogRevision": calc.FIELDLOG,
        "fieldlogTrees": {"old": pair.OLD_TREE, "successor": SUCCESSOR}, "nativeABI": ABI,
        "vm": {"archiveSHA256": digest(vm), "sourceManifestSHA256": receipt["source_manifest_sha256"]},
        "apks": results, "changedMembers": sorted(changed), "guests": calc.GUESTS,
        "compiledManifestSHA256": old["members"]["AndroidManifest.xml"],
        "manifestContractSHA256": digest(packet / "old/permissions.json"), "port": port,
        "handoffInputs": bindings(packet),
    })


def seal(work, packet, recipe_revision):
    stages = {
        "preflight", "fieldlog-fetch", "mixer-export", "stock-export", "build-guests", "fieldlog-checkout",
        "fieldlog-baseline", "fieldlog-clone", "fieldlog-successor-base", "fieldlog-https-overlay",
        "mixer-trace-overlay", "adapter-inputs", "vm-android", "vm-host", "java-old", "java-successor",
        "build-stock", "build-update", "native-old", "native-successor", "host-old", "host-successor",
        "stock-project", "package", "host-replay", "inspect",
    }
    receipts = {path.stem: read(path) for path in (work / "logs").glob("*.json")}
    require(receipts.keys() == stages and all(
        row["custody"] == "closed" and row["exit"] == 0 and "interrupted" not in row
        and not any(key in row for key in ("collectionErrors", "scratchSampleError", "scratchLimitExceeded"))
        for row in receipts.values()), "Incomplete current ABI build stage")
    tools = read(work / "preflight.json")
    source_inputs = verify_recipe(HERE.parents[2], recipe_revision)
    recipe_lock = source_inputs[CALCULATION_LOCK.as_posix()]
    require(recipe_lock == tools["recipeLockSHA256"], "Calculation recipe differs from preflight")
    validate_for_seal(packet)
    write(packet / "rebuild.json", {
        "stageResults": {name: {key: row[key] for key in ("exit", "custody")} for name, row in receipts.items()},
        "peakSampledScratchKiB": max(row["peakSampledScratchKiB"] for row in receipts.values()),
        "toolVersions": tools["toolVersions"], "swiftPMInputs": tools["swiftPMInputs"],
        "recipeCommit": recipe_revision, "sourceInputs": source_inputs, "calculationRecipeSHA256": recipe_lock,
    })
    with (packet / "android-origin.py").open("xb") as relay:
        relay.write((HERE / "android-origin.py").read_bytes())
    pin(packet / "android-origin.py", source_inputs[(HERE / "android-origin.py").relative_to(HERE.parents[2]).as_posix()])
    require_members(packet, SEALED)
    pending = work / "handoff-checksums.new"
    with pending.open("x") as sums:
        for name in sorted(SEALED):
            sums.write(f"{digest(packet / name)}  {name}\n")
    # Publish the complete checksum file without overwriting a prior seal.
    os.link(pending, packet / "SHA256SUMS")
    pending.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("package", "seal", "adapter-pins"))
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--recipe-revision", help="independently selected recipe commit, required for seal")
    args = parser.parse_args()
    if (args.action == "seal") != bool(args.recipe_revision):
        parser.error("--recipe-revision is required for seal and only accepted for seal")
    try:
        source, output = args.input.resolve(strict=True), args.output.resolve()
        if args.action == "seal":
            seal(source, output, args.recipe_revision)
        else:
            {"package": package, "adapter-pins": adapter_pins}[args.action](source, output)
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"{error}\n{error.stdout or error.stderr}") from error
