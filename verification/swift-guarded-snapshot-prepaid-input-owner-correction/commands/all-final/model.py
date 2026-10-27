"""Pure Python affine ownership regression model, NEVER an OS/trust adapter.

Synthetic work, storage, handles, verification and generations select no policy.
No descriptor is opened/closed. A model retirement is not healthy native close.
"""
from dataclasses import dataclass, asdict
from functools import wraps
import hashlib
import json
import struct

U64_MAX = (1 << 64) - 1
ROLES = ("source", "build", "session", "executable", "compiler",
         "compiler_version", "compile_manifest", "compile_argv",
         "compile_environment", "process_argv", "process_environment", "review")
KNOWN_CAPS = (1947, 131072, 65536, 67108864, None, 16384, 65536,
              16384, 16384, 16384, 16384, None)
BLOCK, ATTEMPTS = 4096, 32
SLOT_ARGS = dict(single_threaded=True, no_prior_owners=True, no_close_handlers=True)


class Refused(ValueError):
    def __init__(self, reason, outcome=None):
        super().__init__(reason)
        self.outcome = outcome


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


def owning_boundary(function):
    @wraps(function)
    def invoke(paid, *args, **kwargs):
        try:
            return function(paid, *args, **kwargs)
        except Refused as original:
            if not paid.retirement_started and not paid.released:
                paid.fail(original)
                original.outcome = paid.outcome
            raise
    return invoke


@dataclass(frozen=True)
class TestPolicy:
    work: int
    storage: int
    role_caps: tuple
    path_caps: tuple
    packet_cap: int
    native_and_diagnostic_contract_complete: bool = True


@dataclass(frozen=True)
class AllocationContract:
    """Future concrete adapter must bound ALL three before invocation.

    requested: complete request, slack: max additional success backing,
    failure_backing: max original error backing overlapping partial allocation.
    These are synthetic logical bounds, never Python/native allocator measures.
    """
    requested: int
    slack: int = 0
    failure_backing: int = 0

    def bound(self, count):
        need(type(count) is int and count > 0, "allocation count")
        need(type(self.requested) is int and self.requested >= count, "requested extent")
        return add(self.requested, self.slack, self.failure_backing)


class TestRoot:
    def __init__(self, policy, *, startup_already_provisioned):
        need(type(policy) is TestPolicy, "source-selected test policy required")
        need(startup_already_provisioned is True, "startup cannot fund itself")
        need(policy.native_and_diagnostic_contract_complete is True, "unpriced native/diagnostic closure")
        need(len(policy.role_caps) == 12 and len(policy.path_caps) == 5, "role counts")
        need(all(type(n) is int and 0 < n <= U64_MAX for n in
                 policy.role_caps + policy.path_caps +
                 (policy.packet_cap, policy.work, policy.storage)), "finite policy")
        self.policy = policy
        self.used_work = self.used_storage = self.peak = 0
        self.reserved = False
        self.trace = []

    def reserve(self, work, storage, *, cleanup_work):
        # No input operation can occur until BOTH finite work partitions exist.
        need(not self.reserved, "one acquisition")
        need(type(work) is int and work > 0 and type(cleanup_work) is int and
             cleanup_work > 0 and type(storage) is int and storage > 0, "complete quote")
        total_work = add(work, cleanup_work)
        next_work, next_storage = add(self.used_work, total_work), add(self.used_storage, storage)
        need(next_work <= self.policy.work, "insufficient work")
        need(next_storage <= self.policy.storage, "insufficient storage")
        self.used_work, self.used_storage = next_work, next_storage
        self.peak = max(self.peak, next_storage)
        self.reserved = True
        self.trace.append(("reserve-operation-cleanup-storage", work, cleanup_work, storage))
        return TestReservation(self, work, storage, cleanup_work)


@dataclass
class Slot:
    index: int
    handle: object
    state: str = "raw"
    adoption_bit: bool = False
    close_attempted: bool = False


class AcquisitionOutcome:
    """One affine carrier for raw obligations, Files, buffers, errors and result."""
    def __init__(self, paid):
        self.reservation = paid
        self.slots = []
        self.adoption_started = False
        self.admission = None
        self.loader_results = []
        self.carrier_live = True
        self.complete_token = None
        self.native_healthy_close_claim = False


