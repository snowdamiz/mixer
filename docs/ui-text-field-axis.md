# Explicit text-field axis

`MixerUI.TextField` accepts `axis: .vertical` for a field that grows vertically
through the public Apple `MixerNativeView` adapter. This is the SDK prerequisite
for moving a native multiline title editor into a public UI document without
discarding its declared axis:

```swift
let document = MixerUI.TextField(
    "title", "Title", value: title, action: "title.changed", axis: .vertical
).document(revision: revision)
let host = try MixerUIHost(document: document)
```

The default remains `.horizontal`. Both omitted and explicitly horizontal
authoring produce the exact previous schema-1 node shape, with `label` and `value`
properties and no `axis` property. Vertical authoring adds only
`"axis": "vertical"`; action IDs, scalar values, identity, revision and event
routing keep their existing contracts. Old SDK validators reject the new property
rather than silently rendering a horizontal field.

`UIValidator` defaults to `supportedTextFieldAxes: [.horizontal]`, preserving the
portable supported surface. The public `MixerUIHost` default explicitly admits
both axes and maps them to SwiftUI's native text-field axis. Passing a narrower
validator to the host preserves that restriction for initialization and updates.
Unknown axis strings, wrong value types and an axis on another node kind fail
property validation. A known unsupported axis throws
`UIValidationError.unsupportedTextFieldAxis` before reconciliation changes the
snapshot.

An application that separately owns Apple document reconciliation can explicitly
select the same admission policy:

```swift
var reconciler = UIReconciler(
    validator: UIValidator(supportedTextFieldAxes: [.horizontal, .vertical])
)
```

An opted-in snapshot does not expand another consumer's support. The native
packet-V1 encoder and appearance-V1/V2 resolvers revalidate with the portable
default and reject vertical fields. Android document sessions retain that
default, and Android's packet decoder independently rejects an unknown `axis`
property before touching native views. The default guest value codec rejects
vertical fields; explicitly opting that codec in only admits data and establishes
no guest execution or presentation support. The current guest exchange supports
no text-field node at all.

This slice adds no shared-theme behavior or Android multiline renderer. Its host
tests cover wire compatibility, bounded validation, newline/Unicode values,
current event routing, transactional rejection and unsupported-consumer
revalidation. The Apple tests cover host admission and snapshot routing, without
creating a native view or running input. Native editing, wrapping, focus, IME,
accessibility and cross-platform appearance remain pending while native/UI tests
are paused. FieldLog must consume an immutable published SDK revision from its
separate repository before this becomes consumer integration evidence.
