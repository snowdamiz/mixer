"""Bind the localized rotation inputs using the ordinary iOS source inventories."""

import argparse
from hashlib import file_digest, sha256
import json
from pathlib import Path

PACKAGES = ("capability-activation", "experimental-capability-runtime", "runtime-identity", "sdk", "updates")
EMBEDDED = Path("ios/FieldLog/ChecklistRelease")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open("rb") as source:
        return file_digest(source, "sha256").hexdigest()


def inventory(root, directories, exclude=None):
    files = []
    for directory in directories:
        path = root / directory
        require(path.is_dir() and not path.is_symlink(), f"Missing source root: {path}")
        for entry in path.rglob("*"):
            if exclude is not None and entry.is_relative_to(exclude):
                continue
            require(not entry.is_symlink(), f"Unexpected source link: {entry}")
            if entry.is_file():
                files.append(entry)
    lines = (f"{digest(file)}  {file.relative_to(root)}\n" for file in sorted(files))
    return sha256("".join(lines).encode()).hexdigest()


def source_digests(source):
    fieldlog = source / "fieldlog"
    return {
        "link_inputs_sha256": inventory(source, [Path("mixer") / name for name in PACKAGES]),
        "native_fallback_sha256": inventory(fieldlog, [Path("Sources"), Path("ios/FieldLog")],
                                            exclude=fieldlog / EMBEDDED),
    }


def verify(packet, fixture=None):
    source = packet.parent / "source"
    template = packet / "templates/Installed/identity.json"
    binding = json.loads((packet / "localized-binding.json").read_bytes())
    identity = json.loads(template.read_bytes())
    require(digest(template) == binding["identityTemplateSHA256"], "Changed localized identity template")
    actual = source_digests(source)
    require(actual == binding["buildSourceDigests"] and all(identity["build"][k] == v for k, v in actual.items()),
            "Localized identity does not match the staged source inventories")
    for relative, expected in binding["overlayFilesSHA256"].items():
        require(digest(source / relative) == expected, f"Changed staged overlay: {relative}")
    for relative, expected in binding["packetFilesSHA256"].items():
        require(digest(packet / relative) == expected, f"Changed staged recipe: {relative}")
    if fixture is not None:
        installed = fixture / "Installed"
        identity["build"]["trust_roots_sha256"] = digest(installed / "roots.json")
        require(json.loads((installed / "identity.json").read_bytes()) == identity,
                "Signed fixture identity differs from the localized template and public roots")
    return actual


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, help="also check the signed Installed identity")
    args = parser.parse_args()
    print(json.dumps(verify(Path(__file__).resolve().parent, args.fixture), indent=2))
