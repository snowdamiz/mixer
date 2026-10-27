"""Pure host protocol state machine. All grants/handles are TEST MODELS only.

No OS handles, input files, compiler, product code or native APIs are used here.
Numbers are synthetic model units, never product costs or selected policy.
"""
from dataclasses import dataclass
import hashlib
import struct

U64_MAX = (1 << 64) - 1
ROLES = ("source", "build", "session", "executable", "compiler",
         "compiler_version", "compile_manifest", "compile_argv",
         "compile_environment", "process_argv", "process_environment", "review")
KNOWN_CAPS = (1947, 131072, 65536, 67108864, None, 16384, 65536,
              16384, 16384, 16384, 16384, None)
BLOCK, ATTEMPTS = 4096, 32


class Refused(ValueError):
    pass


def need(value, reason):
    if not value:
        raise Refused(reason)


def add(*values):
    result = 0
    for value in values:
        need(type(value) is int and 0 <= value <= U64_MAX, "u64")
        need(result <= U64_MAX - value, "overflow")
        result += value
    return result


@dataclass(frozen=True)
class TestPolicy:
    """Explicitly synthetic independently provisioned test fixture policy."""
    work: int
    storage: int
    role_caps: tuple
    path_caps: tuple
    packet_cap: int
    native_and_diagnostic_contract_complete: bool = True


class TestRoot:
    """External synthetic startup root, not derivable from data/digest labels."""
    def __init__(self, policy, *, startup_already_provisioned):
        need(type(policy) is TestPolicy, "source-selected test policy required")
        need(startup_already_provisioned is True, "startup cannot fund itself")
        need(policy.native_and_diagnostic_contract_complete is True,
             "unpriced native/diagnostic closure")
        need(len(policy.role_caps) == 12 and len(policy.path_caps) == 5,
             "role counts")
        need(all(type(n) is int and 0 < n <= U64_MAX for n in
                 policy.role_caps + policy.path_caps +
                 (policy.packet_cap, policy.work, policy.storage)), "finite policy")
        self.policy = policy
        self.used_work = self.used_storage = self.peak = 0
        self.reserved = False
        self.trace = []

    def reserve(self, work, storage):
        need(not self.reserved, "one acquisition")
        need(work > 0 and storage > 0, "complete quote")
        next_work, next_storage = add(self.used_work, work), add(self.used_storage, storage)
        need(next_work <= self.policy.work, "insufficient work")
        need(next_storage <= self.policy.storage, "insufficient storage")
        self.used_work, self.used_storage = next_work, next_storage
        self.peak = max(self.peak, next_storage)
        self.reserved = True
        self.trace.append(("reserve", work, storage))
        return TestReservation(self, work, storage)


class TestReservation:
    def __init__(self, root, work, storage):
        self.root = root
        self.work_left, self.storage_left = work, storage
        self.owned = []
        self.diagnostics = []
        self.effects = []
        self.retired = self.released = False

    def operation(self, name, work, storage=0):
        need(not self.retired, "retired reservation")
        need(type(work) is int and work > 0 and type(storage) is int and storage >= 0,
             "positive priced work")
        need(work <= self.work_left, "operation before work prepay")
        need(storage <= self.storage_left, "operation before storage prepay")
        # Both comparisons finish before any commit/effect; failure is atomic.
        self.work_left -= work
        self.storage_left -= storage
        self.root.trace.append(("prepay", name, work, storage))
        self.effects.append(name)
        self.root.trace.append(("effect", name))

    def allocate(self, name, count, allocation_bound):
        need(count > 0 and allocation_bound >= count, "allocation contract")
        # Allocation bound includes all adapter-specified capacity/slack; a
        # post-hoc capacity comparison cannot authorize an earlier allocation.
        self.operation("allocate:" + name, 1, allocation_bound)
        body = TestBody(name, count, allocation_bound)
        self.owned.append(body)
        return body

    def fail(self, original):
        self.diagnostics.append(original)  # preserve same original object

    def destroy(self):
        need(not self.retired, "destroy once")
        for owner in self.owned:
            owner.live = False
        self.owned.clear()
        self.diagnostics.clear()
        self.retired = True
        # No release inside this frame; carrier/return is external startup P0.
        return TestDestroyed(self)


