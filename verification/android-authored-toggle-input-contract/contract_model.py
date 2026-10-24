"""Independent host specification model. This is not Android/product code.

It models proposed arithmetic, cancellation ownership, and ordinary proposal counts.
It does not emulate Android event dispatch, Switch, accessibility, or JNI.
"""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Geometry:
    density: float = 3.0
    width: float = 1014.0
    height: float = 132.0
    rtl: bool = False
    screen_x: float = 96.0
    screen_y: float = 1566.0

    @property
    def track_left(self):
        return 0.0 if self.rtl else self.width - 63 * self.density

    @property
    def hit_top(self):
        return (self.height - 44 * self.density) / 2

    def endpoint(self, checked):
        origin = 24 if checked != self.rtl else 2
        return self.track_left + (origin + 18.5) * self.density

    def row_contains(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def carrier_contains(self, x, y):
        return self.track_left <= x < self.track_left + 63 * self.density and self.hit_top <= y < self.hit_top + 44 * self.density

    def release_corridor(self, y):
        # Inclusive bounds match Apple's proposed -22...height+22 policy.
        return self.hit_top - 22 * self.density <= y <= self.hit_top + 66 * self.density

class Toggle:
    def __init__(self, checked=False, geometry=None, slop=24.0):
        self.geometry = geometry or Geometry()
        self.slop = slop
        self.bound = self.native = checked
        self.binding = 1
        self.open = True
        self.mode = 'idle'
        self.pressed = False
        self.parent_locked = False
        self.parent_acquires = self.parent_releases = 0
        self.proposals = self.commits = self.raw_checked_callbacks = 0
        self.local_interactions = self.move_jni_calls = 0
        self.preview = None
        self.pointer = None
        self.token = None

    def clear(self, drain=False):
        self.mode = 'drain' if drain else 'idle'
        self.preview = None
        self.pointer = None
        self.token = None
        self.pressed = False
        # Clear ownership before calling a parent; a later callback cannot release it twice.
        if self.parent_locked:
            self.parent_locked = False
            self.parent_releases += 1

    def cancel(self, reason='cancel', drain=True):
        self.clear(drain)

    def bind(self, value):
        self.clear()
        self.binding += 1
        self.bound = value
        self.native = value

    def invalidate(self, reason):
        self.open = False
        self.cancel(reason)

    def down(self, x, y, pointer=0, count=1):
        self.clear()
        if not self.open or count != 1 or not all(map(math.isfinite, (x, y))) or not self.geometry.row_contains(x, y):
            return False
        if self.native != self.bound:
            self.native = self.bound
            return False
        self.local_interactions += 1
        self.mode = 'pending'
        self.pointer = pointer
        self.token = self.binding
        self.initial = self.bound
        self.start_x, self.start_y = x, y
        self.drag_eligible = self.geometry.carrier_contains(x, y)
        self.pressed = True
        return True

    def valid(self, pointer, count):
        return self.open and self.token == self.binding and count == 1 and pointer == self.pointer and self.native == self.bound

    def sample(self, x, y, pointer=0, count=1):
        if self.mode not in ('pending', 'drag'):
            return False
        if not self.valid(pointer, count) or not all(map(math.isfinite, (x, y))):
            self.cancel('invalid-sample')
            return False
        dx, dy = x - self.start_x, y - self.start_y
        if self.mode == 'pending':
            if abs(dy) > self.slop and abs(dy) >= abs(dx):
                self.cancel('vertical-surrender')
                return False
            if abs(dx) > self.slop and abs(dx) > abs(dy):
                if not self.drag_eligible:
                    self.cancel('label-horizontal-movement')
                    return False
                self.mode = 'drag'
                self.parent_locked = True
                self.parent_acquires += 1
        if self.mode == 'drag':
            span = self.geometry.endpoint(True) - self.geometry.endpoint(False)
            value = min(1.0, max(0.0, float(self.initial) + dx / span))
            if value != self.preview:
                self.local_interactions += 1
            self.preview = value
            self.pressed = True
        else:
            self.pressed = self.geometry.row_contains(x, y)
        return True

    def click(self, reject=False, rebind_to=None, expected_binding=None):
        # Native nonpointer activation always ends an in-flight touch first.
        self.clear()
        if not self.open or expected_binding is not None and expected_binding != self.binding:
            return False
        if self.native != self.bound:
            self.native = self.bound
            return False
        self.proposals += 1
        self.native = not self.native
        self.raw_checked_callbacks += 1
        if rebind_to is not None:
            self.bind(rebind_to)
        elif reject:
            self.open = False  # Existing coordinator retires rejected ordinary native input.
        else:
            self.commits += 1
            self.bind(self.native)
        if self.native != self.bound:
            self.native = self.bound
            self.raw_checked_callbacks += 1  # Record.changing suppresses another ordinary proposal.
        return True

    def up(self, x, y, pointer=0, count=1, reject=False, rebind_to=None):
        if not self.sample(x, y, pointer, count):
            self.clear()
            return False
        expected = self.token
        if self.mode == 'drag':
            if not self.geometry.release_corridor(y):
                self.clear()
                return False
            target = self.initial if self.preview == .5 else self.preview > .5
        else:
            if not self.geometry.row_contains(x, y):
                self.clear()
                return False
            target = not self.initial
        self.clear()
        if target == self.bound:
            return True
        return self.click(reject=reject, rebind_to=rebind_to, expected_binding=expected)
