# Initial native V2 nested-row limitation

Both initial native consumers reject interactive controls nested beneath a list
row's root before attachment. Direct button, field and toggle rows keep semantic
content distinct from their minimum hit envelopes. Recursive semantic layout and
native hit routing through smaller container bounds need coordinated gesture
evidence before nested interactive rows can be enabled. Text-only nested stacks
remain within the first slice. This temporary implementation limitation does not
narrow the product's required component and layout support.

This coordinated constraint supplements the internal implementation boundary in
`native-appearance-v2-implementation-boundary.md`. Each native lane must verify
rejection before live editor, hierarchy or action changes; merely reporting an
unsupported arrangement after mutation is insufficient.
