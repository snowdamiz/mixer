"""Independent pure-byte oracle. Never constructs product authority or opens inputs.

The Rust proposal only checks candidate shape and counts references. This Python
oracle additionally checks byte relationships in the frozen loader's formats.
Passing it does not authenticate a launcher, review, file identity or admission.
"""
from dataclasses import dataclass
import hashlib
import json
import struct

IDENTITIES = (
    "source", "build", "session", "executable", "compiler", "compiler_version",
    "compile_manifest", "compile_argv", "compile_environment", "process_argv",
    "process_environment", "review",
)
PATH_ROLES = ("source", "build", "session", "rows create_new", "snapshot create_new")
COMPILE_KEYS = (
    b"MIXER_LOADER_MANIFEST_SHA256", b"MIXER_LOADER_COMMAND_SHA256",
    b"MIXER_LOADER_COMPILE_ENV_SHA256", b"MIXER_LOADER_COMPILER_SHA256",
    b"MIXER_LOADER_COMPILER_VERSION_SHA256",
)
SESSION_KEYS = (b"MIXER_LOADER_EXPECTED_SESSION_SHA256", b"MIXER_LOADER_EXPECTED_NONCE_HEX")
SOURCE_SHA256 = "9804738523f3053f2b7a0093ecd5b324ecf54b1d43094993cdb2ee7d63747806"
VALIDATION = (1947, 1_000_000, 65_536, 1_000_000, 10_000)
PRODUCT_FIELDS = (
    "source_bytes", "metadata_bytes", "cache_bytes", "cache_entry_bytes",
    "cache_entries", "active_pins", "cache_work", "frames", "values", "controls",
    "memory_pages", "state_bytes", "combined_bytes", "instruction_fuel",
    "execution_work", "host_calls", "deadline_ms",
)
U64_MAX = (1 << 64) - 1
STATUS = "byte-relationships-only-unqualified-candidate"


class InvalidInput(ValueError):
    pass


def require(test, reason):
    if not test:
        raise InvalidInput(reason)


def digest(data):
    require(type(data) is bytes, "immutable bytes required")
    return hashlib.sha256(data).digest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def word(data, offset):
    require(offset >= 0 and offset + 8 <= len(data), "truncated u64")
    return struct.unpack_from("<Q", data, offset)[0]


def unpack_list(data, *, environment=False, compile=False):
    require(type(data) is bytes and 8 <= len(data) <= 16384, "list extent")
    count = word(data, 0)
    require(count <= 64 and (environment or count > 0), "list count")
    at, result, prior = 8, [], None
    for _ in range(count):
        size = word(data, at)
        at += 8
        require(size < 4096 and at + size <= len(data), "list item extent")
        value = data[at:at + size]
        require(b"\0" not in value, "NUL list item")
        at += size
        if environment:
            key, equal, _ = value.partition(b"=")
            require(equal and key, "environment entry")
            require(prior is None or prior < key, "environment key ordering/duplicate")
            require(key not in (COMPILE_KEYS if compile else SESSION_KEYS), "excluded identity key")
            prior = key
        result.append(value)
    require(at == len(data), "list trailing bytes")
    return tuple(result)


