"""Fixed /proc task metadata inventory, bounded by the original disposal clock.

No process content is opened. Directory handles pin the enumerated proc object;
name identity and two complete task/namespace/descriptor observations must agree.
No retry, foreign signal, alternate root, or ambiguity-to-zero fallback exists.
"""
from contextlib import contextmanager
import os
import stat
import time

import lifecycle as life

NS_NAMES = ("pid", "mnt", "net", "ipc", "uts")
NS_LINKS = (*NS_NAMES, "pid_for_children")
KINDS = {"pipe", "socket", *NS_NAMES}
ZERO = {"namespaceHolders": 0, "pipeHolders": 0, "socketHolders": 0, "listenerHolders": 0}


class InventoryUnavailable(life.Unavailable):
    """Only sanitized partial numeric observations survive a failed inventory."""
    def __init__(self, counts=None):
        self.observed_counts = None if counts is None else tuple(sorted(counts.items()))


class HolderCounts(dict):
    """Final counts plus immutable references seen earlier in this same scan."""
    def __init__(self, final, observed):
        super().__init__(final)
        self.observed_counts = tuple(sorted(observed.items()))


def directory_stamp(value):
    if not stat.S_ISDIR(value.st_mode):
        raise life.Unavailable()
    return value.st_dev, value.st_ino, value.st_uid


def descriptor_value(raw):
    # Discard ordinary file names immediately; retain only bounded numeric
    # descriptor/namespace identities. No raw link target enters a receipt.
    kind, separator, rest = raw.partition(":[")
    if separator and kind in KINDS and rest.endswith("]") and rest[:-1].isdecimal():
        return kind, int(rest[:-1])
    return "other", 0


class ProcMetadata:
    """Closed read-only Linux adapter. Replaced only by host-test mocks."""
    def root(self):
        return os.open("/proc", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)

    def open(self, parent, name):
        return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)

    def close(self, handle):
        os.close(handle)

    def stamp(self, handle):
        return directory_stamp(os.fstat(handle))

    def named_stamp(self, parent, name):
        return directory_stamp(os.stat(name, dir_fd=parent, follow_symlinks=False))

    def names(self, handle, check):
        names = []
        with os.scandir(handle) as entries:
            for entry in entries:
                check()
                if entry.name.isdecimal():
                    names.append(entry.name)
        if len(names) != len(set(names)):
            raise life.Unavailable()
        return tuple(sorted(names, key=int))

    def namespace(self, handle, name):
        return os.stat(name, dir_fd=handle, follow_symlinks=True).st_ino

    def descriptors(self, handle, check):
        result = []
        # Read links while the iterator remains open. Its temporary descriptor
        # can appear in our own table and must not become a false ENOENT race.
        with os.scandir(handle) as entries:
            for entry in entries:
                check()
                if entry.name.isdecimal():
                    result.append((entry.name, descriptor_value(os.readlink(entry.name, dir_fd=handle))))
        if len(result) != len({name for name, _ in result}):
            raise life.Unavailable()
        return tuple(sorted(result, key=lambda item: int(item[0])))


