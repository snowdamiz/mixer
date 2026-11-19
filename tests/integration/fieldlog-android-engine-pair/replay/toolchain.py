"""Admit the build tools and pass their exact paths to the recipe phase."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

GO_VERSION = b"go version go1.27.1 darwin/arm64"
SWIFT_PINS = {
    "swift-frontend": "1ed6c28434801b1abb053e283cbc7e16d8e73ff12deb2ae3a539790afafbb3f5",
    "swift-driver": "3d13e20b1504d7d30038fcd2201b9d0a8ead5c09eea752a5da223453b3ae0c6f",
    "swift-package": "b8771765038b1a9d5313c09bbaa123675529f456547920bbb2b7c61714d09a4c",
}
SDK_PINS = {
    "info.json": "e72a978739b28a8902fe2b69cd6f57bb72bf343c98ab1486b02ac36eea5a72dc",
    "swift-android/swift-sdk.json": "e81f3f2142bce0a795cdec567ad24434db3a7b02c288eb2eef2041d2066111dc",
    "swift-android/swift-toolset.json": "0f9e3a784a4e60bf4c816460dae0ed64e0a723167af111fc05bac8a010b0e065",
}


def verify(root, pins):
    for name, expected in pins.items():
        path = root / name
        if path.resolve(strict=True) != path:
            raise ValueError(f"toolchain path redirected: {path}")
        with path.open("rb") as stream:
            observed = hashlib.file_digest(stream, "sha256").hexdigest()
        if observed != expected:
            raise ValueError(f"toolchain digest differs for {path}: {observed}")


def build_env(scratch):
    # Use the same Go settings for admission and the service and signer builds.
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("GO", "CGO_", "TESTGO_")) and key != "TEST_TELEMETRY_DIR"}
    env.pop("SWIFTPM_CUSTOM_BIN_DIR", None)
    env.update(
        GOENV="off",
        GOTOOLCHAIN="local",
        GOWORK="off",
        GOOS="darwin",
        GOARCH="arm64",
        GOARM64="v8.0",
        CGO_ENABLED="0",
        GOPATH=str(scratch / "go"),
        GOCACHE=str(scratch / "go-cache"),
        GOMODCACHE=str(scratch / "go-mod"),
    )
    go = shutil.which("go", path=env.get("PATH"))
    if go is None:
        raise ValueError("Go 1.27.1 is required")
    go = Path(go).resolve(strict=True)

    # Even a Go version query can start telemetry on this toolchain.
    go_home = Path(tempfile.mkdtemp(prefix="go-home.", dir=scratch))
    telemetry = go_home / "Library/Application Support/go/telemetry"
    telemetry.mkdir(parents=True)
    (telemetry / "mode").write_text("off\n", encoding="ascii")
    go_env = env | {"HOME": str(go_home)}
    observed = json.loads(subprocess.check_output(
        [go, "env", "-json", "GOTELEMETRY", "GOTELEMETRYDIR"], env=go_env, timeout=10))
    if observed != {"GOTELEMETRY": "off", "GOTELEMETRYDIR": str(telemetry)}:
        raise ValueError(f"Go telemetry is not disabled in {telemetry}: {observed}")

    version = subprocess.check_output([go, "version"], env=go_env, timeout=10).strip()
    if version != GO_VERSION:
        raise ValueError(f"Go toolchain differs at {go}: {version.decode(errors='replace')}")

    compiler = subprocess.check_output([go, "tool", "compile", "-V=full"], env=go_env, timeout=10).strip()
    if compiler != b"compile version go1.27.1":
        raise ValueError(f"Go compiler differs for {go}: {compiler.decode(errors='replace')}")

    home = Path.home()
    swift = (home / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin").resolve(strict=True)
    verify(swift, SWIFT_PINS)
    for name, target in (("swift", "swift-driver"), ("swiftc", "swift-driver"), ("swift-build", "swift-package")):
        if (swift / name).resolve(strict=True) != swift / target:
            raise ValueError(f"Swift tool redirected: {swift / name}")

    bundle = (home / ".swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle").resolve(strict=True)
    verify(bundle, SDK_PINS)
    sdk = bundle / "swift-android"
    registry = scratch / "swift-sdks"
    registry.mkdir(exist_ok=True)
    link = registry / bundle.name
    try:
        link.symlink_to(bundle, target_is_directory=True)
    except FileExistsError:
        pass
    if (registry.is_symlink() or set(registry.iterdir()) != {link}
            or not link.is_symlink() or link.resolve(strict=True) != bundle):
        raise ValueError(f"unexpected Swift SDK search directory: {registry}")

    env.update(
        MIXER_RECIPE_GO=str(go),
        MIXER_RECIPE_GO_HOME=str(go_home),
        SWIFT_EXEC=str(swift / "swiftc"),
        SWIFT_EXEC_MANIFEST=str(swift / "swiftc"),
        SWIFT_DRIVER_SWIFT_FRONTEND_EXEC=str(swift / "swift-frontend"),
        MIXER_RECIPE_SWIFT_ANDROID_SDK=str(sdk),
        MIXER_RECIPE_SWIFT_SDKS_PATH=str(registry),
    )
    return env


if __name__ == "__main__":
    work, command, *args = sys.argv[1:]
    os.execve(command, [command, *args], build_env(Path(work).resolve(strict=True) / "scratch"))
