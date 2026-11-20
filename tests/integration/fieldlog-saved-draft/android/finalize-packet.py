#!/usr/bin/env python3
"""Verify the rebuilt native payload and write the root runner's packet pins."""
from datetime import datetime, timezone
from hashlib import file_digest
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

SOURCE = Path(__file__).resolve().parent
APK_NAME = "FieldLog-selected-draft-dev-arm64.apk"
NDK = Path("/opt/homebrew/share/android-commandlinetools/ndk/27.1.12297006")
LLVM = NDK / "toolchains/llvm/prebuilt/darwin-x86_64/bin"
XCODE = "/Applications/Xcode_26.6.app/Contents/Developer"


def load(path):
    return json.loads(path.read_bytes())


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def write(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def output(*argv, env=None):
    return subprocess.check_output(argv, env=env, text=True, timeout=30).strip()


def compare_inventory(fresh, previous, expected, label):
    actual = {name for name in previous.keys() | fresh.keys() if fresh.get(name) != previous.get(name)}
    require(fresh.keys() == previous.keys() and actual == expected,
            f"{label}: missing changes {sorted(expected - actual)}, unexpected changes {sorted(actual - expected)}")
    return {name: {"previous": previous[name], "rebuild": fresh[name]} for name in sorted(actual)}


def main(work, packet):
    pins = load(SOURCE / "reviewed-pins.json")
    reviewed = pins["source"]
    diagnostic = load(SOURCE / "diagnostic-pins.json")
    require(all(digest(SOURCE / path) == checksum for path, checksum in diagnostic["overlaySHA256"].items())
            and digest(SOURCE / "reference/root-failed-run-identity.json") == diagnostic["priorRootIdentitySHA256"],
            "Wrong trace overlay or failed-run reference")
    capture = load(packet / "source-capture.json")
    prior_diagnostic = diagnostic["priorDiagnostic"]
    prior_storage = diagnostic["priorStorage"]
    prior_renderer = diagnostic["priorRenderer"]
    renderer_capture_path = SOURCE / "reference/prior-renderer-capture.json"
    renderer_identity_path = SOURCE / "reference/prior-renderer-identity.json"
    require(digest(renderer_capture_path) == prior_renderer["captureSHA256"]
            and digest(renderer_identity_path) == prior_renderer["identitySHA256"]
            and digest(SOURCE / "reference/prior-renderer-roots.json") == prior_renderer["trust"],
            "Wrong closed renderer packet comparison")
    renderer_capture = load(renderer_capture_path)
    native = work / "payload/libmixer_public_android_jni.so"
    abi = capture["binding"]["engine"]
    apk = packet / APK_NAME
    old_apk = pins["previousApk"]
    source = reviewed | {
        "linkInputSHA256": capture["binding"]["build"]["link_inputs_sha256"],
        "linkInventoryEntries": len(capture["linkFiles"]),
    }
    fresh_files = capture["linkFiles"]
    first_frame_changes = set(diagnostic["firstFrameSourceSHA256"]) | {
        "payload/bridge/DraftPressTrace.o", "payload/libmixer_public_android_jni.so",
    }
    source["comparisons"] = {
        "priorRendererLink": compare_inventory(fresh_files, renderer_capture["linkFiles"],
            first_frame_changes, "Reviewed renderer and bounded first-frame sources"),
    }
    renderer_package = {name: sha for name, sha in renderer_capture["apkMembersSHA256"].items()
                        if not name.startswith("META-INF/")}
    current_package = {name: sha for name, sha in capture["apkMembersSHA256"].items()
                       if not name.startswith("META-INF/")}
    source["comparisons"]["priorRendererApkMembers"] = compare_inventory(current_package, renderer_package, {
        "assets/ChecklistRelease/identity.json", "assets/ChecklistRelease/roots.json",
        "lib/arm64-v8a/libmixer_public_android_jni.so",
    }, "APK members apart from signing metadata")
    require(current_package["classes.dex"] == prior_renderer["dex"]
            and current_package["classes.dex"] == digest(work / "java/dex/classes.dex"),
            "Wrong tested renderer DEX")
    source["priorInstalledStorageCorrection"] = prior_storage
    source["priorInstalledDiagnostic"] = prior_diagnostic
    source["priorRendererPacket"] = {key: prior_renderer[key] for key in ("apk", "receiptSHA256", "captureSHA256", "runtime")}
    require(all(fresh_files.get(name) == checksum for name, checksum in diagnostic["sourceSHA256"].items()),
            "A diagnostic source input differs from its pin")
    source.update(recipeManifestSHA256=digest(SOURCE / "SHA256SUMS"), fieldLogTree=diagnostic["fieldLogTree"], fallbackSHA256=diagnostic["fallbackSHA256"],
                  reviewedFieldLogTree=reviewed["fieldLogTree"], diagnosticOverlaysSHA256=diagnostic["overlaySHA256"])
    require(capture["fieldLogTree"] == diagnostic["fieldLogTree"]
            and capture["mixerRevision"] == reviewed["mixerRevision"]
            and capture["publicProfile"]["id"] == reviewed["profile"]
            and digest(packet / "mixer.lock") == reviewed["profileLockSHA256"]
            and abi == reviewed["engine"]
            and capture["binding"]["build"]["native_fallback_sha256"] == diagnostic["fallbackSHA256"],
            "Reviewed source, toolchain profile or fallback differs")
    require(digest(apk) == capture["apkSHA256"]
            and capture["apkSHA256"] not in (old_apk["sha256"], prior_renderer["apk"]),
            "APK SHA mismatch or reused APK")
    jni_sha = digest(native)
    require(jni_sha == capture["apkMembersSHA256"]["lib/arm64-v8a/" + native.name]
            == capture["payload"][native.name] == digest(
                work / "android-build/aarch64-unknown-linux-android28/debug" / native.name)
            and jni_sha != prior_renderer["jni"], "APK, fresh link output and bound JNI bytes differ or were reused")
    with zipfile.ZipFile(apk) as archive:
        jni_bytes = archive.read("lib/arm64-v8a/" + native.name)
    markers = ("first_document", "first_draw", "checklist_begin", "checklist_observe", "checklist_result",
               "checklist_protocol", "checklist_bridge", "checklist_retire")
    require(all(marker.encode() + b"\0" in jni_bytes for marker in markers), "APK JNI lacks the fixed diagnostic markers")
    loads = [line.split() for line in output(LLVM / "llvm-readelf", "-lW", native).splitlines()
             if line.lstrip().startswith("LOAD ")]
    require(loads and all(int(row[-1], 16) >= 16384
                          and int(row[1], 16) % 16384 == int(row[2], 16) % 16384 for row in loads),
            "Fresh JNI has a non-16-KiB ELF load segment")

    members = {Path(name).name: checksum for name, checksum in capture["apkMembersSHA256"].items()
               if name.startswith("lib/arm64-v8a/")}
    closure = load(SOURCE / "reviewed-package-inputs.json")["nativeLibraries"]
    require(set(members) == set(closure)
            and all(checksum == closure[name]["sha256"] for name, checksum in members.items()
                    if name != native.name), "Reviewed support library closure differs")
    require(capture["apkMembersSHA256"]["classes.dex"] != old_apk["dexSHA256"]
            and digest(work / "java/manifest.apk") == old_apk["linkedManifestSHA256"]
            and capture["apkMembersSHA256"]["assets/MixerAppearanceV2/descriptor.json"]
                == old_apk["buildDescriptorSHA256"], "Diagnostic DEX, reviewed linked manifest or descriptor differs")

    symbols = set(output(LLVM / "llvm-nm", "--defined-only", native).split())
    require(set(pins["symbols"].values()) <= symbols, "Final ELF lacks reviewed binding symbols")
    adapter = {}
    for name, checksum in pins["adapterSource"].items():
        require(digest(work / "fieldlog" / name) == checksum, f"Wrong adapter source {name}")
        adapter[name] = {"sourceSHA256": checksum}
    for obj, expected in pins["relocations"].items():
        path = work / "android-build/aarch64-unknown-linux-android28/debug/FieldLogAndroid.build" / obj
        relocations = output(LLVM / "llvm-readelf", "--relocations", path)
        require(all(pins["symbols"][key] in relocations for key in expected), f"Missing call in {obj}")

    logs = work / "logs"
    signature = (logs / "apksigner.log").read_text()
    signers = re.findall(r"^Signer #\d+ certificate SHA-256 digest: ([0-9a-f]{64})$", signature, re.M)
    require(len(signers) == 1 and signers[0] not in (old_apk["certificateSHA256"], diagnostic["priorRootCertificateSHA256"],
            prior_diagnostic["certificate"], prior_storage["certificate"], prior_renderer["certificate"])
            and "Verified using v3 scheme (APK Signature Scheme v3): true" in signature.splitlines(),
            "APK must have one fresh v3 signer")
    certificate = dict(line.split("=", 1) for line in (logs / "certificate-interval.log").read_text().splitlines())
    require(certificate["SHA256 Fingerprint"].replace(":", "").lower() == signers[0],
            "Certificate date readback used a different signer")
    clock = {key: datetime.strptime(certificate[key], "%b %d %H:%M:%S %Y %Z")
             .replace(tzinfo=timezone.utc).isoformat() for key in ("notBefore", "notAfter")}

    badging = (logs / "badging.log").read_text().splitlines()
    require(set(("minSdkVersion:'36'", "targetSdkVersion:'37'", "native-code: 'arm64-v8a'")) <= set(badging)
            and any(line.startswith("package: name='dev.fieldlog.generatedr90' ") for line in badging)
            and any(line.startswith("launchable-activity: name='dev.fieldlog.generatedr90.androidhost.PublicActivity' ")
                    for line in badging), "Unexpected APK package, activity, API level or ABI")

    delivery = packet / "delivery-android"
    host = load(delivery / "host.json")
    root_sha = digest(delivery / "Installed/roots.json")
    require(host["runtime"] == capture["androidRuntime"]
            and host["runtime"] not in (pins["previousRuntime"], pins["reviewed"]["runtime"], diagnostic["priorRootRuntime"], prior_diagnostic["runtime"], prior_storage["runtime"], prior_renderer["runtime"])
            and root_sha not in (pins["previousRootSHA256"], pins["reviewedRootSHA256"], diagnostic["priorRootTrustSHA256"], prior_diagnostic["trust"], prior_storage["trust"], prior_renderer["trust"]),
            "Delivery identity or public trust root was reused")
    new_identity = load(delivery / "Installed/identity.json")
    previous_identity = load(renderer_identity_path)
    require({key: value for key, value in new_identity.items() if key != "build"}
            == {key: value for key, value in previous_identity.items() if key != "build"},
            "Installed runtime policy, deadlines or ABI changed")
    build_changes = compare_inventory(new_identity["build"], previous_identity["build"],
            {"link_inputs_sha256", "native_fallback_sha256", "trust_roots_sha256"}, "Signed runtime build bindings")
    source["comparisons"]["priorRendererIdentityBuild"] = build_changes
    roots = load(delivery / "Installed/roots.json")
    older_roots = load(SOURCE / "reference/prior-renderer-roots.json")
    require(len(roots) == 1 and roots[0]["public_key"] != older_roots[0]["public_key"]
            and roots[0]["scope"] == host["scope"] and host["scope"] == {
                "organization": "mixer-local", "project": "fieldlog", "app": "fieldlog",
                "environment": "development", "platform": "android",
            }, "Delivery key is reused or outside the FieldLog development scope")
    guest_bytes = {}
    for variant, expected in prior_renderer["manifest"].items():
        manifest = load(delivery / f"{variant}.manifest.json")["manifest"]
        built_guest = work / f"guests/{variant}.wasm"
        packet_guest = delivery / f"{variant}.wasm"
        fresh_digest = digest(built_guest)
        fresh_size = built_guest.stat().st_size
        require(manifest == expected | {
                    "runtime": host["runtime"],
                    "created_at_unix": manifest["created_at_unix"],
                    "provenance_id": f"fieldlog-l08-android-{host['runtime'][:24]}",
                    "payload_sha256": fresh_digest,
                    "compressed_bytes": fresh_size,
                    "expanded_bytes": fresh_size,
                } and digest(packet_guest) == fresh_digest and packet_guest.stat().st_size == fresh_size,
                f"Signed policy, deadline or fresh Wasm differs for {variant}")
        guest_bytes[variant] = {"sha256": fresh_digest, "bytes": fresh_size}
    require(new_identity["capability_execution"]["turn_milliseconds"] == 50,
            "The selected-draft VM turn must retain its reviewed 50 ms limit")
    results = (logs / "verify-delivery.log").read_text().splitlines()
    batches = [results[index:index + 5] for index in range(0, len(results), 5)]
    require(len(batches) == 6 and all(len(batch) == 5 and batch[4].startswith("PASS four v3 assignments,")
                                    for batch in batches), "Missing signed delivery readback")
    assignments = []
    for sequence, variant in enumerate(("baseline", "optional", "baseline", "optional"), 1):
        path = delivery / f"sequence-{sequence}.assignment.json"
        assignment = load(path)["assignment"]
        payload = delivery / f"{variant}.wasm"
        artifact = results[sequence - 1].split()
        require(artifact == [str(sequence), variant, assignment["artifact_sha256"]]
                and all(batch[sequence - 1] == batches[0][sequence - 1] for batch in batches),
                "Verifier readback and assignment disagree")
        assignments.append({
            "sequence": sequence, "variant": variant, "releaseID": assignment["release_id"],
            "artifactSHA256": assignment["artifact_sha256"], "assignmentSHA256": digest(path),
            "payloadSHA256": digest(payload), "payloadBytes": payload.stat().st_size,
            "signedAtUnix": assignment["created_at_unix"],
        })
    host_editor = (logs / "host.log").read_text().strip()
    guest_checks = (logs / "guest-preflight.log").read_text().splitlines()
    require(host_editor.startswith("PASS ") and len(guest_checks) == 2
            and all("rc=0 status=0" in line for line in guest_checks), "Host controls missing")

    replay_installation = (packet / "host-replay-installation.txt").read_text().strip()
    replay = [json.loads(line) for line in (packet / "host-replay.jsonl").read_text().splitlines()]
    staged = [chapter for chapter in replay[:-1] if chapter["staged"]]
    require([(chapter["sequence"], chapter["variant"], chapter["payloadSHA256"])
             for chapter in staged] == [(item["sequence"], item["variant"], item["payloadSHA256"])
                                         for item in assignments]
            and all(chapter["installation"] == replay_installation for chapter in replay)
            and replay[-1]["status"] == "passed" and replay[-1]["nativeWriterCount"] == 1
            and replay[-1]["ownersRetired"] == 5 and replay[-1]["liveAllocations"] == 0
            and all(replay[-1][key] is True for key in (
                "coldRollbackReadback", "coldRepositoryReadback", "wrongDraftKeyRejected", "detachedLeaseRejected")),
            "Installed host-runtime readback did not replay this packet as one installation and writer")
    require((logs / "press-trace-host.log").read_text().startswith("PASS "),
            "Missing host diagnostic control")
    artifacts = sorted(path for path in packet.rglob("*") if path.is_file())
    checksum_file = packet / "SHA256SUMS"
    with checksum_file.open("x") as stream:
        for path in artifacts:
            checksum = capture["apkSHA256"] if path == apk else digest(path)
            stream.write(f"{checksum}  {path.relative_to(packet).as_posix()}\n")

    tools = capture["binding"]["toolchain"] | {
        "host": output("sw_vers"),
        "xcodeHost": output("env", "DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer", "xcodebuild", "-version"),
        "xcodeAndroidCrossBuild": output("env", f"DEVELOPER_DIR={XCODE}", "xcodebuild", "-version"),
        "androidNdk": "27.1.12297006", "androidBuildTools": "36.0.0",
        "rust": load(work / "android-engine/receipt.json")["rustc"],
        "jdk": output("/opt/homebrew/opt/openjdk@25/bin/javac", "-version"),
    }
    apk_facts = {key: old_apk[key] for key in (
        "package", "activity", "minApi", "targetApi", "abi", "dexSHA256", "linkedManifestSHA256",
        "buildDescriptorSHA256")}
    apk_facts.update(dexSHA256=capture["apkMembersSHA256"]["classes.dex"], sha256=capture["apkSHA256"], bytes=apk.stat().st_size,
                     jniSHA256=digest(native), nativeLibraries=len(members),
                     certificateSHA256=signers[0], v3Signature=True, apkZipAlignmentKiB=16,
                     jniElfLoadAlignments=[int(row[-1], 16) for row in loads])
    receipt = {
        "status": "private_opt_in_diagnostic_apk_ready_for_root_replay",
        "scenario": "L08 §22.2.4", "source": source, "toolchain": tools, "apk": apk_facts,
        "runtime": host["runtime"], "clock": clock,
        "delivery": {"runtime": host["runtime"], "assignments": assignments, "trustRootSHA256": root_sha,
                     "previousRuntimesRejected": [pins["reviewed"]["runtime"], pins["previousRuntime"], diagnostic["priorRootRuntime"], prior_diagnostic["runtime"], prior_storage["runtime"], prior_renderer["runtime"]],
                     "scope": host["scope"], "channel": "beta", "guests": guest_bytes,
                     "sameInstallReplay": {
                         "hostInstallation": replay_installation,
                         "freshAndroidInstallRequired": True,
                         "installedInstallation": None,
                         "sequences": [1, 2, 3, 4],
                     },
                     "signedLimits": {variant: manifest["limits"] for variant, manifest in prior_renderer["manifest"].items()},
                     "runtimeDeadlines": {"startupMs": new_identity["execution"]["startup_ms"],
                                          "capabilityTimeoutMs": new_identity["capability_execution"]["timeout_milliseconds"],
                                          "capabilityTurnMs": new_identity["capability_execution"]["turn_milliseconds"]},
                     "negativeChecks": ["wrong-channel", "foreign-development-trust-scope", "former-development-key",
                                        "legacy-runtime", "stale-sequence", "tampered-wasm"],
                     "staleSequenceRejected": True, "verifiedWith": "Pinned MixerUpdates.ReleaseVerifierV3"},
        "adapter": {"compilerSources": adapter, "definedInFinalApkElf": pins["symbols"],
                    "objectRelocationTargets": pins["relocations"],
                    "javaDeclaredAndElfExportedJni": capture["jniDeclaredAndExported"]},
        "hostChecks": {"editor": host_editor, "guestDeferredABI": guest_checks,
                        "packagedDiagnosticStages": list(markers),
                        "pressTrace": (logs / "press-trace-host.log").read_text().strip(),
                        "sameInstallReplay": replay,
                        "replaySHA256": digest(packet / "host-replay.jsonl")},
        "replayPacketChecksumSHA256": digest(checksum_file),
        "installedAndroid": "pending root-owned replay",
    }
    receipt_path = packet / "rebuild-receipt.json"
    write(receipt_path, receipt)
    print(f"{receipt['runtime']}  runtime")
    print(f"{apk_facts['sha256']}  {APK_NAME}")
    print(f"{signers[0]}  APK v3 signer certificate")
    print(f"{root_sha}  delivery trust roots")
    print(f"{digest(receipt_path)}  rebuild-receipt.json")


if __name__ == "__main__":
    main(*(Path(arg).resolve(strict=True) for arg in sys.argv[1:]))
