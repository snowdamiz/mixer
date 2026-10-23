#!/usr/bin/env python3
"""Build/capture only the named dedicated Simulator; never discovers phones."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
SIMULATOR = "D55AD884-6D5A-4403-9D16-A0FEE48A29C5"
BUNDLE = "dev.mixer.appearancereference"
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)
COMMANDS = []


def command(name, arguments):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    path = LOGS / (name + ".log")
    with path.open("w") as stream:
        result = subprocess.run(arguments, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    COMMANDS.append(dict(name=name, argv=arguments, cwd=str(ROOT), startedUTC=started,
        finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        exitCode=result.returncode, output=str(path.relative_to(ROOT))))
    (ROOT / "commands.json").write_text(json.dumps(COMMANDS, indent=2) + "\n")
    if result.returncode:
        raise RuntimeError(f"{name} failed; see {path}")
    return path.read_text()


def sim(name, *arguments):
    return command(name, ["xcrun", "simctl", *arguments])


def files_under(path):
    return [{"path": str(p.relative_to(path)), "bytes": p.stat().st_size,
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in sorted(path.rglob("*")) if p.is_file()]


lock = json.loads((ROOT / "input-lock.json").read_text())
for entry in lock["sourceFiles"]:
    assert hashlib.sha256((ROOT / "frozen" / entry["path"]).read_bytes()).hexdigest() == entry["sha256"], entry["path"]
command("prepare", ["python3", str(ROOT / "scripts/prepare.py")])
command("xcode-version", ["xcodebuild", "-version"])
command("swift-version", ["xcrun", "swift", "--version"])
command("sdk-version", ["xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"])
command("sdk-path", ["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"])
command("host-version", ["sw_vers"])
devices = json.loads(sim("simulator-inventory", "list", "devices", "available", "--json"))
selected = [(runtime, d) for runtime, ds in devices["devices"].items() for d in ds if d["udid"] == SIMULATOR]
assert len(selected) == 1 and selected[0][1]["name"] == "MixerAppearanceReference"
runtime, device = selected[0]
runtimes = json.loads(sim("runtime-inventory", "list", "runtimes", "--json"))
runtime_details = [{k: r.get(k) for k in ["identifier", "name", "version", "buildversion", "isAvailable"]}
    for r in runtimes["runtimes"] if r["identifier"] == runtime][0]
(ROOT / "simulator.json").write_text(json.dumps(dict(udid=SIMULATOR, device=device,
    runtime=runtime_details, creation=dict(argv=["xcrun", "simctl", "create", "MixerAppearanceReference",
    "com.apple.CoreSimulator.SimDeviceType.iPhone-18-Pro", "com.apple.CoreSimulator.SimRuntime.iOS-27-0"],
    exitCode=0, output=SIMULATOR)), indent=2) + "\n")
if device["state"] != "Booted":
    sim("boot", "boot", SIMULATOR)
sim("bootstatus", "bootstatus", SIMULATOR, "-b")
sim("status-bar", "status_bar", SIMULATOR, "override", "--time", "9:41", "--dataNetwork", "wifi",
    "--wifiMode", "active", "--wifiBars", "3", "--cellularMode", "active", "--cellularBars", "4",
    "--batteryState", "charged", "--batteryLevel", "100")
sim("increase-contrast", "ui", SIMULATOR, "increase_contrast", "disabled")
command("build", ["xcodebuild", "-project", str(ROOT / "harness/MixerAppearanceReference.xcodeproj"),
    "-scheme", "MixerAppearanceReference", "-configuration", "Debug", "-sdk", "iphonesimulator",
    "-destination", "platform=iOS Simulator,id=" + SIMULATOR, "-derivedDataPath", str(ROOT / "build"),
    "CODE_SIGNING_ALLOWED=NO", "build"])
app = ROOT / "build/Build/Products/Debug-iphonesimulator/MixerAppearanceReference.app"
(ROOT / "built-app-manifest.json").write_text(json.dumps(dict(files=files_under(app)), indent=2) + "\n")
sim("install", "install", SIMULATOR, str(app))
data_container = Path(sim("data-container", "get_app_container", SIMULATOR, BUNDLE, "data").strip())
captures = []
for fixture, size, rtl in [("typography", "large", False), ("controls", "large", False),
        ("layouts", "large", False), ("rtl-large", "accessibility-medium", True)]:
    for appearance in ["light", "dark"]:
        name = fixture + "-" + appearance
        folder = ROOT / "captures" / name
        folder.mkdir(parents=True, exist_ok=True)
        sim(name + "-appearance-set", "ui", SIMULATOR, "appearance", appearance)
        sim(name + "-size-set", "ui", SIMULATOR, "content_size", size)
        sim(name + "-appearance-observed", "ui", SIMULATOR, "appearance")
        sim(name + "-size-observed", "ui", SIMULATOR, "content_size")
        for old in ["environment.json", "rendered-document.json", "fixture-validation.json"]:
            (data_container / "Documents" / old).unlink(missing_ok=True)
        arguments = ["launch", "--terminate-running-process", SIMULATOR, BUNDLE, "--fixture", fixture]
        if rtl:
            arguments.append("--rtl")
        sim(name + "-launch", *arguments)
        deadline = time.monotonic() + 20
        while not (data_container / "Documents/environment.json").exists():
            if time.monotonic() > deadline:
                raise RuntimeError(f"No native environment receipt for {name}")
            time.sleep(0.25)
        time.sleep(2)
        for file in ["environment.json", "rendered-document.json", "fixture-validation.json"]:
            shutil.copy2(data_container / "Documents" / file, folder / file)
        native = json.loads((folder / "environment.json").read_text())
        assert native["fixture"] == fixture and native["swiftUIColorScheme"] == appearance
        assert native["swiftUILayoutDirection"] == ("rightToLeft" if rtl else "leftToRight")
        assert (folder / "rendered-document.json").read_bytes() == (ROOT / "harness/Fixtures" / (fixture + ".json")).read_bytes()
        sim(name + "-screenshot", "io", SIMULATOR, "screenshot", "--type=png", "--mask=black", str(folder / "screenshot.png"))
        captures.append(dict(name=name, fixture=fixture, requestedAppearance=appearance,
            requestedContentSize=size, requestedDirection="rightToLeft" if rtl else "leftToRight",
            files=files_under(folder)))
(ROOT / "capture-manifest.json").write_text(json.dumps(dict(captures=captures), indent=2) + "\n")
print("Built unchanged frozen renderer and recorded eight Simulator reference captures.")
