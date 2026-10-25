# Browser lifecycle pure runtime constructors

This development slice implements only `BrowserAuth.Custody.new/2` and
`BrowserAuth.RuntimeConfig.new/4` from the
[reviewed runtime contract](hosted-browser-lifecycle-runtime-contract.md).
It starts no runtime owner, pool, application, route or provider capability.

Custody requires the exact material keys, a canonical bounded `vault://` reference,
exact reference equality and the existing `Vault.key/2` validation. Runtime
configuration takes the actual hosted configuration value and its role and
identity startup settings. It delegates browser admission to the existing Config
and Manifest and derives the existing ConfigurationDigest. It requires four
distinct restricted role names, separate externally supplied lifecycle
credentials, exact ordinary loader Repo/TLS keys and unchanged connection
accounting. It retains the exact supplied verified TLS roots, SNI and OTP HTTPS
hostname matcher. Matcher admission compares function identity without invoking
supplied functions. Invalid and duplicate options fail closed.

The resulting lifecycle Repo settings use the ordinary exact host/database/port
and TLS with pool size 2, one pool, 5,000-ms connect/query limits, `queue: false`
and disabled sensitive connection errors. Disabled mode requires nil lifecycle
and custody inputs and retains no browser configuration or key. Both error APIs
return only `{:error, :session_unavailable}` and Inspect reveals no material.
The runtime Inspect connection bound is this slice's added two connections;
future aggregate accounting uses the ordinary bound plus two.

Run `python3 verification/hosted-browser-runtime-constructors/run.py` from this
checkout. It compiles only ten explicitly selected ordinary source files to
owned temporary storage and reuses only existing pinned Jason BEAMs. It does not
invoke Mix, the application, broad hosted compilation or any frozen/rejected
lane. Receipts bind source revision, source/dependency hashes, command output,
tool versions, unchanged inputs and scratch cleanup. Initial failures remain in
the attempts directory. The initial selected run passes 30 host methods with no
failures, skips or exclusions; source/dependency continuity and owned scratch
cleanup pass. See the [current receipt](../verification/hosted-browser-runtime-constructors/receipt.json).

Selected tests exercise the actual ordinary loader, Config/Manifest identity
matching, configuration digest and existing Vault preauth AEAD. They mutate
closed keys, role separation/grammar, reference and byte bounds, direct hosts,
pool accounting, TLS verification/roots/SNI and callback identities. The actual
ordinary loader reads the host CA store in these tests; constructors never read
environment, Application state, roots, DNS or network. Only synthetic keys and
passwords are supplied.

This is pure constructor evidence. A struct proves no live startup provenance or
external secret custody. Root acceptance, independently reviewed startup joins,
dedicated Repo/catalog/Store behavior, deployed connection/pool/provider
qualification, browser workflows and customer/FieldLog/GA acceptance remain
pending. Browser/capture/native runtime/phone checks remain paused. No such
process, database or provider connection is started by this slice.
