"""Verify and package relocatable unsigned XCTest products and their local origin."""
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
WITNESS = "export/source/capability-activation/verification/f11-native/Witness"


def package(stage, work, tools, kit):
    native = stage / "tests/integration/fieldlog-d8-f11-ios-simulator"
    replace = runpy.run_path(str(native / "prepare.py"))["checked_replace"]
    source = native / "package-kit.py"
    code = replace(source.read_text(),
        'json.loads((sealed / "assignment.json").read_bytes())["assignment"]["runtime"]',
        'json.loads((work / "final-releases/host.json").read_bytes())["runtime"]')
    module = dict(__name__="package_f11_ota")
    exec(compile(code, str(source), "exec"), module)
    metadata = module["inspect"](work, kit)
    app = kit / "Debug-iphonesimulator/F11NativeWitness.app"
    sealed = app / "SealedInput"
    assert {p.name for p in sealed.iterdir()} == {
        "bridge.json", "delivery.json", "identity.json", "roots.json", "storage-grant.json", "storage.json", "workspace.json",
    }
    assert not list(app.rglob("*.wasm"))
    shutil.copytree(tools, kit / "tools", ignore=shutil.ignore_patterns("F09Control"))
    releases = kit / "releases"
    releases.mkdir()
    for name in ("host.json", "roots.json", "prior", "successor", "rollback"):
        item = work / "final-releases" / name
        if item.is_dir():
            shutil.copytree(item, releases / name)
        else:
            shutil.copy2(item, releases / name)
    shutil.copy2(work / WITNESS / "SealedInput/delivery.json", kit / "delivery.json")
    for name in ("delivery.py", "issue.py", "configure.py"):
        shutil.copy2(HERE / name, kit / name)

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    members = kit / "MEMBERS.sha256"
    members.write_text("".join(f"{digest(file)}  {file.relative_to(kit)}\n"
                               for file in sorted(kit.rglob("*"))
                               if file.is_file() and not file.is_symlink() and file != members))
    subprocess.run(["shasum", "-a", "256", "-c", members.name], cwd=kit, check=True, stdout=subprocess.DEVNULL)
    metadata["memberManifestSHA256"] = digest(members)
    metadata["members"] = len(members.read_text().splitlines())
    return metadata


if __name__ == "__main__":
    print(json.dumps(package(*map(Path, sys.argv[1:])), indent=2))