class TestDestroyed:
    def __init__(self, reservation):
        self.reservation = reservation

    def release(self):
        paid = self.reservation
        need(paid.retired and not paid.owned and not paid.diagnostics, "live owner")
        need(not paid.released, "release once")
        paid.released = True
        paid.root.used_storage = 0
        # Consumed work and peak are deliberately retained.


class TestBody:
    def __init__(self, role, length, allocation_bound):
        self.role, self.length, self.allocation_bound = role, length, allocation_bound
        self.data = None
        self.live = True

    def set_once(self, data):
        need(self.data is None and type(data) is bytes and len(data) == self.length,
             "one immutable complete body")
        self.data = data


@dataclass(frozen=True)
class TestFileIdentity:
    device: int
    inode: int
    length: int
    regular: bool = True
    metadata_version: int = 1


class TestHandle:
    def __init__(self, body, identity, *, slot_valid=True, position=0, responses=None):
        self.body, self.identity = body, identity
        self.final_identity = identity
        self.slot_valid, self.position = slot_valid, position
        self.responses = list(responses or [])
        self.adopted = False


def adopt_slots(paid, handles, *, single_threaded, no_prior_owners, no_close_handlers):
    need(single_threaded and no_prior_owners and no_close_handlers,
         "unsafe descriptor ownership boundary")
    need(len(handles) == 13 and len({id(h) for h in handles}) == 13,
         "exact13 unique inherited slots")
    identities = set()
    for index, handle in enumerate(handles):
        paid.operation("descriptor-check:" + str(index), 1)
        need(handle.slot_valid and not handle.adopted, "invalid or already owned FD")
        paid.operation("metadata-adoption:" + str(index), 1)
        need(handle.identity.regular, "nonregular inherited object")
        key = (handle.identity.device, handle.identity.inode)
        need(key not in identities, "inherited object alias")
        identities.add(key)
        paid.operation("adopt:" + str(index), 1)
        handle.adopted = True
    return handles


def acquire_body(paid, handle, role, cap, *, allocation_bound=None):
    need(handle.adopted, "actual owned handle required")
    paid.operation("metadata:" + role, 1)
    initial = handle.identity
    need(initial.regular, "nonregular")
    paid.operation("offset:" + role, 1)
    need(handle.position == 0, "nonzero offset")
    need(type(initial.length) is int and 0 < initial.length <= cap, "actual extent/cap")
    add(initial.length)  # explicit checked native/u64 conversion model
    bound = initial.length if allocation_bound is None else allocation_bound
    result = paid.allocate(role, initial.length, bound)
    position = 0
    while position < initial.length:
        count = min(BLOCK, initial.length - position)
        used = 0
        for attempt in range(ATTEMPTS):
            paid.operation("read:" + role, 1)
            response = handle.responses.pop(0) if handle.responses else count - used
            if response == "Interrupted":
                continue
            if isinstance(response, BaseException):
                paid.fail(response)
                raise Refused("original read error retained")
            need(type(response) is int and 0 <= response <= count - used, "overreported read")
            need(response > 0 and position + used + response <= len(handle.body), "short input")
            used += response
            if used == count:
                break
        else:
            raise Refused("attempt cap")
        position += count
    for _ in range(ATTEMPTS):
        paid.operation("eof:" + role, 1)
        response = handle.responses.pop(0) if handle.responses else int(len(handle.body) > position)
        if response == "Interrupted":
            continue
        if isinstance(response, BaseException):
            paid.fail(response)
            raise Refused("original EOF error retained")
        need(response == 0, "extra input")
        break
    else:
        raise Refused("EOF attempt cap")
    handle.position = position
    paid.operation("metadata-final:" + role, 1)
    need(handle.final_identity == initial, "metadata changed")
    paid.operation("copy-body:" + role, initial.length)
    result.set_once(handle.body)
    paid.operation("hash:" + role, initial.length)
    return result, hashlib.sha256(result.data).digest()


