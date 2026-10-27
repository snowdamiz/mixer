"""Independent bounded review adapters: verified data and source-only loading, no pycache."""
import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys
import types

OWN = Path(__file__).resolve().parent
REPO = OWN.parents[2]
CANDIDATE = REPO / "verification/android-editor-generic-descriptor-joins"
ARCHIVE = REPO / "verification/android-editor-membership-compiled-boundary-qualification/selected-v4-composed-replay-review"
PREACCESS = OWN.parent
CANDIDATE_SEAL = "e8c7263060a98f05142ac1f31eb5b30d05a921fd8feeeb9d23de798cab4b3ad5"
ARCHIVE_SEAL = "c06e384c26568f50be149a819bdf08259c03ab3e65ce867f1dc8477933bf8423"
PARSER_SHA = "211ad86c8b0ffd9048d322efbb9e93bc3fc6606dcf745788bb36ec6052adfd2d"
USED = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def ident(raw):
    return {"bytes": len(raw), "sha256": sha(raw)}


def members(root, expected):
    raw = (root / "seal.json").read_bytes()
    assert sha(raw) == expected
    return {m["path"]: m for m in json.loads(raw)["members"]}


ARCHIVE_MEMBERS = members(ARCHIVE, ARCHIVE_SEAL)
CANDIDATE_MEMBERS = members(CANDIDATE, CANDIDATE_SEAL)


def verified(root, member, table):
    path = PurePosixPath(str(member))
    assert not path.is_absolute() and ".." not in path.parts and str(path) == str(member)
    assert str(member) in table
    target = root
    for part in path.parts:
        target /= part
        assert not target.is_symlink()
    assert target.resolve().is_relative_to(root.resolve())
    raw = target.read_bytes()
    assert ident(raw) == {k: table[str(member)][k] for k in ("bytes", "sha256")}
    USED[str(target.relative_to(REPO))] = ident(raw)
    return raw


def candidate(member):
    return verified(CANDIDATE, member, CANDIDATE_MEMBERS)


def archive(member):
    return verified(ARCHIVE, member, ARCHIVE_MEMBERS)


def source_module(name, raw, filename):
    module = types.ModuleType(name)
    module.__file__ = str(filename)
    sys.modules[name] = module
    exec(compile(raw, str(filename), "exec"), module.__dict__)
    return module


def load_candidate():
    # This is the sole candidate implementation module. No wrapper/auditor/product is executed.
    d = source_module("check_descriptor_joins", candidate("check_descriptor_joins.py"), CANDIDATE / "check_descriptor_joins.py")

    class ArchiveInputs(d.Inputs):
        def pinned(self, relative, expected):
            key = "reference-tree/" + str(relative)
            if key in ARCHIVE_MEMBERS:
                raw = archive(key)
            else:
                assert str(relative) in (str(d.SELECTION), str(d.ACCEPTANCE))
                path = REPO / relative
                assert not path.is_symlink()
                raw = path.read_bytes()
                USED[str(relative)] = ident(raw)
            assert sha(raw) == expected
            self.used[str(relative)] = ident(raw)
            return raw

        def read(self, relative):
            name = str(relative)
            d.need(name in self.allowed, "unreleased independent data input")
            raw = archive("reference-tree/" + name)
            d.need(ident(raw) == self.allowed[name], "independent archived input identity")
            self.used[name] = ident(raw)
            return raw

    d.Inputs = ArchiveInputs
    # Root-authorized source-only execution of exact existing data-reader dependency.
    parser_path = REPO / d.PARSER
    parser_raw = parser_path.read_bytes()
    assert sha(parser_raw) == PARSER_SHA
    USED[str(d.PARSER)] = ident(parser_raw)
    original_spec = importlib.util.spec_from_file_location

    class VerifiedSourceLoader(importlib.abc.Loader):
        def create_module(self, spec):
            return None

        def exec_module(self, module):
            exec(compile(parser_raw, str(parser_path), "exec"), module.__dict__)

    def source_only_spec(name, location, *args, **kwargs):
        assert name == "_sealed_data_classfile_reader" and Path(location) == parser_path
        return importlib.util.spec_from_loader(name, VerifiedSourceLoader(), origin=str(parser_path))

    d.importlib.util.spec_from_file_location = source_only_spec
    return d, original_spec


def write(name, value):
    (OWN / name).write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n")


def check_preaccess():
    raw = (PREACCESS / "preaccess-seal.json").read_bytes()
    assert sha(raw) == "e04efcdbeedfea4c8effc99d51bbe4ca63b2b4b1be21f22c7076ee0c89e5f236"
    seal = json.loads(raw)
    for member in seal["members"]:
        assert ident((PREACCESS / member["path"]).read_bytes()) == {k: member[k] for k in ("bytes", "sha256")}
    return True