class TestReservation:
    def __init__(self, root, work, storage, cleanup_work):
        self.root = root
        self.work_left, self.storage_left = work, storage
        self.storage_charge = storage
        self.cleanup_left = cleanup_work
        self.owned = []
        self.diagnostics = []
        self.effects = []
        self.state = "acquiring"
        self.generation = 1
        self.released = False
        self.retirement_started = False
        self.outcome = AcquisitionOutcome(self)

    @property
    def retired(self):
        return self.state == "retired"

    def fail(self, original):
        # Calls after complete retirement are rejected by the external test
        # caller; they cannot resurrect a destroyed carrier or claim P0 backing.
        if self.retired or self.released:
            return
        if not any(item is original for item in self.diagnostics):
            self.diagnostics.append(original)

    def reject(self, reason):
        if self.retired or self.released:
            raise Refused(reason)  # external caller misuse, no resurrected owner
        original = Refused(reason, self.outcome)
        self.fail(original)
        raise original

    def operation(self, name, work, storage=0):
        if self.state not in ("acquiring", "admitted", "consumed") or self.retirement_started:
            self.reject("retired reservation")
        if not (type(work) is int and 0 < work <= U64_MAX and type(storage) is int and 0 <= storage <= U64_MAX):
            self.reject("positive priced work")
        if work > self.work_left:
            self.reject("operation before work prepay")
        if storage > self.storage_left:
            self.reject("operation before storage prepay")
        self.work_left -= work
        self.storage_left -= storage
        self.root.trace.append(("prepay", name, work, storage))
        self.effects.append(name)
        self.root.trace.append(("effect", name))

    def allocate(self, name, count, contract=None, *, failure=None):
        if contract is None:
            contract = AllocationContract(count)
        need(type(contract) is AllocationContract, "concrete allocation contract required")
        bound = contract.bound(count)
        self.operation("allocate:" + name, 1, bound)
        if failure is not None:
            self.fail(failure)  # same original object, backing already reserved
            self.reject("original allocation failure retained")
        body = TestBody(name, count, bound, self)
        self.owned.append(body)
        return body

    def owns_handle(self, handle):
        return (handle.owner is self and handle.live and handle.adopted and
                any(slot.handle is handle and slot.state == "adopted" for slot in self.outcome.slots))

    def replace_generation_model_only(self):
        need(not self.retirement_started and not self.released, "live generation")
        self.generation += 1  # retained marker will fail; no object/trust minted

    def _cleanup_step(self, name, index, fail_at, original):
        if self.cleanup_left == 0:
            self.fail(Refused("cleanup provision exhausted", self.outcome))
            return False
        self.cleanup_left -= 1
        self.root.trace += [("prepay-cleanup", name, 1), ("cleanup-effect", name)]
        if index == fail_at:
            self.fail(original if original is not None else OSError("synthetic retirement refusal"))
            return False
        return True

    def retirement_plan(self):
        return (["slot:" + str(s.index) for s in self.outcome.slots] +
                ["loader-file:" + str(i) + ":" + str(j)
                 for i, result in enumerate(self.outcome.loader_results) for j in range(len(result.files))] +
                ["loader-body:" + str(i) + ":" + str(j)
                 for i, result in enumerate(self.outcome.loader_results) for j in range(len(result.buffers))] +
                ["body:" + b.role for b in self.owned if type(b) is TestBody and
                 not any(b is x for r in self.outcome.loader_results for x in r.buffers)] +
                ["diagnostics", "results", "carrier"])

    def destroy(self, *, fail_at=None, original=None, unwind_at=None):
        """Bounded MODEL retirement, once. Raw slots NEVER receive close effects.

        Raw/validated obligations conservatively retain the entire reservation
        pending a separately reviewed process-retirement protocol (not supplied).
        """
        need(not self.retirement_started, "retirement once")
        self.retirement_started = True
        self.generation += 1
        self.state = "retiring"
        plan = self.retirement_plan()
        index = 0

        def step(name):
            nonlocal index
            current = index
            index += 1
            if current == unwind_at:
                self.state = "unqualified-retirement"
                raise RuntimeError("synthetic unwind; charge retained")
            return self._cleanup_step(name, current, fail_at, original)

        complete = len(self.outcome.slots) == 13
        for slot in self.outcome.slots:
            if slot.state != "adopted":
                # Only a raw obligation: never close an invalid/unowned integer.
                complete = False
                if not step("retain-raw:" + str(slot.index)):
                    self.state = "unqualified-retirement"
                    return TestDestroyed(self, False)
                continue
            slot.close_attempted = True
            if not step("retire-model-file:" + str(slot.index)):
                self.state = "unqualified-retirement"
                return TestDestroyed(self, False)
            slot.handle.live = False
            slot.handle.slot_valid = False
            slot.state = "retired"
        for result in self.outcome.loader_results:
            for handle in result.files:
                if not step("retire-model-loader-file"):
                    self.state = "unqualified-retirement"
                    return TestDestroyed(self, False)
                handle.live = False
                handle.slot_valid = False
            for body in result.buffers:
                if not step("retire-model-loader-body"):
                    self.state = "unqualified-retirement"
                    return TestDestroyed(self, False)
                body.live = False
        for body in self.owned:
            if type(body) is TestBody and not any(body is x for r in self.outcome.loader_results for x in r.buffers):
                if not step("retire-body:" + body.role):
                    self.state = "unqualified-retirement"
                    return TestDestroyed(self, False)
                body.live = False
        # Incomplete raw retirement retains original diagnostics and carrier too.
        if not complete:
            self.state = "raw-obligations-retained"
            return TestDestroyed(self, False)
        if not step("retire-diagnostics"):
            self.state = "unqualified-retirement"
            return TestDestroyed(self, False)
        self.diagnostics.clear()
        if not step("retire-results"):
            self.state = "unqualified-retirement"
            return TestDestroyed(self, False)
        for result in self.outcome.loader_results:
            result.live = False
        self.outcome.admission = None
        if not step("retire-carrier"):
            self.state = "unqualified-retirement"
            return TestDestroyed(self, False)
        self.outcome.carrier_live = False
        self.state = "retired"
        token = TestDestroyed(self, True)
        self.outcome.complete_token = token
        return token

    def release(self, token):
        need(type(token) is TestDestroyed and token is self.outcome.complete_token and token.complete,
             "complete original retirement token required")
        need(not self.released and not token.used, "release once")
        need(self.retired and not self.outcome.carrier_live and not self.diagnostics and
             all(s.state == "retired" and not s.handle.live for s in self.outcome.slots) and
             all(not b.live for b in self.owned) and
             all(not r.live and all(not h.live for h in r.files) and all(not b.live for b in r.buffers)
                 for r in self.outcome.loader_results), "live owner/result/carrier")
        token.used = self.released = True
        self.root.used_storage -= self.storage_charge


