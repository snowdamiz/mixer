# Dispatcher default authority preaccess oracle

This is an independently derived offline acceptance checklist for the delivered
private `BrowserWorkspaceDispatcher.dispatch/3`. It was prepared before reading
the active `console-dispatcher-default-authority-slice` producer packet. Nothing
in this packet demonstrates a new successful dispatcher request or runtime
authorization. The canonical sources and the accepted prior fixed-dispatcher
packets are the inputs; `source-manifest.json` pins their exact bytes.

The next admissible evidence is a narrowly scoped local fixture run through
the unchanged default BearerIdentity, ConfiguredVerifier, registered KeyOwner,
ordinary controller/CustomerWorkspace and default Repo. The existing test-only
`KeyOwner.start_fixture` changes local destination selection, while ordinary
refresh and certificate/hostname verification remain. This is local identity
trust qualification, not configured production-provider/startup evidence.

`acceptance-oracle.json` separates runtime obligations from source properties.
`adversarial-design.md` specifies independently chosen state transitions and
their exact public outcomes. They are a review/test design, not executed tests.
`verify_sources.py` is an executable offline byte-integrity check; it proves no
authority, SQL policy, compiler behavior or security property by itself.

No compiler, BEAM, test suite, DB, network, UI, capture, native runtime or global
process inventory is used by this lane. Only this verification directory is
owned. Product files, metadata, workflows and Git state are not mutated. Root
coordinates any later frozen-packet review, runtime release and delivery.

Pending beyond any passing local component run: actual configured provider/DNS
path, issuer/OIDC exchange, active server-held token provenance and request-ID
randomness, callback Unit A, session/cookie/browser_auth/lifecycle, Endpoint/
Router/workspace HTTP equivalence, deployed Neon/Cloudflare ingress/log behavior,
controlled lifecycle writers and operational topology, customer/FieldLog,
W14/G22 and GA. Physical phones remain disconnected; native runtime, computer
use and capture remain paused. No GA gate or release is accepted here.
