import os


def run_tests(commands, arm, platform):
    work = commands.root
    root = work / arm
    label = arm + "-" + platform + "-existing-tests"
    build = root / (platform + "Existing")
    workspace = root / (platform + "ExistingWorkspace")
    workspace.mkdir()
    env = os.environ.copy()
    env.update(TMPDIR=str(work / "tmp"), SWIFTCI_USE_LOCAL_DEPS="1",
               FIELDLOG_WORKSPACE=str(workspace),
               SWIFTPM_MODULECACHE_OVERRIDE=str(work / "host-module-cache"),
               CLANG_MODULE_CACHE_PATH=str(work / "host-clang-cache"))
    if platform == "apple":
        package = root / "fieldlog"
        target = ("taskPresentationRoutesRealRepositorySaveAndFinishesNavigationAfterDurability"
                  "|commitFaultsReopenPreviousOrCompleteNextState"
                  "|textAutosaveCannotEraseAConcurrentlyImportedPhoto"
                  "|photoReferencesArePrivateBoundedAndDurable")
    else:
        assert platform == "android"
        package = root / "App/Platforms/Android"
        target = "PhotoSelectionTests|testR109OriginalConditionsAndIndependentControls"
    commands.run(label, root, 110, [
        "/usr/bin/swift", "test", "--package-path", str(package),
        "--build-system", "native", "--scratch-path", str(build),
        "--cache-path", str(work / "host-cache"), "--config-path", str(work / "swift-config"),
        "--security-path", str(work / "swift-security"), "--disable-dependency-cache",
        "--disable-prefetching", "--disable-index-store", "--jobs", "5", "--filter", target,
    ], env)