class Inventory:
    def __init__(self, metadata, deadline_ns):
        self.metadata, self.deadline = metadata, deadline_ns
        self.observations_made = False
        self.partial_counts = dict(ZERO)
        self.seen_references = set()

    def namespace_matches(self, kind, inode):
        return inode in (self.owned_pids if kind == "pid_for_children" else self.owned_namespaces)

    def observe(self, identity, kind, inode, descriptor=None):
        self.observations_made = True
        field = None
        if kind in NS_LINKS and self.namespace_matches(kind, inode):
            field = "namespaceHolders"
        elif kind == "pipe" and inode in self.owned_descriptors:
            field = "pipeHolders"
        elif kind == "socket" and inode in self.owned_descriptors:
            field = "socketHolders"
        reference = identity, kind, inode, descriptor
        if field and reference not in self.seen_references:
            self.seen_references.add(reference)
            self.partial_counts[field] += 1
            self.partial_counts["listenerHolders"] = self.partial_counts["socketHolders"]

    def observe_descriptors(self, handle, values):
        self.observations_made = True
        identity = self.metadata.stamp(handle)
        for descriptor, (kind, inode) in values:
            self.check()
            self.observe(identity, kind, inode, descriptor)

    def check(self):
        if type(self.deadline) is not int or time.monotonic_ns() >= self.deadline:
            raise life.Unavailable()

    @contextmanager
    def opened(self, parent=None, name=None):
        self.check()
        handle = self.metadata.root() if parent is None else self.metadata.open(parent, name)
        try:
            yield handle
        finally:
            self.metadata.close(handle)

    def absent(self, parent, name):
        """Explicitly prove a vanished name, rather than swallowing ENOENT."""
        self.check()
        try:
            self.metadata.named_stamp(parent, name)
        except FileNotFoundError:
            return name not in self.metadata.names(parent, self.check)
        return False

    def unchanged(self, parent, name, handle):
        self.check()
        return self.metadata.named_stamp(parent, name) == self.metadata.stamp(handle)

    def namespaces(self, handle):
        values = []
        identity = self.metadata.stamp(handle)
        for kind in NS_LINKS:
            self.check()
            inode = self.metadata.namespace(handle, kind)
            if type(inode) is not int or inode <= 0:
                raise life.Unavailable()
            values.append(inode)
            self.observe(identity, kind, inode)
        return tuple(values)

    def task(self, task_parent, tid):
        with self.opened(task_parent, tid) as task:
            identity = self.metadata.stamp(task)
            if not self.unchanged(task_parent, tid, task):
                raise life.Unavailable()
            with self.opened(task, "ns") as namespaces, self.opened(task, "fd") as descriptors:
                first_ns = self.namespaces(namespaces)
                self.check()
                first_fd = self.metadata.descriptors(descriptors, self.check)
                self.observe_descriptors(descriptors, first_fd)
                second_ns = self.namespaces(namespaces)
                self.check()
                second_fd = self.metadata.descriptors(descriptors, self.check)
                self.observe_descriptors(descriptors, second_fd)
                if first_ns != second_ns or first_fd != second_fd:
                    raise life.Unavailable()
            if not self.unchanged(task_parent, tid, task):
                raise life.Unavailable()
            return identity, first_ns, first_fd

    def process(self, root, pid):
        with self.opened(root, pid) as process:
            identity = self.metadata.stamp(process)
            if not self.unchanged(root, pid, process):
                raise life.Unavailable()
            with self.opened(process, "task") as tasks:
                before = self.metadata.names(tasks, self.check)
                if not before:
                    raise life.Unavailable()
                found = {}
                for tid in before:
                    self.check()
                    try:
                        found[tid] = self.task(tasks, tid)
                    except FileNotFoundError:
                        if not self.absent(tasks, tid):
                            raise life.Unavailable() from None
                after = self.metadata.names(tasks, self.check)
                if set(after) - set(before):
                    raise life.Unavailable()
                for tid in set(before) - set(after):
                    if not self.absent(tasks, tid):
                        raise life.Unavailable()
                    found.pop(tid, None)
                for tid in after:
                    self.check()
                    if tid not in found or self.metadata.named_stamp(tasks, tid) != found[tid][0]:
                        raise life.Unavailable()
            if not self.unchanged(root, pid, process):
                raise life.Unavailable()
            return identity, found

    def snapshot(self, root):
        before = self.metadata.names(root, self.check)
        # The live controller itself must be visible in a genuine usable proc
        # inventory. An empty enumeration is ambiguity, not evidence of zero.
        if not before:
            raise life.Unavailable()
        found = {}
        for pid in before:
            self.check()
            try:
                found[pid] = self.process(root, pid)
            except FileNotFoundError:
                if not self.absent(root, pid):
                    raise life.Unavailable() from None
        after = self.metadata.names(root, self.check)
        if set(after) - set(before):
            raise life.Unavailable()
        for pid in set(before) - set(after):
            if not self.absent(root, pid):
                raise life.Unavailable()
            found.pop(pid, None)
        for pid in after:
            self.check()
            if pid not in found or self.metadata.named_stamp(root, pid) != found[pid][0]:
                raise life.Unavailable()
        return found

    def gone_between(self, root, pid, previous, tids):
        """Only proven exits may disappear between the two complete passes."""
        try:
            with self.opened(root, pid) as process:
                if self.metadata.stamp(process) != previous[0] or not self.unchanged(root, pid, process):
                    raise life.Unavailable()
                with self.opened(process, "task") as tasks:
                    for tid in tids:
                        if not self.absent(tasks, tid):
                            raise life.Unavailable()
        except FileNotFoundError:
            if not self.absent(root, pid):
                raise life.Unavailable() from None

    def run(self, owned_namespaces, owned_descriptors, owned_pids):
        self.owned_namespaces, self.owned_descriptors, self.owned_pids = owned_namespaces, owned_descriptors, owned_pids
        with self.opened() as root:
            first = self.snapshot(root)
            second = self.snapshot(root)
            if set(second) - set(first):
                raise life.Unavailable()
            for pid, prior in first.items():
                self.check()
                current = second.get(pid)
                if current is None:
                    self.gone_between(root, pid, prior, prior[1])
                    continue
                if current[0] != prior[0] or set(current[1]) - set(prior[1]):
                    raise life.Unavailable()
                missing = set(prior[1]) - set(current[1])
                if missing:
                    self.gone_between(root, pid, prior, missing)
                for tid, values in current[1].items():
                    if values != prior[1][tid]:
                        raise life.Unavailable()
            counts = dict(ZERO)
            for _, tasks in second.values():
                for _, namespaces, descriptors in tasks.values():
                    self.check()
                    counts["namespaceHolders"] += sum(self.namespace_matches(kind, inode) for kind, inode in zip(NS_LINKS, namespaces))
                    for _, (kind, inode) in descriptors:
                        if kind == "pipe" and inode in owned_descriptors:
                            counts["pipeHolders"] += 1
                        elif kind == "socket" and inode in owned_descriptors:
                            counts["socketHolders"] += 1
                        elif kind in NS_NAMES and inode in owned_namespaces:
                            counts["namespaceHolders"] += 1
            counts["listenerHolders"] = counts["socketHolders"]
            self.check()
            return counts


def holder_counts(namespace_ids, descriptor_inodes, deadline_ns=None, *, pid_namespace_ids=()):
    owned_namespaces = {inode for inode in namespace_ids if inode}
    owned_descriptors = set(descriptor_inodes)
    owned_pids = set(pid_namespace_ids)
    if not owned_pids <= owned_namespaces or any(type(inode) is not int or inode <= 0 for inode in owned_pids):
        raise InventoryUnavailable()
    if not owned_namespaces and not owned_descriptors:
        return dict(ZERO)
    if type(deadline_ns) is not int:
        raise InventoryUnavailable()
    inventory = Inventory(ProcMetadata(), deadline_ns)
    try:
        final = inventory.run(owned_namespaces, owned_descriptors, owned_pids)
        return HolderCounts(final, inventory.partial_counts)
    except (life.Unavailable, OSError, ValueError, TypeError, KeyError):
        raise InventoryUnavailable(inventory.partial_counts if inventory.observations_made else None) from None
