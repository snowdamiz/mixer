"""Guarded request persistence for this setup-only diagnostic.

Successful payload/journal fsync, exact publication checks, and successful
publication-directory fsync form irrevocable commit. Guard retirement happens
afterward and can block new work, but can never reject or roll back that commit.
A present guard rejects replay. Live retirement uncertainty without durable
evidence does not promise to survive restart. No power-loss testing is claimed.
"""
import hashlib
import json
import os
import pathlib
import stat
import uuid


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'


def digest(value):
    return hashlib.sha256(value).hexdigest()


class PersistenceUncertain(OSError):
    pass


class DiskIO:
    """Actual filesystem operations, individually injectable in host controls."""
    def write(self, path, payload, role):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            remaining = memoryview(payload)
            while remaining:
                count = os.write(fd, remaining)
                if count <= 0:
                    raise OSError('Zero-length persistence write')
                remaining = remaining[count:]
            os.fsync(fd)
        finally:
            os.close(fd)

    def sync(self, path, role):
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            if not stat.S_ISDIR(os.fstat(fd).st_mode):
                raise ValueError('Persistence directory redirected')
            os.fsync(fd)
        finally:
            os.close(fd)

    def publish(self, staged, final, role):
        os.link(staged, final, follow_symlinks=False)

    def unlink(self, path, role):
        os.unlink(path)


def unresolved(folder):
    guard = pathlib.Path(folder) / '.settings-transaction-guard.json'
    # A malformed/partial guard or dangling symlink poisons replay. Only ENOENT
    # establishes absence; EIO/permission errors must never masquerade as absence.
    try:
        os.lstat(guard)
        return True
    except FileNotFoundError:
        return False


