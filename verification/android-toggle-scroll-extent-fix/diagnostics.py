"""Reuse exact sealed finite trace capture and hash validation; no runtime dispatch."""
import support
_upstream=support.load('extent_frozen_trace_capture',support.SCROLL/'diagnostics.py')
LIMIT=_upstream.LIMIT
capture=_upstream.capture
bind_trace=_upstream.bind_trace