def parse_record(data, *, session=False):
    require(type(data) is bytes, "immutable record required")
    require(512 <= len(data) <= (65536 if session else 131072), "record extent")
    require(data[:8] == (b"MIXLSE01" if session else b"MIXLBD01"), "record magic")
    require(tuple(word(data, at) for at in (8, 16, 24)) == (1, 512, len(data)), "record header")
    if session:
        require(not any(data[368:512]), "session reserved")
        offsets, caps = 40, (64, 16384, 16384, 4096)
    else:
        require((word(data, 32), word(data, 40)) == (146, 11), "fresh146+11 required")
        require(0 < word(data, 80) <= 67108864, "executable extent")
        target = b"aarch64-apple-darwin"
        require(data[88:88 + len(target)] == target, "target")
        require(not any(data[88 + len(target):152]) and not any(data[344:512]), "build reserved")
        offsets, caps = 48, (65536, 16384, 16384, 16384)
    cursor, parts = 512, []
    for i, cap in enumerate(caps):
        size = word(data, offsets + i * 8)
        require(0 < size <= cap and cursor + size <= len(data), "section extent")
        parts.append(data[cursor:cursor + size])
        cursor += size
    require(cursor == len(data), "record trailing bytes")
    if session:
        require(len(parts[0]) == 64, "source File identity64")
        unpack_list(parts[1])
        unpack_list(parts[2], environment=True)
        require(parts[3].startswith(b"/") and b"\0" not in parts[3] and len(parts[3]) < 4096, "cwd encoding")
        digests = tuple(data[240 + 32 * i:272 + 32 * i] for i in range(4))
        return {"parts": tuple(parts), "digests": digests, "source_bytes": word(data, 32),
                "validation": tuple(word(data, 72 + i * 8) for i in range(5)),
                "nonce": data[112:144], "source": data[144:176],
                "build": data[176:208], "executable": data[208:240]}
    unpack_list(parts[1], compile=True)
    unpack_list(parts[2], environment=True, compile=True)
    digests = tuple(data[152 + 32 * i:184 + 32 * i] for i in range(6))
    return {"parts": tuple(parts), "digests": digests, "output_bytes": word(data, 80)}


@dataclass(frozen=True)
class Identity:
    role: str
    data: bytes
    sha256: bytes


def checked_sum(values, limit=U64_MAX):
    require(type(limit) is int and 0 < limit <= U64_MAX, "sum limit")
    total = 0
    for value in values:
        require(type(value) is int and 0 < value <= limit, "positive actual extent")
        require(total <= limit - value, "backing overflow")
        total += value
    return total


def describe_candidate(identities, native_paths, retained_paths, *, limit=U64_MAX):
    require(tuple(item.role for item in identities) == IDENTITIES, "exact12 role order")
    require(len(native_paths) == len(retained_paths) == 5, "exact5 paths")
    for item in identities:
        require(type(item.data) is bytes and len(item.data) > 0, "immutable nonempty identity")
        # This oracle verifies digests using Python's standard hashlib. The Rust
        # candidate delegates this work; this check creates no trusted witness.
        require(type(item.sha256) is bytes and item.sha256 == digest(item.data), "identity digest mismatch")
    source = identities[0]
    require(len(source.data) == 1947 and source.sha256.hex() == SOURCE_SHA256, "selected source constraint")
    for actual, retained in zip(native_paths, retained_paths):
        require(type(actual) is bytes and type(retained) is bytes, "immutable native paths")
        require(actual and b"\0" not in actual, "native path shape")
        require(actual == retained, "native path correspondence")
    counts = tuple(len(item.data) for item in identities)
    paths = tuple(map(len, native_paths))
    retained = tuple(map(len, retained_paths))
    total = checked_sum(counts + paths + retained, limit)
    return {"status": STATUS, "identity_bytes": counts, "native_path_bytes": paths,
            "separately_retained_path_bytes": retained, "input_backing_bytes": total,
            "authenticated_owner": False, "operational_grant": False,
            "upstream_acquisition_work_storage_diagnostics": "pending"}


def checked_roster(value, count):
    require(type(value) is dict and value.get("schema") == 1, "roster schema")
    rows = value.get("members")
    require(type(rows) is list and len(rows) == value.get("member_count") == count, "roster member count")
    names = [row.get("path") for row in rows]
    require(all(type(name) is str and name for name in names), "roster path")
    require(names == sorted(set(names)), "roster order/duplicate")
    for row in rows:
        require(set(row) == {"path", "bytes", "sha256"}, "roster row keys")
        require(type(row["bytes"]) is int and row["bytes"] > 0, "roster size")
        require(type(row["sha256"]) is str and len(row["sha256"]) == 64, "roster digest")
        require(all(c in "0123456789abcdef" for c in row["sha256"]), "roster digest encoding")
    require(value.get("tree_sha256") == digest(canonical(rows)).hex(), "roster tree digest")
    return rows


