"""Project the existing calculation fixture into a disposable task-reorder build."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROW = Path(__file__).resolve().parent
CALC = ROW.parent / "fieldlog-task-calculation"
ADAPTER = "app/src/dev/mixer/android/NativeAppearanceViewsV2.java"
ADAPTER_SHA = "34feafa32dcf94f5fb235e01b7f9515704e50664f39508ead18aaad35d009f65"
INPUT_SOURCE = "capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIAndroidResources.swift"
INPUT_SOURCE_SHA = "29cdbf9eddffa5ac333c44637151e1bf74e39850cffbb4aff051619282754e3d"
FIELDLOG_ROW_TREE = "8b485333d1caa832748944cf25fe9726588b21cb"


def git(work, *args):
    return subprocess.check_output(["git", "-C", work, *args], text=True, timeout=30).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    work = Path(sys.argv[1]).resolve(strict=True)
    fieldlog = work / "fieldlog"
    recipe = work / "recipe"
    generated = fieldlog / "Integrations/GeneratedReport/Platforms/Android"
    adapter = work / "mixer/native/android" / ADAPTER
    if sha(adapter) != ADAPTER_SHA or sha(work / "mixer" / INPUT_SOURCE) != INPUT_SOURCE_SHA:
        raise SystemExit("Pinned platform appearance or native input route differs")
    git(fieldlog, "apply", "--index", "--whitespace=error", str(ROW / "fieldlog-row-composition.patch"))
    shutil.copyfile(ROW / "CalculationFixture.swift", fieldlog / "Integrations/InstalledGuest/CalculationFixture.swift")
    shutil.copyfile(ROW / "CalculationFixture.java",
                    generated / "Java/dev/fieldlog/generatedr90/androidhost/CalculationFixture.java")
    git(fieldlog, "add", "--update", "Integrations")
    if git(fieldlog, "write-tree") != FIELDLOG_ROW_TREE:
        raise SystemExit("Projected FieldLog task-reorder tree differs")

    shutil.copytree(CALC / "android-packaging", recipe)
    git(recipe, "apply", "--whitespace=error", str(ROW / "row-recipe.patch"))
    shutil.copyfile(ROW / "Probe.swift", recipe / "Probe.swift")
    pins_file = recipe / "java-adapter-pins.json"
    pins = json.loads(pins_file.read_bytes())
    pins[ADAPTER] = {"bytes": adapter.stat().st_size, "sha256": ADAPTER_SHA}
    pins_file.write_text(json.dumps(pins, indent=2) + "\n")


if __name__ == "__main__":
    main()
