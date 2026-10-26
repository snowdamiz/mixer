#!/usr/bin/env python3
"""Bounded proposal evidence only: SDK codec, host Java decode, synthetic AAPT2 asset.

Never imports a repository collector, starts an Android runtime, or touches products.
"""
import datetime
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
RUN = OUT / "probe-2"
JDK = pathlib.Path("/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home")
SDK = pathlib.Path("/opt/homebrew/share/android-commandlinetools")
AAPT = SDK / "build-tools/37.0.0/aapt2"
JAR = SDK / "platforms/android-37.0/android.jar"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    RUN.mkdir(exist_ok=False)
    commands = []
    source_inputs = RUN / "source-inputs"
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="owned-scratch-", dir=RUN))
    receipt = {
        "schema": 1, "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Source review plus pure host codec/decode and synthetic unsigned asset-container experiment only",
        "python": sys.version, "commands": commands,
        "native_runtime_or_capture_started": False, "generated_app_built": False,
        "public_routing_changed": False, "release_or_GA_qualified": False,
    }

    def command(argv, name, timeout=55, accepted=(0,)):
        result = subprocess.run(list(map(str, argv)), cwd=ROOT, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        output = RUN / (name + ".txt")
        output.write_text(result.stdout)
        commands.append({"argv": list(map(str, argv)), "cwd": str(ROOT),
                         "exit_code": result.returncode, "output": output.relative_to(OUT).as_posix(),
                         "output_sha256": sha(output.read_bytes())})
        if result.returncode not in accepted:
            raise RuntimeError(name + " failed")
        return result.stdout

    try:
        receipt["base_revision"] = command(["git", "rev-parse", "HEAD"], "revision").strip()
        for args, name in [(["git", "--version"], "git-version"), (["swift", "--version"], "swift-version"),
                           ([JDK / "bin/javac", "--version"], "javac-version"),
                           ([JDK / "bin/java", "--version"], "java-version"), ([AAPT, "version"], "aapt-version"),
                           ([AAPT, "link", "-h"], "aapt-link-help")]:
            command(args, name, accepted=(0, 1) if name == "aapt-link-help" else (0,))
        inputs = sorted(list(ROOT.glob("sdk/Sources/MixerCore/*.swift")) + list(ROOT.glob("sdk/Sources/MixerUI/*.swift")) + [ROOT / p for p in [
            "AGENTS.md", "mixer-product-plan.md", "cli/Package.swift", "sdk/Package.swift",
            "cli/Sources/MixerBuild/AndroidProject.swift", "cli/Sources/MixerBuild/ProjectGenerator.swift",
            "cli/Sources/MixerBuild/Configuration.swift", "cli/Sources/MixerBuild/Resources/android-build.py",
            "cli/Tests/MixerBuildTests/AndroidProjectTests.swift", "sdk/Tests/MixerUITests/AppearanceDescriptorV2Tests.swift",
            "native/android/app/src/dev/mixer/android/AppearanceDescriptorV2.java",
            "native/android/app/src/dev/mixer/android/AppearanceGeometryV2.java",
            "native/android/app/src/dev/mixer/android/InstalledAppearanceV2.java",
            "native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java",
            "native/android/app/src/dev/mixer/android/MixerActivity.java",
            "docs/android-public-appearance-routing-proposal.md", "docs/android-authored-toggle-generated-export.md",
            "verification/android-authored-toggle-generated-export/final-receipt.json",
            "verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json",
        ]])
        manifest = []
        for path in inputs:
            relative = path.relative_to(ROOT).as_posix()
            target = source_inputs / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            data = path.read_bytes()
            target.write_bytes(data)
            manifest.append({"path": relative, "bytes": len(data), "sha256": sha(data)})
        save(RUN / "source-manifest.json", manifest)
        receipt["source_manifest_sha256"] = sha((RUN / "source-manifest.json").read_bytes())
        receipt["selected_input_tree_sha256"] = sha("".join(x["path"] + "\0" + x["sha256"] + "\n" for x in manifest).encode())
        for module in ["MixerCore", "MixerUI"]:
            shutil.copytree(source_inputs / "sdk/Sources" / module, scratch / "Sources" / module)
        (scratch / "Sources/DescriptorProbe").mkdir()
        (scratch / "Package.swift").write_text('''// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "DescriptorProposalProbe", platforms: [.macOS(.v14)], targets: [
    .target(name: "MixerCore"), .target(name: "MixerUI", dependencies: ["MixerCore"]),
    .executableTarget(name: "DescriptorProbe", dependencies: ["MixerUI"])], swiftLanguageModes: [.v6])
''')
        probe = scratch / "Sources/DescriptorProbe/main.swift"
        probe.write_text('''import Foundation
import MixerUI
let value = try UIAppearanceDescriptorCodecV2.mixerDefaultV2()
guard case let .shared(theme) = value.mode, value.resources.isEmpty,
      case .systemSans = theme.typography.font else { fatalError("unexpected default") }
let bytes = try UIAppearanceDescriptorCodecV2.canonicalData(value)
guard try UIAppearanceDescriptorCodecV2.decode(bytes) == value else { fatalError("round trip") }
try bytes.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
print("default=\\(value.id) mode=shared resources=0 font=systemSans bytes=\\(bytes.count)")
''')
        shutil.copy2(scratch / "Package.swift", RUN / "probe-Package.swift")
        shutil.copy2(probe, RUN / "probe-main.swift")
        descriptor = RUN / "descriptor.json"
        command(["swift", "run", "--package-path", scratch, "--scratch-path", scratch / ".build", "-j", "2", "DescriptorProbe", descriptor], "swift-default-codec")
        data = descriptor.read_bytes()
        assert data == (source_inputs / "verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json").read_bytes()
        receipt["descriptor"] = {"bytes": len(data), "sha256": sha(data), "equals_retained_golden": True}
        javaprobe = scratch / "DescriptorProbe.java"
        javaprobe.write_text('''package dev.mixer.android;
import java.nio.file.Files;
import java.nio.file.Path;
final class DescriptorProbe {
    public static void main(String[] args) throws Exception {
        byte[] bytes = Files.readAllBytes(Path.of(args[0]));
        AppearanceDescriptorV2 value = AppearanceDescriptorV2.decode(bytes);
        if (value.mode != AppearanceDescriptorV2.Mode.shared || value.iOS != value.android ||
            value.platformSpecificReason != null || !value.resources.isEmpty() ||
            !(value.iOS.typography().font() instanceof AppearanceDescriptorV2.SystemSans))
            throw new AssertionError("unexpected default");
        byte[] noncanonical = java.util.Arrays.copyOf(bytes, bytes.length + 1);
        noncanonical[bytes.length] = ' ';
        try { AppearanceDescriptorV2.decode(noncanonical); throw new AssertionError("accepted whitespace"); }
        catch (AppearanceDescriptorV2.Failure rejected) {
            if (rejected.code != AppearanceDescriptorV2.Error.noncanonical) throw rejected;
        }
        System.out.println("hostJava=shared identicalTheme=true emptyCatalog=true systemSans=true rejectsTrailingSpace=true");
    }
}
''')
        shutil.copy2(javaprobe, RUN / "DescriptorProbe.java")
        classes = scratch / "classes"
        classes.mkdir()
        empty = scratch / "empty-sourcepath"
        empty.mkdir()
        java_inputs = [source_inputs / "native/android/app/src/dev/mixer/android" / p for p in ["AppearanceDescriptorV2.java", "AppearanceGeometryV2.java"]]
        command([JDK / "bin/javac", "--release", "17", "-Xlint:all", "-Werror", "-implicit:none", "-sourcepath", empty, "-d", classes, *java_inputs, javaprobe], "javac-pure-decoder")
        command([JDK / "bin/java", "-cp", classes, "dev.mixer.android.DescriptorProbe", descriptor], "java-pure-decoder")
        with zipfile.ZipFile(RUN / "host-classes.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(classes.rglob("*.class")):
                archive.write(path, path.relative_to(classes))
        assets = scratch / "assets/MixerAppearanceV2"
        assets.mkdir(parents=True)
        shutil.copy2(descriptor, assets / "descriptor.json")
        manifestfile = scratch / "AndroidManifest.xml"
        manifestfile.write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="dev.mixer.proposal" android:versionCode="1" android:versionName="0.1"><uses-sdk android:minSdkVersion="28" android:targetSdkVersion="37"/><application android:label="Descriptor proposal"/></manifest>\n')
        shutil.copy2(manifestfile, RUN / "probe-AndroidManifest.xml")
        apk = RUN / "asset-probe-unsigned.apk"
        command([AAPT, "link", "-I", JAR, "--manifest", manifestfile, "--min-sdk-version", "28", "--target-sdk-version", "37", "-A", assets.parent, "-o", apk], "aapt-asset-link")
        with zipfile.ZipFile(apk) as archive:
            names = archive.namelist()
            assert names.count("assets/MixerAppearanceV2/descriptor.json") == 1
            assert sorted(n for n in names if n.startswith("assets/")) == ["assets/MixerAppearanceV2/descriptor.json"]
            assert archive.read("assets/MixerAppearanceV2/descriptor.json") == data
            receipt["synthetic_apk_entries"] = {name: sha(archive.read(name)) for name in sorted(names)}
        receipt["artifacts"] = {p.name: {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in [descriptor, apk, RUN / "host-classes.zip"]}
        receipt["selected_inputs_unchanged"] = all(sha((ROOT / x["path"]).read_bytes()) == x["sha256"] for x in manifest)
        assert receipt["selected_inputs_unchanged"]
        receipt["status"] = "proposal-host-observations-passed-no-product-implementation"
    except BaseException as failure:
        receipt["status"] = "proposal-probe-failed"
        receipt["failure"] = repr(failure)
        raise
    finally:
        shutil.rmtree(scratch)
        receipt["cleanup"] = {"owned_scratch": str(scratch), "removed": not scratch.exists(),
                              "children": "All subprocess.run children returned; no background jobs started."}
        receipt["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save(RUN / "receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "descriptor": receipt["descriptor"], "cleanup": receipt["cleanup"]}, indent=2))


if __name__ == "__main__":
    main()
