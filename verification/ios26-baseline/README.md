# iOS 26 product baseline

The user fixed the product minimum at iOS 26.0 and requested iOS 26, 27 and
subsequent releases. There is no public upper major-version cutoff. Raising
this minimum needs an explicit product decision. Each maintained OS version
still requires runtime qualification before support is considered verified.

The nine Swift manifests, generated Swift package and Xcode project, Rust native
archive defaults, and active Apple appearance build commands now target 26.0.
Candidate 1 records 19 passing host CLI tests and a fresh unsigned generated
app cross-build. Both arm64 and x86_64 Simulator Mach-O slices and the app's
Info.plist declare minimum 26.0. Root independently audits all 122 captured
source files, 41 retained artifacts, command logs and the archived app.
`acceptance.json` records that bounded acceptance.

No app or simulator was launched, and no device or screen was accessed. The
private shared-appearance prototype still admits only its previously exercised
iOS 26.5 runtime. Minimum 26.0, maintained 26.x, 27 and future-version runtime
qualification remain pending during the user's pause. Changing deployment
settings alone does not establish native UI behavior or any GA gate.

Historical iOS17 test scripts, signed fixtures and evidence retain their original
inputs; they do not define the active product baseline. The captured source
manifest also includes an incidental ignored Python cache from the CLI resource
directory; it is not an engine dependency or new product source. Rust iOS archive
builds were not repeated for this slice.

`verify.py` is the fresh build procedure and deliberately refuses to replace
candidate-1. `review.py` audits retained bytes plus the original temporary CLI
binary/dependency checkouts and performs offline Mach-O inspection only.