class TestDestroyed:
    def __init__(self, paid, complete):
        self.reservation, self.complete, self.used = paid, complete, False

    def release(self):
        self.reservation.release(self)


class TestBody:
    def __init__(self, role, length, allocation_bound, owner):
        self.role, self.length, self.allocation_bound = role, length, allocation_bound
        self.owner, self.live, self.source_handle = owner, True, None
        self._data = None
        self.acquired_digest = None

    @property
    def data(self):
        return self._data

    def set_once(self, data):
        need(self.live and self._data is None and type(data) is bytes and len(data) == self.length,
             "one immutable complete body")
        self._data = data
        self.acquired_digest = hashlib.sha256(data).digest()


@dataclass(frozen=True)
class TestFileIdentity:
    """Full FileIdentity64. regular metadata gate is distinct from all 8 fields."""
    device: int
    inode: int
    length: int
    mode: int = 0o100600
    mtime: int = 0
    mtime_ns: int = 0
    ctime: int = 0
    ctime_ns: int = 0

    @property
    def regular(self):
        return self.mode & 0o170000 == 0o100000

    def valid(self):
        return (all(type(v) is int and 0 <= v <= U64_MAX for v in
                    (self.device, self.inode, self.length, self.mode)) and
                all(type(v) is int and -(1 << 63) <= v < (1 << 63) for v in
                    (self.mtime, self.mtime_ns, self.ctime, self.ctime_ns)))


class TestHandle:
    def __init__(self, body, identity, *, slot_valid=True, position=0, responses=None):
        self.body, self.identity, self.final_identity = body, identity, identity
        self.slot_valid, self.position = slot_valid, position
        self.responses = list(responses or [])
        self.owner = None
        self.raw_controller = None
        self.live = True
        self._adopted = False

    @property
    def adopted(self):
        return self._adopted

    def close(self):
        raise Refused("only paid outcome model retirement may retire handle")