def acquire_native_paths(paid, paths):
    need(len(paths) == 5, "five paths")
    native, retained = [], []
    for index, (path, cap) in enumerate(zip(paths, paid.root.policy.path_caps)):
        need(type(path) is bytes and 0 < len(path) <= cap and b"\0" not in path,
             "native path extent/shape")
        for target, tag in ((native, "native:"), (retained, "retained:")):
            body = paid.allocate(tag + str(index), len(path), len(path))
            paid.operation("copy:" + body.role, len(path))
            body.set_once(path)
            target.append(body)
    return tuple(native), tuple(retained)


def decode_path_packet(paid, packet):
    need(type(packet) is bytes and 64 <= len(packet) <= paid.root.policy.packet_cap,
         "path packet cap/header")
    paid.operation("decode-path-header", 64)
    need(packet[:8] == b"MIXPTH01" and struct.unpack_from("<Q", packet, 8)[0] == 1,
         "path packet magic/version")
    need(struct.unpack_from("<Q", packet, 16)[0] == len(packet), "path packet total")
    cursor, sections = 64, []
    for index, cap in enumerate(paid.root.policy.path_caps):
        length = struct.unpack_from("<Q", packet, 24 + index * 8)[0]
        need(0 < length <= cap, "path individual cap")
        end = add(cursor, length)
        need(end <= len(packet), "path section extent")
        paid.operation("decode-path:" + str(index), length)
        # A view only in a concrete implementation; this Python slice is model
        # scaffolding, not a claim about Python/production allocator accounting.
        section = packet[cursor:end]
        need(b"\0" not in section, "path NUL")
        sections.append(section)
        cursor = end
    need(cursor == len(packet), "path packet tail")
    return tuple(sections)


def check_dependency_dag(graph):
    """Pure logical dependency control, not source/build authentication."""
    seen, active = set(), set()
    def visit(node):
        need(node not in active, "identity/funding cycle")
        if node in seen:
            return
        active.add(node)
        for predecessor in graph.get(node, ()):
            visit(predecessor)
        active.remove(node)
        seen.add(node)
    for node in graph:
        visit(node)
    return tuple(sorted(seen))


@dataclass(frozen=True)
class TestAdmittedView:
    """Model-only marker; no product admission/cryptographic trust follows."""
    body_ids: tuple
    path_ids: tuple
    immutable: bool


def admit_model_only(paid, bodies, paths, *, trusted_local_launch_contract,
                     all_actual_correspondence, review_provenance):
    need(len(bodies) == 12 and tuple(b.role for b in bodies) == ROLES, "actual12 bodies")
    native, retained = paths
    need(len(native) == len(retained) == 5, "actual5+5 paths")
    all_bodies = tuple(bodies) + native + retained
    need(len({id(body) for body in all_bodies}) == 22, "independent owned bodies")
    need(all(b.live and type(b.data) is bytes for b in all_bodies), "live immutable owner")
    need(all(a.data == b.data for a, b in zip(native, retained)), "native byte correspondence")
    need(trusted_local_launch_contract is True, "digest equality cannot authenticate launcher")
    need(review_provenance is True, "review label cannot authenticate itself")
    need(all_actual_correspondence is True, "actual identity correspondence")
    paid.operation("admit-model-only", 1)
    return TestAdmittedView(tuple(id(b) for b in bodies),
                            tuple(id(b) for b in native + retained), True)


def correlate_before_leaf(paid, admitted, loader_provenance, expected_provenance):
    need(type(admitted) is TestAdmittedView, "admitted model view")
    paid.operation("correlate-before-leaf", 1)
    # Minimum existing-route-compatible check: all fields including4 identities,
    # not just equal digest labels. Different model handles may represent the
    # same immutable object; identity/content correspondence decides admission.
    need(loader_provenance == expected_provenance, "loader/admission mismatch")
    paid.operation("leaf-model-only", 1)
    return "model leaf reached; no product/native execution"
