"""Synthetic test fixtures only. No OS Files or production identity authority."""
from dataclasses import asdict
import hashlib
import json
import struct
import model as m


def policy(work=1000000, storage=1000000, complete=True):
    return m.TestPolicy(work, storage, (100000,) * 12, (10000,) * 5, 60000, complete)


def reservation(work=1000000, storage=1000000, cleanup=1000):
    root = m.TestRoot(policy(work + cleanup, storage), startup_already_provisioned=True)
    return root, root.reserve(work, storage, cleanup_work=cleanup)


def handle(data=b"abc", *, inode=1, size=None, responses=None):
    return m.TestHandle(data, m.TestFileIdentity(11, inode, len(data) if size is None else size), responses=responses)


def own_handle(paid, h):
    others = [handle(inode=i + 100) for i in range(12)]
    m.adopt_slots(paid, [h] + others, **m.SLOT_ARGS)
    return h


def packet_bytes(paths):
    return (b"MIXPTH01" + struct.pack("<QQ", 1, 64 + sum(map(len, paths))) +
            b"".join(struct.pack("<Q", len(p)) for p in paths) + b"".join(paths))


def complete_owner(paid, *, record_change=None, source_identity=None):
    raw = [role.encode() for role in m.ROLES]
    if source_identity is None:
        source_identity = m.TestFileIdentity(11, 1, len(raw[0]))
    record = {key: hashlib.sha256(raw[index]).hexdigest() for key, index in
              (("source", 0), ("build", 1), ("executable", 3), ("manifest", 6))}
    record.update(nonce=(b"n" * 32).hex(), validation=[1947, 1000000, 65536, 1000000, 10000],
                  extent=len(raw[0]), source_identity=asdict(source_identity))
    if record_change is not None:
        record_change(record)
    raw[2] = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    paths = tuple(b"/test/path/" + bytes([65 + i]) for i in range(5))
    raw.append(packet_bytes(paths))
    files = [handle(body, inode=i + 1) for i, body in enumerate(raw)]
    files[0].identity = files[0].final_identity = source_identity
    m.adopt_slots(paid, files, **m.SLOT_ARGS)
    bodies = tuple(m.acquire_body(paid, h, role, 100000)[0] for h, role in zip(files, m.ROLES))
    packet = m.acquire_body(paid, files[12], "path_packet", paid.root.policy.packet_cap)[0]
    parsed = m.decode_path_packet(paid, packet.data)
    return bodies, m.acquire_native_paths(paid, parsed)


def admitted_owner(paid):
    bodies, paths = complete_owner(paid)
    view = m.admit_model_only(paid, bodies, paths, trusted_local_launch_contract=True,
                            all_actual_correspondence=True, review_provenance=True)
    return bodies, paths, view


def selected_result(paid, view, provenance=None):
    # Independent handles for the same immutable objects; no equal FD predicate.
    files = [m.TestHandle(b.data, h.identity) for b, h in zip(view.bodies[:4], view.files[:4])]
    buffers = []
    for index, h in enumerate(files):
        body = paid.allocate("loader:" + str(index), len(h.body))
        paid.operation("copy-loader-body:" + str(index), len(h.body))
        body.set_once(h.body)
        buffers.append(body)
    return m.TestSelectedResult(view.correspondence.mapping() if provenance is None else provenance, files, buffers)