@owning_boundary
def adopt_slots(paid, handles, *, single_threaded, no_prior_owners, no_close_handlers):
    outcome = paid.outcome
    need(not outcome.adoption_started and paid.state == "acquiring", "adoption once")
    outcome.adoption_started = True
    need(single_threaded is True and no_prior_owners is True and no_close_handlers is True,
         "unsafe descriptor ownership boundary")
    need(type(handles) in (tuple, list) and len(handles) == 13 and
         all(type(h) is TestHandle for h in handles) and len({id(h) for h in handles}) == 13,
         "exact13 unique inherited slots")
    need(all(h.owner is None and h.raw_controller is None and h.live and not h.adopted for h in handles),
         "already controlled/owned inherited slot")
    outcome.slots = [Slot(i, h) for i, h in enumerate(handles)]
    for h in handles:
        h.raw_controller = paid  # affine raw obligation, NOT File ownership
    identities = set()
    for slot in outcome.slots:
        index, handle = slot.index, slot.handle
        paid.operation("descriptor-check:" + str(index), 1)
        need(handle.slot_valid, "invalid FD")
        slot.state = "validated"
        paid.operation("metadata-adoption:" + str(index), 1)
        need(type(handle.identity) is TestFileIdentity and handle.identity.valid() and handle.identity.regular,
             "nonregular/malformed inherited object")
        key = (handle.identity.device, handle.identity.inode)
        need(key not in identities, "inherited object alias")
        identities.add(key)
        paid.operation("adopt:" + str(index), 1)
        # No fallible operation between conversion and immediate outcome move.
        handle._adopted, handle.owner = True, paid
        slot.state, slot.adoption_bit = "adopted", True
        paid.owned.append(handle)
    return outcome


@owning_boundary
def acquire_body(paid, handle, role, cap, *, allocation_contract=None):
    need(paid.owns_handle(handle), "actual paid owned handle required")
    need(not any(type(b) is TestBody and b.source_handle is handle for b in paid.owned), "body acquire once")
    paid.operation("metadata:" + role, 1)
    initial = handle.identity
    need(type(initial) is TestFileIdentity and initial.valid() and initial.regular, "nonregular")
    paid.operation("offset:" + role, 1)
    need(handle.position == 0, "nonzero offset")
    need(type(initial.length) is int and type(cap) is int and 0 < initial.length <= cap <= U64_MAX,
         "actual extent/cap")
    result = paid.allocate(role, initial.length, allocation_contract)
    result.source_handle = handle
    position = 0
    while position < initial.length:
        count, used = min(BLOCK, initial.length - position), 0
        for _ in range(ATTEMPTS):
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
        need(type(response) is int and response == 0, "extra input")
        break
    else:
        raise Refused("EOF attempt cap")
    handle.position = position
    paid.operation("metadata-final:" + role, 1)
    need(handle.final_identity == initial, "metadata changed")
    paid.operation("copy-body:" + role, initial.length)
    result.set_once(handle.body)
    paid.operation("hash:" + role, initial.length)
    return result, result.acquired_digest


@owning_boundary
def acquire_native_paths(paid, paths):
    need(len(paths) == 5, "five paths")
    native, retained = [], []
    for index, (path, cap) in enumerate(zip(paths, paid.root.policy.path_caps)):
        need(type(path) is bytes and 0 < len(path) <= cap and b"\0" not in path, "native path extent/shape")
        for target, tag in ((native, "native:"), (retained, "retained:")):
            body = paid.allocate(tag + str(index), len(path))
            paid.operation("copy:" + body.role, len(path))
            body.set_once(path)
            target.append(body)
    return tuple(native), tuple(retained)


