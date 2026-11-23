#!/usr/bin/env python3
"""Run the stock AppleProject generator on the pinned FieldLog projection."""
import argparse
import json
from pathlib import Path
import shlex
import shutil

from prepare import HERE, PROJECT_SHA, digest, private_env, require, roster, run, tree, write

WORKSPACE = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<Workspace version="1.0"><FileRef location="self:"></FileRef></Workspace>\n')


def generate(work):
    app = work / "RegisteredFieldLog"
    cli = Path((work / "cli-path").read_text().strip())
    env = private_env(work)
    # SwiftPM keeps target object files beside the modules in the Xcode 27.2 layout.
    # Use the same package graph as the stock CLI for this generator entry point.
    bin_path = cli.parent
    metadata = work / "cli-build"
    links = list(metadata.rglob("mixer.LinkFileList"))
    require(len(links) == 1, "stock SwiftPM mixer link file list missing")
    objects = [p for p in shlex.split(links[0].read_text()) if "/MixerCLI.build/" not in p]
    require(objects and all(Path(p).is_relative_to(metadata) and Path(p).is_file() for p in objects),
            "unexpected SwiftPM object path")
    modulemaps = sorted(metadata.rglob("GeneratedModuleMaps/*.modulemap"))
    flags = [item for path in modulemaps for item in ("-Xcc", f"-fmodule-map-file={path}")]
    generator = work / "generate-project"
    run(["/usr/bin/xcrun", "swiftc", "-I", bin_path, "-I", work / "cli-source/cli/Sources/MixerProcessIO/include", *flags, HERE / "generate.swift", *objects, "-o", generator],
        env, cwd=work, timeout=90)
    run([generator, app], env, cwd=work)
    project = app / "Platforms/iOS/FieldLog.xcodeproj"
    require(digest(project / "project.pbxproj") == PROJECT_SHA, "generated Xcode project differs")
    workspace = project / "project.xcworkspace"
    workspace.mkdir(exist_ok=True)
    path = workspace / "contents.xcworkspacedata"
    if path.exists():
        require(path.read_text() == WORKSPACE, "generated workspace descriptor differs")
    else:
        path.write_text(WORKSPACE)
    fallback = json.loads((HERE / "fixture/fallback.json").read_bytes())
    require(all(digest(app / name) == value for name, value in fallback.items()),
            "native fallback differs from the accepted source")
    shutil.rmtree(app / ".mixer")  # Contains only the generated plist. Stock worker regenerates it.
    files = roster(app)
    write(work / "generation.json", {"generatorProjectSHA256": PROJECT_SHA, "sourceSHA256": tree(files),
                                     "fileCount": len(files), "fallbackFilesSHA256": fallback,
                                     "lockSHA256": files["mixer.lock"], "cliSHA256": digest(cli)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    generate(parser.parse_args().work.resolve(strict=True))
