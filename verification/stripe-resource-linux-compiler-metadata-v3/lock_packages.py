"""Derive a byte-pinned package lock from successful native APT simulation.

No dependency solver is implemented here. Native APT selected the versions;
this host-only step strictly joins its Inst/Conf records to authenticated bytes.
It never contacts an origin or reads/executes a package payload.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

import run_container as candidate


ROOTS = ("gcc:arm64", "libc6-dev:arm64", "binutils:arm64")
SUITES = ("noble", "noble-updates", "noble-security")
SIGNER = "F6ECB3762474EDA9D21B7022871920D1991BC93C"
ORIGIN = "https://ports.ubuntu.com/ubuntu-ports/"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(raw):
    values, key = {}, None
    for line in raw.decode("utf-8").splitlines():
        if line.startswith((" ", "\t")):
            require(key is not None, "orphan Deb822 continuation")
            values[key] += "\n"+line
            continue
        require(":" in line, "invalid Deb822 field")
        key, value = line.split(":", 1)
        require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", key) is not None, "invalid Deb822 field name")
        require(key not in values, "duplicate Deb822 field")
        values[key] = value.lstrip(" ")
    return values


def native_selection(text):
    installs, configures, summary = {}, {}, None
    pattern = re.compile(r"^(Inst|Conf) ([a-z0-9][a-z0-9+.-]*)(?::(arm64|all))?(?: \[([^\]]+)\])? \((\S+) (.+) \[(arm64|all)\]\)$")
    for line in text.splitlines():
        if line.startswith("Remv "):
            raise ValueError("native removal forbidden")
        if line.startswith(("Inst ", "Conf ")):
            match = pattern.fullmatch(line)
            require(match is not None, "unrecognized native package record")
            action, name, qualifier, old, version, origins, architecture = match.groups()
            require(qualifier is None or qualifier == architecture, "native architecture qualifier mismatch")
            sources = origins.split(", ")
            require(all(source in {"Ubuntu:24.04/"+suite for suite in SUITES} for source in sources), "unselected native origin")
            target = installs if action == "Inst" else configures
            require(name not in target, "duplicate native package record")
            target[name] = {"name": name, "version": version, "architecture": architecture,
                            "oldVersion": old, "originSuites": [source.split("/", 1)[1] for source in sources],
                            "raw": line}
        match = re.fullmatch(r"(\d+) upgraded, (\d+) newly installed, (\d+) to remove and (\d+) not upgraded\.", line)
        if match:
            require(summary is None, "duplicate native summary")
            summary = dict(zip(("upgraded", "newlyInstalled", "removed", "notUpgraded"), map(int, match.groups())))
    require(summary is not None and summary["removed"] == 0, "native summary missing or removal selected")
    require(0 < len(installs) <= 48 and set(installs) == set(configures), "native Inst/Conf set mismatch")
    require(len(installs) == summary["upgraded"]+summary["newlyInstalled"], "native package count mismatch")
    for name, item in installs.items():
        other = configures[name]
        require((item["version"], item["architecture"], item["originSuites"]) ==
                (other["version"], other["architecture"], other["originSuites"]), "native Inst/Conf identity mismatch")
        item["confRaw"] = other["raw"]
    require(all(root.split(":")[0] in installs for root in ROOTS), "selected native root missing")
    return installs, summary


def artifact_identity(item):
    required = ("Package", "Version", "Architecture", "Filename", "Size", "Installed-Size", "SHA256")
    require(all(key in item for key in required), "signed package identity incomplete")
    require(item["Architecture"] in ("arm64", "all"), "unselected package architecture")
    filename = item["Filename"]
    path = PurePosixPath(filename)
    require(filename.startswith("pool/main/") and not path.is_absolute() and str(path) == filename
            and all(part not in ("", ".", "..") for part in filename.split("/"))
            and re.fullmatch(r"[A-Za-z0-9+._/~\-]+\.deb", filename) is not None, "unsafe or unselected package path")
    require(item["Size"].isdigit() and 0 < int(item["Size"]) <= 67108864, "package size bound")
    require(item["Installed-Size"].isdigit(), "invalid installed size")
    require(re.fullmatch(r"[0-9a-f]{64}", item["SHA256"]) is not None, "signed SHA256 missing")
    return (filename, int(item["Size"]), item["SHA256"], int(item["Installed-Size"]),
            item.get("Source"), item.get("Depends"), item.get("Pre-Depends"))


def ref(path):
    return {"path": str(path.relative_to(candidate.ROOT)), "bytes": path.stat().st_size,
            "sha256": candidate.sha(path)}


def derive():
    here, root = candidate.HERE, candidate.ROOT
    receipt = json.loads((here/"attempt/receipt.json").read_text())
    require(receipt["status"] == "offline-metadata-resolution-completed", "native attempt unsuccessful")
    require(receipt["phases"]["resolve"]["exitCode"] == 0
            and "MIXER_SOLVER_EXIT=0" in receipt["phases"]["resolve"]["markers"], "native simulation unsuccessful")
    require(candidate.sha(candidate.PRIOR_FAILURE) == candidate.PRIOR_FAILURE_SHA, "preserved failure seal changed")
    require(candidate.sha(candidate.METADATA) == candidate.METADATA_SHA, "authenticated metadata seal changed")
    old = root/"verification/stripe-resource-linux-compiler-metadata"
    manifest = json.loads((old/"metadata-authenticated-manifest.json").read_text())
    artifacts = here/"attempt/artifacts"
    base_path, solver_path = artifacts/"base-status", artifacts/"solver.stdout"
    require(candidate.sha(base_path) == "fbebbb0ae9cd843a7d1ffe888b203d2d1dcf879d3ab7efc60122cf4674d6e122", "base status changed")
    installs, summary = native_selection(solver_path.read_text())
    baseline = {}
    for raw in base_path.read_bytes().split(b"\n\n"):
        if raw.strip():
            item = fields(raw)
            require(item.get("Status") == "install ok installed", "unsupported partial baseline package state")
            key = (item["Package"], item["Architecture"])
            require(key not in baseline, "duplicate baseline package")
            baseline[key] = item["Version"]
    selected = {(item["name"], item["version"], item["architecture"]): [] for item in installs.values()}
    raw_stanzas = {}
    for suite in SUITES:
        index = manifest["indexes"][suite]
        index_path = root/index["expandedPath"]
        require(candidate.sha(index_path) == index["expandedSha256"] and index_path.stat().st_size == index["expandedBytes"], "authenticated expanded index changed")
        release_path = artifacts/(suite+".Release")
        require(candidate.sha(release_path) == index["nativeVerifiedCleartextSha256"], "current native release changed")
        status_path = artifacts/(suite+".gpg.status")
        status = status_path.read_text()
        require([line.split()[2] for line in status.splitlines() if line.startswith("[GNUPG:] VALIDSIG ")] == [SIGNER], "current native signer missing")
        offset = 0
        for raw in index_path.read_bytes().split(b"\n\n"):
            if raw.strip():
                item = fields(raw)
                key = (item.get("Package"), item.get("Version"), item.get("Architecture"))
                if key in selected:
                    artifact_identity(item)
                    stanza_sha = hashlib.sha256(raw).hexdigest()
                    source = {"origin": ORIGIN, "suite": suite, "component": "main", "indexArchitecture": "arm64",
                        "signerFingerprint": SIGNER,
                        "inRelease": ref(old/"acquisition"/(suite+".InRelease")),
                        "nativeSignatureStatus": ref(status_path), "nativeVerifiedRelease": ref(release_path),
                        "compressedIndex": ref(old/"acquisition"/(suite+".Packages.xz")),
                        "authenticatedExpandedIndex": ref(index_path),
                        "stanzaOffset": offset, "stanzaBytes": len(raw), "stanzaSha256": stanza_sha}
                    selected[key].append((item, source))
                    raw_stanzas[(item["Package"], suite)] = raw
            offset += len(raw)+2
    packages, changes = [], []
    total_bytes, installed_bytes = 0, 0
    for name, native in installs.items():
        matches = selected[(name, native["version"], native["architecture"])]
        require(matches, "native selected package absent from authenticated indexes")
        identities = {artifact_identity(item) for item, _ in matches}
        require(len(identities) == 1, "signed origins disagree about selected artifact")
        require(set(native["originSuites"]) == {source["suite"] for _, source in matches}, "native origin suite set differs from signed matches")
        item = matches[0][0]
        filename, size, digest, installed_kib, _, _, _ = next(iter(identities))
        total_bytes += size
        installed_bytes += installed_kib*1024
        old_version = baseline.get((name, native["architecture"]))
        require(old_version == native["oldVersion"], "native old version differs from exact baseline")
        if old_version is not None:
            require(old_version != native["version"], "unexpected selected reinstall")
            changes.append({"name": name, "architecture": native["architecture"], "fromVersion": old_version, "toVersion": native["version"]})
        packages.append({"name": name, "version": native["version"], "architecture": native["architecture"],
            "action": "upgrade" if old_version else "new", "baseVersion": old_version,
            "filename": filename, "url": ORIGIN+filename, "bytes": size, "sha256": digest,
            "installedSizeKiB": installed_kib, "sourcePackageField": item.get("Source", name),
            "depends": item.get("Depends"), "preDepends": item.get("Pre-Depends"),
            "recommendsNotSelected": item.get("Recommends"), "suggestsNotSelected": item.get("Suggests"),
            "nativeInstRecord": native["raw"], "nativeConfRecord": native["confRaw"],
            "signedProvenance": [source for _, source in matches]})
    require(len(changes) == summary["upgraded"], "base delta disagrees with native summary")
    require(total_bytes <= 134217728 and installed_bytes <= 536870912, "prospective payload bounds exceeded")
    lock = {"schema": 1, "status": "native-offline-APT-selected-signed-artifacts-locked-not-acquired",
        "selectedRoots": list(ROOTS), "selectionSha256": candidate.SELECTION_SHA,
        "exportAddendumSha256": candidate.ADDENDUM_SHA,
        "nativeAttempt": ref(here/"attempt/receipt.json"), "nativeSolverStdout": ref(solver_path),
        "nativeSolverStderr": ref(artifacts/"solver.stderr"),
        "baseStatus": ref(base_path), "baseKeyring": ref(artifacts/"base-keyring.gpg"),
        "baselinePackages": [{"name": name, "architecture": architecture, "version": version}
                             for (name, architecture), version in sorted(baseline.items())],
        "authenticatedMetadataManifest": ref(old/"metadata-authenticated-manifest.json"),
        "nativeSummary": summary, "packageCount": len(packages),
        "prospectivePackageTransferBytes": total_bytes,
        "signedInstalledSizeBytes": installed_bytes,
        "installedSizeLimitation": "Sum of signed Installed-Size KiB fields; actual extraction bytes not observed or accepted.",
        "basePackageChanges": changes, "baseRuntimeUpgradeDelta": changes,
        "baseRuntimeUpgradeDeltaScope": "All selected baseline package changes; zero here means no baseline package selected for upgrade.",
        "packages": sorted(packages, key=lambda item: item["name"]),
        "resolutionAuthority": "Native APT2.8.3 successful --simulate with exact captured status and authenticated private lists; host does not solve dependencies.",
        "packageAcquisitionSelected": False, "packageRequests": 0, "installed": False,
        "compilerExecuted": False, "LinuxArtifactAccepted": False, "LinuxResourceRuntimeAccepted": False, "gaAccepted": False}
    return lock, raw_stanzas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    lock, stanzas = derive()
    encoded = json.dumps(lock, indent=2, sort_keys=True)+"\n"
    destination = candidate.HERE/"package-lock.json"
    if args.check:
        require(destination.read_text() == encoded, "derived package lock changed")
        directory = candidate.HERE/"package-stanzas"
        require({path.name for path in directory.iterdir()} ==
                {name+"."+suite+".deb822" for name, suite in stanzas}, "retained stanza set changed")
        for (name, suite), raw in stanzas.items():
            require((directory/(name+"."+suite+".deb822")).read_bytes() == raw, "retained signed stanza changed")
    else:
        require(not destination.exists(), "package lock already exists")
        directory = candidate.HERE/"package-stanzas"
        directory.mkdir(exist_ok=False)
        for (name, suite), raw in sorted(stanzas.items()):
            (directory/(name+"."+suite+".deb822")).write_bytes(raw)
        destination.write_text(encoded)
    print(json.dumps({"status": "exact-package-lock-bindings-pass", "packages": lock["packageCount"],
        "prospectivePackageTransferBytes": lock["prospectivePackageTransferBytes"],
        "signedInstalledSizeBytes": lock["signedInstalledSizeBytes"],
        "baseRuntimeUpgradeDelta": lock["baseRuntimeUpgradeDelta"], "packageRequests": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
