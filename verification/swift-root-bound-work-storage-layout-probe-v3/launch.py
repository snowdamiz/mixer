"""Retain Popen handle before acting on catchable asynchronous launch interruption."""
import signal
import time


class Stopped(BaseException):
    pass


class TrackedLaunch:
    def __init__(self, clock=time.monotonic):
        self.process = None
        self.in_progress = False
        self.pending = []
        self.constructor_returned = False
        self.constructor_failed = False
        self.clock = clock
        self.publication_cutoff = False
        self.cutoff_monotonic = None
        self.frozen_pre_cutoff_pending = None
        self.post_cutoff_signal_count = 0
        self.last_post_cutoff_signal = None

    def handle_signal(self, number, phase):
        """Record only: a handler must never skip launch retention or cleanup."""
        if self.publication_cutoff:
            # A finite observation has completed. These observations are only
            # bounded in-memory classifications, outside its persisted scope.
            # They cannot mutate the already frozen pre-cutoff signal set.
            self.post_cutoff_signal_count = min(self.post_cutoff_signal_count + 1, 2147483647)
            self.last_post_cutoff_signal = {'signal': int(number), 'phase': phase,
                'classification': 'outside-completed-observation-after-publication-cutoff'}
            return
        self.pending.append({'signal': int(number), 'phase': phase, 'at_monotonic': self.clock(),
                             'during_launch': self.in_progress,
                             'action': 'deferred-to-explicit-protected-work-checkpoint'})

    def raise_pending(self):
        if self.in_progress:
            raise RuntimeError('interruption checkpoint forbidden before launch handle retention')
        if self.pending:
            raise Stopped('deferred interruption at protected work checkpoint: ' +
                          ','.join(str(item['signal']) for item in self.pending))

    def begin_publication(self):
        if self.publication_cutoff or self.in_progress:
            raise RuntimeError('publication cutoff requires finished launch and is one-way')
        # This assignment is the logical observed-handler cutoff. Python signal
        # handlers run on this same main thread: a handler before this store
        # appends pending before execution resumes; a handler after it returns
        # through the outside-observation branch above. The snapshot therefore
        # follows the cutoff and cannot miss a pre-cutoff handler observation.
        self.publication_cutoff = True
        self.cutoff_monotonic = self.clock()
        self.frozen_pre_cutoff_pending = tuple(self.pending)
        return {'cutoff_reached': True, 'monotonic_observed_after_cutoff_assignment': self.cutoff_monotonic,
            'pre_cutoff_signal_count': len(self.frozen_pre_cutoff_pending),
            'semantics': 'Handler observations before the one-way cutoff assignment are frozen and reject acceptance. Handler observations after assignment are outside the completed observation; only bounded in-memory classification continues. No promise persists every later signal.',
            'post_cutoff_actions': 'Evidence serialization/publication only; no compiler, source/tool hashes, parsing or product work.'}

    def start(self, constructor):
        if self.in_progress or self.process is not None or self.constructor_returned or self.constructor_failed:
            raise RuntimeError('owned launch may be attempted only once')
        self.raise_pending()
        # This flag remains true across the constructor call and the assignment.
        # No pthread mask mutation and no preexec_fn are used. The catchable
        # signal handler returns during this interval rather than raising inside
        # Popen before its handle can reach our unconditional cleanup path.
        self.in_progress = True
        try:
            self.process = constructor()
            self.constructor_returned = True
        except BaseException:
            self.constructor_failed = True
            raise
        finally:
            self.in_progress = False
        self.raise_pending()
        return self.process

    def receipt(self):
        pending = self.frozen_pre_cutoff_pending if self.publication_cutoff and self.frozen_pre_cutoff_pending is not None else self.pending
        return {'launch_in_progress': self.in_progress, 'constructor_returned': self.constructor_returned,
                'constructor_failed': self.constructor_failed, 'deferred_signals': list(pending),
                'handle_retained': self.process is not None,
                'retained_pid': None if self.process is None else self.process.pid,
                'signal_mask_modified': False, 'preexec_fn_used': False,
                'signal_evidence_scope': 'Frozen pre-cutoff handler observations only. Post-cutoff memory classifications are outside this evidence and are not promised persisted.'}

    def record_interruption_failure(self, failures):
        pending = self.frozen_pre_cutoff_pending if self.publication_cutoff and self.frozen_pre_cutoff_pending is not None else self.pending
        if pending:
            failures.append({'classification': 'handled-signal-requested-interruption',
                             'detail': list(pending)})


def observed_unblocked_mask():
    # An empty SIG_BLOCK set is a read of the caller's mask; it blocks nothing.
    blocked = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    if blocked:
        raise RuntimeError('refusing to launch child with inherited blocked signals: ' + str(sorted(int(x) for x in blocked)))
    return {'blocked_signals': [], 'query': 'pthread_sigmask(SIG_BLOCK, empty set)', 'mask_changed': False}