@owning_boundary
def decode_path_packet(paid, packet):
    need(type(packet) is bytes and 64 <= len(packet) <= paid.root.policy.packet_cap, "path packet cap/header")
    paid.operation("decode-path-header", 64)
    need(packet[:8] == b"MIXPTH01" and struct.unpack_from("<Q", packet, 8)[0] == 1, "path packet magic/version")
    need(struct.unpack_from("<Q", packet, 16)[0] == len(packet), "path packet total")
    cursor, sections = 64, []
    for index, cap in enumerate(paid.root.policy.path_caps):
        length = struct.unpack_from("<Q", packet, 24 + index * 8)[0]
        need(0 < length <= cap, "path individual cap")
        end = add(cursor, length)
        need(end <= len(packet), "path section extent")
        paid.operation("decode-path:" + str(index), length)
        section = packet[cursor:end]  # Python scaffolding, never allocator evidence
        need(b"\0" not in section, "path NUL")
        sections.append(section)
        cursor = end
    need(cursor == len(packet), "path packet tail")
    return tuple(sections)


def check_dependency_dag(graph):
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
class AdmittedLoaderCorrespondence:
    """Closed model value constructed internally from verified owned state."""
    source: bytes
    manifest: bytes
    build: bytes
    session: bytes
    executable: bytes
    nonce: bytes
    validation: tuple
    extent: int
    actual4: tuple

    def mapping(self):
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True)
class TestAdmittedView:
    paid: object
    generation: int
    bodies: tuple
    native: tuple
    retained: tuple
    files: tuple
    packet: object
    correspondence: AdmittedLoaderCorrespondence


def _session_decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, "duplicate session field")
            result[key] = value
        return result
    try:
        result = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError) as exc:
        raise Refused("malformed model session") from exc
    need(type(result) is dict and set(result) == {"source", "manifest", "build", "executable", "nonce",
         "validation", "extent", "source_identity"}, "complete model session")
    return result


def _shape(value):
    need(type(value) is dict and set(value) == set(AdmittedLoaderCorrespondence.__dataclass_fields__),
         "complete closed loader provenance")
    need(all(type(value[k]) is bytes and len(value[k]) == 32 for k in
             ("source", "manifest", "build", "session", "executable", "nonce")), "full digest/nonce")
    need(type(value["validation"]) is tuple and len(value["validation"]) == 5 and
         all(type(v) is int and 0 < v <= U64_MAX for v in value["validation"]), "all five validator limits")
    need(type(value["extent"]) is int and 0 < value["extent"] <= U64_MAX, "source extent")
    need(type(value["actual4"]) is tuple and len(value["actual4"]) == 4 and
         all(type(i) is TestFileIdentity and i.valid() and i.regular for i in value["actual4"]), "full four identities")


@owning_boundary
def admit_model_only(paid, bodies, paths, *, trusted_local_launch_contract,
                     all_actual_correspondence, review_provenance):
    need(paid.state == "acquiring" and paid.outcome.admission is None and not paid.retirement_started,
         "one live admission")
    need(len(bodies) == 12 and tuple(b.role for b in bodies) == ROLES, "actual12 bodies")
    native, retained = paths
    need(len(native) == len(retained) == 5, "actual5+5 paths")
    all_bodies = tuple(bodies) + tuple(native) + tuple(retained)
    need(len({id(b) for b in all_bodies}) == 22, "independent owned bodies")
    need(all(type(b) is TestBody and b.owner is paid and b in paid.owned and b.live and
             type(b.data) is bytes and b.acquired_digest == hashlib.sha256(b.data).digest()
             for b in all_bodies), "exact live immutable paid bodies")
    need(all(a.data == b.data for a, b in zip(native, retained)), "native byte correspondence")
    need(trusted_local_launch_contract is True and review_provenance is True and
         all_actual_correspondence is True, "conditional model trust/correspondence required")
    slots = paid.outcome.slots
    need(len(slots) == 13 and all(s.state == "adopted" and s.adoption_bit and paid.owns_handle(s.handle)
                               for s in slots), "all required actual File owners")
    need(all(b.source_handle is slots[i].handle for i, b in enumerate(bodies)), "body File role binding")
    packets = [b for b in paid.owned if type(b) is TestBody and b.role == "path_packet"]
    need(len(packets) == 1 and packets[0].live and packets[0].source_handle is slots[12].handle,
         "actual live packet File/buffer")
    need(decode_path_packet(paid, packets[0].data) == tuple(b.data for b in native), "packet/native correspondence")
    paid.operation("verify-model-session", len(bodies[2].data))
    record = _session_decode(bodies[2].data)
    digests = {"source": bodies[0].acquired_digest, "manifest": bodies[6].acquired_digest,
               "build": bodies[1].acquired_digest, "session": bodies[2].acquired_digest,
               "executable": bodies[3].acquired_digest}
    need(all(record[key] == digests[key].hex() for key in ("source", "manifest", "build", "executable")),
         "actual body/session digest correspondence")
    need(record["extent"] == bodies[0].length and record["source_identity"] == asdict(slots[0].handle.identity),
         "actual source identity/extent correspondence")
    try:
        nonce = bytes.fromhex(record["nonce"]) if type(record["nonce"]) is str else None
    except ValueError:
        nonce = None
    expected = AdmittedLoaderCorrespondence(**digests, nonce=nonce,
                validation=tuple(record["validation"]) if type(record["validation"]) is list else None,
                extent=bodies[0].length, actual4=tuple(s.handle.identity for s in slots[:4]))
    _shape(expected.mapping())
    paid.operation("admit-model-only", 1)
    view = TestAdmittedView(paid, paid.generation, tuple(bodies), tuple(native), tuple(retained),
                            tuple(s.handle for s in slots), packets[0], expected)
    paid.outcome.admission, paid.state = view, "admitted"
    return view


