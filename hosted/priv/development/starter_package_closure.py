"""The operator-provisioned v38 starter's admitted local compiler inputs."""
import hashlib
import json

VERSION = "v38-local-v1"
KEY = "starter_package_closure"
SDK_PREFIX = "Generated/MixerSDK/"
SDK_SHA256 = "ee03d620f05de3ecf3bb1242ab14da76082ca9b7d26ddcfbf72f8c82c967d50b"
APP_SHA256 = "9a3675d963109cb0d3e67b4230c1d2013a16a135263178d1c09a3fa7c6b38672"


def tree_digest(files):
    return hashlib.sha256("".join(f"{name}\0{sha}\n" for name, sha in sorted(files.items())).encode()).hexdigest()


def check_starter_inputs(files, lock_bytes):
    sdk = {name[len(SDK_PREFIX):]: sha for name, sha in files.items() if name.startswith(SDK_PREFIX)}
    app = {name: sha for name, sha in files.items() if name != "mixer.lock" and not name.startswith(SDK_PREFIX)}
    # Full content pins cover every executable manifest, alternate manifest,
    # Xcode package reference, and vendored source without evaluating Swift.
    if (tree_digest(sdk) != SDK_SHA256 or tree_digest(app) != APP_SHA256
            or hashlib.sha256(lock_bytes).hexdigest() != files.get("mixer.lock")
            or json.loads(lock_bytes).get("sdkDigest") != SDK_SHA256):
        raise ValueError("starter inputs are outside the admitted local package closure")
