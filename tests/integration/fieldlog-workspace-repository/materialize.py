import hashlib
import io
import json
from pathlib import Path
import runpy
import shutil
import subprocess as sp
import sys
import tarfile

work = Path(sys.argv[1]).resolve()
arm, tree = sys.argv[2:]
root = work / arm
root.mkdir()
archive = sp.check_output(["git", "-C", work / "fieldlog", "archive", tree])
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    tar.extractall(root / "fieldlog", filter="data")

(root / "mixer").symlink_to(work / "mixer", target_is_directory=True)
fieldlog = root / "fieldlog"
export = fieldlog / "Integrations/GeneratedReport"
app = root / "App"
sdk = app / "Generated/MixerSDK"
shutil.copytree(work / "mixer/sdk", sdk)
recipe = runpy.run_path(str(export / "scripts/build-android.py"))
files, modules = recipe["app_inputs"]()
(app / "Platforms/Android/Tests/AppAndroidTests").mkdir(parents=True)
recipe["install_app_inputs"](app, files, modules)
for package in (fieldlog, fieldlog / "ios/FieldLog.xcodeproj/project.xcworkspace/xcshareddata/swiftpm",
                app / "Platforms/Android"):
    (package / "Package.resolved").unlink(missing_ok=True)

relative = Path("Sources/FieldLogStorage/WorkspaceRepository.swift")
installed = app / relative
assert installed.read_bytes() == (export / relative).read_bytes()
assert (app / "Package.swift").read_bytes() == (export / "Platforms/Android/ApplicationPackage.swift").read_bytes()
assert (app / "Platforms/Android/Package.swift").read_bytes() == (export / "Platforms/Android/Package.swift").read_bytes()
if arm != "baseline":
    assert installed.read_bytes() == (fieldlog / relative).read_bytes()
for path in (fieldlog / relative, export / relative, installed, fieldlog / "Package.swift",
             export / "Package.swift", app / "Package.swift", app / "Platforms/Android/Package.swift"):
    print(path.relative_to(root), hashlib.sha256(path.read_bytes()).hexdigest())