def check_compile_closure(data, *, expected_distribution, expected_compiled_source, expected_host):
    # The loader hashes opaque manifest bytes; this is the separately proposed
    # launcher protocol, based on the exact source146 composition format.
    try:
        value = json.loads(data)
    except (ValueError, TypeError, UnicodeDecodeError) as error:
        raise InvalidInput("manifest JSON") from error
    require(type(value) is dict and value.get("schema") == 1, "manifest schema")
    require(canonical(value) == data, "canonical manifest encoding")
    for name, expected, count in (("distribution", expected_distribution, 146),
                                  ("compiled_source", expected_compiled_source, 146),
                                  ("host_support", expected_host, 11)):
        checked_roster(value.get(name), count)
        require(value[name] == expected, "manifest exact expected " + name)
    require(value.get("private_route_cfg") == "mixer_bootstrap_one_fixture_v1", "private cfg")
    require(value.get("test_overlay") is False, "production source required")
    # An output commitment is produced after this immutable manifest. A future
    # launcher must not patch this manifest to embed its own executable hash.
    require(not any(key in value for key in ("executable", "output_sha256", "artifact")), "postcompile manifest circularity")
    return value


def check_product_budget(fields):
    require(type(fields) is dict and set(fields) == set(PRODUCT_FIELDS), "all17 product fields")
    require(all(type(v) is int and 0 < v <= U64_MAX for v in fields.values()), "explicit positive product fields")
    require(fields["execution_work"] == 1_000_000_000 and fields["combined_bytes"] == 268_435_456, "selected product constraints")
    return "shape-only-policy-selection-pending"


def check_correspondence(identities, *, expected_session, expected_nonce, source_file_identity):
    require(tuple(item.role for item in identities) == IDENTITIES, "exact12 role order")
    items = {item.role: item for item in identities}
    for item in identities:
        require(type(item.data) is bytes and item.data and item.sha256 == digest(item.data), "identity preimage/digest")
    require(len(items["source"].data) == 1947 and items["source"].sha256.hex() == SOURCE_SHA256, "selected source constraint")
    require(0 < len(items["executable"].data) <= 67108864, "executable full preimage")
    build, session = parse_record(items["build"].data), parse_record(items["session"].data, session=True)
    parts = tuple(items[name].data for name in ("compile_manifest", "compile_argv", "compile_environment", "compiler_version"))
    require(build["parts"] == parts, "full build section correspondence")
    require(build["digests"][:4] == tuple(map(digest, parts)), "build section digests")
    require(build["digests"][4] == items["compiler"].sha256, "compiler digest slot")
    require(build["digests"][5] == items["executable"].sha256 and build["output_bytes"] == len(items["executable"].data), "postcompile executable commitment")
    embedded = (items["compile_manifest"].sha256, items["compile_argv"].sha256,
                items["compile_environment"].sha256, items["compiler"].sha256,
                items["compiler_version"].sha256)
    require(tuple(build["digests"][i] for i in (0, 1, 2, 4, 3)) == embedded, "embedded key order")
    require(session["validation"] == VALIDATION, "original validation constraints")
    require(session["source_bytes"] == 1947, "session source extent")
    require(type(source_file_identity) is bytes and len(source_file_identity) == 64, "actual source File identity64 required")
    require(session["parts"][0] == source_file_identity and word(source_file_identity, 16) == 1947, "source File identity correspondence")
    require(session["parts"][1:3] == (items["process_argv"].data, items["process_environment"].data), "process preimage correspondence")
    require(session["digests"] == tuple(map(digest, session["parts"])), "session section digests")
    require(session["source"] == items["source"].sha256 and session["build"] == items["build"].sha256, "session source/build commitments")
    require(session["executable"] == items["executable"].sha256, "session executable commitment")
    require(type(expected_session) is bytes and expected_session == items["session"].sha256, "launcher session commitment")
    require(type(expected_nonce) is bytes and len(expected_nonce) == 32 and session["nonce"] == expected_nonce, "launcher nonce")
    return {"status": STATUS, "embedded_identity_digests": tuple(x.hex() for x in embedded),
            "actual_binary_embedded_values_observed": False, "launcher_or_file_custody_authenticated": False,
            "review_authenticated": False, "operational_grant": False}
