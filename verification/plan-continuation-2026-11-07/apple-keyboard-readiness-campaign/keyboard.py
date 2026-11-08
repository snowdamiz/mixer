"""Public owned-window keyboard observation; no unproved menu mutation.

AXMain selects a menu target. It does not certify the scope of the action or
shared preferences. There is deliberately no toggle implementation until that
separate contract is established. This module never changes a keyboard setting.
"""
from dataclasses import dataclass
from controller import require, guard_custody


@dataclass(frozen=True)
class KeyboardObservation:
    window: object
    connected: bool
    mark: str
    action_scope: str = 'unestablished'


def observe(backend, expected):
    guard_custody(backend)
    try:
        require(backend.ax_trusted(), 'Fresh same-route AX trust required')
        window = backend.exact_element(expected)
        ax = backend.ax
        require(ax.pid(window) == expected.pid and ax.flag(window, 'AXMain'),
                'Exact owned window must be current menu target')
        app = ax.app(expected.pid)
        main = ax.attr(app, 'AXMainWindow')
        require(ax.equal(main, window), 'Application main window differs from retained owned reference')
        bar = ax.attr(app, 'AXMenuBar')
        stack, found, count = [(bar, 0)], [], 0
        while stack:
            item, depth = stack.pop()
            count += 1
            require(count <= 2000 and depth <= 10, 'Menu traversal bound exceeded')
            if ax.text(item, 'AXTitle', True) == 'Connect Hardware Keyboard':
                found.append(item)
            stack.extend((child, depth+1) for child in ax.children(item))
        require(len(found) == 1, 'Unique public keyboard menu item required')
        item = found[0]
        require(ax.pid(item) == expected.pid and ax.text(item, 'AXRole') == 'AXMenuItem',
                'Keyboard menu role/PID mismatch')
        require(ax.flag(item, 'AXEnabled'), 'Disabled keyboard menu is unknown readiness')
        mark = ax.text(item, 'AXMenuItemMarkChar', True)
        require(mark in ('', '✓'), 'Unknown keyboard checkmark')
        # Rebind after traversal; do not use a stale main-window observation.
        current = backend.exact_element(expected)
        require(ax.equal(current, window) and ax.flag(current, 'AXMain') and
                ax.equal(ax.attr(app, 'AXMainWindow'), window),
                'Owned menu target changed during observation')
        return KeyboardObservation(expected, mark == '✓', mark)
    except BaseException:
        backend.unknown = True
        if getattr(backend, 'c', None) is not None:
            backend.c.unresolved = True
        raise
    finally:
        backend.ax.release()


def require_connected(backend, expected):
    observation = observe(backend, expected)
    require(observation.connected is True,
            'Hardware keyboard disconnected; action scope unestablished, no toggle or native dispatch')
    return observation