class TransactionStore:
    def __init__(self, output, identity):
        self.output = pathlib.Path(output)
        self.identity = identity
        self.io = DiskIO()
        self.guard = self.output / '.settings-transaction-guard.json'
        self.uncertain = unresolved(self.output)
        self.uncertainty = None
        self.retirement_pending = False
        self.retirement = None
        self.ancillary = []
        if self.uncertain:
            raise PersistenceUncertain('Terminal unresolved diagnostic transaction guard')

    def _attempt_receipt(self, attempt, value):
        try:
            self.io.write(attempt / 'outcome.json', encoded({**value, 'ancillary': list(self.ancillary)}), 'attempt-outcome')
            self.io.sync(attempt, 'attempt-outcome-directory')
        except BaseException as error:
            self.ancillary.append({'operation': 'attempt-outcome', 'reason': type(error).__name__ + ': ' + str(error)})

    def _clear_guard(self):
        # Precommit rollback only: callers may reject until owned publications
        # have been durably removed. Postcommit retirement uses the separate,
        # nonthrowing path below and never reaches rollback.
        try:
            self.io.unlink(self.guard, 'guard-clear')
        except BaseException as error:
            # Rollback already durably removed introduced evidence. A reported
            # unlink error can still finish rollback if absence is established.
            if unresolved(self.output):
                raise
            self.ancillary.append({'operation': 'guard-clear-error-after-verified-removal', 'reason': type(error).__name__ + ': ' + str(error), 'protocolOutcomeUnchanged': True})
        if unresolved(self.output):
            raise PersistenceUncertain('Transaction guard was not cleared')

    def resolve_retirement(self):
        """Positively retire a committed guard; never change its protocol outcome.

        A failed stat or directory sync conservatively blocks this live store.
        If the guard is absent on a later offline open, there is no claim that
        a transient in-memory warning was durable across restart.
        """
        # A terminal precommit rollback cannot be relabeled as a committed guard.
        if not self.retirement_pending:
            return not self.uncertain
        errors = []
        try:
            try:
                self.io.unlink(self.guard, 'guard-clear')
            except FileNotFoundError:
                pass
            except BaseException as error:
                errors.append({'operation': 'guard-clear', 'reason': type(error).__name__ + ': ' + str(error), 'protocolOutcomeUnchanged': True})
            # Only a successful absence probe allows retirement. It also catches
            # an unlink implementation that returns without removing the guard.
            if unresolved(self.output):
                raise PersistenceUncertain('Committed transaction guard remains present')
            self.io.sync(self.output, 'postcommit-guard-directory')
        except BaseException as error:
            errors.append({'operation': 'postcommit-guard-retirement', 'reason': type(error).__name__ + ': ' + str(error), 'protocolOutcomeUnchanged': True})
            self.retirement_pending = True
            self.uncertain = True
            self.retirement = {'state': 'unresolved', 'errors': errors, 'committedRequestUnchanged': True,
                               'liveOnlyUnlessGuardPresent': True}
        else:
            self.retirement_pending = False
            self.uncertain = False
            self.retirement = {'state': 'resolved', 'guardAbsenceEstablished': True, 'directoryFsyncSucceeded': True,
                               'committedRequestUnchanged': True}
        self.ancillary.extend(errors)
        return not self.retirement_pending

    def commit(self, record, files):
        if self.uncertain or unresolved(self.output):
            self.uncertain = True
            raise PersistenceUncertain('Terminal unresolved diagnostic transaction guard')
        suffix, value = record
        if not suffix.startswith('settings-') or len(suffix) != 13 or not suffix[9:].isdigit():
            raise ValueError('Closed diagnostic persistence suffix')
        saved = {**value, 'ownedSimulatorIdentity': self.identity}
        values = []
        for slot, form, payload in files:
            name = slot + ('.png' if form == 'png' else '.txt')
            if form not in ['png', 'ax'] or pathlib.PurePath(name).name != name:
                raise ValueError('Closed diagnostic payload path')
            values.append((name, payload, 'payload'))
        values.append(('0000-' + suffix + '.json', encoded(saved), 'journal'))
        if len({name for name, _, _ in values}) != len(values):
            raise ValueError('Duplicate diagnostic persistence target')
        for name, _, _ in values:
            if os.path.lexists(self.output / name):
                raise ValueError('Fixed fresh telemetry artifact')
        attempts = self.output / '.settings-attempts'
        attempts.mkdir(exist_ok=True)
        if attempts.is_symlink() or attempts.resolve() != attempts:
            raise ValueError('Diagnostic attempts directory redirected')
        attempt = attempts / str(uuid.uuid4())
        attempt.mkdir()
        introduced = []
        guarded = False
        try:
            intent = {'schema': 'mixer.settings-transaction-guard.1', 'attempt': attempt.name,
                      'record': saved, 'files': {name: {'sha256': digest(data), 'bytes': len(data)} for name, data, _ in values},
                      'meaning': 'Uncleared guard disqualifies replay; intended bytes are not accepted evidence'}
            self.io.write(self.guard, encoded(intent), 'guard')
            self.io.sync(self.output, 'guard-directory')
            guarded = True
            for name, data, role in values:
                staged = attempt / name
                self.io.write(staged, data, role)
            self.io.sync(attempt, 'staging-directory')
            for name, data, role in values:
                staged, final = attempt / name, self.output / name
                introduced.append((staged, final))
                self.io.publish(staged, final, role)
                if final.is_symlink() or final.read_bytes() != data or not os.path.samefile(staged, final):
                    raise ValueError('Published evidence identity differs')
            self.io.sync(self.output, 'publication-directory')
            # IRREVOCABLE COMMIT: every payload/journal file was fsynced, exact
            # publications were checked, and publication-directory sync returned
            # successfully. Nothing after this try may roll back or reject it.
        except BaseException as original:
            try:
                for staged, final in reversed(introduced):
                    if os.path.lexists(final):
                        if final.is_symlink() or not os.path.samefile(staged, final):
                            raise PersistenceUncertain('Rollback target ownership changed')
                        self.io.unlink(final, 'rollback-' + ('journal' if final.suffix == '.json' else 'payload'))
                self.io.sync(self.output, 'rollback-directory')
                if unresolved(self.output):
                    self._clear_guard()
                self._attempt_receipt(attempt, {'outcome': 'rejected-recoverable', 'error': type(original).__name__ + ': ' + str(original), 'introducedFilesDurablyRemoved': True})
            except BaseException as rollback:
                self.uncertain = True
                try:
                    guard_present = unresolved(self.output)
                except BaseException as probe:
                    guard_present = 'unknown: ' + type(probe).__name__ + ': ' + str(probe)
                self.uncertainty = {'original': type(original).__name__ + ': ' + str(original), 'rollback': type(rollback).__name__ + ': ' + str(rollback), 'durableGuardEstablished': guarded, 'guardPresent': guard_present}
                self._attempt_receipt(attempt, {'outcome': 'terminal-uncertainty', **self.uncertainty})
                raise PersistenceUncertain('Terminal diagnostic persistence uncertainty; unresolved guard; no accepted cursor advance') from original
            raise
        # Both methods are postcommit. Even a reporting wrapper that itself
        # fails cannot escape into Session and reject an already committed ACK.
        self.retirement_pending = True
        try:
            self.resolve_retirement()
        except BaseException as error:
            self.retirement_pending = self.uncertain = True
            self.retirement = {'state': 'unresolved', 'reason': type(error).__name__ + ': ' + str(error), 'committedRequestUnchanged': True, 'liveOnlyUnlessGuardPresent': True}
            self.ancillary.append({'operation': 'postcommit-retirement-reporting', **self.retirement})
        try:
            self._attempt_receipt(attempt, {'outcome': 'committed', 'journal': values[-1][0], 'commitPoint': 'successful-evidence-exact-publication-and-publication-directory-fsync', 'retirement': self.retirement})
        except BaseException as error:
            self.ancillary.append({'operation': 'attempt-outcome-wrapper', 'reason': type(error).__name__ + ': ' + str(error), 'protocolOutcomeUnchanged': True})

    def record_ancillary(self, entry):
        self.ancillary.append(entry)
        # This is explicitly outside protocol commit. Failure remains live-visible
        # even if the medium cannot preserve this supplementary receipt.
        path = self.output / ('ancillary-' + str(uuid.uuid4()) + '.json')
        try:
            self.io.write(path, encoded(entry), 'ancillary')
            self.io.sync(self.output, 'ancillary-directory')
        except BaseException as error:
            self.ancillary.append({'operation': 'ancillary-receipt-unavailable', 'reason': type(error).__name__ + ': ' + str(error), 'protocolOutcomeUnchanged': True})
