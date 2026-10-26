# Orchestration-only renderer completion signature

Root selects one additional mechanical closure-A leaf signature required by the
accepted Coordinator's two catch sites:

```java
void completeFailedV2(Candidate candidate, Throwable primary, Error firstFatal) {}
```

This no-op belongs only to the orchestration renderer substitute, which has no
field-preservation journal, completion authority or editor-busy implementation.
It must not call check(candidate), mutate authority/ledgers, clear failures or
replace/rethrow the supplied first fatal. The real Coordinator retains its
original remember/firstFatal/throw behavior. Record this explicit stub and its
byte identity alongside editorDisposalBusyV2() returning false. Retain the first
failed compilation which exposed the missing signature.

Closure A does not model or qualify renderer completion, malformed-own handling,
preservation custody, editor-busy exclusion or completion callbacks. Complete
closure B must compile the unchanged accepted concrete renderer and provide those
actual tests. This leaf adjustment changes no product source or original test
assertion. No source/compiled/native/OTA/GA coverage transfers from the no-op.
