#!/usr/bin/env python3
"""Run the real default starter Activity against a lazy-decor window double."""

import os
from pathlib import Path
import subprocess
import tempfile


def main():
    tests = Path(__file__).resolve().parent
    activity = tests.parent / "app/src/dev/mixer/android/MixerActivity.java"
    leaves = sorted((tests / "MixerActivityHostLeaves").rglob("*.java"))
    jdk = os.environ.get("JAVA_HOME")
    javac = Path(jdk) / "bin/javac" if jdk else "javac"
    java = Path(jdk) / "bin/java" if jdk else "java"
    with tempfile.TemporaryDirectory(prefix="mixer-activity-host-") as classes:
        subprocess.run(
            [javac, "--release", "17", "-Xlint:all", "-Werror", "-proc:none",
             "-d", classes, *leaves, activity, tests / "MixerActivityHostTests.java"],
            check=True,
        )
        subprocess.run([java, "-cp", classes, "dev.mixer.android.MixerActivityHostTests"], check=True)


if __name__ == "__main__":
    main()
