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

    def handle_signal(self, number, phase):
        """Record only: a handler must never skip launch retention or cleanup."""
        self.pending.append({'signal': int(number), 'phase': phase, 'at_monotonic': self.clock(),
                             'during_launch': self.in_progress,
                             'action': 'deferred-to-explicit-protected-work-checkpoint'})

    def raise_pending(self):
        if self.in_progress:
            raise RuntimeError('interruption checkpoint forbidden before launch handle retention')
        if self.pending:
            raise Stopped('deferred interruption at protected work checkpoint: ' +
                          ','.join(str(item['signal']) for item in self.pending))

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
        return {'launch_in_progress': self.in_progress, 'constructor_returned': self.constructor_returned,
                'constructor_failed': self.constructor_failed, 'deferred_signals': list(self.pending),
                'handle_retained': self.process is not None,
                'retained_pid': None if self.process is None else self.process.pid,
                'signal_mask_modified': False, 'preexec_fn_used': False}

    def record_interruption_failure(self, failures):
        if self.pending:
            failures.append({'classification': 'handled-signal-requested-interruption',
                             'detail': list(self.pending)})


def observed_unblocked_mask():
    # An empty SIG_BLOCK set is a read of the caller's mask; it blocks nothing.
    blocked = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    if blocked:
        raise RuntimeError('refusing to launch child with inherited blocked signals: ' + str(sorted(int(x) for x in blocked)))
    return {'blocked_signals': [], 'query': 'pthread_sigmask(SIG_BLOCK, empty set)', 'mask_changed': False}
