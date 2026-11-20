#!/usr/bin/env python3
"""Seal one loopback-only FieldLog Android APK and two ordinary v3 releases."""
import argparse
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import sys
import tempfile
import zipfile

from replay import PAIR, PINS, RECIPE, REPO, inventory, output, require, sha, write

LOCK = json.loads((RECIPE / "package-pins.json").read_bytes())
GIT = ("/usr/bin/git", "-C", REPO)
GIT_ENV = {"GIT_NO_LAZY_FETCH": "1", "GIT_NO_REPLACE_OBJECTS": "1", "GIT_OPTIONAL_LOCKS": "0",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
SCOPE = {"organization": "mixer-local", "project": "fieldlog", "app": "fieldlog",
         "environment": "development", "platform": "android"}
CHANNEL = "beta"
ROUTE = "/v3/orgs/mixer-local/projects/fieldlog"
LABELS = ("baseline", "reviewed")
ASSETS = "assets/ChecklistRelease/"
CHANGES = {"identity.json", "roots.json", "port.txt"}
INSTALLED = CHANGES | {"bridge.json", "storage-grant.json", "storage.json"}
INSTALLATION = "a4d88fe1-13fd-4b82-bc7a-3376c2fa00ea"
VERSION = 24102
BUDGET = 600 * 1024 ** 2


def load(path):
    return json.loads(path.read_bytes())


def import_pair(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pinned(path, digest):
    require(path.is_file() and not path.is_symlink() and sha(path) == digest, f"input digest mismatch: {path}")
    return path


def git(*args):
    env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    return output(*GIT, *args, env=env | GIT_ENV)


def input_plan(base, guests):
    source = LOCK["guestSourceCommit"]
    relative_pair = PAIR.relative_to(REPO)
    require(git("rev-parse", f"{source}:{relative_pair}") == PINS["maintainedPairTree"], "pair tree mismatch")
    require(not git("diff", "--name-only", source, "--", relative_pair, RECIPE / "pins.json"),
            "maintained pair or localized host pins differ")
    service = LOCK["serviceCommit"]
    require(git("rev-parse", f"{service}:services/protocol") == LOCK["protocolTree"], "signing protocol drift")

    binding_path = pinned(guests / "binding.json", LOCK["guestBindingSHA256"])
    binding = load(binding_path)
    require(all(binding[key] == PINS[key] for key in
                ("consumer", "selectedGuestSHA256", "localizedGuestSHA256", "payloads")), "guest binding differs")
    manifests = {}
    template = load(PAIR / "inputs/manifest.json")
    require(template["scope"] == SCOPE and template["protocol"] == template["schema"] == 3, "manifest scope differs")
    for label in LABELS:
        pin = PINS["payloads"][label]
        guest = pinned(guests / f"{label}.wasm", pin["sha256"])
        require(guest.stat().st_size == pin["bytes"], f"unexpected guest length: {label}")
        manifests[label] = template | {
            "created_at_unix": 0, "key_id": "unissued", "runtime": "0" * 64,
            "source_commit": source, "release_id": f"fieldlog-localized-{label}",
            "payload_sha256": pin["sha256"], "compressed_bytes": pin["bytes"], "expanded_bytes": pin["bytes"],
            "provenance_id": "fieldlog-localized-" + PINS["localizedGuestSHA256"],
        }

    for name in ("new", "tools"):
        require((base / name).is_dir() and not (base / name).is_symlink(), f"redirected handoff directory: {name}")
    for name, digest in LOCK["base"].items():
        pinned(base / name, digest)
    receipt = load(base / "package-result.json")
    case = receipt["cases"]["new"]
    host = load(base / "new/host.json")
    installed = load(base / "new/installed.sha256.json")
    require(receipt["status"] == "apk-pair-verified" and receipt["fieldLog"] == {
        "baseRevision": PINS["fieldLogRevision"], "mixerHostSourceBasis": PINS["androidHostRevision"],
        "sourceInventorySHA256": PINS["consumer"]["sha256"],
    }, "base consumer provenance differs")
    engine = case["engine"]
    require(all(engine[key] == pin for key, pin in load(PAIR / "inputs/engines.json")["new"].items()),
            "current engine provenance differs")
    require(case["versionCode"] == VERSION and case["host"] == host and host["scope"] == SCOPE and
            case["apk"]["sha256"] == LOCK["base"]["new/FieldLog.apk"] and set(installed) == INSTALLED,
            "base package or identity provenance differs")

    apk = base / "new/FieldLog.apk"
    with zipfile.ZipFile(apk) as image:
        members = image.namelist()
        signatures = {"META-INF/FIELDLOG.SF", "META-INF/FIELDLOG.EC", "META-INF/MANIFEST.MF"}
        require({name for name in members if name.startswith("META-INF/")} == signatures and
                len(set(members)) == len(members) and image.testzip() is None, "unexpected APK inventory or CRC")
        payload = set(members) - signatures
        require(payload == case["apk"]["membersSHA256"].keys() and
                all(image.getinfo(name).compress_type == zipfile.ZIP_STORED for name in payload),
                "base payload differs from the maintained inventory")
        assets = {name: image.read(ASSETS + name) for name in installed}
        digests = {name: hashlib.sha256(data).hexdigest() for name, data in assets.items()}
        require(digests == installed, "base installed assets differ")
        for name, pin in LOCK["baseMembers"].items():
            with image.open(name) as stream:
                require(hashlib.file_digest(stream, "sha256").hexdigest() == case["apk"]["membersSHA256"][name] == pin,
                        f"base member differs: {name}")
    descriptor = json.loads(assets["identity.json"])
    build, vm = descriptor["build"], descriptor["engine"]
    require(build["trust_roots_sha256"] == installed["roots.json"] and
            build["link_inputs_sha256"] == LOCK["linkInputsSHA256"] and
            (vm["version"], vm["source_sha256"], vm["artifact_sha256"]) ==
            (engine["revision"], engine["sourceSHA256"], engine["archiveSHA256"]),
            "installed descriptor differs from current engine provenance")

    return {
        "source": LOCK | {"pairTree": PINS["maintainedPairTree"], "guestBinding": binding},
        "manifests": manifests, "host": host, "assets": assets, "case": case,
        "routing": {
            "listenHost": "127.0.0.1", "scope": SCOPE, "protocol": 3, "channel": CHANNEL,
            "upload": {"method": "PUT", "path": ROUTE + "/artifacts/{digest}"},
            "validate": {"method": "POST", "path": ROUTE + "/releases/validate"},
            "publish": {"method": "POST", "path": ROUTE + "/channels/beta/publish"},
            "offer": {"method": "GET", "path": "/v3/updates"},
            "releases": {label: {"sequence": index + 1, "cursor": index}
                         for index, label in enumerate(LABELS)},
        },
    }


def build_signer(pair, scratch):
    # Only the pinned protocol sources are needed. Go builds offline in the maintained private home/cache.
    rev = LOCK["serviceCommit"]
    path = "services/protocol"
    module = scratch / "signer"
    (module / "protocol").mkdir(parents=True)
    entries = git("ls-tree", "--name-only", f"{rev}:{path}").splitlines()
    for source in ("services/go.mod", *(f"{path}/{name}" for name in entries
                                          if name.endswith(".go") and not name.endswith("_test.go"))):
        data = pair.command(*GIT, "show", f"{rev}:{source}", env=pair.ENV | GIT_ENV)
        (module / source.removeprefix("services/")).write_bytes(data)
    signer = scratch / "sign-localized"
    pair.command(pair.GO, "-C", module, "build", "-p", "2", "-mod=readonly", "-trimpath", "-o", signer,
                 RECIPE / "sign-localized.go", timeout=100, env=pair.ENV | {
                     "HOME": os.environ["MIXER_RECIPE_GO_HOME"], "GOPROXY": "off", "GOSUMDB": "off",
                 })
    return signer


def workspace_bytes(work):
    return sum(path.lstat().st_blocks * 512 for path in work.rglob("*") if path.is_file() and not path.is_symlink())


def repackage(pair, base, output_apk, assets, original_case, host, sizes):
    # Inputs are ZIP_STORED. Stream each member so the JNI and SDK libraries never expand in RAM.
    source = base / "new/FieldLog.apk"
    scratch = pair.SCRATCH
    unsigned, aligned = scratch / "unsigned.apk", scratch / "aligned.apk"
    sizes["beforeAPK"] = workspace_bytes(pair.CAMPAIGN)
    require(sizes["beforeAPK"] + 3 * source.stat().st_size + 16 * 1024 ** 2 < BUDGET,
            "insufficient scratch budget for unsigned, aligned and signed APKs")
    with zipfile.ZipFile(source) as image, zipfile.ZipFile(unsigned, "x") as target:
        for member in image.infolist():
            if member.filename.startswith("META-INF/"):
                continue
            name = member.filename.removeprefix(ASSETS)
            if member.filename == ASSETS + name and name in CHANGES:
                target.writestr(member, assets[name])
            else:
                with image.open(member) as src, target.open(deepcopy(member), "w") as dst:
                    shutil.copyfileobj(src, dst, length=1024 * 1024)
    pair.command(pair.TOOLS / "zipalign", "-P", "16", "-f", "4", unsigned, aligned, timeout=30)

    key = scratch / "development.p12"
    password = "FIELDLOG_LOCAL_APK_PASSWORD"
    env = pair.ENV | {password: secrets.token_hex(24)}
    pair.command(pair.JAVA / "bin/keytool", "-genkeypair", "-storetype", "PKCS12", "-keystore", key,
                 "-alias", "fieldlog-localized", "-storepass:env", password, "-keypass:env", password,
                 "-keyalg", "EC", "-groupname", "secp256r1", "-validity", "30",
                 "-dname", "CN=FieldLog Localized Development", env=env)
    cert = pair.command(pair.JAVA / "bin/keytool", "-exportcert", "-keystore", key, "-alias", "fieldlog-localized",
                        "-storepass:env", password, env=env)
    pair.command(pair.TOOLS / "apksigner", "sign", "--ks", key, "--ks-pass", "env:" + password,
                 "--v3-signing-enabled", "true", "--v4-signing-enabled", "false", "--out", output_apk, aligned,
                 timeout=60, env=env)
    sizes["afterAPK"] = workspace_bytes(pair.CAMPAIGN)
    require(sizes["afterAPK"] < BUDGET, "scratch exceeded packaging budget")
    result = pair.check_apk("app", VERSION, output_apk, {"engine": original_case["engine"], "host": host})
    old = original_case["apk"]
    members = result["membersSHA256"]
    require(members.keys() == old["membersSHA256"].keys(), "repackaged APK member inventory differs")
    require({name for name in members if members[name] != old["membersSHA256"][name]} ==
            {ASSETS + name for name in CHANGES}, "repackaged APK had unexpected member changes")
    require(result["signerSHA256"] == pair.sha(cert) != old["signerSHA256"], "APK signer was not the fresh certificate")
    return result


def package(work, base, guests):
    # The maintained packager reads its two fixed path arguments at import time.
    argv = sys.argv
    try:
        sys.argv = [argv[0], str(work), str(PAIR)]
        pair = import_pair("fieldlog_pair_packager", PAIR / "replay/package-pair.py")
    finally:
        sys.argv = argv

    plan = input_plan(base, guests)
    handoff = pair.HANDOFF
    tools = handoff / "tools"
    tools.mkdir(parents=True)
    for name, digest in LOCK["base"].items():
        if name.startswith("tools/"):
            destination = handoff / name
            shutil.copyfile(base / name, destination)
            pinned(destination, digest).chmod(0o700)

    case = plan["case"]
    # Reinspect the original signed APK using the maintained pair's verification.
    pair.HANDOFF = base
    inspected = pair.check_apk("new", VERSION, base / "new/FieldLog.apk", case)
    require(inspected == case["apk"], "base APK did not reverify against the maintained receipt")
    pair.HANDOFF = handoff

    scratch = pair.SCRATCH
    signing = scratch / "signing"
    signing.mkdir()
    signer = build_signer(pair, scratch)
    assets = plan["assets"]
    descriptor = json.loads(assets["identity.json"])
    roots = pair.command(signer, "root", signing)
    root, = json.loads(roots)
    require(root["scope"] == SCOPE and root["artifact"] and root["assignment"] and not root["revoked"] and
            root["public_key"] not in {item["public_key"] for item in json.loads(assets["roots.json"])},
            "unexpected or reused trust root")
    descriptor["build"]["trust_roots_sha256"] = pair.sha(roots)
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]
        if port == int(assets["port.txt"]):
            with socket.socket() as alternate:
                alternate.bind(("127.0.0.1", 0))
                port = alternate.getsockname()[1]
    assets.update({"roots.json": roots, "identity.json": (json.dumps(descriptor, sort_keys=True, indent=2) + "\n").encode(),
                   "port.txt": f"{port}\n".encode()})
    app = handoff / "app"
    installed = app / "Installed"
    installed.mkdir(parents=True)
    for name, data in assets.items():
        (installed / name).write_bytes(data)
    write(app / "installed.sha256.json", {name: pair.sha(data) for name, data in assets.items()})
    host = json.loads(pair.command(pair.VERIFIER, "identity", installed / "identity.json"))
    require(host["runtime"] != plan["host"]["runtime"] and
            host | {"runtime": plan["host"]["runtime"]} == plan["host"], "runtime contract changed")
    write(signing / "host.json", host)
    write(app / "host.json", host)
    for label, manifest in plan["manifests"].items():
        write(signing / f"{label}.manifest.json", manifest)
        shutil.copyfile(guests / f"{label}.wasm", signing / f"{label}.wasm")
        pinned(signing / f"{label}.wasm", PINS["payloads"][label]["sha256"])
    signed = json.loads(pair.command(signer, "issue", signing))

    sizes = {}
    apk = repackage(pair, base, app / "FieldLog.apk", assets, case, host, sizes)
    # Verify both signed sets against bytes extracted from the final APK.
    releases = {}
    for index, label in enumerate(LABELS):
        issued = signed[label]
        manifest, assignment = issued["manifest"]["manifest"], issued["assignment"]["assignment"]
        require(manifest == plan["manifests"][label] | {
            key: manifest[key] for key in ("runtime", "key_id", "created_at_unix")
        } and manifest["runtime"] == host["runtime"], f"{label} manifest input changed")
        require(assignment == {
            "schema": 3, "scope": SCOPE, "runtime": host["runtime"], "channel": CHANNEL, "cohort": "sha256-v1",
            "rollout_basis_points": 10000, "sequence": index + 1, "release_id": manifest["release_id"],
            "artifact_sha256": issued["digest"], "key_id": manifest["key_id"],
            "created_at_unix": manifest["created_at_unix"],
        }, f"{label} assignment binding changed")
        destination = handoff / label
        destination.mkdir()
        manifest_file = destination / "manifest.json"
        assignment_file = destination / "assignment.json"
        guest = destination / "guest.wasm"
        write(manifest_file, issued["manifest"])
        write(assignment_file, issued["assignment"])
        shutil.copyfile(signing / f"{label}.wasm", guest)
        verified = json.loads(pair.command(
            pair.VERIFIER, "verify", scratch / "app.apk.identity.json", scratch / "app.apk.roots.json",
            manifest_file, guest, assignment_file, CHANNEL, INSTALLATION, str(index), str(manifest["created_at_unix"]),
        ))
        require((verified["artifactSHA256"], verified["releaseID"], verified["sequence"]) ==
                (issued["digest"], manifest["release_id"], index + 1), f"{label} verifier binding changed")
        releases[label] = {"cursor": index, **verified}
        write(destination / "upload.json", {"signed_manifest": issued["manifest"],
                                           "payload": base64.b64encode(guest.read_bytes()).decode("ascii")})
        write(destination / "validate.json", {"artifact_sha256": issued["digest"]})
        write(destination / "publish.json", {"signed_assignment": issued["assignment"]})

    require(releases["baseline"]["cohortBucket"] == releases["reviewed"]["cohortBucket"] and
            releases["baseline"]["artifactSHA256"] != releases["reviewed"]["artifactSHA256"],
            "pair did not retain the cohort or distinct artifacts")
    routing = plan["routing"]
    write(handoff / "routing.json", routing | {"listen": f"127.0.0.1:{port}", "runtime": host["runtime"]})
    write(handoff / "origin-config.template.json", {
        "developer_mode": True, "listen": f"127.0.0.1:{port}", "roots": [root], "hosts": [host],
    })
    write(handoff / "package-result.json", {
        "status": "apk-and-two-v3-releases-verified", "createdUTC": datetime.now(timezone.utc).isoformat(),
        "source": plan["source"], "engine": case["engine"], "baseSignerSHA256": case["apk"]["signerSHA256"],
        "apk": apk, "host": host, "releases": releases, "installationUsedByVerifier": INSTALLATION,
        "toolVersions": {
            "python": sys.version, "java": pair.command(pair.JAVA / "bin/java", "--version").decode().strip(),
            "go": pair.command(pair.GO, "version", env=pair.ENV | {
                "HOME": os.environ["MIXER_RECIPE_GO_HOME"],
            }).decode().strip(),
            "apksigner": pair.command(pair.TOOLS / "apksigner", "version").decode().strip(),
        },
        "toolsSHA256": {str(path): sha(path) for path in (
            pair.GO, pair.JAVA / "bin/keytool", pair.TOOLS / "apksigner", pair.TOOLS / "lib/apksigner.jar",
            pair.TOOLS / "zipalign", pair.SDK / "build-tools/37.0.0/aapt",
            pair.SDK / "build-tools/37.0.0/apksigner", pair.SDK / "build-tools/37.0.0/lib/apksigner.jar",
            pair.SDK / "build-tools/37.0.0/zipalign",
        )},
        "scratchSamplesBytes": sizes, "commands": pair.COMMANDS,
        "fixtureSHA256": inventory({name: RECIPE / name for name in
                                    ("package.py", "package-pins.json", "sign-localized.go")}),
        "pending": ["local origin sequencing", "native install, layout, tap, and offline readback"],
    })


def main(base, guests):
    runner = import_pair("fieldlog_pair_runner", PAIR / "run.py")
    os.umask(0o077)
    parent = REPO / "verification/local"
    require(shutil.disk_usage(REPO).free >= runner.STOP_FREE + BUDGET, "insufficient volume reserve for packaging")
    parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="fieldlog-localized-single-apk.", dir=parent))
    print(f"Private packaging campaign {work}", flush=True)
    marker = work / "IN-PROGRESS.json"
    handoff = work / "handoff"
    custody = runner.Custody()
    stage = "package"
    try:
        write(marker, {"stage": stage, "reuse": "fresh campaign only"})
        (work / "scratch/tmp").mkdir(parents=True)
        runner.run(work, custody, stage, [
            sys.executable, "-B", PAIR / "replay/toolchain.py", work, sys.executable, "-B", __file__,
            "--phase", work, "--base", base, "--guests", guests,
        ], 350)
        shutil.copyfile(work / "package.json", handoff / "package-command.json")
        stage = "seal"
        write(marker, {"stage": stage, "reuse": "fresh campaign only"})
        with (handoff / "SHA256SUMS").open("x") as stream:
            for path in sorted(handoff.rglob("*")):
                if path.is_file() and path.name != "SHA256SUMS":
                    stream.write(f"{sha(path)}  {path.relative_to(handoff)}\n")
        runner.run(work, custody, stage, ["/usr/bin/shasum", "-a", "256", "-c", "SHA256SUMS"], 60, cwd=handoff)
        stage = "cleanup"
        write(marker, {"stage": stage, "reuse": "fresh campaign only"})
        shutil.rmtree(work / "scratch")
        marker.unlink()
    except BaseException as error:
        # An outer exit/group observation cannot settle escaped child custody after a failed phase.
        try:
            with (work / "HOLD.json").open("x") as hold:
                json.dump({"stage": stage, "pendingGroup": custody.pending, "failure": type(error).__name__,
                           "reason": "preserve the campaign for root review"}, hold, indent=2)
        except OSError:
            pass
        print(f"Retained campaign after {stage} failure: {work}", file=sys.stderr)
        raise
    print(f"Sealed private handoff: {handoff}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True, help="exact sealed engine-pair handoff directory")
    parser.add_argument("--guests", type=Path, required=True, help="exact verified localized export directory")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-inputs", action="store_true", help="read-only pin, manifest and routing control")
    mode.add_argument("--phase", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    base, guests = args.base.resolve(strict=True), args.guests.resolve(strict=True)
    if args.check_inputs:
        plan = input_plan(base, guests)
        print(json.dumps({key: plan[key] for key in ("manifests", "routing")}, indent=2))
    elif args.phase:
        package(args.phase, base, guests)
    else:
        main(base, guests)