class TestSelectedResult:
    def __init__(self, provenance, files, buffers):
        self.provenance, self.files, self.buffers = provenance, tuple(files), tuple(buffers)
        self.owner = None
        self.live = True
        self.leaf_result = None


def _live_admission(paid, view):
    need(type(view) is TestAdmittedView and view.paid is paid and paid.outcome.admission is view and
         view.generation == paid.generation and paid.state == "admitted" and
         not paid.retirement_started and not paid.released and paid.outcome.carrier_live,
         "original live reservation/generation/one consumption")
    need(tuple(s.handle for s in paid.outcome.slots) == view.files and
         all(paid.owns_handle(h) for h in view.files), "original File owners retained")
    need(all(b.owner is paid and b in paid.owned and b.live and type(b.data) is bytes and
             b.acquired_digest == hashlib.sha256(b.data).digest()
             for b in view.bodies + view.native + view.retained + (view.packet,)), "original backing retained")
    need(tuple(h.identity for h in view.files[:4]) == view.correspondence.actual4,
         "original identities retained")


@owning_boundary
def correlate_before_leaf(paid, admitted, selected, *forbidden_expected):
    # Old four-argument caller-expected API deliberately fails closed.
    need(not forbidden_expected, "caller expected dictionaries forbidden")
    _live_admission(paid, admitted)
    need(type(selected) is TestSelectedResult and selected.live and selected.owner is None,
         "one live selected result")
    need(len(selected.files) == 4 and len({id(h) for h in selected.files}) == 4 and
         all(type(h) is TestHandle and h.live and h.slot_valid and h.owner is None and
             h.raw_controller is None for h in selected.files), "independent loader File owners")
    need(len(selected.buffers) == 4 and len({id(b) for b in selected.buffers}) == 4 and
         all(type(b) is TestBody and b.live and b.owner is paid and b in paid.owned and
             not any(b is original for original in admitted.bodies + admitted.native + admitted.retained +
                     (admitted.packet,)) for b in selected.buffers),
         "loader buffers independently prepaid")
    # Move selected/files/result into the paid outcome before correlation can fail.
    selected.owner = paid
    for handle in selected.files:
        handle.owner, handle._adopted = paid, True
        paid.owned.append(handle)
    paid.outcome.loader_results.append(selected)
    paid.state = "consumed"  # consuming ATTEMPT, including refusal, once
    paid.operation("correlate-before-leaf", 1)
    _shape(selected.provenance)
    need(selected.provenance == admitted.correspondence.mapping(), "loader/admission mismatch")
    need(tuple(h.identity for h in selected.files) == admitted.correspondence.actual4 and
         all(h.final_identity == h.identity and hashlib.sha256(h.body).digest() == digest and
             b.data == h.body for h, b, digest in zip(selected.files, selected.buffers,
             (admitted.correspondence.source, admitted.correspondence.build,
              admitted.correspondence.session, admitted.correspondence.executable))),
         "actual loader File/body correspondence")
    paid.operation("leaf-model-only", 1)
    selected.leaf_result = "model leaf reached; no product/native execution"
    return selected.leaf_result
