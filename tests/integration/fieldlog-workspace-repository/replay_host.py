import os
from pathlib import Path
import shutil


def run_host(commands, arm, platform):
    work = commands.root
    label = f"{arm}-{platform}"
    directory = work / arm
    harness = directory / f"{platform}Replay"
    sources = harness / "Sources" / "WorkspaceReplay"
    sources.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__).with_name("WorkspaceReplay.swift"), sources / "WorkspaceReplay.swift")
    if platform == "apple":
        dependency = '.package(path: "../fieldlog")'
        products = ['.product(name: "FieldLogStorage", package: "fieldlog")',
                    '.product(name: "FieldLogModels", package: "fieldlog")']
        settings = ""
    elif platform == "export":
        dependency = '.package(path: "../App")'
        products = ['.product(name: "FieldLogStorage", package: "App")',
                    '.product(name: "FieldLogModels", package: "App")']
        settings = ', swiftSettings: [.define("ANDROID_EXPORT")]'
    else:
        raise ValueError(platform)
    (harness / "Package.swift").write_text(f"""// swift-tools-version: 6.0
    import PackageDescription
    let package = Package(
      name: "WorkspaceDiskReplay", platforms: [.macOS(.v14)],
      dependencies: [{dependency}],
      targets: [.executableTarget(name: "WorkspaceReplay",
        dependencies: [{', '.join(products)}]{settings})]
    )
    """)
    env = os.environ.copy()
    env.update(TMPDIR=str(work / "tmp"), SWIFTCI_USE_LOCAL_DEPS="1",
               SWIFTPM_MODULECACHE_OVERRIDE=str(work / "host-module-cache"),
               CLANG_MODULE_CACHE_PATH=str(work / "host-clang-cache"))
    build = directory / f"{platform}HostBuild"
    commands.run(label + "-build", harness, 100, [
        "/usr/bin/swift", "build", "--build-system", "native", "--scratch-path", str(build),
        "--cache-path", str(work / "host-cache"), "--config-path", str(work / "swift-config"),
        "--security-path", str(work / "swift-security"), "--disable-dependency-cache",
        "--disable-prefetching", "--disable-index-store", "--jobs", "6", "-v",
    ], env)
    binary = build / "debug/WorkspaceReplay"
    commands.run(label + "-disk", harness, 10, [
        str(binary), str(directory / f"{platform}Disk"),
        str(Path(__file__).with_name("fixtures")),
    ], env)
