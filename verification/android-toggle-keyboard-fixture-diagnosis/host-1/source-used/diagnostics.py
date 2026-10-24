"""Use exact sealed finite scroll observer; no native dispatch."""
import support
_upstream=support.load("keyboard_frozen_scroll_capture",support.ROOT/"verification/android-toggle-scroll-failure-analysis/diagnostics.py")
LIMIT=_upstream.LIMIT
capture=_upstream.capture
bind_trace=_upstream.bind_trace
