"""Finite atomic-transition model, not a Rust concurrency implementation.

The implementation still needs measured storage, bounded atomic admission,
release/acquire ordering and independent synchronous-dispatch/quiescence proof.
"""


class Gate:
    CONTEXT = 4

    def __init__(self):
        self.mode = 'active'
        self.tokens = {}
        self.flags = 0
        self.footer = None
        self.end_refused = False
        self.next_token = 1

    def enter(self, owner=True):
        # One abstract atomic admission point; no callback may touch the latch
        # or writer before admission. Future CAS retry must be bounded.
        if self.mode != 'active':
            return None
        if len(self.tokens) == 64:
            self.flags |= self.CONTEXT
            return None
        token = self.next_token
        self.next_token += 1
        self.tokens[token] = owner
        return token

    def check_owner(self, token):
        if token not in self.tokens:
            raise ValueError('not admitted')
        if not self.tokens[token]:
            self.flags |= self.CONTEXT

    def borrow_failure(self, token):
        if token not in self.tokens:
            raise ValueError('not admitted')
        self.flags |= self.CONTEXT

    def leave(self, token):
        if token not in self.tokens:
            raise ValueError('duplicate/not admitted leave')
        # All latch writes must precede this release publication. End's count
        # observation must acquire them before accepting a stable snapshot.
        del self.tokens[token]

    def end(self, *, owner=True, quiescence_proven=True):
        if self.mode != 'active':
            raise ValueError('duplicate end')
        self.mode = 'closed'  # abstract atomic admission close
        if not owner or not quiescence_proven or self.tokens:
            self.flags |= self.CONTEXT
            self.end_refused = True
            return None  # do not borrow, flush, footer-write or close live writer
        self.footer = self.flags
        return self.footer
