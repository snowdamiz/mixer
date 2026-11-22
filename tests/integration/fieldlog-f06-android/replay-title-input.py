#!/usr/bin/env python3
"""Apply the private F06 Java delta and reproduce its Android API 36 dex."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

BASE = "7fa6b6ea813f73055c38e7d2bf8e607c75c9c384"
SOURCE = "native/android/app/src/dev/mixer/android"
FIXTURE = Path(__file__).resolve().parent
LINK_JAVA = {
    "FrameBufferEvidence.java": "2eb38eda36a828bda5bec09f2e76ab6190126541de37e8a16bbea8d481c9abf1",
    "SignedF05Activity.java": "15ddd72bd2539824a23bed625a526eb5e9cdd7837d5c213d1f6e592f01e41306",
}
SDK_SHA256 = "d9eb9da824d9e247a352f570f01e1169e725b2954bca9e283a71786c59b59f9a"
D8_SHA256 = "4097ff9c46c185c6e7214da7fe9b1befb5adeea5cc9ca349270e0249904f9240"
EXPECTED_DEX = "ae9fed4b69fb58a18ac7d6b78dd4bf55ae8496d72e2b090f70dcc91846c24dbd"
MODIFIED = {
    "AndroidUINativeSurface.java", "F06TitleInput.java", "NativeAppearanceViewsV2.java",
    "NativeEditorConnectionV2.java", "NativeOwnerV2.java", "SignedF05Activity.java",
}


def digest(path):
    with path.open("rb") as data:
        return hashlib.file_digest(data, "sha256").hexdigest()


def require_digest(path, expected):
    if digest(path) != expected:
        raise ValueError(f"SHA-256 mismatch for {path}")


def source_hashes(directory):
    return {path.name: digest(path) for path in sorted(directory.glob("*.java"))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path, help="Mixer Git checkout containing the pinned base")
    parser.add_argument("link_native", type=Path, help="exact F06 link-delivery/native directory")
    parser.add_argument("output", type=Path, help="existing directory for the dex and build receipt")
    args = parser.parse_args()
    output = args.output.resolve(strict=True)
    targets = [output / "classes.dex", output / "java-build.json"]
    if any(path.exists() for path in targets):
        raise FileExistsError("Use an output directory with no previous handoff artifacts")
    jdk = Path(os.environ.get("JAVA_HOME", "/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home"))
    sdk = Path(os.environ.get("ANDROID_HOME", "/opt/homebrew/share/android-commandlinetools"))
    android_jar = sdk / "platforms/android-36/android.jar"
    d8 = sdk / "build-tools/36.0.0/d8"
    require_digest(android_jar, SDK_SHA256)
    require_digest(d8.parent / "lib/d8.jar", D8_SHA256)
    deadline = time.monotonic() + 180

    with tempfile.TemporaryDirectory(prefix=".f06-java.", dir=output) as scratch_path:
        scratch = Path(scratch_path)
        projection = scratch / "native"
        tmp = scratch / "tmp"
        classes = scratch / "classes"
        controls = scratch / "controls"
        dex = scratch / "dex"
        for directory in (projection, tmp, classes, controls, dex):
            directory.mkdir()
        env = dict(os.environ, JAVA_HOME=str(jdk), TMPDIR=str(tmp))
        def run(*args, cwd=None):
            return subprocess.check_output(args, cwd=cwd, env=env, stderr=None,
                                           timeout=max(0.1, deadline - time.monotonic()))

        def git(*parameters):
            return run("git", "-C", args.repo, *parameters)

        def javac(directory, paths):
            run(jdk / "bin/javac", "-J-Xmx256m", f"-J-Djava.io.tmpdir={tmp}",
                "--release", "17", "-proc:none", "-cp", android_jar, "-d", directory, *paths)

        java_version = run(jdk / "bin/javac", "-version").decode().strip()
        if java_version != "javac 25.0.4.1":
            raise ValueError(f"Unexpected compiler: {java_version}")
        d8_version = run(d8, "-JXmx384m", f"-JDjava.io.tmpdir={tmp}", "--version").decode().strip()
        for entry in git("ls-tree", "-r", "--name-only", BASE, "--", SOURCE).decode().splitlines():
            if entry.endswith(".java"):
                (projection / Path(entry).name).write_bytes(git("show", f"{BASE}:{entry}"))
        for name, expected in LINK_JAVA.items():
            path = args.link_native / name
            require_digest(path, expected)
            shutil.copyfile(path, projection / name)
        before = source_hashes(projection)
        javac(classes, sorted(projection.glob("*.java")))
        shutil.rmtree(classes)
        classes.mkdir()
        patch = scratch / "f06-private-title-input.patch"
        patch.write_bytes(base64.b64decode((FIXTURE / "f06-private-title-input.patch.b64").read_bytes()))
        require_digest(patch, "17a554984a816b182026e52712af7b25963dbe804e0deebc45a551bb57c235a5")
        run("git", "apply", "--check", patch, cwd=scratch)
        run("git", "apply", patch, cwd=scratch)
        after = source_hashes(projection)
        if {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)} != MODIFIED:
            raise ValueError("Private patch changed an unexpected source")
        javac(classes, sorted(projection.glob("*.java")))
        class_jar = scratch / "classes.jar"
        run(jdk / "bin/jar", "--create", "--file", class_jar, "--date=2000-01-01T00:00:00Z",
            "-C", classes, ".")
        run(d8, "-JXmx384m", f"-JDjava.io.tmpdir={tmp}", "--min-api", "36", "--lib",
            android_jar, "--output", dex, class_jar)
        require_digest(dex / "classes.dex", EXPECTED_DEX)

        checks = FIXTURE / "title-input-controls"
        leaves = [checks / "android/view/KeyEvent.java", checks / "TitleInputControl.java"]
        candidate = [projection / f"{name}.java" for name in
                     ("F06TitleInput", "NativeEditorConnectionV2", "UiPacket", "Json", "AndroidUIProfile")]
        javac(controls, leaves + candidate)
        results = run(jdk / "bin/java", "-Xmx128m", f"-Djava.io.tmpdir={tmp}", "-cp",
                      f"{controls}{os.pathsep}{android_jar}", "dev.mixer.android.TitleInputControl")
        scratch_bytes = sum(path.stat().st_size for path in scratch.rglob("*") if path.is_file())
        if scratch_bytes >= 1024**3:
            raise ValueError("Scratch exceeded 1 GiB")
        dex_bytes = (dex / "classes.dex").read_bytes()
        receipt = {
            "base": BASE,
            "fixtureJavaSHA256": LINK_JAVA,
            "overlaySHA256": digest(patch),
            "beforeJavaSHA256": before,
            "afterJavaSHA256": after,
            "javac": java_version,
            "d8": d8_version,
            "androidJarSHA256": SDK_SHA256,
            "d8JarSHA256": D8_SHA256,
            "dexSHA256": EXPECTED_DEX,
            "dexBytes": len(dex_bytes),
            "controls": results.decode().splitlines(),
            "controlSourceSHA256": {path.name: digest(path) for path in leaves},
            "scratchBytesBeforeCleanup": scratch_bytes,
        }
    if scratch.exists():
        raise RuntimeError("Owned build scratch remains")
    receipt["buildScratchRemoved"] = True
    targets[0].write_bytes(dex_bytes)
    targets[1].write_text(json.dumps(receipt, indent=2) + "\n")
    print(results.decode(), end="")
    print(f"PASS repeatable classes.dex {EXPECTED_DEX} with owned scratch removed")


if __name__ == "__main__":
    main()
